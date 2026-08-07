#!/usr/bin/env python3
"""Deterministic WCAG 2.2 A/AA bulk fixes for CyberPanel Django templates.

Transforms (all conservative and idempotent):
  T1  Associate visible <label> with the control that follows it (add for=/id=).
  T2  Add aria-label (copied from placeholder) to still-unlabelled controls.
  T3  Add alt="" to <img> tags with no alt (decorative default).
  T4  Add role="dialog" to Bootstrap .modal containers; wire aria-labelledby
      to the .modal-title when one follows closely.
  T5  Re-enable pinch zoom: strip maximum-scale/user-scalable from viewport.
  T6  aria-hidden="true" on Font Awesome / glyphicon <i> icons that sit next
      to visible text (never on icons that are a control's only content).

Run:  python3 tools/a11y_fix.py [root]
"""
import os, re, sys, collections

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
stats = collections.Counter()
CONTROL = r"(?:input|select|textarea)"


def slug(text, used):
    # surface the human text inside {% trans "..." %} before stripping template syntax
    text = re.sub(r"\{%\s*trans\s+[\"']([^\"']*)[\"']\s*%\}", r"\1", text)
    s = re.sub(r"\{%[^%]*%\}|\{\{[^}]*\}\}", "", text)
    s = re.sub(r"<[^>]*>", "", s)
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()[:32] or "field"
    base, n = s, 1
    while s in used:
        n += 1
        s = f"{base}-{n}"
    used.add(s)
    return s


def t1_labels(text, used):
    """<label>TEXT</label> immediately followed by a control -> for=/id= pair."""
    out, pos, changed = [], 0, 0
    label_re = re.compile(
        r"<label\b(?![^>]*\bfor\s*=)([^>]*)>((?:(?!</label>|<input|<select|<textarea).)*?)</label>"
        r"(\s*(?:<(?:div|span)\b[^>]*>\s*){0,2})<(" + CONTROL + r")\b",
        re.I | re.S)
    while True:
        m = label_re.search(text, pos)
        if not m:
            out.append(text[pos:])
            break
        out.append(text[pos:m.start()])
        ctl_start = m.end() - len(m.group(4)) - 1  # position of '<' of control
        ctl_end = text.find(">", ctl_start)
        ctl_tag = text[ctl_start:ctl_end]
        idm = re.search(r"\bid\s*=\s*[\"']([^\"']+)[\"']", ctl_tag)
        if idm:
            cid = idm.group(1)
            new_ctl = ctl_tag
        else:
            cid = "cpa11y-" + slug(m.group(2), used)
            new_ctl = ctl_tag.replace("<" + m.group(4), f"<{m.group(4)} id=\"{cid}\"", 1)
        out.append(f"<label for=\"{cid}\"{m.group(1)}>{m.group(2)}</label>{m.group(3)}")
        out.append(new_ctl)
        pos = ctl_end
        changed += 1
    stats["T1 label-for/id pairs"] += changed
    return "".join(out)


def t2_arialabel(text):
    """Controls with a placeholder but no label association -> aria-label."""
    changed = 0

    def get_ids_with_for(t):
        return set(re.findall(r"<label\b[^>]*\bfor\s*=\s*[\"']([^\"']+)[\"']", t, re.I))

    labelled = get_ids_with_for(text)

    def repl(m):
        nonlocal changed
        tag = m.group(0)
        if re.search(r"aria-label(ledby)?\s*=", tag, re.I):
            return tag
        idm = re.search(r"\bid\s*=\s*[\"']([^\"']+)[\"']", tag)
        if idm and idm.group(1) in labelled:
            return tag
        pm = re.search(r"placeholder\s*=\s*(\"[^\"]*\"|'[^']*')", tag, re.I)
        if not pm:
            return tag
        changed += 1
        return tag[:-1].rstrip() + " aria-label=" + pm.group(1) + tag[-1]

    text = re.sub(r"<" + CONTROL + r"\b[^>]*>", repl, text, flags=re.I | re.S)
    stats["T2 aria-label from placeholder"] += changed
    return text


def t3_img_alt(text):
    changed = 0

    def repl(m):
        nonlocal changed
        tag = m.group(0)
        if re.search(r"\balt\s*=", tag, re.I):
            return tag
        changed += 1
        end = "/>" if tag.rstrip().endswith("/>") else ">"
        return tag[: -len(end)].rstrip() + ' alt=""' + end

    text = re.sub(r"<img\b[^>]*/?>", repl, text, flags=re.I | re.S)
    stats["T3 img alt"] += changed
    return text


