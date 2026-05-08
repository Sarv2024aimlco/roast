import os 
from dotenv import load_dotenv

load_dotenv()

def get_required_key(key:str):
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Required environment variable {key} is not set.Check your .env file")
    return value

def get_optional_key(key:str,default=None):
    value = os.getenv(key)
    if value is None:
        return default
    return value
# ── LLM Providers ──────────────────────────────────────────
# Comma-separated for key rotation — e.g. "key1,key2,key3"
GROQ_API_KEYS = get_required_key("GROQ_API_KEYS")
GEMINI_API_KEYS = get_required_key("GEMINI_API_KEYS")
CEREBRAS_API_KEY = get_optional_key("CEREBRAS_API_KEY")
OPENROUTER_API_KEY = get_optional_key("OPENROUTER_API_KEY")

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
HMAC_SECRET = get_optional_key("HMAC_SECRET", "dev-secret-change-in-prod")

# ── Observability ──────────────────────────────────────────

LANGFUSE_PUBLIC_KEY = get_required_key("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = get_required_key("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = get_optional_key("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

# ── App ────────────────────────────────────────────────────

ENVIRONMENT = get_optional_key("ENVIRONMENT", "development")
# ── Resume Validation Limits ───────────────────────────────
MAX_FILE_SIZE_MB = 5
MAX_PAGES = 3
MIN_CHARS = 200
MAX_CHARS = 15_000