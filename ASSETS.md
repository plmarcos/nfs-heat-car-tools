# Usar os modelos do NFS Heat

Guia de quem vai abrir estes arquivos no Blender, num motor de jogo ou num
projeto próprio. Tudo aqui foi **medido nos arquivos**, não estimado; onde não
deu para medir, está escrito que não deu.

Unidade de tamanho: **MiB** (1.048.576 bytes) em todo o documento.

---

## De quem é esse material

Os modelos, as texturas e as liveries são da **Electronic Arts**. Nada foi criado
por quem extraiu — são os arquivos do jogo, convertidos de formato. Este projeto
não tem vínculo com a EA nem com a Criterion Games, e não vem com licença
nenhuma delas.

O **código** das ferramentas é MIT. Os **modelos não são.** Quem usar assume a
responsabilidade: estudo, render pessoal, mod para o próprio jogo e portfólio com
crédito são um terreno; vender o modelo, embarcar num jogo seu ou publicar como
trabalho original são outro.

---

## O que tem dentro

49.452 arquivos, **9,98 GiB**. Por peso: 70,3% OBJ, 23,0% PNG, 6,6% FBX.

```
<raiz>/
  car_bmw_m3e46_2003/
    car_bmw_m3e46_2003.obj        carroceria (+ .mtl ao lado)
    car_bmw_m3e46_2003.fbx        a MESMA malha, com as normais  <- leia abaixo
    car_bmw_m3e46_2003_wheel.obj  só o aro, sem pneu
    car_bmw_m3e46_2003_com_rodas.obj   carro montado, pronto
    car_bmw_m3e46_2003_lowpoly.obj     versão leve (outro formato!)
    parts/                        peças de fábrica, uma por slot
    mods/<slot>/                  variantes de customização
    textures/                     PNG do carro
  _pneu/                          malha do pneu, compartilhada (3 arquivos)
  _texturas_rodas/                PNG de aro e pneu (só PNG, nenhum OBJ)
  _liveries/  _swatches/  _vinis_gerados/
  _indice.csv  _mods_indice.csv  _mods_mapa.csv
  _rodas_eixos.csv  _ficha_tecnica.csv  _mods_relatorio.csv
```

| | |
|---|---|
| carrocerias | **168** OBJ (169 pastas — `car_porsche_carreras_2014` só tem `mods/`) |
| peças de fábrica | **3.751** em `parts/`, em 164 carros |
| peças de customização | **13.834** em `mods/`, em 104 carros, 65 slots |
| texturas | **6.132** em `textures/` + 442 de roda + 5.182 de vinil |
| liveries | **126** (252 arquivos `_d`+`_m`) + 6 wraps de derelict = 258 PNG |
| triângulos | 13,8 milhões nas carrocerias, 36,9 milhões nos mods |

---

## As cinco coisas que mudam o resultado

### 1. É metro, Y para cima, +Z é a frente, +X é a esquerda

Sistema destro, o mesmo do OpenGL e do three.js. Confirmado em **158 de 158**
carros pelo par farol/lanterna, e **159 de 159** pelo par de retrovisores.
A origem fica na linha de centro (X = 0 exato) e perto do chão.

A escala é fiel em **comprimento e largura** — o M3 E46 sai com 4.492,8 mm
contra 4.492 de ficha, erro de +0,02%. **Mas a altura lê baixo**, de 8% a 17%:

| | modelo | real | |
|---|---|---|---|
| BMW M3 E46 | 1.254,9 mm | 1.372 mm | −8,5% |
| Nissan Skyline R34 | 1.191,3 mm | 1.360 mm | −12,4% |
| Ford F-150 Raptor | 1.742,0 mm | 1.995 mm | −12,7% |
| VW Fusca 1963 | 1.240,3 mm | 1.500 mm | −17,3% |

Medido do teto até Y = 0, que é onde o pneu assenta. **Não use estes modelos
para tirar altura de carro.** Comprimento e largura, pode.

### 2. Não há normal nos OBJ — e soldar vértice estraga a malha

**Nenhum** dos 18.088 OBJ extraídos tem linha `vn` (censo, não amostra). O
Blender traz os 62.768 polígonos do M3 em *flat*.

A tentação é rodar **Merge by Distance** e suavizar. Não faça: a malha **já vem
partida nas quinas**, e de 72% a 87% das posições duplicadas têm normais
divergindo **mais de 30°** (mediana de 50° a 85°). Soldar derrete a quina entre
capô e carroceria, e o painel vira uma superfície só.

