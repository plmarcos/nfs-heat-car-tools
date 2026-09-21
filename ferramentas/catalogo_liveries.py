"""
Folhas de contato dos vinis de fabrica (_liveries).

Cada vinil vem em dois arquivos: `_d` (a arte colorida) e `_m` (mascara de acabamento).
O catalogo usa o `_d`, composto sobre xadrez porque boa parte tem fundo transparente.

Uso:  python catalogo_liveries.py <pasta _liveries>
"""
import os, sys, glob
from PIL import Image, ImageDraw

root = sys.argv[1] if len(sys.argv) > 1 else r"F:\CarsNfSHeat\_liveries"
outdir = os.path.join(root, "_catalogo")
os.makedirs(outdir, exist_ok=True)

CELL, COLS, PAD, LABEL_H = 190, 8, 4, 13
_cache = {}


def checker(size, step=14, a=(152, 152, 158), b=(120, 120, 126)):
    if size in _cache:
        return _cache[size].copy()
    img = Image.new("RGB", size, a)
    d = ImageDraw.Draw(img)
    for yy in range(0, size[1], step):
        for xx in range(0, size[0], step):
            if ((xx // step) + (yy // step)) % 2:
                d.rectangle([xx, yy, xx + step - 1, yy + step - 1], fill=b)
    _cache[size] = img
    return img.copy()


groups = {}
for f in glob.glob(os.path.join(root, "**", "*_d.png"), recursive=True):
    if os.sep + "_catalogo" + os.sep in f:
        continue
    cat = os.path.basename(os.path.dirname(f))
    groups.setdefault(cat, []).append(f)

made = 0
for cat, files in sorted(groups.items()):
    files.sort()
    rows = (len(files) + COLS - 1) // COLS
    W = COLS * (CELL + PAD) + PAD
    H = rows * (CELL + PAD + LABEL_H) + PAD + 26
    sheet = Image.new("RGB", (W, H), (24, 24, 28))
    dr = ImageDraw.Draw(sheet)
    dr.text((PAD + 2, 7), "%s  (%d vinis)" % (cat, len(files)), fill=(235, 238, 245))

    for i, f in enumerate(files):
        try:
            im = Image.open(f).convert("RGBA")
        except Exception:
            continue
        tile = checker(im.size)
        tile.paste(im.convert("RGB"), (0, 0), im.split()[3])
        tile = tile.resize((CELL, CELL))
        x = PAD + (i % COLS) * (CELL + PAD)
        y = 26 + PAD + (i // COLS) * (CELL + PAD + LABEL_H)
        sheet.paste(tile, (x, y))
        name = os.path.basename(f)[:-6]
        for pre in ("ai_persona_livery01_", "ai_perosna_livery01_", "ai_persona_", "livery_"):
            if name.startswith(pre):
                name = name[len(pre):]
                break
        dr.text((x + 1, y + CELL + 1), name[:26], fill=(150, 156, 168))

    sheet.save(os.path.join(outdir, cat + ".png"))
    made += 1
    print("%-24s %d vinis" % (cat, len(files)))

print("\nfolhas geradas: %d em %s" % (made, outdir))
