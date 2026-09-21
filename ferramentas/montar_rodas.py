"""
Monta o carro com as quatro rodas no lugar.

Gera <carro>_com_rodas.obj a partir de <carro>.obj + <carro>_wheel.obj.

De onde vem cada numero:
  - diametro e largura do pneu: tireconfig do proprio jogo (dado autoritativo)
  - posicao dos eixos: ajuste de um circulo do raio conhecido ao labio do arco de roda
    (ver fitwheels.py). O raio vir do jogo deixa sobrar um unico grau de liberdade,
    o que torna o ajuste bem posto.

Cada carro sai com uma nota de confianca; os que nao passam no teste usam uma
estimativa proporcional e ficam marcados no relatorio.

Uso:  python montar_rodas.py <raiz> [carro ...]
"""
import os, sys, glob, math, json, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitwheels import car_wheels, load_all

SP = os.path.dirname(os.path.abspath(__file__))
TIRE_DIR = os.path.join(SP, "tirecfg")

DEF_DIA, DEF_WIDTH = 0.66, 0.235       # usados quando o carro nao tem tireconfig


def num(s):
    return float(s.replace(",", "."))


def tire_specs(car, donor_map):
    """(diam_front, diam_rear, width_front, width_rear) do tireconfig; herda do pai se preciso."""
    for name in (car, donor_map.get(car)):
        if not name:
            continue
        p = os.path.join(TIRE_DIR, name + ".xml")
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8", errors="replace").read()
        def g(field, default):
            m = re.search(r'name="%s">([^<]+)' % field, txt)
            return num(m.group(1)) if m else default
        df = g("DiameterFront", DEF_DIA)
        dr = g("DiameterRear", DEF_DIA)
        wf = g("SectionWidthFront", DEF_WIDTH * 1000) / 1000.0
        wr = g("SectionWidthRear", DEF_WIDTH * 1000) / 1000.0
        return df, dr, wf, wr, name
    return DEF_DIA, DEF_DIA, DEF_WIDTH, DEF_WIDTH, None


def read_obj_objects(path):
    """{nome: (verts, uvs, faces)} — faces com indices locais 1-based."""
    objs, cur = {}, None
    V, VT = [], []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("o "):
                cur = line.split()[1].strip()
                objs[cur] = {"f": [], "mtl": None}
            elif line.startswith("v "):
                p = line.split(); V.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith("vt "):
                p = line.split(); VT.append((float(p[1]), float(p[2])))
            elif line.startswith("usemtl ") and cur:
                objs[cur]["mtl"] = line.split(None, 1)[1].strip()
            elif line.startswith("f ") and cur:
                objs[cur]["f"].append(line.split()[1:])
    return V, VT, objs


