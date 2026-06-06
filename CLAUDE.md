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
(set via `usermod -s /opt/sessao.py jogador` in the Dockerfile). v1.1 model: a journey of
`TOTAL_ETAPAS` (20) **etapas**, max `ETAPAS_POR_DIA` (2) per day.
- `ETAPAS` (top of file) is the list of 20 progressive Linux missions. Each has a `missao`,
  `dica`, a `verificar` shell command (run as the child via `verificar_missao`), and a `teaser`.
- `fazer_etapa()` runs one etapa: **(1) challenge** — `executar_sessao_bash` (timed `bash -i`,
  5-min warning + hard `terminate()`, heartbeat + parent-message threads), then loops on
  `verificar_missao` until the mission is actually done; **(2) reading gate** —
  `temporizador_leitura`; **(3) summary** — `coletar_resumo_portal` (see below). Then reveals
  the next etapa. `registro['desafio_ok']` lets a disconnected etapa resume mid-way.
- `coletar_resumo_portal` writes `resumo_pendente.json` with a random token, shows the child a
  `https://<ADMIN_DOMAIN>/resumo?t=<token>` link, and **polls** `resumo_enviado.json` until the
  portal receives the summary (Ctrl+C aborts; the etapa stays resumable). Summary is no longer
  typed in the terminal.
- Required summary length grows over time: `calcular_linhas_minimas` (LINHAS_BASE + cycles).
- `iniciar-minecraft.sh` is the **reward**: it reads `etapa_atual` from `historico.json` and
  refuses to launch the Paper server until all 20 etapas are done (the only place that promises
  "play with dad").
- `sys.argv[1] == '-c'` short-circuits to plain bash so scp/rsync/non-interactive SSH still work.
- Data migration: `carregar_dados` upgrades the v1.0 `sessoes` shape to `etapas` + `etapa_atual`.

**`portal/portal.py`** — FastAPI backend in the portal container; serves `portal.html`.
- Read-only dashboard of `/data`: `get_estado()` aggregates etapa/book stats (`_etapas()`
  handles both `etapas` and legacy `sessoes`); `/api/stream` is an SSE endpoint (4s).
- Parent → child messaging via `/api/dica` (password-protected by `senha` query param).
- **Child summary flow (token-auth, no parent password):** `GET /resumo?t=<token>` serves a
  mobile form (`_RESUMO_HTML`); `POST /api/resumo-enviar` validates the token against
  `resumo_pendente.json` + line rules, then writes `resumo_enviado.json`.

### The `/data` file contract (the real interface between the two processes)

| File | Writer | Reader | Purpose |
|------|--------|--------|---------|
| `historico.json` | sessao | both | `inicio`, `etapa_atual`, and the `etapas` list (source of truth) |
| `online.json` | sessao | portal | heartbeat; portal treats it stale after 90s (`ler_online`) |
| `dicas.json` | portal | sessao | queued login messages; child marks `mostrada: true` after showing |
| `mensagem.txt` | portal | sessao | one real-time message; child writes it to the bash tty then blanks the file |
| `resumo_pendente.json` | sessao | portal | open summary request: `token`, `etapa`, `linhas_minimas` |
| `resumo_enviado.json` | portal | sessao | summary the child submitted; sessao consumes + deletes it |
| `trail.log` | sessao | portal | activity log shown in the dashboard (`escrever_trail`) |

Real-time messaging works by `sessao.py` writing directly to `/proc/<bash_pid>/fd/1` — the
child's live terminal. This is Linux-specific and depends on the spawned bash PID.

The summary handshake is a file-based request/response over `/data`: sessao writes
`resumo_pendente.json` (with a token) → child submits on the portal → portal writes
`resumo_enviado.json` → sessao polls, matches the token, and continues. When changing a field,
update both `sessao.py` and `portal/portal.py` (shared JSON shapes, no schema enforcement).

## Commands

```bash
cp .env.example .env           # configure domains/passwords/ports first
docker compose up -d --build   # build + start all three services
docker compose logs -f         # tail logs
docker compose down            # stop
```

Connect as the child: `ssh jogador@<host> -p 2222` (drops into the etapa flow).
`iniciar-minecraft` starts the Paper server but is **locked until all 20 etapas are done**.
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
