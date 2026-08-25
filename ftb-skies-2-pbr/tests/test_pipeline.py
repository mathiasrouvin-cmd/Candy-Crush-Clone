#!/usr/bin/env python3
"""
Tests de la chaine de generation (bibliotheque standard uniquement).

    python3 tests/test_pipeline.py

Couvre le codec PNG maison, les motifs, l'encodage LabPBR, la generation
procedurale et le mode --vanilla (fixtures synthetiques : texture animee,
texture ajouree, texture emissive, blocs de mods, PNG en palette / 16 bits).
"""

import argparse
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build as BUILD          # noqa: E402
import collect_assets as CA    # noqa: E402
import materials as MAT        # noqa: E402
import patterns as PAT         # noqa: E402
import validate as VAL         # noqa: E402
from pngio import Image, read_png, write_png   # noqa: E402


def make_args(**over):
    a = argparse.Namespace(vanilla=None, all_namespaces=False, resolution=1,
                           blend=0.65, no_pom=False, no_ao=False, items=False,
                           out=None, zip=False, verbose=False)
    for k, v in over.items():
        setattr(a, k, v)
    return a


def write_exotic_png(path, w, h, kind):
    """Ecrit un PNG que notre codec doit savoir relire : palette, gris, 16 bits."""
    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    if kind == "palette":
        depth, ctype, chans, sample = 8, 3, 1, 1
        plte = bytes([0, 0, 0, 255, 0, 0, 0, 255, 0, 40, 60, 200])
        rows = bytearray()
        for y in range(h):
            rows.append(0)
            for x in range(w):
                rows.append((x + y) % 4)
        extra = chunk(b"PLTE", plte)
    elif kind == "gray":
        depth, ctype, chans, sample = 8, 0, 1, 1
        rows = bytearray()
        for y in range(h):
            rows.append(0)
            for x in range(w):
                rows.append((x * 16 + y * 3) % 256)
        extra = b""
    else:  # gris 16 bits
        depth, ctype, chans, sample = 16, 0, 1, 2
        rows = bytearray()
        for y in range(h):
            rows.append(0)
            for x in range(w):
                rows += struct.pack(">H", ((x * 4096 + y * 257) % 65536))
        extra = b""

    blob = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, ctype, 0, 0, 0))
            + extra
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
            + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(blob)


