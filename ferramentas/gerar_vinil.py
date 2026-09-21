"""
Gerador de vinis para os carros extraidos do NFS Heat.

Monta uma textura de lataria 2048x2048 compondo decalques da biblioteca do proprio
jogo (`_swatches\\`) sobre o UV da carroceria — a mesma materia-prima que o editor do
jogo oferece. A saida sai no formato dos vinis de fabrica (`_d`), entao entra direto
no aplicar_vinil.py.

  python gerar_vinil.py <carro> [opcoes]

    --estilo   racing | listras | tribal | camuflagem | bandeira   (padrao: racing)
    --cores    lista hex separada por virgula, ex: "e01b24,ffffff,111111"
    --seed     numero; a mesma seed com as mesmas opcoes da o mesmo vinil
    --saida    caminho do png (padrao: <carro>/<carro>_vinil.png)
    --raiz     pasta base (padrao: F:\\CarsNfSHeat)

Como os decalques funcionam (descoberto nos arquivos do jogo):
  _m    canal G guarda a FORMA do decalque (R=0, B=255 sempre)
  _t_d  branco puro: decalque "tintable", a cor vem de fora
  _d    arte colorida de verdade (bandeiras, logos)
"""
import os, sys, glob, random, argparse, math
from PIL import Image, ImageDraw

PAINT_MATS = ("carpaint",)          # so a lataria; vidro/cromo/interior ficam de fora
SIZE = 2048

