"""Refaz o `_indice.csv` a partir dos arquivos em disco.

POR QUE ISTO EXISTE
-------------------
O `_indice.csv` e' escrito durante a extracao, e a extracao nao e' o fim da
linha: depois dela roda o `limpar_pecas.py`, que tira da carroceria o que nao e'
peca -- copia do carro inteiro, farol animado, aero ativo. O indice nao era
reescrito, entao a coluna `triangulos` ficava com a contagem de **antes** da
limpeza.

Medido em 21/09/2026: a coluna batia com o disco em 64 dos 168 carros, e sempre
para mais. O pior caso e' o Ferrari FXX-K Evo, com 147.409 no indice contra
65.148 em disco -- 82.261 triangulos de diferenca, mais que o dobro. Quem ler o
indice para dimensionar um orcamento de poligonos leva um susto e erra por 2x.

As outras colunas estavam certas e sao recalculadas do mesmo jeito, por
coerencia: `pecas` e' o numero de objetos `o ` da carroceria e
`triangulos_lowpoly` batia em 168 de 168.

    python refazer_indice.py [pasta_do_acervo] [--aplicar]

Sem `--aplicar` ele so' mostra o que mudaria. O arquivo antigo vira `.bak`.
"""
from __future__ import annotations

import csv
import os
import shutil
import sys
from pathlib import Path

NOME = "_indice.csv"
COLS = ["carro", "pecas", "triangulos", "triangulos_lowpoly"]


def contar(caminho: Path) -> tuple[int, int]:
    """(triangulos, objetos). Face de N vertices vale N-2 triangulos.

    Le' em binario e compara os primeiros bytes: e' cerca de 3x mais rapido que
    decodificar cada linha, e num acervo de 7 GB de OBJ isso e' a diferenca
    entre 40 segundos e dois minutos.
    """
    tris = objs = 0
    try:
        with open(caminho, "rb") as fh:
            for linha in fh:
                if linha.startswith(b"f "):
                    n = len(linha.split()) - 1
                    if n >= 3:
                        tris += n - 2
                elif linha.startswith(b"o "):
                    objs += 1
    except OSError:
        return 0, 0
    return tris, objs


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    aplicar = "--aplicar" in args
    args = [a for a in args if a != "--aplicar"]
    raiz = Path(args[0] if args else os.environ.get("NFSHEAT_ACERVO", "F:/CarsNfSHeat"))

    caminho = raiz / NOME
    if not caminho.is_file():
        print("nao achei %s" % caminho, file=sys.stderr)
        return 2

    with open(caminho, encoding="utf-8-sig", newline="") as fh:
        linhas = list(csv.DictReader(fh))

    mudancas, sem_corpo, novas = [], [], []
    for r in linhas:
        carro = r["carro"]
        corpo = raiz / carro / (carro + ".obj")
        low = raiz / carro / (carro + "_lowpoly.obj")
        if not corpo.is_file():
            # Nao inventa numero para o que nao esta' em disco: mantem a linha
            # como estava e avisa. Apagar seria pior -- o carro pode estar so'
            # fora desta copia do acervo.
            sem_corpo.append(carro)
            novas.append(r)
            continue

        tris, objs = contar(corpo)
        low_tris = contar(low)[0] if low.is_file() else int(r["triangulos_lowpoly"])
        nova = {"carro": carro, "pecas": objs, "triangulos": tris,
                "triangulos_lowpoly": low_tris}
        for c in COLS[1:]:
            if str(r.get(c)) != str(nova[c]):
                mudancas.append((carro, c, r.get(c), nova[c]))
        novas.append(nova)

    print("carros no indice: %d" % len(linhas))
    print("sem carroceria em disco: %s" % (len(sem_corpo) or "nenhum"))
    print("celulas a corrigir: %d" % len(mudancas))
    por_coluna: dict[str, int] = {}
    for _, c, _, _ in mudancas:
        por_coluna[c] = por_coluna.get(c, 0) + 1
    for c, n in sorted(por_coluna.items()):
        print("   %-20s %d linha(s)" % (c, n))

    piores = sorted((m for m in mudancas if m[1] == "triangulos"),
                    key=lambda m: -abs(int(m[3]) - int(m[2])))
    for carro, _, velho, novo in piores[:8]:
        print("   %-46s %8s -> %8d  (%+d)" % (carro, velho, novo, int(novo) - int(velho)))

    if not aplicar:
        print("\n(simulacao -- rode com --aplicar para gravar)")
        return 0
    if not mudancas:
        print("\nnada a fazer")
        return 0

    shutil.copy2(caminho, caminho.with_suffix(".csv.bak"))
    with open(caminho, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(novas)
    print("\ngravado: %s  (antigo em %s)" % (caminho, caminho.name + ".bak"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
