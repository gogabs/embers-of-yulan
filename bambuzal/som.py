"""Onde um som do mapa toca: a única parte do jogo que sabe de estéreo.

O mundo só diz "toque isto na casa N". Aqui se decide como o ouvido percebe
a casa N: hoje, uma posição 3D à esquerda ou à direita do ouvinte.

Nada no jogo depende disso para ser jogável: tudo o que o estéreo mostra
também sai por outro caminho (A, L1 e R1 dizem o lado e a distância por voz,
e o som de mira avisa, no centro, quando você vira para um bicho). Para jogar
sem fone no futuro, basta trocar esta função.
"""
from . import config as C


def place(tile, listener):
    """Como tocar um som na casa `tile` com o ouvinte em `listener`.

    Devolve None se está longe demais para ouvir, ou um dict com pos (3D),
    volume e pitch (multiplicadores)."""
    d = tile - listener
    if abs(d) > C.HEAR_TILES:
        return None
    return {"pos": (d * C.TILE_METERS, 0.0, -0.6), "volume": 1.0, "pitch": 1.0}
