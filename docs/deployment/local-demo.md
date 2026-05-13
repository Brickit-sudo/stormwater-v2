# V2 Local Demo

This is the safe path for showing V2 on Bryce's local computer. It starts local Postgres, runs migrations, optionally seeds deterministic demo data, then opens FastAPI and Next.js in separate PowerShell windows.

This is not production hosting, not a real import, and not a place for real client data.

## One-Command Demo

From the V2 repo root:

```powershell
cd C:\Users\brolf\Desktop\Stormwater_APP_Clean\stormwater-v2
.\scripts\start-v2-demo.ps1 -Seed
```

For a fresh deterministic demo reset:

```powershell
.\scripts\start-v2-demo.ps1 -ResetSeed
```

Use `-NoBrowser` when you do not want the script to open the browser:

```powershell
.\scripts\start-v2-demo.ps1 -Seed -NoBrowser
```

Optional ports:

```powershell
.\scripts\start-v2-demo.ps1 -Seed -ApiPort 8000 -WebPort 3000
```

The script will:

- Verify it is running inside the `stormwater-v2` repo.
- Verify Docker is available.
- Start or create the local `stormwater-v2-postgres` container with safe local defaults.
- Create missing env files from safe local demo defaults only.
- Keep existing `apps/api/.env` and `apps/web/.env.local` untouched.
- Run `alembic upgrade head`.
- Seed demo rows when `-Seed` or `-ResetSeed` is passed.
- Start API and web dev servers in separate PowerShell windows.
- Write ignored runtime logs under `logs/v2-demo/`.

## Stop Demo

Stop API and web windows started by the launcher:

```powershell
.\scripts\stop-v2-demo.ps1
```

Postgres is left running by default so the next demo starts quickly. To stop it too:

```powershell
.\scripts\stop-v2-demo.ps1 -StopPostgres
```

The stop script never deletes Docker containers or volumes.

## Check Status

```powershell
.\scripts\status-v2-demo.ps1
```

Status shows:

- Git branch, latest commit, and working tree status.
- Env file presence and required key presence without printing secrets.
- Docker/Postgres status.
- Tracked API/web process status.
- API health and frontend HTTP checks.
- Helpful next commands.

## Boss Demo URLs

Use these same-machine URLs:

- App: `http://127.0.0.1:3000`
- API health: `http://127.0.0.1:8000/health`
- Roadmap: `http://127.0.0.1:3000/roadmap`
- Clients: `http://127.0.0.1:3000/crm/clients`
- Sites: `http://127.0.0.1:3000/crm/sites`
- Jobs: `http://127.0.0.1:3000/crm/jobs`
- Schedule: `http://127.0.0.1:3000/schedule`
- Map: `http://127.0.0.1:3000/map`
- Work Hub: `http://127.0.0.1:3000/work`
- Search: `http://127.0.0.1:3000/search`

Use `127.0.0.1` for the demo URL. If `localhost:3000` or an old browser tab
shows raw, unstyled HTML with default blue links, run:

```powershell
.\scripts\status-v2-demo.ps1
```

The status script checks that the frontend HTML and its CSS chunk both load. A
CSS failure usually means a stale Next.js process is still serving an older
build after `.next` changed. Close the old Node/Next window or stop the process
on port `3000`, then rerun `.\scripts\start-v2-demo.ps1 -Seed`.

## Local Demo vs LAN Demo vs Tunnel

### Local Same-Machine Demo

Best for Bryce's boss sitting at, or screen-sharing into, Bryce's computer.

The launcher binds API and web to `127.0.0.1`, so only the same computer can open it. This is the safest default because V2 does not have production auth yet.

The local computer must stay on, Docker Desktop must stay running, and both PowerShell server windows must stay open.

### LAN Demo

A LAN demo means another device on the same office/Wi-Fi network opens Bryce's computer by local IP address. This should stay a deliberate manual step, not the default launcher behavior.

Before doing a LAN demo:

- Bind dev servers to a LAN interface such as `0.0.0.0`.
- Update API CORS origins for the LAN web URL.
- Use only seed/demo data.
- Confirm Windows firewall allows the selected ports.
- Stop the demo when finished.

Do not use LAN sharing for real client data until login and organization access control exist.

### Temporary Tunnel

A temporary tunnel, such as an ngrok-style or Cloudflare-style tunnel, exposes the local demo through a public HTTPS URL for a short review window.

Use this only with seed/demo data. A tunnel does not turn the local app into hosted staging. Bryce's computer must stay on, the tunnel must stay running, and anyone with the URL may be able to reach the app unless the tunnel adds its own access gate.

If provider OAuth is tested later through a tunnel, Microsoft/Google callback URLs must match the public HTTPS tunnel URL.

### 24/7 Hosted Staging

24/7 staging means the app is deployed to persistent hosting with managed HTTPS, a managed database, backups, environment variables, OAuth callback URLs, and auth/login. See [staging-deploy-plan.md](staging-deploy-plan.md).

## Env Files

The launcher will create missing local files only:

- `apps/api/.env`
- `apps/web/.env.local`

It will not overwrite existing env files and will not commit them. Real secrets stay local and ignored.

The default demo organization ID is deterministic:

```text
850c47b8-6d32-58a0-8605-955527cadbf3
```

## Real Data Warning

Do not expose real client data over LAN, tunnel, or public hosting until at least these are configured:

- Real auth/login.
- Organization membership and access control.
- HTTPS.
- Hosted database backups.
- Secret-managed environment variables.
- Provider OAuth callback URLs for the deployed domain.
- A reviewed import process using the V2 import contract/templates/validator.

Use demo/seed data only unless auth and hosting are configured.
