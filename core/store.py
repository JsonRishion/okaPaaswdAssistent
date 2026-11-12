import datetime
import json
import re
from pathlib import Path

from .config import PASSWORD_IDEA_DIR

_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def domain_from_url(url):
    match = re.match(r"^\s*[a-zA-Z][a-zA-Z0-9+.-]*://([^/?#]+)", url or "")
    host = match.group(1) if match else (url or "unknown")
    host = host.split("@")[-1].split(":")[0]
    return host or "unknown"


def safe_name(text):
    return _BAD_CHARS.sub("_", text or "").strip(" .") or "unknown"


def save_password(url, password, rules, username="", directory=None):
    target = Path(directory) if directory else PASSWORD_IDEA_DIR
    target.mkdir(parents=True, exist_ok=True)

    domain = domain_from_url(url)
    now = datetime.datetime.now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    path = target / "{}_{}.txt".format(safe_name(domain), stamp)

    payload = rules.to_dict() if hasattr(rules, "to_dict") else (rules or {})
    lines = [
        "URL: {}".format(url),
        "域名: {}".format(domain),
        "时间: {}".format(now.isoformat(timespec="seconds")),
        "用户名: {}".format(username),
        "密码: {}".format(password),
        "规则: {}".format(json.dumps(payload, ensure_ascii=False)),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)
