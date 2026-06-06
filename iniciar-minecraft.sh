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

echo
echo "  🎉  RECOMPENSA DESBLOQUEADA! Iniciando o servidor Minecraft..."
echo "      RAM ${RAM_MIN}–${RAM_MAX}  •  conecte o cliente em <IP-da-VPS>:25565"
echo "      Para parar, digite 'stop' no console."
echo

exec java -Xms"${RAM_MIN}" -Xmx"${RAM_MAX}" -jar paper.jar nogui
