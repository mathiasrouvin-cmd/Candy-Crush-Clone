#!/usr/bin/env python3
"""
preview.py - Rend une planche de previsualisation des cartes _n / _s produites,
sans lancer Minecraft.

Chaque vignette est un rendu Lambert + Blinn-Phong utilisant la normale du _n,
l'occlusion du canal B, la brillance du canal R du _s et l'emission du canal A.
L'albedo est volontairement gris neutre : on juge le relief et la matiere, pas
la couleur. Sert a verifier le pack avant de l'installer.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pngio import Image, read_png, write_png   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LIGHT = (-0.45, 0.55, 0.70)     # direction de la lumiere (x, y, z)
VIEW = (0.0, 0.0, 1.0)

# Couleurs des metaux predefinis LabPBR : permet de verifier d'un coup d'oeil
# que l'index ecrit dans le canal G du _s est bien celui attendu.
METAL_COLORS = {
    230: (196, 199, 199),   # fer
    231: (255, 226, 155),   # or
    232: (245, 246, 246),   # aluminium
    233: (196, 197, 196),   # chrome
    234: (250, 208, 192),   # cuivre
    235: (140, 142, 148),   # plomb
    236: (206, 204, 198),   # platine
    237: (252, 250, 245),   # argent
    255: (185, 187, 192),   # metal generique
}


def _norm(v):
    l = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / l for c in v)


def _environment(ry):
    """Environnement approxime : sol sombre en bas, ciel clair en haut.
    Sans ce terme un metal apparait noir - il ne fait que refleter."""
    return 0.09 + 0.76 * max(0.0, min(1.0, ry * 0.5 + 0.5))


def render_tile(n_img, s_img, size, albedo=(168, 168, 172)):
    """Rend une texture eclairee, agrandie a `size` px.

    Modele : diffus Lambert + speculaire Blinn-Phong + reflexion d'environnement
    ponderee par un Fresnel de Schlick. Les dielectriques utilisent un albedo
    gris neutre (on juge le relief, pas la couleur) ; les metaux utilisent la
    teinte de leur index LabPBR.
    """
    L = _norm(LIGHT)
    H = _norm(tuple(L[i] + VIEW[i] for i in range(3)))
    w, h = n_img.w, min(n_img.h, n_img.w)   # une seule image si texture animee
    out = Image(size, size)
    scale = size / float(w)
    for py in range(size):
        sy = min(h - 1, int(py / scale))
        for px in range(size):
            sx = min(w - 1, int(px / scale))
            n = n_img.get(sx, sy)
            s = s_img.get(sx, sy)
            nx = n[0] / 255.0 * 2.0 - 1.0
            ny = -(n[1] / 255.0 * 2.0 - 1.0)   # LabPBR : Y- (DirectX)
            nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
            ao = n[2] / 255.0
            smooth = s[0] / 255.0
            g = s[1]
            metal = g >= 230
            f0 = (METAL_COLORS.get(g, (200, 200, 200))[0] / 255.0) if metal else g / 255.0
            emission = 0.0 if s[3] == 255 else s[3] / 255.0

            ndl = max(0.0, nx * L[0] + ny * L[1] + nz * L[2])
            ndh = max(0.0, nx * H[0] + ny * H[1] + nz * H[2])
            ndv = max(1e-4, nz)

            # vecteur reflechi (vue = +Z)
            rx, ry, rz = 2 * nz * nx, 2 * nz * ny, 2 * nz * nz - 1.0
            env = _environment(ry)
            rdl = max(0.0, rx * L[0] + ry * L[1] + rz * L[2])

            shininess = 4.0 + 500.0 * (smooth ** 2)
            sun = (rdl ** shininess) * (0.25 + 0.75 * smooth)
            fresnel = f0 + (1.0 - f0) * ((1.0 - ndv) ** 5)

            tint = METAL_COLORS.get(g, (185, 187, 192)) if metal else albedo
            out_px = []
            for c in range(3):
                base = tint[c] / 255.0
                if metal:
                    # un metal n'a pas de diffus : uniquement reflexion + soleil
                    v = base * (env * (0.30 + 0.70 * smooth) + sun * 1.6) * ao
                    v += base * ndl * 0.10
                else:
                    diffuse = (0.18 + 0.82 * ndl) * ao
                    v = base * diffuse * (1.0 - fresnel * 0.5)
                    v += (env * fresnel * smooth * 0.9 + sun * (0.10 + 0.90 * smooth) * fresnel * 6.0) * ao
                v = v * (1.0 - 0.55 * emission) + emission * 0.62
                out_px.append(max(0, min(255, int(round(v * 255)))))
            out.put(px, py, (out_px[0], out_px[1], out_px[2], 255))
    return out


def contact_sheet(pack_dir, names, cols=6, tile=64, gap=4):
    tiles, missing = [], []
    for name in names:
        n_path = os.path.join(pack_dir, "assets/minecraft/textures/block", name + "_n.png")
        s_path = os.path.join(pack_dir, "assets/minecraft/textures/block", name + "_s.png")
        if not (os.path.isfile(n_path) and os.path.isfile(s_path)):
            missing.append(name)
            continue
        tiles.append((name, render_tile(read_png(n_path), read_png(s_path), tile)))
    if not tiles:
        raise SystemExit("aucune texture trouvee dans %s" % pack_dir)
    if missing:
        # sans cet avertissement, une texture absente decale toute la grille et
        # l'on croit regarder un bloc alors qu'on en regarde un autre
        print("  ! absentes du pack, non affichees : %s" % ", ".join(missing))
    rows = (len(tiles) + cols - 1) // cols
    W = cols * tile + (cols + 1) * gap
    H = rows * tile + (rows + 1) * gap
    sheet = Image(W, H, fill=(22, 24, 30, 255))
    for i, (_name, t) in enumerate(tiles):
        ox = gap + (i % cols) * (tile + gap)
        oy = gap + (i // cols) * (tile + gap)
        for y in range(tile):
            for x in range(tile):
                sheet.put(ox + x, oy + y, t.get(x, y))
    return sheet, [n for n, _ in tiles]


DEFAULT_SET = [
    "stone", "cobblestone", "stone_bricks", "bricks", "deepslate_tiles", "gravel",
    "oak_planks", "oak_log", "oak_log_top", "spruce_planks", "dark_oak_planks", "bookshelf",
    "iron_block", "gold_block", "diamond_block", "copper_block", "oxidized_copper", "netherite_block",
    "sand", "sandstone", "dirt", "grass_block_top", "clay", "snow",
    "glass", "ice", "white_wool", "white_concrete", "white_glazed_terracotta", "terracotta",
    "glowstone", "redstone_lamp_on", "shroomlight", "ochre_froglight_side", "crying_obsidian", "copper_bulb_lit",
    "iron_ore", "deepslate_diamond_ore", "amethyst_block", "quartz_block_side", "prismarine_bricks", "copper_grate",
    "netherrack", "nether_bricks", "soul_sand", "end_stone", "purpur_block", "obsidian",
    "white_candle_lit", "vault_front_on", "copper_door_top", "bone_block_side", "rail", "sculk_catalyst_top",
]

if __name__ == "__main__":
    pack = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "pack")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "build", "preview.png")
    sheet, used = contact_sheet(pack, DEFAULT_SET)
    write_png(out, sheet)
    print("Apercu ecrit : %s (%d textures, %dx%d)" % (out, len(used), sheet.w, sheet.h))
