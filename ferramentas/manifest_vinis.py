"""
Casa cada vinil ai_persona com o carro dele e escolhe uma cor de base que combine.

A cor sai do proprio vinil: pega a cor media dos pixels opacos e escurece. Assim a
lataria harmoniza com a arte em vez de brigar com ela.
"""
import glob, os, re, json, colorsys
from PIL import Image

ROOT = os.environ.get("NFSHEAT_ACERVO", r"F:/CarsNfSHeat")
LIV = os.path.join(ROOT, "_liveries", "staticliveries", "ai_persona")

# casos que o casamento por token nao acerta
OVERRIDE = {
    "ai_persona_livery01_bmw_e46_m3_2003": "car_bmw_m3e46_2003",
    "ai_persona_livery01_chevrolet_corvette_gs_2017_ks": "car_chevrolet_corvettegs_2017",
    "ai_persona_livery01_ferrarifxxkevo_2018": "car_ferrari_fxxkevoicon_2018",
    "template_narrative_anna_350z": "car_nissan_350zanariviera_2006",
}
# vinis genericos, sem carro associado
SKIP = ("prebakedwrap_",)


def toks(s):
    s = re.sub(r"^(ai_pers?ona_)?(livery\d*_)?", "", s)
    s = re.sub(r"^(car_|bike_|sd_)", "", s)
    return [t for t in re.split(r"[_]+", s) if t]


def score(a, b):
    A, B = set(toks(a)), set(toks(b))
    j = len(A & B) / max(1, len(A | B))
    # bonus por semelhanca de string sem separadores (pega m3e46 vs e46_m3)
    sa, sb = "".join(sorted(toks(a))), "".join(sorted(toks(b)))
    common = sum(1 for c in set(sa) if c in sb)
    return j + 0.001 * common


def base_color(path):
    im = Image.open(path).convert("RGBA").resize((96, 96))
    px = [p for p in im.getdata() if p[3] > 40]
    if not px:
        return "1a1d24"
    r = sum(p[0] for p in px) / len(px) / 255
    g = sum(p[1] for p in px) / len(px) / 255
    b = sum(p[2] for p in px) / len(px) / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    # escurece e satura um pouco: cor de carro, nao de textura
    l = max(0.10, min(0.26, l * 0.55))
    s = min(0.75, s * 1.25 + 0.12)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


cars = sorted(os.path.basename(d) for d in glob.glob(os.path.join(ROOT, "*"))
              if os.path.isdir(d) and not os.path.basename(d).startswith("_"))

jobs = []
skipped = []
for f in sorted(glob.glob(os.path.join(LIV, "*_d.png"))):
    name = os.path.basename(f)[:-6]
    if any(name.startswith(s) for s in SKIP):
        skipped.append((name, "vinil generico"))
        continue
    car = OVERRIDE.get(name)
    if not car:
        car = max(cars, key=lambda c: score(name, c))
        if score(name, car) < 0.45:
            skipped.append((name, "sem carro: melhor palpite " + car))
            continue
    obj = os.path.join(ROOT, car, car + "_com_rodas.obj")
    if not os.path.exists(obj):
        obj = os.path.join(ROOT, car, car + ".obj")
    if not os.path.exists(obj):
        skipped.append((name, "modelo nao existe: " + car))
        continue
    jobs.append({"livery": f.replace("\\", "/"), "obj": obj.replace("\\", "/"),
                 "car": car, "name": name, "color": base_color(f)})

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vinis_jobs.json")
json.dump(jobs, open(out, "w"), indent=1)
print("jobs: %d" % len(jobs))
print("pulados: %d" % len(skipped))
for n, why in skipped:
    print("   %-52s %s" % (n, why))
