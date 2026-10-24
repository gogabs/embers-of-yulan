"""O que existe no mundo: terrenos, itens e o que se acha em cada lugar."""
from . import config as C

# --- terrenos ------------------------------------------------------------------
# chave: (nome falado, som dos passos). Onde cada um fica quem diz é o mapa (mapa.py).
TERRAIN_INFO = {
    "campo": ("Campo", "passo_campo"),
    "bambuzal": ("Bambuzal", "passo_bambu"),
    "cascalho": ("Cascalho", "passo_cascalho"),
    "margem": ("Margem do rio", "passo_margem"),
}


def terrain_name(key):
    return TERRAIN_INFO[key][0]


def step_sound(key):
    return TERRAIN_INFO[key][1]


# --- itens ---------------------------------------------------------------------
# chave: (singular, plural, gênero, saciedade ao comer ou None, horas até estragar ou None)
ITEMS = {
    "bambu": ("bambu", "bambus", "m", None, None),
    "cipo": ("cipó", "cipós", "m", None, None),
    "pedra": ("pedra", "pedras", "f", None, None),
    "argila": ("torrão de argila", "torrões de argila", "m", None, None),
    "fruta": ("fruta silvestre", "frutas silvestres", "f", 12, 24),
    "broto": ("broto de bambu", "brotos de bambu", "m", 16, 36),
    "carne": ("carne crua", "carnes cruas", "f", 6, 14),
    "assado": ("carne assada", "carnes assadas", "f", 35, 48),
    "nabo": ("nabo", "nabos", "m", 18, 60),
    "hortela": ("hortelã", "hortelãs", "f", None, 60),
    "artemisia": ("artemísia", "artemísias", "f", None, 72),
    "lenha": ("lenha", "lenhas", "f", None, None),
    "gengibre": ("raiz de gengibre", "raízes de gengibre", "f", None, 60),
    "semente": ("semente de nabo", "sementes de nabo", "f", None, None),
    "resto": ("resto de comida", "restos de comida", "m", None, None),
    "adubo": ("adubo", "adubos", "m", None, None),
}
ITEM_ORDER = ("assado", "nabo", "broto", "fruta", "carne", "hortela", "gengibre", "artemisia", "semente",
              "adubo", "resto", "lenha", "bambu", "cipo", "pedra", "argila")
FOODS = tuple(k for k in ITEM_ORDER if ITEMS[k][3] is not None)
LEAVES_SCRAP = ("fruta", "broto", "nabo")     # comer isto deixa um resto
PERISHABLE = tuple(k for k in ITEM_ORDER if ITEMS[k][4] is not None)

# O que cada terreno dá numa busca: (item, peso).
SEARCH = {
    "campo": (("lenha", 42), ("fruta", 22), ("cipo", 10), ("pedra", 8), ("hortela", 8),
              ("semente", 7), ("artemisia", 4)),
    "bambuzal": (("bambu", 40), ("broto", 20), ("cipo", 16), ("gengibre", 24)),
    "cascalho": (("pedra", 80), ("artemisia", 20)),
    "margem": (("argila", 60), ("pedra", 12), ("hortela", 18), ("artemisia", 10)),
}

# --- receitas da base -----------------------------------------------------------
STAKE_COST = {"bambu": 2}
FIRE_COST = {"lenha": 4, "pedra": 2}
FEED_COST = {"lenha": 4}
SPEAR_COST = {"bambu": 2, "pedra": 1, "cipo": 1}
POT_COST = {"argila": 3}
COMPOST_COST = {"resto": 3}
HORTELA_COST = {"hortela": 2}
GENGIBRE_COST = {"gengibre": 2}


def name(key, n=1):
    singular, plural = ITEMS[key][0], ITEMS[key][1]
    return singular if n == 1 else plural


def count(key, n):
    """'1 bambu', '3 bambus', 'uma pedra'... com o número sempre em algarismo."""
    return "%d %s" % (n, name(key, n))


def cost_text(cost):
    parts = [count(k, n) for k, n in cost.items()]
    return join(parts)


def join(parts):
    parts = list(parts)
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " e " + parts[-1]


def direction(delta):
    return "a leste" if delta > 0 else "a oeste"


def distance(delta):
    d = abs(delta)
    if d == 0:
        return "aqui"
    return "a %d %s %s" % (d, "casa" if d == 1 else "casas", direction(delta))


# Uma dica, dita só na primeira vez que se acha o item.
HINTS = {
    "hortela": "Hortelã dá chá, no acampamento, com a fogueira acesa.",
    "gengibre": "Gengibre dá chá, no acampamento, com a fogueira acesa.",
    "artemisia": "Artemísia jogada na fogueira solta a fumaça que espanta os jiangshi.",
    "lenha": "Lenha só serve para a fogueira, e é preciso bastante: 4 lenhas por vez. A mochila "
             "guarda muita.",
    "semente": "Plante em terra boa: abra a mochila e escolha a semente.",
    "resto": "Com 3 restos de comida você faz adubo no acampamento.",
}
