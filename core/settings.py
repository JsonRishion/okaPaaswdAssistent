import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import FCC_BASE_URL, MODEL
from .i18n import DEFAULT_LANGUAGE

SETTINGS_PATH = Path.home() / ".oka" / "config.json"
DEFAULT_SAVE_DIR = str(Path.home() / "oka passwd" / "password-idea")
BUILTIN_NAME = "Free Claude Code"


@dataclass
class BackendConfig:
    kind: str = "fcc"
    name: str = BUILTIN_NAME
    base_url: str = FCC_BASE_URL
    model: str = MODEL
    api_key: str = ""


@dataclass
class AppSettings:
    backend: BackendConfig = field(default_factory=BackendConfig)
    auto_save: bool = True
    save_dir: str = DEFAULT_SAVE_DIR
    language: str = DEFAULT_LANGUAGE


def load_settings(path=None):
    target = Path(path) if path else SETTINGS_PATH
    if not target.exists():
        return AppSettings()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppSettings()
    backend = data.get("backend") or {}
    return AppSettings(
        backend=BackendConfig(
            kind=backend.get("kind", "fcc"),
            name=backend.get("name", BUILTIN_NAME),
            base_url=backend.get("base_url", FCC_BASE_URL),
            model=backend.get("model", MODEL),
            api_key=backend.get("api_key", ""),
        ),
        auto_save=bool(data.get("auto_save", True)),
        save_dir=data.get("save_dir", DEFAULT_SAVE_DIR),
        language=data.get("language", DEFAULT_LANGUAGE),
    )


def save_settings(settings, path=None):
    target = Path(path) if path else SETTINGS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "backend": asdict(settings.backend),
        "auto_save": settings.auto_save,
        "save_dir": settings.save_dir,
        "language": settings.language,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)
