"""Gráficos opcionais: a faixa de terra vista de lado, com a câmera na heroína.

Nada aqui é necessário para jogar: tudo o que aparece na tela também é falado
(regra do contrato da plataforma). A legenda embaixo é sempre a última fala.
A tela segue a opção do sistema (SCREEN=0 desliga) e a economia de energia.

`draw_frame(gfx, art, scene)` só lê o estado do mundo e só usa a API de
desenho do Mage Core, então roda no console, nos testes e no gerador de
prévias (tools/previas.py). Personagens são PNG feitos de SVG (art/); o
cenário é desenhado com formas, quadro a quadro.
"""
import math
import os
import time

from . import config as C
from . import data as D

W, H = 640, 480
TILE_W = 64
GROUND_Y = 352          # onde os pés pisam
TOP_BAR = 34
CAPTION_Y = 404

INK = "#3a2228"
TEXT = "#fff8ec"
TEXT_DIM = "#e8d8c0"
FOCUS = "#ffd34d"
PANEL = (34, 22, 26, 235)
HEALTH = "#e5484d"
FOOD = "#f0a030"
WALL = "#9cc45a"

GROUND = {"campo": ("#7cbf5a", "#5f9c45"), "bambuzal": ("#5f9a4a", "#4a7d3a"),
          "cascalho": ("#a7a196", "#8a857b"), "margem": ("#8a6f52", "#6e5640")}
SOIL = ("#6a4a30", "#563a26")
RIVER = ("#4aa3c8", "#2f7fa3")

# Céu por hora: (hora, cor de cima, cor de baixo); entre duas, mistura.
SKY = ((0, "#0d1030", "#1f2350"), (5, "#1a1d48", "#5a4a78"), (6, "#f6a58a", "#ffd9a0"),
       (8, "#7fc4ee", "#d3efff"), (16, "#7fc4ee", "#d3efff"), (18, "#f08a5d", "#ffcf87"),
       (19, "#5a3a78", "#c0607a"), (20, "#141842", "#2a2c5c"), (24, "#0d1030", "#1f2350"))


def mix(a, b, t):
    a, b = a.lstrip("#"), b.lstrip("#")
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return tuple(int(x + (y - x) * t) for x, y in zip(ca, cb))


def sky_colors(hours):
    h = hours % 24
    for (h0, t0, b0), (h1, t1, b1) in zip(SKY, SKY[1:]):
        if h0 <= h < h1:
            t = (h - h0) / float(h1 - h0)
            return mix(t0, t1, t), mix(b0, b1, t)
    return mix(SKY[0][1], SKY[0][1], 0), mix(SKY[0][2], SKY[0][2], 0)


def darkness(hours):
    """Quanto escurecer o chão e os bichos: 0 de dia, até 0.55 de madrugada."""
    h = hours % 24
    if 7 <= h < 17:
        return 0.0
    if 17 <= h < 20:
        return 0.55 * (h - 17) / 3.0
    if 4 <= h < 7:
        return 0.55 * (7 - h) / 3.0
    return 0.55


def rnd(*key):
    """Número fixo de 0 a 1 para cada casa, para os enfeites não tremerem."""
    x = 0
    for k in key:
        x = (x * 1103515245 + int(k) * 2654435761 + 12345) & 0x7FFFFFFF
    return (x % 10007) / 10007.0


class Art:
    """Os PNG dos personagens, carregados uma vez."""
    NAMES = ("heroina_parada", "heroina_passo_a", "heroina_passo_b", "heroina_golpe",
             "heroina_piscando", "heroina_firme", "javali_0", "javali_1", "jiangshi")

    def __init__(self, gfx):
        self.img = {n: gfx.image("images/%s.png" % n) for n in self.NAMES}
        self.small = gfx.font(None, 18)
        self.normal = gfx.font(None, 21)
        self.big = gfx.font(None, 25)


