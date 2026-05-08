"""
DSA AutoGrader - Grading Service (Orchestrator).

Coordinates the full grading pipeline:
  1. AST analysis  (primary — always works)
  2. AI grading    (optional — only if API key is set)
  3. Plagiarism check
"""

import logging
import asyncio
import time
from typing import Any, Dict, List, Optional

from app.core.config import PORT
from app.core.models import GradingResult
from app.services.ai_grading_service import AIGradingService
from app.services.ast_grader import DSALightningGrader
from app.services.plagiarism_service import PlagiarismService

logger = logging.getLogger("dsa.services.grading")


_BREAKDOWN_MAPPING = {
    "tests": "Testing (Dynamic Tests)",
    "dsa": "Data Structures & Algorithms",
    "pep8": "Code Style (PEP8)",
    "complexity": "Optimization (Complexity)"
}

_IMPROVEMENT_KEYWORDS = ["should", "consider", "need", "optimize", "style", "naming", "blank line", "avoid"]

_COMPONENT_MAX = {
    "tests": 4.0,
    "dsa": 6.0,
    "pep8": 1.0,
    "complexity": 1.0,
}

_RUBRIC_COMPONENT_KEYWORDS = {
    "tests": ["test", "kiểm thử", "case", "correct", "đúng", "chính xác", "output"],
    "dsa": ["algorithm", "thuật toán", "dsa", "data structure", "cấu trúc dữ liệu", "logic"],
    "pep8": ["style", "pep8", "format", "readability", "naming", "coding convention", "trình bày"],
    "complexity": ["complexity", "big o", "optimization", "hiệu năng", "tối ưu", "time", "memory"],
}

