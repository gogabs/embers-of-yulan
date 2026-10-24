# Origem e atualização do Mage Core

A cópia de reserva em `r36s_a11y/` corresponde à main de
[gogabs/r36s-a11y-sdk](https://github.com/gogabs/r36s-a11y-sdk) no commit
`e51b0f1deeb33c4f2b7d90e86a23c8e1b4971423`. Não há
patches exclusivos do jogo. `sdk-origin.json` registra os hashes dos arquivos.

O instalador prefere um clone do Mage Core ao lado deste repositório e usa a cópia
incluída como reserva. Para atualizar a cópia de reserva:

```sh
python3 tools/sync_sdk.py --sdk ../r36s-a11y-sdk
python3 -m unittest discover -s tests
git diff -- r36s_a11y sdk-origin.json
```
