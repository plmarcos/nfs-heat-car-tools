"""
Monta folhas de contato dos decalques extraidos.

Os arquivos _thumb guardam a silhueta so no canal alfa (RGB e branco puro), entao no
Explorer aparecem em branco. Este script compoe o alfa sobre fundo escuro e gera uma
folha por categoria em _swatches\\_catalogo\\.

Uso:  python catalogo.py <pasta_swatches>
"""
import os, sys, glob
from PIL import Image, ImageDraw

root = sys.argv[1] if len(sys.argv) > 1 else r"F:\CarsNfSHeat\_swatches"
outdir = os.path.join(root, "_catalogo")
os.makedirs(outdir, exist_ok=True)

CELL = 128
COLS = 12
PAD = 4
LABEL_H = 14

thumbs = glob.glob(os.path.join(root, "**", "*_thumb.png"), recursive=True)
print("thumbs encontrados: %d" % len(thumbs))

groups = {}
for t in thumbs:
    d = os.path.dirname(t)
    if os.path.basename(d).lower() == "thumbnails":
        d = os.path.dirname(d)
    groups.setdefault(os.path.basename(d), []).append(t)

made = 0
_checker_cache = {}


def checker(size, step=16, a=(150, 150, 156), b=(118, 118, 124)):
    """Fundo xadrez cinza: arte clara e arte escura ficam legiveis no mesmo tile."""
    if size in _checker_cache:
        return _checker_cache[size].copy()
    img = Image.new("RGB", size, a)
    d = ImageDraw.Draw(img)
    for yy in range(0, size[1], step):
        for xx in range(0, size[0], step):
            if ((xx // step) + (yy // step)) % 2:
                d.rectangle([xx, yy, xx + step - 1, yy + step - 1], fill=b)
    _checker_cache[size] = img
    return img.copy()


def common_prefix(names):
    if len(names) < 2:
        return ""
    p = names[0]
    for n in names[1:]:
        i = 0
        while i < len(p) and i < len(n) and p[i] == n[i]:
            i += 1
        p = p[:i]
        if not p:
            break
    # nao cortar no meio de uma palavra
    return p[:p.rfind("_") + 1] if "_" in p else ""


for cat, files in sorted(groups.items()):
    files.sort()
    # rotulos: tirar o prefixo que todos compartilham, senao so sobra o pedaco comum
    raw = [os.path.basename(f).replace("_thumb.png", "") for f in files]
    pre = common_prefix(raw)
    labels = [r[len(pre):] if pre and r.startswith(pre) else r for r in raw]
    rows = (len(files) + COLS - 1) // COLS
    W = COLS * (CELL + PAD) + PAD
    H = rows * (CELL + PAD + LABEL_H) + PAD + 26
    sheet = Image.new("RGB", (W, H), (24, 24, 28))
    dr = ImageDraw.Draw(sheet)
    dr.text((PAD + 2, 7), "%s  (%d)" % (cat, len(files)), fill=(235, 238, 245))

    for i, f in enumerate(files):
        try:
            im = Image.open(f).convert("RGBA")
        except Exception:
            continue
        # Decalque colorido (bandeiras, logos) traz a arte no RGB; decalque "tintable"
        # vem com RGB branco e a forma so no alfa. Compor o RGB real usando o alfa cobre
        # os dois casos. O fundo e xadrez pra arte preta e arte branca aparecerem igual.
        tile = checker(im.size)
        tile.paste(im.convert("RGB"), (0, 0), im.split()[3])
        tile = tile.resize((CELL, CELL))
        x = PAD + (i % COLS) * (CELL + PAD)
        y = 26 + PAD + (i // COLS) * (CELL + PAD + LABEL_H)
        sheet.paste(tile, (x, y))
        name = labels[i]
        if len(name) > 20:
            name = name[:19] + "~"
        dr.text((x + 1, y + CELL + 1), name, fill=(150, 156, 168))

    sheet.save(os.path.join(outdir, cat + ".png"))
    made += 1

print("folhas geradas: %d em %s" % (made, outdir))
