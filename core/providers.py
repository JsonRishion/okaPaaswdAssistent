import urllib.request
from pathlib import Path

from .config import FCC_BASE_URL

BACKEND_CANDIDATES = [
    ("fcc", "Free Claude Code", FCC_BASE_URL, "/models"),
    ("ollama", "Ollama", "http://127.0.0.1:11434/v1", "/models"),
    ("lmstudio", "LM Studio", "http://127.0.0.1:1234/v1", "/models"),
    ("llamacpp", "llama.cpp", "http://127.0.0.1:8080/v1", "/models"),
]

ASSISTANT_CANDIDATES = [
    ("opencode", "~/.config/opencode"),
    ("claude-code", "~/.claude"),
    ("codex", "~/.codex"),
    ("aider", "~/.aider.conf.yml"),
]


def _reachable(base_url, probe, timeout=3):
    url = base_url.rstrip("/") + probe
    try:
        request = urllib.request.Request(url)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def detect_backends(timeout=3):
    found = []
    for kind, name, base, probe in BACKEND_CANDIDATES:
        if _reachable(base, probe, timeout):
            found.append({"kind": kind, "name": name, "base_url": base})
    return found


def detect_assistants():
    found = []
    for name, raw_path in ASSISTANT_CANDIDATES:
        path = Path(raw_path).expanduser()
        if path.exists():
            found.append({"name": name, "path": str(path)})
    return found
