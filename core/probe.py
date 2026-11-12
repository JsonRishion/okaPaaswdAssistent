COLLECT_JS = r"""
(() => {
  const inputs = Array.from(document.querySelectorAll('input[type=password]'));
  const attrsOf = (el) => {
    const out = {};
    ['name','id','minlength','maxlength','pattern','title','placeholder',
     'autocomplete','aria-label','aria-describedby','required'].forEach((a) => {
      const v = el.getAttribute(a);
      if (v !== null) out[a] = v;
    });
    return out;
  };
  const textOf = (el) => {
    const parts = [];
    const label = el.closest('label');
    if (label) parts.push(label.innerText);
    const aria = el.getAttribute('aria-describedby');
    if (aria) aria.split(/\s+/).forEach((id) => {
      const node = document.getElementById(id);
      if (node) parts.push(node.innerText);
    });
    let node = el.parentElement;
    let hops = 0;
    while (node && hops < 4) {
      parts.push(node.innerText || '');
      node = node.parentElement;
      hops += 1;
    }
    return parts.join(' ').replace(/\s+/g, ' ').trim().slice(0, 1200);
  };
  return JSON.stringify({
    url: location.href,
    title: document.title,
    fields: inputs.map((el) => ({ attrs: attrsOf(el), text: textOf(el) })),
  });
})()
"""


def build_context(payload):
    if not payload:
        return "", {}
    fields = payload.get("fields") or []
    if not fields:
        return "", {}
    field = fields[0]
    text = field.get("text") or ""
    attrs = field.get("attrs") or {}
    parts = [text]
    for key, value in attrs.items():
        parts.append("{}={}".format(key, value))
    return " ".join(p for p in parts if p).strip(), attrs
