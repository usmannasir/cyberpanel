# AWS EC2 + Cursor Remote-SSH – Full Setup Guide

Use this guide to get **aws-server** (3.144.171.128) working with Cursor Remote-SSH.  
Do the steps in order. Everything is copy-paste ready.

---

## 1. Windows SSH config

**File:** `C:\Users\kimsk\.ssh\config`

- Open the file in Notepad or Cursor.
- Find the `Host aws-server` block and replace it entirely with the block below (or add it if missing).
- Use **straight double quotes** `"`, not curly quotes. Path uses forward slashes to avoid issues.

**Exact block to use (port 22 – default):**

```
Host aws-server
    HostName 3.144.171.128
    User ec2-user
    Port 22
    IdentityFile "D:/OneDrive - v-man/Priv/VPS/Cyberpanel.pem"
```

- Save and close.  
- If you later confirm SSH on the instance is on port 2222, change `Port 22` to `Port 2222` and add an inbound rule for 2222 in the Security Group (see step 3).

---

## 2. AWS Security Group – allow SSH (port 22)

1. **AWS Console** → **EC2** → **Instances**.
2. Select the instance whose **Public IPv4** is **3.144.171.128**.
3. Open the **Security** tab → click the **Security group** name (e.g. `sg-xxxxx`).
4. **Edit inbound rules** → **Add rule**:
   - **Type:** SSH  
   - **Port:** 22  
   - **Source:** **My IP** (recommended) or **Anywhere-IPv4** (`0.0.0.0/0`) for testing only.
5. **Save rules**.

If you use port 2222 on the instance, add another rule: **Custom TCP**, port **2222**, source **My IP** (or **Anywhere-IPv4** for testing).

---

## 3. Start SSH on the instance (fix “Connection refused”)

You must run commands on the instance without using SSH from your PC. Use one of these.

### Option A: EC2 Instance Connect (simplest)

1. **EC2** → **Instances** → select the instance (3.144.171.128).
2. Click **Connect**.
3. Open the **EC2 Instance Connect** tab → **Connect** (browser shell).

In the browser terminal, run:

```bash
sudo systemctl status sshd
sudo systemctl start sshd
sudo systemctl enable sshd
sudo ss -tlnp | grep 22
```

You should see `sshd` listening on port 22. Then close the browser and try Cursor.

### Option B: Session Manager

1. **EC2** → **Instances** → select the instance → **Connect**.
2. Choose **Session Manager** → **Connect**.
3. Run the same commands as in Option A.

### Option C: SSH is on port 2222

If you know SSH was moved to 2222 on this instance:

1. In the Security Group, add an **inbound rule**: **Custom TCP**, port **2222**, source **My IP** (or **Anywhere-IPv4** for testing).
2. In your SSH config, set `Port 2222` for `aws-server` (see step 1).
3. Test (see step 4).

---

## 4. Test from Windows

Open **PowerShell** and run:

```powershell
ssh -i "D:/OneDrive - v-man/Priv/VPS/Cyberpanel.pem" -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new ec2-user@3.144.171.128
```

- If it asks for a host key, type `yes`.
- If you get a shell prompt, SSH works. Type `exit` to close.
- If you get **Connection refused**: SSH is not listening on 22 (or 2222); repeat step 3 (Instance Connect / Session Manager) and ensure `sshd` is running and listening on the port you use.
- If you get **Connection timed out**: Security Group is still blocking the port; recheck step 2 and that you edited the security group attached to this instance.

---

## 5. Connect from Cursor

1. In Cursor: **Ctrl+Shift+P** (or **Cmd+Shift+P** on Mac) → **Remote-SSH: Connect to Host**.
2. Choose **aws-server** (or type `aws-server`).
3. Wait for the remote window to open. Cursor AI (Chat, Composer) works in that window as usual.

---

## Checklist

- [ ] SSH config has the `aws-server` block with correct `IdentityFile` and `Port` (22 or 2222).
- [ ] Security Group has an inbound rule for the SSH port (22 or 2222) from My IP (or 0.0.0.0/0 for testing).
- [ ] `sshd` is running on the instance (started via Instance Connect or Session Manager).
- [ ] `ssh ... ec2-user@3.144.171.128` works in PowerShell.
- [ ] Cursor **Connect to Host** → **aws-server** succeeds.

---

## If it still fails

- **Connection refused** → Instance side: start/enable `sshd` and confirm it listens on the port you use (step 3).
- **Connection timed out** → Network: open that port in the instance’s Security Group (step 2).
- **Permission denied (publickey)** → Wrong key or user: confirm the .pem is the one for this instance and the user is `ec2-user` (Amazon Linux) or `ubuntu` (Ubuntu AMI).
