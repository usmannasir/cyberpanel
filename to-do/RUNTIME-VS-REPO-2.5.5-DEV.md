# Runtime vs Repo: What Belongs in cyberpanel-repo for 2.5.5-dev

## Goal

When users upgrade to **our** (master3395) 2.5.5-dev, the panel should look and behave the same. That means **default** look-and-feel and behavior must be defined in the repo, not only “generated” on the server.

---

## What is “runtime generated”?

On the live server, after install/upgrade you have:

1. **From the repo (clone/copy)**  
   All app code, templates, static sources, migrations, `version.txt`, default `settings.py`, etc.  
   → This **should** be in the repo (and already is).

2. **Generated at install/upgrade**  
   - Python venv under `/usr/local/CyberCP/bin`, `lib`, `lib64`  
   - `collectstatic` output under `/usr/local/CyberCP/public/static`  
   - `version` table and `baseTemplate_cyberpanelcosmetic` row (if created by code/migrations)  
   - `lscpd` binary copy, symlinks, etc.  
   → The **sources** that produce these (e.g. static sources, migrations) **should** be in the repo.

3. **Per-server / preserved**  
   - `CyberCP/settings.py` — upgrade **merges** only the `DATABASES` section from the old server; the rest (e.g. `INSTALLED_APPS`) comes from the **new** clone.  
   - `baseTemplate/static/baseTemplate/custom/` (custom CSS files)  
   - DB row `baseTemplate_cyberpanelcosmetic.MainDashboardCSS` (custom dashboard CSS)  
   - `.git/`, phpMyAdmin config, SnappyMail data, etc.  
   → **Defaults** that define “how 2.5.5-dev looks” should be in the repo; **per-server overrides** stay on the server.

---

## What we need in the repo so 2.5.5-dev “looks the same”

- **Templates, static sources, JS/CSS**  
  Already in repo (e.g. `baseTemplate/`, `static/`). No change needed for “same look” unless you change the design.

- **Default `settings.py`**  
  Already in repo. Upgrade keeps DB credentials from the server and uses repo for everything else (e.g. `INSTALLED_APPS`).  
  So 2.5.5-dev behavior is driven by the repo’s `settings.py`.

- **Version**  
  `baseTemplate/views.py` has `VERSION = '2.5.5'`, `BUILD = 'dev'`. Repo’s `version.txt` is `{"version":"2.5.5","build":"dev"}`.  
  Upgrade also writes version into the DB. So version “same as 2.5.5-dev” is already defined in the repo.

- **Default “look” (cosmetic)**  
  - Code already creates a default `CyberPanelCosmetic` row with **empty** `MainDashboardCSS` if none exists (`baseTemplate/context_processors.py`, `plogical/httpProc.py`, `loginSystem/views.py`).  
  - If **your live server** has custom dashboard CSS (in DB or in `baseTemplate/static/baseTemplate/custom/`), that is **your** customization.  
  - To make “our 2.5.5-dev” ship with that same look as default, you have two options:

  1. **Data migration**  
     Add a baseTemplate data migration that does:
     - `CyberPanelCosmetic.objects.get_or_create(pk=1, defaults={'MainDashboardCSS': '<your default CSS>'})`  
     so every new/upgraded install gets that default look.

  2. **Static default**  
     Put the CSS in a static file under `baseTemplate/static/` and include it in the base template so the default theme matches your live server.

- **Migrations**  
  All schema (and optional data) migrations must be in the repo so every 2.5.5-dev install/upgrade runs the same schema and, if you add it, the same default cosmetic data.

---

## What should **not** be in the repo

- **Secrets**: DB password, `SECRET_KEY`, API keys.  
  Keep in `settings.py` only placeholders or env reads; real values stay on the server (or in config.php / env per your rules).

- **User data**: sites, users, mail, backups.  
  These are per-server.

- **Generated artifacts**: venv, `collectstatic` output, compiled binaries.  
  Repo holds the **source**; install/upgrade generates these on the server.

---

## Summary

- **Yes:** “Runtime generated” **defaults** that define how 2.5.5-dev looks and behaves **should** be reflected in the repo (templates, static sources, migrations, default cosmetic logic or data).
- **Already in repo:** App code, default settings structure, version, static sources, migrations. So 2.5.5-dev upgrades already get the same **code** and **default look** (empty custom CSS).
- **Optional:** If your live server has a **specific** custom look (e.g. custom dashboard CSS), and you want that to be the **default** for everyone on 2.5.5-dev, add it to the repo via a data migration or default static CSS as above.

No change is **required** for “same look” unless you want to ship a non-empty default cosmetic (e.g. your current dashboard CSS) as part of 2.5.5-dev.
