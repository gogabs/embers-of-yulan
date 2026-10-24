"""Falas longas do jogo."""

INTRO = ("Você acordou numa clareira à beira de um rio assombrado, ao lado da sua fogueira. "
         "A leste ficam o campo, o bambuzal, o cascalho e, no fim, o rio. De dia, procure comida, "
         "bambu e ervas, e arme buracos e estacas na frente do acampamento. De noite, o sino avisa "
         "cada onda de mortos que sai do rio e vem pulando até você. Mantenha a fogueira acesa e "
         "queime artemísia nela: a fumaça os segura na beira. Você só tem uma vida. "
         "Select diz como você está. Start pausa e explica os botões.")

HELP = ("Esquerda e direita, ou o analógico esquerdo, andam. "
        "B é o verbo do lugar: fora do acampamento tateia o chão ou pega o que caiu, no bambuzal "
        "corta bambu com vários toques, na plantação cuida dela, e no acampamento abre o menu, "
        "para alimentar o fogo (vários toques para acender), queimar artemísia, guardar, comer, "
        "cozinhar (carne e chás) e fabricar (lança, pote e adubo). "
        "A fogueira só queima lenha, e é preciso bastante; bambu é para lança e estacas. "
        "De noite, a artemísia queimada faz fumaça que segura os jiangshi na beira do acampamento, "
        "mas cada golpe deles come fumaça e fogo. O sino avisa cada onda, e ao entardecer o "
        "céu avisa o clima da noite: lua cheia, chuva ou neblina. "
        "Y ataca para o lado em que você está olhando. Ao virar para um bicho, um tique no centro "
        "avisa que ele está na mira: mais agudo quanto mais perto. "
        "A diz o que tem aqui e quem está perto. "
        "L1 e R1 dizem o próximo ponto à esquerda e à direita. "
        "X abre a mochila, onde você também come, espalha adubo, planta, monta o acampamento "
        "em outro lugar e arma estacas e buracos. "
        "Select diz a fase do dia, a vida, a fome e a fogueira. "
        "Start pausa. "
        "O jogo salva sozinho a cada amanhecer e ao sair. Se você morrer, o jogo salvo "
        "acaba.")


PHASE_WHEN = {"alvorada": "na alvorada", "manhã": "de manhã", "meio-dia": "ao meio-dia",
              "tarde": "à tarde", "anoitecendo": "ao anoitecer", "noite": "de noite"}


def phase_when(phase):
    return PHASE_WHEN[phase]


def death_text(summary):
    nights = summary["nights"]
    if nights == 0:
        survived = "Não chegou a ver um amanhecer."
    elif nights == 1:
        survived = "Sobreviveu a 1 noite."
    else:
        survived = "Sobreviveu a %d noites." % nights
    kills = summary["kills"]
    hunt = []
    if kills.get("javali"):
        hunt.append("%d %s" % (kills["javali"], "javali" if kills["javali"] == 1 else "javalis"))
    if kills.get("jiangshi"):
        hunt.append("%d jiangshi" % kills["jiangshi"])
    text = "Você morreu %s, no dia %d, %s. %s" % (
        summary["cause"], summary["day"], phase_when(summary["phase"]), survived)
    if hunt:
        text += " Derrubou " + " e ".join(hunt) + "."
    return text + " Este mundo acabou."
