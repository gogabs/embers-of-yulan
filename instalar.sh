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

if ssh "$HOST" 'for p in /proc/[0-9]*; do readlink "$p/cwd"; done 2>/dev/null | grep -Eq "^/(roms|opt)/a11y/games/bambuzal(/|$)"'; then
  echo "O Bambuzal está aberto no console. Feche o jogo e rode de novo."
  exit 1
fi

PKG=$(mktemp -d)
trap 'rm -rf "$PKG"' EXIT
mkdir -p "$PKG/bambuzal"
cp -r "$HERE/game.json" "$HERE/main.py" "$HERE/bambuzal" "$HERE/sounds" "$HERE/images" "$SDK_PY" "$PKG/bambuzal/"
find "$PKG" -name __pycache__ -prune -exec rm -rf {} +

tar -C "$PKG" -czf - bambuzal | ssh "$HOST" '
  set -e; mkdir -p /roms/a11y/games; cd /roms/a11y/games
  rm -rf .bambuzal.novo && mkdir .bambuzal.novo
  tar -xzmf - -C .bambuzal.novo
  rm -rf bambuzal && mv .bambuzal.novo/bambuzal . && rmdir .bambuzal.novo
  rm -rf /opt/a11y/games/bambuzal
  echo "instalado: $(ls bambuzal/sounds | wc -l) sons, $(ls bambuzal/images | wc -l) imagens"; df -h /roms | tail -1'