def t4_modals(text, used):
    changed = 0
    out, pos = [], 0
    # match only the outer .modal container: "modal" as a full class token
    # (NOT modal-dialog / modal-content / modal-header — hyphens are word
    # boundaries, so \bmodal\b alone would match those too)
    modal_re = re.compile(r"<div\b[^>]*class\s*=\s*[\"'](?:[^\"']*\s)?modal(?:\s[^\"']*)?[\"'][^>]*>", re.I)
    title_re = re.compile(r"<(h\d)\b([^>]*class\s*=\s*[\"'][^\"']*\bmodal-title\b[^\"']*[\"'][^>]*)>", re.I)
    while True:
        m = modal_re.search(text, pos)
        if not m:
            out.append(text[pos:])
            break
        tag = m.group(0)
        out.append(text[pos:m.start()])
        pos = m.end()
        if re.search(r"\brole\s*=", tag):
            out.append(tag)
            continue
        # find a modal-title in the next 1500 chars (before any nested modal div)
        window = text[pos:pos + 1500]
        nm = modal_re.search(window)
        tw = window[: nm.start()] if nm else window
        tm = title_re.search(tw)
        extra = ' role="dialog"'
        if tm:
            tidm = re.search(r"\bid\s*=\s*[\"']([^\"']+)[\"']", tm.group(2))
            if tidm:
                tid = tidm.group(1)
            else:
                tid = "cpa11y-mt-" + slug(str(len(used)), used)
                new_title = f"<{tm.group(1)} id=\"{tid}\"{tm.group(2)}>"
                text = text[:pos] + tw[:tm.start()] + new_title + tw[tm.end():] + text[pos + len(tw):]
            extra += f' aria-labelledby="{tid}"'
        out.append(tag[:-1].rstrip() + extra + ">")
        changed += 1
    stats["T4 modal role=dialog"] += changed
    return "".join(out)


def t5_viewport(text):
    n1 = len(re.findall(r",?\s*(maximum-scale\s*=\s*1(\.0)?|user-scalable\s*=\s*no)", text, re.I))
    text, _ = re.subn(r",?\s*maximum-scale\s*=\s*1(\.0)?", "", text, flags=re.I)
    text, _ = re.subn(r",?\s*user-scalable\s*=\s*no", "", text, flags=re.I)
    stats["T5 viewport zoom unblocked"] += 1 if n1 else 0
    return text


def t6_icons(text):
    changed = 0
    out, pos = [], 0
    icon_re = re.compile(r"<i\b[^>]*class\s*=\s*[\"'][^\"']*\b(?:fa[a-z]?|fa-[\w-]+|glyph-icon|glyphicon)\b[^\"']*[\"'][^>]*>", re.I)
    while True:
        m = icon_re.search(text, pos)
        if not m:
            out.append(text[pos:])
            break
        tag = m.group(0)
        out.append(text[pos:m.start()])
        pos = m.end()
        if re.search(r"aria-hidden|aria-label|\brole\s*=", tag, re.I):
            out.append(tag)
            continue
        # sole content of a button/anchor? then skip (it may be the accname)
        before = text[max(0, m.start() - 200):m.start()]
        after = text[pos:pos + 40]
        sole = re.search(r"<(button|a)\b[^>]*>\s*$", before, re.I) and re.match(r"\s*</i>\s*</(button|a)>", after, re.I)
        if sole:
            parent = re.search(r"<(?:button|a)\b[^>]*>\s*$", before, re.I).group(0)
            if not re.search(r"aria-label|title\s*=", parent, re.I):
                out.append(tag)  # leave visible: it's the only name the control has
                continue
        out.append(tag[:-1].rstrip() + ' aria-hidden="true">')
        changed += 1
    stats["T6 decorative icons hidden"] += changed
    return "".join(out)


nfiles = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules"}]
    for fn in filenames:
        if not fn.endswith(".html"):
            continue
        path = os.path.join(dirpath, fn)
        if "/templates/" not in path:
            continue
        text = orig = open(path, encoding="utf-8").read()
        used = set(re.findall(r"\bid\s*=\s*[\"']([^\"']+)[\"']", text))
        text = t1_labels(text, used)
        text = t2_arialabel(text)
        text = t3_img_alt(text)
        text = t4_modals(text, used)
        text = t5_viewport(text)
        text = t6_icons(text)
        if text != orig:
            open(path, "w", encoding="utf-8").write(text)
            nfiles += 1

print(f"Modified {nfiles} files")
for k, v in sorted(stats.items()):
    print(f"  {k}: {v}")

# --- T7 (appended): icon-only buttons — derive aria-label from data-tooltip/title ---
def t7_iconbtn_names(text):
    changed = 0
    def repl(m):
        nonlocal changed
        tag = m.group(0)
        head = tag[:tag.find('>') + 1]
        if re.search(r'aria-label\s*=', head, re.I):
            return tag
        src = re.search(r'(?:data-tooltip|title)\s*=\s*("[^"]*"|\'[^\']*\')', head, re.I)
        if not src:
            return tag
        changed += 1
        new_head = head[:-1].rstrip() + ' aria-label=' + src.group(1) + '>'
        return new_head + tag[len(head):]
    text = re.sub(r'<button\b[^>]*>\s*<i\b[^>]*>\s*</i>\s*</button>', repl, text, flags=re.I | re.S)
    stats['T7 icon-button aria-label'] += changed
    return text

if __name__ == '__main__' or True:
    n2 = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in {'.git', 'node_modules'}]
        for fn in filenames:
            if not fn.endswith('.html'):
                continue
            path = os.path.join(dirpath, fn)
            if '/templates/' not in path:
                continue
            text = orig = open(path, encoding='utf-8').read()
            text = t7_iconbtn_names(text)
            if text != orig:
                open(path, 'w', encoding='utf-8').write(text)
                n2 += 1
    print(f"T7 modified {n2} files: {stats['T7 icon-button aria-label']} buttons")
