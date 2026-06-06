# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"Minecraft Quest" (Pai Vinny) — a gamified parental-control system that gates a child's
SSH/Linux terminal time behind reading sessions. The child connects via SSH; their login
shell is a Python session manager that grants timed bash sessions and requires reading a
book + writing a summary to unlock the next session. A separate FastAPI "portal" lets the
parent watch progress in real time and push messages to the child's terminal.

The codebase and all UI strings are in Brazilian Portuguese — keep that convention.

## Architecture

Three services (`docker-compose.yml`): **`minecraft-quest`** (child's SSH + Minecraft),
**`portal`** (parent dashboard), **`landing`** (public static page). The first two
communicate **only** through a shared Docker volume mounted at `/data` (`sessao-data`) —
there is no direct network/API call between them; all coordination is file-based.

Repo layout: `sessao.py` + `Dockerfile` + `iniciar-minecraft.sh` + `docker-entrypoint.sh`
build the minecraft container (root context). `portal/` and `landing/` each have their own
`Dockerfile` and build context.

**`sessao.py`** — runs inside the child's (minecraft) container as the SSH login shell
(set via `usermod -s /opt/sessao.py jogador` in the Dockerfile).
- `main()` is the gate state machine: enforces `SESSOES_POR_DIA` (2) sessions/day, each
  `SESSAO_MINUTOS` (30) min. Between sessions the child must complete `temporizador_leitura`
  (reading timer) + `coletar_resumo` (line-validated book summary).
- Required summary length grows over time: `calcular_linhas_minimas` adds `CICLO_INCREMENTO`
  lines every `CICLO_DIAS` days since `inicio`.
- `executar_sessao_bash` spawns `bash -i` with two timer threads (5-min warning, hard
  `terminate()`) plus background threads that write a heartbeat and poll for parent messages.
- `sys.argv[1] == '-c'` short-circuits to plain bash so scp/rsync/non-interactive SSH still work.
- Tuning constants live at the top of the file (session/reading minutes, sessions per day,
  summary growth curve).

**`portal/portal.py`** — FastAPI dashboard backend in the portal container; serves `portal.html`.
- Read-only view of `/data`: `get_estado()` aggregates today/total stats; `/api/stream` is
  an SSE endpoint polling every 4s.
- Writes back only to push parent → child communication (`/api/dica`).
- Password auth via the `senha` query param checked against `PORTAL_SENHA` env var.

### The `/data` file contract (the real interface between the two processes)

| File | Writer | Reader | Purpose |
|------|--------|--------|---------|
| `historico.json` | sessao | both | start date + all session records (the source of truth) |
| `online.json` | sessao | portal | heartbeat; portal treats it stale after 90s (`ler_online`) |
| `dicas.json` | portal | sessao | queued login messages; child marks `mostrada: true` after showing |
| `mensagem.txt` | portal | sessao | one real-time message; child writes it to the bash tty then blanks the file |
| `trail.log` | (external) | portal | activity log shown in dashboard |

Real-time messaging works by `sessao.py` writing directly to `/proc/<bash_pid>/fd/1` — the
child's live terminal. This is Linux-specific and depends on the spawned bash PID.

When changing any data field, update **both** files — they share these JSON shapes with no
schema enforcement.

## Commands

```bash
cp .env.example .env           # configure domains/passwords/ports first
docker compose up -d --build   # build + start all three services
docker compose logs -f         # tail logs
docker compose down            # stop
```

Connect as the child: `ssh jogador@<host> -p 2222`. Inside the session, run
`iniciar-minecraft` to start the Paper server (manual start, by design).
Portal: `https://<ADMIN_DOMAIN>/?senha=<PORTAL_SENHA>`. Landing: `https://<LANDING_DOMAIN>`.

There are no tests, linter, or build step beyond Docker.

## Deploy (Dokploy + Traefik)

Target host runs Dokploy with Traefik as the reverse proxy. Constraints baked into the config:
- Host port **8080 is taken by Traefik** — `portal` and `landing` are **not** published on the
  host. They join the external `dokploy-network` and are routed by Traefik **labels** in
  `docker-compose.yml` (keyed on `ADMIN_DOMAIN` / `LANDING_DOMAIN`, TLS via `letsencrypt`).
- Only `minecraft-quest` publishes host ports: **2222** (SSH) and **25565** (Minecraft).
- `dokploy-network` is declared `external: true` — it must already exist (Dokploy creates it).
- Deploy is done via the Dokploy UI as a **Compose** app pointing at the Git repo; set the
  env vars from `.env.example` in the service's Environment tab. The Domains tab can also
  inject the Traefik labels as an alternative to the ones in the compose file.

When changing the session duration, set `SESSAO_MINUTOS` — it is read by **both** `sessao.py`
(`SESSAO_MINUTOS` constant default) and `portal/portal.py` (env var) so the dashboard timer
stays in sync.
