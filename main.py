#!/usr/bin/env python3
"""Bambuzal: sobreviva às noites numa beira de rio assombrada, de ouvido."""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# Durante o desenvolvimento, usa a biblioteca do repositório vizinho se não houver cópia aqui.
if not os.path.isdir(os.path.join(HERE, "r36s_a11y")):
    sys.path.insert(1, os.path.join(HERE, "..", "r36s-a11y-sdk", "python"))

import r36s_a11y as a11y

from yulan import config as C
from yulan import data as D
from yulan import som
from yulan import tela
from yulan import texts as T
from yulan.mundo import World

game = a11y.Game(repeat=False, axes=True, deadzone=0.2)
SAVE_FILE = os.path.join(game.save_dir, "mundo.json")
sounds = {}
for f in sorted(os.listdir(os.path.join(game.dir, "sounds"))):
    base, ext = os.path.splitext(f)
    if ext.lower() in (".wav", ".ogg"):
        sounds[base] = game.sound.load(base, os.path.join("sounds", f))
menu_sounds = {"move": sounds.get("menu_mover"), "select": sounds.get("menu_confirmar"),
               "edge": sounds.get("borda")}

state = {"world": None, "playing": False}
tela.Renderer(game, lambda: state["world"] if state["playing"] else None)


# --- jogo salvo ------------------------------------------------------------------
# Um save só. Morrer apaga o save: não tem volta.
def has_save():
    return os.path.isfile(SAVE_FILE)


def write_save():
    world = state["world"]
    if world is None or not world.alive:
        return
    tmp = SAVE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"versao": 1, "mundo": world.to_dict()}, f, ensure_ascii=False)
    os.replace(tmp, SAVE_FILE)


def delete_save():
    try:
        os.remove(SAVE_FILE)
    except OSError:
        pass


# --- som e fala --------------------------------------------------------------------
class UI:
    """Ponte entre o mundo e o áudio. Onde cada casa soa fica em yulan/som.py."""

    def __init__(self):
        self.loops = {}        # chave -> (voz, casa ou None, volume, nome)
        self.x = 0

    def say(self, text, queue=False):
        game.say(text, queue=queue)

    def play(self, name, tile=None, volume=1.0, pitch=1.0):
        sound = sounds.get(name)
        if sound is None:
            return
        if tile is None:
            sound.play(volume=volume, pitch=pitch)
            return
        p = som.place(tile, self.x)
        if p is not None:
            sound.play(volume=volume * p["volume"], pitch=pitch * p["pitch"], pos=p["pos"])

    def loop(self, key, name, tile=None, volume=1.0):
        voice = self.loops.get(key, (None,))[0]
        if voice is not None and getattr(voice, "name", None) == name and voice.playing:
            self.loops[key] = (voice, tile, volume, name)
            self._place(voice, tile, volume)
            return
        if voice is not None:
            voice.stop()
        sound = sounds.get(name)
        if sound is None:
            return
        if tile is None:
            voice = sound.play(loop=True, volume=volume)
        else:
            # longe demais: começa mudo e ganha volume quando a heroína chegar perto
            p = som.place(tile, self.x) or {"pos": None, "volume": 0.0, "pitch": 1.0}
            voice = sound.play(loop=True, volume=volume * p["volume"], pitch=p["pitch"],
                               pos=p["pos"])
        voice.name = name
        self.loops[key] = (voice, tile, volume, name)

    def _place(self, voice, tile, volume):
        if tile is None:
            return
        p = som.place(tile, self.x)
        if p is None:
            voice.set_volume(0.0)
            return
        voice.set_volume(volume * p["volume"])
        voice.set_pitch(p["pitch"])
        if p["pos"] is not None:
            voice.set_position(*p["pos"])

    def stop(self, key):
        voice = self.loops.pop(key, (None,))[0]
        if voice is not None:
            voice.stop(fade=0.3)

    def stop_all(self):
        for key in list(self.loops):
            self.stop(key)

    def listen(self, x):
        self.x = x
        for voice, tile, volume, _ in self.loops.values():
            self._place(voice, tile, volume)

    def open_base(self):
        open_base_menu()


