"""Corrige as rodas que abriam brancas.

  python corrigir_materiais_rodas.py [--aplicar] [--raiz F:/CarsNfSHeat]

Dois defeitos, somados:

1. `<carro>_com_rodas.obj` usa `M_Tire_Max` e `M_Rim_Main_Max`, mas o MTL do carro
   nao define nenhum dos dois. Sem definicao, o visualizador cai no cinza claro
   padrao, e o pneu aparece branco. Isso atinge 159 dos 166 carros.
2. Onde a definicao existe (`<carro>_wheel.mtl`, `_pneu/shared_tire_*.mtl`), ela
   veio com `Kd 0.800 0.800 0.800`, que tambem e' branco.

A correcao escreve valores de borracha e metal, e liga o mapa de normal do aro do
proprio carro quando ele existe. Nao toca em material de lataria: so' mexe em nome
de pneu, aro e emblema de aro. Roda de novo sem estragar nada (idempotente).
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

BRANCO = re.compile(r"^Kd\s+0\.8(00)?\s+0\.8(00)?\s+0\.8(00)?\s*$", re.I)

# Kd/Ks/Ns servem para qualquer visualizador; Pr/Pm o Blender 4 le como
# rugosidade e metalicidade, que e' o que da' borracha fosca e aro metalico.
# As chaves casam RESPEITANDO MAIUSCULAS de proposito: em minusculas, "trim"
# (material de lataria) contem "rim" e seria repintado como aro por engano.
RECEITAS = (
    ("Tire", dict(Kd="0.050 0.050 0.052", Ks="0.030 0.030 0.030", Ns="12", Pr="0.85", Pm="0.0")),
    ("RimBadge", dict(Kd="0.700 0.700 0.720", Ks="0.400 0.400 0.400", Ns="120", Pr="0.35", Pm="0.8")),
    ("Rim", dict(Kd="0.620 0.630 0.660", Ks="0.850 0.850 0.850", Ns="260", Pr="0.25", Pm="1.0")),
    ("PlasticRoughBlack", dict(Kd="0.040 0.040 0.045", Ks="0.050 0.050 0.050", Ns="20", Pr="0.70", Pm="0.0")),
    ("Brake", dict(Kd="0.180 0.180 0.190", Ks="0.300 0.300 0.300", Ns="90", Pr="0.45", Pm="0.6")),
    ("Caliper", dict(Kd="0.350 0.060 0.060", Ks="0.300 0.300 0.300", Ns="120", Pr="0.35", Pm="0.2")),
)
DE_RODA = ("Tire", "Rim", "Brake", "Caliper")


def receita(nome: str) -> dict | None:
    for chave, valores in RECEITAS:
        if chave in nome:
            return valores
    return None


def e_de_roda(nome: str) -> bool:
    return any(chave in nome for chave in DE_RODA)


def mapas_do_aro(pasta: Path, nome_material: str) -> list[str]:
    """Mapa de normal do aro do proprio carro, quando existe.

    So' vale para aro e emblema de aro. Pneu NAO leva mapa: o Heat nao tem
    textura de pneu por carro, e pendurar o normal do aro nele desenha o
    desenho das raias na borracha.
    """
    texturas = pasta / "textures"
    if not texturas.is_dir() or "Rim" not in nome_material:
        return []
    alvo = "rimbadge" if "RimBadge" in nome_material else "rim"
    linhas = []
    if alvo == "rimbadge":
        for arquivo in sorted(texturas.glob("*rimbadge_d.png")):
            linhas.append(f"map_Kd textures/{arquivo.name}")
            break
    for sufixo in (f"*{alvo}_n.png",):
        for arquivo in sorted(texturas.glob(sufixo)):
            if alvo == "rim" and "rimbadge" in arquivo.name.lower():
                continue
            linhas.append(f"map_Bump textures/{arquivo.name}")
            linhas.append(f"bump textures/{arquivo.name}")
            break
    return linhas


def bloco(nome: str, valores: dict, mapas: list[str]) -> str:
    linhas = [f"newmtl {nome}"]
    linhas += mapas
    linhas.append(f"Kd {valores['Kd']}")
    linhas.append(f"Ks {valores['Ks']}")
    linhas.append(f"Ns {valores['Ns']}")
    linhas.append(f"Pr {valores['Pr']}")
    linhas.append(f"Pm {valores['Pm']}")
    linhas.append("illum 2")
    linhas.append("d 1.0")
    return "\n".join(linhas) + "\n\n"


def definidos_em(mtl: Path) -> set[str]:
    if not mtl.is_file():
        return set()
    return {
        linha.split(None, 1)[1].strip()
        for linha in mtl.read_text(encoding="utf-8", errors="replace").splitlines()
        if linha.startswith("newmtl ")
    }


def repintar(mtl: Path, pasta: Path, aplicar: bool) -> list[str]:
    """Troca o branco 0.8 por borracha/metal nas definicoes que ja existem."""
    if not mtl.is_file():
        return []
    texto = mtl.read_text(encoding="utf-8", errors="replace")
    partes = texto.split("newmtl ")
    mudados = []
    saida = [partes[0]]
    for parte in partes[1:]:
        nome = parte.splitlines()[0].strip()
        valores = receita(nome) if e_de_roda(nome) else None
        if valores is None or not any(BRANCO.match(l.strip()) for l in parte.splitlines()):
            saida.append("newmtl " + parte)
            continue
        linhas = []
        tem_mapa = any(l.startswith(("map_", "bump")) for l in parte.splitlines())
        for linha in parte.splitlines():
            despido = linha.strip()
            if BRANCO.match(despido):
                linhas.append(f"Kd {valores['Kd']}")
                linhas.append(f"Ks {valores['Ks']}")
                linhas.append(f"Ns {valores['Ns']}")
                linhas.append(f"Pr {valores['Pr']}")
                linhas.append(f"Pm {valores['Pm']}")
            elif despido.startswith(("Ks ", "Ns ", "Pr ", "Pm ")):
                continue
            else:
                linhas.append(linha)
        if not tem_mapa:
            extras = mapas_do_aro(pasta, nome)
            if extras:
                linhas = [linhas[0]] + extras + linhas[1:]
        saida.append("newmtl " + "\n".join(linhas) + "\n")
        mudados.append(nome)
    if mudados and aplicar:
        if not mtl.with_suffix(mtl.suffix + ".bak").exists():
            shutil.copy2(mtl, mtl.with_suffix(mtl.suffix + ".bak"))
        mtl.write_text("".join(saida), encoding="utf-8", newline="\n")
    return mudados


def completar(obj: Path, aplicar: bool) -> tuple[list[str], Path | None]:
    """Acrescenta ao MTL do carro os materiais de roda que faltam."""
    pasta = obj.parent
    mtllib = None
    usados: set[str] = set()
    for linha in obj.read_text(encoding="utf-8", errors="replace").splitlines():
        if linha.startswith("mtllib "):
            mtllib = linha.split(None, 1)[1].strip()
        elif linha.startswith("usemtl "):
            usados.add(linha.split(None, 1)[1].strip())
    if not mtllib:
        return [], None
    mtl = pasta / mtllib
    faltando = sorted(usados - definidos_em(mtl))
    novos = []
    adicoes = ""
    for nome in faltando:
        valores = receita(nome)
        if valores is None:
            valores = dict(Kd="0.350 0.350 0.360", Ks="0.200 0.200 0.200",
                           Ns="60", Pr="0.55", Pm="0.0")
        adicoes += bloco(nome, valores, mapas_do_aro(pasta, nome) if e_de_roda(nome) else [])
        novos.append(nome)
    if novos and aplicar:
        if not mtl.with_suffix(mtl.suffix + ".bak").exists():
            shutil.copy2(mtl, mtl.with_suffix(mtl.suffix + ".bak"))
        with mtl.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n# materiais de roda acrescentados por corrigir_materiais_rodas.py\n")
            fh.write(adicoes)
    return novos, mtl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz", type=Path, default=Path("F:/CarsNfSHeat"))
    parser.add_argument("--aplicar", action="store_true", help="sem isso, so' mostra o que faria")
    args = parser.parse_args()

    acrescentados = 0
    repintados = 0
    carros = 0
    for obj in sorted(args.raiz.glob("*/*_com_rodas.obj")):
        carros += 1
        novos, mtl = completar(obj, args.aplicar)
        trocados = repintar(obj.parent / f"{obj.parent.name}_wheel.mtl", obj.parent, args.aplicar)
        # alguns carros ja definiam o aro no MTL principal, tambem em branco
        if mtl is not None:
            trocados += repintar(mtl, obj.parent, args.aplicar)
        if novos:
            acrescentados += 1
        if trocados:
            repintados += 1
        if (novos or trocados) and carros <= 5:
            print("  %-42s + %s   repintado: %s" % (obj.parent.name, ",".join(novos) or "-",
                                                    ",".join(trocados) or "-"))
    for mtl in sorted((args.raiz / "_pneu").glob("*.mtl")):
        trocados = repintar(mtl, mtl.parent, args.aplicar)
        if trocados:
            print("  %-42s repintado: %s" % (mtl.name, ",".join(trocados)))

    print("\ncarros varridos: %d" % carros)
    print("com material de roda acrescentado: %d" % acrescentados)
    print("com definicao branca repintada:    %d" % repintados)
    print("modo: %s" % ("APLICADO" if args.aplicar else "simulacao (use --aplicar)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
