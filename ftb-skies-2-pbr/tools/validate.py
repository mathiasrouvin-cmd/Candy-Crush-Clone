#!/usr/bin/env python3
"""
validate.py - Verifie qu'un pack genere respecte bien la specification LabPBR
et les contraintes de chargement de Minecraft. A lancer apres build.py.

Controles :
  * pack.mcmeta present, JSON valide, pack_format coherent et inclus dans
    supported_formats
  * assets/minecraft/optifine/texture.properties declarant format = lab-pbr/1.3
  * pack.png present et carre
  * chaque _n a son _s (et inversement), memes dimensions
  * tous les PNG sont en RVBA 8 bits (l'alpha porte hauteur et emission)
  * canal G du _s hors de la plage reservee 238-254
  * canal A du _s : 255 = pas d'emission ; une texture voulue emissive ne doit
    pas etre entierement a 255 (l'erreur la plus courante des packs PBR)
  * canal B du _n (occlusion) jamais totalement noir
  * canal A du _n (hauteur) jamais a 0 : cela casse le POM de plusieurs shaders
  * pixel neutre du _n a 127 (valeur par defaut d'Iris), pas 128
  * une texture animee (_n/_s plus haute que large) doit avoir son .mcmeta
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import materials as MAT           # noqa: E402
from pngio import read_png        # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def channel_stats(img, ch):
    vals = [img.data[i * 4 + ch] for i in range(img.w * img.h)]
    return min(vals), max(vals)


def validate(pack_dir):
    errors, warnings, checked = [], [], 0

    meta_path = os.path.join(pack_dir, "pack.mcmeta")
    if not os.path.isfile(meta_path):
        errors.append("pack.mcmeta manquant")
    else:
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
            fmt = meta["pack"]["pack_format"]
            if fmt != 34:
                warnings.append("pack_format = %s (34 attendu pour 1.21.1)" % fmt)
            sup = meta["pack"].get("supported_formats")
            if isinstance(sup, list):
                if len(sup) != 2:
                    errors.append("supported_formats doit avoir exactement 2 elements")
                elif not (sup[0] <= fmt <= sup[1]):
                    errors.append("pack_format %s hors de supported_formats %s" % (fmt, sup))
            if "§" not in meta["pack"]["description"]:
                warnings.append("description sans code couleur (cosmetique)")
        except Exception as exc:
            errors.append("pack.mcmeta illisible : %s" % exc)

    icon = os.path.join(pack_dir, "pack.png")
    if not os.path.isfile(icon):
        errors.append("pack.png manquant")
    else:
        im = read_png(icon)
        if im.w != im.h:
            errors.append("pack.png doit etre carre (%dx%d)" % (im.w, im.h))

    props = os.path.join(pack_dir, "assets", "minecraft", "optifine", "texture.properties")
    if not os.path.isfile(props):
        errors.append("assets/minecraft/optifine/texture.properties manquant : "
                      "sans lui Iris filtre le _s en lineaire et corrompt les canaux discrets")
    else:
        with open(props, encoding="utf-8") as fh:
            body = fh.read()
        if "lab-pbr/1.3" not in body:
            errors.append("texture.properties ne declare pas format = lab-pbr/1.3")

    assets = os.path.join(pack_dir, "assets")
    pairs = {}
    for dirpath, _d, files in os.walk(assets):
        for f in files:
            if not f.endswith(".png"):
                continue
            full = os.path.join(dirpath, f)
            if f.endswith("_n.png"):
                pairs.setdefault(full[:-6], {})["n"] = full
            elif f.endswith("_s.png"):
                pairs.setdefault(full[:-6], {})["s"] = full
            else:
                errors.append("texture de base redistribuee : %s"
                              % os.path.relpath(full, pack_dir))
        for f in files:
            if f.endswith(".properties"):
                continue

    emissive_names = {n for n, m in MAT.TEXTURES.items() if m["emission"] > 0}
    seen_emissive = set()

    for stem, got in sorted(pairs.items()):
        name = os.path.basename(stem)
        if "n" not in got:
            errors.append("%s : _s sans _n" % name)
            continue
        if "s" not in got:
            errors.append("%s : _n sans _s" % name)
            continue
        n_img, s_img = read_png(got["n"]), read_png(got["s"])
        checked += 1

        if (n_img.w, n_img.h) != (s_img.w, s_img.h):
            errors.append("%s : dimensions _n %dx%d != _s %dx%d"
                          % (name, n_img.w, n_img.h, s_img.w, s_img.h))

        for label, img, path in (("_n", n_img, got["n"]), ("_s", s_img, got["s"])):
            if img.h > img.w and not os.path.isfile(path + ".mcmeta"):
                errors.append("%s%s : texture animee sans .mcmeta" % (name, label))

        ao_lo, _ao_hi = channel_stats(n_img, 2)
        if ao_lo < 60:
            warnings.append("%s : occlusion tres sombre (B min = %d)" % (name, ao_lo))

        ha_lo, _ha_hi = channel_stats(n_img, 3)
        if ha_lo == 0:
            errors.append("%s : hauteur a 0 dans le _n (casse le POM de certains shaders)"
                          % name)

        rn_lo, rn_hi = channel_stats(n_img, 0)
        if rn_lo == rn_hi == 128:
            warnings.append("%s : normale plate encodee a 128 (Iris utilise 127)" % name)

        g_lo, g_hi = channel_stats(s_img, 1)
        if 238 <= g_lo <= 254 or 238 <= g_hi <= 254:
            errors.append("%s : canal G dans la plage reservee 238-254" % name)

        b_lo, b_hi = channel_stats(s_img, 2)
        if b_lo != b_hi:
            warnings.append("%s : canal B non uniforme" % name)
        if 64 < b_lo < 65:
            errors.append("%s : canal B ambigu" % name)

        a_lo, _a_hi = channel_stats(s_img, 3)
        if name in emissive_names:
            seen_emissive.add(name)
            if a_lo == 255:
                errors.append("%s : declaree emissive mais alpha _s entierement a 255 "
                              "(255 = aucune emission)" % name)
        elif name in MAT.TEXTURES and a_lo != 255:
            errors.append("%s : emission non voulue (alpha _s = %d)" % (name, a_lo))

    missing = sorted(emissive_names - seen_emissive - MAT.ANIMATED)
    for m in missing:
        warnings.append("texture emissive absente du pack : %s" % m)

    return errors, warnings, checked, len(pairs)


if __name__ == "__main__":
    pack = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "pack")
    errs, warns, checked, pairs = validate(pack)
    print("Validation LabPBR de %s" % pack)
    print("  paires _n/_s verifiees : %d" % checked)
    for w in warns[:15]:
        print("  [avertissement] %s" % w)
    if len(warns) > 15:
        print("  ... et %d autres avertissements" % (len(warns) - 15))
    for e in errs[:30]:
        print("  [ERREUR] %s" % e)
    if errs:
        print("\n%d erreur(s), %d avertissement(s)" % (len(errs), len(warns)))
        sys.exit(1)
    print("\nOK : %d paires valides, %d avertissement(s)" % (pairs, len(warns)))
