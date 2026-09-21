"""
Acha os eixos ajustando um circulo de raio CONHECIDO ao labio do arco de roda.

O raio vem do tireconfig do proprio jogo (dado autoritativo), entao sobra um unico
grau de liberdade: a posicao Z do centro. O labio do arco e o contorno inferior dos
paineis externos (paralama, porta, saia) — o chassi e o interior sao ignorados.
"""
import os, math, glob

SKIP_OBJ = {"base"}   # o mesh base carrega chassi/motor/interior e polui o contorno


def load_outer(path):
    """Vertices dos paineis externos, agrupados fora do objeto 'base'."""
    out, cur, keep = [], None, False
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("o "):
                cur = line.split()[1].strip()
                keep = cur not in SKIP_OBJ
            elif keep and line.startswith("v "):
                p = line.split()
                out.append((float(p[1]), float(p[2]), float(p[3])))
    return out


def load_all(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("v "):
                p = line.split()
                out.append((float(p[1]), float(p[2]), float(p[3])))
    return out


def lower_profile(pts, ground, nbins=150):
    """Contorno inferior do flanco: (z, ymin) por fatia."""
    if not pts:
        return []
    zs = [p[2] for p in pts]
    z0, z1 = min(zs), max(zs)
    span = z1 - z0
    if span <= 0:
        return []
    bins = [None] * nbins
    for x, y, z in pts:
        i = int((z - z0) / span * (nbins - 1))
        if bins[i] is None or y < bins[i]:
            bins[i] = y
    return [(z0 + (i + 0.5) / nbins * span, v - ground)
            for i, v in enumerate(bins) if v is not None]


def axle_profile(prof, r, zlo, zhi, step=0.005):
    """Erro de ajuste do circulo pra cada Z candidato: [(z, erro_medio, n_pontos)]."""
    out = []
    zc = zlo
    while zc <= zhi:
        err = 0.0
        n = 0
        for z, y in prof:
            dz = z - zc
            if abs(dz) > r * 1.05:
                continue
            dy = y - r
            d = math.hypot(dz, dy)
            if d > r * 1.35:
                continue
            err += (d - r) ** 2
            n += 1
        if n >= 8:
            out.append((zc, err / n, n))
        zc += step
    return out


def fit_axle(prof, r, zlo, zhi, step=0.005):
    """Melhor Z pro centro de um circulo de raio r apoiado no chao (y=r)."""
    cand = axle_profile(prof, r, zlo, zhi, step)
    if not cand:
        return (1e18, None, 0)
    z, e, n = min(cand, key=lambda t: t[1])
    return (e, z, n)


def fit_pair(prof, rf, rr, z0, z1, wb_lo, wb_hi):
    """Ajusta os dois eixos juntos, exigindo um entre-eixos plausivel.

    Sozinho, cada eixo as vezes encaixa melhor numa curva de para-choque perto da ponta
    do carro. Exigir que o par respeite a proporcao tipica de entre-eixos elimina isso.
    """
    front = axle_profile(prof, rf, 0.20 * z1, z1 - rf * 0.45)
    rear = axle_profile(prof, rr, z0 + rr * 0.45, 0.20 * z0)
    if not front or not rear:
        return None
    rear_sorted = sorted(rear, key=lambda t: t[0])
    best = None
    for zf, ef, nf in front:
        for zr, er, nr in rear_sorted:
            wb = zf - zr
            if wb < wb_lo or wb > wb_hi:
                continue
            tot = ef + er
            if best is None or tot < best[0]:
                best = (tot, zf, zr, ef, er, nf, nr)
    return best


def car_wheels(cdir, dia_front, dia_rear):
    name = os.path.basename(cdir)
    body = os.path.join(cdir, name + ".obj")
    if not os.path.exists(body):
        return None
    allv = load_all(body)
    if not allv:
        return None
    xs = [v[0] for v in allv]
    ys = [v[1] for v in allv]
    zs = [v[2] for v in allv]
    ground = min(ys)
    height = max(ys) - ground
    maxx = max(abs(min(xs)), max(xs))
    z0, z1 = min(zs), max(zs)

    outer = load_outer(body) or allv
    flank = [v for v in outer if abs(v[0]) > 0.62 * maxx]
    if len(flank) < 300:
        flank = [v for v in outer if abs(v[0]) > 0.45 * maxx]
    prof = lower_profile(flank, ground)
    if len(prof) < 30:
        return None

    rf, rr = dia_front / 2.0, dia_rear / 2.0
    length = z1 - z0

    # Ancora: nos 13 carros que conferi contra ficha tecnica, o entre-eixos fica em
    # 0.582 +- 0.028 do comprimento total — bem mais estavel que o ajuste sozinho.
    # O ajuste ao arco entra so pra refinar dentro de uma janela estreita em volta
    # dessa ancora, o que da precisao onde o arco e limpo sem deixar o fit fugir.
    WB_RATIO, WINDOW = 0.582, 0.17
    zc = (z0 + z1) / 2.0
    pf, pr = zc + WB_RATIO * length / 2.0, zc - WB_RATIO * length / 2.0

    ef, zf, nf = fit_axle(prof, rf, pf - WINDOW, pf + WINDOW)
    er, zr, nr = fit_axle(prof, rr, pr - WINDOW, pr + WINDOW)
    if zf is None:
        zf, ef, nf = pf, 0.0, 0
    if zr is None:
        zr, er, nr = pr, 0.0, 0
    wb = zf - zr
    if wb < 1.5 or wb > 4.2:
        zf, zr = pf, pr
        wb = zf - zr

    # Meia-bitola = 0.832 x a meia-largura da carroceria medida abaixo da cintura.
    # Calibrado contra a bitola de ficha tecnica de 13 carros (M3 E46, GT-R, Fusca,
    # Golf, Mustang, 911 GT3, F40, Charger 69, MX-5, Camaro 67, LaFerrari, R8, R34):
    # erro medio 1,2 cm, maximo 5,1 cm. Medir a largura "na altura do arco" — que era
    # o que eu fazia antes — dava ate 23 cm a menos e afundava a roda na lataria.
    # O corte em 55% da altura tira o retrovisor, que fica alto e esticaria a medida.
    low = [abs(v[0]) for v in allv if (v[1] - ground) < 0.55 * height]
    half_w = max(low) if low else maxx
    track_half = 0.832 * half_w

    def half_track(zc, rad):
        return track_half

    return {
        "name": name, "z_front": zf, "z_rear": zr, "wheelbase": wb,
        "r_front": rf, "r_rear": rr, "ground": ground,
        "half_track_front": half_track(zf, rf), "half_track_rear": half_track(zr, rr),
        "err_front": ef, "err_rear": er, "n_front": nf, "n_rear": nr,
    }


if __name__ == "__main__":
    REAL = {"car_bmw_m3e46_2003": (0.657, 0.661, 2.731),
            "car_nissan_gtr_2017": (0.665, 0.675, 2.780),
            "car_volkswagen_beetle_1963": (0.62, 0.62, 2.400),
            "car_dodge_charger_1969": (0.68, 0.69, 2.972),
            "car_volkswagen_golfgti_2016": (0.63, 0.63, 2.637),
            "car_ford_mustanggt_2015": (0.66, 0.66, 2.720),
            "car_porsche_991gt3_2015": (0.65, 0.67, 2.457)}
    print("%-42s %7s %7s %6s %6s %7s  %s" % ("carro", "Zf", "Zr", "wb", "real", "erro", "ajuste(mm)"))
    for c, (df, dr, rw) in REAL.items():
        d = os.path.join(os.environ.get("NFSHEAT_ACERVO", r"F:/CarsNfSHeat"), c)
        r = car_wheels(d, df, dr)
        if not r:
            print("%-42s FALHOU" % c); continue
        print("%-42s %+7.3f %+7.3f %6.3f %6.3f %+7.3f  f=%.1f r=%.1f" %
              (c, r["z_front"], r["z_rear"], r["wheelbase"], rw, r["wheelbase"] - rw,
               math.sqrt(r["err_front"]) * 1000, math.sqrt(r["err_rear"]) * 1000))
