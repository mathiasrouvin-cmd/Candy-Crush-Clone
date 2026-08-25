#!/usr/bin/env python3
"""
collect_assets.py - Rassemble les textures de reference d'une instance
Minecraft (jar du client + jars de mods) dans un seul arbre assets/, pret a
etre passe a `build.py --vanilla`.

    python3 tools/collect_assets.py "<dossier de l'instance>" -o /tmp/mcassets
    python3 tools/build.py --vanilla /tmp/mcassets --all-namespaces --zip

Seules les textures de blocs et d'objets sont extraites, et uniquement pour
servir de source de calcul : elles ne finissent jamais dans le pack produit.
"""

import argparse
import os
import sys
import zipfile

WANTED_DIRS = ("textures/block/", "textures/blocks/", "textures/item/", "textures/items/")


def is_wanted(name):
    if not (name.endswith(".png") or name.endswith(".png.mcmeta")):
        return False
    if not name.startswith("assets/"):
        return False
    parts = name.split("/", 2)
    if len(parts) < 3:
        return False
    return any(parts[2].startswith(d) for d in WANTED_DIRS)


def safe_join(root, name):
    """Refuse toute entree d'archive qui sortirait du dossier de destination
    (chemin absolu, remontee en ..), y compris via un lien symbolique."""
    dest = os.path.realpath(os.path.join(root, name))
    root = os.path.realpath(root)
    if dest != root and not dest.startswith(root + os.sep):
        return None
    return dest


def find_jars(paths, include_client):
    jars = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(".jar"):
            jars.append(p)
            continue
        if not os.path.isdir(p):
            print("  ! introuvable, ignore : %s" % p, file=sys.stderr)
            continue
        mods = os.path.join(p, "mods")
        for d in ([mods] if os.path.isdir(mods) else [p]):
            for f in sorted(os.listdir(d)):
                if f.endswith(".jar"):
                    jars.append(os.path.join(d, f))
        if include_client:
            # le jar du client n'est pas toujours dans l'instance : on le
            # cherche largement, sans jamais supposer un chemin de launcher
            for dirpath, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in ("mods", "resourcepacks", "shaderpacks")]
                for f in files:
                    if f.endswith(".jar") and ("1.21" in f or f == "client.jar"):
                        full = os.path.join(dirpath, f)
                        if full not in jars:
                            jars.append(full)
    return jars


def extract(jars, out_dir, verbose=False):
    os.makedirs(out_dir, exist_ok=True)
    written, skipped, namespaces = 0, 0, set()
    for jar in jars:
        try:
            zf = zipfile.ZipFile(jar)
        except Exception as exc:
            print("  ! archive illisible, ignoree : %s (%s)" % (os.path.basename(jar), exc),
                  file=sys.stderr)
            continue
        with zf:
            count = 0
            for info in zf.infolist():
                if info.is_dir() or not is_wanted(info.filename):
                    continue
                dest = safe_join(out_dir, info.filename)
                if dest is None:
                    skipped += 1
                    continue
                if os.path.exists(dest):       # premier jar rencontre : priorite
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with zf.open(info) as src, open(dest, "wb") as fh:
                    fh.write(src.read())
                namespaces.add(info.filename.split("/")[1])
                count += 1
            written += count
            if verbose and count:
                print("  %-60s %5d textures" % (os.path.basename(jar)[:60], count))
    return written, skipped, namespaces


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("paths", nargs="+",
                   help="dossier de l'instance, dossier mods/, ou jars a lire")
    p.add_argument("-o", "--out", default="mcassets", help="dossier de sortie")
    p.add_argument("--no-client", action="store_true",
                   help="ne pas chercher le jar du client (mods uniquement)")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    jars = find_jars(args.paths, include_client=not args.no_client)
    if not jars:
        print("Aucun .jar trouve.", file=sys.stderr)
        return 1
    print("%d archive(s) a lire..." % len(jars))
    written, skipped, namespaces = extract(jars, args.out, args.verbose)
    print("\n  textures extraites : %d" % written)
    if skipped:
        print("  entrees refusees   : %d (chemin hors du dossier de sortie)" % skipped)
    print("  namespaces         : %d" % len(namespaces))
    print("  dossier            : %s" % os.path.abspath(args.out))
    print("\nEnsuite :\n  python3 tools/build.py --vanilla %s --all-namespaces --zip"
          % os.path.abspath(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