class Scene:
    """O que desenhar: o mundo (ou nada, no menu principal), o menu aberto,
    a legenda e o tempo, mais o estado da animação que a tela guarda."""

    def __init__(self, world=None, menu=None, caption="", t=0.0):
        self.world, self.menu, self.caption, self.t = world, menu, caption, t
        self.cam = None
        self.walk_t = 0.0


# --- formas ------------------------------------------------------------------------
_fit_cache = {}


def fit(gfx, text, font, width):
    key = (text, id(font), width)
    if key in _fit_cache:
        return _fit_cache[key]
    out = text
    if gfx.measure(text, font)[0] > width:
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if gfx.measure(text[:mid] + "…", font)[0] <= width:
                lo = mid
            else:
                hi = mid - 1
        out = text[:lo].rstrip() + "…"
    if len(_fit_cache) > 500:
        _fit_cache.clear()
    _fit_cache[key] = out
    return out


def wrap(gfx, text, font, width, lines):
    """Quebra em até `lines` linhas; se não couber, mostra o fim (a fala mais nova)."""
    key = ("wrap", text, id(font), width, lines)
    if key in _fit_cache:
        return _fit_cache[key]
    rows, row = [], ""
    for word in text.split():
        test = (row + " " + word).strip()
        if row and gfx.measure(test, font)[0] > width:
            rows.append(row)
            row = word
        else:
            row = test
    if row:
        rows.append(row)
    if len(rows) > lines:
        rows = rows[-lines:]
        rows[0] = "…" + rows[0]
    _fit_cache[key] = rows
    return rows