class GradingService:
    """
    Main grading orchestrator.
    """

    def __init__(
        self,
        ast_service: DSALightningGrader,
        ai_service: AIGradingService,
        plagiarism_service: PlagiarismService,
        repository: Any,
        job_store: Any,
        event_bus: Any,
    ) -> None:
        self._ast = ast_service
        self._ai = ai_service
        self._plagiarism = plagiarism_service
        self._repository = repository
        self._job_store = job_store
        self._event_bus = event_bus
        self._ai_enabled = True  # Enabled for hybrid grading

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------
    async def grade_submission(
        self,
        files: List[tuple],
        topic: str,
        student_name: str,
        student_id: Optional[str] = None,
        assignment_code: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Grade a batch of files and return aggregated results."""
        start = time.time()
        logger.info(
            "Grading %d file(s) | Student: %s (%s) | Topic: %s",
            len(files), student_name, student_id or "N/A", topic or "Auto",
        )

        rubric_profile = self._load_rubric_profile(assignment_code, topic)

        # Process files concurrently with semaphore limit
        semaphore = asyncio.Semaphore(50)
        total_files = len(files)
        completed_count = 0

        async def _grade_safe(fname: str, fcode: str) -> GradingResult:
            async with semaphore:
                try:
                    res = await self.grade_single_file(
                        fcode,
                        fname,
                        topic,
                        assignment_code=assignment_code,
                        rubric_profile=rubric_profile,
                    )
                except Exception as exc:
                    logger.error("Failed to grade %s: %s", fname, exc)
                    res = self._error_result(fname, str(exc))
                
                res.student_name = student_name
                res.student_id = student_id
                
                # Update progress
                nonlocal completed_count
                completed_count += 1
                if job_id and self._job_store:
                    job_data = await self._job_store.get(job_id)
                    if job_data:
                        job_data["progress"] = {
                            "current": completed_count,
                            "total": total_files,
                            "percent": int((completed_count / total_files) * 100)
                        }
                        await self._job_store.set(job_id, job_data)
                
                return res

        tasks = [_grade_safe(fn, fc) for fn, fc in files]
        results: List[GradingResult] = await asyncio.gather(*tasks)

        # Plagiarism check
        plagiarism_alerts = await self.check_plagiarism(results, assignment_code)

        # Summary
        elapsed = time.time() - start
        scores = [r.total_score for r in results if r.total_score is not None]
        avg = round(sum(scores) / len(scores), 1) if scores else 0.0

        # Save to DB
        saved_db_count = self._save_to_database(
            results, job_id, student_name, student_id, topic, assignment_code
        )

        summary = {
            "total_files": len(results),
            "avg_score": avg,
            "total_time": f"{elapsed:.1f}s",
            "plagiarism_alerts": len(plagiarism_alerts),
            "saved_to_db": saved_db_count,
        }
        logger.info("Grading completed: %s", summary)

        return {
            "results": [self._to_dict(r) for r in results],
            "summary": summary,
            "plagiarism_alerts": plagiarism_alerts,
        }

    def _save_to_database(
        self,
        results: List[GradingResult],
        job_id: Optional[str],
        student_name: str,
        student_id: Optional[str],
        topic: str,
        assignment_code: Optional[str]
    ) -> int:
        """Save all grading results to database."""
        if not self._repository or not results:
            return 0

        dicts_to_save = []
        for r in results:
            d = self._to_dict(r)
            d["job_id"] = job_id or ""
            d["student_name"] = student_name
            d["student_id"] = student_id or ""
            d["topic"] = topic
            dicts_to_save.append(d)

        try:
            saved_ids = self._repository.save_batch_results(dicts_to_save, assignment_code)
            logger.info("[SUCCESS] Saved %d submissions to database", len(saved_ids))
            return len(saved_ids)
        except Exception as e:
            logger.error("[ERROR] Failed to save to db: %s", e)
            # Try saving one by one
            saved_count = 0
            for result_dict in dicts_to_save:
                try:
                    self._repository.save_result(result_dict)
                    saved_count += 1
                    logger.info("[SUCCESS] Saved individual submission")
                except Exception as e2:
                    logger.error("[ERROR] Failed to save individual: %s", e2)
            return saved_count

    async def grade_single_file(
        self,
        code: str,
        filename: str,
        topic: str,
        assignment_code: Optional[str] = None,
        rubric_profile: Optional[Dict[str, Any]] = None,
    ) -> GradingResult:
        """Grade a single file through AST pipeline (+ AI optional)."""
        logger.debug("Grading: %s", filename)

        # Step 1 — AST analysis (always runs)
        try:
            from starlette.concurrency import run_in_threadpool
            ast_result = await run_in_threadpool(
                self._ast.grade_file_ultra_fast, code, filename, topic
            )
        except Exception as exc:
            logger.error("AST grading failed for %s: %s", filename, exc)
            return self._error_result(filename, f"AST analysis error: {str(exc)}")

        # Step 2 — AI grading (optional)
        if self._ai_enabled:
            try:
                ai_result = await self._ai.grade_with_ai(
                    code=code,
                    filename=filename,
                    topic=topic,
                    ast_report=ast_result,
                    rubric_context=rubric_profile,
                )
                merged = self._combine(ast_result, ai_result, code)
                return self._apply_rubric_to_result(merged, rubric_profile)
            except Exception as exc:
                logger.warning("AI grading failed, falling back to AST: %s", exc)

        ast_only = self._ast_to_result(ast_result, filename, code)
        return self._apply_rubric_to_result(ast_only, rubric_profile)

    async def check_plagiarism(
        self,
        results: List[GradingResult],
        assignment_code: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Check plagiarism within and across submissions."""
        logger.info("Checking plagiarism for %d results.", len(results))

        intra = await self._plagiarism.check_intra_job_plagiarism(results)
        cross = await self._plagiarism.check_cross_job_plagiarism(results, assignment_code)
        alerts = intra + cross

        if alerts:
            logger.warning("Plagiarism detected: %d alerts.", len(alerts))
        return alerts

    # ------------------------------------------------------------------
    #  Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_score(raw_score: Any) -> float:
        """Normalize score to 0-100 scale."""
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            return 0.0

        return round(max(0.0, min(score, 100.0)), 1)

    def _ast_to_result(
        self,
        ast_result: Dict[str, Any],
        filename: str,
        code: str = "",
    ) -> GradingResult:
        """Convert AST result dict to GradingResult object."""
        score = self._normalize_score(ast_result.get("total_score", 0))
        status = "AC" if score >= 50.0 else "WA"

        algorithms = ast_result.get("algorithms", [])
        if isinstance(algorithms, str):
            algorithms = [a.strip() for a in algorithms.split(",") if a.strip()]

        ast_breakdown = ast_result.get("breakdown", {})
        breakdown = {
            "logic_score": ast_breakdown.get("tests", 0),
            "algorithm_score": ast_breakdown.get("dsa", 0),
            "style_score": ast_breakdown.get("pep8", 0),
            "optimization_score": ast_breakdown.get("complexity", 0),
        }

        # Get detailed test results
        test_results = ast_result.get("test_results", [])

        return GradingResult(
            filename=filename,
            total_score=score,
            status=status,
            algorithms_detected=algorithms,
            feedback=self._ast_feedback(ast_result),
            time_used=ast_result.get("runtime_ms", 0.0) / 1000.0,
            memory_used=0.0,
            plagiarism_detected=False,
            has_rubric=True,
            breakdown=breakdown,
            reasoning="\n".join(ast_result.get("notes", [])),
            complexity=ast_result.get("complexity", "O(n)"),
            complexity_analysis=next((n for n in ast_result.get("notes", []) if "Hiệu năng:" in n), None),
            fingerprint="|".join(map(str, ast_result.get("fingerprint", []))) if isinstance(ast_result.get("fingerprint"), list) else None,
            code=code,
            language="python",
            test_results=test_results,
            complexity_curve=self._generate_complexity_curve(ast_result.get("complexity", "O(n)")),
        )

    @staticmethod
    def _ast_feedback(ast_result: Dict[str, Any]) -> str:
        """Build student-friendly feedback from AST result in Vietnamese."""
        lines = ["## Kết quả chấm điểm chi tiết\n"]
        score = ast_result.get("total_score", 0)

        breakdown = ast_result.get("breakdown", {})
        if breakdown:
            lines.append("### Phân bổ điểm số:")
            for cat, val in breakdown.items():
                label = _BREAKDOWN_MAPPING.get(cat, cat)
                # Simple translation for categories
                labels_vn = {
                    "tests": "Kiểm thử (Dynamic Tests)",
                    "dsa": "Cấu trúc dữ liệu & Thuật toán",
                    "pep8": "Phong cách lập trình (PEP8)",
                    "complexity": "Tối ưu hóa (Complexity)"
                }
                lines.append(f"- **{labels_vn.get(cat, label)}**: {val} điểm")

        algos = ast_result.get("algorithms", [])
        if algos:
            label = ", ".join(algos) if isinstance(algos, list) else algos
            lines.append(f"\n### Thuật toán phát hiện: `{label}`")

        notes = ast_result.get("notes", [])
        if notes:
            main_notes = []
            improvements = []

            for n in notes:
                if any(x in n for x in ["/10", "đ)"]):
                    continue
                if any(kw in n.lower() for kw in _IMPROVEMENT_KEYWORDS):
                    improvements.append(n)
                else:
                    main_notes.append(n)

            if main_notes:
                lines.append("\n### Nhận xét & Đánh giá:")
                for n in main_notes:
                    lines.append(f"- {n}")

            if improvements:
                lines.append("\n### 💡 Gợi ý cải thiện:")
                for n in improvements:
                    lines.append(f"- {n}")
            elif score >= 9.0:
                lines.append("\n### 💡 Gợi ý cải thiện:")
                lines.append("- Mã nguồn của em rất tốt. Hãy thử thách với các bộ dữ liệu lớn hơn hoặc tối ưu bộ nhớ.")

        if score >= 8.0:
            lines.append("\n**XUẤT SẮC!** Mã nguồn của em rất chất lượng.")
        elif score >= 5.0:
            lines.append("\n**ĐẠT YÊU CẦU.** Em có thể tối ưu thêm mã nguồn của mình.")
        else:
            lines.append("\n**CẦN CỐ GẮNG.** Hãy xem các nhận xét bên trên để cải thiện bài làm.")

        return "\n".join(lines)

    def _load_rubric_profile(self, assignment_code: Optional[str], topic: str) -> Optional[Dict[str, Any]]:
        """Load rubric criteria from DB and prepare a profile for runtime scoring."""
        if not self._repository:
            return None

        # Priority 1: SQL Server table dbo.BAITAP (requested production source)
        baitap_rows: List[Dict[str, Any]] = []
        try:
            baitap_rows = self._repository.get_baitap_criteria(assignment_code, topic)
        except Exception as exc:
            logger.warning("Cannot load rubric from dbo.BAITAP: %s", exc)

        if baitap_rows:
            criteria = []
            total_max = 0.0

            for item in baitap_rows:
                max_score = float(item.get("max_score") or 0)
                if max_score <= 0:
                    continue

                name = (item.get("criteria_name") or "Tiêu chí").strip()
                description = (item.get("description") or "").strip()
                component_hint = (item.get("component") or "").strip().lower()

                if component_hint:
                    components = self._map_rubric_components(component_hint, description)
                else:
                    components = self._map_rubric_components(name, description)

                total_max += max_score
                criteria.append(
                    {
                        "name": name,
                        "description": description,
                        "max_score": max_score,
                        "components": components,
                    }
                )

            if criteria and total_max > 0:
                return {
                    "source": "dbo.BAITAP",
                    "assignment_code": assignment_code,
                    "topic": topic,
                    "criteria": criteria,
                    "total_max": total_max,
                }

        return None

    @staticmethod
    def _map_rubric_components(criteria_name: str, description: str) -> List[str]:
        """Map a rubric criterion to grading components using keyword matching."""
        text = f"{criteria_name} {description}".lower()
        mapped = []

        for comp, keywords in _RUBRIC_COMPONENT_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                mapped.append(comp)

        # If no explicit keyword is found, treat it as an overall criterion.
        return mapped

    def _apply_rubric_to_result(
        self,
        result: GradingResult,
        rubric_profile: Optional[Dict[str, Any]],
    ) -> GradingResult:
        """Rescore result using rubric criteria loaded from database."""
        if not rubric_profile:
            return result

        breakdown = result.breakdown or {}
        component_scores = {
            "tests": float(breakdown.get("logic_score", 0) or 0),
            "dsa": float(breakdown.get("algorithm_score", 0) or 0),
            "pep8": float(breakdown.get("style_score", 0) or 0),
            "complexity": float(breakdown.get("optimization_score", 0) or 0),
        }

        component_ratio = {}
        for component, score in component_scores.items():
            max_value = _COMPONENT_MAX.get(component, 1.0)
            ratio = score / max_value if max_value > 0 else 0.0
            component_ratio[component] = max(0.0, min(ratio, 1.0))

        criteria_results = []
        total_points = 0.0
        total_weight = rubric_profile["total_max"]

        all_components = ["tests", "dsa", "pep8", "complexity"]

        for criterion in rubric_profile["criteria"]:
            criterion_weight_10 = (criterion["max_score"] / total_weight) * 10.0
            components = criterion["components"] or all_components
            criterion_ratio = sum(component_ratio[c] for c in components) / len(components)
            earned = round(criterion_ratio * criterion_weight_10, 2)
            total_points += earned
            criteria_results.append({
                "name": criterion["name"],
                "earned": earned,
                "max": round(criterion_weight_10, 2),
            })

        result.total_score = round(min(max(total_points, 0.0), 100.0), 1)
        result.status = "AC" if result.total_score >= 50.0 else "WA"
        result.has_rubric = True

        if result.feedback:
            source_label = rubric_profile.get("source", "database")
            lines = ["", f"### Chấm theo tiêu chí từ cơ sở dữ liệu ({source_label})"]
            for item in criteria_results:
                lines.append(f"- {item['name']}: {item['earned']}/{item['max']} điểm")
            result.feedback = f"{result.feedback}\n" + "\n".join(lines)

        return result

    @staticmethod
    def _combine(
        ast_result: Dict[str, Any],
        ai_result: GradingResult,
        code: str,
    ) -> GradingResult:
        """Merge AST and AI results with weighted scoring."""
        ast_score = GradingService._normalize_score(ast_result.get("total_score", 0))
        ai_score = GradingService._normalize_score(ai_result.total_score or 0)

        weighted = round(0.4 * ast_score + 0.6 * ai_score, 1)
        final = weighted if ai_score >= 50 else max(weighted, ast_score)
        final = GradingService._normalize_score(final)

        ast_breakdown = ast_result.get("breakdown", {})
        breakdown = {
            "logic_score": ast_breakdown.get("tests", 0),
            "algorithm_score": ast_breakdown.get("dsa", 0),
            "style_score": ast_breakdown.get("pep8", 0),
            "optimization_score": ast_breakdown.get("complexity", 0),
        }

        ast_algos = ast_result.get("algorithms", [])
        if isinstance(ast_algos, str):
            ast_algos = [a.strip() for a in ast_algos.split(",") if a.strip()]

        combined_algos = list(set(ai_result.algorithms_detected + ast_algos))

        return GradingResult(
            filename=ai_result.filename,
            total_score=final,
            status=ai_result.status,
            algorithms_detected=combined_algos,
            feedback=ai_result.feedback,
            time_used=ast_result.get("runtime_ms", 0.0) / 1000.0,
            memory_used=ai_result.memory_used,
            plagiarism_detected=ai_result.plagiarism_detected,
            has_rubric=True,
            breakdown=breakdown,
            strengths=ai_result.strengths,
            weaknesses=ai_result.weaknesses,
            reasoning=ai_result.reasoning,
            improvement=ai_result.improvement,
            complexity=ast_result.get("complexity", "O(n)"),
            complexity_analysis=ai_result.complexity_analysis,
            complexity_curve=GradingService._generate_complexity_curve(ast_result.get("complexity", "O(n)")),
            optimized_code=ai_result.optimized_code,
            code=code,
            language="python",
        )

    @staticmethod
    def _error_result(filename: str, error: str) -> GradingResult:
        """Create result for failed grading."""
        return GradingResult(
            filename=filename,
            total_score=0,
            status="RE",
            algorithms_detected=[],
            feedback=f"Grading failed: {error}",
            time_used=0.0,
            memory_used=0.0,
            plagiarism_detected=False,
            code=None,
            language="python",
        )

    @staticmethod
    def _to_dict(result: GradingResult) -> Dict[str, Any]:
        """Serialize GradingResult to dict."""
        return {
            "filename": result.filename,
            "total_score": result.total_score,
            "status": result.status,
            "algorithms_detected": result.algorithms_detected,
            "feedback": result.feedback,
            "time_used": result.time_used,
            "memory_used": result.memory_used,
            "plagiarism_detected": result.plagiarism_detected,
            "plagiarism_matches": result.plagiarism_matches,
            "has_rubric": result.has_rubric,
            "breakdown": result.breakdown,
            "complexity": result.complexity,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "reasoning": result.reasoning,
            "improvement": result.improvement,
            "complexity_analysis": result.complexity_analysis,
            "student_name": result.student_name,
            "student_id": result.student_id,
            "code": result.code,
            "language": result.language,
            "test_results": getattr(result, "test_results", []),
            "optimized_code": getattr(result, "optimized_code", None),
            "complexity_curve": getattr(result, "complexity_curve", []),
        }

    @staticmethod
    def _generate_complexity_curve(complexity_str: str) -> List[Dict[str, Any]]:
        """Generate dummy data points for visual complexity chart."""
        import math
        points = []
        n_values = [10, 20, 50, 100, 200, 500, 1000]
        
        # Determine actual curve type
        is_n2 = "n^2" in complexity_str or "square" in complexity_str.lower()
        is_n3 = "n^3" in complexity_str
        is_logn = "log" in complexity_str.lower()
        is_nlogn = "n log" in complexity_str.lower()

        for n in n_values:
            # Baseline (Optimal O(n) or O(log n))
            optimal_val = n if not is_logn else math.log2(n) * 10
            
            # Student's val
            if is_n3:
                student_val = (n ** 3) / 10000 
            elif is_n2:
                student_val = (n ** 2) / 100
            elif is_nlogn:
                student_val = n * math.log2(n) / 5
            elif is_logn:
                student_val = math.log2(n) * 12
            else: # O(n) or unknown
                student_val = n * 1.1 

            points.append({
                "n": n,
                "student": round(student_val, 2),
                "optimal": round(optimal_val, 2)
            })
        return points
