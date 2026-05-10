import os
from dotenv import load_dotenv

load_dotenv()


def get_required_key(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' is not set. Check your .env file.")
    return value


def get_optional_key(key: str, default=None):
    return os.getenv(key, default)


# ── App ────────────────────────────────────────────────────
ENVIRONMENT = get_optional_key("ENVIRONMENT", "production")  # safe default

# ── LLM Providers ──────────────────────────────────────────
GROQ_API_KEYS = get_required_key("GROQ_API_KEYS")
GEMINI_API_KEYS = get_required_key("GEMINI_API_KEYS")
CEREBRAS_API_KEY = get_optional_key("CEREBRAS_API_KEY")
OPENROUTER_API_KEY = get_optional_key("OPENROUTER_API_KEY")
NVIDIA_NIM_API_KEY = get_optional_key("NVIDIA_NIM_API_KEY")

# ── Search & Scraping ──────────────────────────────────────
TAVILY_API_KEY_DEEP = get_required_key("TAVILY_API_KEY_DEEP")
TAVILY_API_KEY_GENERAL = get_required_key("TAVILY_API_KEY_GENERAL")

# ── Storage ────────────────────────────────────────────────
UPSTASH_REDIS_REST_URL = get_required_key("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = get_required_key("UPSTASH_REDIS_REST_TOKEN")

# ── Scheduling & Webhooks ──────────────────────────────────
QSTASH_TOKEN = get_optional_key("QSTASH_TOKEN")
QSTASH_SIGNING_KEY = get_optional_key("QSTASH_SIGNING_KEY")
DISCORD_WEBHOOK_URL = get_optional_key("DISCORD_WEBHOOK_URL")
RESEND_API_KEY = get_optional_key("RESEND_API_KEY")

# ── Security ───────────────────────────────────────────────
_hmac_default = "dev-secret-change-in-prod" if ENVIRONMENT != "production" else None
HMAC_SECRET = get_optional_key("HMAC_SECRET", _hmac_default)
if ENVIRONMENT == "production" and not HMAC_SECRET:
    raise ValueError("HMAC_SECRET must be set in production. Generate with: python3 -c \"import secrets; print(secrets.token_hex(32))\"")

# ── CORS ───────────────────────────────────────────────────
# Comma-separated list of allowed origins, e.g. "https://roast.dev,https://www.roast.dev"
_origins_env = get_optional_key("ALLOWED_ORIGINS", "")
if _origins_env == "*":
    ALLOWED_ORIGINS = ["*"]
elif _origins_env:
    ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]
elif ENVIRONMENT == "production":
    raise ValueError("ALLOWED_ORIGINS must be set in production. e.g. https://roast.dev,https://www.roast.dev")
else:
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

# ── Observability ──────────────────────────────────────────
LANGFUSE_PUBLIC_KEY = get_required_key("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = get_required_key("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = get_optional_key("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

# ── Resume Validation Limits ───────────────────────────────
MAX_FILE_SIZE_MB = 5
MAX_PAGES = 3
MIN_CHARS = 200
MAX_CHARS = 15_000
