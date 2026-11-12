import random
import re
import secrets
import string

from .rules import DEFAULT_SYMBOLS, PasswordRules


def _target_length(rules, length):
    low = max(1, int(rules.min_length or 1))
    high = max(low, int(rules.max_length or max(low, 64)))
    if length is None:
        length = min(high, max(low, 16))
    return max(low, min(high, int(length)))


def generate_password(rules, length=None):
    rules = rules or PasswordRules()
    size = _target_length(rules, length)
    forbidden = set(rules.forbidden_chars or "")

    def allowed(chars):
        return "".join(ch for ch in chars if ch not in forbidden)

    classes = []
    if rules.require_lower:
        classes.append(string.ascii_lowercase)
    if rules.require_upper:
        classes.append(string.ascii_uppercase)
    if rules.require_digit:
        classes.append(string.digits)
    if rules.require_symbol:
        classes.append(rules.allowed_symbols or DEFAULT_SYMBOLS)

    required = []
    pools = []
    for group in classes:
        pool = allowed(group)
        if pool:
            required.append(secrets.choice(pool))
            pools.append(pool)

    base = "".join(pools) if pools else allowed(string.ascii_letters + string.digits)
    if rules.allow_spaces:
        base += " "
    if not base:
        base = string.ascii_letters + string.digits

    pattern = None
    if rules.regex:
        try:
            pattern = re.compile(rules.regex)
        except re.error:
            pattern = None

    rng = random.SystemRandom()
    for _ in range(3000):
        if size < len(required):
            chars = list(required[:size])
        else:
            chars = list(required)
            while len(chars) < size:
                chars.append(secrets.choice(base))
        rng.shuffle(chars)
        candidate = "".join(chars)
        if forbidden and (forbidden & set(candidate)):
            continue
        if not rules.allow_spaces and " " in candidate:
            continue
        if pattern is not None and not pattern.search(candidate):
            continue
        return candidate

    fallback = "".join(required)
    while len(fallback) < size:
        fallback += secrets.choice(base)
    return fallback[:size]
