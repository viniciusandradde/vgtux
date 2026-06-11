# =============================================================
# Dockerfile — Container do filho (Minecraft Quest)
# Java 21 (Paper 1.21.x) + ttyd (terminal web) + sessao.py
# Acesso é pelo NAVEGADOR (ttyd), sem SSH.
# =============================================================
FROM eclipse-temurin:21-jre

ARG MC_VERSION=1.21.4
ARG TTYD_VERSION=1.7.7

# Pacotes: Python (login shell + parse da API do Paper), utilitários
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        ca-certificates \
        curl \
        nano \
        less \
    && rm -rf /var/lib/apt/lists/*

# ── Terminal web (ttyd) — binário estático conforme a arquitetura ──
RUN set -eux; \
    arch="$(uname -m)"; \
    case "$arch" in \
        x86_64|amd64) tarch=x86_64 ;; \
        aarch64|arm64) tarch=aarch64 ;; \
        armv7l|armhf) tarch=arm ;; \
        *) echo "arch não suportada para ttyd: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /usr/local/bin/ttyd \
        "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.${tarch}"; \
    chmod +x /usr/local/bin/ttyd; \
    ttyd --version

# ── Usuário do filho ─────────────────────────────────────────
RUN useradd -m -s /bin/bash jogador \
    && mkdir -p /home/jogador/minecraft

# ── Login shell = gerenciador de sessões (a quest) ───────────
COPY sessao.py /opt/sessao.py
RUN chmod +x /opt/sessao.py \
    && usermod -s /opt/sessao.py jogador \
    && echo "/opt/sessao.py" >> /etc/shells

# ── Helper para o filho iniciar o servidor manualmente ───────
COPY iniciar-minecraft.sh /usr/local/bin/iniciar-minecraft
RUN chmod +x /usr/local/bin/iniciar-minecraft

# ── Download do Paper jar (última build da versão) ───────────
RUN set -eux; \
    BUILD=$(curl -fsSL "https://api.papermc.io/v2/projects/paper/versions/${MC_VERSION}/builds" \
            | python3 -c "import sys,json; b=json.load(sys.stdin)['builds']; print(b[-1]['build'])"); \
    JAR="paper-${MC_VERSION}-${BUILD}.jar"; \
    curl -fsSL -o /home/jogador/minecraft/paper.jar \
        "https://api.papermc.io/v2/projects/paper/versions/${MC_VERSION}/builds/${BUILD}/downloads/${JAR}"

# ── Aceite explícito do EULA da Mojang (definido pelo dono do projeto) ──
RUN echo "eula=true" > /home/jogador/minecraft/eula.txt \
    && chown -R jogador:jogador /home/jogador/minecraft

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 7681 25565 19132/udp
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