def assemble(cdir, spec, out_path, tire_path=None):
    name = os.path.basename(cdir)
    body = os.path.join(cdir, name + ".obj")
    wheel = os.path.join(cdir, name + "_wheel.obj")
    if not (os.path.exists(body) and os.path.exists(wheel)):
        return None

    WV, WVT, WO = read_obj_objects(wheel)
    if not WO:
        return None

    # Nos carros o mesh da roda e SO O ARO: raio externo ~0.247 contra o raio interno
    # ~0.239 do pneu compartilhado. As motos ja trazem o pneu proprio, entao nao levam
    # o compartilhado. Aro e pneu sao desenhados pra encaixar em escala nativa: uma
    # escala unica pros dois mantem a proporcao certa.
    TV, TVT, TO = ([], [], {})
    if tire_path and os.path.exists(tire_path):
        TV, TVT, TO = read_obj_objects(tire_path)

    # raio nativo do mesh da roda (o eixo e X, entao o raio esta no plano YZ)
    def native_radius(objname):
        idx = set()
        for f in WO[objname]["f"]:
            for tok in f:
                idx.add(int(tok.split("/")[0]) - 1)
        if not idx:
            return None, None
        pts = [WV[i] for i in idx if 0 <= i < len(WV)]
        r = max(math.hypot(p[1], p[2]) for p in pts)
        w = max(p[0] for p in pts) - min(p[0] for p in pts)
        return r, w

    front_obj = next((k for k in WO if "wheelf" in k.lower()), None)
    rear_obj = next((k for k in WO if "wheelr" in k.lower()), None)
    if front_obj is None:
        front_obj = list(WO)[0]
    if rear_obj is None:
        rear_obj = front_obj

    body_txt = open(body, encoding="utf-8", errors="replace").read()
    nV = body_txt.count("\nv ") + (1 if body_txt.startswith("v ") else 0)
    nVT = body_txt.count("\nvt ") + (1 if body_txt.startswith("vt ") else 0)

    out = [body_txt.rstrip("\n"), "", "# ---- rodas montadas ----"]
    vbase, vtbase = nV, nVT

    # Moto tem uma roda por eixo, na linha de centro — nao dois pares afastados.
    axles = (
        ("f", front_obj, spec["z_front"], spec["r_front"], spec["w_front"]),
        ("r", rear_obj,  spec["z_rear"],  spec["r_rear"],  spec["w_rear"]),
    )
    placements = []
    if spec.get("single_track"):
        for a in axles:
            placements.append((+1,) + a)
    else:
        for side in (+1, -1):
            for a in axles:
                placements.append((side,) + a)

    def mesh_span(verts, obj):
        idx = set()
        for f in obj["f"]:
            for tok in f:
                idx.add(int(tok.split("/")[0]) - 1)
        pts = [verts[i] for i in sorted(idx) if 0 <= i < len(verts)]
        if not pts:
            return None, None
        return (max(math.hypot(p[1], p[2]) for p in pts),
                max(p[0] for p in pts) - min(p[0] for p in pts))

    tire_obj = list(TO)[0] if TO else None
    tire_r = tire_w = None
    if tire_obj:
        tire_r, tire_w = mesh_span(TV, TO[tire_obj])

    def emit(verts, vts, obj, s_rad, s_wid, xc, yc, zc, side, label):
        nonlocal vbase, vtbase
        idx = set()
        for f in obj["f"]:
            for tok in f:
                idx.add(int(tok.split("/")[0]) - 1)
        idx = sorted(i for i in idx if 0 <= i < len(verts))
        if not idx:
            return
        remap = {}
        out.append("o " + label)
        if obj["mtl"]:
            out.append("usemtl " + obj["mtl"])
        for k, i in enumerate(idx):
            x, y, zz = verts[i]
            # espelha em X no lado direito pra roda nao ficar do avesso
            X = xc + (x * s_wid if side > 0 else -x * s_wid)
            Y = yc + y * s_rad
            Z = zc + zz * s_rad
            out.append("v %.6f %.6f %.6f" % (X, Y, Z))
            remap[i + 1] = vbase + k + 1
        vbase += len(idx)

        tidx = set()
        for f in obj["f"]:
            for tok in f:
                p = tok.split("/")
                if len(p) > 1 and p[1]:
                    tidx.add(int(p[1]) - 1)
        tidx = sorted(i for i in tidx if 0 <= i < len(vts))
        tremap = {}
        for k, i in enumerate(tidx):
            u, v = vts[i]
            out.append("vt %.6f %.6f" % (u, v))
            tremap[i + 1] = vtbase + k + 1
        vtbase += len(tidx)

        for f in obj["f"]:
            toks = []
            for tok in f:
                p = tok.split("/")
                vi = remap.get(int(p[0]))
                if vi is None:
                    toks = None; break
                if len(p) > 1 and p[1]:
                    ti = tremap.get(int(p[1]))
                    toks.append("%d/%d" % (vi, ti) if ti else str(vi))
                else:
                    toks.append(str(vi))
            if toks:
                # lado direito inverte a orientacao por causa do espelhamento
                if side < 0:
                    toks = list(reversed(toks))
                out.append("f " + " ".join(toks))

    for side, which, objn, z, r, w in placements:
        nr, nw = native_radius(objn)
        if not nr:
            continue
        # Com pneu: a escala vem do pneu (aro e pneu casam em escala nativa).
        # Sem pneu (motos): o proprio mesh ja e a roda inteira.
        if tire_r:
            s_rad = r / tire_r
            s_wid = (w / tire_w) if tire_w else s_rad
        else:
            s_rad = r / nr
            s_wid = (w / nw) if nw else s_rad
        # meia_bitola JA e a posicao do centro da roda (ver fitwheels.half_track),
        # nao a lateral da carroceria — nao subtrair a largura do pneu aqui.
        if spec.get("single_track"):
            xc = 0.0                       # moto: roda na linha de centro
        else:
            xc = side * max(0.15, spec["half_track_f"] if which == "f" else spec["half_track_r"])
        tag = ("L" if side > 0 else "R") + which

        emit(WV, WVT, WO[objn], s_rad, s_wid, xc, r, z, side, "rim_" + tag)
        if tire_obj:
            emit(TV, TVT, TO[tire_obj], s_rad, s_wid, xc, r, z, side, "tire_" + tag)

    open(out_path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    return out_path


def build_donor_map():
    """Variante -> pasta que tem os dados (mesmo criterio usado na extracao)."""
    import csv
    m = {}
    p = os.path.join(SP, "report2.csv")
    if os.path.exists(p):
        with open(p, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                if row.get("body") and row.get("folder"):
                    m[row["body"]] = row["folder"]
    return m


CSV_NAME = "_rodas_eixos.csv"
CSV_COLS = ["carro", "z_frente", "z_tras", "meia_bitola_f", "meia_bitola_t",
            "diam_frente", "diam_tras", "larg_frente", "larg_tras", "confianca"]


def load_overrides(root):
    """Le F:\\CarsNfSHeat\\_rodas_eixos.csv, se existir. Editar a linha de um carro
    e rodar de novo e a forma de corrigir uma roda fora do lugar."""
    import csv
    p = os.path.join(root, CSV_NAME)
    if not os.path.exists(p):
        return {}
    out = {}
    with open(p, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            c = row.get("carro")
            if not c:
                continue
            try:
                out[c] = {k: float(row[k].replace(",", ".")) for k in CSV_COLS[1:-1]}
            except (KeyError, ValueError):
                pass
    return out


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else r"F:/CarsNfSHeat"
    only = set(sys.argv[2:])
    donor = build_donor_map()
    overrides = load_overrides(root)
    if overrides:
        print("usando %d ajustes de %s" % (len(overrides), CSV_NAME))
    dirs = sorted(d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d)
                  and not os.path.basename(d).startswith("_"))
    if only:
        dirs = [d for d in dirs if os.path.basename(d) in only]

    report = []
    for d in dirs:
        name = os.path.basename(d)
        df, dr, wf, wr, src = tire_specs(name, donor)
        fit = car_wheels(d, df, dr)
        conf = "ok"
        if not fit:
            # fallback proporcional: entre-eixos ~ 60% do comprimento
            v = load_all(os.path.join(d, name + ".obj"))
            if not v:
                report.append((name, "sem-modelo", None)); continue
            ys = [p[1] for p in v]; zs = [p[2] for p in v]; xs = [p[0] for p in v]
            z0, z1 = min(zs), max(zs); L = z1 - z0
            maxx = max(abs(min(xs)), max(xs))
            mid = (z0 + z1) / 2
            fit = {"z_front": mid + 0.30 * L, "z_rear": mid - 0.30 * L,
                   "half_track_front": maxx * 0.88, "half_track_rear": maxx * 0.88,
                   "ground": min(ys)}
            conf = "estimado"
        else:
            # O ajuste so pode andar ate 17 cm da ancora proporcional. Quando ele vai
            # ate a borda da janela, e sinal de que o arco nao deu sinal claro — vale
            # conferir esse carro a olho.
            v = load_all(os.path.join(d, name + ".obj"))
            zs = [p[2] for p in v]
            L = max(zs) - min(zs)
            dev = abs(fit["wheelbase"] - 0.582 * L)
            if dev > 0.30:
                conf = "conferir"

        spec = {"z_front": fit["z_front"], "z_rear": fit["z_rear"],
                "r_front": df / 2, "r_rear": dr / 2, "w_front": wf, "w_rear": wr,
                "half_track_f": fit["half_track_front"], "half_track_r": fit["half_track_rear"]}

        ov = overrides.get(name)
        if ov:
            spec.update(z_front=ov["z_frente"], z_rear=ov["z_tras"],
                        half_track_f=ov["meia_bitola_f"], half_track_r=ov["meia_bitola_t"],
                        r_front=ov["diam_frente"] / 2, r_rear=ov["diam_tras"] / 2,
                        w_front=ov["larg_frente"], w_rear=ov["larg_tras"])
            df, dr = ov["diam_frente"], ov["diam_tras"]
            conf = "manual"

        # motos ja tem pneu proprio no _wheel.obj; carro precisa do compartilhado
        is_bike = name.startswith("bike_")
        spec["single_track"] = is_bike
        tire = None if is_bike else os.path.join(root, "_pneu", "shared_tire_race01.obj")
        out = os.path.join(d, name + "_com_rodas.obj")
        ok = assemble(d, spec, out, tire)
        wb = spec["z_front"] - spec["z_rear"]
        report.append({"carro": name, "z_frente": round(spec["z_front"], 4),
                       "z_tras": round(spec["z_rear"], 4),
                       "meia_bitola_f": round(spec["half_track_f"], 4),
                       "meia_bitola_t": round(spec["half_track_r"], 4),
                       "diam_frente": round(df, 4), "diam_tras": round(dr, 4),
                       "larg_frente": round(spec["w_front"], 4),
                       "larg_tras": round(spec["w_rear"], 4),
                       "confianca": conf if ok else "falhou"})
        print("%-48s %-10s wb=%.3f dia=%.3f/%.3f %s" %
              (name, conf, wb, df, dr, "" if src in (name, None) else "(tire de " + str(src) + ")"))

    # Merge: rodar um subconjunto nao pode apagar as linhas dos outros carros.
    import csv
    path = os.path.join(root, CSV_NAME)
    rows = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                if row.get("carro"):
                    rows[row["carro"]] = row
    for r in report:
        rows[r["carro"]] = r
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLS)
        w.writeheader()
        for k in sorted(rows):
            w.writerow(rows[k])
    from collections import Counter
    print("\n", Counter(r["confianca"] for r in report))
    print("planilha: %s" % os.path.join(root, CSV_NAME))


if __name__ == "__main__":
    main()
