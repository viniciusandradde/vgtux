#!/bin/bash
# =============================================================
# iniciar-minecraft — RECOMPENSA FINAL
# Só libera o servidor Minecraft depois que o filho concluir
# as 20 etapas da Quest Linux. Antes disso, mostra o progresso.
# =============================================================
RAM_MIN="${MC_RAM_MIN:-512M}"
RAM_MAX="${MC_RAM_MAX:-1G}"
TOTAL_ETAPAS=20
HIST="/data/historico.json"

# Lê a etapa atual do progresso (sem depender de jq)
etapa_atual() {
    python3 - "$HIST" <<'PY' 2>/dev/null || echo 1
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(int(d.get("etapa_atual",
          len([e for e in d.get("etapas", d.get("sessoes", [])) if e.get("completa")]) + 1)))
except Exception:
    print(1)
PY
}

ATUAL="$(etapa_atual)"

if [ "$ATUAL" -le "$TOTAL_ETAPAS" ]; then
    CONCLUIDAS=$((ATUAL - 1))
    FALTAM=$((TOTAL_ETAPAS - CONCLUIDAS))
    echo
    echo "  🔒  Minecraft ainda está TRANCADO."
    echo
    echo "  A recompensa de jogar com o Pai Vinny é a GRANDE FINAL da jornada."
    echo "  Progresso: ${CONCLUIDAS}/${TOTAL_ETAPAS} etapas concluídas."
    echo "  Faltam ${FALTAM} etapa(s)! Continue firme — você consegue. 💪"
    echo
    exit 0
fi

cd "$HOME/minecraft" || { echo "Pasta minecraft não encontrada."; exit 1; }

# IP público da VPS (para conectar de fora). Cai para um aviso se offline.
IP_PUB="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || echo '<IP-da-VPS>')"

echo
echo "  🎉  RECOMPENSA DESBLOQUEADA! Iniciando o servidor Minecraft..."
echo "      RAM ${RAM_MIN}–${RAM_MAX}  •  aguarde aparecer 'Done' abaixo."
echo "      Para parar, digite 'stop' no console."
echo
echo "  ┌──────────────────────────────────────────────────────────────┐"
echo "  │  📱  COMO ENTRAR PELO CELULAR (Minecraft Bedrock / Pocket)     │"
echo "  ├──────────────────────────────────────────────────────────────┤"
echo "  │  1) Abra o Minecraft no celular                               │"
echo "  │  2) Toque em JOGAR → aba SERVIDORES → 'Adicionar servidor'     │"
echo "  │  3) Nome do servidor:  Pai Vinny                              │"
echo "  │     Endereço (IP):     ${IP_PUB}"
echo "  │     Porta:             19132                                  │"
echo "  │  4) Salvar e tocar no servidor para ENTRAR! 🎮                │"
echo "  ├──────────────────────────────────────────────────────────────┤"
echo "  │  💻  No COMPUTADOR (Minecraft Java):  ${IP_PUB}:25565"
echo "  └──────────────────────────────────────────────────────────────┘"
echo "      (Se não conectar: peça pro responsável abrir a porta 19132/UDP"
echo "       no firewall da nuvem. O servidor só fica no ar enquanto isto roda.)"
echo

exec java -Xms"${RAM_MIN}" -Xmx"${RAM_MAX}" -jar paper.jar nogui
