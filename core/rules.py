import re
from dataclasses import asdict, dataclass

DEFAULT_SYMBOLS = "!@#$%^&*()-_=+"


@dataclass
class PasswordRules:
    min_length: int = 8
    max_length: int = 64
    require_upper: bool = False
    require_lower: bool = False
    require_digit: bool = False
    require_symbol: bool = False
    allowed_symbols: str = DEFAULT_SYMBOLS
    forbidden_chars: str = ""
    allow_spaces: bool = False
    regex: str = ""
    notes: str = ""
    source: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        allowed = set(cls().__dict__.keys())
        clean = {}
        for key, value in (data or {}).items():
            if key in allowed and value is not None:
                clean[key] = value
        return cls(**clean)


def _int_or_none(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def from_attributes(attrs):
    out = {}
    attrs = attrs or {}
    low = _int_or_none(attrs.get("minlength"))
    if low is not None:
        out["min_length"] = low
    high = _int_or_none(attrs.get("maxlength"))
    if high is not None:
        out["max_length"] = high
    pattern = attrs.get("pattern")
    if pattern:
        out["regex"] = pattern
    title = attrs.get("title")
    if title:
        out["notes"] = str(title)
    return out


def parse_hints(text):
    content = (text or "").lower()
    out = {}
    if not content:
        return out

    rng = re.search(r"(\d{1,3})\s*(?:-|~|to|至|到)\s*(\d{1,3})", content)
    if rng:
        out["min_length"] = int(rng.group(1))
        out["max_length"] = int(rng.group(2))
    else:
        low = re.search(
            r"(?:at least|minimum of|min\b|至少|最少|不低于)\s*(\d{1,3})", content
        ) or re.search(r"(\d{1,3})\s*(?:位|characters|chars|个字符)", content)
        if low:
            out["min_length"] = int(low.group(1))
        high = re.search(
            r"(?:at most|maximum of|max\b|最多|不超过|至多)\s*(\d{1,3})", content
        )
        if high:
            out["max_length"] = int(high.group(1))

    if re.search(r"upper|uppercase|capital|大写", content):
        out["require_upper"] = True
    if re.search(r"lower|lowercase|小写", content):
        out["require_lower"] = True
    if re.search(r"letter|alphabetic|字母", content):
        if "require_lower" not in out and "require_upper" not in out:
            out["require_lower"] = True
    if re.search(r"digit|number|numeric|数字", content):
        out["require_digit"] = True
    if re.search(r"special|symbol|punctuation|特殊字符|特殊符号|符号", content):
        out["require_symbol"] = True
    if re.search(r"no spaces|without spaces|不含空格|不能有空格|不得包含空格|无空格", content):
        out["allow_spaces"] = False

    forbidden = re.search(
        r"(?:cannot contain|must not contain|forbidden|禁止|不能包含|不得包含)\s*[：:]?\s*([^\s。.;；]{1,24})",
        content,
    )
    if forbidden:
        out["forbidden_chars"] = forbidden.group(1)
    return out


def infer_from_field(field):
    field = field or {}
    attrs = field.get("attrs") or {}
    text = field.get("text") or ""
    data = parse_hints(text)
    data.update(from_attributes(attrs))
    return PasswordRules.from_dict(data)


def infer_from_payload(payload):
    fields = (payload or {}).get("fields") or []
    if not fields:
        return PasswordRules()
    text = " ".join((field.get("text") or "") for field in fields)
    data = parse_hints(text)
    best_attrs = {}
    for field in fields:
        attrs = field.get("attrs") or {}
        if len(attrs) > len(best_attrs):
            best_attrs = attrs
    data.update(from_attributes(best_attrs))
    rules = PasswordRules.from_dict(data)
    rules.source = "heuristic"
    return rules
