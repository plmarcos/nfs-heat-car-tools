"""
Liga as texturas exportadas aos materiais nos arquivos .mtl.

Conservador de proposito: so escreve map_Kd / map_Bump / map_Ke quando existe um
arquivo de textura que corresponde exatamente ao nome do material. Material sem
textura correspondente fica cinza (no Heat a pintura da lataria e procedural,
entao nao existe textura de carroceria pra ligar).

Uso:  python link_mtl.py <pasta_raiz>
"""
import os, sys, glob, re

root = sys.argv[1] if len(sys.argv) > 1 else r"F:\CarsNfSHeat"

# material token -> tokens de textura que valem a pena tentar
ALIAS = {
    "light": ["light_seta", "light"],
    "lightbucket": ["lbucket_seta", "lightbucket", "lbucket"],
    "lightglass_clear": ["lightglass_seta", "lightglass"],
    "lightglass_red": ["lightglass_seta", "lightglass"],
    "lightglassnormal_orange": ["lightglass_seta", "lightglass"],
    "lightglassnormal_red": ["lightglass_seta", "lightglass"],
    "carpaintnormal": [],   # pintura e procedural, nao tem textura
    "carpaint": [],
}

SUF_D = ["_d", "_da"]
SUF_N = ["_n", "_no", "_nd", "_na"]
SUF_E = ["_e", "_ea"]


def mat_token(name):
    """M_Interior_Max -> interior ; M_LightGlass_Clear_Max -> lightglass_clear"""
    m = re.match(r"^M_(.+?)_Max$", name)
    if not m:
        return None
    return m.group(1).lower()


def find_tex(texfiles, token, suffixes):
    for s in suffixes:
        tail = "_" + token + s + ".png"
        for f in texfiles:
            if f.lower().endswith(tail):
                return f
    return None


def process_mtl(path, texdir, relprefix):
    if not os.path.isdir(texdir):
        return (0, 0)
    texfiles = [os.path.basename(p) for p in glob.glob(os.path.join(texdir, "*.png"))]
    if not texfiles:
        return (0, 0)

    out, linked, total = [], 0, 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    # ja ligado -> nao mexer (senao roda duas vezes e duplica as linhas map_*)
    if any(k in content for k in ("map_Kd", "map_Bump", "map_Ke", "map_Ks")):
        return (0, 0)
    lines = content.split("\n")

    for line in lines:
        out.append(line)
        if not line.startswith("newmtl "):
            continue
        total += 1
        name = line.split(None, 1)[1].strip()
        tok = mat_token(name)
        if tok is None:
            continue
        cands = ALIAS.get(tok, [tok])
        d = n = e = None
        for c in cands:
            d = d or find_tex(texfiles, c, SUF_D)
            n = n or find_tex(texfiles, c, SUF_N)
            e = e or find_tex(texfiles, c, SUF_E)
        if d:
            out.append("map_Kd " + relprefix + d)
        if n:
            out.append("map_Bump " + relprefix + n)
            out.append("bump " + relprefix + n)
        if e:
            out.append("map_Ke " + relprefix + e)
        if d or n or e:
            linked += 1
    if linked:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out))
    return (linked, total)


cars = sorted(d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d)
              and not os.path.basename(d).startswith("_"))
tot_l = tot_m = tot_files = 0
for cdir in cars:
    texdir = os.path.join(cdir, "textures")
    for mtl in glob.glob(os.path.join(cdir, "*.mtl")):
        l, m = process_mtl(mtl, texdir, "textures/")
        tot_l += l; tot_m += m; tot_files += 1
    for mtl in glob.glob(os.path.join(cdir, "parts", "*.mtl")):
        l, m = process_mtl(mtl, texdir, "../textures/")
        tot_l += l; tot_m += m; tot_files += 1

print("mtl files processed: %d" % tot_files)
print("materials: %d   with texture linked: %d  (%.0f%%)" %
      (tot_m, tot_l, 100.0 * tot_l / tot_m if tot_m else 0))
