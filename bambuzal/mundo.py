"""O mundo do jogo: o mapa em linha, o relógio, o jogador, a base e os bichos.

Não sabe nada de botões nem de arquivos. Recebe uma `ui` com say, play, loop,
stop e listen, e avisa o main.py pelas funções on_dawn e on_death. Os testes
usam uma ui de mentira.
"""
import functools
import random

from . import config as C
from . import data as D
from . import mapa as M


class Boar:
    kind = "javali"

    def __init__(self, tile, rng):
        self.tile = tile
        self.health = C.BOAR_HEALTH
        self.charging = False
        self.move_in = rng.uniform(*C.BOAR_WANDER_SECONDS)
        self.attack_in = C.BOAR_ATTACK_SECONDS
        self.grunt_in = rng.uniform(*C.BOAR_GRUNT_SECONDS)
        self.stuck = 0.0              # segundos que faltam para sair do buraco

    def to_dict(self):
        return {"tile": self.tile, "health": self.health}


class Jiangshi:
    kind = "jiangshi"

    def __init__(self, tile, hop=None, attack=None):
        self.tile = tile
        self.health = C.JIANGSHI_HEALTH
        self.hop_s = hop or C.JIANGSHI_HOP_SECONDS        # mais rápidos a cada noite
        self.attack_s = attack or C.JIANGSHI_ATTACK_SECONDS
        self.hop_in = self.hop_s
        self.attack_in = self.attack_s
        self.stuck = 0.0

    def to_dict(self):
        return {"tile": self.tile, "health": self.health}