O certo é **Shade Auto Smooth** com ângulo em torno de 30°, sem soldar.

### 3. O FBX não é arquivo repetido — é onde estão as normais

Cada pasta tem um `.fbx` com a **mesma malha** do OBJ (mesmos 20 materiais,
mesmos nomes) e as **normais divididas** que o OBJ perdeu. No objeto `base` do
M3, **71,4% dos vértices têm mais de uma normal** (até 34 num mesmo vértice).

Recalcular no lugar de usar as originais erra pouco na mediana e muito na cauda:

| | erro angular |
|---|---|
| mediana | 3,23° |
| p90 | **26,48°** |
| máximo | 130,78° |

Os 26° do p90 estão exatamente nas quinas, que é onde se vê.

**Mas o FBX não tem nenhuma referência a textura** — zero `Texture`, zero
`RelativeFilename`, zero `.png`. Os dois formatos são complementares:

> **FBX para a geometria, MTL do OBJ para achar as texturas.**

### 4. Mais da metade das texturas não está ligada a material nenhum

Cruzando os 18.088 `.mtl` com os 6.132 PNG de `textures/`: **2.388 referenciados,
3.744 órfãos — 61,1%.**

Ficam de fora **todos** os `_m` (1.409), **todos** os `_mask` (196) e **todos**
os `_nd` (252), mais 573 `_d`, 545 `_n`, 330 `_e`, 269 `_no`.

E dos materiais que o OBJ realmente usa, **67% não têm textura nenhuma** — são
`Kd 0.800` chapado. No M3, o Blender carrega **12 imagens para 20 materiais**.

> Importar OBJ+MTL traz metade da lataria pronta e **nenhum mapa PBR**. O resto
> é trabalho manual. É o fato mais importante deste documento.

Existem exatamente quatro chaves de mapa em todo o acervo — nenhum `map_Ks`,
`map_d`, `map_Ns`, `map_Pr` ou `map_Pm`:

| chave | puxa |
|---|---|
| `map_Kd` | `_d` |
| `map_Bump` / `bump` | `_no`, `_n`, `_na` |
| `map_Ke` | `_e`, `_ea` |

### 5. A lataria não tem textura, e isso não é erro

Zero arquivos com `carpaint` ou `paint` em qualquer `textures/`, num censo de
12.121 PNG. A pintura do Heat é **procedural**: cor mais acabamento, composta em
tempo de execução. Não existe o que procurar.

As liveries são arte separada, com máscara, em `_liveries/`.

---

## Texturas, canal por canal

| sufixo | o que é | espaço de cor |
|---|---|---|
| `_d` | cor base | sRGB |
| `_n` `_no` `_nd` `_na` | normal | linear |
| `_m` | máscara empacotada | linear |
| `_e` `_ea` | emissivo | sRGB |
| `_mask` | máscara de dano/variante | linear |

O sufixo `a` indica alfa presente, mas a **ausência dele não garante que não
tem**.

### Normal de dois canais: reconstrua o Z

Boa parte dos mapas de normal traz o **canal azul zerado** — são normais de dois
canais, do formato BC5 original, não falha da extração:

| sufixo | com B zerado |
|---|---|
| `_n` | **75,8%** (787 de 1.038) |
| `_nd` | 29,4% |
| `_no` | 4,7% |
| `_na` | 0% |

Reconstrução: `z = sqrt(1 − x² − y²)`, com **x e y normalizados antes**. Isso não
é detalhe: **85,2% dos mapas de normal têm ao menos um pixel com x² + y² > 1**, e
num deles isso vale para 99,5% da imagem. Sem normalizar, o `sqrt` devolve NaN e
a textura sai com buracos pretos.

### A máscara `_m`

Medido canal a canal, no censo:

- **R é metalicidade** — tecido 0,0, refletor cromado 206,4. Quase 1 bit em 63,7%
  dos arquivos.
- **G é suavidade** — tecido 27,6, cromo 231,4. Se fosse rugosidade seria o
  contrário. É o único canal contínuo. Para usar como `roughness`: **inverta**.
- **B não é oclusão usável.** Dentro da ilha de UV, 90,3% dos pixels são
  exatamente 255; a correlação com a inclinação do relevo é +0,061 (oclusão daria
  negativa); e 19,3% dos arquivos têm B zero na imagem inteira. Comporta-se como
  máscara de cobertura. **O que o motor faz com ele, não sei.**

