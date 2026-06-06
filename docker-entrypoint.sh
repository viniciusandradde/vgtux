#!/bin/bash
# =============================================================
# docker-entrypoint.sh
# Roda TODA VEZ que o container inicia.
# Define a senha do jogador a partir da variável de ambiente
# e inicia o servidor SSH.
# =============================================================
set -e

# Definir a senha do usuário jogador
# (vem do .env via docker-compose)
SENHA="${JOGADOR_SENHA:-minecraft123}"
echo "jogador:${SENHA}" | chpasswd

# Volume compartilhado com o portal — garante permissões corretas
mkdir -p /data
chown jogador:jogador /data
chmod 755 /data

# Mundo Minecraft persistido em volume — garante dono correto
mkdir -p /home/jogador/minecraft
chown -R jogador:jogador /home/jogador/minecraft

# Diretório de runtime do sshd
mkdir -p /run/sshd

# Propaga variáveis para a sessão SSH do filho (pam_env lê /etc/environment)
{
  echo "MC_RAM_MIN=${MC_RAM_MIN:-512M}"
  echo "MC_RAM_MAX=${MC_RAM_MAX:-1G}"
  echo "SESSAO_MINUTOS=${SESSAO_MINUTOS:-30}"
  echo "LEITURA_MINUTOS=${LEITURA_MINUTOS:-30}"
} > /etc/environment

echo "╔═══════════════════════════════════════════╗"
echo "║      Minecraft Quest — Container ativo    ║"
echo "║                                           ║"
echo "║  SSH na porta 22                          ║"
echo "║  Usuário:  jogador                        ║"
echo "║  Minecraft na porta 25565 (após a quest)  ║"
echo "╚═══════════════════════════════════════════╝"

# Iniciar o servidor SSH em foreground
exec /usr/sbin/sshd -D
