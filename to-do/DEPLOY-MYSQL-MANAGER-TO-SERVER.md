# Deploy MySQL Manager fixes to the server (e.g. 207.180.193.210)

## Why you still see no data

- The URL **https://207.180.193.210:2087** is the **remote server** (or your server’s public IP). It is **not** “localhost.”
- Our earlier deploy commands ran on the machine where the repo lives. If that machine is **not** the one serving 207.180.193.210, then the panel you open in the browser is still running the **old** code and old `databases.js`.
- Seeing **`{$ Slow_queries $}`** (literal text) and empty processes means the **Mysqlmanager** controller or the updated JS is not running on the server that serves that URL.

## Fix: run the deploy on the server that serves 207.180.193.210

You must copy the updated files into CyberPanel **on the same machine** that serves https://207.180.193.210:2087 (i.e. where `/usr/local/CyberCP` is used by the panel).

### Option A – You have the repo on that server (e.g. at `/home/cyberpanel-repo`)

SSH to **207.180.193.210** (or the host that serves that IP) and run:

```bash
# Path to repo on THAT server (change if different)
REPO=/home/cyberpanel-repo

cp "$REPO/plogical/mysqlUtilities.py" /usr/local/CyberCP/plogical/
cp "$REPO/databases/views.py" /usr/local/CyberCP/databases/
cp "$REPO/databases/static/databases/databases.js" /usr/local/CyberCP/databases/static/databases/
cp "$REPO/static/databases/databases.js" /usr/local/CyberCP/static/databases/
# LiteSpeed serves /static/ from public/static/ – must deploy here or the browser gets the old file
mkdir -p /usr/local/CyberCP/public/static/databases
cp "$REPO/static/databases/databases.js" /usr/local/CyberCP/public/static/databases/

# Restart panel so changes are used
systemctl restart lscpd

echo "MySQL Manager deploy done. Hard-refresh the MySQL Manager page (Ctrl+Shift+R)."
```

### Option B – Repo is only on another machine (e.g. your dev box)

1. Copy the **four files** from the machine that has the repo to **207.180.193.210** (e.g. with `scp` or `rsync`):
   - `plogical/mysqlUtilities.py`
   - `databases/views.py`
   - `databases/static/databases/databases.js`
   - `static/databases/databases.js`

2. On **207.180.193.210**, run the same `cp` commands as in Option A, using the paths where you put those files instead of `$REPO`.

3. Restart the panel:  
   `systemctl restart lscpd`

### After deploy

- Open **https://207.180.193.210:2087/dataBases/MysqlManager**
- Do a **hard refresh**: **Ctrl+Shift+R** (or Cmd+Shift+R on Mac) so the browser doesn’t use cached `databases.js`.

If you still see no data, open the browser **Developer Tools (F12) → Console** and note any red errors (e.g. `ctrlreg` or 404 for `databases.js`), then share that message.
