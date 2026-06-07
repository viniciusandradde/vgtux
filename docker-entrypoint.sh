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

# Propaga variáveis para a sessão do filho (su - jogador é login shell;
# pam_env lê /etc/environment)
{
  echo "MC_RAM_MIN=${MC_RAM_MIN:-512M}"
  echo "MC_RAM_MAX=${MC_RAM_MAX:-1G}"
  echo "SESSAO_MINUTOS=${SESSAO_MINUTOS:-30}"
  echo "LEITURA_MINUTOS=${LEITURA_MINUTOS:-30}"
  echo "ETAPAS_POR_DIA=${ETAPAS_POR_DIA:-2}"
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