class TestPngCodec(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_roundtrip_rgba(self):
        img = Image(16, 16)
        for y in range(16):
            for x in range(16):
                img.put(x, y, (x * 16, y * 16, (x * y) % 256, 255 - x))
        p = os.path.join(self.tmp, "a.png")
        write_png(p, img)
        back = read_png(p)
        self.assertEqual((back.w, back.h), (16, 16))
        self.assertEqual(bytes(back.data), bytes(img.data))

    def test_exotic_inputs(self):
        for kind in ("palette", "gray", "gray16"):
            p = os.path.join(self.tmp, kind + ".png")
            write_exotic_png(p, 16, 16, kind)
            img = read_png(p)
            self.assertEqual((img.w, img.h), (16, 16), kind)
            self.assertEqual(len(img.data), 16 * 16 * 4, kind)

    def test_scaled_is_nearest_neighbour(self):
        img = Image(2, 2)
        img.put(0, 0, (255, 0, 0, 255))
        img.put(1, 0, (0, 255, 0, 255))
        img.put(0, 1, (0, 0, 255, 255))
        img.put(1, 1, (255, 255, 0, 255))
        big = img.scaled(4)
        self.assertEqual((big.w, big.h), (8, 8))
        self.assertEqual(big.get(3, 3), (255, 0, 0, 255))
        self.assertEqual(big.get(4, 0), (0, 255, 0, 255))


class TestPngEdgeCases(unittest.TestCase):
    """Cas limites du decodeur : ces quatre defauts ont ete trouves en revue."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _png(self, name, w, h, depth, ctype, rows, extra=b"", truncate=0):
        def chunk(tag, body):
            return (struct.pack(">I", len(body)) + tag + body
                    + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))
        payload = bytes(rows)
        if truncate:
            payload = payload[:-truncate]
        blob = (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, ctype, 0, 0, 0))
                + extra + chunk(b"IDAT", zlib.compress(payload, 9))
                + chunk(b"IEND", b""))
        p = os.path.join(self.tmp, name)
        with open(p, "wb") as fh:
            fh.write(blob)
        return p

    def test_trns_key_compared_at_full_depth(self):
        """La cle tRNS est sur 16 bits meme quand on reduit l'image a 8 bits :
        la comparer a l'octet de poids fort inventerait ou perdrait de la
        transparence."""
        rows = bytearray([0]) + bytearray(struct.pack(">H", 0xFFFF))
        img = read_png(self._png("a.png", 1, 1, 16, 0, rows,
                                 extra=self._trns(struct.pack(">H", 0xFFFF))))
        self.assertEqual(img.get(0, 0)[3], 0, "la cle exacte doit rendre transparent")

        rows = bytearray([0]) + bytearray(struct.pack(">H", 0x00FF))
        img = read_png(self._png("b.png", 1, 1, 16, 0, rows,
                                 extra=self._trns(struct.pack(">H", 0x0000))))
        self.assertEqual(img.get(0, 0)[3], 255, "meme octet fort mais valeur differente")

    def test_trns_colour_key_on_truecolour(self):
        rows = bytearray([0]) + bytearray([255, 0, 0, 0, 255, 0])
        img = read_png(self._png("c.png", 2, 1, 8, 2, rows,
                                 extra=self._trns(struct.pack(">HHH", 255, 0, 0))))
        self.assertEqual(img.get(0, 0)[3], 0)
        self.assertEqual(img.get(1, 0)[3], 255)

    def test_invalid_colour_type_raises_valueerror(self):
        with self.assertRaises(ValueError):
            read_png(self._png("d.png", 1, 1, 8, 5, bytearray([0, 0])))

    def test_truncated_idat_raises_valueerror(self):
        rows = bytearray()
        for _y in range(2):
            rows += bytearray([0]) + bytearray([1, 2, 3, 4] * 2)
        with self.assertRaises(ValueError):
            read_png(self._png("e.png", 2, 2, 8, 6, rows, truncate=2))

    def test_validator_reports_corrupt_map_instead_of_crashing(self):
        pack = os.path.join(self.tmp, "pack")
        block = os.path.join(pack, "assets/minecraft/textures/block")
        os.makedirs(block)
        os.makedirs(os.path.join(pack, "assets/minecraft/optifine"))
        with open(os.path.join(pack, "pack.mcmeta"), "w") as fh:
            fh.write('{"pack":{"pack_format":34,"description":"\u00a7bx"}}')
        with open(os.path.join(pack, "assets/minecraft/optifine/texture.properties"), "w") as fh:
            fh.write("format=lab-pbr/1.3\n")
        write_png(os.path.join(pack, "pack.png"), Image(8, 8, fill=(0, 0, 0, 255)))
        with open(os.path.join(block, "stone_n.png"), "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n" + b"pourri" * 4)
        write_png(os.path.join(block, "stone_s.png"), Image(16, 16, fill=(0, 0, 0, 255)))
        errs, _w, _c, _p = VAL.validate(pack)     # ne doit pas lever
        self.assertTrue(any("illisible" in e for e in errs), errs)

    @staticmethod
    def _trns(body):
        return (struct.pack(">I", len(body)) + b"tRNS" + body
                + struct.pack(">I", zlib.crc32(b"tRNS" + body) & 0xFFFFFFFF))


class TestPatterns(unittest.TestCase):
    def test_all_patterns_bounded(self):
        for name, fn in PAT.PATTERNS.items():
            hm = fn(16, 16, name="unit")
            self.assertEqual(len(hm), 256, name)
            self.assertTrue(all(-1e-9 <= v <= 1 + 1e-9 for v in hm), name)

    def test_deterministic(self):
        a = PAT.compose([("fbm", 1.0, {}), ("speckle", 0.4, {})], 16, 16, "stone")
        b = PAT.compose([("fbm", 1.0, {}), ("speckle", 0.4, {})], 16, 16, "stone")
        self.assertEqual(a, b)
        c = PAT.compose([("fbm", 1.0, {}), ("speckle", 0.4, {})], 16, 16, "dirt")
        self.assertNotEqual(a, c)

    def test_flat_height_gives_neutral_normal(self):
        flat = [1.0] * 256
        img = BUILD.encode_normal(flat, 16, 16, MAT.mat(relief=1.0, pom=0.5))
        for i in range(256):
            px = img.get(i % 16, i // 16)
            # 127 et non 128 : c'est la valeur de la texture _n par defaut d'Iris
            self.assertEqual(px[0], 127)
            self.assertEqual(px[1], 127)
            self.assertEqual(px[3], 255)   # surface plate : hauteur maximale

    def test_green_channel_uses_directx_convention(self):
        """LabPBR 1.3 est en Y- : sur une bosse, le versant situe SOUS le sommet
        pointe vers le bas de la texture, donc vert > 127. En OpenGL (Y+) on
        obtiendrait l'inverse et l'eclairage semblerait subtilement retourne."""
        hm = []
        for y in range(16):
            for x in range(16):
                d = ((x - 8) ** 2 + (y - 8) ** 2) ** 0.5
                hm.append(max(0.0, 1.0 - d / 6.0))
        img = BUILD.encode_normal(hm, 16, 16, MAT.mat(relief=1.0, pom=0.5))
        self.assertGreater(img.get(8, 12)[1], 130, "versant bas : vert doit augmenter")
        self.assertLess(img.get(8, 4)[1], 124, "versant haut : vert doit diminuer")
        self.assertGreater(img.get(12, 8)[0], 130, "versant droit : rouge doit augmenter")
        self.assertLess(img.get(4, 8)[0], 124, "versant gauche : rouge doit diminuer")

    def test_height_never_zero(self):
        """Une hauteur de 0 casse le POM de plusieurs shaders : minimum 1."""
        hm = [0.0] * 256
        img = BUILD.encode_normal(hm, 16, 16, MAT.mat(pom=1.0))
        self.assertGreaterEqual(min(img.get(x, y)[3] for y in range(16) for x in range(16)), 1)

    def test_normals_are_unit_length(self):
        hm = PAT.compose([("bricks", 1.0, {})], 16, 16, "b")
        for (nx, ny, nz) in PAT.height_to_normal(hm, 16, 16, 1.2):
            self.assertAlmostEqual((nx * nx + ny * ny + nz * nz) ** 0.5, 1.0, places=6)

    def test_patterns_tile_without_seam(self):
        """Le gradient au bord doit rester du meme ordre qu'a l'interieur :
        sinon une couture apparait entre deux blocs adjacents."""
        hm = PAT.compose([("fbm", 1.0, dict(octaves=3, scale=4))], 16, 16, "tile")
        wrap = max(abs(hm[y * 16 + 15] - hm[y * 16 + 0]) for y in range(16))
        inner = max(abs(hm[y * 16 + 8] - hm[y * 16 + 7]) for y in range(16))
        self.assertLessEqual(wrap, max(0.25, inner * 3.0))


class TestLabPbrEncoding(unittest.TestCase):
    def test_emission_never_255_when_emissive(self):
        for e in (0.05, 0.5, 0.9, 1.0):
            img = BUILD.encode_specular(16, 16, MAT.mat(emission=e), "x")
            alphas = {img.get(x, y)[3] for y in range(16) for x in range(16)}
            self.assertNotIn(255, alphas, "emission %s encodee comme 255 = aucune" % e)
            self.assertTrue(max(alphas) <= 254)

    def test_no_emission_is_exactly_255(self):
        img = BUILD.encode_specular(16, 16, MAT.mat(emission=0.0), "x")
        self.assertEqual({img.get(x, y)[3] for y in range(16) for x in range(16)}, {255})

    def test_porosity_and_sss_ranges(self):
        self.assertLessEqual(BUILD.specular_b(MAT.mat(porosity=64)), 64)
        self.assertEqual(BUILD.specular_b(MAT.mat(porosity=0)), 0)
        for s in (1, 128, 255):
            b = BUILD.specular_b(MAT.mat(sss=s))
            self.assertTrue(65 <= b <= 255, b)

    def test_metal_indices_are_preserved(self):
        for idx in (MAT.METAL_IRON, MAT.METAL_GOLD, MAT.METAL_COPPER, MAT.METAL_GENERIC):
            img = BUILD.encode_specular(8, 8, MAT.mat(f0=idx), "m")
            self.assertEqual(img.get(0, 0)[1], idx)

    def test_catalogue_avoids_reserved_f0_range(self):
        for name, m in MAT.TEXTURES.items():
            self.assertFalse(238 <= m["f0"] <= 254,
                             "%s utilise un F0 reserve (%d)" % (name, m["f0"]))

    def test_pom_disabled_gives_flat_alpha(self):
        hm = PAT.compose([("bricks", 1.0, {})], 16, 16, "b")
        img = BUILD.encode_normal(hm, 16, 16, MAT.mat(pom=0.9), use_pom=False)
        self.assertEqual({img.get(x, y)[3] for y in range(16) for x in range(16)}, {255})


class TestRobustness(unittest.TestCase):
    """Le mode --vanilla suit la taille de la texture d'origine : bandes
    d'animation (jusqu'a 16x512), packs HD, et quelques tailles degenerees."""

    SIZES = [(16, 16), (16, 48), (16, 80), (16, 512), (32, 32), (1, 1), (3, 7)]

    def test_every_pattern_at_every_size(self):
        for (w, h) in self.SIZES:
            for name, fn in PAT.PATTERNS.items():
                with self.subTest(pattern=name, size=(w, h)):
                    hm = fn(w, h, name="t")
                    self.assertEqual(len(hm), w * h)
                    self.assertTrue(all(-1e-9 <= v <= 1 + 1e-9 for v in hm))

    def test_whole_catalogue_encodes_at_every_size(self):
        # Tout le catalogue sur les petites tailles ; un echantillon
        # deterministe sur les grandes, qui coutent cher a encoder.
        catalogue = sorted(MAT.TEXTURES.items())
        for (w, h) in self.SIZES:
            subset = catalogue if w * h <= 16 * 48 else catalogue[::25]
            for tname, m in subset:
                hm = PAT.compose(m["layers"], w, h, tname)
                n = BUILD.encode_normal(hm, w, h, m)
                s = BUILD.encode_specular(w, h, m, tname)
                self.assertEqual((n.w, n.h, s.w, s.h), (w, h, w, h))
                step = max(1, (w * h) // 11)
                for i in range(0, w * h, step):
                    px_n = n.get(i % w, i // w)
                    px_s = s.get(i % w, i // w)
                    self.assertGreaterEqual(px_n[3], 1, "%s : hauteur nulle" % tname)
                    self.assertFalse(238 <= px_s[1] <= 254, "%s : F0 reserve" % tname)
                    if m["emission"] == 0:
                        self.assertEqual(px_s[3], 255, "%s : emission parasite" % tname)
                    elif m.get("emissive_layers") is None:
                        self.assertNotEqual(px_s[3], 255, "%s : emission perdue" % tname)

    def test_animated_names_are_never_emitted_procedurally(self):
        """Une carte de taille non multiple de la base ferait rééchantillonner
        le _s en bilinéaire, ce qui corrompt ses canaux discrets."""
        for name in MAT.ANIMATED:
            self.assertIn(name, MAT.TEXTURES,
                          "%s est ecartee mais absente du catalogue : elle "
                          "n'aurait aucun materiau en mode --vanilla" % name)


class TestGuessMaterial(unittest.TestCase):
    def test_mod_blocks_map_to_sensible_materials(self):
        cases = {
            "brass_casing": lambda m: m["f0"] >= 230,
            "steel_block": lambda m: m["f0"] >= 230,
            "industrial_iron_block": lambda m: m["f0"] >= 230,
            "oak_planks_mod": lambda m: m["smooth"] == MAT.PLANK["smooth"],
            "ruby_ore": lambda m: m["relief"] == MAT.ORE["relief"],
            "arcane_glass": lambda m: m["smooth"] >= 240,
            "glowing_crystal": lambda m: m["emission"] > 0,
            "mystic_leaves": lambda m: m["sss"] > 0,
            "unknown_thing": lambda m: m["smooth"] == MAT.ROUGH_STONE["smooth"],
        }
        for name, check in cases.items():
            self.assertTrue(check(BUILD.guess_material(name)), name)

    def test_substring_false_positives(self):
        """Ces noms piegeaient la recherche par sous-chaine."""
        # "industrial" contient "dust" : ce bloc est en metal, pas en sable
        self.assertGreaterEqual(BUILD.guess_material("industrial_iron_block")["f0"], 230)
        # "tinted" contient "tin" : c'est du verre, pas de l'etain
        self.assertGreaterEqual(BUILD.guess_material("tinted_glass")["smooth"], 240)
        # "creosote" contient "ore" sans etre un minerai
        self.assertNotEqual(BUILD.guess_material("creosote_block")["relief"],
                            MAT.ORE["relief"])
        # un mot entier doit toujours fonctionner
        self.assertGreaterEqual(BUILD.guess_material("deepslate_ruby_ore")["relief"],
                                MAT.ORE["relief"])


class TestCollectAssets(unittest.TestCase):
    """collect_assets.py lit des archives fournies par le joueur : il doit
    filtrer strictement et ne jamais ecrire hors du dossier de sortie."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.inst = os.path.join(self.tmp, "instance")
        os.makedirs(os.path.join(self.inst, "mods"))
        png = os.path.join(self.tmp, "x.png")
        write_png(png, Image(16, 16, fill=(1, 2, 3, 255)))
        with open(png, "rb") as fh:
            self.blob = fh.read()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_only_block_and_item_textures_are_kept(self):
        self.assertTrue(CA.is_wanted("assets/minecraft/textures/block/stone.png"))
        self.assertTrue(CA.is_wanted("assets/create/textures/item/wrench.png"))
        self.assertTrue(CA.is_wanted("assets/minecraft/textures/block/fire_0.png.mcmeta"))
        self.assertFalse(CA.is_wanted("assets/minecraft/textures/gui/widgets.png"))
        self.assertFalse(CA.is_wanted("assets/minecraft/sounds/x.ogg"))
        self.assertFalse(CA.is_wanted("META-INF/MANIFEST.MF"))
        self.assertFalse(CA.is_wanted("assets/minecraft/textures/block/stone.txt"))

    def test_safe_join_blocks_escapes(self):
        root = os.path.join(self.tmp, "out")
        os.makedirs(root, exist_ok=True)
        self.assertIsNone(CA.safe_join(root, "../evil.png"))
        self.assertIsNone(CA.safe_join(root, "a/../../evil.png"))
        self.assertIsNone(CA.safe_join(root, "/etc/evil.png"))
        self.assertIsNotNone(CA.safe_join(root, "assets/minecraft/textures/block/a.png"))

    def test_extraction_ignores_malicious_entries(self):
        jar = os.path.join(self.inst, "mods", "evil.jar")
        with zipfile.ZipFile(jar, "w") as z:
            z.writestr("assets/create/textures/block/brass_casing.png", self.blob)
            z.writestr("../../../evil.png", self.blob)
            z.writestr("assets/../../../etc/evil2.png", self.blob)
        out = os.path.join(self.tmp, "out")
        written, _skipped, namespaces = CA.extract([jar], out)
        self.assertEqual(written, 1)
        self.assertEqual(namespaces, {"create"})
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "evil.png")))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "instance", "evil.png")))

    def test_first_jar_wins_on_duplicate(self):
        a = os.path.join(self.inst, "mods", "a.jar")
        b = os.path.join(self.inst, "mods", "b.jar")
        other = Image(16, 16, fill=(9, 9, 9, 255))
        other_path = os.path.join(self.tmp, "other.png")
        write_png(other_path, other)
        with open(other_path, "rb") as fh:
            other_blob = fh.read()
        with zipfile.ZipFile(a, "w") as z:
            z.writestr("assets/create/textures/block/x.png", self.blob)
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("assets/create/textures/block/x.png", other_blob)
        out = os.path.join(self.tmp, "out")
        CA.extract([a, b], out)
        img = read_png(os.path.join(out, "assets/create/textures/block/x.png"))
        self.assertEqual(img.get(0, 0), (1, 2, 3, 255))

    def test_full_chain_instance_to_valid_pack(self):
        with zipfile.ZipFile(os.path.join(self.inst, "1.21.1.jar"), "w") as z:
            z.writestr("assets/minecraft/textures/block/stone.png", self.blob)
            z.writestr("assets/minecraft/textures/item/diamond.png", self.blob)
        with zipfile.ZipFile(os.path.join(self.inst, "mods", "create.jar"), "w") as z:
            z.writestr("assets/create/textures/block/brass_casing.png", self.blob)
        out = os.path.join(self.tmp, "assets_out")
        jars = CA.find_jars([self.inst], include_client=True)
        self.assertEqual(len(jars), 2)
        CA.extract(jars, out)
        pack, _st = BUILD.generate(make_args(out=os.path.join(self.tmp, "b"),
                                             vanilla=out, all_namespaces=True, items=True))
        errs, _w, checked, _p = VAL.validate(pack)
        self.assertEqual(errs, [])
        self.assertGreater(checked, 600)
        for rel in ("assets/create/textures/block/brass_casing_n.png",
                    "assets/minecraft/textures/item/diamond_s.png"):
            self.assertTrue(os.path.isfile(os.path.join(pack, rel)), rel)


class TestProceduralBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.pack, cls.stats = BUILD.generate(make_args(out=cls.tmp))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_pack_metadata(self):
        with open(os.path.join(self.pack, "pack.mcmeta"), encoding="utf-8") as fh:
            meta = json.load(fh)
        self.assertEqual(meta["pack"]["pack_format"], 34)
        sup = meta["pack"]["supported_formats"]
        self.assertEqual(len(sup), 2)
        self.assertTrue(sup[0] <= 34 <= sup[1])
        self.assertTrue(os.path.isfile(os.path.join(self.pack, "pack.png")))

    def test_labpbr_format_is_declared(self):
        """Sans ce fichier Iris filtre le _s en lineaire : les identifiants de
        metaux, la frontiere porosite/SSS et le sentinel d'emission se melangent."""
        p = os.path.join(self.pack, "assets/minecraft/optifine/texture.properties")
        self.assertTrue(os.path.isfile(p))
        with open(p, encoding="utf-8") as fh:
            self.assertIn("lab-pbr/1.3", fh.read())

    def test_no_base_texture_is_redistributed(self):
        for dirpath, _d, files in os.walk(os.path.join(self.pack, "assets")):
            for f in files:
                if f.endswith(".png"):
                    self.assertTrue(f.endswith(("_n.png", "_s.png")),
                                    "texture d'origine redistribuee : %s" % f)

    def test_animated_textures_are_skipped(self):
        block = os.path.join(self.pack, "assets/minecraft/textures/block")
        for name in MAT.ANIMATED:
            self.assertFalse(os.path.isfile(os.path.join(block, name + "_n.png")),
                             "%s ne doit pas etre genere sans reference" % name)

    def test_validator_passes(self):
        errs, warns, checked, _pairs = VAL.validate(self.pack)
        self.assertEqual(errs, [])
        self.assertEqual(warns, [])
        self.assertGreater(checked, 400)


