#!/usr/bin/env python3
"""Generate a dark-mode override stylesheet for CyberPanel internal pages.

Scans every template's embedded <style> blocks, finds class/id selectors whose
declarations hardcode NEUTRAL light values (white/grey backgrounds, light
borders, dark/grey text) instead of design tokens, and emits override rules
scoped under [data-theme="dark"] #main-content that route them to the dark
tokens. Light mode is never touched. Brand/semantic colors are left alone.
"""
import os, re, glob, colorsys

ROOT = "/Users/cyberpersons/cyberpanel"

# ---- value buckets (normalized: lowercase, spaces stripped) ----
BG_SECONDARY = {"#fff", "#ffffff", "white", "#fefefe", "#fcfcfc", "#fdfdfd"}
BG_MUTED = {"#f8f9ff","#f0f1ff","#fafbff","#f6f7f9","#f6f7fc","#f9fafb","#f9fafc",
            "#f3f4f6","#f1f5f9","#f8fafc","#f5f6fa","#eef0f4","#eceefb","#f4f5fa",
            "#fafafa","#f5f5f5","#f7f8fa","#eef","#f0f2f5","#f8f9fa","#fbfbfc",
            "#f2f3f5","#fafbfc","#eff1f5","#f0f4ff","#edf2f7","#f0f0ff","#eef0ff",
            "#eeeeff","#f5f5ff","#fbfcff","#fcfdff","#eef1f6","#f7f9fc","#fcfcff"}
BORDER_LIGHT = {"#e8e9ff","#e2e8f0","#e5e7eb","#e7e9ee","#eee","#eeeeee","#ddd",
                "#dddddd","#e0e0e0","#e9ebf4","#e9ecef","#dee2e6","#e1e4e8",
                "#ebedf0","#eaecef","#e3e6ea","#edf0f3","#d1d5db","#e6e8eb",
                "#e4e7ec","#f0f0f0","#ececec"}
TEXT_HEADING = {"#1e293b","#0f172a","#111827","#1a202c","#111","#000","#000000",
                "#1f2937","#2d3748","#212529","#1c1e21","#222","#212121"}
TEXT_PRIMARY = {"#2f3640","#333","#333333","#374151","#334155","#3b4252","#444",
                "#2d3436","#343a40","#393e46","#2c3e50","#4b5563"}
TEXT_SECONDARY = {"#64748b","#6b7280","#6c757d","#94a3b8","#9ca3af","#718096",
                  "#7b8794","#8492a6","#888","#999","#777","#667085","#52525b",
                  "#6e7891","#5a6270","#73798c","#848d9c"}

def norm(v):
    v = v.strip().lower().replace("!important", "").strip()
    v = v.rstrip(";").strip()
    return v

def rgb_channels(val):
    m = re.search(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", val)
    if not m: return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))

def gradient_is_neutral_light(val):
    """True if a linear/radial-gradient is composed only of neutral light stops."""
    if "gradient" not in val:
        return False
    hexes = re.findall(r"#[0-9a-fA-F]{3,6}", val)
    names = re.findall(r"\b(white|whitesmoke|ghostwhite|snow)\b", val.lower())
    if not hexes and not names:
        return False
    for h in hexes:
        if h.lower() not in (BG_SECONDARY | BG_MUTED | BORDER_LIGHT):
            return False
    return True

def _rgb(v):
    v = v.strip().lower()
    if v == "white": return (255, 255, 255)
    if v == "black": return (0, 0, 0)
    m = re.match(r"^#([0-9a-f]{3}|[0-9a-f]{6})$", v)
    if m:
        h = m.group(1)
        if len(h) == 3: h = "".join(c * 2 for c in h)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return rgb_channels(v)
def _lum(c): return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def _sat(c):
    mx, mn = max(c), min(c)
    return 0 if mx == 0 else (mx - mn) / mx
def _hue(c):
    h, _, _ = colorsys.rgb_to_hls(c[0] / 255, c[1] / 255, c[2] / 255)
    d = h * 360
    if d < 18 or d >= 345: return "red"
    if d < 70:  return "amber"
    if d < 170: return "green"
    if d < 250: return "blue"
    if d < 290: return "indigo"
    return "red"
