#!/usr/bin/env python3
"""Static WCAG 2.2 A/AA pattern scanner for CyberPanel Django templates."""
import os, re, sys, json, collections

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/claude/cyberpanel"

checks = collections.defaultdict(list)  # check_id -> [(file, line, snippet)]

IMG_RE = re.compile(r"<img\b[^>]*>", re.I | re.S)
INPUT_RE = re.compile(r"<input\b[^>]*>", re.I | re.S)
SELECT_RE = re.compile(r"<select\b[^>]*>", re.I | re.S)
TEXTAREA_RE = re.compile(r"<textarea\b[^>]*>", re.I | re.S)
BTN_DIV_RE = re.compile(r"<(div|span|a|i|td|li)\b[^>]*\bng-click\s*=", re.I)
ONCLICK_DIV_RE = re.compile(r"<(div|span|i|td|li)\b[^>]*\bonclick\s*=", re.I)
IFRAME_RE = re.compile(r"<iframe\b[^>]*>", re.I | re.S)
TABLE_RE = re.compile(r"<table\b[^>]*>", re.I)
AHASH_RE = re.compile(r"<a\b[^>]*href=[\"']#[\"'][^>]*>", re.I)
TABINDEX_POS_RE = re.compile(r"tabindex\s*=\s*[\"']([1-9]\d*)[\"']", re.I)
AUTOFOCUS_RE = re.compile(r"\bautofocus\b", re.I)
VIEWPORT_RE = re.compile(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1", re.I)
MARQUEE_RE = re.compile(r"<(marquee|blink)\b", re.I)
TITLE_ONLY_ICON_BTN = re.compile(r"<button\b(?![^>]*aria-label)[^>]*>\s*<i\b[^>]*>\s*</i>\s*</button>", re.I | re.S)

def line_of(text, pos):
    return text.count("\n", 0, pos) + 1

def has_attr(tag, attr):
    return re.search(r"\b" + attr + r"\s*=", tag, re.I) is not None

def strip_django(text):
    # remove django comments
    return text

nfiles = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "test", "tests"}]
    for fn in filenames:
        if not fn.endswith(".html"):
            continue
        path = os.path.join(dirpath, fn)
        if "/templates/" not in path:
            continue
        rel = os.path.relpath(path, ROOT)
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        nfiles += 1

        for m in IMG_RE.finditer(text):
            tag = m.group(0)
            if not has_attr(tag, "alt"):
                checks["img-no-alt (1.1.1)"].append((rel, line_of(text, m.start()), tag[:100]))
            elif re.search(r"alt\s*=\s*[\"']\.\.+[\"']", tag):
                checks["img-alt-dots (1.1.1)"].append((rel, line_of(text, m.start()), tag[:100]))

        for m in INPUT_RE.finditer(text):
            tag = m.group(0)
            typ = re.search(r"type\s*=\s*[\"']?(\w+)", tag, re.I)
            typ = typ.group(1).lower() if typ else "text"
            if typ in ("hidden", "submit", "button", "checkbox", "radio"):
                continue
            if not (has_attr(tag, "aria-label") or has_attr(tag, "aria-labelledby") or has_attr(tag, "id")):
                if has_attr(tag, "placeholder"):
                    checks["input-placeholder-only-no-id (1.3.1/3.3.2)"].append((rel, line_of(text, m.start()), tag[:120]))
                else:
                    checks["input-no-label-no-id (1.3.1/4.1.2)"].append((rel, line_of(text, m.start()), tag[:120]))
            elif has_attr(tag, "id"):
                idm = re.search(r"\bid\s*=\s*[\"']([^\"']+)[\"']", tag)
                if idm and not re.search(r"for\s*=\s*[\"']" + re.escape(idm.group(1)) + r"[\"']", text) \
                   and not (has_attr(tag, "aria-label") or has_attr(tag, "aria-labelledby")):
                    checks["input-id-but-no-label-for (1.3.1/3.3.2)"].append((rel, line_of(text, m.start()), tag[:120]))

        for m in SELECT_RE.finditer(text):
            tag = m.group(0)
            if not (has_attr(tag, "aria-label") or has_attr(tag, "aria-labelledby")):
                idm = re.search(r"\bid\s*=\s*[\"']([^\"']+)[\"']", tag)
                if not (idm and re.search(r"for\s*=\s*[\"']" + re.escape(idm.group(1)) + r"[\"']", text)):
                    checks["select-no-label (1.3.1/4.1.2)"].append((rel, line_of(text, m.start()), tag[:120]))

        for m in BTN_DIV_RE.finditer(text):
            tag_full = text[m.start():text.find(">", m.start())+1]
            el = m.group(1).lower()
            if el == "a" and re.search(r"href\s*=\s*[\"'](?!#)[^\"']+[\"']", tag_full):
                continue  # real link with href
            if "role=" in tag_full or "tabindex" in tag_full:
                continue
            checks[f"clickable-{el}-not-focusable (2.1.1)"].append((rel, line_of(text, m.start()), tag_full[:120]))

        for m in ONCLICK_DIV_RE.finditer(text):
            tag_full = text[m.start():text.find(">", m.start())+1]
            if "role=" in tag_full or "tabindex" in tag_full:
                continue
            checks[f"clickable-{m.group(1).lower()}-onclick-not-focusable (2.1.1)"].append((rel, line_of(text, m.start()), tag_full[:120]))

        for m in IFRAME_RE.finditer(text):
            if not has_attr(m.group(0), "title"):
                checks["iframe-no-title (4.1.2)"].append((rel, line_of(text, m.start()), m.group(0)[:100]))

        for m in TABINDEX_POS_RE.finditer(text):
            checks["tabindex-positive (2.4.3)"].append((rel, line_of(text, m.start()), m.group(0)))

        for m in VIEWPORT_RE.finditer(text):
            checks["viewport-zoom-block (1.4.4)"].append((rel, line_of(text, m.start()), m.group(0)))

        for m in MARQUEE_RE.finditer(text):
            checks["marquee-blink (2.2.2)"].append((rel, line_of(text, m.start()), m.group(0)))

        for m in TITLE_ONLY_ICON_BTN.finditer(text):
            checks["icon-button-no-accname (4.1.2)"].append((rel, line_of(text, m.start()), m.group(0)[:100].replace("\n"," ")))

        # tables without th
        for m in TABLE_RE.finditer(text):
            seg = text[m.start():m.start()+3000]
            if "<th" not in seg and "</table>" in seg:
                checks["table-no-th (1.3.1)"].append((rel, line_of(text, m.start()), m.group(0)[:80]))

        # modals: bootstrap modal divs without role=dialog
        for m in re.finditer(r"<div\b[^>]*class\s*=\s*[\"'](?:[^\"']*\s)?modal(?:\s[^\"']*)?[\"'][^>]*>", text, re.I):
            tag = m.group(0)
            if "role=" not in tag:
                checks["modal-no-role-dialog (4.1.2)"].append((rel, line_of(text, m.start()), tag[:110]))

summary = sorted(((k, len(v)) for k, v in checks.items()), key=lambda x: -x[1])
print(f"Scanned {nfiles} template files under {ROOT}\n")
print(f"{'CHECK':58} COUNT  FILES")
for k, c in summary:
    files = len(set(f for f, _, _ in checks[k]))
    print(f"{k:58} {c:5}  {files}")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "a11y_findings.json"), "w") as fh:
    json.dump({k: v for k, v in checks.items()}, fh, indent=1)
print("\nDetail written to a11y_findings.json")
