"""
patterns.py - Generation procedurale de cartes de hauteur tuilables, puis
conversion en normal maps au format LabPBR.

Toutes les fonctions renvoient une carte de hauteur : une liste de flottants
dans [0, 1] de longueur w*h (0 = creux, 1 = surface). Les motifs sont
tuilables (wrap) pour qu'il n'y ait pas de couture entre deux blocs adjacents.
"""

import math
import random

# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------


def _seed_of(name, salt=0):
    """Graine deterministe derivee du nom de texture (rendu reproductible)."""
    h = 2166136261
    for ch in name.encode("utf-8"):
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return (h ^ (salt * 2654435761)) & 0xFFFFFFFF


def _smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def flat(w, h, value=1.0, **_):
    return [value] * (w * h)


def value_noise(w, h, name="", scale=4, seed_salt=0, **_):
    """Bruit de valeur tuilable : grille scale x scale interpolee en douceur."""
    scale = max(1, min(scale, max(w, h)))
    rnd = random.Random(_seed_of(name, seed_salt + scale * 977))
    grid = [[rnd.random() for _ in range(scale)] for _ in range(scale)]
    out = [0.0] * (w * h)
    for y in range(h):
        fy = y * scale / h
        y0 = int(fy) % scale
        y1 = (y0 + 1) % scale
        ty = _smoothstep(fy - int(fy))
        for x in range(w):
            fx = x * scale / w
            x0 = int(fx) % scale
            x1 = (x0 + 1) % scale
            tx = _smoothstep(fx - int(fx))
            a = grid[y0][x0] + (grid[y0][x1] - grid[y0][x0]) * tx
            b = grid[y1][x0] + (grid[y1][x1] - grid[y1][x0]) * tx
            out[y * w + x] = a + (b - a) * ty
    return out


def fbm(w, h, name="", octaves=3, scale=2, gain=0.5, **_):
    """Bruit fractal : plusieurs octaves de value_noise."""
    out = [0.0] * (w * h)
    amp, total, s = 1.0, 0.0, scale
    for o in range(octaves):
        layer = value_noise(w, h, name=name, scale=s, seed_salt=o * 31 + 7)
        for i in range(w * h):
            out[i] += layer[i] * amp
        total += amp
        amp *= gain
        s = min(s * 2, max(w, h))
    return [v / total for v in out]


def speckle(w, h, name="", density=0.5, **_):
    """Grain pixel par pixel (sable, gravier, terre)."""
    rnd = random.Random(_seed_of(name, 4242))
    return [rnd.random() if rnd.random() < density else 0.5 for _ in range(w * h)]