SOFT_BG = {"red": "var(--danger-soft-bg)", "green": "var(--success-soft-bg)",
           "amber": "var(--warn-soft-bg)", "blue": "var(--info-soft-bg)",
           "indigo": "var(--accent-soft-bg)"}
SOFT_TEXT = {"red": "var(--danger-soft-text)", "green": "var(--success-soft-text)",
             "amber": "var(--warn-soft-text)", "blue": "var(--info-soft-text)",
             "indigo": "var(--text-heading)"}

def bg_token(val):
    n = norm(val)
    if n in BG_SECONDARY: return "var(--bg-secondary)"
    if n in BG_MUTED: return "var(--bg-muted)"
    if gradient_is_neutral_light(n): return "var(--bg-muted)"
    if "gradient" in n: return None
    c = _rgb(n)
    if not c: return None
    L, S = _lum(c), _sat(c)
    if S < 0.10:                                  # neutral
        if L >= 246: return "var(--bg-secondary)"
        if L >= 205: return "var(--bg-muted)"
        return None                               # mid/dark neutral: intentional, leave
    if L >= 200:                                  # light semantic tint -> soft dark tint
        return SOFT_BG[_hue(c)]
    return None                                   # saturated mid/dark bg (brand) -> leave

def bg_text_misuse(val):
    """Pages set `background: var(--text-primary, #1e293b)` to get a DARK panel
    (code editors / terminals). In dark mode the text token flips light and the
    panel breaks. Restore a dark surface: use the (dark) fallback, else a dark token."""
    n = norm(val)
    m = re.match(r"^var\(\s*--text-[a-z]+\s*(?:,\s*([^)]+))?\)$", n)
    if not m:
        return None
    fb = (m.group(1) or "").strip()
    c = _rgb(fb) if fb else None
    if c is not None:
        if _lum(c) <= 175:            # intended a dark/mid surface -> keep that exact color
            return fb
        return None                   # light fallback: not a dark-panel misuse, leave
    return "var(--bg-hover)"          # no fallback: give it a dark surface token

def border_token(val):
    # value may be "1px solid #e8e9ff" — extract color
    n = norm(val)
    m = re.findall(r"#[0-9a-fA-F]{3,6}|\b(?:white|whitesmoke)\b", n)
    if not m: return None
    col = m[-1] if isinstance(m[-1], str) else None
    col = re.findall(r"#[0-9a-fA-F]{3,6}|white|whitesmoke", n)
    col = col[-1] if col else None
    if not col: return None
    if col in BORDER_LIGHT: return "var(--border-color)"
    c = _rgb(col)
    if c and _lum(c) >= 198:                       # any light border (incl. semantic tints) -> token
        return "var(--border-color)"
    return None

def text_token(val):
    n = norm(val)
    if "gradient" in n: return None
    if n in TEXT_HEADING: return "var(--text-heading)"
    if n in TEXT_PRIMARY: return "var(--text-primary)"
    if n in TEXT_SECONDARY: return "var(--text-secondary)"
    c = _rgb(n)
    if not c: return None
    L, S = _lum(c), _sat(c)
    if S < 0.16:                                  # neutral dark/grey ink -> light text token
        if L <= 90:  return "var(--text-heading)"
        if L <= 130: return "var(--text-primary)"
        if L <= 165: return "var(--text-secondary)"
        return None                               # already-light text -> leave
    if L <= 95:                                   # vivid dark semantic ink -> soft light ink
        return SOFT_TEXT[_hue(c)]
    return None                                   # vivid mid/bright brand text -> leave (reads on dark)

# selectors we refuse to emit (too broad / would over-reach in dark mode)
BAD_SEL_RE = re.compile(r"[%@]|:root|^html|^body|::?before|::?after|keyframes|^\d|^from$|^to$")
def selector_ok(sel):
    sel = sel.strip()
    if not sel: return False
    if BAD_SEL_RE.search(sel): return False
    if "[data-theme" in sel: return False
    # must be class/id targeted (not a bare element/universal selector)
    if "." not in sel and "#" not in sel and "[" not in sel: return False
    if "*" in sel: return False
    return True