ui = UI()


# --- menus -------------------------------------------------------------------------
def make_menu(title, items, on_select, on_back):
    return a11y.Menu(game, title, items, on_select=on_select, on_back=on_back, sounds=menu_sounds)


def main_items():
    items = ["Continuar"] if has_save() else []
    return items + ["Novo jogo", "Como jogar", "Sair"]


def on_main(index, item):
    if item == "Continuar":
        continue_game()
    elif item == "Novo jogo":
        if has_save():
            main_menu.close()
            confirm_menu.open(announce_help=False)
        else:
            main_menu.close()
            new_game()
    elif item == "Como jogar":
        game.say(T.HELP)
    else:
        game.quit()


main_menu = make_menu("Embers of Yulan", ["Novo jogo"], on_main, game.quit)


def open_main():
    main_menu.items = main_items()
    main_menu.open(announce_help=False)


def on_confirm(index, item):
    confirm_menu.close()
    if item.startswith("Sim"):
        delete_save()
        new_game()
    else:
        open_main()


confirm_menu = make_menu("Começar de novo apaga o jogo que está salvo. Tem certeza?",
                         ["Não, voltar", "Sim, começar de novo"], on_confirm,
                         lambda: (confirm_menu.close(), open_main()))


def new_game():
    state["playing"] = False
    state["world"] = World(ui, random.Random(), on_dawn=write_save, on_death=on_death)
    write_save()
    game.say(T.INTRO, on_done=lambda done: begin())


