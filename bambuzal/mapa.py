"""O mapa: uma grade de casas, com o terreno de cada uma e a terra cultivável.

Hoje o jogador só anda pela fileira 0, de oeste a leste, mas o mapa já é uma grade
(x, y) com vizinhos nas quatro direções, para uma navegação em 2D no futuro. Quem
muda de casa é o mundo; aqui só se descreve e se sorteia o terreno.

Terrenos: campo, bambuzal, cascalho, margem. A terra cultivável é
um conjunto de casas de campo, à parte do terreno.
"""
import math

from . import config as C

# um caractere por terreno, para guardar o mapa no save
CODES = {"c": "campo", "z": "bambuzal", "r": "cascalho", "m": "margem",
         "b": "campo", "p": "campo"}     # base e paliçada (até a 0.5) viraram campo
KEYS = {"campo": "c", "bambuzal": "z", "cascalho": "r", "margem": "m"}


class Mapa:
    def __init__(self, rows, fertile=()):
        self.rows = [list(r) for r in rows]          # rows[y][x] = chave do terreno
        self.fertile = set(fertile)                  # {(x, y)}: terra boa para plantar

    @property
    def width(self):
        return len(self.rows[0])

    @property
    def height(self):
        return len(self.rows)

    @property
    def last_x(self):
        return self.width - 1

    @property
    def river_x(self):
        return self.last_x + 2          # o rio toca além da última casa

    def inside(self, x, y=0):
        return 0 <= y < self.height and 0 <= x < self.width

    def terrain(self, x, y=0):
        """A chave do terreno; fora do mapa, o da casa mais perto."""
        y = min(max(y, 0), self.height - 1)
        return self.rows[y][min(max(x, 0), self.width - 1)]

    def neighbors(self, x, y=0):
        return [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if self.inside(x + dx, y + dy)]

    def cells(self):
        return [(x, y) for y in range(self.height) for x in range(self.width)]

    def is_fertile(self, x, y=0):
        return (x, y) in self.fertile

    def nearest(self, key, x, y=0):
        """A casa de `key` mais perto de (x, y), ou None."""
        found = [(abs(cx - x) + abs(cy - y), cx, cy) for cx, cy in self.cells()
                 if self.rows[cy][cx] == key]
        if not found:
            return None
        _, cx, cy = min(found)
        return cx, cy

    def zones(self, y=0):
        """Trechos seguidos de um mesmo terreno na fileira y: [(chave, primeira, última)]."""
        out, row = [], self.rows[y]
        start = 0
        for x in range(1, len(row) + 1):
            if x == len(row) or row[x] != row[start]:
                out.append((row[start], start, x - 1))
                start = x
        return out

    # --- save ----------------------------------------------------------------------
    def to_dict(self):
        return {"rows": ["".join(KEYS[k] for k in r) for r in self.rows],
                "fertile": sorted([x, y] for x, y in self.fertile)}

    @classmethod
    def from_dict(cls, data):
        return cls([[CODES[c] for c in r] for r in data["rows"]],
                   [tuple(c) for c in data.get("fertile", [])])


def _blank(width, height):
    row = ["campo"] * (width - C.MARGEM_LENGTH) + ["margem"] * C.MARGEM_LENGTH
    return [list(row) for _ in range(height)]


def classic():
    """O mapa fixo das versões antigas (e dos testes): campo, bambuzal, cascalho, margem."""
    rows = _blank(38, 1)
    for x in range(14, 26):
        rows[0][x] = "bambuzal"
    for x in range(26, 34):
        rows[0][x] = "cascalho"
    return Mapa(rows)


def _scatter(rows, rng, key, count, radius, x_lo, x_hi, min_gap, centers):
    """Sorteia `count` focos de `key` e faz o terreno crescer em volta de cada um: no
    centro é certo, na borda vai rareando. Só ocupa casas de campo."""
    height = len(rows)
    made = []
    for _ in range(count):
        for _try in range(40):
            cx = rng.randint(x_lo, x_hi)
            cy = rng.randrange(height)
            if all(abs(cx - ox) + abs(cy - oy) >= min_gap for ox, oy in centers):
                break
        else:
            continue
        centers.append((cx, cy))
        made.append((cx, cy))
        r = rng.randint(*radius)
        for y in range(height):
            for x in range(max(0, cx - r), min(len(rows[0]), cx + r + 1)):
                if rows[y][x] != "campo":
                    continue
                d = math.hypot(x - cx, y - cy)
                if d <= r and rng.random() < 1.0 - (d / (r + 1.0)) ** 2:
                    rows[y][x] = key
    return made


def generate(rng, width=None, height=None):
    """Um mapa novo. A margem do rio fica sempre no fim; o resto é sorteado: focos
    de bambu espalhados (sempre um perto do começo), cascalho na
    metade de lá e retalhos de terra boa no campo."""
    width = width or C.MAP_WIDTH
    height = height or C.MAP_HEIGHT
    rows = _blank(width, height)
    first = C.ZONE_START
    last = width - 1 - C.MARGEM_LENGTH
    span = last - first
    centers = []
    # o primeiro foco de bambu fica perto, para o começo não ser uma caminhada
    near_lo = first + 8
    _scatter(rows, rng, "bambuzal", 1, C.BAMBOO_RADIUS, near_lo, near_lo + 8, 0, centers)
    _scatter(rows, rng, "bambuzal", rng.randint(*C.BAMBOO_ZONES) - 1, C.BAMBOO_RADIUS,
             first + 16, last - 4, 14, centers)
    _scatter(rows, rng, "cascalho", rng.randint(*C.GRAVEL_ZONES), C.GRAVEL_RADIUS,
             first + span // 2, last - 2, 10, centers)
    # cascalho garantido: se o sorteio deixou muito pouco, abre um trecho perto da margem
    if sum(r.count("cascalho") for r in rows) < 6:
        for x in range(last - 6, last - 1):
            rows[0][x] = "cascalho"
    mapa = Mapa(rows)
    _scatter_fertile(mapa, rng)
    return mapa


def _scatter_fertile(mapa, rng):
    count = rng.randint(*C.FERTILE_PATCHES)
    field = [(x, y) for x, y in mapa.cells() if mapa.rows[y][x] == "campo"]
    for _ in range(count):
        if not field:
            return
        x, y = rng.choice(field)
        for k in range(rng.randint(1, 3)):
            if mapa.inside(x + k, y) and mapa.rows[y][x + k] == "campo":
                mapa.fertile.add((x + k, y))
