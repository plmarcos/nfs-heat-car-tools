"""Compara os carros pela nuvem de pontos ordenada, nao pela ordem do arquivo.

O teste anterior deu 42% de vertices "diferentes" com desvio de 4,5 m: isso e'
reordenacao de peca, nao carro diferente. Ordenar antes de comparar resolve.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
import os
from pathlib import Path

RAIZ = Path(os.environ.get("NFSHEAT_ACERVO", "F:/CarsNfSHeat"))
SAIDA = Path(__file__).with_name("nuvens.json")


def nuvem(nome: str) -> str:
    obj = RAIZ / nome / (nome + ".obj")
    pontos = []
    with obj.open("r", encoding="utf-8", errors="replace") as fh:
        for linha in fh:
            if linha.startswith("v "):
                x, y, z = (float(t) for t in linha.split()[1:4])
                pontos.append((round(x, 4), round(y, 4), round(z, 4)))
    pontos.sort()
    h = hashlib.sha256()
    for p in pontos:
        h.update(("%.4f,%.4f,%.4f;" % p).encode("ascii"))
    return h.hexdigest()


def main() -> int:
    fichas = json.loads(Path(__file__).with_name("duplicados.json").read_text(encoding="utf-8"))
    por_faces = defaultdict(list)
    for f in fichas:
        por_faces[f["faces"]].append(f["carro"])
    alvos = sorted({c for v in por_faces.values() if len(v) > 1 for c in v})
    print("carros a comparar por nuvem: %d" % len(alvos), flush=True)

    nuvens = {}
    for n, c in enumerate(alvos, start=1):
        nuvens[c] = nuvem(c)
        print("  %2d/%d %s" % (n, len(alvos), c), flush=True)
    SAIDA.write_text(json.dumps(nuvens, indent=1), encoding="utf-8")

    grupos = defaultdict(list)
    for c, h in nuvens.items():
        grupos[h].append(c)
    print("\n=== MESMA NUVEM DE PONTOS (mesmo modelo, ordem diferente) ===")
    for h, v in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
        if len(v) > 1:
            print("  " + "\n  ".join(sorted(v)))
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
