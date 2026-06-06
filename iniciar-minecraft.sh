#!/bin/bash
# =============================================================
# iniciar-minecraft — o filho roda este comando dentro da sessão
# para subir o servidor Paper manualmente (economiza RAM quando
# ninguém está jogando).
# =============================================================
RAM_MIN="${MC_RAM_MIN:-512M}"
RAM_MAX="${MC_RAM_MAX:-1G}"

cd "$HOME/minecraft" || { echo "Pasta minecraft não encontrada."; exit 1; }

echo "🟢 Iniciando servidor Minecraft (RAM ${RAM_MIN}–${RAM_MAX})..."
echo "   Conecte no cliente em: <IP-da-VPS>:25565"
echo "   Para parar, digite 'stop' no console."
echo

exec java -Xms"${RAM_MIN}" -Xmx"${RAM_MAX}" -jar paper.jar nogui