# peca -> onde ela fica no carro, pra cada estilo saber onde pintar
FRENTE = ("hood", "bumperf", "fenderfl", "fenderfr", "fenderschassisf")
TETO = ("roof", "base")
LADO = ("doorl", "doorr", "skirts", "fendersr", "fenderfl", "fenderfr")
TRAS = ("boot", "bumperr", "spoiler", "diffuser")


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- UV da carroceria
def uv_masks(obj_path):
    """Rasteriza o UV da lataria: mascara geral + uma por peca."""
    VT = []
    part = None
    mat = None
    tris = {}                      # peca -> lista de triangulos em UV
    pend = []

    with open(obj_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("vt "):
                a = line.split()
                VT.append((float(a[1]), float(a[2])))
            elif line.startswith("o "):
                part = line.split()[1].strip()
            elif line.startswith("usemtl "):
                mat = line.split(None, 1)[1].strip().lower()
            elif line.startswith("f ") and part and mat:
                if not any(p in mat for p in PAINT_MATS):
                    continue
                idx = []
                for tok in line.split()[1:]:
                    q = tok.split("/")
                    if len(q) > 1 and q[1]:
                        idx.append(int(q[1]) - 1)
                if len(idx) >= 3:
                    tris.setdefault(part, []).append(idx[:3])

    if not tris:
        return None, {}

    def draw(tri_list):
        m = Image.new("L", (SIZE, SIZE), 0)
        d = ImageDraw.Draw(m)
        for t in tri_list:
            pts = []
            ok = True
            for i in t:
                if not (0 <= i < len(VT)):
                    ok = False; break
                u, v = VT[i]
                # o UV do jogo tem V invertido em relacao a imagem
                pts.append((u * SIZE, (1.0 - v) * SIZE))
            if ok:
                d.polygon(pts, fill=255)
        return m

    per_part = {k: draw(v) for k, v in tris.items()}
    todo = Image.new("L", (SIZE, SIZE), 0)
    for m in per_part.values():
        todo.paste(255, (0, 0), m)
    return todo, per_part


def bbox_of(mask):
    b = mask.getbbox()
    return b


# ---------------------------------------------------------------- decalques
def load_decal(base):
    """Devolve (forma_L, arte_RGB|None) a partir do par _m / _d / _t_d."""
    m_path = base + "_m.png"
    if not os.path.exists(m_path):
        return None, None
    m = Image.open(m_path).convert("RGB")
    shape = m.split()[1]                       # canal G = forma
    art = None
    for suf in ("_d.png", "_t_d.png"):
        p = base + suf
        if os.path.exists(p):
            im = Image.open(p).convert("RGB")
            ex = im.getextrema()
            flat = all(lo == hi for lo, hi in ex)      # branco puro = tintable
            if not flat:
                art = im
            break
    return shape, art


def decal_pool(swatch_root, categories):
    out = []
    for cat in categories:
        for f in glob.glob(os.path.join(swatch_root, "**", cat, "*_m.png"), recursive=True):
            out.append(f[:-6])
    return sorted(set(out))


def stamp(canvas, alpha, shape, art, color, box, rot=0, flip=False, opacity=255):
    """Cola um decalque dentro de box=(x0,y0,x1,y1), preservando proporcao."""
    x0, y0, x1, y1 = box
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    sw, sh = shape.size
    sc = min(bw / sw, bh / sh)
    nw, nh = max(1, int(sw * sc)), max(1, int(sh * sc))
    s = shape.resize((nw, nh), Image.LANCZOS)
    a = art.resize((nw, nh), Image.LANCZOS) if art is not None else None
    if flip:
        s = s.transpose(Image.FLIP_LEFT_RIGHT)
        if a is not None:
            a = a.transpose(Image.FLIP_LEFT_RIGHT)
    if rot:
        s = s.rotate(rot, expand=True, resample=Image.BICUBIC)
        if a is not None:
            a = a.rotate(rot, expand=True, resample=Image.BICUBIC)
    if opacity < 255:
        s = s.point(lambda v: v * opacity // 255)
    px = x0 + (bw - s.size[0]) // 2
    py = y0 + (bh - s.size[1]) // 2
    layer = a if a is not None else Image.new("RGB", s.size, color)
    canvas.paste(layer, (px, py), s)
    alpha.paste(s, (px, py), s)


def band(canvas, alpha, box, color, frac=0.22, offset=0.0):
    """Faixa horizontal simples — base das listras."""
    x0, y0, x1, y1 = box
    h = y1 - y0
    cy = y0 + h * (0.5 + offset)
    hh = max(2, int(h * frac / 2))
    d = ImageDraw.Draw(canvas); da = ImageDraw.Draw(alpha)
    d.rectangle([x0, int(cy - hh), x1, int(cy + hh)], fill=color)
    da.rectangle([x0, int(cy - hh), x1, int(cy + hh)], fill=255)


# ---------------------------------------------------------------- estilos
def estilo_racing(canvas, alpha, parts, pool, cores, rnd):
    c1, c2 = cores[0], cores[1 % len(cores)]
    for grupo, frac in ((TETO, 0.30), (FRENTE, 0.26), (TRAS, 0.26)):
        for name in grupo:
            if name in parts:
                b = bbox_of(parts[name])
                if b:
                    band(canvas, alpha, b, c1, frac)
                    band(canvas, alpha, b, c2, frac * 0.38)
    # patrocinios nas laterais
    marcas = [p for p in pool if any(k in p.lower() for k in ("logo", "sponsor", "brand", "ciay"))]
    if not marcas:
        marcas = pool
    for name in ("doorl", "doorr", "fendersr", "skirts"):
        if name not in parts:
            continue
        b = bbox_of(parts[name])
        if not b:
            continue
        for _ in range(rnd.randint(2, 4)):
            shp, art = load_decal(rnd.choice(marcas))
            if shp is None:
                continue
            w = (b[2] - b[0]); h = (b[3] - b[1])
            bw = int(w * rnd.uniform(0.18, 0.34)); bh = int(h * rnd.uniform(0.12, 0.26))
            x = rnd.randint(b[0], max(b[0], b[2] - bw)); y = rnd.randint(b[1], max(b[1], b[3] - bh))
            stamp(canvas, alpha, shp, art, cores[rnd.randrange(len(cores))],
                  (x, y, x + bw, y + bh), rot=rnd.choice([0, 0, 0, 90, 270]))


def estilo_listras(canvas, alpha, parts, pool, cores, rnd):
    c1, c2 = cores[0], cores[1 % len(cores)]
    for name in list(TETO) + list(FRENTE) + list(TRAS):
        if name not in parts:
            continue
        b = bbox_of(parts[name])
        if not b:
            continue
        band(canvas, alpha, b, c1, 0.10, -0.06)
        band(canvas, alpha, b, c1, 0.10, +0.06)
        band(canvas, alpha, b, c2, 0.03, 0.0)


def estilo_tribal(canvas, alpha, parts, pool, cores, rnd):
    tri = [p for p in pool if "tribal" in p.lower()] or pool
    for name in LADO + TRAS:
        if name not in parts:
            continue
        b = bbox_of(parts[name])
        if not b:
            continue
        for k in range(rnd.randint(2, 4)):
            shp, art = load_decal(rnd.choice(tri))
            if shp is None:
                continue
            w = b[2] - b[0]; h = b[3] - b[1]
            bw = int(w * rnd.uniform(0.5, 0.95)); bh = int(h * rnd.uniform(0.35, 0.8))
            x = rnd.randint(b[0], max(b[0], b[2] - bw)); y = rnd.randint(b[1], max(b[1], b[3] - bh))
            stamp(canvas, alpha, shp, art, cores[k % len(cores)],
                  (x, y, x + bw, y + bh), flip=rnd.random() < 0.5)


def estilo_camuflagem(canvas, alpha, parts, pool, cores, rnd):
    shapes = [p for p in pool if any(k in p.lower() for k in ("basicshape", "shapes", "abstract"))] or pool
    for name, m in parts.items():
        b = bbox_of(m)
        if not b:
            continue
        area = (b[2] - b[0]) * (b[3] - b[1])
        n = max(3, min(26, area // 42000))
        for _ in range(n):
            shp, art = load_decal(rnd.choice(shapes))
            if shp is None:
                continue
            s = rnd.randint(90, 300)
            x = rnd.randint(b[0], max(b[0], b[2] - s)); y = rnd.randint(b[1], max(b[1], b[3] - s))
            stamp(canvas, alpha, shp, None, cores[rnd.randrange(len(cores))],
                  (x, y, x + s, y + s), rot=rnd.randrange(0, 360), opacity=rnd.randint(190, 255))


def estilo_bandeira(canvas, alpha, parts, pool, cores, rnd):
    flags = [p for p in pool if "flag" in p.lower()] or pool
    pick = rnd.choice(flags)
    for name in list(TETO) + list(FRENTE) + list(TRAS) + list(LADO):
        if name not in parts:
            continue
        b = bbox_of(parts[name])
        if not b:
            continue
        shp, art = load_decal(pick)
        if shp is None:
            continue
        stamp(canvas, alpha, shp, art, cores[0], b, opacity=235)


ESTILOS = {"racing": (estilo_racing, ("*",)),
           "listras": (estilo_listras, ("*",)),
           "tribal": (estilo_tribal, ("sh_tribal_01", "sh_tribal_02", "sh_stripes_01")),
           "camuflagem": (estilo_camuflagem, ("sh_basicshapes", "pa_abstractpatterns")),
           "bandeira": (estilo_bandeira, ("rob_flags",))}

PALETAS = {"racing": ["e01b24", "ffffff", "141414"],
           "listras": ["ffffff", "1b3fa0", "141414"],
           "tribal": ["ffffff", "141414", "b0b4bb"],
           "camuflagem": ["3d4a2e", "5c6b46", "22281c", "808a68"],
           "bandeira": ["ffffff", "141414"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carro")
    ap.add_argument("--estilo", default="racing", choices=sorted(ESTILOS))
    ap.add_argument("--cores", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--saida", default=None)
    ap.add_argument("--raiz", default=r"F:/CarsNfSHeat")
    a = ap.parse_args()

    cdir = os.path.join(a.raiz, a.carro)
    obj = os.path.join(cdir, a.carro + ".obj")
    if not os.path.exists(obj):
        sys.exit("modelo nao encontrado: " + obj)

    rnd = random.Random(a.seed if a.seed is not None else random.randrange(1 << 30))
    cores = [hex_rgb(c) for c in (a.cores.split(",") if a.cores else PALETAS[a.estilo])]

    todo, parts = uv_masks(obj)
    if todo is None:
        sys.exit("esse carro nao tem material de lataria com UV utilizavel")
    print("pecas de lataria: %d" % len(parts))

    fn, cats = ESTILOS[a.estilo]
    swatch_root = os.path.join(a.raiz, "_swatches")
    pool = decal_pool(swatch_root, cats) if cats != ("*",) else decal_pool(swatch_root, ["*"])
    if not pool:                      # fallback: qualquer decalque
        pool = [f[:-6] for f in glob.glob(os.path.join(swatch_root, "**", "*_m.png"), recursive=True)]
    print("decalques disponiveis: %d" % len(pool))

    canvas = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    alpha = Image.new("L", (SIZE, SIZE), 0)
    fn(canvas, alpha, parts, pool, cores, rnd)

    # nada pode vazar pra fora da lataria
    alpha = Image.composite(alpha, Image.new("L", (SIZE, SIZE), 0), todo)

    out = a.saida or os.path.join(cdir, a.carro + "_vinil.png")
    res = canvas.convert("RGBA")
    res.putalpha(alpha)
    res.save(out)
    cov = sum(alpha.resize((256, 256)).getdata()) / (256 * 256 * 255)
    print("cobertura da lataria: %.0f%%" % (cov * 100))
    print("salvo: " + out)


if __name__ == "__main__":
    main()