class TestReferenceBuild(unittest.TestCase):
    """Mode --vanilla : c'est le chemin qui touche aux fichiers du joueur."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        block = os.path.join(cls.tmp, "src", "assets", "minecraft", "textures", "block")
        os.makedirs(block)

        # texture opaque ordinaire
        stone = Image(16, 16)
        for y in range(16):
            for x in range(16):
                v = 100 + ((x * 7 + y * 13) % 40)
                stone.put(x, y, (v, v, v, 255))
        write_png(os.path.join(block, "stone.png"), stone)

        # texture HD (32x32) : les cartes doivent suivre la taille reelle
        hd = Image(32, 32)
        for y in range(32):
            for x in range(32):
                hd.put(x, y, ((x * 8) % 256, (y * 8) % 256, 90, 255))
        write_png(os.path.join(block, "oak_planks.png"), hd)

        # texture animee : 16x80 + .mcmeta
        anim = Image(16, 80)
        for y in range(80):
            for x in range(16):
                anim.put(x, y, (200, 220, 255, 255))
        write_png(os.path.join(block, "sea_lantern.png"), anim)
        with open(os.path.join(block, "sea_lantern.png.mcmeta"), "w") as fh:
            fh.write('{"animation": {"frametime": 5}}')

        # texture ajouree : la moitie droite est transparente
        leaves = Image(16, 16)
        for y in range(16):
            for x in range(16):
                leaves.put(x, y, (60, 120, 50, 0 if x >= 8 else 255))
        write_png(os.path.join(block, "oak_leaves.png"), leaves)

        # texture partiellement lumineuse : seuls quelques pixels doivent emettre
        cry = Image(16, 16)
        for y in range(16):
            for x in range(16):
                bright = (x % 5 == 0 and y % 4 == 0)
                cry.put(x, y, (250, 120, 255, 255) if bright else (20, 18, 30, 255))
        write_png(os.path.join(block, "crying_obsidian.png"), cry)

        # blocs de mods, dans deux namespaces
        for ns, fname in (("create", "brass_casing.png"), ("mekanism", "steel_block.png")):
            d = os.path.join(cls.tmp, "src", "assets", ns, "textures", "block")
            os.makedirs(d, exist_ok=True)
            im = Image(16, 16)
            for y in range(16):
                for x in range(16):
                    im.put(x, y, (150, 130, 90, 255))
            write_png(os.path.join(d, fname), im)

        cls.pack, cls.stats = BUILD.generate(make_args(
            out=os.path.join(cls.tmp, "out"),
            vanilla=os.path.join(cls.tmp, "src"),
            all_namespaces=True))
        cls.block_out = os.path.join(cls.pack, "assets/minecraft/textures/block")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_hd_texture_keeps_source_resolution(self):
        n = read_png(os.path.join(self.block_out, "oak_planks_n.png"))
        s = read_png(os.path.join(self.block_out, "oak_planks_s.png"))
        self.assertEqual((n.w, n.h), (32, 32))
        self.assertEqual((s.w, s.h), (32, 32))

    def test_animated_texture_gets_matching_size_and_mcmeta(self):
        n = read_png(os.path.join(self.block_out, "sea_lantern_n.png"))
        self.assertEqual((n.w, n.h), (16, 80))
        for suffix in ("_n.png.mcmeta", "_s.png.mcmeta"):
            p = os.path.join(self.block_out, "sea_lantern" + suffix)
            self.assertTrue(os.path.isfile(p), p)
            with open(p, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["animation"]["frametime"], 5)

    def test_cutout_pixels_are_neutral(self):
        n = read_png(os.path.join(self.block_out, "oak_leaves_n.png"))
        s = read_png(os.path.join(self.block_out, "oak_leaves_s.png"))
        for y in range(16):
            for x in range(8, 16):          # moitie transparente
                self.assertEqual(n.get(x, y), BUILD.NEUTRAL_N)
                self.assertEqual(s.get(x, y)[3], 255)
        opaque = {n.get(x, y) for y in range(16) for x in range(8)}
        self.assertGreater(len(opaque), 1, "la moitie opaque doit avoir du relief")

    def test_emissive_mask_follows_bright_pixels(self):
        s = read_png(os.path.join(self.block_out, "crying_obsidian_s.png"))
        emitting = sum(1 for y in range(16) for x in range(16) if s.get(x, y)[3] != 255)
        self.assertGreater(emitting, 0, "aucun pixel emissif")
        self.assertLess(emitting, 16 * 16, "toute la texture emet : le masque est inactif")

    def test_mod_namespaces_are_covered(self):
        for ns, name in (("create", "brass_casing"), ("mekanism", "steel_block")):
            base = os.path.join(self.pack, "assets", ns, "textures", "block")
            self.assertTrue(os.path.isfile(os.path.join(base, name + "_n.png")))
            s = read_png(os.path.join(base, name + "_s.png"))
            self.assertGreaterEqual(s.get(0, 0)[1], 230, "%s devrait etre metallique" % name)

    def test_unreadable_reference_is_skipped_not_guessed(self):
        """Une texture de reference illisible ne doit pas produire une carte de
        taille arbitraire : Iris redimensionnerait le _s en bilineaire et
        corromprait les identifiants de metaux et le sentinel d'emission."""
        tmp = tempfile.mkdtemp()
        try:
            block = os.path.join(tmp, "src", "assets", "minecraft", "textures", "block")
            os.makedirs(block)
            with open(os.path.join(block, "cobblestone.png"), "wb") as fh:
                fh.write(b"\x89PNG\r\n\x1a\n" + b"corrompu" * 8)
            pack, stats = BUILD.generate(make_args(out=os.path.join(tmp, "out"),
                                                   vanilla=os.path.join(tmp, "src")))
            self.assertEqual(stats["skipped_unreadable"], 1)
            out = os.path.join(pack, "assets/minecraft/textures/block/cobblestone_n.png")
            self.assertFalse(os.path.isfile(out), "carte generee malgre une source illisible")
            # les autres textures restent generees normalement
            self.assertTrue(os.path.isfile(os.path.join(
                pack, "assets/minecraft/textures/block/stone_n.png")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_items_are_covered_when_requested(self):
        tmp = tempfile.mkdtemp()
        try:
            item = os.path.join(tmp, "src", "assets", "minecraft", "textures", "item")
            os.makedirs(item)
            im = Image(16, 16)
            for y in range(16):
                for x in range(16):
                    im.put(x, y, (200, 200, 210, 255 if 4 <= x < 12 else 0))
            write_png(os.path.join(item, "iron_sword.png"), im)
            pack, _st = BUILD.generate(make_args(out=os.path.join(tmp, "out"),
                                                 vanilla=os.path.join(tmp, "src"),
                                                 items=True))
            s_path = os.path.join(pack, "assets/minecraft/textures/item/iron_sword_s.png")
            self.assertTrue(os.path.isfile(s_path))
            sp = read_png(s_path)
            self.assertGreaterEqual(sp.get(8, 8)[1], 230, "une epee en fer doit etre metallique")
            n = read_png(os.path.join(pack, "assets/minecraft/textures/item/iron_sword_n.png"))
            self.assertEqual(n.get(0, 0), BUILD.NEUTRAL_N, "pixel transparent = normale neutre")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_validator_passes_on_reference_build(self):
        errs, _warns, checked, _pairs = VAL.validate(self.pack)
        self.assertEqual(errs, [])
        self.assertGreater(checked, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
