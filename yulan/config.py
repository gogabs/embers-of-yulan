"""Números do equilíbrio do jogo, num lugar só.

Tempos em segundos reais. Uma hora do jogo dura HOUR_SECONDS; o resto do
relógio (fome, comida estragando, fogueira) conta em horas do jogo.
"""

# --- relógio -------------------------------------------------------------------
HOUR_SECONDS = 30.0           # 30 segundos reais = 1 hora (um dia dura 12 minutos)
START_HOUR = 7
DUSK_WARNING_HOUR = 17        # "o sol está baixando"
NIGHT_START = 19              # escurece; os jiangshi começam a sair depois
NIGHT_END = 6                 # amanhece; os jiangshi que sobraram somem
# O jogo não diz a hora, só a fase do dia: (hora em que começa, nome).
PHASES = ((6, "alvorada"), (8, "manhã"), (12, "meio-dia"), (14, "tarde"),
          (17, "anoitecendo"), (19, "noite"))

# Variações de som: arquivos nome_1.wav ... nome_N.wav, sorteados sem repetir o último.
STEP_VARIANTS = 5             # passos de cada terreno
STRIKE_VARIANTS = 3           # golpe (soco e lança usam os mesmos)
EFFORT_VARIANTS = 4           # voz de esforço da heroína ao golpear
BOAR_GRUNT_VARIANTS = 2       # grunhido do javali
HOOF_VARIANTS = 4             # casco do javali

# --- mapa ----------------------------------------------------------------------
# Uma grade de MAP_WIDTH por MAP_HEIGHT casas. Hoje só se anda pela fileira 0 (de oeste
# a leste); a grade já aceita mais fileiras. O acampamento começa perto da ponta oeste
# e o rio fica logo depois da última casa.
MAP_WIDTH = 58
MAP_HEIGHT = 1
MAP_END = MAP_WIDTH - 1
CAMP_START = 3                # onde fica o primeiro acampamento
CAMP_RADIUS = 2               # até tantas casas da fogueira você está "no acampamento"
ZONE_START = 5                # os sorteios de bambu e cascalho começam daqui
MARGEM_LENGTH = 4             # casas de margem antes do rio
BAMBOO_ZONES = (3, 4)         # quantos focos de bambu o mapa sorteia
BAMBOO_RADIUS = (4, 6)        # raio de cada foco; na borda o bambu rareia
GRAVEL_ZONES = (1, 2)
GRAVEL_RADIUS = (3, 4)
FERTILE_PATCHES = (3, 4)      # pedaços de terra boa já no campo, de 1 a 3 casas
TILE_METERS = 0.8             # distância entre casas no som 3D
HEAR_TILES = 12               # mais longe que isso, coisas do mapa não tocam

# --- jogador -------------------------------------------------------------------
MAX_HEALTH = 10
STEP_SECONDS = 0.38
STEP_SECONDS_HUNGRY = 0.55
CARRY_LIMIT = 12              # itens na mochila (a lança não conta)
SEARCH_SECONDS = 0.6          # um tateio com a mão
SEARCH_FIND_CHANCE = 0.3      # chance de cada tateio pegar alguma coisa
# Tarefas que pedem apertar B várias vezes: quantos toques, e quanto tempo pode
# passar entre dois toques antes de o progresso se perder.
CHOP_PRESSES = 5              # cortar um bambu
CHOP_IDLE_SECONDS = 2.0
FIRE_PRESSES = 8              # acender a fogueira
FIRE_IDLE_SECONDS = 1.2
COMPOST_PRESSES = 4           # espalhar adubo
COMPOST_IDLE_SECONDS = 2.0
WEED_PRESSES = 4              # capinar
WEED_IDLE_SECONDS = 2.0
HARVEST_PRESSES = 3           # colher
HARVEST_IDLE_SECONDS = 2.0
STICK_DEADZONE = 0.5          # analógico esquerdo: passou disso, anda
PUNCH_DAMAGE = 1
AIM_RANGE = 8                 # ao virar, o som de mira avisa um bicho até esta distância
ATTACK_COOLDOWN = 0.8

# --- fome ----------------------------------------------------------------------
# Saciedade de 0 a 100. Abaixo de HUNGRY anda devagar e não se cura;
# em 0 perde STARVE_DAMAGE de vida por hora.
FULLNESS_START = 75
FULLNESS_PER_HOUR = 4.0
HUNGRY = 30
STARVE_DAMAGE = 1

# --- cura ----------------------------------------------------------------------
HEAL_HOURS_BASE = 2           # na base, 1 de vida a cada 2 horas
HEAL_HOURS_FIRE = 1           # com a fogueira acesa, a cada hora

# --- busca ---------------------------------------------------------------------
TILE_STOCK = 2                # quanto cada casa tem para achar
TILE_REGROW_HOURS = 14        # 1 volta a cada 14 horas, até TILE_STOCK

