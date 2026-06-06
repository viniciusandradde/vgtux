# =============================================================
# Dockerfile — Container do filho (Minecraft Quest)
# Java 21 (Paper 1.21.x) + SSH + sessao.py como login shell
# =============================================================
FROM eclipse-temurin:21-jre

ARG MC_VERSION=1.21.4

# Pacotes: SSH, Python (login shell + parse da API do Paper), utilitários
RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
        python3 \
        ca-certificates \
        curl \
        nano \
        less \
    && rm -rf /var/lib/apt/lists/*

# ── Usuário do filho ─────────────────────────────────────────
RUN useradd -m -s /bin/bash jogador \
    && mkdir -p /home/jogador/minecraft \
    && mkdir -p /run/sshd

# ── Login shell = gerenciador de sessões ─────────────────────
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

# ── Hardening básico do sshd ─────────────────────────────────
RUN sed -i \
        -e 's/^#\?PermitRootLogin.*/PermitRootLogin no/' \
        -e 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' \
        /etc/ssh/sshd_config \
    && echo "AllowUsers jogador" >> /etc/ssh/sshd_config

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 22 25565
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
