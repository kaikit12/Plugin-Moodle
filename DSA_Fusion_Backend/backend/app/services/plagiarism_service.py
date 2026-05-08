"""
DSA AutoGrader - Enhanced Plagiarism Service.

Features:
- AST fingerprint generation (n-gram)
- Token-based similarity
- Semantic similarity (AI-powered)
- Jaccard similarity
- Multi-level detection
"""

import hashlib
import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.models import GradingResult

logger = logging.getLogger("dsa.services.plagiarism")


class PlagiarismService:
    """
    Enhanced plagiarism detection service.
    
    Features:
    - AST-based fingerprinting
    - Token-based similarity
    - Semantic similarity (optional AI)
    - Multi-level detection (intra-job, cross-job)
    """

    def __init__(self, repository: Any, ai_provider: Any = None):
        self._repository = repository
        self._ai = ai_provider
        self._similarity_threshold = 0.8  # 80% similarity
        self._ngram_size = 5  # Size of n-grams for fingerprinting

    # ------------------------------------------------------------------
    #  Code Normalization & Tokenization
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_code(code: str) -> str:
        """Normalize code for comparison (remove whitespace, comments, etc.)."""
        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
        
        # Remove string literals (replace with placeholder)
        code = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '"STR"', code)
        code = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", "'STR'", code)
        
        # Normalize whitespace
        code = re.sub(r'\s+', ' ', code)
        code = code.strip()
        
        return code

    @staticmethod
    def _tokenize_code(code: str) -> List[str]:
        """Tokenize code into meaningful tokens."""
        # Remove strings and normalize
        normalized = PlagiarismService._normalize_code(code)
        
        # Split into tokens (identifiers, keywords, operators)
        tokens = re.findall(r'\b\w+\b|[+\-*/=<>!&|%^~]+', normalized)
        
        return tokens

    @staticmethod
    def _generate_ngrams(tokens: List[str], n: int = 5) -> Set[str]:
        """Generate n-grams from tokens."""
        if len(tokens) < n:
            return {' '.join(tokens)}
        
        ngrams = set()
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i + n])
            ngrams.add(ngram)
        
        return ngrams

    # ------------------------------------------------------------------
    #  Fingerprint Generation (Enhanced)
    # ------------------------------------------------------------------
    def generate_fingerprint(self, code: str) -> str:
        """
        Generate enhanced code fingerprint.
        
        Uses:
        - Normalized code hash
        - Token n-grams
        - AST structure hash
        
        Args:
            code: Source code
            
        Returns:
            Fingerprint string (pipe-separated components)
        """
        try:
            from app.utils.security import generate_code_fingerprint
            
            # Get base AST fingerprint
            ast_fp = generate_code_fingerprint(code)
            
            # Add token-based fingerprint
            tokens = self._tokenize_code(code)
            token_fp = '|'.join(sorted(set(tokens)))[:500]
            
            # Add normalized code hash
            normalized = self._normalize_code(code)
            code_hash = hashlib.md5(normalized.encode()).hexdigest()[:16]
            
            # Combine fingerprints
            combined = f"{ast_fp}|{token_fp}|{code_hash}"
            return combined[:2000]  # Limit length
            
        except Exception as e:
            logger.error("Fingerprint generation failed: %s", e)
            return hashlib.md5(code.encode()).hexdigest()

    # ------------------------------------------------------------------
    #  Similarity Calculation (Multi-method)
    # ------------------------------------------------------------------
    def calculate_similarity(self, fingerprint1: str, fingerprint2: str) -> float:
        """
        Calculate similarity between fingerprints using Jaccard.
        
        Args:
            fingerprint1: First fingerprint
            fingerprint2: Second fingerprint
            
        Returns:
            Similarity score (0.0 - 1.0)
        """
        try:
            from app.utils.security import calculate_jaccard_similarity
            
            # Parse fingerprints as sets
            set1 = set(fingerprint1.split("|")) if "|" in fingerprint1 else {fingerprint1}
            set2 = set(fingerprint2.split("|")) if "|" in fingerprint2 else {fingerprint2}
            
            return calculate_jaccard_similarity(set1, set2)
        except Exception as e:
            logger.error("Similarity calculation failed: %s", e)
            return 0.0

    def calculate_token_similarity(self, code1: str, code2: str) -> float:
        """
        Calculate token-based similarity between two codes.
        
        Uses cosine similarity on token frequency vectors.
        
        Args:
            code1: First code
            code2: Second code
            
        Returns:
            Similarity score (0.0 - 1.0)
        """
        try:
            tokens1 = self._tokenize_code(code1)
            tokens2 = self._tokenize_code(code2)
            
            # Generate n-grams
            ngrams1 = self._generate_ngrams(tokens1, self._ngram_size)
            ngrams2 = self._generate_ngrams(tokens2, self._ngram_size)
            
            # Calculate Jaccard similarity on n-grams
            intersection = len(ngrams1 & ngrams2)
            union = len(ngrams1 | ngrams2)
            
            if union == 0:
                return 0.0
            
            return intersection / union
        except Exception as e:
            logger.error("Token similarity calculation failed: %s", e)
            return 0.0

    def calculate_structural_similarity(self, code1: str, code2: str) -> float:
        """
        Calculate structural similarity (AST-based).
        
        Compares:
        - Number of functions/classes
        - Control flow structures
        - Variable usage patterns
        
        Args:
            code1: First code
            code2: Second code
            
        Returns:
            Similarity score (0.0 - 1.0)
        """
        try:
            import ast
            
            # Parse ASTs
            tree1 = ast.parse(code1)
            tree2 = ast.parse(code2)
            
            # Extract structural features
            def extract_features(tree: ast.AST) -> Dict[str, int]:
                features = {
                    'functions': 0,
                    'classes': 0,
                    'for_loops': 0,
                    'while_loops': 0,
                    'if_statements': 0,
                    'try_except': 0,
                    'imports': 0,
                    'assignments': 0,
                    'function_calls': 0,
                }
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        features['functions'] += 1
                    elif isinstance(node, ast.ClassDef):
                        features['classes'] += 1
                    elif isinstance(node, ast.For):
                        features['for_loops'] += 1
                    elif isinstance(node, ast.While):
                        features['while_loops'] += 1
                    elif isinstance(node, ast.If):
                        features['if_statements'] += 1
                    elif isinstance(node, ast.Try):
                        features['try_except'] += 1
                    elif isinstance(node, ast.Import):
                        features['imports'] += 1
                    elif isinstance(node, ast.Assign):
                        features['assignments'] += 1
                    elif isinstance(node, ast.Call):
                        features['function_calls'] += 1
                
                return features
            
            features1 = extract_features(tree1)
            features2 = extract_features(tree2)
            
            # Calculate cosine similarity on feature vectors
            values1 = list(features1.values())
            values2 = list(features2.values())
            
            dot_product = sum(a * b for a, b in zip(values1, values2))
            magnitude1 = sum(a * a for a in values1) ** 0.5
            magnitude2 = sum(b * b for b in values2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception as e:
            logger.error("Structural similarity calculation failed: %s", e)
            return 0.0

    def calculate_combined_similarity(
        self,
        code1: str,
        code2: str,
        fingerprint1: Optional[str] = None,
        fingerprint2: Optional[str] = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate combined similarity using multiple methods.
        
        Args:
            code1: First code
            code2: Second code
            fingerprint1: Optional pre-computed fingerprint
            fingerprint2: Optional pre-computed fingerprint
            
        Returns:
            Tuple of (combined_score, breakdown_dict)
        """
        # Get fingerprints if not provided
        if not fingerprint1:
            fingerprint1 = self.generate_fingerprint(code1)
        if not fingerprint2:
            fingerprint2 = self.generate_fingerprint(code2)
        
        # Calculate individual similarities
        fingerprint_sim = self.calculate_similarity(fingerprint1, fingerprint2)
        token_sim = self.calculate_token_similarity(code1, code2)
        structural_sim = self.calculate_structural_similarity(code1, code2)
        
        # Weighted combination
        weights = {
            'fingerprint': 0.4,
            'token': 0.35,
            'structural': 0.25,
        }
        
        combined = (
            weights['fingerprint'] * fingerprint_sim +
            weights['token'] * token_sim +
            weights['structural'] * structural_sim
        )
        
        breakdown = {
            'fingerprint': fingerprint_sim,
            'token': token_sim,
            'structural': structural_sim,
            'combined': combined,
        }
        
        return combined, breakdown

    # ------------------------------------------------------------------
    #  Plagiarism Detection
    # ------------------------------------------------------------------
    async def check_intra_job_plagiarism(
        self, results: List[GradingResult]
    ) -> List[Dict[str, Any]]:
        """
        Check plagiarism within same job (files from same submission).
        
        Compares all files against each other.
        
        Args:
            results: List of grading results
            
        Returns:
            List of plagiarism alerts
        """
        alerts = []
        
        logger.info("Checking intra-job plagiarism for %d files", len(results))
        
        # Compare each pair
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                result1 = results[i]
                result2 = results[j]
                
                # Get fingerprints
                fp1 = getattr(result1, "fingerprint", None)
                fp2 = getattr(result2, "fingerprint", None)
                
                if not fp1 or not fp2:
                    continue
                
                # Calculate combined similarity
                code1 = getattr(result1, "code", "")
                code2 = getattr(result2, "code", "")
                
                if not code1 or not code2:
                    similarity = self.calculate_similarity(fp1, fp2)
                else:
                    similarity, _ = self.calculate_combined_similarity(
                        code1, code2, fp1, fp2
                    )
                
                if similarity > self._similarity_threshold:
                    alert = {
                        "type": "intra_job",
                        "file1": result1.filename,
                        "file2": result2.filename,
                        "similarity": similarity,
                        "message": f"Giống nhau {similarity:.0%} với {result2.filename}",
                    }
                    alerts.append(alert)
                    
                    # Mark results as flagged
                    result1.plagiarism_detected = True
                    result2.plagiarism_detected = True
        
        if alerts:
            logger.warning("Found %d intra-job plagiarism alerts", len(alerts))
        
        return alerts

    async def check_cross_job_plagiarism(
        self, results: List[GradingResult], assignment_code: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Check plagiarism against historical submissions.
        
        Args:
            results: List of grading results
            assignment_code: Assignment identifier
            
        Returns:
            List of plagiarism alerts
        """
        alerts = []
        
        logger.info("Checking cross-job plagiarism for %d files", len(results))
        
        try:
            for result in results:
                # Get fingerprint and code
                fingerprint = getattr(result, "fingerprint", None)
                code = getattr(result, "code", "")
                
                if not fingerprint:
                    continue
                
                # Find similar submissions in database
                similar = self._repository.find_similar_submissions(
                    fingerprint, self._similarity_threshold
                )
                
                if similar:
                    # Enhance with detailed analysis
                    matches = []
                    highest_similarity = 0
                    
                    for submission in similar:
                        # Get historical code for deeper analysis
                        historical_code = submission.get("code", "")
                        
                        if historical_code and code:
                            # Calculate detailed similarity
                            detailed_sim, breakdown = self.calculate_combined_similarity(
                                code, historical_code
                            )
                        else:
                            detailed_sim = submission.get("similarity", 0)
                            breakdown = {}
                        
                        matches.append({
                            "id": submission.get("id"),
                            "student": submission.get("student_name", "Unknown"),
                            "assignment": submission.get(
                                "assignment_code", "Unknown"
                            ),
                            "similarity": detailed_sim,
                            "date": submission.get("created_at", "Unknown"),
                            "breakdown": breakdown,
                        })
                        highest_similarity = max(highest_similarity, detailed_sim)
                    
                    alert = {
                        "type": "cross_job",
                        "filename": result.filename,
                        "matches": matches,
                        "highest_similarity": highest_similarity,
                        "message": f"PHÁT HIỆN ĐẠO VĂN: Giống {len(matches)} bài cũ (cao nhất: {highest_similarity:.0%})",
                    }
                    alerts.append(alert)
                    
                    # Mark result as flagged
                    result.plagiarism_detected = True
                    result.plagiarism_matches = matches
                    
        except Exception as e:
            logger.error("Cross-job plagiarism check failed: %s", e)
        
        return alerts

    async def check_with_ai(
        self, code1: str, code2: str, student1: str, student2: str
    ) -> Dict[str, Any]:
        """
        Use AI for deep semantic plagiarism analysis.
        
        Args:
            code1: First code
            code2: Second code
            student1: First student name
            student2: Second student name
            
        Returns:
            AI analysis result
        """
        if not self._ai:
            return {"error": "AI provider not available"}
        
        # First check basic similarity
        basic_sim = self.calculate_token_similarity(code1, code2)
        structural_sim = self.calculate_structural_similarity(code1, code2)
        
        # Only use AI if basic similarity is high enough
        if basic_sim < 0.5 and structural_sim < 0.5:
            return {
                "similarity_score": basic_sim * 100,
                "is_plagiarism": False,
                "analysis": "Similarity too low for AI analysis",
                "evidence": [],
            }
        
        prompt = f"""
        You are a code plagiarism detection expert. Compare these two Python submissions:

        ### SUBMISSION 1 (Student: {student1})
        ```python
        {code1[:5000]}
        ```

        ### SUBMISSION 2 (Student: {student2})
        ```python
        {code2[:5000]}
        ```

        Analyze the following aspects:
        1. **Logic structure**: Are the problem-solving steps unusually similar?
        2. **Programming style**: Are variable naming, whitespace, and coding habits similar?
        3. **Unnatural similarities**: Identical errors or specific code handling segments.

        Return results in JSON format:
        {{
            "similarity_score": <0-100>,
            "is_plagiarism": <true/false>,
            "analysis": "Detailed analysis in English",
            "evidence": ["Similarity point 1", "Similarity point 2"]
        }}
        """
        try:
            return await self._ai.generate_json(prompt)
        except Exception as e:
            logger.error("AI Plagiarism analysis failed: %s", e)
            return {
                "error": str(e),
                "is_plagiarism": False,
                "similarity_score": basic_sim * 100,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get plagiarism detection statistics."""
        return {
            "similarity_threshold": self._similarity_threshold,
            "ngram_size": self._ngram_size,
            "ai_enabled": self._ai is not None,
        }


__all__ = [
    "PlagiarismService",
]
