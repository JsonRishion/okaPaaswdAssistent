import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PASSWORD_IDEA_DIR = PROJECT_ROOT / "password-idea"

FCC_BASE_URL = os.environ.get("OKA_FCC_URL", "http://127.0.0.1:8082/v1")
MODEL = os.environ.get("OKA_MODEL", "nvidia_nim/z-ai/glm-5.3-flash")
BUILTIN_MODELS = [
    "nvidia_nim/z-ai/glm-5.3-flash",
    "nvidia_nim/deepseek-ai/deepseek-v4.1-flash",
]
DEFAULT_TIMEOUT = 120
DEFAULT_RETRIES = 1
