# Deploy Locally Before Push (v2.5.5-dev)

## Rule
**Always deploy to the local CyberPanel installation before pushing to v2.5.5-dev.**

When deploying and pushing changes:

1. **First: Deploy locally**  
   Copy all modified/relevant files from the repo to `/usr/local/CyberCP`, preserving directory structure.

2. **Then: Commit and push**  
   Stage the same files, commit (author: `master3395`), and push to `origin v2.5.5-dev`.

## Order
1. Deploy → 2. Commit → 3. Push  

Never push to v2.5.5-dev without deploying to `/usr/local/CyberCP` first.

## Example
```bash
# 1. Deploy
cp /home/cyberpanel-repo/path/to/file /usr/local/CyberCP/path/to/

# 2. Commit and push
cd /home/cyberpanel-repo && git add ... && git commit -m "..." --author="master3395 <master3395@users.noreply.github.com>" && git push origin v2.5.5-dev
```
