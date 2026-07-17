# CyberPanel WCAG 2.2 A/AA Accessibility Audit

**Scope:** CyberPanel v2.4.8 (branch `v2.4.8`, commit `2bbce95`), all Django templates (232 files scanned), shared design-system CSS (`baseTemplate/static/baseTemplate/css/*`), base page shell, and the live login page rendered from a production install.

**Method:** static pattern scan of every template (custom scanner, `tools/a11y_scan.py`), manual review of the page shell (`baseTemplate/templates/baseTemplate/index.html`), the login page (`loginSystem/templates/loginSystem/login.html`), representative form pages (`websiteFunctions/createWebsite.html`), and the shared JS/CSS. Target: WCAG 2.2 Level A and AA.

## What is already good

The v2.4.x redesign brought the shell to a solid baseline:

- Skip link to `#main-content`, `:focus-visible` outline ring, and a focus-suppression rule only for non-keyboard focus (`cyberpanel-ui.css`).
- Sidebar nav is real links inside `<nav aria-label>`; mobile toggle and theme toggle carry `aria-expanded`/`aria-pressed`; notification panel closes on Esc and returns focus.
- Design tokens with light/dark themes; `--text-secondary: #6b7280` on white is 4.8:1 (passes 1.4.3).
- PNotify toasts set `aria-live`.

## Findings

### F1 — Forms: labels not programmatically associated (WCAG 1.3.1, 3.3.2, 4.1.2 — Level A)

The dominant failure. The house style is `<label class="form-label">Text</label>` followed by a control with **no `id`** and no `for`, so the visible label is never programmatically bound:

- 213 `<select>` elements with no label association or `aria-label` (96 files)
- 289 `<input>` elements whose only "label" is a placeholder (85 files)
- 194 `<input>` elements with no label and no placeholder-derived name at all (50 files)
- 17 inputs that have an `id` but whose label still lacks `for`

Screen-reader users get "edit text, blank" for essentially every form field in the panel (create website, DNS records, email accounts, backups, firewall rules…).

### F2 — Modals missing dialog semantics (WCAG 4.1.2 — Level A)

Most Bootstrap `.modal` containers already carry `role="dialog"`; 12 (file manager, CLManager, others) have neither `role` nor an accessible name, and almost none reference their `.modal-title` via `aria-labelledby`. Focus is also not trapped where modals are shown/hidden with raw jQuery/Angular `ng-show` instead of the Bootstrap modal plugin (Bootstrap 3's `enforceFocus` only runs when the plugin is used).

### F3 — Images without text alternatives (WCAG 1.1.1 — Level A)

261 `<img>` tags in 91 files have no `alt` attribute (mostly decorative artwork, loading spinners, and logos), plus literal `alt="..."` placeholders. Unnamed images are read out as raw file names.

### F4 — Keyboard operability of custom controls (WCAG 2.1.1 — Level A)

- 6 `<a ng-click>` elements with **no `href`** — not focusable, completely unreachable by keyboard.
- 134 `<a href="#" ng-click>` — focusable and operable, but activate a hash jump; minor.
- ~50 `div`/`li`/`i`/`td`/`span` elements with `ng-click`/`onclick` and no `role`, no `tabindex` — invisible to keyboard users (list-row actions, icon glyph buttons).

### F5 — Icon-only buttons with no accessible name (WCAG 4.1.2 — Level A)

76 buttons in 20 files whose entire content is a Font Awesome `<i>` glyph, with no `aria-label` (some have `title`, many have nothing). Font Awesome renders via CSS generated content, which *is* exposed to the accessibility tree, so these announce as garbage glyph names or nothing.

### F6 — Login page (multiple criteria)

`loginSystem/login.html`, verified against the live rendered page:

- `viewport` sets `maximum-scale=1.0, user-scalable=no` — zoom disabled (**1.4.4 AA**). 5 more templates do the same.
- Username, 2FA, and language fields: placeholder-only, no labels (**1.3.1/3.3.2 A**); username lacks `autocomplete="username"` (**1.3.5 AA**), 2FA lacks `autocomplete="one-time-code"`.
- Brand teal `#33CCCC` used for the "Sign In" button (white text, **1.93:1**) and the CyberPanel `<h1>` on white (**1.93:1**) — fails **1.4.3 AA** (needs 4.5:1, or 3:1 large text); the white hero heading sits on the teal end of the gradient (~2:1).
- Login error box has no `role="alert"`/`aria-live` — failures are silent to screen readers (**4.1.3 AA**).
- Logo `<img>` has no `alt`; card image `alt="..."`.
- Pressing Enter in the username field triggers a native GET submit of `action="/"` (page reload, input lost) instead of logging in — keyboard flow broken.
- Page-load spinner overlay has no status semantics.
- Invalid markup: `<div class>`, `</br />`.

### F7 — Status messages not announced (WCAG 4.1.3 — Level AA)

Only 2 templates in the entire codebase use `aria-live`. The panel is heavily AJAX: create/delete operations flip `ng-show` status divs, progress bars, and success/error blocks that are never announced. Raw `alert()` is still used in several module JS files (announced, but obtrusive). The base-template `cpToast` fallback does set `role`, and PNotify sets `aria-live`, so toast-based flows are OK.

### F8 — Page shell gaps (base template)

- `<html lang="en">` is hardcoded even though `LANGUAGE_CODE` is loaded one line above — wrong language for the 17 supported locales (**3.1.1 A**).
- Command palette (Ctrl/Cmd-K): `role="dialog" aria-modal="true"` but **no focus trap** (Tab escapes into the obscured page), focus is not restored to the trigger on close, and arrow-key selection is invisible to screen readers (no `aria-activedescendant`/option semantics) (**2.4.3, 4.1.2**).
- Sidebar quick-filter: result changes and the "No matching menu items" state are not announced (**4.1.3 AA**).
- Icon-only social links rely on `title` only; their `<i>` glyphs lack `aria-hidden`.
- "Copied!" feedback for the IP-copy control is `aria-hidden` — copy success is never announced (**4.1.3 AA**).

### F9 — Tables (WCAG 1.3.1 — Level A)

Most data tables correctly use `<th>`; 2 templates have header-less tables. Angular-generated list tables generally lack `scope="col"` but have real `<th>` — minor.

### Not failing / out of scope

- 4.1.1 Parsing is obsolete in WCAG 2.2 (invalid markup noted only where it affects AT).
- WCAG 2.2's new 2.5.8 Target Size: sidebar/menu items and buttons are ≥24px; icon buttons in table rows are borderline but have adjacent spacing (passes the spacing exception).
- 3.3.8 Accessible Authentication: password login + TOTP both allow paste; passes.
- Dragging (2.5.7): no drag-only interactions found.

## Remediation plan (this fork)

| Tier | What | How |
|------|------|-----|
| 1 | Login page, base-template shell (F6, F8) | Hand-rewritten |
| 2 | F1–F3, F5, viewport (F6) across all templates | Scripted, deterministic transforms (`tools/a11y_fix.py`), full diff reviewed |
| 3 | F4 no-href links, F7 aria-live on key AJAX flows, F9 | Hand fixes on the worst offenders |
| Doc | Anything left (per-page contrast in legacy inline styles, modal focus traps beyond Bootstrap's) | Tracked in this document |