Exceção: o `_m` do pneu em `_texturas_rodas/tires/` tem R médio 245,9 — ali o R
**não** é metalicidade.

### Duas armadilhas de importação

**O Blender carrega toda imagem do MTL como sRGB.** Medido: importando o M3 em
`--factory-startup`, as 12 imagens vêm sRGB — inclusive os cinco mapas de normal.
Tem que corrigir para *Non-Color* na mão, ou o relevo sai errado.

**Orientação do canal verde (OpenGL × DirectX): não medi.** É a primeira pergunta
de quem monta material, e com o G invertido o relevo inteiro aponta para o lado
errado sem ninguém notar até bater luz rasante. Fica **em aberto** — se você
medir, o resultado é bem-vindo.

---

## Montar o carro

**Toda peça já está no espaço da carroceria.** `parts/<slot>.obj` é bit a bit o
mesmo objeto de nome igual dentro de `<carro>.obj` — delta de centróide
exatamente zero em **3.707 de 3.751 pares**. Montar é:

1. esconder o objeto homônimo na carroceria;
2. soltar o arquivo da peça no lugar, **sem transformação nenhuma**.

Vale até quando a peça vem da pasta de outro carro: em 40 de 51 pares
doador/receptor a diferença de centro é exatamente 0,0 mm.

### O que não é peça

44 arquivos de `mods/` não têm objeto homônimo na carroceria. Desses, **41 são
lixo** e estragam o modelo:

- **5 cópias do carro inteiro** — dobram a geometria no mesmo lugar;
- **19 faróis animados** — estão no espaço local do pivô, não no do carro (o do
  F40 é uma caixa de 30 cm colada na origem, enquanto os faróis estão em Z ≈ +2,0
  m). A transformação de runtime **não está no acervo**;
- **17 peças de aero ativo** — mesma história.

Os outros 3 são peça boa (chassi da C10, `bumperr` e `suspensionr` do Defender).

> O critério que separa peça de não-peça **não** é o nome nem "desce abaixo do
> chão" — é **não ter objeto homônimo na carroceria**. Filtrar por nome pega só
> 24 dos 41.

### Slot vazio disfarçado de peça

Existe placeholder de "sem peça" em três lugares:

- **36 em `mods/`** — no M3, a primeira variante de `diffuser` tem bbox de
  38 × 11 × 6 mm;
- **30 em `parts/`** com 4 triângulos ou menos;
- **29 objetos dentro de 22 carrocerias** com 6 vértices ou menos — `roof` nos
  quatro Corvette, `fenderfl`/`fenderfr` do F40, `spoiler` do NSX Type R.

Quem montar um menu a partir dos objetos da carroceria vai listar slot vazio como
se fosse peça. E abrir a primeira variante de um slot para descobrir onde ele
fica **não funciona**.

---

## Rodas

**O `_wheel.obj` é só o aro.** O pneu é malha compartilhada e está em `_pneu/`
(3 arquivos: `race01`, `drift01`, `offroad01`). A pasta `_texturas_rodas/` tem
**só PNG**, nenhum OBJ.

O eixo de giro é **X**. `wheelr` é de *rear*, não de *right* — montar o aro
traseiro na frente é o erro clássico.

Os 166 arquivos não têm todos a mesma forma: 68 têm 1 objeto, 90 têm 2, e as 4
motos têm 8 (aro, pneu, disco e pinça, dos dois eixos).

### A regra que importa

**O aro assenta no talão do pneu**, não na escala do pneu. O raio nativo do aro
varia de 0,18 a 0,50 m entre os carros — dividir uma escala só entre aro e pneu
deforma o aro. No Polestar 1 o aro nativo (0,3163) é do tamanho do pneu inteiro
(0,3165) e a roda sai como um disco liso; no reboque o aro monta a 0,87 m num
pneu de 0,55 e atravessa a borracha.

```
s_pneu = raio_alvo / raio_nativo_do_pneu
talao  = raio_interno_do_pneu * s_pneu
s_aro  = talao * 1.02 / raio_nativo_do_aro     <- 2% de lábio
largura do aro: a mesma escala do pneu, não a do raio
```

`_rodas_eixos.csv` traz diâmetro, largura, meia-bitola e a posição em Z de cada
eixo, medidos por carro. **`meia_bitola` já é o X do centro da roda** — não
desconte largura de pneu dela.

