# NFS Heat Car Tools

Ferramentas para **extrair, montar e visualizar os veículos do Need for Speed Heat** (PC).
Tiram as carrocerias, as texturas e as liveries de fábrica dos arquivos do jogo, montam o
carro com rodas e pneus na medida certa, e preparam o modelo para abrir no Blender, no
3ds Max ou no ZModeler.

> **English:** Tools to extract Need for Speed Heat car meshes, textures and factory liveries,
> assemble them with correctly sized wheels, and prepare them for Blender / 3ds Max.
> **Code only — no game data is included.** Bring your own legally obtained copy of the game.

> **Trabalho pausado.** O desenvolvimento deste projeto está parado. O que está
> aqui funciona e continua aberto: **quem quiser modificar, pode** — não é preciso
> pedir permissão. O código é MIT.

Depois de extrair, o acervo abre numa interface 3D em
[nfs-heat-garagem](https://github.com/plmarcos/nfs-heat-garagem): escolher o carro,
trocar peça por peça entre as variantes, montar as rodas na medida e pintar.

---

## Este repositório não traz arquivo de jogo

Aqui só tem **código**. Nenhum modelo, textura ou livery do Need for Speed Heat acompanha o
repositório. Esse material é da **Electronic Arts**. Para usar as ferramentas você precisa da
sua própria cópia legal do jogo.

Também **não** acompanha nada do Frosty Tool Suite, nem a chave de descriptografia do jogo: o
`Export.cs` lê o `NFSHEAT.key` da sua instalação do Frosty, em tempo de execução. Não commite
`.key` nem DLL aqui.

Este projeto não tem vínculo com a Electronic Arts, a Criterion Games nem com o Frosty Tool Suite.

## O que você precisa

- **Need for Speed Heat** instalado (a sua cópia)
- **Frosty Tool Suite 1.0.7** — as ferramentas carregam as DLLs dele em tempo de execução
- **Windows PowerShell 5.1** para a parte de extração (as DLLs são .NET Framework 4.8)
- **Python 3.11+** com `Pillow` e `numpy` para a parte de montagem e imagem
- **Blender 4.5** para os scripts de render e de aplicação de livery

## As ferramentas

### Extração (PowerShell + C#)

| Script | O que faz |
|---|---|
| `Export.cs` | O extrator em si: inicializa o Frosty, lê o `MeshSet` e grava OBJ + texturas |
| `extrair.ps1` | Extrai as carrocerias em lote, com a peça de fábrica de cada slot |
| `listar_mods.ps1` | Levanta todas as peças de customização do jogo, num CSV, sem extrair nada |
| `extrair_mods.ps1` | Extrai as **peças de modificação** (as variantes que o `extrair.ps1` descarta) |
| `extrair_extras.ps1` | Extrai as peças soltas dos derelicts, o chop shop e os VFX |
| `texturas.ps1` | Extrai as texturas dos veículos |
| `swatches.ps1` | Extrai as amostras de pintura |

### Montagem do modelo (Python)

| Script | O que faz |
|---|---|
| `fitwheels.py` | Calcula entre-eixos e bitola a partir da carroceria, com constantes calibradas |
| `montar_rodas.py` | Monta aro e pneu nas quatro posições, com escala única compartilhada |
| `limpar_pecas.py` | Tira do modelo o que não é peça: cópias do carro inteiro, faróis animados, aero ativo |
| `corrigir_materiais_rodas.py` | Define pneu e aro no MTL (sem isso a roda abre branca) |
| `ligar_texturas.py` | Liga as texturas extraídas aos materiais do MTL |
| `converter.py` | Converte entre formatos |
| `analisar_duplicados.py` | Acha veículo duplicado comparando geometria, material e textura |
| `nuvem_de_pontos.py` | Segunda passada: pega o mesmo modelo exportado em outra ordem |

### Liveries e imagem

| Script | O que faz |
|---|---|
| `gerar_vinil.py` | Gera liveries novas rasterizando a UV de pintura do carro |
| `aplicar_vinil.py` / `aplicar_vinil_lote.py` | Aplica uma livery na lataria e renderiza |
| `manifest_vinis.py` | Casa cada livery de fábrica com o carro dela |
| `catalogo.py` / `catalogo_liveries.py` | Monta folhas de contato do acervo |
| `preview.py` / `preview_texturizado.py` | Renders de prévia |

## Três coisas que custaram caro para descobrir

Estão documentadas nos próprios scripts, mas valem o aviso:

1. **A malha da roda no Heat é só o aro, não o pneu.** Escalar o aro para o diâmetro do pneu
   infla a roda em cerca de 33%. O pneu é uma malha compartilhada à parte, e os dois precisam
   usar a **mesma** escala.
2. **A lataria do Heat não tem textura.** A pintura é procedural; não adianta procurar um
   arquivo de cor da carroceria. As liveries são receitas de camadas, compostas em tempo de
   execução.
3. **A peça de customização mora fora da carroceria.** Cada slot (`bumperf`, `hood`,
   `spoiler`…) tem a variante de fábrica e as do menu, com sufixo `_setb`, `_altc` e afins.
   O `extrair.ps1` fica só com a de fábrica de propósito, para montar o carro padrão; as
   outras 13.813 saem com o `extrair_mods.ps1`. Sem elas, dois carros que no jogo têm
   carroceria diferente — o Huracán LP610 Spyder e o Performante Spyder, por exemplo —
   saem com geometria idêntica.

## Caminhos: o que configurar antes de rodar

Três caminhos mudam de máquina para máquina. Nenhum deles precisa ser editado dentro do
script:

| O que | Como apontar | Padrão se você não apontar |
|---|---|---|
| Frosty Tool Suite | variável `FROSTY_EDITOR` | a pasta da máquina do autor |
| Pasta do jogo | variável `NFSHEAT_JOGO` | idem |
| Pasta de saída | parâmetro `-OutRoot` / primeiro argumento / `--raiz` | `F:\CarsNfSHeat` |

```powershell
setx FROSTY_EDITOR "D:\FrostyToolSuite\FrostyEditor"
setx NFSHEAT_JOGO  "D:\Steam\steamapps\common\Need for Speed Heat"
```

Se o Frosty ou o jogo não estiverem onde o script procura, ele **falha na primeira linha
com o caminho na mensagem** — em vez de morrer lá dentro com um "não foi possível carregar o
assembly", que não diz nada a ninguém.

O `Export.cs` é procurado **ao lado do próprio script**, então mantenha a pasta
`ferramentas/` junta. Antes ele era procurado num caminho absoluto, e quem clonasse o
repositório não achava o arquivo.

As variáveis valem para os dois projetos: `NFSHEAT_ACERVO` aponta a pasta do acervo tanto
aqui quanto na [garagem](https://github.com/plmarcos/nfs-heat-garagem).

## Licença

Código: **MIT** (veja `LICENSE`). A licença cobre apenas o código deste repositório — nada do
material do jogo, que continua sendo da Electronic Arts.
