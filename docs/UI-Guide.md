# CyberPanel Interface Guide (v2.4.8)

A complete guide to the redesigned CyberPanel control panel — its navigation,
features, and day‑to‑day workflows. This guide is written for everyone who logs
in: server administrators, resellers, and website owners.

---

## Table of contents

1. [What changed and why](#1-what-changed-and-why)
2. [The layout at a glance](#2-the-layout-at-a-glance)
3. [The sidebar navigation](#3-the-sidebar-navigation)
4. [Category hub pages](#4-category-hub-pages)
5. [The command palette (Ctrl/Cmd‑K)](#5-the-command-palette-ctrlcmd-k)
6. [The dashboard](#6-the-dashboard)
7. [Managing a website](#7-managing-a-website)
8. [The site management tabs](#8-the-site-management-tabs)
9. [Email, Databases, DNS, FTP, Backups](#9-email-databases-dns-ftp-backups)
10. [Server, Security & Settings (administrators)](#10-server-security--settings-administrators)
11. [Users & Plans](#11-users--plans)
12. [Build Services](#12-build-services)
13. [Light & dark themes](#13-light--dark-themes)
14. [Search, notifications & shortcuts](#14-search-notifications--shortcuts)
15. [What admins, resellers and users each see](#15-what-admins-resellers-and-users-each-see)
16. [Performance notes](#16-performance-notes)
17. [FAQ](#17-faq)

---

## 1. What changed and why

The previous interface put **every page** into a long, nested sidebar — each
resource was split into separate “Create”, “List”, “Modify” and “Delete”
entries, producing dozens of top‑level menus. It was hard to scan and easy to
get lost in.

The redesign is built around three ideas:

- **Navigate by *object*, not by *action*.** You go to *Websites*, *Email*, or
  *Databases* — and the actions (create, edit, delete, …) live on those pages.
- **Keep the sidebar short and scannable.** Depth moves *into* the page
  (category hubs and a per‑site workspace) instead of into an ever‑growing menu.
- **Calm, consistent, fast.** A single neutral design system (light & dark),
  lighter pages, and faster loads.

---

## 2. The layout at a glance

```
┌───────────────────────────────────────────────────────────────┐
│  HEADER:  logo · (search) · notifications · theme · logout      │
├───────────┬───────────────────────────────────────────────────┤
│  SIDEBAR  │  MAIN CONTENT                                       │
│  (flat    │  (dashboard, lists, hubs, the page you opened)      │
│   nav)    │                                                     │
│           │                                                     │
└───────────┴───────────────────────────────────────────────────┘
```

- **Header** — brand, a search button (opens the command palette), a
  notifications bell, the light/dark toggle, and logout.
- **Sidebar** — a short, flat list of destinations grouped into a few clear
  sections. It no longer expands into nested accordions.
- **Main content** — whatever you opened. Most areas open a clean landing page
  (a list or a grid of labelled tiles) where the real work happens.

On phones and small screens the sidebar collapses; tap the menu button
(top‑left) to slide it in.

---

## 3. The sidebar navigation

The sidebar is intentionally short. Items are grouped under plain section
labels:

### HOSTING
| Item | Opens |
|------|-------|
| **Dashboard** | The home overview (quick actions, status, activity). |
| **Websites** | The list of your websites. Pick one to manage everything about it. |
| **WordPress** | Your WordPress sites — deploy, manage, back up. |
| **Email** | The Email hub (accounts, forwarding, deliverability, webmail). |
| **Databases & FTP** | The Data hub (databases, phpMyAdmin, FTP accounts). |
| **Backups** | The Backups hub (one‑click, incremental, schedules, destinations). |
| **Build Services** | Request professional development work (see §12). |

### ACCOUNT
| Item | Opens |
|------|-------|
| **Users & Plans** | Your profile, users, reseller settings and hosting packages. |

### ADMINISTRATION *(administrators only)*
| Item | Opens |
|------|-------|
| **Server** | The Server hub (services, PHP, tuning, containers, logs, DNS server). |
| **Security** | The Security hub (firewall, SSH, ModSecurity, Imunify, SSL, AI Scanner). |
| **Settings** | Version management, design/theme, the setup wizard. |

### HELP
| Item | Opens |
|------|-------|
| **Connect** | The CyberPersons platform. |
| **Community** | The CyberPanel knowledge base. |

> **Tip:** Most items take you straight to a page — there are no menus to
> expand. To reach a deep page quickly, use the command palette (§5).

---

## 4. Category hub pages

Areas that contain several tools — **Email**, **Databases & FTP**, **Backups**,
**Users & Plans**, **Server**, **Security**, and **Settings** — open a **hub
page**: a clean grid of labelled tiles, each with an icon and a one‑line
description.

Instead of hunting through a nested menu, you see all the tools for that area at
a glance and click the one you need. For example, the **Email** hub shows tiles
for *Email Accounts*, *Create Email*, *Forwarding*, *Catch‑All*, *DKIM Manager*,
*Webmail*, and (for admins) deliverability tools like *Email Delivery*,
*SpamAssassin*, *Rspamd*, and *Email Marketing*.

Tiles you don’t have permission for are hidden automatically.

---

## 5. The command palette (Ctrl/Cmd‑K)

The fastest way to get anywhere.

- Press **Ctrl‑K** (Windows/Linux) or **⌘‑K** (Mac) — or click the **search
  icon** in the header.
- Start typing a page or action name (e.g. *“create email”*, *“SSL”*,
  *“firewall”*, *“restart php”*).
- Use **↑ / ↓** to move, **Enter** to open, **Esc** to close.

The palette indexes pages and common actions across the whole panel and respects
your permissions, so it only shows what you can actually open. It’s the
recommended way for power users to jump around without touching the sidebar.

---

## 6. The dashboard

The dashboard is **action‑first**. From top to bottom:

1. **Welcome + Quick Actions** — large buttons for the things you do most:
   *Create Website*, *Deploy WordPress*, *Add Email*, *Back Up*, and
   *Build Services*.
2. **Getting started checklist** *(new installs only)* — appears when you have
   no websites yet and walks you through: create a website → point your domain →
   issue SSL → set up email → configure backups.
3. **Build Services card** — a dismissible card offering professional
   development help. Close it once and it stays closed.
4. **Overview** — live CPU, memory and disk usage with clear colour bands
   (green/amber/red).
5. **Insights** — counts of your users, websites, WordPress sites, databases,
   emails and FTP accounts. Each is a link to that list.
6. **Activity board** — recent SSH logins, logs, top processes, and traffic /
   disk / CPU graphs (administrator view).

---

## 7. Managing a website

Open **Websites** in the sidebar to see your sites. Each row has actions:

- **Manage** — opens the **site management page** for that domain
  (`/websites/<domain>`), where everything about the site lives (see §8).
- **Settings** — the same full management page (alternate entry).
- **Filemanager** — jump straight into the file manager for that site.

If you have **no websites yet**, the list shows a friendly prompt to create your
first one — or to have it built for you (Build Services).

> There is also a lightweight **Site Workspace** (`/websites/<domain>/workspace`)
> — a tabbed hub of shortcuts (Files, SSL, DNS, Email, Databases, Backups,
> Advanced) that links into the relevant tools for that domain.

---

## 8. The site management tabs

The site management page is organised into **tabs** so you’re not scrolling
through one long page. The site name, status, and quick actions (Preview, File
Manager, Terminal, Git, Staging, SSH) stay pinned at the top; the detail is
split into:

| Tab | What’s inside |
|-----|---------------|
| **Overview** | Resource usage (disk, bandwidth, databases, FTP, SSL), package limits, and usage graphs. |
| **Domains** | Child/addon domains, aliases and related settings. |
| **Logs** | Access and error logs for the site. |
| **Config** | Web‑server configuration and rewrite rules. |
| **Files** | File listings and related tools. |
| **Apps** | One‑click application installers (WordPress, Git, PrestaShop, Mautic). |

Click a tab to switch sections. Your current tab is remembered in the page
address, so you can bookmark or refresh and land back on the same tab.

---

## 9. Email, Databases, DNS, FTP, Backups

These everyday areas follow the same pattern: a **list or hub** with a clear
primary action and per‑item controls.

- **Email** (sidebar → *Email*) — manage mailboxes, forwarding, catch‑all,
  limits, DKIM and webmail from one hub.
- **Databases & FTP** (sidebar → *Databases & FTP*) — databases, phpMyAdmin and
  FTP accounts together in one hub.
- **DNS** — manage a domain’s DNS records from the site’s workspace (DNS), and
  create zones / nameservers from the **Server** hub (administrators).
- **Backups** (sidebar → *Backups*) — one‑click backups, incremental backups,
  scheduling, destinations, Google Drive and remote transfers.

---

## 10. Server, Security & Settings (administrators)

Server‑level tools are grouped under **ADMINISTRATION** and only appear for
administrators.

- **Server hub** — Services (start/stop, applications, PowerDNS, Postfix,
  Pure‑FTPd), PHP (extensions, configs, tuning), Performance (LiteSpeed tuning &
  status, top processes, change port, package manager), Containers & CloudLinux,
  Root File Manager, MySQL Manager, DNS zones/nameservers, and Logs.
- **Security hub** — AI Scanner, Firewall, Secure SSH, ModSecurity
  (configuration, rules, rule packs), Imunify 360 / ImunifyAV, and SSL
  certificates (site, hostname, mail server).
- **Settings hub** — Version Management (updates), Design (theme & custom CSS),
  the setup wizard, and Connect.

---

## 11. Users & Plans

Open **Users & Plans** (under ACCOUNT) to manage:

- **Your profile.**
- **Users** — list, create and modify users (subject to your permissions).
- **Reseller Center** — for reseller accounts.
- **Hosting plans (Packages)** — view, create and modify packages.
- **Administrator tools** — ACLs, API access and installed plugins
  (administrators only).

What you see here depends on your role and permissions (see §15).

---

## 12. Build Services

Beyond hosting, CyberPanel offers professional **development services** —
websites, WordPress & eCommerce, **Android** and **iOS** apps, custom software,
UI/UX design, DevOps, and maintenance.

You’ll find it in a few places:

- **Sidebar → Build Services** (always available).
- A **dashboard card** (dismissible).
- **Empty states** — e.g. when you have no websites yet, you can choose to have
  one built for you.

The Build Services page summarises what’s offered and links out to request a
free quote. It’s informational — it never interrupts your work.

---

## 13. Light & dark themes

- Toggle light/dark with the **moon/sun button** in the header. Your choice is
  remembered on the device.
- The whole panel uses a single neutral design system, so colours, spacing and
  typography stay consistent across every page — including the internal tool
  pages — in both themes.

---

## 14. Search, notifications & shortcuts

- **Search / command palette** — `Ctrl/⌘‑K` or the header search icon (§5).
- **Notifications** — the bell in the header collects helpful notices (for
  example, “automatic backups not configured”). Dismiss individual items or
  clear them all.
- **Copy server IP** — click the IP shown in the sidebar to copy it.
- **Keyboard:** `Ctrl/⌘‑K` open search · `↑/↓` move · `Enter` open · `Esc` close.

---

## 15. What admins, resellers and users each see

The interface is **role‑aware** — it only shows what you’re allowed to use.

- **Administrator** — everything, including the **ADMINISTRATION** section
  (Server, Security, Settings) and admin‑only tools (ACLs, API access, plugins,
  default nameservers, etc.).
- **Reseller** — hosting management plus user and package management for their
  customers; no server‑level administration.
- **Website owner / user** — their own websites, email, databases, FTP, SSL and
  backups; the management surface is scoped to what they own.

Menu items, hub tiles and per‑page actions you don’t have permission for are
hidden automatically.

---

## 16. Performance notes

The redesign also loads faster:

- Third‑party assets are pre‑connected and heavy scripts are deferred so they
  don’t block the page from showing.
- Lightweight pages (dashboard, hubs, Build Services, the site workspace) skip
  the large per‑module scripts they don’t need.
- Many tool pages load only the code for that page rather than the whole bundle.
- Per‑account dashboard figures are cached briefly so repeated refreshes stay
  snappy.

You don’t need to do anything to benefit from these — they’re automatic.

---

## 17. FAQ

**Where did the old “Create / List / Modify / Delete” menus go?**
They’re now actions *on* the relevant page. Open *Websites* (or *Email*,
*Databases*, …) and you’ll find create and per‑item controls there.

**I can’t find a page I used to use.**
Press **Ctrl/⌘‑K** and type its name — the command palette finds any page you
have access to.

**A menu item is missing.**
It’s almost certainly a permissions thing — the panel hides what your role can’t
use. An administrator can adjust your ACL under *Users & Plans*.

**How do I manage one specific website?**
*Websites → Manage* on that row. Everything for that domain is on its management
page, organised into tabs.

**How do I switch between light and dark mode?**
Use the moon/sun button in the header. Your preference is saved on the device.

**Where are the development services?**
Sidebar → **Build Services**, or the card on the dashboard.

---

*This guide reflects the CyberPanel interface introduced in v2.4.8.*