def bar(gfx, x, y, w, h, frac, color, label, font):
    gfx.rect(x - 2, y - 2, w + 4, h + 4, INK)
    gfx.rect(x, y, w, h, "#4a3438")
    filled = int(w * max(0.0, min(1.0, frac)))
    if filled > 0:
        gfx.rect(x, y, filled, h, color)
    gfx.text(label, x + w // 2, y - 1, font=font, color=TEXT, align="center")


# --- cenário --------------------------------------------------------------------------
def tile_x(tile, cam):
    return W / 2 + (tile - cam) * TILE_W


def draw_sky(gfx, w, t):
    top, bottom = sky_colors(w.hours)
    bands = 12
    for k in range(bands):
        c = mix("#%02x%02x%02x" % top, "#%02x%02x%02x" % bottom, k / (bands - 1.0))
        y0 = TOP_BAR + (GROUND_Y - TOP_BAR) * k // bands
        y1 = TOP_BAR + (GROUND_Y - TOP_BAR) * (k + 1) // bands
        gfx.rect(0, y0, W, y1 - y0 + 1, c)
    h = w.hours % 24
    if 6 <= h < 19:     # sol atravessa da esquerda para a direita
        f = (h - 6) / 13.0
        gfx.circle(40 + f * 560, 200 - math.sin(f * math.pi) * 140, 22, "#fff3b0")
    else:               # lua com estrelas
        f = ((h - 19) % 24) / 11.0
        for k in range(28):
            sx, sy = rnd(k, 1) * W, TOP_BAR + rnd(k, 2) * 180
            if math.sin(t * 2 + k) > -0.6:
                gfx.rect(sx, sy, 2, 2, "#e8ecff")
        mx, my = 40 + f * 560, 200 - math.sin(f * math.pi) * 140
        if w.climate == "lua":          # lua cheia: disco inteiro, maior, com um halo
            for r in range(70, 24, -9):
                gfx.circle(mx, my, r, (255, 246, 210, 14))
            gfx.circle(mx, my, 26, "#fff7d8")
            gfx.circle(mx - 8, my - 5, 5, "#e8e0b8")
            gfx.circle(mx + 9, my + 7, 4, "#e8e0b8")
        else:
            gfx.circle(mx, my, 18, "#f2efd8")
            gfx.circle(mx + 7, my - 4, 15, "#%02x%02x%02x" % top)


def draw_mountains(gfx, w, cam):
    dark = darkness(w.hours)
    far = mix("#9bb7cf", "#2a3058", dark / 0.55)
    near = mix("#7f9fb9", "#202648", dark / 0.55)
    off = -(cam * TILE_W * 0.15) % 320
    for k in range(-1, 4):
        x = k * 320 + off
        gfx.polygon([(x - 40, GROUND_Y), (x + 60, 170), (x + 110, 210), (x + 170, 140),
                     (x + 260, GROUND_Y)], far)
        # pagode pequeno num dos picos
        if k % 2 == 0:
            px, py = x + 170, 140
            for level in range(3):
                ww = 22 - level * 5
                yy = py - 6 - level * 9
                gfx.polygon([(px - ww, yy + 4), (px + ww, yy + 4), (px + ww - 6, yy),
                             (px - ww + 6, yy)], near)
                gfx.rect(px - ww + 8, yy + 4, (ww - 8) * 2, 5, near)
    off2 = -(cam * TILE_W * 0.3) % 240
    for k in range(-1, 4):
        x = k * 240 + off2
        gfx.polygon([(x - 30, GROUND_Y), (x + 50, 240), (x + 100, 270), (x + 150, 230),
                     (x + 230, GROUND_Y)], near)


def draw_ground(gfx, w, cam, t):
    first = int(math.floor(cam - W / 2.0 / TILE_W)) - 1
    for tile in range(first, first + W // TILE_W + 3):
        x = tile_x(tile, cam) - TILE_W / 2
        if tile < 0:
            gfx.rect(x, GROUND_Y - 4, TILE_W + 1, CAPTION_Y - GROUND_Y + 4, "#5a4632")
            continue
        if tile > w.map.last_x:
            draw_water(gfx, x, t, tile)
            continue
        key = w.map.terrain(tile, w.y)
        top, low = GROUND[key]
        fertile = w.map.is_fertile(tile, w.y)
        if fertile:
            top, low = SOIL
        gfx.rect(x, GROUND_Y - 4, TILE_W + 1, 10, top)
        gfx.rect(x, GROUND_Y + 6, TILE_W + 1, CAPTION_Y - GROUND_Y - 6, low)
        if fertile:
            draw_furrows(gfx, w, tile, x, t)
        else:
            draw_detail(gfx, key, tile, x, t)


def draw_furrows(gfx, w, tile, x, t):
    """Terra boa: sulcos escuros, e a plantação em seu estágio, se houver."""
    for k in range(3):
        gfx.rect(x + 4, GROUND_Y - 2 + k * 5, TILE_W - 8, 2, "#4a3020")
    plot = w.plots.get((tile, w.y))
    if plot is None:
        return
    cx = x + TILE_W / 2.0
    frac = 1.0 if plot["ready"] else min(1.0, plot["hours"] / float(C.CROP_HOURS))
    leaf = 8 + 24 * frac
    sway = math.sin(t * 1.5 + tile) * 2
    for side in (-1, 0, 1):
        gfx.polygon([(cx + side * 8 - 4, GROUND_Y - 2), (cx + side * 8 + sway, GROUND_Y - 2 - leaf),
                     (cx + side * 8 + 4, GROUND_Y - 2)], "#5faa3a")
    if plot["ready"]:
        for side in (-1, 0, 1):
            gfx.circle(cx + side * 12, GROUND_Y + 2, 5, "#f4ecd8")
    if plot["weeds"]:
        for k in range(4):
            gx = x + 8 + k * 14
            gfx.polygon([(gx - 4, GROUND_Y - 2), (gx + 2, GROUND_Y - 16 - 3 * k % 5),
                         (gx + 6, GROUND_Y - 2)], "#8a8a2a")


def draw_water(gfx, x, t, tile):
    gfx.rect(x, GROUND_Y + 8, TILE_W + 1, CAPTION_Y - GROUND_Y, RIVER[1])
    gfx.rect(x, GROUND_Y + 8, TILE_W + 1, 6, RIVER[0])
    for k in range(3):
        wx = x + ((t * 30 + k * 23 + tile * 17) % TILE_W)
        gfx.line(wx, GROUND_Y + 22 + k * 12, wx + 10, GROUND_Y + 22 + k * 12, "#a8dcf0", 2)


def draw_detail(gfx, key, tile, x, t):
    if key == "campo":
        for k in range(3):
            gx = x + 6 + rnd(tile, k) * (TILE_W - 12)
            gfx.polygon([(gx - 5, GROUND_Y), (gx, GROUND_Y - 12 - 4 * rnd(tile, k, 3)),
                         (gx + 5, GROUND_Y)], "#4f8f3a")
        if rnd(tile, 9) > 0.5:
            fx = x + 10 + rnd(tile, 7) * (TILE_W - 20)
            gfx.circle(fx, GROUND_Y - 10, 4, "#f6e05e" if rnd(tile, 8) > 0.5 else "#f28fb0")
    elif key == "bambuzal":
        for k in range(2):
            bx = x + 10 + rnd(tile, k) * (TILE_W - 20)
            top = 70 + rnd(tile, k, 5) * 60
            sway = math.sin(t * 0.8 + tile + k) * 3
            gfx.line(bx, GROUND_Y, bx + sway, top, INK, 9)
            gfx.line(bx, GROUND_Y, bx + sway, top, "#7fb24a", 6)
            node = GROUND_Y - 40
            while node > top + 10:
                f = (GROUND_Y - node) / float(GROUND_Y - top)
                gfx.line(bx + sway * f - 4, node, bx + sway * f + 4, node, "#4f7a2a", 2)
                node -= 46
            for side in (-1, 1):
                ly = top + 18 + 30 * rnd(tile, k, side)
                lx = bx + sway * (GROUND_Y - ly) / float(GROUND_Y - top)
                gfx.polygon([(lx, ly), (lx + side * 26, ly - 6), (lx + side * 12, ly + 3)],
                            "#5f9a3a")
    elif key == "cascalho":
        for k in range(4):
            sx = x + 6 + rnd(tile, k) * (TILE_W - 12)
            r = 3 + 4 * rnd(tile, k, 2)
            gfx.circle(sx, GROUND_Y + 2 - r / 2, r, "#c4beb2" if k % 2 else "#8f897e")
    elif key == "margem":
        for k in range(2):
            rx = x + 8 + rnd(tile, k) * (TILE_W - 16)
            gfx.line(rx, GROUND_Y, rx - 3, GROUND_Y - 28 - 10 * rnd(tile, k, 4), "#6f8a3a", 3)
            gfx.circle(rx - 3, GROUND_Y - 30 - 10 * rnd(tile, k, 4), 3, "#8a5a34")


def draw_camp(gfx, w, cam, t):
    """O acampamento: uma tenda de lona, o cesto, os potes e a fogueira, com a fumaça
    das ervas subindo quando ela espanta os jiangshi."""
    fx = tile_x(w.camp, cam)
    if not -160 < fx < W + 160:
        return
    # tenda de lona, à esquerda da fogueira
    tx = fx - 64
    gfx.polygon([(tx - 36, GROUND_Y + 2), (tx, GROUND_Y - 62), (tx + 36, GROUND_Y + 2)], "#d9c9a0")
    gfx.polygon([(tx - 4, GROUND_Y + 2), (tx, GROUND_Y - 30), (tx + 14, GROUND_Y + 2)], "#5a4030")
    gfx.line(tx - 36, GROUND_Y + 2, tx, GROUND_Y - 62, INK, 3)
    gfx.line(tx + 36, GROUND_Y + 2, tx, GROUND_Y - 62, INK, 3)
    # cesto e potes de argila guardados
    gfx.circle(fx + 40, GROUND_Y - 4, 10, "#a8793a")
    gfx.rect(fx + 31, GROUND_Y - 14, 18, 4, "#7a5428")
    for k in range(min(w.pots, 3)):
        px = fx + 64 + k * 14
        gfx.circle(px, GROUND_Y - 8, 7, "#b5653a")
        gfx.rect(px - 4, GROUND_Y - 18, 8, 4, "#8a4a2a")
    # fogueira
    for k in (-1, 1):
        gfx.line(fx - 14 * k, GROUND_Y + 2, fx + 10 * k, GROUND_Y - 6, "#6b4128", 5)
    for k in range(5):
        gfx.circle(fx - 16 + k * 8, GROUND_Y + 2, 4, "#8f897e")
    if w.fire_hours > 0:
        for k, (dx, hh, c) in enumerate(((-6, 22, "#ff8a2a"), (5, 28, "#ffb340"),
                                         (0, 16, "#fff1a0"))):
            fl = hh + 5 * math.sin(t * 9 + k * 2)
            gfx.polygon([(fx + dx - 8, GROUND_Y - 2), (fx + dx, GROUND_Y - 2 - fl),
                         (fx + dx + 8, GROUND_Y - 2)], c)
    if w.smoke_on:
        # a fumaça de erva sobe em ondas e se abre no alto
        for k in range(9):
            rise = (t * 0.6 + k / 9.0) % 1.0
            sx = fx + math.sin(t * 1.3 + k * 1.7) * 14 * rise
            gfx.circle(sx, GROUND_Y - 36 - rise * 120, 6 + 14 * rise,
                       (190, 214, 170, int(110 * (1 - rise))))


def draw_traps(gfx, w, cam):
    for tile, trap in w.traps.items():
        x = tile_x(tile, cam)
        if not -40 < x < W + 40:
            continue
        if trap["kind"] == "estaca":
            for k in range(trap["uses"]):
                sx = x - 12 + k * 12
                gfx.polygon([(sx - 4, GROUND_Y + 2), (sx, GROUND_Y - 24), (sx + 4, GROUND_Y + 2)],
                            "#c8b070")
                gfx.line(sx, GROUND_Y - 24, sx, GROUND_Y + 2, INK, 1)
        else:
            gfx.circle(x, GROUND_Y + 4, 20, "#2a1c14")
            gfx.circle(x, GROUND_Y + 2, 14, "#150d09")


DROP_COLORS = {"fruta": "#e8454a", "broto": "#c8d870", "carne": "#d9606a", "assado": "#a8582a",
               "bambu": "#9cc45a", "cipo": "#4f8a3a", "pedra": "#9aa3a8", "argila": "#b5653a",
               "nabo": "#f4ecd8", "lenha": "#8a5a30", "artemisia": "#9ab88a", "hortela": "#6fd08a", "gengibre": "#d9b86a",
               "semente": "#c8a46a", "resto": "#7a6a4a", "adubo": "#5a4030"}


def draw_drops(gfx, w, cam):
    for tile, pile in w.drops.items():
        x = tile_x(tile, cam)
        if -40 < x < W + 40:
            for k, key in enumerate(pile):
                gfx.circle(x - 8 + k * 10, GROUND_Y - 6, 7, INK)
                gfx.circle(x - 8 + k * 10, GROUND_Y - 6, 5, DROP_COLORS.get(key, TEXT))


def draw_creatures(gfx, art, w, cam, t):
    # com o escuro por baixo deles, os bichos só escurecem um pouco
    shade = int(255 * (1 - darkness(w.hours) * 0.3))
    tint = (shade, shade, min(255, shade + 20))
    for b in w.boars:
        x = tile_x(b.tile, cam)
        img = art.img["javali_%d" % (int(t * (8 if b.charging else 3)) % 2)]
        flip = w.x < b.tile         # o javali olha para a heroína
        gfx.draw(img, x - img.width / 2, GROUND_Y - img.height + 4, flip_x=flip, tint=tint)
    for j in w.jiangshi:
        x = tile_x(j.tile, cam)
        img = art.img["jiangshi"]
        hop = abs(math.sin((t / C.JIANGSHI_HOP_SECONDS) * math.pi)) * 18
        flip = w.x < j.tile
        gfx.draw(img, x - img.width / 2, GROUND_Y - img.height + 2 - hop, flip_x=flip, tint=tint)


def hero_frame(scene, w, t):
    if w.attack_in > C.ATTACK_COOLDOWN - 0.25:
        return "heroina_golpe"
    if w.held:
        return "heroina_passo_a" if int(t * 6) % 2 == 0 else "heroina_passo_b"
    # serena no dia a dia; firme com um bicho perto
    if any(abs(e.tile - w.x) <= 4 for e in w.boars + w.jiangshi):
        return "heroina_firme"
    if t % 3.5 < 0.15:
        return "heroina_piscando"
    return "heroina_parada"


def draw_hero(gfx, art, scene, w, cam, t):
    img = art.img[hero_frame(scene, w, t)]
    x = tile_x(w.x, cam)
    if w.searching is not None or w.task is not None:   # agachada procurando ou cortando: um pouco mais baixa
        y = GROUND_Y - img.height + 10
    else:
        y = GROUND_Y - img.height + 4
    gfx.draw(img, x - img.width / 2, y, flip_x=w.facing < 0)


def draw_night(gfx, w):
    d = darkness(w.hours)
    if d > 0:
        gfx.rect(0, TOP_BAR, W, CAPTION_Y - TOP_BAR, (10, 12, 40, int(255 * d * 0.7)))


def draw_lantern(gfx, w, cam, t):
    d = darkness(w.hours)
    if d <= 0:
        return
    x = tile_x(w.x, cam)
    flicker = 1.0 + 0.06 * math.sin(t * 7.0) + 0.04 * math.sin(t * 13.0)
    for radius in range(120, 20, -10):      # muitos círculos fracos: o brilho sai sem degraus
        gfx.circle(x, GROUND_Y - 44, radius * flicker, (255, 196, 110, int(7 * d / 0.55)))


def draw_fog(gfx, w, t):
    if w.climate != "neblina":
        return
    for k in range(9):
        x = (k * 90 + t * 12 * (1 + k % 3) + rnd(k, 3) * 200) % (W + 200) - 100
        gfx.circle(x, GROUND_Y - 20 - 18 * (k % 3), 95, (222, 230, 238, 20))
    gfx.rect(0, GROUND_Y - 70, W, CAPTION_Y - GROUND_Y + 70, (220, 228, 236, 28))


def draw_rain(gfx, w, t):
    if w.climate != "chuva":
        return
    span = CAPTION_Y - TOP_BAR
    for k in range(70):
        x = (rnd(k, 1) * W + t * 70) % W
        y = TOP_BAR + (rnd(k, 2) * span + t * 520) % span
        gfx.line(x, y, x - 5, y + 16, (190, 212, 238, 150), 1)


def draw_top(gfx, art, w):
    gfx.rect(0, 0, W, TOP_BAR, PANEL)
    gfx.text("Dia %d  %s" % (w.day, w.phase), 12, 6, font=art.normal, color=FOCUS)
    bar(gfx, 150, 10, 130, 16, w.health / float(C.MAX_HEALTH), HEALTH,
        "Vida %d" % w.health, art.small)
    bar(gfx, 300, 10, 130, 16, w.fullness / 100.0, FOOD, "Saciedade %d" % int(w.fullness), art.small)
    bar(gfx, 450, 10, 130, 16, w.smoke / float(C.SMOKE_MAX), WALL,
        "Fumaça %dh" % int(w.smoke + 0.999), art.small)
    gfx.text("%d/%d" % (w.bag_count(), C.CARRY_LIMIT), 628, 6, font=art.small, color=TEXT_DIM,
             align="right")


def draw_caption(gfx, art, caption):
    gfx.rect(0, CAPTION_Y, W, H - CAPTION_Y, PANEL)
    for k, line in enumerate(wrap(gfx, caption, art.normal, W - 28, 3)):
        gfx.text(line, 14, CAPTION_Y + 6 + k * 23, font=art.normal, color=TEXT)


def draw_menu(gfx, art, menu, top=56, bottom=396):
    x, w = 48, W - 96
    bottom = min(bottom, top + 58 + 30 * len(menu.items))
    rows = max(3, (bottom - top - 50) // 30)
    gfx.rect(x - 3, top - 3, w + 6, bottom - top + 6, INK)
    gfx.rect(x, top, w, bottom - top, PANEL)
    gfx.text(fit(gfx, menu.title, art.big, w - 24), x + 12, top + 10, font=art.big, color=FOCUS)
    first = max(0, min(menu.index - rows // 2, len(menu.items) - rows))
    for k, item in enumerate(menu.items[first:first + rows]):
        i = first + k
        y = top + 46 + k * 30
        color = TEXT
        if i == menu.index:
            gfx.rect(x + 6, y - 3, w - 12, 28, FOCUS)
            color = INK
        gfx.text(fit(gfx, item, art.normal, w - 30), x + 14, y, font=art.normal, color=color)


def draw_title(gfx, art, scene):
    """Menu principal: o bambuzal ao entardecer, com a heroína olhando o rio."""
    class Fake:
        hours = 17.6
        x = 18
    w = Fake()
    draw_sky(gfx, w, scene.t)
    draw_mountains(gfx, w, 18)
    gfx.rect(0, GROUND_Y - 4, W, CAPTION_Y - GROUND_Y + 4, "#4a7d3a")
    gfx.rect(0, GROUND_Y - 4, W, 10, "#5f9a4a")
    for tile in range(12, 26):
        draw_detail(gfx, "bambuzal", tile, tile_x(tile, 18) - TILE_W / 2, scene.t)
    img = art.img["heroina_parada"]
    gfx.draw(img, W / 2 - img.width / 2, GROUND_Y - img.height + 4)
    gfx.rect(150, 60, 340, 56, PANEL)
    gfx.text("Embers of Yulan", W / 2, 70, font=art.big, color=FOCUS, align="center")


def draw_frame(gfx, art, scene):
    gfx.clear("#000000")
    w = scene.world
    if w is None:
        draw_title(gfx, art, scene)
    else:
        if scene.cam is None:
            scene.cam = float(w.x)
        cam = scene.cam
        draw_sky(gfx, w, scene.t)
        draw_mountains(gfx, w, cam)
        draw_ground(gfx, w, cam, scene.t)
        draw_traps(gfx, w, cam)
        draw_camp(gfx, w, cam, scene.t)
        draw_drops(gfx, w, cam)
        # O escuro cobre o cenário; a heroína e os bichos vêm por cima, e a lanterna
        # dela acende um círculo quente em volta, para nunca sumir no escuro.
        draw_night(gfx, w)
        draw_lantern(gfx, w, cam, scene.t)
        draw_fog(gfx, w, scene.t)
        draw_creatures(gfx, art, w, cam, scene.t)
        draw_hero(gfx, art, scene, w, cam, scene.t)
        draw_rain(gfx, w, scene.t)
        draw_top(gfx, art, w)
    if scene.menu is not None:
        draw_menu(gfx, art, scene.menu)
    draw_caption(gfx, art, scene.caption)


def follow(scene, dt):
    """A câmera anda atrás da heroína, sem pular de casa em casa."""
    w = scene.world
    if w is None:
        scene.cam = None
        return
    if scene.cam is None:
        scene.cam = float(w.x)
    scene.cam += (w.x - scene.cam) * min(1.0, dt * 8)


# --- ligação com o jogo ------------------------------------------------------------------
def read_setting(key):
    try:
        with open(os.environ.get("A11Y_SISTEMA_CONF", "/opt/a11y/etc/sistema.conf")) as f:
            for line in f:
                k, sep, value = line.strip().partition("=")
                if sep and k == key:
                    return value.strip("'\"")
    except OSError:
        pass
    return None


def screen_on():
    if os.environ.get("A11Y_GRAPHICS") == "0":
        return False
    return read_setting("SCREEN") != "0"


def frame_interval():
    """20 quadros por segundo; menos na economia de energia."""
    return {"moderate": 0.1, "aggressive": 0.2}.get(read_setting("ENERGY"), 1 / 20.0)


class Renderer:
    """Desenha em on_update, no ritmo de frame_interval. Uma falha de vídeo só
    desliga os gráficos: o jogo segue pelo som."""

    def __init__(self, game, get_world, graphics=None):
        self.game = game
        self.get_world = get_world
        self.graphics = graphics          # para os testes: fábrica de gráficos
        self.caption = ""
        self._say = game.say
        game.say = self.say               # a legenda é sempre a última fala
        self.gfx = None
        self.art = None
        self.failed = False
        self.enabled = False
        self.interval = frame_interval()
        self.due = 0.0
        self.checked = -1.0
        self.started = time.monotonic()
        self.scene = Scene()
        self.last_draw = None
        if graphics is None and getattr(game, "pc", False):
            # No PC o Mage já tem uma janela (é dela que vem o teclado) e desenha a
            # legenda nela a cada quadro. Uma segunda janela ficaria escondida atrás
            # da legenda: o jogo desenha na janela do Mage, pelo on_draw.
            game.on_draw(self.draw_pc)
        else:
            game.on_update(self.update)
            game.on_quit(self.close)

    def say(self, text, queue=False, on_done=None):
        self.caption = (self.caption + " " + text) if queue and self.caption else text
        self.caption = self.caption[-400:]
        return self._say(text, queue=queue, on_done=on_done)

    def open(self):
        if self.graphics is not None:
            gfx = self.graphics()
        else:
            from r36s_a11y.graphics import Graphics
            gfx = Graphics("Embers of Yulan", self.game.dir)
        if not gfx.open():
            self.failed = True
            return False
        self.gfx = gfx
        self.art = Art(gfx)
        return True

    def close(self):
        if self.gfx is not None and self.gfx.available:
            self.gfx.close()
        self.gfx = None

    def update(self, dt):
        now = time.monotonic()
        if now - self.checked >= 0.5:
            self.checked = now
            self.enabled = screen_on()
            self.interval = frame_interval()
            if not self.enabled:
                self.close()
        if not self.enabled or self.failed:
            return
        self.scene.world = self.get_world()
        follow(self.scene, dt)
        self.due += dt
        if self.due < self.interval:
            return
        self.due = 0.0
        try:
            if self.gfx is None and not self.open():
                return
            self.gfx.begin()
            self.draw(self.gfx, now)
            self.gfx.end()
        except Exception as exc:   # gráfico com defeito não pode derrubar o jogo
            print("[bambuzal] gráficos desligados: %s" % exc)
            self.failed = True
            self.close()

    def draw(self, gfx, now):
        focus = getattr(self.game, "_focus", [])
        self.scene.menu = focus[-1] if focus else None
        self.scene.caption = self.caption
        self.scene.t = now - self.started
        draw_frame(gfx, self.art, self.scene)

    def draw_pc(self, gfx):
        """Um quadro na janela do PC. Com A11Y_GRAPHICS=0 ou depois de uma falha,
        fica a legenda simples do Mage."""
        now = time.monotonic()
        dt = 0.0 if self.last_draw is None else now - self.last_draw
        self.last_draw = now
        if now - self.checked >= 0.5:
            self.checked = now
            self.enabled = screen_on()
        if not self.enabled or self.failed:
            self.game._draw_caption(gfx)
            return
        self.scene.world = self.get_world()
        follow(self.scene, dt)
        try:
            if self.art is None:
                self.art = Art(gfx)
            self.draw(gfx, now)
        except Exception as exc:   # gráfico com defeito não pode derrubar o jogo
            print("[bambuzal] gráficos desligados: %s" % exc)
            self.failed = True
            self.game._draw_caption(gfx)
