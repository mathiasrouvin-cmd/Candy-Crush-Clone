#!/usr/bin/env python3
"""
build.py - Genere le pack de textures PBR "Skies PBR" pour shaders LabPBR.

Deux modes :

  1. Procedural (par defaut, aucune dependance, aucun fichier du jeu requis)
     Les cartes de relief sont dessinees a partir de motifs parametres par
     famille de materiau.

  2. Reference (--vanilla <chemin>) : on lit les textures d'origine (dossier
     assets/ extrait d'un .jar, ou un autre pack de textures) pour deriver le
     relief de la vraie image, respecter la transparence, recuperer la taille
     reelle (packs HD) et les animations. Aucune texture d'origine n'est
     copiee dans le pack produit : seules les cartes _n / _s sont ecrites.

Usage :
    python3 tools/build.py
    python3 tools/build.py --vanilla ~/.minecraft/versions/1.21.1/extrait/assets
    python3 tools/build.py --vanilla ./assets --all-namespaces --zip
"""

import argparse
import math
import os
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import materials as MAT          # noqa: E402
import patterns as PAT           # noqa: E402
from pngio import Image, read_png, write_png   # noqa: E402

PACK_NAME = "Skies PBR"
PACK_VERSION = "1.0.0"
PACK_FORMAT = 34                 # Minecraft 1.21 - 1.21.1
SUPPORTED_FORMATS = [34, 46]     # 1.21 -> 1.21.4 ; pack_format doit etre dans la plage
LABPBR_FORMAT = "lab-pbr/1.3"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Encodage LabPBR
# ---------------------------------------------------------------------------


# Pixel neutre du _n : c'est exactement la texture par defaut d'Iris
# (PBRType.NORMAL = 0x7F7FFFFF), soit 127 et non 128 - le vrai milieu est 127,5.
NEUTRAL_N = (127, 127, 255, 255)


def encode_normal(height, w, h, m, use_pom=True, use_ao=True):
    """Carte de hauteur -> texture _n LabPBR (RG = normale, B = AO, A = hauteur).

    Attention a deux details de la specification :
      * LabPBR 1.3 suit la convention DirectX / Y- : le canal vert pointe vers
        le BAS. La plupart des generateurs de normal maps sortent de l'OpenGL
        / Y+ ; il faut donc inverser Y, sinon l'eclairage parait subtilement
        inverse sans que rien n'ait l'air casse.
      * une hauteur de 0 casse le POM de plusieurs shaders : le minimum
        recommande est 1.
    """
    normals = PAT.height_to_normal(height, w, h, m["relief"])
    ao = PAT.height_to_ao(height, w, h, 0.55 if use_ao else 0.0)
    img = Image(w, h)
    depth = m["pom"] if use_pom else 0.0
    for i in range(w * h):
        nx, ny, _nz = normals[i]
        r = int((nx * 0.5 + 0.5) * 255)           # tronque : a plat -> 127
        g = int((-ny * 0.5 + 0.5) * 255)          # Y- : convention DirectX
        b = int(round(ao[i] * 255))
        a = max(1, int(round(255 - (1.0 - height[i]) * depth * 255)))
        img.put(i % w, i // w, (max(0, min(255, r)), max(0, min(255, g)),
                                max(0, min(255, b)), max(0, min(255, a))))
    return img


def specular_b(m):
    """Canal B : 0-64 = porosite, 65-255 = diffusion sous-surface."""
    if m["sss"] > 0:
        return max(65, min(255, 65 + int(round(m["sss"] / 255.0 * 190))))
    return max(0, min(64, m["porosity"]))


