import json
import time
import urllib.request

from .config import DEFAULT_RETRIES, DEFAULT_TIMEOUT
from .rules import PasswordRules
from .settings import load_settings

SYSTEM_PROMPT = (
    "你是密码规则分析器。根据给定的网页密码框信息，提取该网站对密码的要求。"
    "只输出一个 JSON 对象，不要任何多余文字。字段："
    "min_length(int), max_length(int), require_upper(bool), require_lower(bool), "
    "require_digit(bool), require_symbol(bool), allowed_symbols(str), "
    "forbidden_chars(str), allow_spaces(bool), regex(str), notes(str)。"
    "无法确定的字段用合理的默认值或留空。"
)


def resolve_backend(settings=None):
    settings = settings or load_settings()
    backend = settings.backend
    return backend.base_url, backend.model, backend.api_key


def _request(url, payload=None, api_key="", method="GET", timeout=DEFAULT_TIMEOUT):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer {}".format(api_key)
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def is_available(timeout=5, settings=None):
    base_url, _, api_key = resolve_backend(settings)
    try:
        _request(base_url.rstrip("/") + "/models", api_key=api_key, timeout=timeout)
        return True
    except Exception:
        return False


def backend_status(timeout=3, settings=None):
    base_url, model, api_key = resolve_backend(settings)
    try:
        _request(base_url.rstrip("/") + "/models", api_key=api_key, timeout=timeout)
        return {"available": True, "base_url": base_url, "model": model, "error": None}
    except Exception as error:
        return {
            "available": False,
            "base_url": base_url,
            "model": model,
            "error": "{}: {}".format(type(error).__name__, error),
        }


def _extract_json(text):
    if not text:
        return None
    chunk = text.strip()
    if chunk.startswith("```"):
        chunk = chunk.strip("`")
    start = chunk.find("{")
    end = chunk.rfind("}")
    if start < 0 or end < 0 or end <= start:
        return None
    try:
        return json.loads(chunk[start : end + 1])
    except json.JSONDecodeError:
        return None


def analyze(context_text, model=None, timeout=DEFAULT_TIMEOUT, retries=DEFAULT_RETRIES, settings=None):
    base_url, default_model, api_key = resolve_backend(settings)
    payload = {
        "model": model or default_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "网页密码框信息如下：\n{}\n\n请输出该网站密码要求的 JSON。".format(
                    (context_text or "").strip()
                ),
            },
        ],
        "temperature": 0,
        "max_tokens": 600,
    }
    url = base_url.rstrip("/") + "/chat/completions"

    last_error = None
    for attempt in range(retries + 1):
        try:
            response = _request(url, payload, api_key=api_key, method="POST", timeout=timeout)
        except Exception as error:
            last_error = error
            if attempt < retries:
                time.sleep(1.0)
                continue
            raise
        choices = response.get("choices") or []
        if not choices:
            return None
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        data = _extract_json(content)
        if not data:
            return None
        rules = PasswordRules.from_dict(data)
        rules.source = "llm"
        return rules
    if last_error:
        raise last_error
    return None
