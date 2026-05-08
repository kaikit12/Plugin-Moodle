import asyncio
import logging
import time
from typing import Any, Dict
import google.generativeai as genai
from app.core.models import AIResponse

logger = logging.getLogger("dsa.ai.gemini")


class GeminiProvider:
    """
    Google Gemini AI provider.

    Implements IAIProvider for Gemini API.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self._api_key = api_key
        self._model_name = model_name
        self._client = None
        self._model = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Gemini client."""
        try:
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(self._model_name)
            logger.info("Gemini provider initialized with model: %s", self._model_name)
        except Exception as e:
            logger.error("Failed to initialize Gemini: %s", e)
            raise

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """
        Generate text from prompt using Gemini.

        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            AIResponse with generated content
        """
        start_time = time.time()

        try:
            # Configure generation parameters
            temperature = kwargs.get("temperature", 0.1)
            max_tokens = kwargs.get("max_tokens", 4096)

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    ),
                ),
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract text from response
            content = response.text if hasattr(response, "text") else str(response)

            # Usage info (if available)
            usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

            logger.debug(
                "Gemini generated %d chars in %.0fms", len(content), latency_ms
            )

            return AIResponse(
                content=content,
                model=self._model_name,
                usage=usage,
                latency_ms=latency_ms,
                success=True,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("Gemini generation failed: %s", e)

            return AIResponse(
                content="",
                model=self._model_name,
                usage={},
                latency_ms=latency_ms,
                success=False,
                error_message=str(e),
            )

    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate structured JSON response.

        Args:
            prompt: Input prompt
            **kwargs: Additional parameters

        Returns:
            Parsed JSON as dictionary
        """
        import json

        # Add instruction for JSON output
        json_prompt = f"""{prompt}

Respond ONLY with valid JSON. No markdown, no explanations, just the JSON object.
"""

        response = await self.generate(json_prompt, **kwargs)

        if not response.success:
            return {"error": response.error_message}

        # Parse JSON from response
        try:
            # Try to extract JSON from response (handle markdown code blocks)
            content = response.content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])  # Remove first and last line

            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from Gemini response: %s", e)
            return {"error": "Invalid JSON response", "raw": response.content}

    async def health_check(self) -> bool:
        """
        Check if Gemini API is available.

        Returns:
            True if API is healthy
        """
        try:
            # Simple test - list models
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: genai.list_models())
            return True
        except Exception as e:
            logger.error("Gemini health check failed: %s", e)
            return False
