import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from typing import Dict, Generator, List, Optional, Tuple

from sqlalchemy import create_engine, desc, func, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import DB_FILE
from app.utils.security import calculate_jaccard_similarity
from app.models.models import Base, User, GradingHistory, RunResult, Rubric, ManualGrade

import logging
logger = logging.getLogger("dsa.repository")

class GradingRepository:
    def __init__(self, sql_server_url: str = None, sqlite_file: str = None):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
        self._is_sql_server = bool(sql_server_url)

        if sql_server_url:
            self._init_sql_server(sql_server_url)
        else:
            self._init_sqlite(sqlite_file or DB_FILE)

    def _init_sqlite(self, db_file: str):
        try:
            self.engine = create_engine(
                f"sqlite:///{db_file}",
                connect_args={"check_same_thread": False},
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False,
            )
            self.SessionLocal = sessionmaker(bind=self.engine)
            self._create_tables()
            self._initialized = True
            logger.info("SQLite database initialized: %s", db_file)
        except Exception as e:
            logger.error("SQLite init failed: %s", e)
            raise

    def _init_sql_server(self, conn_str: str):
        try:
            # SQLAlchemy expects DSN-less ODBC strings through odbc_connect.
            # Passing raw semicolon connection strings directly can fail with IM002.
            encoded_conn = quote_plus(conn_str)
            self.engine = create_engine(
                f"mssql+pyodbc:///?odbc_connect={encoded_conn}",
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                echo=False,
            )
            self.SessionLocal = sessionmaker(bind=self.engine)
            self._create_tables()
            self._initialized = True
            logger.info("SQL Server database initialized")
        except Exception as e:
            logger.error("SQL Server init failed: %s", e)
            self._init_sqlite(DB_FILE)

    def _create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        self._add_missing_columns()

    def _add_missing_columns(self):
        # Migration logic
        try:
            with self.get_session() as session:
                session.execute("ALTER TABLE grading_history ADD COLUMN is_manual_grade BOOLEAN DEFAULT 0")
        except Exception: pass
        try:
            with self.get_session() as session:
                session.execute("ALTER TABLE grading_history ADD COLUMN rubric_file_path VARCHAR(500)")
        except Exception: pass

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_result(self, result: Dict) -> int:
        try:
            with self.get_session() as session:
                record = GradingHistory(
                    job_id=result.get("job_id", ""),
                    student_id=result.get("student_id", ""),
                    student_name=result.get("student_name", ""),
                    assignment_code=result.get("assignment_code", ""),
                    filename=result.get("filename", ""),
                    topic=result.get("topic", ""),
                    total_score=result.get("total_score", 0),
                    algorithms=",".join(result.get("algorithms_detected", [])),
                    status=result.get("status", "AC"),
                    feedback=json.dumps(result.get("feedback", "")),
                    fingerprint=result.get("fingerprint", ""),
                    plagiarism_detected=result.get("plagiarism_detected", False),
                    plagiarism_matches=json.dumps(result.get("plagiarism_matches", [])),
                    code=result.get("code"),
                    language=result.get("language", "python"),
                    needs_review=result.get("needs_review", False),
                )
                session.add(record)
                session.flush()
                test_results = result.get("test_results", [])
                if test_results:
                    self._save_test_results_internal(record.id, test_results, session)
                return record.id
        except Exception as e:
            logger.error("Save result failed: %s", e)
            raise

    def _save_test_results_internal(self, grading_history_id: int, test_results: List[Dict], session: Session):
        for tc_result in test_results:
            run_result = RunResult(
                grading_history_id=grading_history_id,
                testcase_id=tc_result.get("testcase_id", ""),
                stdout=tc_result.get("actual_output", ""),
                stderr=tc_result.get("error", ""),
                time_ms=tc_result.get("time_ms", 0),
                mem_kb=tc_result.get("memory_kb", 0),
                passed=tc_result.get("passed", False),
                error_message=tc_result.get("error", "") if not tc_result.get("passed") else "",
            )
            session.add(run_result)

    def get_stats(self, assignment_code: Optional[str] = None) -> Dict:
        try:
            with self.get_session() as session:
                query = session.query(
                    func.count(GradingHistory.id).label('total'),
                    func.avg(GradingHistory.total_score).label('avg'),
                    func.max(GradingHistory.total_score).label('max'),
                    func.min(GradingHistory.total_score).label('min'),
                )
                if assignment_code:
                    query = query.filter(GradingHistory.assignment_code == assignment_code)
                result = query.first()
                if not result or result.total == 0:
                    return {"total_submissions": 0, "avg_score": 0, "max_score": 0, "min_score": 0}
                return {
                    "total_submissions": result.total or 0,
                    "avg_score": round(result.avg, 2) if result.avg else 0,
                    "max_score": result.max or 0,
                    "min_score": result.min or 0,
                }
        except Exception as e:
            logger.error("Get stats failed: %s", e)
            return {"total_submissions": 0, "avg_score": 0, "max_score": 0, "min_score": 0}

    def get_summary_stats(self) -> Dict:
        try:
            with self.get_session() as session:
                stats = session.query(
                    func.count(GradingHistory.id).label('total'),
                    func.avg(func.coalesce(GradingHistory.final_score, GradingHistory.total_score)).label('avg'),
                    func.max(func.coalesce(GradingHistory.final_score, GradingHistory.total_score)).label('max'),
                    func.min(func.coalesce(GradingHistory.final_score, GradingHistory.total_score)).label('min')
                ).first()
                total_students = session.query(func.count(func.distinct(GradingHistory.student_id))).scalar()
                thirty_days_ago = datetime.now() - timedelta(days=30)
                active_students = session.query(func.count(func.distinct(GradingHistory.student_id))).filter(
                    GradingHistory.submitted_at >= thirty_days_ago
                ).scalar()
                plag_count = session.query(func.count(GradingHistory.id)).filter(
                    GradingHistory.plagiarism_detected == True
                ).scalar()
                distribution = {
                    "0-2": session.query(func.count(GradingHistory.id)).filter(func.coalesce(GradingHistory.final_score, GradingHistory.total_score) < 2).scalar(),
                    "2-4": session.query(func.count(GradingHistory.id)).filter(func.coalesce(GradingHistory.final_score, GradingHistory.total_score) >= 2, func.coalesce(GradingHistory.final_score, GradingHistory.total_score) < 4).scalar(),
                    "4-6": session.query(func.count(GradingHistory.id)).filter(func.coalesce(GradingHistory.final_score, GradingHistory.total_score) >= 4, func.coalesce(GradingHistory.final_score, GradingHistory.total_score) < 6).scalar(),
                    "6-8": session.query(func.count(GradingHistory.id)).filter(func.coalesce(GradingHistory.final_score, GradingHistory.total_score) >= 6, func.coalesce(GradingHistory.final_score, GradingHistory.total_score) < 8).scalar(),
                    "8-10": session.query(func.count(GradingHistory.id)).filter(func.coalesce(GradingHistory.final_score, GradingHistory.total_score) >= 8).scalar(),
                }
                recent = session.query(GradingHistory).order_by(desc(GradingHistory.submitted_at)).limit(10).all()
                activity = [{"student_name": r.student_name, "action": f"Nộp bài {r.topic}", "timestamp": r.submitted_at.isoformat()} for r in recent]
                return {
                    "total_submissions": stats.total or 0,
                    "total_students": total_students or 0,
                    "active_students": active_students or 0,
                    "avg_score": round(stats.avg, 1) if stats.avg else 0.0,
                    "max_score": stats.max or 0.0,
                    "min_score": stats.min or 0.0,
                    "pass_rate": round((session.query(func.count(GradingHistory.id)).filter(func.coalesce(GradingHistory.final_score, GradingHistory.total_score) >= 5.0).scalar() or 0) / (stats.total or 1) * 100, 1),
                    "plagiarism_count": plag_count or 0,
                    "score_distribution": distribution,
                    "recent_activity": activity
                }
        except Exception as e:
            logger.error("Get summary stats failed: %s", e)
            return {"total_submissions": 0, "error": str(e)}

    def get_result_by_id(self, result_id: int) -> Optional[Dict]:
        try:
            with self.get_session() as session:
                record = session.query(GradingHistory).filter(GradingHistory.id == result_id).first()
                return record.to_dict() if record else None
        except Exception as e:
            logger.error("Get result by ID failed: %s", e)
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.username == username).first()
                if not user: return None
                return {
                    "id": user.id, 
                    "username": user.username, 
                    "email": user.email,
                    "password_hash": user.password_hash, 
                    "full_name": user.full_name, 
                    "role": user.role
                }
        except Exception as e:
            logger.error("Get user failed: %s", e)
            return None

    def create_user(self, username: str, password_hash: str, full_name: str, role: str = "LECTURER", email: str = None):
        try:
            with self.get_session() as session:
                # Generate email from username if not provided
                user_email = email or f"{username}@dsa.local"
                user = User(username=username, password_hash=password_hash, full_name=full_name, role=role, email=user_email)
                session.add(user)
                session.flush()
                return user.id
        except Exception as e:
            logger.error("Create user failed: %s", e)
            return None

    def get_all_submissions(self, page: int = 1, page_size: int = 50,
                           student_id: Optional[str] = None,
                           assignment_code: Optional[str] = None,
                           topic: Optional[str] = None,
                           status: Optional[str] = None) -> Dict:
        try:
            with self.get_session() as session:
                # Don't load 'code' column for performance
                db_query = session.query(
                    GradingHistory.id,
                    GradingHistory.job_id,
                    GradingHistory.student_id,
                    GradingHistory.student_name,
                    GradingHistory.assignment_code,
                    GradingHistory.filename,
                    GradingHistory.topic,
                    GradingHistory.total_score,
                    GradingHistory.algorithms,
                    GradingHistory.status,
                    GradingHistory.feedback,
                    GradingHistory.fingerprint,
                    GradingHistory.plagiarism_detected,
                    GradingHistory.plagiarism_matches,
                    GradingHistory.submitted_at,
                    GradingHistory.language,
                    GradingHistory.final_score,
                    GradingHistory.needs_review,
                    GradingHistory.reviewer_id,
                    GradingHistory.is_manual_grade,
                    GradingHistory.rubric_file_path
                )
                if student_id: db_query = db_query.filter(GradingHistory.student_id == student_id)
                if assignment_code: db_query = db_query.filter(GradingHistory.assignment_code == assignment_code)
                if topic and topic != "all": db_query = db_query.filter(GradingHistory.topic == topic)
                if status and status != "all": db_query = db_query.filter(GradingHistory.status == status)
                total = db_query.count()
                offset = (page - 1) * page_size
                records = db_query.order_by(desc(GradingHistory.submitted_at)).offset(offset).limit(page_size).all()

                # Convert to dict manually
                submissions = []
                for r in records:
                    submissions.append({
                        "id": r.id,
                        "job_id": r.job_id,
                        "student_id": r.student_id,
                        "student_name": r.student_name,
                        "assignment_code": r.assignment_code,
                        "filename": r.filename,
                        "topic": r.topic,
                        "total_score": float(r.total_score) if r.total_score is not None else 0.0,
                        "algorithms": r.algorithms,
                        "status": r.status,
                        "feedback": r.feedback,
                        "fingerprint": r.fingerprint,
                        "plagiarism_detected": bool(r.plagiarism_detected) if r.plagiarism_detected is not None else False,
                        "plagiarism_matches": r.plagiarism_matches,
                        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                        "language": r.language,
                        "final_score": float(r.final_score) if r.final_score is not None else 0.0,
                        "needs_review": bool(r.needs_review) if r.needs_review is not None else False,
                        "reviewer_id": r.reviewer_id,
                        "is_manual_grade": bool(r.is_manual_grade) if r.is_manual_grade is not None else False,
                        "rubric_file_path": r.rubric_file_path
                    })

                return {
                    "submissions": submissions,
                    "total": total, "page": page, "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
                }
        except Exception as e:
            logger.error("Get all submissions failed: %s", e)
            return {"submissions": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    def delete_submission(self, submission_id: int) -> bool:
        try:
            with self.get_session() as session:
                record = session.query(GradingHistory).filter(GradingHistory.id == submission_id).first()
                if record:
                    session.delete(record)
                    return True
                return False
        except Exception as e:
            logger.error("Delete submission failed: %s", e)
            return False
            
    def get_recent_submissions(self, student_name: str, minutes: int = 5) -> int:
        try:
            with self.get_session() as session:
                cutoff = datetime.now() - timedelta(minutes=minutes)
                count = session.query(GradingHistory).filter(GradingHistory.student_name == student_name, GradingHistory.submitted_at >= cutoff).count()
                return count
        except Exception as e:
            logger.error("Get recent submissions failed: %s", e)
            return 0

    def get_assignment_scores(self, assignment_code: str, page: int = 1, page_size: int = 50) -> Dict:
        try:
            with self.get_session() as session:
                total = session.query(func.count(GradingHistory.id)).filter(GradingHistory.assignment_code == assignment_code).scalar()
                offset = (page - 1) * page_size
                query = session.query(GradingHistory).filter(GradingHistory.assignment_code == assignment_code).order_by(desc(GradingHistory.submitted_at)).offset(offset).limit(page_size)
                scores = [record.to_dict() for record in query.all()]
                return {"assignment_code": assignment_code, "submissions": scores, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}
        except Exception as e:
            logger.error("Get assignment scores failed: %s", e)
            return {"assignment_code": assignment_code, "submissions": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    def save_batch_results(self, results: List[Dict], assignment_code: Optional[str] = None) -> List[int]:
        saved_ids = []
        try:
            with self.get_session() as session:
                for result in results:
                    if assignment_code:
                        result["assignment_code"] = assignment_code
                    try:
                        record = GradingHistory(
                            job_id=result.get("job_id", ""),
                            student_id=result.get("student_id", ""),
                            student_name=result.get("student_name", ""),
                            assignment_code=result.get("assignment_code", ""),
                            filename=result.get("filename", ""),
                            topic=result.get("topic", ""),
                            total_score=result.get("total_score", 0),
                            algorithms=",".join(result.get("algorithms_detected", [])),
                            status=result.get("status", "AC"),
                            feedback=json.dumps(result.get("feedback", "")),
                            fingerprint=result.get("fingerprint", ""),
                            plagiarism_detected=result.get("plagiarism_detected", False),
                            plagiarism_matches=json.dumps(result.get("plagiarism_matches", [])),
                            code=result.get("code"),
                            language=result.get("language", "python"),
                            needs_review=result.get("needs_review", False),
                        )
                        session.add(record)
                        session.flush()
                        saved_ids.append(record.id)
                        test_results = result.get("test_results", [])
                        if test_results:
                            self._save_test_results_internal(record.id, test_results, session)
                    except Exception as e:
                        logger.error("Failed to save individual result: %s", e)
                        continue
                return saved_ids
        except Exception as e:
            logger.error("Batch save failed: %s", e)
            return []

    def update_submission_score(self, submission_id: int, new_score: float, reviewer_id: str, reason: str, feedback: str = "") -> bool:
        try:
            with self.get_session() as session:
                record = session.query(GradingHistory).filter(GradingHistory.id == submission_id).first()
                if not record: return False
                record.final_score = new_score
                record.reviewer_id = reviewer_id
                record.needs_review = False
                if feedback:
                    try:
                        f_list = json.loads(record.feedback) if record.feedback else []
                        if isinstance(f_list, list):
                            f_list.append(f"Instructor Note: {feedback}")
                            record.feedback = json.dumps(f_list)
                    except:
                        record.feedback = json.dumps([f"Instructor Note: {feedback}"])
                return True
        except Exception as e:
            logger.error("Update score failed: %s", e)
            return False

    def save_runs(self, history_id: int, runs_data: List[Dict]):
        try:
            with self.get_session() as session:
                for run_data in runs_data:
                    run = RunResult(
                        grading_history_id=history_id,
                        testcase_id=run_data.get("testcase_id"),
                        stdout=run_data.get("stdout", ""),
                        stderr=run_data.get("stderr", ""),
                        time_ms=run_data.get("time_ms", 0.0),
                        mem_kb=run_data.get("mem_kb", 0.0),
                        passed=run_data.get("passed", False),
                        error_message=run_data.get("error_message", "")
                    )
                    session.add(run)
        except Exception as e:
            logger.error("Failed to save runs: %s", e)

    def get_test_results_by_submission(self, submission_id: int) -> List[Dict]:
        try:
            with self.get_session() as session:
                runs = session.query(RunResult).filter(RunResult.grading_history_id == submission_id).order_by(RunResult.id).all()
                return [{
                    "id": r.id, "testcase_id": r.testcase_id, "actual_output": r.stdout,
                    "error": r.stderr, "time_ms": r.time_ms, "memory_kb": r.mem_kb,
                    "passed": r.passed, "error_message": r.error_message,
                    "error_type": self._classify_error(r.stderr, r.passed)
                } for r in runs]
        except Exception as e:
            logger.error("Get test results failed: %s", e)
            return []

    def _classify_error(self, stderr: str, passed: bool) -> str:
        if passed: return "passed"
        if not stderr: return "wrong_answer"
        if "Time Limit" in stderr: return "timeout"
        if "Traceback" in stderr or "Error" in stderr: return "runtime_error"
        return "wrong_answer"

    def get_runs_by_submission(self, submission_id: int) -> List[Dict]:
        try:
            with self.get_session() as session:
                runs = session.query(RunResult).filter(RunResult.grading_history_id == submission_id).all()
                return [{
                    "id": r.id, "testcase_id": r.testcase_id, "stdout": r.stdout,
                    "stderr": r.stderr, "time_ms": r.time_ms, "mem_kb": r.mem_kb,
                    "passed": r.passed, "error_message": r.error_message
                } for r in runs]
        except Exception as e:
            logger.error("Get runs failed: %s", e)
            return []

    def get_student_scores(self, student_id: str, page: int = 1, page_size: int = 20) -> Dict:
        try:
            with self.get_session() as session:
                total = session.query(func.count(GradingHistory.id)).filter(GradingHistory.student_id == student_id).scalar()
                offset = (page - 1) * page_size
                query = session.query(GradingHistory).filter(GradingHistory.student_id == student_id).order_by(desc(GradingHistory.submitted_at)).offset(offset).limit(page_size)
                scores = [record.to_dict() for record in query.all()]
                return {"student_id": student_id, "submissions": scores, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}
        except Exception as e:
            logger.error("Get student scores failed: %s", e)
            return {"student_id": student_id, "submissions": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    def find_similar_submissions(self, fingerprint: str, threshold: float = 0.8, topic: str = None) -> List[Dict]:
        """
        Optimized similar submission search.
        Filters by topic and date range to avoid loading the entire database.
        """
        try:
            with self.get_session() as session:
                # 1. Filter by 90 days AND topic (if available)
                cutoff = datetime.now() - timedelta(days=90)
                query = session.query(GradingHistory).filter(
                    GradingHistory.submitted_at >= cutoff,
                    GradingHistory.fingerprint.isnot(None),
                    GradingHistory.fingerprint != ""
                )
                
                # Major optimization: only compare against same topic if topic is known
                if topic and topic != "none":
                    query = query.filter(GradingHistory.topic == topic)
                
                # Limit to 500 recent records for comparison to protect memory
                records = query.order_by(desc(GradingHistory.submitted_at)).limit(500).all()
                
                matches = []
                target_set = set(fingerprint.split("|")) if "|" in fingerprint else {fingerprint}
                
                for r in records:
                    source_set = set(r.fingerprint.split("|")) if "|" in r.fingerprint else {r.fingerprint}
                    similarity = calculate_jaccard_similarity(target_set, source_set)
                    
                    if similarity >= threshold:
                        matches.append({
                            "id": r.id, 
                            "student_name": r.student_name, 
                            "assignment_code": r.assignment_code, 
                            "similarity": similarity, 
                            "created_at": r.submitted_at.isoformat() if r.submitted_at else ""
                        })
                
                matches.sort(key=lambda x: x["similarity"], reverse=True)
                return matches[:10]
        except Exception as e:
            logger.error("Find similar submissions failed: %s", e)
            return []

    def create_rubric(self, assignment_code: str, topic: str, criteria_name: str, max_score: float, description: str, file_path: str, created_by: str) -> int:
        try:
            with self.get_session() as session:
                rubric = Rubric(assignment_code=assignment_code, topic=topic, criteria_name=criteria_name, max_score=max_score, description=description, file_path=file_path, created_by=created_by)
                session.add(rubric)
                session.flush()
                return rubric.id
        except Exception as e:
            logger.error("Create rubric failed: %s", e)
            return None

    def get_rubrics_by_assignment(self, assignment_code: str) -> List[Dict]:
        try:
            with self.get_session() as session:
                rubrics = session.query(Rubric).filter(Rubric.assignment_code == assignment_code).order_by(Rubric.created_at.desc()).all()
                return [{
                    "id": r.id, "assignment_code": r.assignment_code, "topic": r.topic,
                    "criteria_name": r.criteria_name, "max_score": r.max_score,
                    "description": r.description, "file_path": r.file_path,
                    "created_by": r.created_by, "created_at": r.created_at.isoformat() if r.created_at else None
                } for r in rubrics]
        except Exception as e:
            logger.error("Get rubrics failed: %s", e)
            return []

    def delete_rubric(self, rubric_id: int) -> bool:
        try:
            with self.get_session() as session:
                rubric = session.query(Rubric).filter(Rubric.id == rubric_id).first()
                if rubric:
                    session.delete(rubric)
                    return True
                return False
        except Exception as e:
            logger.error("Delete rubric failed: %s", e)
            return False

    def create_manual_grade(self, grading_history_id: int, student_id: str,
                           assignment_code: str, rubric_id: int, criteria_scores: Dict,
                           total_score: float, feedback: str, graded_by: str,
                           rubric_file_path: str = None) -> int:
        try:
            with self.get_session() as session:
                manual_grade = ManualGrade(
                    grading_history_id=grading_history_id,
                    student_id=student_id,
                    assignment_code=assignment_code,
                    rubric_id=rubric_id,
                    criteria_scores=json.dumps(criteria_scores),
                    total_score=total_score,
                    feedback=feedback,
                    graded_by=graded_by,
                    rubric_file_path=rubric_file_path
                )
                session.add(manual_grade)
                session.flush()
                history = session.query(GradingHistory).filter(GradingHistory.id == grading_history_id).first()
                if history:
                    history.final_score = total_score
                    history.is_manual_grade = True
                    history.reviewer_id = graded_by
                return manual_grade.id
        except Exception as e:
            logger.error("Create manual grade failed: %s", e)
            return None

    def get_manual_grades(self, student_id: str = None, assignment_code: str = None) -> List[Dict]:
        try:
            with self.get_session() as session:
                query = session.query(ManualGrade)
                if student_id: query = query.filter(ManualGrade.student_id == student_id)
                if assignment_code: query = query.filter(ManualGrade.assignment_code == assignment_code)
                grades = query.order_by(ManualGrade.graded_at.desc()).all()
                return [{
                    "id": g.id, "grading_history_id": g.grading_history_id, "student_id": g.student_id,
                    "assignment_code": g.assignment_code, "rubric_id": g.rubric_id,
                    "criteria_scores": json.loads(g.criteria_scores) if g.criteria_scores else {},
                    "total_score": g.total_score, "feedback": g.feedback, "graded_by": g.graded_by,
                    "graded_at": g.graded_at.isoformat() if g.graded_at else None
                } for g in grades]
        except Exception as e:
            logger.error("Get manual grades failed: %s", e)
            return []

    def cleanup_old_submissions(self, days: int = 90) -> int:
        try:
            with self.get_session() as session:
                cutoff = datetime.now() - timedelta(days=days)
                count = session.query(GradingHistory).filter(GradingHistory.submitted_at < cutoff).delete()
                return count
        except Exception as e:
            logger.error("Cleanup failed: %s", e)
            return 0

    def initialize(self):
        pass

    def close(self):
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed.")

    def get_baitap_criteria(
        self,
        assignment_code: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> List[Dict]:
        """Load grading criteria from SQL Server table dbo.BAITAP.

        The function is resilient to schema differences by discovering columns
        from INFORMATION_SCHEMA and mapping common Vietnamese/English names.
        """
        if not self._is_sql_server:
            return []

        try:
            with self.get_session() as session:
                col_rows = session.execute(
                    text(
                        """
                        SELECT COLUMN_NAME
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'BAITAP'
                        """
                    )
                ).fetchall()

                columns = [str(r[0]) for r in col_rows]
                if not columns:
                    logger.warning("Table dbo.BAITAP not found or has no columns")
                    return []

                col_lookup = {c.lower(): c for c in columns}

                def pick(*candidates: str) -> Optional[str]:
                    for candidate in candidates:
                        found = col_lookup.get(candidate.lower())
                        if found:
                            return found
                    return None

                criteria_col = pick(
                    "criteria_name", "criterion", "tieu_chi", "ten_tieu_chi", "noi_dung", "description"
                )
                description_col = pick(
                    "description", "mo_ta", "ghi_chu", "note", "chi_tiet"
                )
                max_score_col = pick(
                    "max_score", "diem_toi_da", "trong_so", "weight", "score"
                )
                assignment_col = pick(
                    "assignment_code", "ma_bai_tap", "mabaitap", "baitap_code", "code"
                )
                topic_col = pick("topic", "chu_de", "chude", "category", "loai")
                component_col = pick(
                    "component", "criteria_type", "nhom", "nhom_tieu_chi", "criterion_type"
                )

                if not criteria_col:
                    logger.warning("dbo.BAITAP found but no criteria column detected")
                    return []

                select_cols = [criteria_col]
                for col in [description_col, max_score_col, assignment_col, topic_col, component_col]:
                    if col and col not in select_cols:
                        select_cols.append(col)

                select_sql = ", ".join(f"[{c}]" for c in select_cols)
                sql = f"SELECT {select_sql} FROM [dbo].[BAITAP]"

                where_parts = []
                params: Dict[str, str] = {}

                if assignment_code and assignment_col:
                    where_parts.append(f"[{assignment_col}] = :assignment_code")
                    params["assignment_code"] = assignment_code

                if topic and topic_col:
                    where_parts.append(f"[{topic_col}] = :topic")
                    params["topic"] = topic

                if where_parts:
                    sql += " WHERE " + " AND ".join(where_parts)

                rows = session.execute(text(sql), params).mappings().all()

                criteria = []
                for row in rows:
                    raw_name = row.get(criteria_col)
                    name = str(raw_name).strip() if raw_name is not None else ""
                    if not name:
                        continue

                    raw_max = row.get(max_score_col) if max_score_col else 1
                    try:
                        max_score = float(raw_max) if raw_max is not None else 1.0
                    except (TypeError, ValueError):
                        max_score = 1.0

                    if max_score <= 0:
                        continue

                    description = ""
                    if description_col:
                        raw_desc = row.get(description_col)
                        description = str(raw_desc).strip() if raw_desc is not None else ""

                    component = ""
                    if component_col:
                        raw_comp = row.get(component_col)
                        component = str(raw_comp).strip() if raw_comp is not None else ""

                    criteria.append(
                        {
                            "criteria_name": name,
                            "description": description,
                            "max_score": max_score,
                            "component": component,
                        }
                    )

                return criteria
        except Exception as e:
            logger.error("Get BAITAP criteria failed: %s", e)
            return []
