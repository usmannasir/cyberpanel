# 🤖 Hermes Agent Hosting Guide

CyberPanel can deploy [Hermes Agent](https://hermes-agent.nousresearch.com) as a
one-click Docker application, on its own domain, behind your own SSL, with a
password-protected dashboard.

Available from CyberPanel **v3.0.2**.

## What you get

- The official `nousresearch/hermes-agent` container, managed as a Docker site
- A domain, a vhost and an SSL certificate, created for you
- The Hermes dashboard served at `https://your-domain`, never on an open port
- A persistent data volume, so upgrades and restarts keep your agent's memory
- CPU and RAM limits you choose

## Before you start

- **RAM:** Hermes needs at least **2048MB** for its container. The default Docker
  package allows 1024MB, so raise it first under
  **Docker → Docker Packages**, then assign the package to the site owner.
- **Domain:** point the domain's DNS at your server before you create the site,
  so the SSL certificate can be issued.
- **Model provider:** you need an API key for whichever provider you plan to use
  (Nous Portal, OpenAI, OpenRouter, a local model, and so on). You add this
  **inside the Hermes dashboard after the deployment**, CyberPanel never asks for
  it and never stores it.

## Create the site

1. Go to **Websites → Create Docker Site**.
2. Fill in:
   - **Site Name** — lowercase letters and digits only, this becomes the
     container name
   - **Select Owner** — the panel user who will own the site
   - **Domain Name** — the domain the dashboard will be served on
   - **Select App** — `Hermes`
   - **CPU Cores / RAM** — 1 core and 2048MB is a reasonable starting point
   - **Admin Username / Password** — **these become your Hermes dashboard
     login**, choose a strong password
   - **Admin Email** — used for the website record and the SSL certificate
3. Click **Create Docker Site** and watch the progress bar. The panel creates the
   website, pulls the image, starts the container, wires up the reverse proxy and
   reloads the web server.

The MySQL resource fields disappear when you pick Hermes, because Hermes stores
everything in its own data volume and needs no database container.

## First login

1. Open `https://your-domain`.
2. You will be sent to a login form. Sign in with the admin username and password
   you entered when creating the site.
3. Open the dashboard settings and add your model provider API key.

If the dashboard asks for credentials that are not accepted, the site was created
with a different password than you remember, recreate the site rather than
editing the container by hand.

## Managing the agent

From **Websites → List Docker Sites**, open the site to start, stop, restart or
rebuild the container and to read its logs.

Useful checks over SSH:

```bash
docker ps --filter name=<your-site-name>
docker logs <container-name> --tail 100
docker exec <container-name> hermes doctor
docker exec <container-name> hermes gateway status
```

## Where your data lives

Everything the agent knows lives in:

```
/home/docker/<your-domain>/data
```

That directory is mounted into the container at `/opt/data`. Back it up if the
agent's memory, sessions and skills matter to you. Deleting the Docker site
removes the container, so copy this directory first if you want to keep it.

## Security notes

- The dashboard is **never** published on a public port. It is bound to the
  server's loopback interface and reached only through the domain's HTTPS vhost.
- Hermes refuses to start without a dashboard login configured, so the dashboard
  is protected from the first request. This is deliberate, do not try to disable
  it.
- The agent runs commands inside its own container, and it can reach the internet
  from there. Give it only the API keys it needs, and treat its dashboard
  password like a server password.
- Never point two Hermes containers at the same data directory.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "You can add 1024 or less then 1024 Ram" | The owner's Docker package is too small | Raise the package RAM to at least 2048MB and reassign it |
| Deployment stops at "Containers healthy" | The image is still being pulled on a slow link | Wait, the image is around 4GB, then retry the creation |
| Dashboard shows a login page you cannot pass | Wrong admin credentials for this site | Recreate the site with a known password |
| Domain shows the default page, not Hermes | The vhost proxy context was not written | Check `/usr/local/lsws/conf/vhosts/<domain>/vhost.conf` for a `context /` block and restart the web server |
