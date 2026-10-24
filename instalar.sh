#!/bin/bash
# Empacota o jogo com a biblioteca Python do Mage Core e instala no console.
#
#   ./instalar.sh [host-ssh] [pasta-do-sdk]
#   padrão: r36s e ../r36s-a11y-sdk (clone de github.com/gogabs/r36s-a11y-sdk)
#
# Não reinicia nada: o Luma percebe o jogo novo sozinho. Com o jogo aberto,
# não instala, porque ele carrega os sons sob demanda da pasta instalada.
set -euo pipefail
HOST=${1:-r36s}
HERE=$(cd "$(dirname "$0")" && pwd)
SDK=${2:-$HERE/../r36s-a11y-sdk}
SDK_PY="$SDK/python/r36s_a11y"
if [ ! -d "$SDK_PY" ]; then
  if [ "$#" -ge 2 ]; then
    echo "Mage Core não encontrado no caminho solicitado: $SDK"; exit 1
  fi
  SDK_PY="$HERE/r36s_a11y"
fi
[ -d "$SDK_PY" ] || { echo "Mage Core não encontrado."; exit 1; }
echo "Mage Core selecionado: $SDK_PY"

if ssh "$HOST" 'for p in /proc/[0-9]*; do readlink "$p/cwd"; done 2>/dev/null | grep -Eq "^/(roms|opt)/a11y/games/embers-of-yulan(/|$)"'; then
  echo "O Embers of Yulan está aberto no console. Feche o jogo e rode de novo."
  exit 1
fi

PKG=$(mktemp -d)
trap 'rm -rf "$PKG"' EXIT
mkdir -p "$PKG/embers-of-yulan"
cp -r "$HERE/game.json" "$HERE/main.py" "$HERE/yulan" "$HERE/sounds" "$HERE/images" "$SDK_PY" "$PKG/embers-of-yulan/"
find "$PKG" -name __pycache__ -prune -exec rm -rf {} +

tar -C "$PKG" -czf - embers-of-yulan | ssh "$HOST" '
  set -e; mkdir -p /roms/a11y/games; cd /roms/a11y/games
  rm -rf .embers.novo && mkdir .embers.novo
  tar -xzmf - -C .embers.novo
  rm -rf embers-of-yulan && mv .embers.novo/embers-of-yulan . && rmdir .embers.novo
  rm -rf /opt/a11y/games/embers-of-yulan
  echo "instalado: $(ls embers-of-yulan/sounds | wc -l) sons, $(ls embers-of-yulan/images | wc -l) imagens"; df -h /roms | tail -1'
