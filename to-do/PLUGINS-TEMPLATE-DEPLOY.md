# Deploy and verify latest Plugins template on server

## 1. Check if server has the latest template

On the server (207.180.193.210), run:

```bash
grep -q "installedFilterBtnAll" /usr/local/CyberCP/pluginHolder/templates/pluginHolder/plugins.html && echo "LATEST: Yes (Show / Installed only / Active only present)" || echo "LATEST: No (run deploy below)"
```

## 2. Deploy latest template to the server

**Option A – Run on the server (repo already on server)**

If the cyberpanel repo is on the same machine (e.g. at `/home/cyberpanel-repo`):

```bash
sudo bash /home/cyberpanel-repo/pluginHolder/deploy-plugins-template.sh
```

**Option B – Copy from this machine to the server**

From your dev machine (where the repo lives):

```bash
scp /home/cyberpanel-repo/pluginHolder/templates/pluginHolder/plugins.html root@207.180.193.210:/usr/local/CyberCP/pluginHolder/templates/pluginHolder/plugins.html
ssh root@207.180.193.210 "systemctl restart lscpd"
```

Then on the server, verify:

```bash
ssh root@207.180.193.210 'grep -q "installedFilterBtnAll" /usr/local/CyberCP/pluginHolder/templates/pluginHolder/plugins.html && echo "LATEST: Yes" || echo "LATEST: No"'
```

## 3. Verify in the browser

1. Open: https://207.180.193.210:2087/plugins/installed#grid  
2. Ensure **Grid View** is selected.  
3. You should see two rows under the view toggle:
   - **Show:** [All] [Installed only] [Active only]
   - **Sort by:** [Name A–Å] [Type] [Date (newest)]

If you see **Show:** and the three filter buttons, you are on the latest template.
