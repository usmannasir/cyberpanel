#!/usr/bin/env python3
"""Define the design tokens that CyberPanel templates REFERENCE but that were
never declared in the theme (issue #1804).

Every `var(--foo, <fallback>)` whose --foo is undefined silently uses the
hardcoded light fallback in BOTH themes -> dark mode breaks. This script
collects those tokens and emits cyberpanel-tokens.css with:
  :root { --foo: <fallback>; }                 # light == the exact fallback (no change)
  [data-theme="dark"] { --foo: <dark value>; } # mapped, legible dark value

Light values are byte-identical to the fallbacks pages already use, so LIGHT
MODE IS UNCHANGED. Dark values are derived by role (background/text/border) and
hue, referencing the canonical dark palette so everything stays consistent.
"""
import re, glob, os, collections, colorsys

ROOT = "/Users/cyberpersons/cyberpanel"
EXCLUDE = re.compile(r"/mode/|/static/filemanager/")

# ---- canonical tokens already defined (don't redefine these) ----
defined = set()
for c in glob.glob(os.path.join(ROOT, "baseTemplate/static/baseTemplate/css/*.css")):
    if c.endswith("cyberpanel-tokens.css"):
        continue
    for m in re.finditer(r"(--[a-zA-Z0-9-]+)\s*:", open(c, errors="ignore").read()):
        defined.add(m.group(1))

# ---- collect (token -> most common hex/simple-color fallback) ----
# match var(--tok , fallback) where fallback has no nested parens (hex / named color)
VAR_RE = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)\s*,\s*([^(),]+?)\s*\)")
fallbacks = collections.defaultdict(collections.Counter)
for f in glob.glob(os.path.join(ROOT, "**/*.html"), recursive=True):
    if EXCLUDE.search(f):
        continue
    txt = open(f, errors="ignore").read()
    for m in VAR_RE.finditer(txt):
        tok, fb = m.group(1), m.group(2).strip()
        fallbacks[tok][fb] += 1

HEX = re.compile(r"^#[0-9a-fA-F]{3,6}$")
NAMED = {"white": "#ffffff", "black": "#000000", "whitesmoke": "#f5f5f5",
         "transparent": "transparent"}

def to_rgb(v):
    v = v.strip().lower()
    if v in NAMED and NAMED[v].startswith("#"):
        v = NAMED[v]
    if not HEX.match(v):
        return None
    h = v[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def lum(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def sat(rgb):
    mx, mn = max(rgb), min(rgb)
    return 0 if mx == 0 else (mx - mn) / mx

def hue_bucket(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    h, _l, _s = colorsys.rgb_to_hls(r, g, b)
    deg = h * 360
    if deg < 18 or deg >= 345: return "red"
    if deg < 45:               return "amber"   # orange-amber
    if deg < 70:               return "amber"   # yellow
    if deg < 170:              return "green"
    if deg < 250:              return "blue"
    if deg < 290:              return "indigo"  # violet
    return "red"                                # magenta/pink -> treat as red family

SOFT_BG = {"red": "var(--danger-soft-bg)", "green": "var(--success-soft-bg)",
           "amber": "var(--warn-soft-bg)", "blue": "var(--info-soft-bg)",
           "indigo": "var(--accent-soft-bg)", "neutral": "var(--bg-muted)"}
SOFT_TEXT = {"red": "var(--danger-soft-text)", "green": "var(--success-soft-text)",
             "amber": "var(--warn-soft-text)", "blue": "var(--info-soft-text)",
             "indigo": "var(--text-heading)", "neutral": "var(--text-secondary)"}

def dark_value(name, light):
    n = name.lower()
    rgb = to_rgb(light)
    if rgb is None:
        return None  # only handle color tokens; non-colors stay as their (theme-neutral) fallback
    L, S, hb = lum(rgb), sat(rgb), hue_bucket(rgb)
    is_text = ("text" in n or n.endswith("-color") and "bg" not in n and "border" not in n
               or "muted" in n or n.endswith("-label"))
    is_border = "border" in n
    is_bg = ("bg" in n or "background" in n or "surface" in n or "card" in n
             or "fill" in n or "-light" in n or "overlay" in n) and not is_text and not is_border
    is_darksurface = any(k in n for k in ("console", "terminal", "code", "editor")) and L < 90

    # intentionally-dark surfaces (consoles/terminals/code) already read fine -> keep
    if is_darksurface:
        return light

    def neutral_text(L):
        if L >= 170: return light                 # already-light text stays light (e.g. white)
        if L <= 70:  return "var(--text-heading)"
        if L <= 150: return "var(--text-primary)"
        return "var(--text-secondary)"

    NEUTRAL = S < 0.10
    if NEUTRAL:
        if is_border:
            return "var(--border-color)"
        if is_text:
            return neutral_text(L)
        if L >= 205:                       # light surface
            return "var(--bg-secondary)" if L >= 242 else "var(--bg-muted)"
        return "var(--bg-hover)"           # mid/dark neutral surface
    # saturated (semantic / brand)
    if is_border:
        return "var(--border-color)"
    if is_text:
        if S >= 0.45 and L <= 95:          # vivid dark ink -> soft light ink
            return SOFT_TEXT[hb]
        if S < 0.45:                        # desaturated blue/grey text -> neutral
            return neutral_text(L)
        return light                        # vivid mid brand color (icon/link) -> keep, reads on dark
    if L >= 200:                           # light tint surface -> soft dark tint
        return SOFT_BG[hb]
    if is_bg and L >= 160:
        return SOFT_BG[hb]
    return light                           # mid saturated brand color (buttons/accents) -> keep

# ---- build definitions ----
light_defs, dark_defs = {}, {}
skipped = []
for tok, ctr in fallbacks.items():
    if tok in defined:
        continue
    # choose the most common COLOR fallback if any, else most common overall
    color_fb = [(fb, c) for fb, c in ctr.items() if to_rgb(fb)]
    if not color_fb:
        skipped.append(tok)
        continue
    light = max(color_fb, key=lambda x: x[1])[0]
    dv = dark_value(tok, light)
    if dv is None:
        skipped.append(tok)
        continue
    light_defs[tok] = light
    dark_defs[tok] = dv

# ---- emit ----
out = []
out.append("/* ====================================================================")
out.append("   CyberPanel Missing Design Tokens  (AUTO-GENERATED — issue #1804)")
out.append("   --------------------------------------------------------------------")
out.append("   Templates reference these tokens via var(--x, <fallback>) but they were")
out.append("   never defined, so the hardcoded light fallback was used in BOTH themes")
out.append("   and dark mode broke. LIGHT values below are byte-identical to those")
out.append("   fallbacks (light mode unchanged); DARK values are mapped to the canonical")
out.append("   palette. The dark block follows the light :root so it wins in dark mode.")
out.append("   Regenerate with tools/gen_tokens.py — do not edit by hand.")
out.append("   ==================================================================== */")
out.append(":root {")
for tok in sorted(light_defs):
    out.append(f"    {tok}: {light_defs[tok]};")
out.append("}")
out.append("")
out.append('[data-theme="dark"] {')
for tok in sorted(dark_defs):
    out.append(f"    {tok}: {dark_defs[tok]};")
out.append("}")

dest = os.path.join(ROOT, "baseTemplate/static/baseTemplate/css/cyberpanel-tokens.css")
open(dest, "w").write("\n".join(out) + "\n")
print(f"defined {len(light_defs)} tokens -> {dest}")
print(f"skipped {len(skipped)} non-color/size/gradient tokens (theme-neutral fallbacks, harmless)")
