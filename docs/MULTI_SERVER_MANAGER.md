# Multi-Server Manager

Multi-Server Manager lets one CyberPanel server, the **controller**, manage your other CyberPanel servers, the
**managed servers**, from its own panel: one Nodes page for every paired server, combined lists of websites,
databases and mailboxes, a server switcher in the header, and one-click sign-in to each managed server's panel.

It is in CyberPanel from **3.0.11** and is off on every server until an administrator turns it on.
Online guide: <https://cyberpanel.net/KnowledgeBase/home/multi-server-manager/>.

## Requirements

- CyberPanel 3.0.11 or later on every server: the controller and each server it manages.
- A full administrator account on each server, with **two-factor login** turned on.
- A Multi-Server Manager license for the controller's public IP address. Managed servers need no license.
- Each managed server needs a public IP address. A server whose own address (`/etc/cyberpanel/machineIP`) is
  private gives no pairing code yet.

## License

- $49 per year or $149 lifetime, charged in USD. No monthly plan.
- One license covers one controller, by its IP address, with unlimited managed servers.
- Not included in the Add-ons package or AppSumo licenses.
- Buy it at <https://cyberpanel.net/multi-server-manager>. From 3.0.12, an unlicensed controller's Multi-Server
  pages link to the order page with the server's address filled in. A paid license is active within about a minute.

## Setting it up

1. **Upgrade** every server to 3.0.11 or later.
2. **Turn on two-factor login** for the administrator on each server (Users > Modify User), then sign in again.
3. **Give each server its role:** sidebar > **Multi-Server** (`/multiserver/role`). Choose **Controller** on one
   server and **Managed server** on the others, with your password and a new verification code. After choosing
   Controller, sign out and sign in again.
4. **On the managed server:** Multi-Server > **Controllers** > **Allow a controller**. Enter the controller's public
   IP, your password and a code. Copy the **pairing code** (shown once, one use, valid 10 minutes).
5. **On the controller:** **Nodes** > **Add a server**. Paste the code and a name, check the address and
   fingerprints shown, and confirm with your password and a code. The controller shows an **eight-digit number**.
6. **On the managed server:** Controllers > type that number > **Approve**. Five wrong numbers close the request.
7. **On the controller:** Nodes > **Check approval**. The server shows as **Active**.

## Using it

- **Nodes:** pause, resume, revoke or forget a server.
- **Combined lists:** websites, databases and mailboxes of every paired server (`/multiserver/inventory/…`).
- **Server switcher** in the header.
- **Open panel:** signs you in to the managed server's own panel. The session lasts 30 minutes.
- **Open this page on another server** on create pages. A form always applies to the server whose page it is on:
  choose the server first, then fill in the form there.

A session opened from the controller cannot create panel users, ACLs or API access, or open phpMyAdmin, the
terminal or SSH keys. For those, sign in to that server directly. A controller can sign in to every server it
manages, so protect it like your most important server.

## Ending a link

- On the controller: Nodes can pause, resume or revoke a link.
- On the managed server: Multi-Server > Controllers > **End this link** stops the controller at once.
- Role **Off** stops the feature but keeps the links; with the same role they work again. End or revoke a link
  first to remove it for good.

## Command line (root)

```bash
P=/usr/local/CyberCP/bin/python; M=/usr/local/CyberCP/multiServer/msctl.py
$P $M status                      # role, links
$P $M role off|controller|node    # same as the role page; refused while links of the other kind exist
$P $M disable                     # = role off, always possible
$P $M revoke <32-hex link id>     # managed server: end one controller's link for good
```

Files: `/etc/cyberpanel/multiserver/` (root:cyberpanel 0750): `role`, the identity or master key, `generation`,
`revoked/`. Tables `ms_*` in the panel database; audit trail in `ms_audit`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| No Multi-Server in the sidebar | Panel older than 3.0.11, or the account is not a full administrator |
| The role form asks for two-factor login | Turn on two-factor login for the account and sign in again |
| Nodes says "Sign in to this controller again" | The session started before the server became a controller. Sign out and in |
| "License: Unavailable" on Nodes | No active license for the controller's IP. A new license shows within about a minute |
| "The server answered with a redirect instead of a signed reply" | The managed server no longer accepts the link (feature off, link ended, or the request came from another IP). Pair again |
| "This server is already connected" when pairing again | On the controller: Nodes > Forget the old entry, then pair |
| Signed out of a managed server | Sessions opened from the controller last 30 minutes. Open the server again from the controller |
| One-click sign-in fails in Safari | Needs Safari 16.4 or later |
| Certificate warning when opening a managed server | Its panel uses a self-signed certificate. Issue a real certificate for its hostname |
| The controller's IP changed | The license is per IP: contact support to move it, then pair each server again (a link's allowed IP cannot be edited) |
| The upgrade says the Multi-Server tables were not created | Warning only: the feature stays off. Run the upgrade again when the database is healthy |

## Known limits

- A managed server's pages do not open inside the controller; you work in that server's own panel.
- A managed server cannot pause a link (it can end it).
- A managed server with a private address cannot be paired yet.
- A link's allowed IP cannot be edited.