def split_selectors(selblob):
    return [s.strip() for s in selblob.split(",") if s.strip()]

# accumulate: selector -> dict(props)
rules = {}  # sel -> {prop: tokenvalue}

def add(sel, prop, token):
    if not selector_ok(sel): return
    sel = re.sub(r"\s+", " ", sel.strip())
    rules.setdefault(sel, {})
    # don't clobber a more specific earlier mapping for same prop with different token
    rules[sel].setdefault(prop, token)

# innermost-block matcher
BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
DECL_RE = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;{}]+)\s*;?")

EXCLUDE = re.compile(r"/mode/|/static/filemanager/|_backup\.html|_fixed\.html|"
                     r"indexJavaFixed\.html|loginSystem/templates/loginSystem/test\.html")

templates = []
for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
    if EXCLUDE.search(f): continue
    templates.append(f)

scanned = 0
for f in templates:
    try:
        txt = open(f, encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    if "<style" not in txt: continue
    styleblobs = STYLE_RE.findall(txt)
    if not styleblobs: continue
    scanned += 1
    css = "\n".join(styleblobs)
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)  # strip comments (else they glue onto selectors)
    for m in BLOCK_RE.finditer(css):
        selblob, body = m.group(1), m.group(2)
        # skip at-rule preludes captured as selector
        decls = dict()
        for d in DECL_RE.finditer(body):
            prop = d.group(1).strip().lower()
            val = d.group(2).strip()
            decls[prop] = val
        if not decls: continue
        # backgrounds
        for prop in ("background", "background-color"):
            if prop in decls:
                t = bg_token(decls[prop])
                if not t:
                    t = bg_text_misuse(decls[prop])   # background: var(--text-*, dark) -> dark surface
                if t:
                    for sel in split_selectors(selblob):
                        add(sel, "background", t)
        # borders -> border-color
        for prop in ("border", "border-color", "border-top", "border-bottom",
                     "border-left", "border-right"):
            if prop in decls:
                t = border_token(decls[prop])
                if t:
                    for sel in split_selectors(selblob):
                        add(sel, "border-color", t)
        # text color
        if "color" in decls:
            t = text_token(decls["color"])
            if t:
                for sel in split_selectors(selblob):
                    add(sel, "color", t)

# ---- emit ----
out = []
out.append("/* ====================================================================")
out.append("   CyberPanel Dark-Mode Overrides  (AUTO-GENERATED — issue #1804)")
out.append("   --------------------------------------------------------------------")
out.append("   Internal pages hardcode the old light palette (white / #f8f9ff / dark")
out.append("   text) in their embedded <style> instead of using design tokens, so in")
out.append("   dark mode they render as blinding white panels. This sheet re-maps ONLY")
out.append("   the neutral light values those pages declare to the dark tokens, scoped")
out.append("   to [data-theme=\"dark\"] #main-content so LIGHT MODE IS NEVER AFFECTED and")
out.append("   brand / semantic colors (accents, success, danger…) are left untouched.")
out.append("   Regenerate with tools/gen_dark.py — do not edit by hand.")
out.append("   ==================================================================== */")
out.append("")

PROP_ORDER = ["background", "border-color", "color"]
for sel in sorted(rules):
    props = rules[sel]
    decls = []
    for p in PROP_ORDER:
        if p in props:
            decls.append(f"{p}: {props[p]} !important;")
    if not decls: continue
    scoped = f'[data-theme="dark"] #main-content {sel}'
    out.append(scoped + " { " + " ".join(decls) + " }")

dest = os.path.join(ROOT, "baseTemplate/static/baseTemplate/css/cyberpanel-dark.css")
open(dest, "w").write("\n".join(out) + "\n")
print(f"scanned {scanned} templates with <style>")
print(f"emitted {len(rules)} selector rules -> {dest}")
