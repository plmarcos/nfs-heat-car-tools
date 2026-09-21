"""Procura veiculos duplicados no acervo, comparando geometria de verdade.

Nao confia em nome nem em contagem de triangulo: gera hash de tres coisas
separadas, porque duplicata de geometria com textura diferente NAO e' duplicata.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

RAIZ = Path(os.environ.get("NFSHEAT_ACERVO", "F:/CarsNfSHeat"))
SAIDA = Path(__file__).with_name("duplicados.json")


def hash_geometria(obj: Path) -> tuple[str, int, int]:
    """Hash so' de v/vn/vt/f. Ignora comentario, mtllib, nome de objeto."""
    h = hashlib.sha256()
    verts = faces = 0
    with obj.open("rb") as fh:
        for linha in fh:
            if linha[:2] in (b"v ", b"f ") or linha[:3] in (b"vn ", b"vt "):
                h.update(linha.strip())
                h.update(b"\n")
                if linha[:2] == b"v ":
                    verts += 1
                elif linha[:2] == b"f ":
                    faces += 1
    return h.hexdigest(), verts, faces


def hash_materiais(obj: Path) -> str:
    """Hash dos nomes de grupo e usemtl: distingue variante com material trocado."""
    h = hashlib.sha256()
    with obj.open("rb") as fh:
        for linha in fh:
            if linha[:2] == b"g " or linha[:7] == b"usemtl ":
                h.update(linha.strip())
                h.update(b"\n")
    return h.hexdigest()


def hash_texturas(pasta: Path) -> tuple[str, int, int]:
    if not pasta.is_dir():
        return "", 0, 0
    arquivos = sorted(p for p in pasta.rglob("*") if p.is_file())
    h = hashlib.sha256()
    total = 0
    for p in arquivos:
        h.update(p.name.encode("utf-8", "replace"))
        hf = hashlib.sha256()
        with p.open("rb") as fh:
            for pedaco in iter(lambda: fh.read(1 << 20), b""):
                hf.update(pedaco)
        h.update(hf.digest())
        total += p.stat().st_size
    return h.hexdigest(), len(arquivos), total


def tamanho(pasta: Path) -> int:
    return sum(p.stat().st_size for p in pasta.rglob("*") if p.is_file())


def main() -> int:
    pastas = [p for p in sorted(RAIZ.iterdir())
              if p.is_dir() and not p.name.startswith("_")]
    print("veiculos a analisar: %d" % len(pastas), flush=True)

    fichas = []
    for n, pasta in enumerate(pastas, start=1):
        obj = pasta / (pasta.name + ".obj")
        if not obj.is_file():
            candidatos = [p for p in pasta.glob("*.obj")
                          if "_lowpoly" not in p.name and "_wheel" not in p.name
                          and "_com_rodas" not in p.name]
            obj = candidatos[0] if candidatos else None
        if obj is None:
            print("  SEM OBJ: %s" % pasta.name, flush=True)
            continue
        g, verts, faces = hash_geometria(obj)
        m = hash_materiais(obj)
        t, n_tex, bytes_tex = hash_texturas(pasta / "textures")
        pecas = len(list((pasta / "parts").glob("*.obj"))) if (pasta / "parts").is_dir() else 0
        fichas.append({
            "carro": pasta.name,
            "geometria": g,
            "materiais": m,
            "texturas": t,
            "vertices": verts,
            "faces": faces,
            "n_texturas": n_tex,
            "bytes_texturas": bytes_tex,
            "pecas": pecas,
            "bytes_total": tamanho(pasta),
        })
        if n % 20 == 0 or n == len(pastas):
            print("  %3d/%d" % (n, len(pastas)), flush=True)

    SAIDA.write_text(json.dumps(fichas, indent=1), encoding="utf-8")

    # agrupa por geometria
    grupos: dict[str, list[dict]] = {}
    for f in fichas:
        grupos.setdefault(f["geometria"], []).append(f)

    iguais = {k: v for k, v in grupos.items() if len(v) > 1}
    print("\n=== GEOMETRIA IDENTICA: %d grupos ===" % len(iguais))
    desperdicio = 0
    for k, v in sorted(iguais.items(), key=lambda kv: -len(kv[1])):
        mesma_tex = len({f["texturas"] for f in v}) == 1
        mesmo_mat = len({f["materiais"] for f in v}) == 1
        rotulo = ("IDENTICO" if (mesma_tex and mesmo_mat) else
                  "geometria igual, textura/material diferente")
        print("\n[%s]  %d vertices, %d faces  -> %s" % (rotulo, v[0]["vertices"], v[0]["faces"], ""))
        for f in sorted(v, key=lambda f: f["carro"]):
            print("    %-55s  %6.1f MB  tex=%s..  mat=%s.." % (
                f["carro"], f["bytes_total"] / 1024**2,
                f["texturas"][:6], f["materiais"][:6]))
        if mesma_tex and mesmo_mat:
            desperdicio += sum(f["bytes_total"] for f in sorted(v, key=lambda f: f["carro"])[1:])
    print("\nespaco em copia 100%% identica: %.2f GB" % (desperdicio / 1024**3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
