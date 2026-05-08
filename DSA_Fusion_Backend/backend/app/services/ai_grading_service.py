"""
DSA AutoGrader - AI Grading Service (Optimized with Retry Logic).

Features:
- Exponential backoff retry (3 attempts)
- Circuit breaker pattern
- Response caching
- Graceful fallback
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.models import GradingResult

logger = logging.getLogger("dsa.services.ai_grading")

# Maximum code length sent to the AI (characters)
_MAX_CODE_LENGTH = 15_000
_MAX_FEEDBACK_CODE = 3_000

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # seconds
MAX_RETRY_DELAY = 10.0  # seconds
RETRY_EXPONENT = 2.0  # Exponential backoff factor

# Circuit breaker configuration
CIRCUIT_BREAKER_THRESHOLD = 5  # Failures before opening circuit
CIRCUIT_BREAKER_TIMEOUT = 60  # Seconds to wait before half-open


@dataclass
class CircuitBreakerState:
    """Circuit breaker state."""
    failures: int = 0
    last_failure_time: float = 0.0
    state: str = "closed"  # closed, open, half-open


class AIGradingService:
    """
    AI-powered grading service with retry logic and circuit breaker.

    Dependencies:
    - ``IAIProvider`` (Gemini, OpenAI …)
    - ``IGradingRepository`` (database, for history)
    """

    def __init__(
        self,
        ai_provider: Any,
        repository: Any,
    ) -> None:
        self._ai = ai_provider
        self._repository = repository
        self._prompt = self._build_prompt()
        self._circuit_breaker = CircuitBreakerState()
        self._response_cache: Dict[str, Any] = {}  # Simple cache
        self._cache_ttl = 3600  # 1 hour
        
        # Quota tracking (free tier limit: 20/day, we use 15 to be safe)
        from app.core.config import AI_QUOTA_PER_DAY
        self._daily_quota = AI_QUOTA_PER_DAY
        self._usage_today = 0
        self._usage_date = time.strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    #  Quota Management
    # ------------------------------------------------------------------
    def _check_quota(self) -> bool:
        """Check if we're within daily quota limit."""
        # Reset counter if new day
        today = time.strftime("%Y-%m-%d")
        if today != self._usage_date:
            self._usage_today = 0
            self._usage_date = today
        
        if self._usage_today >= self._daily_quota:
            logger.warning("AI daily quota exceeded (%d/%d). Falling back to AST grading.", 
                          self._usage_today, self._daily_quota)
            return False
        
        return True

    def _record_usage(self) -> None:
        """Record one AI usage."""
        self._usage_today += 1
        logger.info("AI usage: %d/%d today", self._usage_today, self._daily_quota)

    # ------------------------------------------------------------------
    #  Circuit Breaker
    # ------------------------------------------------------------------
    def _can_execute(self) -> bool:
        """Check if circuit breaker allows execution."""
        if self._circuit_breaker.state == "closed":
            return True

        if self._circuit_breaker.state == "open":
            # Check if timeout has passed
            if time.time() - self._circuit_breaker.last_failure_time > CIRCUIT_BREAKER_TIMEOUT:
                self._circuit_breaker.state = "half-open"
                logger.info("Circuit breaker half-open, testing...")
                return True
            return False

        # Half-open - allow one test request
        return True

    def _record_success(self) -> None:
        """Record successful execution."""
        self._circuit_breaker.failures = 0
        self._circuit_breaker.state = "closed"

    def _record_failure(self) -> None:
        """Record failed execution."""
        self._circuit_breaker.failures += 1
        self._circuit_breaker.last_failure_time = time.time()

        if self._circuit_breaker.failures >= CIRCUIT_BREAKER_THRESHOLD:
            self._circuit_breaker.state = "open"
            logger.warning("Circuit breaker OPEN after %d failures", self._circuit_breaker.failures)

    # ------------------------------------------------------------------
    #  Retry Logic with Exponential Backoff
    # ------------------------------------------------------------------
    async def _execute_with_retry(self, func, *args, **kwargs) -> Any:
        """Execute function with retry logic and exponential backoff."""
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                # Check circuit breaker
                if not self._can_execute():
                    raise Exception(
                        f"Circuit breaker is open. Try again after {CIRCUIT_BREAKER_TIMEOUT}s"
                    )

                result = await func(*args, **kwargs)
                self._record_success()
                return result

            except Exception as exc:
                last_exception = exc
                self._record_failure()

                if attempt == MAX_RETRIES - 1:
                    # Last attempt - re-raise
                    logger.error("All %d retry attempts failed", MAX_RETRIES)
                    raise last_exception

                # Calculate delay with exponential backoff + jitter
                delay = min(
                    INITIAL_RETRY_DELAY * (RETRY_EXPONENT ** attempt),
                    MAX_RETRY_DELAY
                )
                jitter = delay * 0.1 * (0.5 + asyncio.get_event_loop().time() % 1)
                total_delay = delay + jitter

                logger.warning(
                    "AI grading attempt %d failed: %s. Retrying in %.2fs...",
                    attempt + 1, exc, total_delay
                )
                await asyncio.sleep(total_delay)

        # Should not reach here, but just in case
        # Initial wait-time for re-execution
        raise last_exception

    # ------------------------------------------------------------------
    #  Prompt template
    # ------------------------------------------------------------------
    @staticmethod
    def _build_prompt() -> str:
        """Return the grading prompt template for multi-file grading."""
        return """
Bạn là một Senior Software Engineer và Giảng viên DSA chuyên nghiệp, có nhiều năm kinh nghiệm chấm bài, code review, và mentoring.

## VAI TRÒ & NHIỆM VỤ:
Bạn đang chấm điểm bài nộp môn **Cấu trúc dữ liệu và Thuật toán (DSA)**.
Bài nộp có thể chứa **1 hoặc nhiều file** Python. Hãy chấm từng file một cách công bằng, khách quan và chuyên nghiệp.

## NGUYÊN TẮC CHẤM ĐIỂM (BẮT BUỘC):
1. **Công bằng tuyệt đối**: Chỉ chấm theo bằng chứng trong code, AST report và rubric. Không suy diễn ngoài dữ kiện.
2. **Không thiên vị**: Không phân biệt tên sinh viên, độ dài code, phong cách viết (nếu vẫn đúng chuẩn).
3. **Nhất quán**: Cùng mức lỗi → cùng mức trừ điểm giữa các file/bài.
4. **Bảo thủ khi thiếu dữ liệu**: Nếu không đủ bằng chứng, chấm保守 và ghi rõ mức độ chắc chắn.
5. **Ưu tiên tiêu chí bắt buộc**: Độ đúng thuật toán > Độ phức tạp > Code style > Tối ưu hóa.
6. **Phản hồi có giá trị**: Mọi nhận xét phải gắn với tiêu chí cụ thể, có ví dụ, có hành động cải thiện.

## TIÊU CHÍ CHẤM ĐIỂM CHI TIẾT (Thang điểm 10/file):

### 1. **Correctness (Độ đúng) - 4.0 điểm**
- Code có chạy đúng yêu cầu đề bài không?
- Có xử lý được tất cả test cases không?
- Có edge cases nào bị bỏ sót không?
- Logic thuật toán có chính xác không?

### 2. **Algorithm & Data Structure (Thuật toán & Cấu trúc dữ liệu) - 3.0 điểm**
- Có sử dụng đúng thuật toán cho topic không?
- Độ phức tạp thời gian (Time Complexity) có tối ưu không?
- Độ phức tạp bộ nhớ (Space Complexity) có hợp lý không?
- Có sử dụng cấu trúc dữ liệu phù hợp không?

### 3. **Code Quality & PEP8 (Chất lượng code) - 2.0 điểm**
- Code có tuân thủ PEP8 không?
- Đặt tên biến/hàm có rõ ràng, có ý nghĩa không?
- Có comment/docstring giải thích logic phức tạp không?
- Code có modular, dễ đọc, dễ bảo trì không?

### 4. **Optimization & Best Practices (Tối ưu & Thực hành tốt) - 1.0 điểm**
- Có sử dụng Python idioms phù hợp không?
- Có tránh code duplication không?
- Có xử lý error/exception hợp lý không?
- Có thể tối ưu thêm được không?

## HƯỚNG DẪN CHO ĐIỂM:
- **9.0-10.0**: Hoàn hảo, không lỗi, tối ưu, code sạch
- **7.5-8.9**: Tốt, có thể cải thiện nhỏ, đúng thuật toán
- **6.0-7.4**: Đạt yêu cầu, có lỗi nhỏ hoặc chưa tối ưu
- **4.0-5.9**: Dưới trung bình, sai logic hoặc thiếu nhiều
- **0.0-3.9**: Không đạt, sai nghiêm trọng hoặc không chạy được

## THÔNG TIN BÀI NỘP:
- **Chủ đề (Topic):** {topic}
- **Tên file (Filename):** {filename}
- **Số file trong batch:** (Nếu có nhiều file, chấm riêng từng file)

## MÃ NGUỒN SINH VIÊN:
```python
{code}
```

## BÁO CÁO PHÂN TÍCH AST:
{ast_report}

## TIÊU CHÍ TỪ DATABASE (Nếu có):
{rubric_context}

## YÊU CẦU ĐẦU RA:
Trả về **DUY NHẤT** một JSON object với cấu trúc sau:

{{
    "score": <điểm từ 0.0-10.0, làm tròn 1 số thập phân>,
    "breakdown": {{
        "correctness": <điểm 0-4.0>,
        "algorithm": <điểm 0-3.0>,
        "code_quality": <điểm 0-2.0>,
        "optimization": <điểm 0-1.0>
    }},
    "strengths": [
        "<điểm mạnh 1>",
        "<điểm mạnh 2>",
        "..."
    ],
    "weaknesses": [
        "<điểm yếu 1>",
        "<điểm yếu 2>",
        "..."
    ],
    "feedback": "<Nhận xét tổng quan bằng Tiếng Việt, 3-5 câu, chuyên nghiệp và khích lệ>",
    "suggestions": [
        "<Gợi ý cải thiện cụ thể 1>",
        "<Gợi ý cải thiện cụ thể 2>",
        "..."
    ],
    "ai_advice": "<Lời khuyên chi tiết từ AI, 2-3 đoạn, bao gồm: phân tích thuật toán, gợi ý tối ưu, best practices>",
    "optimized_code": "<Mã nguồn đã được tối ưu (nếu cần), giữ nguyên logic nhưng cải thiện hiệu năng/style. Nếu code đã tốt thì để nguyên>"
}}

## LƯU Ý QUAN TRỌNG:
1. **Score phải trong [0.0, 10.0]**, có thể dùng 1 số thập phân
2. **Breakdown phải cộng lại đúng bằng score**
3. **Strengths/Weaknesses**: Mỗi mục 1 câu ngắn gọn, cụ thể
4. **Feedback**: Nhận xét tổng quan, khách quan, chuyên nghiệp
5. **Suggestions**: Hành động cụ thể có thể làm ngay
6. **AI Advice**: Phân tích sâu về thuật toán, complexity, best practices
7. **Optimized Code**: Chỉ đưa ra nếu code gốc có thể cải thiện đáng kể
8. **Toàn bộ nội dung bằng Tiếng Việt** (trừ code và technical terms)
9. **JSON phải hợp lệ 100%**, không thêm text ngoài JSON
10. **Nếu không có đủ thông tin để chấm tiêu chí nào, ghi 0 và giải thích trong feedback**

## VÍ DỤ ĐẦU RA MONG ĐỢI:
{{
    "score": 8.5,
    "breakdown": {{
        "correctness": 3.5,
        "algorithm": 2.5,
        "code_quality": 1.5,
        "optimization": 1.0
    }},
    "strengths": [
        "Thuật toán đúng và chạy qua tất cả test cases",
        "Sử dụng đúng cấu trúc dữ liệu cho bài toán",
        "Code có comment giải thích logic phức tạp"
    ],
    "weaknesses": [
        "Độ phức tạp thời gian chưa tối ưu (O(n²) thay vì O(n log n))",
        "Một số biến đặt tên chưa rõ nghĩa",
        "Thiếu xử lý edge cases"
    ],
    "feedback": "Bài làm thể hiện tư duy thuật toán tốt, code chạy đúng yêu cầu. Tuy nhiên còn một số điểm có thể cải thiện về hiệu năng và chất lượng code.",
    "suggestions": [
        "Thay thế bubble sort bằng merge sort để giảm complexity từ O(n²) xuống O(n log n)",
        "Đặt tên biến mô tả hơn (ví dụ: 'arr' → 'numbers_list')",
        "Thêm try-except để xử lý input không hợp lệ"
    ],
    "ai_advice": "Về mặt thuật toán, bài làm đã chọn đúng hướng tiếp cận. Tuy nhiên, với dataset lớn hơn, độ phức tạp O(n²) sẽ gây bottleneck. Nên nghiên cứu các thuật toán sorting efficient hơn. Về code quality, nên áp dụng SOLID principles và viết unit tests để đảm bảo độ tin cậy.",
    "optimized_code": "# Code đã tối ưu..."
}}

**BẮT ĐẦU CHẤM ĐIỂM - TRẢ VỀ JSON:**
"""

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------
    async def grade_with_ai(
        self,
        code: str,
        filename: str,
        topic: str,
        ast_report: Dict[str, Any],
        rubric_context: Optional[Dict[str, Any]] = None,
    ) -> GradingResult:
        """Grade code using the AI provider with retry logic and quota management."""
        logger.info("AI grading: %s (topic: %s)", filename, topic)

        if self._ai is None:
            logger.warning("AI provider is not configured. Falling back to AST for %s", filename)
            return self._fallback(filename, code, "Gemini API chưa được cấu hình hoặc không khởi tạo được")

        # Check daily quota limit
        if not self._check_quota():
            logger.warning("Quota exceeded for %s. Falling back to AST grading.", filename)
            return self._fallback(filename, code, "Đã vượt quá giới hạn API ngày hôm nay. Hệ thống chuyển sang chấm AST.")

        # Check cache first (doesn't count against quota)
        cache_key = f"{filename}:{topic}:{hash(code)}"
        if cache_key in self._response_cache:
            cached_time, cached_result = self._response_cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                logger.debug("Using cached AI grading result for %s", filename)
                return cached_result

        # Smart truncation: Keep imports (head) and main execution (tail)
        processed_code = code
        if len(code) > _MAX_CODE_LENGTH:
            keep_len = _MAX_CODE_LENGTH // 2
            head = code[:keep_len]
            tail = code[-keep_len:]
            processed_code = f"{head}\n\n# ... [CODE TRUNCATED BY SYSTEM DUE TO LENGTH] ...\n\n{tail}"
            logger.warning("Code truncated for AI: %s", filename)

        try:
            # Execute with retry logic
            prompt = self._prompt.format(
                topic=topic,
                filename=filename,
                code=processed_code,
                ast_report=self._format_ast(ast_report),
                rubric_context=self._format_rubric_context(rubric_context),
            )
            response = await self._execute_with_retry(self._ai.generate_json, prompt)
            
            if "error" in response:
                raise ValueError(f"AI Provider Error: {response['error']}")

            # Record successful usage
            self._record_usage()

            result = self._parse(response, filename)

            # Cache result
            self._response_cache[cache_key] = (time.time(), result)

            # Clean old cache entries
            self._clean_cache()

            return result

        except Exception as exc:
            logger.error("AI grading failed after retries: %s", exc, exc_info=True)
            return self._fallback(filename, code, str(exc))

    def _clean_cache(self) -> None:
        """Removes expired entries from the response cache based on TTL."""
        now = time.time()
        expired_keys = [
            key for key, (timestamp, _) in self._response_cache.items()
            if now - timestamp > self._cache_ttl
        ]
        for key in expired_keys:
            del self._response_cache[key]

    @staticmethod
    def _format_rubric_context(rubric_context: Optional[Dict[str, Any]]) -> str:
        """Render rubric criteria from DB for AI prompt guidance."""
        if not rubric_context:
            return "Không có tiêu chí từ cơ sở dữ liệu. Hãy chấm theo chuẩn DSA thông thường."

        source = rubric_context.get("source", "database")
        criteria = rubric_context.get("criteria", []) or []
        if not criteria:
            return "Không có tiêu chí hợp lệ từ cơ sở dữ liệu. Hãy chấm theo chuẩn DSA thông thường."

        lines = [f"Nguồn tiêu chí: {source}", "Danh sách tiêu chí bắt buộc:"]
        for idx, item in enumerate(criteria[:25], start=1):
            name = (item.get("name") or item.get("criteria_name") or "Tiêu chí").strip()
            max_score = item.get("max_score", 0)
            description = (item.get("description") or "").strip()
            lines.append(f"{idx}. {name} (max: {max_score})")
            if description:
                lines.append(f"   - Mô tả: {description}")

        lines.append(
            "Yêu cầu: Cho điểm và nhận xét phải bám sát các tiêu chí trên, không tự thêm tiêu chí ngoài danh sách."
        )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    #  Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_score_10(raw_score: Any) -> float:
        """Normalize score to 0-10 scale (supports accidental 0-100 responses)."""
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            return 0.0

        if score > 10.0:
            score = score / 10.0

        return round(max(0.0, min(score, 10.0)), 1)

    @staticmethod
    def _format_ast(report: Dict[str, Any]) -> str:
        """Format an AST report into readable text for the AI prompt."""
        lines = ["## AST Analysis Results"]

        breakdown = report.get("score_breakdown", {})
        if breakdown:
            lines.append("\n### Score Breakdown")
            lines.extend(f"- {k}: {v}" for k, v in breakdown.items())

        algos = report.get("algorithms", [])
        if algos:
            lines.append("\n### Algorithms Detected")
            lines.extend(f"- {a}" for a in algos)

        complexity = report.get("complexity", {})
        if complexity:
            lines.append("\n### Complexity")
            lines.append(f"- Time: {complexity.get('time', 'N/A')}")
            lines.append(f"- Space: {complexity.get('space', 'N/A')}")

        return "\n".join(lines)

    @staticmethod
    def _parse(response: Dict[str, Any], filename: str) -> GradingResult:
        """Parse the AI response dict into a ``GradingResult``."""
        # 1. Mandatory Fields
        score = AIGradingService._normalize_score_10(response.get("score", 0.0))
        status = response.get("status", "WA")
        
        algorithms = response.get("algorithms_detected", [])
        if isinstance(algorithms, str):
            algorithms = [algorithms]
        elif not isinstance(algorithms, list):
            algorithms = []
        
        # Mapping for the new requested format
        analysis = str(response.get("analysis", "Không có phân tích bổ sung."))
        feedback_suggestions = str(response.get("feedback_suggestions", "Không có gợi ý cụ thể."))

        # 2. Detail lists
        strengths = response.get("strengths", [])
        if isinstance(strengths, str): strengths = [strengths]
        elif not isinstance(strengths, list): strengths = []
            
        weaknesses = response.get("weaknesses", [])
        if isinstance(weaknesses, str): weaknesses = [weaknesses]
        elif not isinstance(weaknesses, list): weaknesses = []

        optimized_code = response.get("optimized_code")

        # 3. Build Combined Feedback for UI
        parts = []
        if analysis:
            parts.extend(["\n### [ANALYSIS] PHÂN TÍCH CHẤM ĐIỂM", analysis])
        if feedback_suggestions:
            parts.extend(["\n### [HINT] GỢI Ý CẢI THIỆN", feedback_suggestions])
        
        if strengths:
            parts.append("\n[STRENGTHS]")
            parts.extend(f"- {s}" for s in strengths)
        if weaknesses:
            parts.append("\n[ISSUES_FOUND]")
            parts.extend(f"- {w}" for w in weaknesses)

        # 4. Return GradingResult Object
        return GradingResult(
            filename=filename,
            total_score=score,
            status=status,
            algorithms_detected=algorithms,
            feedback="\n".join(parts),
            time_used=0.0,
            memory_used=0.0,
            plagiarism_detected=False,
            strengths="\n".join(f"- {s}" for s in strengths) if strengths else None,
            weaknesses="\n".join(f"- {w}" for w in weaknesses) if weaknesses else None,
            improvement=feedback_suggestions,
            reasoning=analysis,
            optimized_code=optimized_code,
        )

    @staticmethod
    def _fallback(filename: str, code: str, error_reason: Optional[str] = None) -> GradingResult:
        """Simple heuristic result when AI is unavailable."""
        line_count = max(1, len(code.split("\n")))
        score = min(7.5, round(4.0 + line_count * 0.08, 1))
        reason_suffix = f" Chi tiết: {error_reason}." if error_reason else ""
        return GradingResult(
            filename=filename,
            total_score=score,
            status="AC",
            algorithms_detected=["basic"],
            feedback="AI grading currently unavailable (Fallback to AST).",
            time_used=0.0,
            memory_used=0.0,
            plagiarism_detected=False,
            reasoning="[WARNING] Gemini AI đang tạm gián đoạn hoặc phản hồi chậm. Hệ thống đã chuyển sang bộ chấm AST để không gián đoạn kết quả." + reason_suffix,
            improvement="[HINT] Vui lòng kiểm tra GEMINI_API_KEY, hạn mức/quota Gemini và thử nộp lại sau vài giây.",
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get AI service statistics."""
        return {
            "circuit_breaker_state": self._circuit_breaker.state,
            "circuit_breaker_failures": self._circuit_breaker.failures,
            "cache_size": len(self._response_cache),
            "max_retries": MAX_RETRIES,
        }