def encode_specular(w, h, m, name="", emissive_mask=None):
    """Texture _s LabPBR (R = smoothness, G = F0, B = porosite/SSS, A = emission).

    Rappel : alpha 255 signifie AUCUNE emission ; une emission maximale vaut 254.
    """
    r = m["smooth"]
    g = m["f0"]
    b = specular_b(m)
    base_e = m["emission"]

    if base_e <= 0:
        alpha_flat = 255
        mask = None
    else:
        alpha_flat = min(254, int(round(base_e * 255)))
        mask = emissive_mask
        if mask is None and m.get("emissive_layers"):
            mask = PAT.compose(m["emissive_layers"], w, h, name + "_e")

    img = Image(w, h)
    for i in range(w * h):
        if base_e <= 0:
            a = 255
        elif mask is None:
            a = alpha_flat
        else:
            e = base_e * max(0.0, min(1.0, mask[i]))
            a = 255 if e <= 0.02 else min(254, int(round(e * 255)))
        img.put(i % w, i // w, (r, g, b, a))
    return img


# ---------------------------------------------------------------------------
# Derivation depuis une texture de reference
# ---------------------------------------------------------------------------


def luminance(px):
    return (0.2126 * px[0] + 0.7152 * px[1] + 0.0722 * px[2]) / 255.0


def height_from_image(img, blend=0.65, name="", layers=None):
    """Relief derive de la luminance de la texture d'origine, melange au motif
    procedural. La luminance seule donne un relief trop bruite sur les textures
    tres colorees ; le motif ramene la structure macroscopique du materiau."""
    w, h = img.w, img.h
    lum = [luminance(img.get(i % w, i // w)) for i in range(w * h)]
    lo, hi = min(lum), max(lum)
    if hi - lo > 1e-6:
        lum = [(v - lo) / (hi - lo) for v in lum]
    else:
        lum = [1.0] * (w * h)
    if not layers:
        return lum
    proc = PAT.compose(layers, w, h, name)
    return [lum[i] * blend + proc[i] * (1.0 - blend) for i in range(w * h)]


def emissive_mask_from_image(img, threshold=0.55):
    """Masque d'emission : seuls les pixels les plus lumineux et satures
    emettent (les yeux d'un four allume, les veines de l'obsidienne pleureuse)."""
    w, h = img.w, img.h
    out = []
    for i in range(w * h):
        px = img.get(i % w, i // w)
        if px[3] < 8:
            out.append(0.0)
            continue
        mx, mn = max(px[:3]), min(px[:3])
        sat = 0.0 if mx == 0 else (mx - mn) / float(mx)
        l = luminance(px)
        v = max(0.0, (l - threshold) / max(1e-6, 1.0 - threshold))
        out.append(max(0.0, min(1.0, v * 0.7 + sat * l * 0.6)))
    if max(out, default=0.0) < 0.05:
        return None   # rien d'assez lumineux : on garde une emission uniforme
    return out


def apply_alpha_cutout(n_img, s_img, base):
    """Sur les textures ajourees (feuilles, barreaux, vitres), les pixels
    transparents recoivent une normale neutre et aucune emission : cela evite
    des artefacts de POM sur les bords decoupes."""
    for i in range(base.w * base.h):
        x, y = i % base.w, i // base.w
        if base.get(x, y)[3] < 8:
            n_img.put(x, y, NEUTRAL_N)
            s = s_img.get(x, y)
            s_img.put(x, y, (s[0], s[1], s[2], 255))


# ---------------------------------------------------------------------------
# Deduction de materiau pour les blocs modes
# ---------------------------------------------------------------------------

GUESS_RULES = [
    # (mots-cles, preset, surcharges)
    (("lamp_on", "_lit", "lit_", "glowstone", "luminous", "light_block"), MAT.LAMP, dict(emission=0.95)),
    (("lantern", "torch_on", "candle_lit"), MAT.LAMP, dict(emission=1.0)),
    (("glow", "shine", "beacon", "laser", "energy", "plasma", "reactor_core"), MAT.LAMP, dict(emission=0.8)),
    (("leaves", "sapling", "vine", "moss", "foliage", "bush", "flower", "grass_"), MAT.FOLIAGE, {}),
    (("planks", "plank"), MAT.PLANK, {}),
    (("stripped",), MAT.STRIPPED_LOG, {}),
    (("_log_top", "_stem_top", "log_top"), MAT.LOG_TOP, {}),
    (("_log", "_stem", "_wood", "timber"), MAT.LOG_SIDE, {}),
    (("_ore", "ore_"), MAT.ORE, {}),
    (("raw_", "_ingot_block", "_nugget"), MAT.METAL_SMOOTH, dict(smooth=110)),
    (("brick",), MAT.CLAY_BRICK, {}),
    (("tile", "tiles"), MAT.TILE, {}),
    (("cobble", "rubble"), MAT.COBBLE, {}),
    (("polished", "smooth_", "cut_"), MAT.POLISHED_STONE, {}),
    (("glass", "window", "pane"), MAT.GLASS, {}),
    (("wool", "cloth", "carpet", "fabric", "canvas"), MAT.WOOL, {}),
    (("concrete_powder",), MAT.CONCRETE_POWDER, {}),
    (("concrete",), MAT.CONCRETE, {}),
    (("glazed",), MAT.GLAZED, {}),
    (("terracotta",), MAT.TERRACOTTA, {}),
    (("sand", "sandstone", "dust", "powder"), MAT.SAND, {}),
    (("dirt", "soil", "mud", "clay", "loam", "peat"), MAT.SOIL, {}),
    (("gravel", "crushed", "aggregate"), MAT.GRAVELLY, {}),
    (("obsidian",), MAT.OBSIDIAN, {}),
    (("quartz",), MAT.QUARTZ, {}),
    (("ice", "frost", "crystal", "diamond", "emerald", "amethyst", "gem", "ruby",
      "sapphire", "topaz", "peridot"), MAT.GEM_BLOCK, {}),
    (("netherrack", "nether_", "basalt", "blackstone", "soul_"), MAT.NETHER_ROCK, {}),
    (("machine", "casing", "chassis", "frame", "gearbox", "boiler", "tank",
      "pipe", "duct", "conduit", "cable", "wire", "steel", "iron", "copper",
      "brass", "bronze", "aluminum", "aluminium", "tin", "lead", "nickel",
      "silver", "gold", "platinum", "titanium", "tungsten", "invar",
      "electrum", "signalum", "enderium", "osmium", "uranium", "metal",
      "alloy", "plating", "girder", "andesite_casing", "brass_casing"),
     MAT.METAL_SMOOTH, dict(smooth=150)),
    (("stone", "rock", "granite", "andesite", "diorite", "deepslate", "tuff",
      "limestone", "marble", "slate", "asphalt"), MAT.ROUGH_STONE, {}),
]

DEFAULT_GUESS = MAT.ROUGH_STONE


def _matches(low, tokens, kw):
    """Un mot-cle contenant un souligne est cherche tel quel dans le nom
    (utile pour les suffixes : "_log_top", "concrete_powder"). Sinon il doit
    correspondre a un mot entier du nom, ou en etre le debut s'il fait au
    moins 4 lettres.

    Ce detour evite les faux positifs de la recherche par sous-chaine :
    "industrial" contient "dust", "tinted" contient "tin", "plating"
    contient "lat" - autant de blocs de mods qui se retrouveraient dans la
    mauvaise famille de materiau.
    """
    if "_" in kw:
        return kw in low
    if len(kw) >= 4:
        return any(t == kw or t.startswith(kw) for t in tokens)
    return kw in tokens


def guess_material(name):
    """Devine un materiau pour une texture inconnue (blocs de mods) d'apres
    les mots-cles de son nom de fichier."""
    low = name.lower()
    tokens = [t for t in low.replace("-", "_").split("_") if t]
    for keys, preset, over in GUESS_RULES:
        for k in keys:
            if _matches(low, tokens, k):
                return MAT.derive(preset, **over) if over else dict(preset)
    return dict(DEFAULT_GUESS)


# ---------------------------------------------------------------------------
# Ressources du pack
# ---------------------------------------------------------------------------


def pack_mcmeta():
    desc = ("\\u00a7bSkies PBR \\u00a77" + PACK_VERSION + "\\n"
            "\\u00a7fCartes LabPBR pour shaders \\u00a78- FTB Skies 2 (1.21.1)")
    return (
        '{\n'
        '  "pack": {\n'
        '    "pack_format": %d,\n'
        '    "supported_formats": [%d, %d],\n'
        '    "description": "%s"\n'
        '  }\n'
        '}\n' % (PACK_FORMAT, SUPPORTED_FORMATS[0], SUPPORTED_FORMATS[1], desc)
    )


def make_pack_icon(size=128):
    """Icone du pack : ciel nocturne + cube en relief avec un reflet net,
    dessinee proceduralement (aucun asset externe)."""
    img = Image(size, size)
    cx, cy = size * 0.5, size * 0.52
    s = size * 0.30

    def top_face(px, py):
        dx, dy = (px - cx) / s, (py - (cy - s * 0.55)) / (s * 0.55)
        return abs(dx) + abs(dy) <= 1.0

    def left_face(px, py):
        dx, dy = (px - cx) / s, (py - cy) / s
        return -1.0 <= dx <= 0.0 and (dy >= -0.55 - dx * 0.55) and (dy <= 1.0 + dx * 0.55)

    def right_face(px, py):
        dx, dy = (px - cx) / s, (py - cy) / s
        return 0.0 <= dx <= 1.0 and (dy >= -0.55 + dx * 0.55) and (dy <= 1.0 - dx * 0.55)

    for y in range(size):
        for x in range(size):
            t = y / float(size - 1)
            bg = (int(9 + 16 * (1 - t)), int(14 + 26 * (1 - t)), int(32 + 44 * (1 - t)), 255)
            px = bg
            u = (x - cx) / s
            v = (y - cy) / s
            if top_face(x, y):
                k = 0.55 + 0.45 * max(0.0, 1.0 - abs(u))
                spec = math.exp(-((u + 0.35) ** 2 + (v + 0.75) ** 2) * 7.0)
                px = (int(min(255, 90 + 150 * k + 120 * spec)),
                      int(min(255, 190 + 55 * k + 60 * spec)),
                      int(min(255, 220 + 35 * k + 35 * spec)), 255)
            elif left_face(x, y):
                k = 0.30 + 0.25 * (1.0 + u)
                px = (int(28 + 70 * k), int(70 + 110 * k), int(110 + 120 * k), 255)
            elif right_face(x, y):
                k = 0.45 + 0.35 * (1.0 - u)
                spec = math.exp(-((u - 0.55) ** 2 + (v - 0.10) ** 2) * 9.0)
                px = (int(min(255, 40 + 90 * k + 150 * spec)),
                      int(min(255, 95 + 120 * k + 130 * spec)),
                      int(min(255, 140 + 110 * k + 110 * spec)), 255)
            img.put(x, y, px)

    # quelques etoiles deterministes dans le ciel
    import random as _r
    rnd = _r.Random(20250825)
    for _ in range(size // 2):
        sx, sy = rnd.randrange(size), rnd.randrange(int(size * 0.55))
        if not (top_face(sx, sy) or left_face(sx, sy) or right_face(sx, sy)):
            b = rnd.randint(150, 255)
            img.put(sx, sy, (b, b, min(255, b + 20), 255))
    return img


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def collect_reference(vanilla_root, all_namespaces):
    """Repere les textures de reference : {(namespace, sous-chemin): fichier}."""
    found = {}
    if not vanilla_root:
        return found
    assets = vanilla_root
    if os.path.isdir(os.path.join(vanilla_root, "assets")):
        assets = os.path.join(vanilla_root, "assets")
    if not os.path.isdir(assets):
        return found
    namespaces = sorted(os.listdir(assets)) if all_namespaces else ["minecraft"]
    for ns in namespaces:
        tex_root = os.path.join(assets, ns, "textures")
        if not os.path.isdir(tex_root):
            continue
        for sub in ("block", "blocks"):
            d = os.path.join(tex_root, sub)
            if not os.path.isdir(d):
                continue
            for dirpath, _dirs, files in os.walk(d):
                for f in files:
                    if not f.endswith(".png") or f.endswith(("_n.png", "_s.png")):
                        continue
                    full = os.path.join(dirpath, f)
                    rel = os.path.relpath(full, tex_root).replace(os.sep, "/")
                    found[(ns, rel)] = full
    return found


def generate(args):
    out_pack = os.path.join(args.out, "pack")
    if os.path.isdir(out_pack):
        shutil.rmtree(out_pack)
    os.makedirs(out_pack, exist_ok=True)

    with open(os.path.join(out_pack, "pack.mcmeta"), "w", encoding="utf-8") as fh:
        fh.write(pack_mcmeta())
    write_png(os.path.join(out_pack, "pack.png"), make_pack_icon())

    # Declaration du format PBR. Sans ce fichier, Iris interpole lineairement le
    # _s : les identifiants de metaux bavent dans la plage des dielectriques, la
    # frontiere porosite/SSS (64/65) est franchie par interpolation et l'emission
    # 255 "ignoree" se melange aux valeurs emissives. Le pack fonctionne quand
    # meme, mais se degrade avec la distance - un defaut facile a ne pas voir.
    of_dir = os.path.join(out_pack, "assets", "minecraft", "optifine")
    os.makedirs(of_dir, exist_ok=True)
    with open(os.path.join(of_dir, "texture.properties"), "w", encoding="utf-8") as fh:
        fh.write("# Format des cartes PBR fournies par ce pack.\n"
                 "# Active MC_TEXTURE_FORMAT_LAB_PBR / _1_3 cote shader et le\n"
                 "# filtrage adapte des canaux discrets du _s.\n"
                 "format = %s\n" % LABPBR_FORMAT)

    reference = collect_reference(args.vanilla, args.all_namespaces)
    stats = {"generated": 0, "from_reference": 0, "procedural": 0,
             "guessed": 0, "skipped_animated": 0, "animated_handled": 0,
             "namespaces": set(), "emissive": 0}

    # 1) Ce qui est explicitement catalogue (vanilla 1.21.1)
    work = []
    for name, m in sorted(MAT.TEXTURES.items()):
        ref = reference.get(("minecraft", "block/%s.png" % name))
        work.append(("minecraft", "block/%s.png" % name, name, m, ref, False))

    # 2) Les textures de reference non catalogues (blocs de mods, oublis vanilla)
    if reference:
        known = {("minecraft", "block/%s.png" % n) for n in MAT.TEXTURES}
        for key, path in sorted(reference.items()):
            if key in known:
                continue
            ns, rel = key
            base = os.path.basename(rel)[:-4]
            work.append((ns, rel, base, guess_material(base), path, True))

    for ns, rel, name, m, ref, is_guess in work:
        base_img = None
        frames_meta = None
        if ref:
            try:
                base_img = read_png(ref)
            except Exception as exc:                       # texture illisible
                if args.verbose:
                    print("  ! illisible %s (%s)" % (rel, exc))
                base_img = None
            meta_path = ref + ".mcmeta"
            if base_img is not None and os.path.isfile(meta_path):
                with open(meta_path, "r", encoding="utf-8", errors="replace") as fh:
                    frames_meta = fh.read()

        if base_img is None:
            if name in MAT.ANIMATED:
                stats["skipped_animated"] += 1
                continue
            w = h = 16 * args.resolution
            height = PAT.compose(m["layers"], w, h, name)
            emask = None
            stats["procedural"] += 1
        else:
            w, h = base_img.w, base_img.h
            if w == 0 or h == 0 or w > 1024 or h > 4096:
                continue
            if h > w:                                       # texture animee
                stats["animated_handled"] += 1
            height = height_from_image(base_img, args.blend, name, m["layers"])
            emask = emissive_mask_from_image(base_img) if m["emission"] > 0 else None
            stats["from_reference"] += 1

        n_img = encode_normal(height, w, h, m, use_pom=not args.no_pom, use_ao=not args.no_ao)
        s_img = encode_specular(w, h, m, name, emask)
        if base_img is not None:
            apply_alpha_cutout(n_img, s_img, base_img)

        dest_dir = os.path.join(out_pack, "assets", ns, "textures", os.path.dirname(rel))
        os.makedirs(dest_dir, exist_ok=True)
        stem = os.path.join(dest_dir, os.path.basename(rel)[:-4])
        write_png(stem + "_n.png", n_img)
        write_png(stem + "_s.png", s_img)
        if frames_meta:
            # une texture animee exige un .mcmeta identique sur ses cartes
            for suffix in ("_n.png.mcmeta", "_s.png.mcmeta"):
                with open(stem + suffix, "w", encoding="utf-8") as fh:
                    fh.write(frames_meta)
        stats["generated"] += 2
        stats["namespaces"].add(ns)
        if is_guess:
            stats["guessed"] += 1
        if m["emission"] > 0:
            stats["emissive"] += 1
        if args.verbose:
            print("  %s:%s" % (ns, rel))

    return out_pack, stats


def make_zip(pack_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    zip_path = os.path.join(out_dir, "%s-%s.zip" % (PACK_NAME.replace(" ", ""), PACK_VERSION))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dirpath, _dirs, files in os.walk(pack_dir):
            for f in sorted(files):
                full = os.path.join(dirpath, f)
                z.write(full, os.path.relpath(full, pack_dir).replace(os.sep, "/"))
    return zip_path


def main():
    p = argparse.ArgumentParser(description="Genere le pack de textures PBR Skies PBR.")
    p.add_argument("--vanilla", default=None,
                   help="dossier assets/ (ou parent) contenant les textures de reference")
    p.add_argument("--all-namespaces", action="store_true",
                   help="traiter tous les namespaces trouves, pas seulement minecraft (blocs de mods)")
    p.add_argument("--resolution", type=int, default=1,
                   help="multiplicateur de resolution en mode procedural (1 = 16x16). "
                        "A laisser a 1 sauf si vos textures de base sont en HD : Iris "
                        "redimensionne en bilineaire toute carte qui n'est pas un "
                        "multiple entier de la texture de base, ce qui corrompt le _s.")
    p.add_argument("--blend", type=float, default=0.65,
                   help="part du relief derivee de la texture d'origine (0-1)")
    p.add_argument("--no-pom", action="store_true", help="desactiver la carte de hauteur (parallax)")
    p.add_argument("--no-ao", action="store_true", help="desactiver l'occlusion ambiante")
    p.add_argument("--out", default=os.path.join(ROOT, "build"), help="dossier de sortie")
    p.add_argument("--zip", action="store_true", help="produire aussi l'archive .zip installable")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    if args.vanilla:
        print("Mode reference : %s" % args.vanilla)
    else:
        print("Mode procedural (aucune texture d'origine requise)")

    pack_dir, stats = generate(args)
    print("\n--- %s %s ---" % (PACK_NAME, PACK_VERSION))
    print("  fichiers PNG ecrits      : %d" % stats["generated"])
    print("  textures procédurales    : %d" % stats["procedural"])
    print("  textures dérivées        : %d" % stats["from_reference"])
    print("  matériaux devinés (mods) : %d" % stats["guessed"])
    print("  animées prises en charge  : %d" % stats["animated_handled"])
    print("  animées ignorées         : %d" % stats["skipped_animated"])
    print("  textures émissives       : %d" % stats["emissive"])
    print("  namespaces               : %s" % ", ".join(sorted(stats["namespaces"])))
    print("  pack                     : %s" % pack_dir)
    if args.zip:
        print("  archive                  : %s" % make_zip(pack_dir, os.path.join(args.out, "dist")))


if __name__ == "__main__":
    main()