def cells(w, h, name="", size=4, jitter=0.35, **_):
    """Cellules carrees d'altitudes differentes (graviers, blocs concasses)."""
    rnd = random.Random(_seed_of(name, 991))
    n = max(1, w // max(1, size))
    # les altitudes restent sous 1.0 : centrees sur 1.0, la moitie des cellules
    # butait sur le plafond et se retrouvait a la meme hauteur, la plus creusee
    # perdant meme sa rainure
    lvl = [[rnd.uniform(1.0 - jitter, 1.0) for _ in range(n)] for _ in range(n)]
    out = [0.0] * (w * h)
    for y in range(h):
        cy = (y * n // h) % n
        # une rainure marque la premiere ligne / colonne de chaque cellule :
        # la deduire du meme reseau que l'indice evite qu'elle derive vers
        # l'interieur des cellules quand w n'est pas divisible par la taille
        edge_y = cy != (((y - 1) * n // h) % n)
        for x in range(w):
            cx = (x * n // w) % n
            edge = edge_y or (cx != (((x - 1) * n // w) % n))
            out[y * w + x] = max(0.0, min(1.0, lvl[cy][cx] - (0.35 if edge else 0.0)))
    return out


# ---------------------------------------------------------------------------
# Motifs structures
# ---------------------------------------------------------------------------


def bricks(w, h, name="", rows=4, cols=2, mortar=1, depth=1.0, stagger=True, **_):
    """Appareil de briques : joints creuses, decalage d'une rangee sur deux."""
    rows, cols = max(1, rows), max(1, cols)
    rh = max(1, h // rows)
    cw = max(1, w // cols)
    out = [1.0] * (w * h)
    rnd = random.Random(_seed_of(name, 17))
    tint = [rnd.uniform(-0.10, 0.10) for _ in range(rows * cols + rows)]
    for y in range(h):
        r = y // rh
        off = (cw // 2) if (stagger and r % 2 == 1) else 0
        in_h_joint = (y % rh) < mortar
        for x in range(w):
            xx = (x + off) % w
            in_v_joint = (xx % cw) < mortar
            i = y * w + x
            if in_h_joint or in_v_joint:
                out[i] = 1.0 - depth
            else:
                out[i] = min(1.0, 0.88 + tint[(r * cols + xx // cw) % len(tint)])
    return out


def planks(w, h, name="", count=4, axis="h", groove=1, depth=0.7, **_):
    """Planches paralleles avec rainure entre chaque, plus un leger galbe."""
    out = [1.0] * (w * h)
    rnd = random.Random(_seed_of(name, 53))
    count = max(1, count)
    span = h if axis == "h" else w
    pw = max(1, span // count)
    tint = [rnd.uniform(-0.08, 0.06) for _ in range(count + 1)]
    for y in range(h):
        for x in range(w):
            t = y if axis == "h" else x
            idx = (t // pw) % (count + 1)
            local = t % pw
            i = y * w + x
            if local < groove:
                out[i] = 1.0 - depth
            else:
                # galbe : la planche est legerement bombee en son centre
                c = (local - groove) / max(1.0, (pw - groove - 1))
                bow = 0.06 * math.sin(math.pi * c)
                out[i] = min(1.0, 0.90 + tint[idx] + bow)
    return out


def strips(w, h, name="", axis="v", width=2, depth=0.35, **_):
    """Bandes paralleles (fibres de bois, bambou, tiges)."""
    out = [1.0] * (w * h)
    rnd = random.Random(_seed_of(name, 71))
    span = w if axis == "v" else h
    # les bandes partagent le span en parts exactes : avec une simple division
    # entiere, la derniere bande partielle se repliait sur la premiere et
    # doublait la rainure a la jointure entre deux blocs
    # au moins deux pixels par bande, sinon la rainure occupe toute la bande
    # et deux rainures se retrouvent collees
    n = max(1, min(max(1, span // 2), int(round(span / float(max(1, width))))))
    lv = [rnd.uniform(0.55, 1.0) for _ in range(n)]
    for y in range(h):
        for x in range(w):
            t = x if axis == "v" else y
            k = t * n // span
            edge = (t * n) % span < n          # premiere ligne de la bande
            out[y * w + x] = max(0.0, lv[k] - (depth if edge else 0.0))
    return out


def grain(w, h, name="", axis="v", amp=0.25, **_):
    """Fines fibres de bois superposables a un autre motif."""
    rnd = random.Random(_seed_of(name, 131))
    lanes = [rnd.uniform(1.0 - amp, 1.0) for _ in range(max(w, h))]
    out = [0.0] * (w * h)
    for y in range(h):
        for x in range(w):
            t = x if axis == "v" else y
            u = (y if axis == "v" else x) / float(h if axis == "v" else w)
            wobble = 0.03 * math.sin(2.0 * math.pi * u + t)
            out[y * w + x] = max(0.0, min(1.0, lanes[t % len(lanes)] + wobble))
    return out


def rings(w, h, name="", spacing=2.2, depth=0.3, **_):
    """Cernes concentriques : dessus des buches."""
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    out = [0.0] * (w * h)
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy)
            v = 0.5 + 0.5 * math.cos(d / spacing * math.pi * 2.0)
            out[y * w + x] = 1.0 - depth * v
    return out


def grid(w, h, name="", n=2, groove=1, depth=0.8, **_):
    """Grille reguliere (carrelage, blocs cisele, quartz)."""
    n = max(1, n)
    cw = max(1, w // n)
    ch = max(1, h // n)
    out = [1.0] * (w * h)
    for y in range(h):
        for x in range(w):
            edge = (x % cw) < groove or (y % ch) < groove
            out[y * w + x] = (1.0 - depth) if edge else 0.92
    return out


def frame(w, h, name="", border=1, depth=0.5, inner=0.85, **_):
    """Bordure en relief autour d'un panneau plat (blocs cisele, coffres).

    La largeur de bordure est bornee pour qu'il reste toujours un panneau :
    au-dela, les deux anneaux se rejoignaient et le motif devenait uniforme.
    """
    border = max(1, min(border, max(1, (min(w, h) - 1) // 4)))
    out = [inner] * (w * h)
    for y in range(h):
        for x in range(w):
            if x < border or y < border or x >= w - border or y >= h - border:
                out[y * w + x] = 1.0
            elif x < border * 2 or y < border * 2 or x >= w - border * 2 or y >= h - border * 2:
                out[y * w + x] = 1.0 - depth
    return out


def weave(w, h, name="", size=2, amp=0.35, **_):
    """Tissage regulier : laine, tapis, tissus."""
    out = [0.0] * (w * h)
    size = max(1, size)
    for y in range(h):
        for x in range(w):
            u = math.sin((x / size) * math.pi) * math.cos((y / size) * math.pi)
            out[y * w + x] = 0.75 + amp * 0.5 * u
    return out


def crystal(w, h, name="", facets=3, **_):
    """Facettes anguleuses : amethyste, glace, cristaux."""
    rnd = random.Random(_seed_of(name, 613))
    pts = [(rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0.55, 1.0)) for _ in range(max(2, facets))]
    out = [0.0] * (w * h)
    for y in range(h):
        for x in range(w):
            best, bv = 1e9, 0.7
            for (px, py, pv) in pts:
                dx = min(abs(x - px), w - abs(x - px))
                dy = min(abs(y - py), h - abs(y - py))
                d = dx * dx + dy * dy
                if d < best:
                    best, bv = d, pv
            out[y * w + x] = bv - 0.25 * (best ** 0.5) / max(w, h)
    return out


def organic(w, h, name="", amp=0.5, **_):
    """Relief souple et irregulier : feuillages, mousses, champignons."""
    base = fbm(w, h, name=name, octaves=3, scale=3, gain=0.55)
    sp = speckle(w, h, name=name, density=0.35)
    return [max(0.0, min(1.0, 0.55 + (base[i] - 0.5) * amp + (sp[i] - 0.5) * 0.18))
            for i in range(w * h)]


def scales(w, h, name="", size=4, depth=0.4, **_):
    """Ecailles arrondies : prismarine, tortue, cuivre patine."""
    size = max(1, size)
    out = [0.0] * (w * h)
    for y in range(h):
        for x in range(w):
            ox = (x + (size // 2 if (y // size) % 2 else 0)) % w
            u = (ox % size) / size - 0.5
            v = (y % size) / size - 0.5
            d = min(1.0, math.hypot(u, v) * 2.0)
            out[y * w + x] = 1.0 - depth * d
    return out


def slats(w, h, name="", n=4, axis="h", depth=0.9, thickness=1, **_):
    """Barreaux / claustras ajoures : grilles de cuivre, barreaux de fer."""
    out = [1.0] * (w * h)
    span = h if axis == "h" else w
    step = max(2, span // max(1, n))
    thickness = max(1, min(thickness, step - 1))   # toujours au moins un vide
    for y in range(h):
        for x in range(w):
            t = y if axis == "h" else x
            out[y * w + x] = 1.0 if (t % step) < thickness else 1.0 - depth
    return out


PATTERNS = {
    "flat": flat,
    "noise": value_noise,
    "fbm": fbm,
    "speckle": speckle,
    "cells": cells,
    "bricks": bricks,
    "planks": planks,
    "strips": strips,
    "grain": grain,
    "rings": rings,
    "grid": grid,
    "frame": frame,
    "weave": weave,
    "crystal": crystal,
    "organic": organic,
    "scales": scales,
    "slats": slats,
}


def compose(layers, w, h, name=""):
    """Combine plusieurs motifs ponderes en une seule carte de hauteur [0,1].

    Le resultat est toujours etire sur toute la plage [0, 1], afin que la carte
    de hauteur exploite tout le canal alpha disponible pour le parallaxe. Par
    consequent le parametre `depth` d'un motif agit sur la forme et sur le
    rapport entre couches, pas sur l'amplitude finale : celle-ci se regle par
    materiau, avec `relief` (force de la normale) et `pom` (profondeur).
    """
    if not layers:
        return flat(w, h)
    acc = [0.0] * (w * h)
    total = 0.0
    for entry in layers:
        kind, weight = entry[0], entry[1]
        params = entry[2] if len(entry) > 2 else {}
        fn = PATTERNS[kind]
        layer = fn(w, h, name=name, **params)
        for i in range(w * h):
            acc[i] += layer[i] * weight
        total += weight
    if total <= 0:
        return flat(w, h)
    out = [v / total for v in acc]
    lo, hi = min(out), max(out)
    if hi - lo < 1e-6:
        return [1.0] * (w * h)
    return [(v - lo) / (hi - lo) for v in out]


# ---------------------------------------------------------------------------
# Conversion hauteur -> normale / occlusion ambiante
# ---------------------------------------------------------------------------


def height_to_normal(height, w, h, strength=1.0):
    """Gradient central avec wrap -> normales tangentes, convention OpenGL
    (canal vert vers le haut de la texture), telle qu'attendue par LabPBR."""
    out = []
    for y in range(h):
        ym = (y - 1) % h
        yp = (y + 1) % h
        for x in range(w):
            xm = (x - 1) % w
            xp = (x + 1) % w
            gx = (height[y * w + xp] - height[y * w + xm]) * 0.5
            gy = (height[yp * w + x] - height[ym * w + x]) * 0.5
            nx = -gx * strength * 4.0
            ny = gy * strength * 4.0
            nz = 1.0
            inv = 1.0 / math.sqrt(nx * nx + ny * ny + nz * nz)
            out.append((nx * inv, ny * inv, nz * inv))
    return out


def height_to_ao(height, w, h, strength=0.5, radius=1):
    """Occlusion ambiante grossiere : un pixel plus bas que ses voisins est
    occulte. Volontairement douce (plancher a 0.72) pour ne pas noircir le
    rendu, certains shaders multipliant deja cette AO dans l'eclairage direct."""
    out = [1.0] * (w * h)
    if strength <= 0:
        return out
    for y in range(h):
        for x in range(w):
            c = height[y * w + x]
            acc = 0.0
            n = 0
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx == 0 and dy == 0:
                        continue
                    v = height[((y + dy) % h) * w + ((x + dx) % w)]
                    acc += max(0.0, v - c)
                    n += 1
            occ = acc / max(1, n)
            out[y * w + x] = max(0.72, 1.0 - occ * strength * 2.2)
    return out
