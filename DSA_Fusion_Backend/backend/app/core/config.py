import logging
import os
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("dsa.config")


# ═══════════════════════════════════════════
#  Helper Functions
# ═══════════════════════════════════════════


def get_required_env(var_name: str) -> str:
    """
    Get environment variable - REQUIRED.
    Raises error if not set.
    """
    value = os.getenv(var_name)
    if value is None or value.strip() == "":
        error_msg = (
            f"\n{'='*60}\n"
            f"ERROR: {var_name} is not set!\n"
            f"{'='*60}\n"
            f"Please set {var_name} in your .env file.\n"
            f"\n"
            f"Steps:\n"
            f"1. Copy .env.example to .env (if not exists)\n"
            f"2. Edit .env and set {var_name}\n"
            f"3. Restart the server\n"
            f"\n"
            f"For GEMINI_API_KEY:\n"
            f"  - Get your key from: https://makersuite.google.com/app/apikey\n"
            f"  - Paste it in .env: GEMINI_API_KEY=your_key_here\n"
            f"{'='*60}\n"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    return value.strip()


def get_optional_env(var_name: str, default: str = "") -> str:
    """Get environment variable with default value (optional)."""
    return os.getenv(var_name, default).strip()


def get_bool_env(var_name: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    value = os.getenv(var_name, str(default)).lower()
    return value in ("true", "1", "yes", "on")


def get_int_env(var_name: str, default: int = 0) -> int:
    """Get integer environment variable."""
    try:
        return int(os.getenv(var_name, str(default)))
    except ValueError:
        return default


def get_float_env(var_name: str, default: float = 0.0) -> float:
    """Get float environment variable."""
    try:
        return float(os.getenv(var_name, str(default)))
    except ValueError:
        return default


# ═══════════════════════════════════════════
#  Application Info
# ═══════════════════════════════════════════
ENVIRONMENT: str = get_optional_env("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT.lower() == "production"
IS_DEVELOPMENT = ENVIRONMENT.lower() == "development"
IS_TESTING = ENVIRONMENT.lower() == "testing"


# ═══════════════════════════════════════════
#  API Keys & External Services
# ═══════════════════════════════════════════
# For DEVELOPMENT: API keys are optional (AI grading will use fallback)
# For PRODUCTION: API keys MUST be set in .env file
# DO NOT hardcode them anywhere in the codebase!

GEMINI_API_KEY: str = get_optional_env("GEMINI_API_KEY", "")

MY_SECRET_KEY: str = get_optional_env("MY_SECRET_KEY", "")

# External service URLs (optional - have defaults)
QUESTION_BANK_API_URL: str = get_optional_env(
    "QUESTION_BANK_API_URL",
    "https://api-dsa-python.onrender.com",
)
RUBRIC_API_URL: str = get_optional_env(
    "RUBRIC_API_URL",
    "https://api-dsa-python.onrender.com/api/rubrics",
)

# Database (optional)
SQL_SERVER_URL: str = get_optional_env("SQL_SERVER_URL", "")
REDIS_URL: str = get_optional_env("REDIS_URL", "")


# ═══════════════════════════════════════════
#  AI Model Settings (Optional)
# ═══════════════════════════════════════════
AI_PROVIDER: str = get_optional_env("AI_PROVIDER", "gemini").lower()
AI_MODEL_NAME: str = get_optional_env("AI_MODEL_NAME", "gemini-2.0-flash-exp")
AI_MODEL_TEMPERATURE: float = get_float_env("AI_MODEL_TEMPERATURE", 0.1)
AI_QUOTA_PER_DAY: int = int(os.getenv("AI_QUOTA_PER_DAY", "15"))  # Free tier limit protection
AI_MAX_OUTPUT_TOKENS: int = get_int_env("AI_MAX_OUTPUT_TOKENS", 8192)


# ═══════════════════════════════════════════
#  Paths
# ═══════════════════════════════════════════
# config.py nằm tại  app/core/config.py  →  đi lên 3 cấp = project root
BASE_DIR: str = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
DATA_DIR: str = os.path.join(BASE_DIR, "data")
TESTCASE_ROOT: str = os.path.join(DATA_DIR, "testcases")
LOGS_DIR: str = os.path.join(BASE_DIR, "logs")


# ═══════════════════════════════════════════
#  Grading Thresholds (Optional)
# ═══════════════════════════════════════════
PLAGIARISM_THRESHOLD: float = get_float_env("PLAGIARISM_THRESHOLD", 0.85)
PASS_SCORE_THRESHOLD: int = get_int_env("PASS_SCORE_THRESHOLD", 50)
MAX_CONCURRENT_AI_CALLS: int = get_int_env("MAX_CONCURRENT_AI_CALLS", 5)


# ═══════════════════════════════════════════
#  Application Constants (Optional)
# ═══════════════════════════════════════════
MAX_HISTORY_ROWS: int = get_int_env("MAX_HISTORY_ROWS", 2000)
JOB_TTL_SECONDS: int = get_int_env("JOB_TTL_SECONDS", 3600)
DYNAMIC_TEST_TIMEOUT: int = get_int_env("DYNAMIC_TEST_TIMEOUT", 5)


# ═══════════════════════════════════════════
#  Database (SQLite - Optional)
# ═══════════════════════════════════════════
DB_NAME: str = get_optional_env("DB_NAME", "database.db")
DB_FILE: str = os.path.join(DATA_DIR, DB_NAME)


# ═══════════════════════════════════════════
#  Server Configuration (Optional)
# ═══════════════════════════════════════════
PORT: int = get_int_env("PORT", 8000)
AUTO_RELOAD: bool = get_bool_env("AUTO_RELOAD", True)


# ═══════════════════════════════════════════
#  Security & Rate Limiting (Optional)
# ═══════════════════════════════════════════
RATE_LIMIT_ENABLED: bool = get_bool_env("RATE_LIMIT_ENABLED", True)
RATE_LIMIT_PER_MINUTE: int = get_int_env("RATE_LIMIT_PER_MINUTE", 60)
RATE_LIMIT_PER_HOUR: int = get_int_env("RATE_LIMIT_PER_HOUR", 1000)

# 🔒 HIGH SECURITY JWT KEY - 64 bytes cryptographic random
# Priority: 1) .env file → 2) This default secure key
JWT_SECRET_KEY: str = get_optional_env(
    "JWT_SECRET_KEY",
    "5a1ToRxZvesagHvWClAySqZ9bp7NHCJJsHK4TWpbEQF34q50-7pDECZOwVjQ7HEqjriZFQuTm6MImhOPgcisMg"
)
CORS_ALLOWED_ORIGINS: str = get_optional_env("CORS_ALLOWED_ORIGINS", "*")


# ═══════════════════════════════════════════
#  Sandbox Security (Optional)
# ═══════════════════════════════════════════
SANDBOX_MAX_MEMORY_MB: int = get_int_env("SANDBOX_MAX_MEMORY_MB", 256)
SANDBOX_MAX_CPU_TIME: int = get_int_env("SANDBOX_MAX_CPU_TIME", 5)
MAX_UPLOAD_SIZE_MB: int = get_int_env("MAX_UPLOAD_SIZE_MB", 10)


# ═══════════════════════════════════════════
#  Logging & Monitoring (Optional)
# ═══════════════════════════════════════════
LOG_LEVEL: str = get_optional_env("LOG_LEVEL", "INFO").upper()
LOG_FORMAT: str = get_optional_env("LOG_FORMAT", "text").lower()
METRICS_ENABLED: bool = get_bool_env("METRICS_ENABLED", True)


# ═══════════════════════════════════════════
#  Webhook Configuration (Optional)
# ═══════════════════════════════════════════
WEBHOOK_MAX_RETRIES: int = get_int_env("WEBHOOK_MAX_RETRIES", 3)
WEBHOOK_RETRY_DELAY: int = get_int_env("WEBHOOK_RETRY_DELAY", 2)


# ═══════════════════════════════════════════
#  Validation
# ═══════════════════════════════════════════
def validate_config() -> bool:
    """
    Validate critical configuration values.
    Returns True if all checks pass, False otherwise.
    """
    errors = []
    warnings = []

    # Critical errors (only in production)
    if IS_PRODUCTION:
        if AI_PROVIDER == "gemini" and not GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is required in production but not set!")

        if not MY_SECRET_KEY:
            errors.append("MY_SECRET_KEY is required in production but not set!")
    else:
        # Development warnings
        if AI_PROVIDER == "gemini" and not GEMINI_API_KEY:
            warnings.append("GEMINI_API_KEY not set - AI grading will use fallback heuristic")

        if not MY_SECRET_KEY:
            warnings.append("MY_SECRET_KEY not set - External API calls will not work")

    # Production warnings
    if IS_PRODUCTION:
        if not JWT_SECRET_KEY:
            errors.append("JWT_SECRET_KEY is required in production but not set!")

        if len(JWT_SECRET_KEY) < 32:
            errors.append("JWT_SECRET_KEY should be at least 32 characters!")

        if CORS_ALLOWED_ORIGINS == "*":
            warnings.append(
                "CORS_ALLOWED_ORIGINS is set to '*' in production. Consider restricting to specific domains!"
            )

    # Redis URL validation
    if REDIS_URL and not REDIS_URL.startswith("redis://"):
        warnings.append(
            "REDIS_URL format may be incorrect (should start with 'redis://')"
        )

    # Log results
    for error in errors:
        logger.error("CONFIGURATION ERROR: %s", error)

    for warning in warnings:
        logger.warning("CONFIGURATION WARNING: %s", warning)

    if errors:
        logger.error(
            f"\n{'='*60}\n"
            f"CONFIGURATION VALIDATION FAILED!\n"
            f"{'='*60}\n"
            f"Please fix the errors above in your .env file.\n"
            f"{'='*60}\n"
        )
        return False

    if warnings and IS_PRODUCTION:
        logger.warning(
            f"\n{'='*60}\n"
            f"CONFIGURATION WARNINGS (Production)\n"
            f"{'='*60}\n"
            f"Please review the warnings above.\n"
            f"{'='*60}\n"
        )

    return True


# ═══════════════════════════════════════════
#  Startup Check
# ═══════════════════════════════════════════
def check_and_log_config():
    """
    Check configuration and log startup info.
    Called during application startup.
    """
    logger.info("=" * 50)
    logger.info("DSA AutoGrader Configuration")
    logger.info("=" * 50)
    logger.info("Environment: %s", ENVIRONMENT)
    logger.info("Production: %s", IS_PRODUCTION)
    logger.info("Port: %s", PORT)
    logger.info("Rate Limiting: %s", "Enabled" if RATE_LIMIT_ENABLED else "Disabled")
    logger.info("Metrics: %s", "Enabled" if METRICS_ENABLED else "Disabled")
    logger.info("AI Model: %s", AI_MODEL_NAME)
    logger.info("Database: %s", "SQL Server" if SQL_SERVER_URL else "SQLite")
    logger.info("Redis: %s", "Enabled" if REDIS_URL else "Disabled (in-memory)")
    logger.info("=" * 50)

    # Validate configuration
    if not validate_config():
        logger.error("Configuration validation failed! Exiting...")
        sys.exit(1)

    # Log API key status (not the key itself!)
    if GEMINI_API_KEY:
        key_preview = GEMINI_API_KEY[:10] + "..." if len(GEMINI_API_KEY) > 10 else "***"
        logger.info("GEMINI_API_KEY: Set (%s)", key_preview)
    else:
        if IS_PRODUCTION:
            logger.error("GEMINI_API_KEY: NOT SET - AI grading will not work!")
        else:
            logger.info(
                "GEMINI_API_KEY: Not set (using fallback heuristic for development)"
            )

    if MY_SECRET_KEY:
        key_preview = MY_SECRET_KEY[:10] + "..." if len(MY_SECRET_KEY) > 10 else "***"
        logger.info("MY_SECRET_KEY: Set (%s)", key_preview)
    else:
        if IS_PRODUCTION:
            logger.error("MY_SECRET_KEY: NOT SET - External API calls will not work!")
        else:
            logger.info("MY_SECRET_KEY: Not set (development mode)")

    logger.info("=" * 50)