Conferido nos 166 carros / 332 eixos com essa regra: borracha aparente de
**64,6 a 125,6 mm**, mediana 75,4, **zero negativos**.

**Se você só quer o carro pronto, use o `_com_rodas.obj`** — ele já vem montado
assim. Só lembre que ele herda os defeitos da carroceria: os mesmos 3,15 milhões
de vértices órfãos, sem `vn`, e a fração de UV fora de [0,1] sobe para 41,1%.
Nas 4 motos ele traz só os dois aros, sem pneu e sem o lado direito.

---

## Os arquivos de índice

| arquivo | BOM | decimal |
|---|---|---|
| `_indice.csv` | sim | — |
| `_rodas_eixos.csv` | sim | **ponto** |
| `_ficha_tecnica.csv` | sim | **vírgula** |
| `_mods_relatorio.csv` | sim | **vírgula** |
| `_mods_indice.csv` | **não** | — |
| `_mods_mapa.csv` | **não** | — |

Todos em CRLF. Leia com `utf-8-sig` sempre — resolve os dois casos.

`_mods_indice.csv` é exato nas 13.834 linhas, em `triangulos` e em `bytes`.
`_indice.csv` esteve desatualizado (a coluna `triangulos` contava o estado de
antes da limpeza das peças falsas); foi recontado e hoje bate em 168 de 168.
Para refazer: `python ferramentas/refazer_indice.py <raiz> --aplicar`.

---

## Para abrir na interface 3D

Existe um programa que lê este acervo, monta o carro com as peças e as rodas na
medida certa e deixa pintar: **[nfs-heat-garagem](https://github.com/plmarcos/nfs-heat-garagem)**.

Ele aceita **qualquer pasta** como raiz, desde que ela tenha estes seis itens:

```
_indice.csv  _mods_indice.csv  _mods_mapa.csv
_rodas_eixos.csv  _ficha_tecnica.csv  _pneu/
```

Sem `_ficha_tecnica.csv` ele não sobe.

---

## Outros números úteis

- **Vértice órfão**: 17,5% dos vértices das carrocerias não são usados por
  nenhuma face (mediana de 16,9% por arquivo, máximo 52,7%, 9 carros com zero).
  Importadores descartam sozinhos — menos no `_lowpoly.obj`, que tem 52,2% de
  vértice solto e o Blender **mantém**.
- **UV**: o índice de UV é literalmente igual ao índice de vértice em 100% dos
  arquivos. Fora de [0,1] é comum e esperado (mediana de 33,3% na carroceria,
  16,0% nos mods); o extremo do acervo está nos mods, com V de −586,5 a +588,0.
- **Triângulos degenerados**: da ordem de 0,01%.
- **Formato de face**: `f v/vt`, 100% triângulos, em todos os 18.088 extraídos.
  O `_lowpoly.obj` é a exceção em tudo — tem `vn`, usa `f v/vt/vn`, tem `o` mas
  não tem `g`.
- **`g` é igual a `usemtl`** nas 168 carrocerias; cada arquivo de mod tem
  exatamente 1 objeto `o`.
- **Duplicação**: 36 conjuntos de textura servem mais de um carro (91 carros no
  total), 481 MiB em cópias — 4,7% do acervo. E 12 pastas de carro são
  redundantes, 400,75 MiB.
- **O `.mtl` da carroceria declara material que o OBJ não usa**: 3.999 blocos
  `newmtl` contra 3.652 `usemtl`, sobrando 347 em 159 dos 168 carros. São
  justamente os que trazem `Ns`/`Pr`/`Pm`. O Blender descarta os não usados;
  quem escrever leitor próprio vai criar slot a mais.

---

## O que não foi medido

Honestidade sobre o limite deste documento:

- **orientação do canal verde do normal** (OpenGL × DirectX) — em aberto;
- **o que o motor faz com o canal B da máscara `_m`**;
- **vértice órfão e solda em `mods/`** — o teste de "não solde" foi feito em
  carroceria, capô e aro, não nas peças de customização;
- **a causa da altura ler baixo** — o efeito está medido em quatro carros; a
  hipótese de "o modelo inclui geometria abaixo do pneu" foi **descartada** (no
  `_com_rodas.obj` o pneu assenta em Y ≈ 0 e a carroceria desce de 4,7 a 8,3 cm
  abaixo disso, então Y = 0 é o asfalto mesmo). Sobra a postura rebaixada ou
  proporção simplificada do modelo de jogo, e isso não medi.
