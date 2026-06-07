# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"Minecraft Quest" (Pai Vinny) — a gamified parental-control system that gates a child's
Linux terminal time behind reading. The child opens a **web terminal in the browser**
(ttyd, password-protected); their login shell is a Python session manager that runs a
journey of Linux challenges and requires reading a book + writing a summary to unlock the
next stage. A separate FastAPI "portal" lets the parent watch progress in real time and
push messages to the child's terminal.

The codebase and all UI strings are in Brazilian Portuguese — keep that convention.

## Architecture

Two services (`docker-compose.yml`): **`minecraft-quest`** (the child's container: ttyd web
terminal + the quest + Minecraft server) and **`portal`** (parent dashboard). They
communicate **only** through a shared Docker volume mounted at `/data` (`sessao-data`) —
there is no direct network/API call between them; all coordination is file-based.

Access is **browser-only** (no SSH): `docker-entrypoint.sh` runs `ttyd ... su - jogador`,
so each browser connection to the terminal domain opens a fresh quest session as `jogador`.
ttyd's HTTP Basic Auth (`--credential jogador:$JOGADOR_SENHA`) is the password gate, served
over HTTPS by Traefik. Minecraft (25565) is the only host-published port.

Repo layout: `sessao.py` + `Dockerfile` + `iniciar-minecraft.sh` + `docker-entrypoint.sh`
build the quest container (root context). `portal/` has its own `Dockerfile` and build context.

**`sessao.py`** — runs inside the child's container as the login shell of `jogador`
(set via `usermod -s /opt/sessao.py jogador`; reached through `su - jogador` under ttyd).
Model: a journey of `TOTAL_ETAPAS` (20) **etapas**, max `ETAPAS_POR_DIA` (2) per day.
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
- Data migration: `carregar_dados` upgrades the v1.0 `sessoes` shape to `etapas` + `etapa_atual`.
- (`sys.argv[1] == '-c'` still short-circuits to plain bash — legacy of the old SSH path, harmless.)

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
cp .env.example .env           # configure domains/passwords first
docker compose up -d --build   # build + start both services
docker compose logs -f         # tail logs
docker compose down            # stop
```

Child access: open `https://<TERMINAL_DOMAIN>` in a browser → Basic Auth (`jogador` +
`JOGADOR_SENHA`) → drops into the etapa flow. No SSH. `iniciar-minecraft` (run inside the
terminal) starts the Paper server but is **locked until all 20 etapas are done**.
Portal: `https://<ADMIN_DOMAIN>/?senha=<PORTAL_SENHA>`.
Admin/emergency shell: `docker exec -it minecraft-quest bash` on the host.

There are no tests, linter, or build step beyond Docker.

## Deploy (Dokploy + Traefik)

Target host runs Dokploy with Traefik as the reverse proxy. Constraints baked into the config:
- Host port **8080 is taken by Traefik** — neither web service is published on the host. Both
  join the external `dokploy-network` and are routed by Traefik **labels** in
  `docker-compose.yml`: `minecraft-quest`'s ttyd (port 7681) on `TERMINAL_DOMAIN`, and `portal`
  (8080) on `ADMIN_DOMAIN`, TLS via `letsencrypt`.
- Only **25565** (Minecraft) is published on the host (raw TCP — not via Traefik).
- `dokploy-network` is declared `external: true` — it must already exist (Dokploy creates it).
- Deploy via the Dokploy UI as a **Compose** app pointing at the Git repo; set the env vars
  from `.env.example` in the Environment tab. If you use the Dokploy **Domains** tab instead of
  the compose labels, don't enable both for the same host (duplicate Traefik routers).

When changing journey timing set `SESSAO_MINUTOS` / `LEITURA_MINUTOS` / `ETAPAS_POR_DIA` — they
reach `sessao.py` via `/etc/environment` (written by the entrypoint) and the `portal` via its
own env, so terminal and dashboard stay in sync.

## Security / isolation

The web terminal is an internet-exposed real shell, so `minecraft-quest` is **a hardened,
isolated container — never the host**. What enforces that (in `docker-compose.yml`):
- The child runs as **non-root `jogador`** (`su - jogador`); no `sudo`. Verified: the child
  shell has **`CapEff=0`** (zero effective capabilities).
- `security_opt: no-new-privileges` — blocks privilege escalation via setuid (su/sudo).
- `cap_drop: ALL` + a minimal `cap_add` (only what `su`/PAM + the entrypoint `chown` need:
  CHOWN, DAC_OVERRIDE, FOWNER, SETUID, SETGID, SETPCAP, AUDIT_WRITE).
- `pids_limit: 200` (anti fork-bomb), `cpus`/`mem_limit` caps.
- **No** host bind mounts (named volumes only), **no** `privileged`, **no** `docker.sock`,
  **no** `network_mode/pid: host`. Admin access is `docker exec` from the host only.

**Residual risks (known, not fully solvable in compose):**
- `minecraft-quest` shares `dokploy-network` with other Dokploy services (Traefik needs it), so
  it could reach them over the network. Mitigation would need a dedicated Traefik↔quest network,
  host firewall, or a Traefik allowlist.
- The container has outbound internet; locking egress needs host firewall/network policy.
- Containers share the host kernel — keep the host patched.
- The terminal is Basic Auth on the internet — use a strong `JOGADOR_SENHA`; consider a Traefik
  rate-limit/IP-allowlist middleware.
Further hardening left as follow-up: read-only rootfs + tmpfs, running ttyd as non-root (gosu),
and egress lockdown.