# --- clima da noite ------------------------------------------------------------
# Ao entardecer o céu avisa como será a noite. A primeira noite é sempre limpa.
WEATHER_WEIGHTS = (("limpa", 30), ("lua", 25), ("chuva", 25), ("neblina", 20))
MOON_GROWTH = 3.0             # lua cheia: as plantações crescem tantas horas por hora
RAIN_BURN = 2.0               # chuva: fogo e fumaça queimam tantas horas por hora
FOG_SPEED = 0.85              # neblina: os jiangshi pulam e batem em tantas vezes o tempo
FOG_HEALTH = 2                # e aguentam mais
FOG_DAMAGE = 1                # e machucam mais

# --- plantação -----------------------------------------------------------------
CROP_HOURS = 36               # horas de crescimento, sem contar o tempo com mato
WEEDS_AT_HOURS = 16           # o mato aparece nesta hora do crescimento e para tudo
CROP_YIELD = 3                # nabos por colheita
SEED_YIELD = 1                # e uma semente de volta

# --- ervas e chás --------------------------------------------------------------
TEA_HEAL = 3                  # chá de hortelã
GINGER_HOURS = 12             # chá de gengibre: a fome cai na metade por tantas horas
GINGER_HEAL = 1

# --- base ----------------------------------------------------------------------
CAMP_PRESSES = 6              # montar o acampamento
CAMP_IDLE_SECONDS = 2.0
FIRE_HOURS_PER_WOOD = 1.0        # cada lenha dá 1 hora de fogo, mas cada vez se põe 4 de uma vez
WOOD_LIMIT = 40               # lenha tem lugar à parte na mochila, fora do limite dos outros itens
WOOD_BUNDLE = 4               # pegar lenha do acampamento vem em feixes
POT_SPOIL_FACTOR = 0.5        # com pote de argila, a comida da base estraga na metade do ritmo

# --- lança ---------------------------------------------------------------------
SPEAR_DAMAGE = 3
SPEAR_REACH = 2
SPEAR_DURABILITY = 40

# --- javali (dia) --------------------------------------------------------------
BOAR_HEALTH = 5
BOAR_SPAWN_CHANCE = 0.35      # por hora de dia, se não houver um
BOAR_WANDER_SECONDS = (2.0, 5.0)
BOAR_NOTICE = 2               # chega a esta distância e ele investe
BOAR_CALM = 6                 # longe assim, ele desiste
BOAR_CHARGE_SECONDS = 0.45
BOAR_ATTACK_SECONDS = 1.6
BOAR_DAMAGE = (1, 2)
BOAR_MEAT = 2
BOAR_GRUNT_SECONDS = (3.5, 7.0)

# --- fumaça: a erva no fogo --------------------------------------------------------
# Com a fogueira acesa e fumaça, os jiangshi não passam da beira do acampamento; cada
# golpe deles na fogueira come um pouco da fumaça e do fogo.
SMOKE_HOURS = {"artemisia": 8.0}   # só a artemísia faz fumaça: horas por erva
SMOKE_MAX = 16.0
SMOKE_WARN_HOURS = 1.0        # o chiado de aviso toca quando a fumaça cai abaixo disso

# --- armadilhas ----------------------------------------------------------------
STAKE_PRESSES = 3             # fincar uma estaca
STAKE_IDLE_SECONDS = 2.0
STAKE_DAMAGE = 3
STAKE_USES = 3
PIT_PRESSES = 5               # cavar um buraco
PIT_IDLE_SECONDS = 2.0
PIT_STUCK_SECONDS = 6.0       # quanto tempo um bicho fica preso no buraco
PIT_DAMAGE = 1
PIT_USES = 2

# --- jiangshi (noite) ----------------------------------------------------------
JIANGSHI_HEALTH = 6
JIANGSHI_HEALTH_PER_NIGHT = 1  # mais duros a cada noite
JIANGSHI_HEALTH_MAX = 12
JIANGSHI_HOP_SECONDS = 1.4    # um pulo = uma casa; encurta a cada noite
JIANGSHI_HOP_PER_NIGHT = 0.06
JIANGSHI_HOP_MIN = 0.9
JIANGSHI_ATTACK_SECONDS = 2.4
JIANGSHI_ATTACK_PER_NIGHT = 0.1
JIANGSHI_ATTACK_MIN = 1.5
JIANGSHI_PLAYER_DAMAGE = 2
JIANGSHI_SMOKE_DRAIN = 0.25   # horas de fumaça que cada golpe na fogueira come
JIANGSHI_FIRE_DRAIN = 0.1     # e de fogo
JIANGSHI_CLAW_CHANCE = 0.25   # colado em você na beira, chance de o golpe ser em você
JIANGSHI_CLAW_DAMAGE = 1
JIANGSHI_NOTICE = 3           # fora do acampamento, persegue o jogador que chega tão perto
JIANGSHI_FIRST_NIGHT = 3      # quantos saem na primeira noite
JIANGSHI_PER_NIGHT = 3        # a mais a cada noite
JIANGSHI_MAX = 20
# As ondas: o sino toca, e um grupo sai do rio de uma vez.
WAVES_FIRST = 2               # ondas na primeira noite; +1 a cada duas noites
WAVES_MAX = 5
WAVE_HOURS = (20, 4)          # a primeira onda sai na primeira hora, a última até a segunda