def continue_game():
    try:
        with open(SAVE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        world = World.from_dict(data["mundo"], ui, random.Random(), on_dawn=write_save,
                                on_death=on_death)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("[yulan] save ilegível: %s" % exc, file=sys.stderr)
        game.say("Não deu para ler o jogo salvo.")
        return
    main_menu.close()
    state["world"] = world
    state["playing"] = True
    world.start()
    game.say("%s. %s. Vida %d." % (world.time_text(), world.terrain_name(), world.health))


def begin():
    main_menu.close()
    world = state["world"]
    if world is not None and world.alive:
        state["playing"] = True
        world.start()
        game.say("%s. Você está no acampamento." % world.time_text())


def on_death(summary):
    state["world"] = None
    state["playing"] = False
    delete_save()
    nights = summary["nights"]
    game.high_scores.add("noites", nights, board_name="Noites sobrevividas", unit="noites")
    text = T.death_text(summary)
    game.after(1.5, lambda: game.say(text, on_done=lambda done: open_main()))


# pausa
def on_pause(index, item):
    pause_menu.close()
    if item == "Como jogar":
        game.say(T.HELP, on_done=lambda done: open_pause(index))
    elif item == "Salvar e sair":
        write_save()
        ui.stop_all()
        state["world"] = None
        state["playing"] = False
        game.say("Jogo salvo.", on_done=lambda done: open_main())
    else:
        game.say("Continuando.")


def pause_items():
    return ["Continuar", "Como jogar", "Salvar e sair"]


def open_pause(index=0):
    pause_menu.items = pause_items()
    pause_menu.open(index=index, announce_help=False)


pause_menu = make_menu("Pausa", pause_items(), on_pause, lambda: on_pause(0, "Continuar"))


# base
def open_base_menu(index=0):
    world = state["world"]
    base_menu.items = [text for text, _ in world.base_menu()]
    base_menu.open(index=min(index, len(base_menu.items) - 1), announce_help=False)


SUBMENUS = {"cozinhar": ("Cozinhar", lambda w: w.cook_menu()),
            "fabricar": ("Fabricar", lambda w: w.craft_menu())}


def on_base(index, item):
    world = state["world"]
    text, action = world.base_menu()[index]
    if action == "comer":
        base_menu.close()
        open_eat_menu()
    elif action == "pegar":
        base_menu.close()
        open_take_menu()
    elif action in SUBMENUS:
        base_menu.close()
        open_sub_menu(action)
    elif action == "voltar":
        base_menu.close()
        game.say("Acampamento.")
    else:
        said = action()
        if world.task is not None:          # a fogueira pede vários B: fecha o menu para apertar
            base_menu.close()
            write_save()
            return
        write_save()
        base_menu.items = [t for t, _ in world.base_menu()]
        base_menu.index = min(index, len(base_menu.items) - 1)
        game.say(said)


base_menu = make_menu("Acampamento", ["Voltar"], on_base, lambda: on_base_back())


def on_base_back():
    base_menu.close()
    game.say("Acampamento.")


# Cozinhar e Fabricar: dois menus pequenos, com Voltar para a raiz do acampamento.
sub = {"kind": None}


def open_sub_menu(kind, index=0):
    sub["kind"] = kind
    title, build = SUBMENUS[kind]
    sub_menu.title = title
    sub_menu.items = [t for t, _ in build(state["world"])]
    sub_menu.open(index=min(index, len(sub_menu.items) - 1), announce_help=False)


def on_sub(index, item):
    world = state["world"]
    title, build = SUBMENUS[sub["kind"]]
    text, action = build(world)[index]
    if action == "voltar":
        sub_menu.close()
        open_base_menu()
        return
    said = action()
    write_save()
    sub_menu.items = [t for t, _ in build(world)]
    sub_menu.index = min(index, len(sub_menu.items) - 1)
    game.say(said)


sub_menu = make_menu("Cozinhar", ["Voltar"], on_sub, lambda: (sub_menu.close(), open_base_menu()))


def eat_items():
    world = state["world"]
    return [world.stored_text(k) if not world.bag[k] else
            "%s: %d na mochila, %d no acampamento" % (D.name(k, 2).capitalize(), len(world.bag[k]),
                                               len(world.base[k]))
            for k in eat_keys()] + ["Voltar"]


def eat_keys():
    world = state["world"]
    return [k for k in D.FOODS if world.total(k)]


def open_eat_menu(index=0):
    eat_menu.items = eat_items()
    eat_menu.title = "Comer. " + state["world"].fullness_text()
    eat_menu.open(index=min(index, len(eat_menu.items) - 1), announce_help=False)


def on_eat(index, item):
    keys = eat_keys()
    if index >= len(keys):
        eat_menu.close()
        open_base_menu()
        return
    said = state["world"].eat(keys[index])
    write_save()
    eat_menu.items = eat_items()
    eat_menu.index = min(index, len(eat_menu.items) - 1)
    game.say(said)


eat_menu = make_menu("Comer", ["Voltar"], on_eat, lambda: (eat_menu.close(), open_base_menu()))


def take_keys():
    world = state["world"]
    return [k for k in D.ITEM_ORDER if world.base[k]]


def open_take_menu(index=0):
    world = state["world"]
    take_menu.items = [world.stored_text(k) for k in take_keys()] + ["Voltar"]
    take_menu.title = "Pegar. Mochila %d de %d" % (world.bag_count(), C.CARRY_LIMIT)
    take_menu.open(index=min(index, len(take_menu.items) - 1), announce_help=False)


def on_take(index, item):
    keys = take_keys()
    if index >= len(keys):
        take_menu.close()
        open_base_menu()
        return
    said = state["world"].take(keys[index])
    write_save()
    world = state["world"]
    take_menu.items = [world.stored_text(k) for k in take_keys()] + ["Voltar"]
    take_menu.index = min(index, len(take_menu.items) - 1)
    game.say(said)


take_menu = make_menu("Pegar", ["Voltar"], on_take, lambda: (take_menu.close(), open_base_menu()))


# mochila
def bag_entries():
    """O que a mochila mostra, em ordem: a lança, as ações do lugar (montar acampamento,
    armadilhas) e os itens. Cada entrada: (texto, tipo, dado)."""
    world = state["world"]
    entries = []
    if world.spear:
        entries.append(("Lança, %d de %d" % (world.spear, C.SPEAR_DURABILITY), "spear", None))
    for text, fn in world.field_actions():
        entries.append((text, "action", fn))
    hints = {"adubo": ", B espalha no campo", "semente": ", B planta em terra boa"}
    for k in D.ITEM_ORDER:
        if world.bag[k]:
            entries.append((world.bag_text(k) + (", B come" if k in D.FOODS else hints.get(k, "")),
                            "item", k))
    return entries


def bag_items():
    return [text for text, _, _ in bag_entries()] + ["Voltar"]


def open_bag(index=0):
    world = state["world"]
    bag_menu.items = bag_items()
    bag_menu.title = "Mochila, %d de %d" % (world.bag_count(), C.CARRY_LIMIT)
    if bag_menu.items == ["Voltar"]:
        game.say("A mochila está vazia.")
        return
    bag_menu.open(index=min(index, len(bag_menu.items) - 1), announce_help=False)


def refresh_bag(index, said):
    write_save()
    bag_menu.items = bag_items()
    bag_menu.index = min(index, len(bag_menu.items) - 1)
    game.say(said)


def on_bag(index, item):
    world = state["world"]
    entries = bag_entries()
    if item == "Voltar" or index >= len(entries):
        bag_menu.close()
        game.say("Fechou a mochila.")
        return
    _, kind, data = entries[index]
    if kind == "spear":
        game.say("Y ataca com a lança para o lado em que você está olhando.")
    elif kind == "action":
        said = data()
        if world.task is not None:          # pede vários B: fecha a mochila para apertar
            bag_menu.close()
            return
        refresh_bag(index, said)
    elif data == "adubo":
        said = world.use_compost()
        if world.task is not None:
            bag_menu.close()
            return
        game.say(said)
    elif data == "semente":
        refresh_bag(index, world.plant())
    elif data not in D.FOODS:
        game.say("Leve ao acampamento e guarde com B.")
    else:
        refresh_bag(index, world.eat(data))


bag_menu = make_menu("Mochila", ["Voltar"], on_bag,
                     lambda: (bag_menu.close(), game.say("Fechou a mochila.")))


# --- laço ------------------------------------------------------------------------------
@game.on_button
def on_button(button, st, ms):
    world = state["world"]
    if world is None or not world.alive or not state["playing"]:
        return
    if st == a11y.UP:
        world.release(button)
        return
    if st != a11y.DOWN:
        return
    if button == "start":
        world.release("left")
        world.release("right")
        stick["dir"] = 0
        open_pause()
    elif button == "x":
        world.release("left")
        world.release("right")
        stick["dir"] = 0
        open_bag()
    else:
        world.press(button)


# Analógico esquerdo anda como o direcional. Só liga/desliga ao passar da zona morta,
# então o mundo continua recebendo o mesmo "esquerda"/"direita" de sempre.
stick = {"dir": 0}


def stick_release():
    world = state["world"]
    if stick["dir"] and world is not None:
        world.release("left" if stick["dir"] < 0 else "right")
    stick["dir"] = 0


@game.on_axis
def on_axis(axis, value, ms):
    if axis != "lx":
        return
    world = state["world"]
    if world is None or not world.alive or not state["playing"] or game._focus:
        stick_release()
        return
    direction = -1 if value <= -C.STICK_DEADZONE else 1 if value >= C.STICK_DEADZONE else 0
    if direction == stick["dir"]:
        return
    stick_release()
    stick["dir"] = direction
    if direction:
        world.press("left" if direction < 0 else "right")


@game.on_update
def update(dt):
    world = state["world"]
    # Menus abertos param o tempo: nada acontece enquanto você escolhe.
    if world is None or not state["playing"] or game._focus:
        return
    world.update(min(dt, 0.25))


@game.on_start
def start():
    open_main()


@game.on_quit
def quit_game():
    write_save()


if __name__ == "__main__":
    game.run()
