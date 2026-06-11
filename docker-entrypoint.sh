#!/bin/bash
# =============================================================
# docker-entrypoint.sh
# Roda TODA VEZ que o container inicia.
# Sobe o terminal web (ttyd) que serve a quest no navegador,
# protegido por senha (HTTP Basic Auth = JOGADOR_SENHA).
# =============================================================
set -e

SENHA="${JOGADOR_SENHA:-minecraft123}"
# Mantém a conta unix com senha (inofensivo; login web é via 'su' como root)
echo "jogador:${SENHA}" | chpasswd

# Volume compartilhado com o portal — garante permissões corretas
mkdir -p /data
chown jogador:jogador /data
chmod 755 /data

# Casa do filho (aventura + mundo Minecraft) persistida em volume
mkdir -p /home/jogador/minecraft
chown -R jogador:jogador /home/jogador/minecraft

# ── Minecraft no CELULAR: Geyser + Floodgate (ponte Bedrock, UDP 19132) ──
# Provisiona os plugins DENTRO do volume (idempotente: só baixa se faltar),
# porque o volume sombreia o conteúdo da imagem. Falha de download não derruba
# o container (|| true) — o terminal/quest seguem funcionando.
MCDIR=/home/jogador/minecraft
PLUGINS="$MCDIR/plugins"
GEYSER_CFG="$PLUGINS/Geyser-Spigot"
mkdir -p "$GEYSER_CFG"
if [ ! -s "$PLUGINS/Geyser-Spigot.jar" ]; then
  echo "→ Baixando Geyser (ponte Bedrock/celular)..."
  curl -fsSL -o "$PLUGINS/Geyser-Spigot.jar" \
    "https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/spigot" \
    || echo "  (aviso: download do Geyser falhou; tenta de novo no próximo start)"
fi
if [ ! -s "$PLUGINS/floodgate-spigot.jar" ]; then
  echo "→ Baixando Floodgate..."
  curl -fsSL -o "$PLUGINS/floodgate-spigot.jar" \
    "https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/spigot" \
    || echo "  (aviso: download do Floodgate falhou; tenta de novo no próximo start)"
fi
# Config mínima do Geyser: porta Bedrock 19132 + auth pelo Floodgate
if [ ! -f "$GEYSER_CFG/config.yml" ]; then
  cat > "$GEYSER_CFG/config.yml" <<'YML'
bedrock:
  port: 19132
remote:
  auth-type: floodgate
YML
fi
# Servidor Java em offline-mode (necessário p/ o Bedrock entrar via Floodgate)
touch "$MCDIR/server.properties"
if grep -q '^online-mode=' "$MCDIR/server.properties"; then
  sed -i 's/^online-mode=.*/online-mode=false/' "$MCDIR/server.properties"
else
  printf 'online-mode=false\n' >> "$MCDIR/server.properties"
fi
chown -R jogador:jogador "$MCDIR"

# Propaga variáveis para a sessão do filho (su - jogador é login shell;
# pam_env lê /etc/environment)
{
  echo "MC_RAM_MIN=${MC_RAM_MIN:-512M}"
  echo "MC_RAM_MAX=${MC_RAM_MAX:-1G}"
  echo "SESSAO_MINUTOS=${SESSAO_MINUTOS:-30}"
  echo "LEITURA_MINUTOS=${LEITURA_MINUTOS:-30}"
  echo "ETAPAS_POR_DIA=${ETAPAS_POR_DIA:-2}"
  echo "FOTO_A_PARTIR=${FOTO_A_PARTIR:-10}"
  echo "ADMIN_DOMAIN=${ADMIN_DOMAIN:-adminvgtux.vsanexus.com}"
} > /etc/environment

echo "╔═══════════════════════════════════════════╗"
echo "║      Minecraft Quest — Container ativo    ║"
echo "║                                           ║"
echo "║  Terminal web (ttyd) na porta 7681        ║"
echo "║  Usuário:  jogador                        ║"
echo "║  Minecraft na porta 25565 (após a quest)  ║"
echo "╚═══════════════════════════════════════════╝"

# Terminal web em foreground. Cada conexão do navegador abre uma nova
# sessão da quest como 'jogador' (login shell = /opt/sessao.py).
exec ttyd \
    --writable \
    --port 7681 \
    --base-path /app \
    --credential "jogador:${SENHA}" \
    --terminal-type xterm-256color \
    -t titleFixed='Minecraft Quest' \
    -t fontSize=16 \
    su - jogador
