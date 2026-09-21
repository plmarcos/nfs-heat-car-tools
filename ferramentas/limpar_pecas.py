"""
Tira do <carro>.obj peças que nao deviam estar ali.

Tres casos encontrados:
  1. Copia do carro inteiro entrando como peca — objetos 'static' e 'carstatic_*'
     (a LaFerrari trazia um 'carstatic' de 162 mil vertices por cima do carro real).
  2. Pecas animadas desenhadas no pivo — 'animated*' (farol escamoteavel do F40,
     Testarossa e NSX ficam 27 cm abaixo do chao).
  3. Aero ativo desenhado na posicao de acionamento — spoiler da LaFerrari a -49 cm.

Regra: fora objetos com nome de copia/animacao, e fora qualquer peca que nao seja a
base e desca mais de 15 cm abaixo do chao do carro.

Uso:  python limpar_pecas.py <raiz>
"""
import os, sys, glob, re

BAD_NAME = re.compile(r"^(static|carstatic|animated)", re.I)
BELOW = -0.15


def clean(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().split("\n")

    # 1a passada: limites e contagem de cada objeto (indices de vertice sao globais)
    objs, order, cur = {}, [], None
    vi = 0
    for ln in lines:
        if ln.startswith("o "):
            cur = ln.split()[1].strip()
            if cur not in objs:
                objs[cur] = {"ymin": 1e9, "ymax": -1e9, "n": 0}
                order.append(cur)
        elif ln.startswith("v "):
            vi += 1
            if cur:
                y = float(ln.split()[2])
                o = objs[cur]
                o["ymin"] = min(o["ymin"], y)
                o["ymax"] = max(o["ymax"], y)
                o["n"] += 1

    if not objs:
        return None

    # O chao e o da carroceria base. Usar o minimo global nao serve: a propria peca
    # solta costuma ser o ponto mais baixo, e aí ela vira a referencia e se salva.
    ground = objs["base"]["ymin"] if "base" in objs else min(o["ymin"] for o in objs.values())
    drop = set()
    for k, o in objs.items():
        if k == "base":
            continue
        if BAD_NAME.match(k):
            drop.add(k)
        elif o["ymin"] - ground < BELOW:
            drop.add(k)
    if not drop:
        return None

    # 2a passada: reescreve sem os objetos descartados, renumerando v/vt
    out = []
    vmap, tmap = {}, {}
    nv = nt = 0
    keep = True
    cur = None
    src_v = src_t = 0
    for ln in lines:
        if ln.startswith("o "):
            cur = ln.split()[1].strip()
            keep = cur not in drop
            if keep:
                out.append(ln)
        elif ln.startswith("v "):
            src_v += 1
            if keep:
                nv += 1
                vmap[src_v] = nv
                out.append(ln)
        elif ln.startswith("vt "):
            src_t += 1
            if keep:
                nt += 1
                tmap[src_t] = nt
                out.append(ln)
        elif ln.startswith("f "):
            if not keep:
                continue
            toks = []
            ok = True
            for tok in ln.split()[1:]:
                p = tok.split("/")
                a = vmap.get(int(p[0]))
                if a is None:
                    ok = False; break
                if len(p) > 1 and p[1]:
                    b = tmap.get(int(p[1]))
                    toks.append("%d/%d" % (a, b) if b else str(a))
                else:
                    toks.append(str(a))
            if ok and len(toks) >= 3:
                out.append("f " + " ".join(toks))
        elif ln.startswith("usemtl ") or ln.startswith("g "):
            if keep:
                out.append(ln)
        else:
            out.append(ln)

    open(path, "w", encoding="utf-8").write("\n".join(out))
    return sorted(drop)


root = sys.argv[1] if len(sys.argv) > 1 else r"F:/CarsNfSHeat"
n = 0
for d in sorted(glob.glob(os.path.join(root, "*"))):
    if not os.path.isdir(d) or os.path.basename(d).startswith("_"):
        continue
    name = os.path.basename(d)
    p = os.path.join(d, name + ".obj")
    if not os.path.exists(p):
        continue
    dropped = clean(p)
    if dropped:
        n += 1
        print("%-48s removeu: %s" % (name, ", ".join(dropped)))
print("\ncarros limpos: %d" % n)
