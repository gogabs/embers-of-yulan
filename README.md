# Embers of Yulan

Jogo de áudio de sobrevivência para o R36S acessível, jogável só com som e
fala. Você vive numa faixa de terra à beira de um rio assombrado: de dia
procura comida e material no campo, no bambuzal, no cascalho e na margem; de
noite, os jiangshi, mortos que andam aos pulos, saem do rio em ondas, avisadas
por um sino, e vêm até a sua fogueira. Um único jogo salvo e uma vida só: se você morrer, aquele mundo
acaba.

Inspirado no Draugnorak, um audio game em NVGT, mas
escrito do zero, com outra ambientação (fantasia do leste asiático) e
outras regras: a fome é sua, a fogueira é que precisa ser mantida de pé e a morte é
para valer.

Este é um protótipo: um dia e uma noite de sobrevivência, que se repetem e ficam
mais difíceis. Luas, neblina, chuva, estações e moedas ficam para as próximas
fases.

Feito em Python com o [Mage Core](https://github.com/gogabs/r36s-a11y-sdk).

## Controles

| Botão | O quê |
|---|---|
| Esquerda / direita (direcional ou analógico esquerdo) | Anda (segure para continuar). Virar para um lado faz um som curto |
| B | O verbo do lugar: fora do acampamento tateia o chão ou pega o que caiu; na plantação cuida dela; no bambuzal, aperte B várias vezes para cortar um bambu; no acampamento abre o menu do acampamento |
| Y | Ataca para o lado em que você está olhando (soco, ou lança, que alcança 2 casas) |
| A | O que tem aqui: terreno, se ainda tem o que achar, o que está no chão e quem está perto |
| L1 / R1 | O próximo ponto à esquerda / à direita: acampamento, terrenos, plantações, armadilhas, coisas no chão, bichos |
| X | Mochila; escolher uma comida come, o adubo espalha, a semente planta; fora do acampamento também monta o acampamento e arma estacas e buracos |
| Select | Fase do dia, vida, fome, mochila, lança, fogueira e fumaça |
| Start | Pausa: continuar, como jogar, salvar e sair |

Menus abertos param o tempo.

## Sem depender de estéreo

O jogo usa som 3D (cada coisa toca do lado em que está), mas nada precisa
dele para ser jogável sem fone: A, L1 e R1 dizem o lado e a distância por
voz, e **ao virar para um bicho toca um "tic" no centro**, mais agudo quanto
mais perto (até 8 casas), e um som duplo quando ele já está ao alcance da
arma. Assim dá para mirar sem saber de que lado ele soa.

O mundo nunca sabe de esquerda e direita: ele só diz "toque isto na casa N".
Quem decide como a casa N soa é `bambuzal/som.py`, então trocar o estéreo por
outra coisa no futuro é mexer numa função só.

## Na tela

O jogo é feito para ser jogado só pelo som, e tudo o que aparece na tela
também é falado. A tela mostra a faixa de terra de lado, com a câmera
seguindo a heroína: o céu muda com a fase do dia, as montanhas e um pagode ao fundo,
cada terreno com o seu chão, a tenda e a fogueira do acampamento (com a fumaça
de erva subindo), as armadilhas, os bichos, as barras de vida, saciedade e
fumaça, e a última fala como legenda. Segue a opção de tela do sistema e a
economia de energia.

| Campo, de manhã | Noite no acampamento |
|---|---|
| ![Javali no campo](docs/telas/campo-javali.png) | ![Noite no acampamento](docs/telas/noite-fumaca.png) |
| ![Bambuzal](docs/telas/bambuzal.png) | ![Entardecer no acampamento](docs/telas/entardecer-acampamento.png) |

A heroína (quimono cinza de mangas largas, faixa marrom, calça verde-musgo, sandálias de palha e pontas do cabelo azuis; serena no dia a dia, firme quando um bicho chega perto), o javali e o jiangshi são desenhos vetoriais: a fonte é
`tools/arte.py`, que escreve os SVG em `art/`; `tools/gerar_imagens.py` (com
o CairoSVG) os converte nos PNG de `images/`, que o console desenha. As
prévias saem de `python3 tools/previas.py` (com a Pillow).

## O mapa

O mapa é sorteado a cada jogo: uma grade de 58 casas por 1 fileira, de oeste para
leste (a grade já aceita mais fileiras, para uma navegação em 2D no futuro). Só a
margem do rio fica sempre no fim; o resto é sorteado. Cada chão tem o seu passo.

| Terreno | Onde | O que se acha |
|---|---|---|
| Campo | O chão de sempre, a partir do começo | **Lenha (o mais comum)**, fruta silvestre, cipó, pedra, hortelã, semente de nabo, um pouco de artemísia |
| Bambuzal | 3 ou 4 focos, o primeiro perto do começo | Bambu, broto de bambu, cipó, gengibre |
| Cascalho | 1 ou 2 trechos, mais longe | Pedra, artemísia (aqui é onde mais aparece) |
| Margem do rio | Últimas 4 casas | Argila, pedra, hortelã, um pouco de artemísia |
| Terra boa | Retalhos de 1 a 3 casas no campo | Dá para plantar |

Cada casa tem pouco para achar (2 coisas) e volta a ter devagar (1 a cada 14 horas),
então é preciso ir cada vez mais longe. B no chão é um tateio rápido com a mão: cada
toque só tem 30% de chance de pegar algo, e quando não pega fica em silêncio. Quando
pega, o jogo diz o que foi. No bambuzal, B corta o bambu com vários toques.

## O acampamento

Não há casa nem muro: o acampamento é a fogueira, com o cesto onde se guarda tudo e
os potes, e um círculo de 2 casas para cada lado, onde você se cura e B abre o menu.
Você começa com um acampamento já montado, mas pode **montar outro em qualquer lugar**
(mochila, "Montar o acampamento aqui", vários B). As coisas guardadas vão junto; a
fogueira velha fica para trás.

## Horta e ervas

## Horta e ervas

- **Terra boa:** há retalhos de terra boa espalhados pelo campo. Para fazer a sua,
  junte restos de comida (comer fruta, broto ou nabo deixa um resto, e o que estraga
  também vira resto), faça adubo no acampamento (3 restos), leve na mochila ao campo e
  escolha o adubo na mochila: B várias vezes espalha, e a casa vira terra boa.
- **Plantar:** semente de nabo se acha no campo. Na terra boa, escolha a semente na
  mochila. O nabo leva 36 horas; no meio do caminho o mato aparece e o nabo para de
  crescer até você capinar (B várias vezes). Maduro, B colhe: 3 nabos e 1 semente de volta.
- **Chás:** no acampamento, com a fogueira acesa, 2 hortelãs viram um chá que cura 3 de vida,
  e 2 raízes de gengibre um chá que cura 1 e faz a fome cair na metade por 12 horas.
  As ervas estragam em 60 horas (a artemísia, em 72).

## Como se sobrevive

- **Fome:** a saciedade cai 4 por hora. Com fome você anda mais devagar e
  não se cura; faminto, perde vida. Comida estraga: fruta em 24 horas,
  broto em 36, nabo em 60, carne crua em 14, carne assada em 48.
- **Acampamento:** cura 1 de vida a cada 2 horas (1 por hora com a fogueira acesa).
  O menu guarda tudo, come, acende (8 toques de B) e alimenta a fogueira, põe erva no
  fogo, assa carne, faz adubo, chá, a lança (2 bambus, 1 pedra e 1 cipó, dura 40 golpes)
  e o pote de argila (3 torrões, com a fogueira acesa), que faz a comida guardada
  estragar na metade do tempo. O menu tem, na raiz, **Alimentar o fogo** (ou Acender)
  e **Queimar artemísia**, e depois Guardar tudo, Comer, **Cozinhar** (carne e chás),
  **Fabricar** (lança, pote e adubo) e Pegar.
- **Lenha e fogo:** a fogueira só queima **lenha**, e é preciso bastante: acender custa
  4 lenhas e 2 pedras, e cada 4 lenhas a mais dão 4 horas. Uma noite pede mais de 10
  lenhas (o dobro na chuva). A lenha vem do campo, tem lugar à parte na mochila (até 40) e o
  **bambu não alimenta mais o fogo**: serve só para lança e estacas.
- **Dia:** às vezes aparece um javali no campo ou no bambuzal. Chegue perto
  e ele investe. Abatido, deixa 2 carnes cruas no chão. De dia também se preparam as
  armadilhas (veja abaixo) e se junta erva para a noite.
- **Noite:** das 19h às 6h. A fogueira precisa ficar acesa a noite toda, e é a erva
  jogada nela que espanta os jiangshi: só a **artemísia** faz fumaça (hortelã e
  gengibre são só para chá). Com fumaça, eles só chegam à beira do
  acampamento (2 casas além da fogueira, a leste) e ali ficam golpeando; **cada golpe
  come um pouco da fumaça e do fogo**. Sem fumaça, eles vão atrás de você. Fora do
  acampamento eles também perseguem quem chega perto. Cada artemísia dá 8 horas de
  fumaça (até 16 juntas). O crepitar da fogueira muda quando há
  fumaça, e um aviso toca quando ela está acabando.
- **Ondas:** a cada noite o **sino** avisa cada onda: 3 jiangshi na primeira noite e 3 a
  mais a cada noite (até 20), repartidos em 2 ondas (uma a mais a cada duas noites, até
  5), entre 20h e 4h. A cada noite eles ficam mais duros, pulam mais depressa e batem
  mais seguido. Ao amanhecer, os que sobraram viram pó.
- **Clima da noite:** ao entardecer o céu avisa como será a noite (a primeira é sempre
  limpa). **Lua cheia:** as plantações crescem 3 vezes mais depressa. **Chuva:** o fogo e a
  fumaça queimam o dobro. **Neblina:** os jiangshi saem mais duros, mais rápidos e
  machucam mais. Cada clima tem o seu som e o seu desenho na tela.
- **Armadilhas:** pela mochila, fora do acampamento: a **estaca** (2 bambus, vários B)
  fere quem pisar, 3 vezes; o **buraco** (de graça, vários B) prende por 6 segundos e
  fere um pouco, 2 vezes. Servem também contra javalis. Ponha na frente do acampamento,
  a leste, por onde eles vêm.
- **Save:** o jogo salva a cada amanhecer, a cada escolha nos menus do acampamento
  e ao sair. Morrer apaga o jogo salvo e guarda as noites sobrevividas nos
  recordes.

## Sons

Os sons de `sounds/` são provisórios, gerados por `python3 tools/gerar_sons.py`
só com a biblioteca padrão. Para trocar um, ponha um arquivo com o mesmo nome
(WAV ou OGG) e apague o provisório.

A fogueira, os sons do jiangshi (pulo, ataque, aparece, destruído) e os da heroína
(passos, golpe, esforço, dor e morte) vêm da web ou da biblioteca de sons do autor,
e o gerador não os sobrescreve. Passos, golpe e esforço têm variações
(`passo_campo_1.wav` a `_5`, `golpe_1` a `_3`, `esforco_1` a `_4`), sorteadas sem repetir. Autores e links estão em
`CREDITOS-SONS.md`. O pulo é a exceção: foi gerado à parte, com o grave do
anterior e sem o chiado.

## Desenvolvimento

```sh
python3 -m unittest discover -s tests     # testes
python3 tools/simular.py 12               # joga sozinho e mostra quantas noites aguenta
./instalar.sh                             # instala no console (veja o script)
```

Os números do equilíbrio ficam todos em `bambuzal/config.py`. Na simulação,
um jogador parado no acampamento morre na primeira noite, e um jogador razoável
(sai de dia, junta erva e bambu, arma buracos, volta antes de escurecer, mantém o
fogo e a fumaça e luta da beira) aguenta 6 noites na mediana. Um dia dura 12
minutos (30 segundos por hora). O jogo nunca diz a hora: só a fase do dia (alvorada,
manhã, meio-dia, tarde, anoitecendo e noite), anunciada quando muda.

Licença MIT.