class World:
    def __init__(self, ui, rng=None, on_dawn=None, on_death=None, mapa=None):
        self.ui = ui
        self.rng = rng or random.Random()
        self.fx = random.Random(5)          # só escolhe variações de som, sem mexer no rng do jogo
        self._last_variant = {}
        self.map = mapa or M.generate(self.rng)
        self.on_dawn = on_dawn or (lambda: None)
        self.on_death = on_death or (lambda summary: None)

        self.hours = float(C.START_HOUR)   # horas desde a meia-noite do dia 1
        self.camp = C.CAMP_START                # a casa da fogueira
        self.x = self.camp
        self.y = 0                              # a fileira; hoje só existe a 0
        self.facing = 1
        self.health = C.MAX_HEALTH
        self.fullness = float(C.FULLNESS_START)
        self.bag = {k: [] for k in D.ITEMS}    # cada item: horas que faltam para estragar
        self.base = {k: [] for k in D.ITEMS}
        self.spear = 0                          # durabilidade; 0 = sem lança
        self.fire_hours = 0.0
        self.smoke = 0.0                        # horas de fumaça de erva que ainda faltam
        self.pots = 0
        self.stock = {c: C.TILE_STOCK for c in self.map.cells()}     # (x, y) -> o que ainda há
        self.regrow = {c: 0 for c in self.map.cells()}
        self.plots = {}                         # (x, y) -> {"hours", "weeds", "ready"}
        self.warm_hours = 0                     # chá de gengibre: a fome cai na metade
        self.drops = {}                         # casa -> {item: [frescor]}
        self.boars = []
        self.jiangshi = []
        self.waves = []                         # [hora absoluta, quantos] das ondas que faltam
        self.wave_total = 0
        self.weather = "limpa"                 # o clima da noite que vem ou da que passa
        self.traps = {}                         # casa -> {"kind": "estaca"|"buraco", "uses"}
        self.nights = 0                         # noites que já começaram
        self.heal_count = 0
        self.kills = {"javali": 0, "jiangshi": 0}
        self.alive = True

        self.held = 0
        self.step_in = 0.0
        self.searching = None                   # segundos que faltam
        self.task = None                        # tarefa de apertar B: {"kind", "count", "need", "idle"}
        self.hinted = set()
        self.attack_in = 0.0

        self.base["fruta"] = [D.ITEMS["fruta"][4]] * 2

    # --- mapa --------------------------------------------------------------------
    @property
    def cell(self):
        return (self.x, self.y)

    def terrain(self, x=None):
        """A chave do terreno da casa x (da fileira do jogador); sem x, o daqui."""
        return self.map.terrain(self.x if x is None else x, self.y)

    def terrain_name(self, x=None):
        return D.terrain_name(self.terrain(x))

    def at_camp(self, x=None):
        """Dentro do círculo de luz da fogueira?"""
        return abs((self.x if x is None else x) - self.camp) <= C.CAMP_RADIUS

    @property
    def climate(self):
        """O clima de agora: só a noite tem clima; de dia é sempre limpo."""
        return self.weather if self.night else "limpa"

    @property
    def smoke_on(self):
        return self.fire_hours > 0 and self.smoke > 0

    # --- relógio ----------------------------------------------------------------
    @property
    def day(self):
        return int(self.hours // 24) + 1

    @property
    def hour(self):
        return int(self.hours) % 24

    @staticmethod
    def is_night_hour(hour):
        return hour >= C.NIGHT_START or hour < C.NIGHT_END

    @property
    def night(self):
        return self.is_night_hour(self.hour)

    @staticmethod
    def phase_at(hour):
        """Nome da fase do dia: alvorada, manhã, meio-dia, tarde, anoitecendo ou noite."""
        name = C.PHASES[-1][1]          # de 19 às 6 é noite, a fase que atravessa a meia-noite
        for start, label in C.PHASES:
            if hour >= start:
                name = label
        return name

    @property
    def phase(self):
        return self.phase_at(self.hour)

    def time_text(self):
        return "Dia %d, %s" % (self.day, self.phase)

    def start(self):
        """Primeira fala de um jogo novo ou carregado, e os sons de fundo."""
        self.ui.listen(self.x)
        self._ambience()

    def update(self, dt):
        if not self.alive:
            return
        before = int(self.hours)
        self.hours += dt / C.HOUR_SECONDS
        for h in range(before + 1, int(self.hours) + 1):
            self._on_hour(h % 24)
            if not self.alive:
                return
        while self.waves and self.hours >= self.waves[0][0]:
            self._start_wave(self.waves.pop(0)[1])
        self._update_player(dt)
        self._update_boars(dt)
        self._update_jiangshi(dt)

    def _on_hour(self, hour):
        self._hunger()
        if not self.alive:
            return
        self._spoil()
        self._regrow()
        self._grow_plots()
        self._fire_tick()
        self._heal()
        if self.warm_hours > 0:
            self.warm_hours -= 1
        if hour == 12 and self.day == 1 and not self.spear:
            self.ui.say("Dica: no acampamento, com %s, você faz uma lança." % D.cost_text(D.SPEAR_COST),
                        queue=True)
        if hour in self.PHASE_TEXT:
            self.ui.say(self.PHASE_TEXT[hour], queue=True)
        if hour == C.DUSK_WARNING_HOUR:
            self._forecast()
            self.ui.say("Anoitecendo. O sol está baixando. Volte ao acampamento, acenda a fogueira "
                        "e tenha lenha e artemísia antes de escurecer.")
        elif hour == C.NIGHT_START:
            self._nightfall()
        elif hour == C.NIGHT_END:
            self._dawn()
        if not self.night and not self.boars and self.rng.random() < C.BOAR_SPAWN_CHANCE:
            self._spawn_boar()

    PHASE_TEXT = {
        8: "Manhã. O sol já subiu.",
        12: "Meio-dia. O sol está a pino.",
        14: "Tarde. O calor começa a ceder.",
    }

    WEATHER_TEXT = {
        "limpa": "Céu limpo: uma noite sem surpresas.",
        "lua": "Vai ser lua cheia: as plantações crescem mais depressa esta noite.",
        "chuva": "Vai chover: a fogueira e a fumaça queimam o dobro do tempo esta noite.",
        "neblina": "Vem neblina: os jiangshi ficam mais fortes, mais rápidos e mais perigosos "
                   "esta noite.",
    }

    def _forecast(self):
        """Sorteia o clima da noite que vem; a primeira noite é sempre limpa."""
        if self.nights == 0:
            self.weather = "limpa"
        else:
            total = sum(w for _, w in C.WEATHER_WEIGHTS)
            roll = self.rng.uniform(0, total)
            for key, weight in C.WEATHER_WEIGHTS:
                roll -= weight
                if roll <= 0:
                    break
            self.weather = key
        self.ui.say(self.WEATHER_TEXT[self.weather], queue=True)

    def _nightfall(self):
        self.nights += 1
        n = min(C.JIANGSHI_MAX, C.JIANGSHI_FIRST_NIGHT + C.JIANGSHI_PER_NIGHT * (self.nights - 1))
        k = min(C.WAVES_MAX, C.WAVES_FIRST + (self.nights - 1) // 2, n)
        first, last = C.WAVE_HOURS
        span = (last + 24 - first) % 24
        day_start = (self.day - 1) * 24
        self.waves = []
        for i in range(k):
            at = day_start + first + (span * i / float(k - 1) if k > 1 else 0)
            self.waves.append([at, n // k + (1 if i < n % k else 0)])
        self.wave_total = k
        self.boars = []
        self.ui.play("gongo")
        self.ui.say("Noite. Anoiteceu. O sino avisa cada onda de mortos que sair do rio. "
                    + self.WEATHER_TEXT[self.weather])
        self._ambience()

    def _start_wave(self, count):
        number = self.wave_total - len(self.waves)
        for i in range(count):
            self._spawn_jiangshi(i)
        self.ui.play("sino_onda")
        self.ui.say("Onda %d de %d: %d %s saem do rio." % (
            number, self.wave_total, count, "jiangshi"))

    def _dawn(self):
        gone = len(self.jiangshi)
        self.jiangshi = []
        self.waves = []
        self.ui.stop("jiangshi")
        self.ui.play("sino")
        text = "Alvorada. Amanheceu o dia %d." % self.day
        if gone:
            text += " O sol fez os mortos virarem pó."
        if self.fire_hours > 0:
            text += " A fogueira ainda queima por %d horas." % int(self.fire_hours + 0.999)
        self.ui.say(text)
        self.weather = "limpa"
        self._ambience()
        self.on_dawn()

    def _ambience(self):
        if self.night:
            self.ui.stop("dia")
            self.ui.loop("noite", "noite", volume=0.5)
        else:
            self.ui.stop("noite")
            self.ui.loop("dia", "dia", volume=0.5)
        for name in ("chuva", "neblina"):
            if self.climate == ("chuva" if name == "chuva" else "neblina"):
                self.ui.loop(name, name, volume=0.55)
            else:
                self.ui.stop(name)
        self._place_loops()

    def _place_loops(self):
        """Sons parados no mapa: o rio, o bambuzal ao vento e a fogueira."""
        self.ui.loop("rio", "rio", self.map.river_x, volume=0.8)
        grove = self.map.nearest("bambuzal", self.x, self.y)
        if grove is not None:
            self.ui.loop("vento_bambu", "vento_bambu", grove[0], volume=0.6)
        else:
            self.ui.stop("vento_bambu")
        if self.fire_hours > 0:
            self.ui.stop("fogueira_erva" if not self.smoke_on else "fogueira")
            name = "fogueira_erva" if self.smoke_on else "fogueira"
            self.ui.loop(name, name, self.camp, volume=0.8)
        else:
            self.ui.stop("fogueira")
            self.ui.stop("fogueira_erva")

    # --- fome, comida, cura ------------------------------------------------------
    def _hunger(self):
        was = self.fullness
        self.fullness = max(0.0, self.fullness - C.FULLNESS_PER_HOUR
                            * (0.5 if self.warm_hours > 0 else 1.0))
        if was >= C.HUNGRY > self.fullness:
            self.ui.play("barriga")
            self.ui.say("Você está com fome. Com fome, anda mais devagar e não se cura.")
        elif was > 0 and self.fullness == 0:
            self.ui.play("barriga")
            self.ui.say("Você está faminto e começa a perder vida. Coma alguma coisa.")
        elif self.fullness == 0:
            self.hurt(C.STARVE_DAMAGE, "A fome aperta", "de fome")

    @property
    def hungry(self):
        return self.fullness < C.HUNGRY

    def _spoil(self):
        lost = []
        base_rate = C.POT_SPOIL_FACTOR if self.pots else 1.0
        for where, store, rate in (("na mochila", self.bag, 1.0), ("na base", self.base, base_rate)):
            for k in D.PERISHABLE:
                left = [f - rate for f in store[k]]
                rotten = sum(1 for f in left if f <= 0)
                store[k] = [f for f in left if f > 0]
                if rotten:
                    lost.append("%s %s" % (D.count(k, rotten), where))
                    self._add(store, "resto", rotten)       # o que estraga vira adubo em potencial
        for tile in list(self.drops):
            pile = self.drops[tile]
            for k in D.PERISHABLE:
                if k in pile:
                    pile[k] = [f - 1 for f in pile[k] if f - 1 > 0]
                    if not pile[k]:
                        del pile[k]
            if not pile:
                del self.drops[tile]
        if lost:
            self.ui.say("Estragou: %s. Sobrou resto de comida." % D.join(lost), queue=True)

    def _regrow(self):
        for c in self.stock:
            if self.stock[c] < C.TILE_STOCK:
                self.regrow[c] += 1
                if self.regrow[c] >= C.TILE_REGROW_HOURS:
                    self.regrow[c] = 0
                    self.stock[c] += 1

    def _fire_tick(self):
        if self.fire_hours > 0:
            rate = C.RAIN_BURN if self.climate == "chuva" else 1.0
            self.fire_hours -= rate
            if self.smoke > 0:
                self._set_smoke(self.smoke - rate)
            if self.fire_hours <= 0:
                self._fire_out()

    def _fire_out(self):
        self.fire_hours = 0.0
        self.smoke = 0.0
        self.ui.stop("fogueira")
        self.ui.stop("fogueira_erva")
        self.ui.play("fogo_apaga", self.camp)
        self.ui.say("A fogueira apagou.", queue=not self.night)

    def _set_smoke(self, value):
        """Muda a fumaça e avisa, de ouvido e por voz, quando ela está acabando."""
        was = self.smoke
        self.smoke = max(0.0, min(C.SMOKE_MAX, value))
        if was > 0 and self.smoke <= 0:
            self.ui.play("fumaca_fraca")
            self.ui.say("A fumaça acabou. Os jiangshi vão passar.")
            self._place_loops()
        elif was >= C.SMOKE_WARN_HOURS > self.smoke > 0:
            self.ui.play("fumaca_fraca")
            self.ui.say("A fumaça está acabando.")
        elif was <= 0 < self.smoke:
            self._place_loops()

    def _heal(self):
        if self.health >= C.MAX_HEALTH or self.hungry or not self.at_camp():
            self.heal_count = 0
            return
        self.heal_count += 1
        need = C.HEAL_HOURS_FIRE if self.fire_hours > 0 else C.HEAL_HOURS_BASE
        if self.heal_count >= need:
            self.heal_count = 0
            self.health += 1
            self.ui.say("Vida %d." % self.health, queue=True)

    def eat(self, key):
        """Come um do item, da mochila primeiro, o que estraga antes."""
        for store in (self.bag, self.base):
            if store[key]:
                store[key].sort()
                store[key].pop(0)
                gain = D.ITEMS[key][3]
                self.fullness = min(100.0, self.fullness + gain)
                self.ui.play("comer")
                text = "Comeu %s. %s." % (D.name(key), self.fullness_text())
                if key in D.LEAVES_SCRAP and self.bag_room() > 0:
                    self._add(self.bag, "resto", 1)
                    text += " Sobrou um resto de comida."
                return text
        return "Não tem %s." % D.name(key, 2)

    def fullness_text(self):
        f = int(round(self.fullness))
        if f == 0:
            state = "faminto"
        elif self.hungry:
            state = "com fome"
        elif f >= 85:
            state = "satisfeito"
        else:
            state = "sem fome"
        return "Saciedade %d, %s" % (f, state)

    # --- jogador -----------------------------------------------------------------
    def bag_count(self):
        """Itens na mochila, sem a lenha, que tem lugar à parte."""
        return sum(len(v) for k, v in self.bag.items() if k != "lenha")

    def bag_room(self):
        return C.CARRY_LIMIT - self.bag_count()

    def wood_room(self):
        return C.WOOD_LIMIT - len(self.bag["lenha"])

    def room_for(self, key):
        return self.wood_room() if key == "lenha" else self.bag_room()

    def press(self, button):
        if not self.alive:
            return
        if button in ("left", "right"):
            d = -1 if button == "left" else 1
            self.held = d
            if self.facing != d:
                self.facing = d
                self.ui.play("virar")
                self._aim_cue()
            self._cancel_search()
            self._cancel_task("Parou: o progresso se perdeu." if self.task else None)
            if self.step_in <= 0:
                self._step()
        elif button == "b":
            self.act()
        elif button == "y":
            self.attack()
        elif button == "a":
            self.ui.say(self.describe_here())
        elif button in ("l1", "r1"):
            self.ui.say(self.next_point(-1 if button == "l1" else 1))
        elif button == "select":
            self.ui.say(self.status())

    def target_ahead(self):
        """O bicho mais perto na direção em que ela olha, ou None."""
        ahead = [e for e in self.boars + self.jiangshi
                 if 0 <= (e.tile - self.x) * self.facing <= C.AIM_RANGE]
        return min(ahead, key=lambda e: abs(e.tile - self.x)) if ahead else None

    def _aim_cue(self):
        """Ao virar para um bicho, um som curto no centro avisa que ele está na mira.
        Não depende de estéreo: quanto mais perto, mais agudo, e dentro do alcance
        da arma toca um som diferente."""
        e = self.target_ahead()
        if e is None:
            return
        d = abs(e.tile - self.x)
        reach = C.SPEAR_REACH if self.spear else 1
        if d <= reach:
            self.ui.play("mira_alcance")
        else:
            self.ui.play("mira", pitch=1.0 + 0.6 * (1 - d / float(C.AIM_RANGE + 1)))

    def release(self, button):
        if button == "left" and self.held == -1 or button == "right" and self.held == 1:
            self.held = 0

    def _update_player(self, dt):
        self.step_in -= dt
        self.attack_in -= dt
        if self.held and self.step_in <= 0:
            self._step()
        if self.task is not None:
            self.task["idle"] -= dt
            if self.task["idle"] <= 0:
                self._cancel_task("Parou de apertar: o progresso se perdeu.")
        if self.searching is not None:
            self.searching -= dt
            if self.searching <= 0:
                self.searching = None
                self._finish_search()

    def variant(self, base, count):
        """Nome de uma das variações base_1 ... base_count, sem repetir a anterior."""
        choices = [i for i in range(1, count + 1) if i != self._last_variant.get(base)] or [1]
        pick = self._last_variant[base] = self.fx.choice(choices)
        return "%s_%d" % (base, pick)

    def _step(self):
        target = self.x + self.held if self.held else self.x
        if not self.held:
            return
        if target < 0:
            self.ui.play("borda")
            self.ui.say("O fim do mapa, a oeste.")
            self.held = 0
            return
        if target > self.map.last_x:
            self.ui.play("borda")
            self.ui.say("O rio. Fundo e rápido demais para atravessar.")
            self.held = 0
            return
        before = self.terrain()
        was_camp = self.at_camp()
        self.x = target
        self.step_in = C.STEP_SECONDS_HUNGRY if self.hungry else C.STEP_SECONDS
        self.ui.listen(self.x)
        after = self.terrain()
        self.ui.play(self.variant(D.step_sound(after), C.STEP_VARIANTS), self.x,
                     pitch=self.rng.uniform(0.95, 1.05))
        self._place_loops()
        now_camp = self.at_camp()
        if now_camp and not was_camp:
            self.ui.say("Acampamento, fogueira %s." % ("acesa" if self.fire_hours > 0 else "apagada"))
        elif was_camp and not now_camp or after != before:
            self.ui.say(D.terrain_name(after) + ".")
        self._check_drops_underfoot()
        self._check_plot_underfoot()

    def _check_drops_underfoot(self):
        pile = self.drops.get(self.x)
        if pile:
            self.ui.play("item_chao", self.x)

    def _check_plot_underfoot(self):
        plot = self.plots.get(self.cell)
        if plot is not None:
            self.ui.say(self.plot_text(plot) + ".", queue=True)
        elif self.map.is_fertile(*self.cell):
            self.ui.say("Terra boa para plantar.", queue=True)

    def act(self):
        """B: o verbo do lugar. Com uma tarefa em andamento, é mais um toque nela; fora, pega o
        que caiu ou cuida da plantação; no acampamento, abre o menu; no bambuzal, corta bambu;
        no resto, tateia o chão."""
        if self.task is not None:
            self._tap()
        elif self.drops.get(self.x):
            self.ui.say(self.pick_up())
        elif self.cell in self.plots:
            self._tend_plot()
        elif self.at_camp():
            self.ui.open_base()
        elif self.terrain() == "bambuzal":
            self._start_task("cortar", C.CHOP_PRESSES, C.CHOP_IDLE_SECONDS)
        elif self.searching is None:
            self._grope()

    # --- tarefas de apertar B -----------------------------------------------------
    TASKS = {
        # tipo: (dica falada na primeira vez, som de cada toque)
        "cortar": ("cortar o bambu", "corte"),
        "fogo": ("acender a fogueira", "faisca"),
        "adubar": ("espalhar o adubo", "adubar"),
        "capinar": ("capinar o mato", "capinar"),
        "colher": ("colher", "colher"),
        "montar": ("montar o acampamento", "plantar"),
        "fincar": ("fincar a estaca", "fincar"),
        "cavar": ("cavar o buraco", "cavar"),
    }

    def _start_task(self, kind, need, idle):
        if kind == "cortar":
            if self.bag_room() <= 0:
                self.ui.play("errado")
                self.ui.say("A mochila está cheia. Guarde as coisas no acampamento.")
                return
            if self.stock[self.cell] <= 0:
                self.ui.play("nada")
                self.ui.say("Aqui já foi cortado. Procure mais adiante ou volte amanhã.")
                return
        self._cancel_search()
        self.task = {"kind": kind, "count": 0, "need": need, "idle": idle, "max_idle": idle}
        if kind not in self.hinted:
            self.hinted.add(kind)
            self.ui.say("Aperte B várias vezes para %s." % self.TASKS[kind][0])
        self._tap()

    def _tap(self):
        t = self.task
        t["count"] += 1
        t["idle"] = t["max_idle"]
        frac = t["count"] / float(t["need"])
        where = self.camp if t["kind"] == "fogo" else self.x
        self.ui.play(self.TASKS[t["kind"]][1], where, pitch=0.85 + 0.4 * frac)
        if t["count"] >= t["need"]:
            self.task = None
            kind = t["kind"]
            if kind == "cortar":
                self.ui.play("bambu_cai", self.x)
                self._gather()
            elif kind == "fogo":
                self.ui.say(self._light_fire())
            elif kind == "adubar":
                self.ui.say(self._finish_compost())
            elif kind == "capinar":
                self.ui.say(self._finish_weeding())
            elif kind == "colher":
                self.ui.say(self._finish_harvest())
            elif kind == "montar":
                self.ui.say(self._finish_camp())
            else:
                self.ui.say(self._finish_trap(kind))

    def _cancel_task(self, text=None):
        if self.task is None:
            return
        self.task = None
        self.ui.play("errado")
        if text:
            self.ui.say(text)

    def _cancel_search(self):
        if self.searching is not None:
            self.searching = None

    # --- coleta ---------------------------------------------------------------------
    def _grope(self):
        """Um tateio rápido com a mão. Cada B tem só uma chance de pegar alguma coisa, e
        quando não pega fica em silêncio: o som curto da mão já diz que tentou."""
        if self.terrain() not in D.SEARCH:
            return
        if self.stock[self.cell] <= 0:
            self.ui.play("nada")
            self.ui.say("Aqui já foi revirado. Procure mais adiante ou volte amanhã.")
            return
        self.searching = C.SEARCH_SECONDS
        self.ui.play("mao", self.x, pitch=self.rng.uniform(0.9, 1.1))

    def _finish_search(self):
        if self.rng.random() < C.SEARCH_FIND_CHANCE:
            self._gather()

    def _gather(self):
        """Pega algo do terreno daqui (se couber) e diz o que foi."""
        pool = D.SEARCH.get(self.terrain())
        if not pool:
            return
        if self.stock[self.cell] <= 0:
            return
        total = sum(w for _, w in pool)
        roll = self.rng.uniform(0, total)
        for key, w in pool:
            roll -= w
            if roll <= 0:
                break
        if self.room_for(key) <= 0:
            self.ui.play("errado")
            self.ui.say("A mochila está cheia. Guarde as coisas no acampamento.")
            return
        self.stock[self.cell] -= 1
        self._add(self.bag, key, 1)
        self.ui.play("achou_" + key if key in ("fruta", "broto") else "achou", self.x)
        left = "" if self.stock[self.cell] else " Aqui acabou."
        text = "%s. %d na mochila.%s" % (D.name(key).capitalize(), len(self.bag[key]), left)
        hint = D.HINTS.get(key)
        if hint and key not in self.hinted:
            self.hinted.add(key)
            text += " " + hint
        self.ui.say(text)

    @staticmethod
    def _add(store, key, n, freshness=None):
        if freshness is None:
            freshness = D.ITEMS[key][4]
        store[key].extend([freshness if freshness is not None else 1e9] * n)

    def pick_up(self):
        pile = self.drops.get(self.x, {})
        got, left = [], 0
        for key in list(pile):
            take = min(len(pile[key]), self.room_for(key))
            if take:
                pile[key].sort(reverse=True)
                self.bag[key].extend(pile[key][:take])
                pile[key] = pile[key][take:]
                got.append(D.count(key, take))
            if not pile[key]:
                del pile[key]
            else:
                left += len(pile[key])
        if not pile:
            self.drops.pop(self.x, None)
        if not got:
            self.ui.play("errado")
            return "A mochila está cheia."
        self.ui.play("achou", self.x)
        text = "Pegou %s." % D.join(got)
        if left:
            text += " Não coube tudo: ficou %d no chão." % left
        return text

    # --- acampamento e armadilhas --------------------------------------------------
    def field_actions(self):
        """O que a mochila oferece fora do acampamento: (texto, função que devolve a fala)."""
        if self.at_camp():
            return []
        out = [("Montar o acampamento aqui, com vários toques em B. O que está guardado vem junto",
                self.make_camp)]
        if self.x not in self.traps:
            out.append(("Fincar uma estaca aqui, com vários toques em B. Custa %s"
                        % D.cost_text(D.STAKE_COST), self.place_stake))
            out.append(("Cavar um buraco aqui, com vários toques em B", self.dig_pit))
        return out

    def make_camp(self):
        if self.at_camp():
            return "Você já está no acampamento."
        self._start_task("montar", C.CAMP_PRESSES, C.CAMP_IDLE_SECONDS)
        return ""

    def _finish_camp(self):
        lit = self.fire_hours > 0
        self.camp = self.x
        self.traps.pop(self.x, None)
        self.fire_hours = 0.0
        self.smoke = 0.0
        self.ui.stop("fogueira")
        self.ui.stop("fogueira_erva")
        self.ui.play("fazer")
        self._place_loops()
        text = "Montou o acampamento aqui. Tudo o que estava guardado veio junto."
        if lit:
            text += " A fogueira velha ficou para trás: acenda uma nova."
        return text

    def place_stake(self):
        if self.at_camp() or self.x in self.traps:
            self.ui.play("errado")
            return "Aqui não dá para fincar uma estaca."
        if not self.can_pay(D.STAKE_COST):
            self.ui.play("errado")
            return "Para a estaca falta %s." % self.missing(D.STAKE_COST)
        self._start_task("fincar", C.STAKE_PRESSES, C.STAKE_IDLE_SECONDS)
        return ""

    def dig_pit(self):
        if self.at_camp() or self.x in self.traps:
            self.ui.play("errado")
            return "Aqui não dá para cavar."
        self._start_task("cavar", C.PIT_PRESSES, C.PIT_IDLE_SECONDS)
        return ""

    def _finish_trap(self, kind):
        if self.x in self.traps:
            return ""
        if kind == "fincar":
            if not self.can_pay(D.STAKE_COST):
                return "Faltou %s para a estaca." % self.missing(D.STAKE_COST)
            self.pay(D.STAKE_COST)
            self.traps[self.x] = {"kind": "estaca", "uses": C.STAKE_USES}
            return "Fincou a estaca. Ela fere quem pisar, %d vezes." % C.STAKE_USES
        self.traps[self.x] = {"kind": "buraco", "uses": C.PIT_USES}
        return "Cavou o buraco. Quem cair fica preso por uns %d segundos." % int(C.PIT_STUCK_SECONDS)

    def _trap_check(self, e):
        """Um bicho acabou de pisar nesta casa: se tem armadilha, ela dispara."""
        trap = self.traps.get(e.tile)
        if not trap:
            return
        name = trap["kind"]
        if name == "estaca":
            self.ui.play("estaca_acerta", e.tile)
            e.health -= C.STAKE_DAMAGE
        else:
            self.ui.play("buraco_cai", e.tile)
            e.health -= C.PIT_DAMAGE
            e.stuck = C.PIT_STUCK_SECONDS
        trap["uses"] -= 1
        if trap["uses"] <= 0:
            del self.traps[e.tile]
            self.ui.say("%s da casa %d cedeu." % ("A estaca" if name == "estaca" else "O buraco",
                                                 e.tile), queue=True)
        if e.health <= 0:
            self._kill(e)

    # --- plantação ---------------------------------------------------------------
    def plot_text(self, plot):
        if plot["ready"]:
            return "Nabos maduros, B colhe"
        if plot["weeds"]:
            return "Plantação tomada pelo mato, B capina"
        left = max(1, int(C.CROP_HOURS - plot["hours"] + 0.999))
        return "Nabo crescendo, faltam %d horas" % left

    def plant(self):
        """Planta uma semente aqui, se for terra boa e estiver livre."""
        if not self.bag["semente"]:
            return "Não tem semente na mochila."
        if not self.map.is_fertile(*self.cell):
            self.ui.play("errado")
            return "Aqui não é terra boa. Procure terra boa ou faça uma com adubo."
        if self.cell in self.plots:
            self.ui.play("errado")
            return "Aqui já tem plantação."
        self.bag["semente"].pop()
        self.plots[self.cell] = {"hours": 0.0, "weeds": False, "ready": False}
        self.ui.play("plantar", self.x)
        return "Plantou. O nabo leva cerca de %d horas, e o mato atrapalha no meio do caminho." % (
            C.CROP_HOURS)

    def use_compost(self):
        """Espalha adubo aqui, com vários toques em B, para fazer terra boa no campo."""
        if not self.bag["adubo"]:
            return "Não tem adubo na mochila."
        if self.terrain() != "campo" or self.map.is_fertile(*self.cell):
            self.ui.play("errado")
            if self.map.is_fertile(*self.cell):
                return "Aqui já é terra boa."
            return "Adubo só serve no campo."
        self._start_task("adubar", C.COMPOST_PRESSES, C.COMPOST_IDLE_SECONDS)
        return ""

    def _finish_compost(self):
        if not self.bag["adubo"]:
            return "O adubo acabou."
        self.bag["adubo"].pop()
        self.map.fertile.add(self.cell)
        self.ui.play("achou", self.x)
        return "Terra boa. Agora dá para plantar aqui."

    def _tend_plot(self):
        plot = self.plots[self.cell]
        if plot["ready"]:
            self._start_task("colher", C.HARVEST_PRESSES, C.HARVEST_IDLE_SECONDS)
        elif plot["weeds"]:
            self._start_task("capinar", C.WEED_PRESSES, C.WEED_IDLE_SECONDS)
        else:
            self.ui.say(self.plot_text(plot) + ".")

    def _finish_weeding(self):
        plot = self.plots.get(self.cell)
        if plot is not None:
            plot["weeds"] = False
        self.ui.play("achou", self.x)
        return "Capinou. O nabo volta a crescer."

    def _finish_harvest(self):
        plot = self.plots.get(self.cell)
        if plot is None or not plot["ready"]:
            return ""
        room = self.bag_room()
        crop = min(C.CROP_YIELD, room)
        if crop < C.CROP_YIELD:
            # sem lugar na mochila, o resto cai no chão da própria plantação
            pile = self.drops.setdefault(self.cell[0], {})
            pile.setdefault("nabo", [])
            self._add(pile, "nabo", C.CROP_YIELD - crop)
        self._add(self.bag, "nabo", crop)
        seeds = min(C.SEED_YIELD, max(0, self.bag_room()))
        self._add(self.bag, "semente", seeds)
        del self.plots[self.cell]
        self.ui.play("achou", self.x)
        text = "Colheu %s" % D.count("nabo", C.CROP_YIELD)
        if seeds:
            text += " e %s" % D.count("semente", seeds)
        text += ". A terra continua boa."
        if crop < C.CROP_YIELD:
            text += " Não coube tudo: o resto ficou no chão."
        return text

    def _grow_plots(self):
        for cell, plot in self.plots.items():
            if plot["ready"] or plot["weeds"]:
                continue
            plot["hours"] += C.MOON_GROWTH if self.climate == "lua" else 1
            near = abs(cell[0] - self.x) <= C.HEAR_TILES
            if plot["hours"] >= C.CROP_HOURS:
                plot["ready"] = True
                self.ui.say("Um nabo ficou maduro, %s." % D.distance(cell[0] - self.x), queue=True)
            elif plot["hours"] >= C.WEEDS_AT_HOURS and not plot.get("weeded"):
                plot["weeds"] = plot["weeded"] = True
                if near:
                    self.ui.say("O mato tomou uma plantação, %s." % D.distance(cell[0] - self.x),
                                queue=True)

    def status(self):
        parts = [self.time_text(),
                 "Vida %d de %d" % (self.health, C.MAX_HEALTH),
                 self.fullness_text(),
                 "Mochila %d de %d" % (self.bag_count(), C.CARRY_LIMIT)]
        if self.total("lenha"):
            parts.append("Lenha %d" % self.total("lenha"))
        if self.spear:
            parts.append("Lança %d de %d" % (self.spear, C.SPEAR_DURABILITY))
        if self.night and self.weather != "limpa":
            parts.append({"lua": "Lua cheia", "chuva": "Chuva", "neblina": "Neblina"}[self.weather])
        if self.warm_hours:
            parts.append("Chá de gengibre por mais %d horas" % self.warm_hours)
        if self.fire_hours:
            text = "Fogueira por mais %d horas" % int(self.fire_hours + 0.999)
            text += (", fumaça por mais %d" % int(self.smoke + 0.999)) if self.smoke > 0 else \
                ", sem fumaça"
            parts.append(text)
        else:
            parts.append("Fogueira apagada")
        return ". ".join(parts) + "."

    def describe_here(self):
        key = self.terrain()
        parts = ["%s, casa %d" % (D.terrain_name(key), self.x)]
        if self.x == self.camp:
            parts.append("ao lado da fogueira, %s" % ("acesa" if self.fire_hours > 0 else "apagada"))
        elif self.at_camp():
            parts.append("no acampamento")
        if key in D.SEARCH:
            parts.append("ainda tem o que achar" if self.stock[self.cell] else "já revirado")
        plot = self.plots.get(self.cell)
        if plot is not None:
            parts.append(self.plot_text(plot))
        elif self.map.is_fertile(*self.cell):
            parts.append("terra boa para plantar")
        trap = self.traps.get(self.x)
        if trap:
            parts.append("%s, %d %s" % (trap["kind"], trap["uses"],
                                        "uso" if trap["uses"] == 1 else "usos"))
        pile = self.drops.get(self.x)
        if pile:
            parts.append("no chão: " + D.join(D.count(k, len(v)) for k, v in pile.items()))
        for e in sorted(self.boars + self.jiangshi, key=lambda e: abs(e.tile - self.x)):
            if abs(e.tile - self.x) <= C.HEAR_TILES:
                parts.append("%s %s" % (e.kind.capitalize(), D.distance(e.tile - self.x)))
        parts.append("olhando para " + ("leste" if self.facing > 0 else "oeste"))
        return ". ".join(p[0].upper() + p[1:] for p in parts) + "."

    def points(self):
        """Pontos que L1 e R1 anunciam: (casa, nome)."""
        pts = [(self.camp, "Acampamento")]
        for key, first, last in self.map.zones(self.y):
            if first > 0:
                pts.append((first, D.terrain_name(key)))
        for tile, trap in self.traps.items():
            pts.append((tile, trap["kind"].capitalize()))
        pts.append((self.map.last_x, "Beira do rio"))
        row = [(x, y) for x, y in self.map.cells() if y == self.y]
        for x, y in row:
            if (x, y) in self.plots:
                pts.append((x, "Plantação"))
            elif (x, y) in self.map.fertile and (x - 1, y) not in self.map.fertile:
                pts.append((x, "Terra boa"))
        for tile, pile in self.drops.items():
            pts.append((tile, "Coisas no chão"))
        for e in self.boars + self.jiangshi:
            pts.append((e.tile, e.kind.capitalize()))
        return pts

    def next_point(self, direction):
        ahead = [(abs(t - self.x), t, n) for t, n in self.points()
                 if (t - self.x) * direction > 0]
        if not ahead:
            return "Nada mais " + ("a oeste." if direction < 0 else "a leste.")
        _, tile, name = min(ahead)
        return "%s, %s." % (name, D.distance(tile - self.x))

    # --- combate -----------------------------------------------------------------
    def attack(self):
        if self.attack_in > 0:
            return
        self.attack_in = C.ATTACK_COOLDOWN
        reach = C.SPEAR_REACH if self.spear else 1
        targets = [e for e in self.boars + self.jiangshi
                   if 0 <= (e.tile - self.x) * self.facing <= reach]
        self.ui.play(self.variant("golpe", C.STRIKE_VARIANTS), self.x)
        self.ui.play(self.variant("esforco", C.EFFORT_VARIANTS), self.x)
        if not targets:
            return
        target = min(targets, key=lambda e: abs(e.tile - self.x))
        damage = C.SPEAR_DAMAGE if self.spear else C.PUNCH_DAMAGE
        if self.spear:
            self.spear -= 1
            if self.spear == 0:
                self.ui.play("quebrou")
                self.ui.say("A lança quebrou.", queue=True)
        target.health -= damage
        self.ui.play("acertou", target.tile)
        if target.health <= 0:
            self._kill(target)
        elif isinstance(target, Boar):
            target.charging = True

    def _kill(self, e):
        self.kills[e.kind] += 1
        if isinstance(e, Boar):
            self.boars.remove(e)
            self.ui.play("javali_morre", e.tile)
            pile = self.drops.setdefault(e.tile, {})
            pile.setdefault("carne", [])
            self._add(pile, "carne", C.BOAR_MEAT)
            self.ui.say("Javali abatido. Deixou %s no chão. B pega." % D.count("carne", C.BOAR_MEAT))
        else:
            self.jiangshi.remove(e)
            self.ui.play("jiangshi_morre", e.tile)
            self.ui.say("Jiangshi destruído.")

    def hurt(self, amount, text, cause):
        """text: o que aconteceu, falado; cause: do que morreu, se morrer."""
        if not self.alive:
            return
        self.health -= amount
        self.ui.play("dor")
        if self.health <= 0:
            self.health = 0
            self.die(cause)
        else:
            self.ui.say("%s. Vida %d." % (text, self.health))

    def die(self, cause):
        self.alive = False
        self.held = 0
        self._cancel_search()
        self.task = None
        for key in ("dia", "noite", "rio", "vento_bambu", "fogueira", "fogueira_erva", "jiangshi",
                    "chuva", "neblina"):
            self.ui.stop(key)
        self.ui.play("morte")
        nights = self.nights - (1 if self.night else 0)
        summary = {"day": self.day, "phase": self.phase, "nights": max(0, nights),
                   "cause": cause, "kills": dict(self.kills)}
        self.on_death(summary)

    # --- javali ------------------------------------------------------------------
    def _spawn_boar(self):
        choices = [t for t in range(self.map.width) if self._boar_ground(t) and abs(t - self.x) >= 6]
        if choices:
            self.boars.append(Boar(self.rng.choice(choices), self.rng))

    def _boar_ground(self, tile):
        return 0 <= tile <= self.map.last_x and self.terrain(tile) in ("campo", "bambuzal")

    def _update_boars(self, dt):
        for b in list(self.boars):
            d = self.x - b.tile
            b.grunt_in -= dt
            if b.grunt_in <= 0:
                b.grunt_in = self.rng.uniform(*C.BOAR_GRUNT_SECONDS)
                self.ui.play("javali", b.tile)
            outside = not self.at_camp()
            if b.stuck > 0:
                b.stuck -= dt
                continue
            if not b.charging and outside and abs(d) <= C.BOAR_NOTICE:
                b.charging = True
                b.move_in = C.BOAR_CHARGE_SECONDS
                b.attack_in = C.BOAR_ATTACK_SECONDS
                self.ui.play("javali_bufa", b.tile)
            if b.charging and (abs(d) >= C.BOAR_CALM or not outside):
                b.charging = False
            b.move_in -= dt
            if b.charging:
                if abs(d) <= 1:
                    b.attack_in -= dt
                    if b.attack_in <= 0:
                        b.attack_in = C.BOAR_ATTACK_SECONDS
                        self.ui.play("javali_ataque", b.tile)
                        self.hurt(self.rng.randint(*C.BOAR_DAMAGE), "O javali te acertou",
                                  "atacado por um javali")
                        if not self.alive:
                            return
                elif b.move_in <= 0:
                    b.move_in = C.BOAR_CHARGE_SECONDS
                    b.tile += 1 if d > 0 else -1
                    self.ui.play("casco", b.tile)
                    self._trap_check(b)
            elif b.move_in <= 0:
                b.move_in = self.rng.uniform(*C.BOAR_WANDER_SECONDS)
                step = self.rng.choice((-1, 1))
                if self._boar_ground(b.tile + step):
                    b.tile += step
                    self.ui.play("casco", b.tile, volume=0.6)
                    self._trap_check(b)

    # --- jiangshi ----------------------------------------------------------------
    def _make_jiangshi(self, tile):
        """Um jiangshi desta noite: mais duro e mais rápido a cada noite que passa."""
        n = max(0, self.nights - 1)
        fog = self.climate == "neblina"
        speed = C.FOG_SPEED if fog else 1.0
        j = Jiangshi(tile,
                     hop=max(C.JIANGSHI_HOP_MIN * speed,
                             (C.JIANGSHI_HOP_SECONDS - C.JIANGSHI_HOP_PER_NIGHT * n) * speed),
                     attack=max(C.JIANGSHI_ATTACK_MIN * speed,
                                (C.JIANGSHI_ATTACK_SECONDS - C.JIANGSHI_ATTACK_PER_NIGHT * n)
                                * speed))
        j.health = min(C.JIANGSHI_HEALTH_MAX,
                       C.JIANGSHI_HEALTH + C.JIANGSHI_HEALTH_PER_NIGHT * max(0, self.nights - 2))
        if fog:
            j.health += C.FOG_HEALTH
        return j

    def _spawn_jiangshi(self, offset=0):
        j = self._make_jiangshi(self.map.last_x - offset)
        self.jiangshi.append(j)
        if offset == 0:
            self.ui.play("jiangshi_sai", self.map.last_x)

    def _update_jiangshi(self, dt):
        smoke = self.smoke_on
        edge = self.camp + C.CAMP_RADIUS + 1        # a beira do acampamento, a leste
        for j in list(self.jiangshi):
            if j.stuck > 0:
                j.stuck -= dt
                continue
            d = self.x - j.tile
            # Com fumaça, só vão atrás de quem sai do acampamento; sem ela, atrás de você.
            chase = not smoke or (not self.at_camp() and abs(d) <= C.JIANGSHI_NOTICE)
            j.attack_in -= dt
            if chase and abs(d) <= 1:
                if j.attack_in <= 0:
                    j.attack_in = j.attack_s
                    self.ui.play("jiangshi_ataque", j.tile)
                    self.hurt(C.JIANGSHI_PLAYER_DAMAGE
                              + (C.FOG_DAMAGE if self.climate == "neblina" else 0),
                              "Um jiangshi te agarrou",
                              "nas mãos de um jiangshi")
                    if not self.alive:
                        return
                continue
            if not chase and j.tile == edge:
                if j.attack_in <= 0:
                    j.attack_in = j.attack_s
                    # Na beira da fumaça: ou arranham quem está ali, ou golpeiam a fogueira.
                    self.ui.play("jiangshi_ataque", j.tile)
                    if abs(d) <= 1 and self.rng.random() < C.JIANGSHI_CLAW_CHANCE:
                        self.hurt(C.JIANGSHI_CLAW_DAMAGE, "Um jiangshi te arranhou",
                                  "arranhado por um jiangshi")
                        if not self.alive:
                            return
                    else:
                        self._drain_fire()
                        smoke = self.smoke_on
                continue
            j.hop_in -= dt
            if j.hop_in <= 0:
                j.hop_in = j.hop_s
                target = self.x if chase else edge
                if j.tile != target:
                    j.tile += 1 if target > j.tile else -1
                    self.ui.play("jiangshi_pulo", j.tile)
                    self._trap_check(j)

    def _drain_fire(self):
        """Um golpe na fogueira come fumaça e fogo."""
        self.ui.play("fogo_chia", self.camp)
        if self.smoke > 0:
            self._set_smoke(self.smoke - C.JIANGSHI_SMOKE_DRAIN)
        self.fire_hours -= C.JIANGSHI_FIRE_DRAIN
        if self.fire_hours <= 0:
            self._fire_out()

    # --- base --------------------------------------------------------------------
    def total(self, key):
        return len(self.bag[key]) + len(self.base[key])

    def can_pay(self, cost):
        return all(self.total(k) >= n for k, n in cost.items())

    def missing(self, cost):
        return D.join(D.count(k, n - self.total(k)) for k, n in cost.items() if self.total(k) < n)

    def pay(self, cost):
        for k, n in cost.items():
            for _ in range(n):
                store = self.base if self.base[k] else self.bag
                store[k].sort()
                store[k].pop(0)

    def store_all(self):
        moved = []
        for k in D.ITEM_ORDER:
            if self.bag[k]:
                moved.append(D.count(k, len(self.bag[k])))
                self.base[k].extend(self.bag[k])
                self.bag[k] = []
        if not moved:
            return "A mochila está vazia."
        self.ui.play("guardar")
        return "Guardou %s." % D.join(moved)

    def take(self, key):
        if not self.base[key]:
            return "Não tem %s no acampamento." % D.name(key, 2)
        if self.room_for(key) <= 0:
            self.ui.play("errado")
            return "A mochila está cheia."
        n = min(C.WOOD_BUNDLE, self.room_for(key), len(self.base[key])) if key == "lenha" else 1
        self.base[key].sort(reverse=True)     # leva o mais fresco
        for _ in range(n):
            self.bag[key].append(self.base[key].pop(0))
        self.ui.play("pegar")
        return "Pegou %s. %d na mochila, %d no acampamento." % (
            D.count(key, n), len(self.bag[key]), len(self.base[key]))

    def fire(self):
        """Fogueira apagada: começa a acender (vários toques em B). Acesa: põe mais lenha."""
        cost = D.FEED_COST if self.fire_hours else D.FIRE_COST
        if not self.can_pay(cost):
            self.ui.play("errado")
            return "Falta %s." % self.missing(cost)
        if self.fire_hours:
            return self._light_fire()
        self._start_task("fogo", C.FIRE_PRESSES, C.FIRE_IDLE_SECONDS)
        return ""

    def _light_fire(self):
        cost = D.FEED_COST if self.fire_hours else D.FIRE_COST
        if not self.can_pay(cost):
            self.ui.play("errado")
            return "Falta %s." % self.missing(cost)
        self.pay(cost)
        lit = self.fire_hours > 0
        self.fire_hours += cost["lenha"] * C.FIRE_HOURS_PER_WOOD
        self.ui.play("fogo_acende", self.camp)
        self._place_loops()
        if lit:
            return "Pôs lenha no fogo. Queima por mais %d horas." % int(self.fire_hours + 0.999)
        return ("Acendeu a fogueira. Queima por %d horas; cada %s a mais dá %d. Joga artemísia "
                "nela para a fumaça espantar os jiangshi."
                % (int(self.fire_hours), D.count("lenha", D.FEED_COST["lenha"]),
                   D.FEED_COST["lenha"] * C.FIRE_HOURS_PER_WOOD))

    def smoke_herb(self, key):
        """Joga uma erva na fogueira: fumaça que segura os jiangshi na beira do acampamento."""
        if not self.fire_hours:
            self.ui.play("errado")
            return "A fogueira está apagada: a erva só solta fumaça no fogo."
        if not self.total(key):
            return "Não tem %s." % D.name(key, 2)
        if self.smoke >= C.SMOKE_MAX - 0.01:
            return "A fumaça já está no máximo."
        self.pay({key: 1})
        self._set_smoke(self.smoke + C.SMOKE_HOURS[key])
        self.ui.play("fumaca", self.camp)
        return "Pôs %s no fogo. Fumaça por mais %d horas." % (D.name(key), int(self.smoke + 0.999))

    def cook(self):
        if not self.fire_hours:
            return "Precisa da fogueira acesa."
        n = self.total("carne")
        if not n:
            return "Não tem carne crua."
        self.bag["carne"] = []
        self.base["carne"] = []
        self._add(self.base, "assado", n)
        self.ui.play("assar", self.camp)
        return "Assou %s. Ficam guardadas no acampamento e duram 2 dias." % D.count("carne", n)

    def make_spear(self):
        if not self.can_pay(D.SPEAR_COST):
            self.ui.play("errado")
            return "Para a lança falta %s." % self.missing(D.SPEAR_COST)
        self.pay(D.SPEAR_COST)
        had = self.spear > 0
        self.spear = C.SPEAR_DURABILITY
        self.ui.play("fazer")
        if had:
            return "Fez uma lança nova. Y ataca para o lado em que você está olhando."
        return "Fez uma lança. Ela alcança 2 casas e bate %d vezes mais forte que o soco." % (
            C.SPEAR_DAMAGE // C.PUNCH_DAMAGE)

    def make_pot(self):
        if not self.fire_hours:
            return "O pote precisa ir ao fogo: acenda a fogueira."
        if not self.can_pay(D.POT_COST):
            self.ui.play("errado")
            return "Para o pote falta %s." % self.missing(D.POT_COST)
        self.pay(D.POT_COST)
        self.pots += 1
        self.ui.play("fazer")
        if self.pots == 1:
            return "Fez um pote de argila. A comida guardada no acampamento agora estraga na metade do tempo."
        return "Fez mais um pote. Você tem %d." % self.pots

    def make_compost(self):
        if not self.can_pay(D.COMPOST_COST):
            self.ui.play("errado")
            return "Para o adubo falta %s." % self.missing(D.COMPOST_COST)
        self.pay(D.COMPOST_COST)
        self._add(self.base, "adubo", 1)
        self.ui.play("fazer")
        return ("Fez um adubo. Está na base: leve na mochila, vá ao campo e use na terra "
                "com a mochila.")

    def tea_hortela(self):
        if not self.fire_hours:
            return "O chá precisa da fogueira acesa."
        if self.health >= C.MAX_HEALTH:
            return "Você já está com a vida cheia."
        if not self.can_pay(D.HORTELA_COST):
            self.ui.play("errado")
            return "Para o chá falta %s." % self.missing(D.HORTELA_COST)
        self.pay(D.HORTELA_COST)
        self.health = min(C.MAX_HEALTH, self.health + C.TEA_HEAL)
        self.ui.play("cha", self.camp)
        return "Tomou o chá de hortelã. Vida %d." % self.health

    def tea_gengibre(self):
        if not self.fire_hours:
            return "O chá precisa da fogueira acesa."
        if not self.can_pay(D.GENGIBRE_COST):
            self.ui.play("errado")
            return "Para o chá falta %s." % self.missing(D.GENGIBRE_COST)
        self.pay(D.GENGIBRE_COST)
        self.warm_hours = C.GINGER_HOURS
        self.health = min(C.MAX_HEALTH, self.health + C.GINGER_HEAL)
        self.ui.play("cha", self.camp)
        return "Tomou o chá de gengibre. Vida %d, e a fome cai na metade por %d horas." % (
            self.health, C.GINGER_HOURS)

    def base_menu(self):
        """A raiz do menu do acampamento: (texto, ação). A ação é uma função que devolve a
        fala, ou um nome ("comer", "cozinhar", "fabricar", "pegar", "voltar") que abre outro
        menu. O fogo e a artemísia ficam aqui na raiz, à mão."""
        if self.fire_hours:
            items = [("Alimentar o fogo, +%d horas. %s"
                      % (D.FEED_COST["lenha"] * C.FIRE_HOURS_PER_WOOD,
                         D.cost_text(D.FEED_COST)), self.fire)]
        else:
            items = [("Acender o fogo, vários B. %s"
                      % D.cost_text(D.FIRE_COST), self.fire)]
        for key in C.SMOKE_HOURS:
            if self.total(key):
                items.append(("Queimar %s, +%d horas de fumaça. Tem %d"
                              % (D.name(key), C.SMOKE_HOURS[key], self.total(key)),
                              functools.partial(self.smoke_herb, key)))
        items.append(("Guardar tudo da mochila", self.store_all))
        foods = [k for k in D.FOODS if self.total(k)]
        if foods:
            items.append(("Comer: " + D.join(D.count(k, self.total(k)) for k in foods), "comer"))
        if self.total("carne") or self.total("hortela") or self.total("gengibre"):
            items.append(("Cozinhar", "cozinhar"))
        items.append(("Fabricar", "fabricar"))
        items.append(("Pegar do acampamento", "pegar"))
        items.append(("Voltar", "voltar"))
        return items

    def cook_menu(self):
        """Cozinhar: carne e chás (a fogueira precisa estar acesa)."""
        items = []
        if self.total("carne"):
            items.append(("Assar %s" % D.count("carne", self.total("carne")), self.cook))
        if self.total("hortela"):
            items.append(("Chá de hortelã, cura %d de vida. Custa %s"
                          % (C.TEA_HEAL, D.cost_text(D.HORTELA_COST)), self.tea_hortela))
        if self.total("gengibre"):
            items.append(("Chá de gengibre, cura %d e a fome cai na metade por %d horas. Custa %s"
                          % (C.GINGER_HEAL, C.GINGER_HOURS, D.cost_text(D.GENGIBRE_COST)),
                          self.tea_gengibre))
        items.append(("Voltar", "voltar"))
        return items

    def craft_menu(self):
        """Fabricar: arma, potes e adubo."""
        items = [("%s. Custa %s" % ("Lança nova" if self.spear else "Lança",
                                    D.cost_text(D.SPEAR_COST)), self.make_spear),
                 ("Pote de argila. Custa %s" % D.cost_text(D.POT_COST), self.make_pot)]
        if self.total("resto") or self.total("adubo"):
            items.append(("Adubo, para terra boa no campo. Custa %s"
                          % D.cost_text(D.COMPOST_COST), self.make_compost))
        items.append(("Voltar", "voltar"))
        return items

    def stored_text(self, key):
        n = len(self.base[key])
        text = "%s: %d no acampamento, %d na mochila" % (D.name(key, 2).capitalize(), n, len(self.bag[key]))
        if self.base[key] and D.ITEMS[key][4]:
            text += ", o mais velho estraga em %d horas" % int(min(self.base[key]) + 0.999)
        return text

    def bag_text(self, key):
        n = len(self.bag[key])
        text = D.count(key, n)
        if D.ITEMS[key][4]:
            text += ", estraga em %d horas" % int(min(self.bag[key]) + 0.999)
        return text

    # --- save --------------------------------------------------------------------
    FIELDS = ("hours", "x", "facing", "health", "fullness", "spear", "fire_hours", "smoke",
              "pots", "nights", "warm_hours", "heal_count", "kills", "camp", "waves", "wave_total",
              "weather")

    def to_dict(self):
        data = {f: getattr(self, f) for f in self.FIELDS}
        data["y"] = self.y
        data["map"] = self.map.to_dict()
        data["stock"] = {"%d,%d" % c: v for c, v in self.stock.items()}
        data["regrow"] = {"%d,%d" % c: v for c, v in self.regrow.items()}
        data["plots"] = {"%d,%d" % c: p for c, p in self.plots.items()}
        data["hinted"] = sorted(self.hinted)
        data["traps"] = {str(x): t for x, t in self.traps.items()}
        data["bag"] = self.bag
        data["base"] = self.base
        data["drops"] = {str(t): p for t, p in self.drops.items()}
        data["boars"] = [b.to_dict() for b in self.boars]
        data["jiangshi"] = [j.to_dict() for j in self.jiangshi]
        return data

    @classmethod
    def from_dict(cls, data, ui, rng=None, on_dawn=None, on_death=None):
        # Saves antigos não têm mapa: usam o mapa fixo de antes, de uma fileira só.
        mapa = M.Mapa.from_dict(data["map"]) if "map" in data else M.classic()
        w = cls(ui, rng, on_dawn, on_death, mapa=mapa)
        for f in cls.FIELDS:
            if f in data:
                setattr(w, f, data[f])
        w.y = data.get("y", 0)
        w.hinted = set(data.get("hinted", []))
        w.traps = {int(x): dict(t) for x, t in data.get("traps", {}).items()}
        w.waves = [list(v) for v in w.waves]
        for name in ("stock", "regrow"):
            raw = data.get(name)
            if isinstance(raw, list):                       # formato antigo: uma lista por casa
                raw = {"%d,0" % i: v for i, v in enumerate(raw)}
            for key, v in (raw or {}).items():
                x, y = key.split(",")
                getattr(w, name)[(int(x), int(y))] = v
        for key, plot in data.get("plots", {}).items():
            x, y = key.split(",")
            w.plots[(int(x), int(y))] = dict(plot)
        for name in ("bag", "base"):
            store = {k: [] for k in D.ITEMS}
            store.update({k: list(v) for k, v in data.get(name, {}).items() if k in D.ITEMS})
            setattr(w, name, store)
        w.drops = {int(t): {k: list(v) for k, v in p.items() if k in D.ITEMS}
                   for t, p in data.get("drops", {}).items()}
        for b in data.get("boars", []):
            boar = Boar(b["tile"], w.rng)
            boar.health = b["health"]
            w.boars.append(boar)
        for j in data.get("jiangshi", []):
            js = w._make_jiangshi(j["tile"])
            js.health = j["health"]
            w.jiangshi.append(js)
        return w
