"""
materials.py - Catalogue des materiaux : proprietes LabPBR + motif de relief
pour chaque texture de bloc de Minecraft 1.21.1.

Rappel du format LabPBR 1.3, tel qu'utilise par Iris / Oculus / OptiFine :

  Texture "_n" (normal)          Texture "_s" (specular)
  ---------------------          -----------------------
  R : normale X                  R : "smoothness" percue (0 = rugueux, 255 = miroir)
  G : normale Y                  G : reflectance F0 ; 0-229 = dielectrique (F0 = G/255),
  B : occlusion ambiante             230-237 = metaux predefinis, 255 = metal generique
  A : hauteur (POM)              B : 0-64 = porosite, 65-255 = diffusion sous-surface
                                 A : emission ; 255 = AUCUNE emission (piege classique)

Valeurs neutres (aucun effet) : _n = (127, 127, 255, 255), _s = (0, 0, 0, 255).
Le canal vert du _n suit la convention DirectX / Y- (le vert pointe vers le bas).
Porosites de reference de la specification : sable 64, laine 38, bois 12, metaux 0.

Indices de metaux predefinis LabPBR :
  230 fer  231 or  232 aluminium  233 chrome  234 cuivre  235 plomb
  236 platine  237 argent  255 metal generique (utilise l'albedo comme F0)
"""

METAL_IRON = 230
METAL_GOLD = 231
METAL_ALUMINIUM = 232
METAL_CHROME = 233
METAL_COPPER = 234
METAL_LEAD = 235
METAL_PLATINUM = 236
METAL_SILVER = 237
METAL_GENERIC = 255

# F0 des dielectriques courants, exprime sur 0-229 (F0 = G / 255)
F0_ROCK = 10        # ~0.039
F0_WOOD = 9         # ~0.035
F0_FABRIC = 6       # ~0.024
F0_GLASS = 12       # ~0.047
F0_GEM = 22         # ~0.086, pierres precieuses taillees
F0_WATER = 5
F0_ORGANIC = 8


def mat(smooth=12, f0=F0_ROCK, porosity=25, sss=0, emission=0.0,
        relief=0.7, pom=0.55, layers=None, emissive_layers=None,
        frames=0, note=""):
    """Fabrique une entree de materiau.

    smooth   : 0-255, "smoothness" percue (canal R du _s)
    f0       : 0-229 pour un dielectrique, ou une constante METAL_* pour un metal
    porosity : 0-64  (canal B) - exclusif avec sss
    sss      : 0-255 en unites utiles, converti en 65..255 (canal B)
    emission : 0.0 a 1.0 (canal A du _s)
    relief   : force de la normale
    pom      : profondeur de la carte de hauteur (canal A du _n)
    layers   : motif de relief, liste de (nom_motif, poids, parametres)
    emissive_layers : motif modulant l'emission (sinon emission uniforme)
    frames   : nombre d'images si la texture de base est animee (0 = statique)
    """
    return {
        "smooth": max(0, min(255, int(smooth))),
        "f0": max(0, min(255, int(f0))),
        "porosity": max(0, min(64, int(porosity))),
        "sss": max(0, min(255, int(sss))),
        "emission": max(0.0, min(1.0, float(emission))),
        "relief": float(relief),
        "pom": max(0.0, min(1.0, float(pom))),
        "layers": layers or [("flat", 1.0, {})],
        "emissive_layers": emissive_layers,
        "frames": int(frames),
        "note": note,
    }


def derive(base, **over):
    """Copie un materiau en surchargeant quelques champs."""
    out = dict(base)
    out.update(over)
    return out


# ---------------------------------------------------------------------------
# Presets par famille de materiau
# ---------------------------------------------------------------------------

ROUGH_STONE = mat(smooth=20, f0=F0_ROCK, porosity=30, relief=0.65, pom=0.35,
                  layers=[("fbm", 1.0, dict(octaves=3, scale=3, gain=0.6)),
                          ("fbm", 0.30, dict(octaves=2, scale=8, gain=0.5)),
                          ("cells", 0.20, dict(size=8, jitter=0.18))])

POLISHED_STONE = mat(smooth=96, f0=F0_ROCK, porosity=8, relief=0.25, pom=0.15,
                     layers=[("fbm", 1.0, dict(octaves=2, scale=3, gain=0.5))])

COBBLE = mat(smooth=16, f0=F0_ROCK, porosity=38, relief=1.15, pom=0.85,
             layers=[("cells", 1.0, dict(size=4, jitter=0.4)),
                     ("fbm", 0.45, dict(octaves=3, scale=6))])

STONE_BRICK = mat(smooth=32, f0=F0_ROCK, porosity=30, relief=0.95, pom=0.8,
                  layers=[("bricks", 1.0, dict(rows=4, cols=2, mortar=1, depth=1.0)),
                          ("fbm", 0.35, dict(octaves=3, scale=8))])

CLAY_BRICK = mat(smooth=40, f0=F0_ROCK, porosity=34, relief=1.0, pom=0.85,
                 layers=[("bricks", 1.0, dict(rows=8, cols=2, mortar=1, depth=1.0)),
                         ("fbm", 0.25, dict(octaves=2, scale=8))])

TILE = mat(smooth=70, f0=F0_ROCK, porosity=16, relief=0.8, pom=0.6,
           layers=[("grid", 1.0, dict(n=4, groove=1, depth=0.85)),
                   ("fbm", 0.2, dict(octaves=2, scale=8))])

SOIL = mat(smooth=8, f0=F0_ORGANIC, porosity=52, relief=0.85, pom=0.45,
           layers=[("fbm", 1.0, dict(octaves=4, scale=3, gain=0.62)),
                   ("cells", 0.35, dict(size=4, jitter=0.3)),
                   ("speckle", 0.22, dict(density=0.45))])

SAND = mat(smooth=14, f0=F0_ROCK, porosity=64, relief=0.55, pom=0.3,
           layers=[("speckle", 1.0, dict(density=0.7)),
                   ("fbm", 0.6, dict(octaves=3, scale=8))])

GRAVELLY = mat(smooth=12, f0=F0_ROCK, porosity=48, relief=1.2, pom=0.9,
               layers=[("cells", 1.0, dict(size=3, jitter=0.45)),
                       ("speckle", 0.5, dict(density=0.55))])

PLANK = mat(smooth=42, f0=F0_WOOD, porosity=12, relief=0.7, pom=0.5,
            layers=[("planks", 1.0, dict(count=4, axis="h", groove=1, depth=0.75)),
                    ("grain", 0.5, dict(axis="v", amp=0.22))])

LOG_SIDE = mat(smooth=30, f0=F0_WOOD, porosity=16, relief=0.85, pom=0.6,
               layers=[("strips", 1.0, dict(axis="v", width=2, depth=0.4)),
                       ("grain", 0.7, dict(axis="v", amp=0.3))])

LOG_TOP = mat(smooth=34, f0=F0_WOOD, porosity=18, relief=0.7, pom=0.45,
              layers=[("rings", 1.0, dict(spacing=2.0, depth=0.35)),
                      ("fbm", 0.3, dict(octaves=3, scale=8))])

STRIPPED_LOG = mat(smooth=48, f0=F0_WOOD, porosity=12, relief=0.55, pom=0.35,
                   layers=[("grain", 1.0, dict(axis="v", amp=0.28)),
                           ("fbm", 0.25, dict(octaves=3, scale=6))])

METAL_SMOOTH = mat(smooth=205, f0=METAL_GENERIC, porosity=0, relief=0.3, pom=0.2,
                   layers=[("frame", 1.0, dict(border=1, depth=0.35, inner=0.9)),
                           ("fbm", 0.2, dict(octaves=2, scale=4))])

GEM_BLOCK = mat(smooth=190, f0=F0_GEM, porosity=0, relief=0.75, pom=0.5,
                layers=[("crystal", 1.0, dict(facets=5)),
                        ("grid", 0.4, dict(n=2, groove=1, depth=0.5))])

GLASS = mat(smooth=246, f0=F0_GLASS, porosity=0, relief=0.12, pom=0.08,
            layers=[("frame", 1.0, dict(border=1, depth=0.25, inner=0.95))])

WOOL = mat(smooth=6, f0=F0_FABRIC, porosity=38, relief=0.7, pom=0.3,
           layers=[("weave", 1.0, dict(size=2, amp=0.45)),
                   ("speckle", 0.18, dict(density=0.5))])

TERRACOTTA = mat(smooth=58, f0=F0_ROCK, porosity=22, relief=0.45, pom=0.25,
                 layers=[("fbm", 1.0, dict(octaves=2, scale=3, gain=0.5)),
                         ("fbm", 0.25, dict(octaves=2, scale=6))])

GLAZED = mat(smooth=196, f0=F0_GLASS, porosity=2, relief=0.3, pom=0.18,
             layers=[("grid", 1.0, dict(n=2, groove=1, depth=0.4)),
                     ("fbm", 0.15, dict(octaves=2, scale=4))])

CONCRETE = mat(smooth=48, f0=F0_ROCK, porosity=26, relief=0.35, pom=0.2,
               layers=[("fbm", 1.0, dict(octaves=3, scale=4, gain=0.45))])

CONCRETE_POWDER = mat(smooth=10, f0=F0_ROCK, porosity=58, relief=0.5, pom=0.3,
                      layers=[("speckle", 1.0, dict(density=0.75)),
                              ("fbm", 0.5, dict(octaves=3, scale=6))])

ORE = mat(smooth=34, f0=F0_ROCK, porosity=28, relief=1.0, pom=0.75,
          layers=[("fbm", 1.0, dict(octaves=3, scale=4, gain=0.55)),
                  ("cells", 0.5, dict(size=4, jitter=0.4)),
                  ("speckle", 0.3, dict(density=0.45))])

FOLIAGE = mat(smooth=24, f0=F0_ORGANIC, porosity=0, sss=210, relief=0.9, pom=0.5,
              layers=[("organic", 1.0, dict(amp=0.6))])

NETHER_ROCK = mat(smooth=18, f0=F0_ROCK, porosity=44, relief=1.0, pom=0.7,
                  layers=[("fbm", 1.0, dict(octaves=4, scale=3, gain=0.65)),
                          ("cells", 0.4, dict(size=4, jitter=0.35)),
                          ("speckle", 0.2, dict(density=0.5))])

ICE = mat(smooth=232, f0=F0_GLASS, porosity=0, sss=200, relief=0.3, pom=0.2,
          layers=[("crystal", 1.0, dict(facets=4)),
                  ("fbm", 0.4, dict(octaves=2, scale=3))])

SNOW = mat(smooth=30, f0=F0_ROCK, porosity=40, sss=0, relief=0.4, pom=0.25,
           layers=[("fbm", 1.0, dict(octaves=3, scale=5)),
                   ("speckle", 0.5, dict(density=0.6))])

QUARTZ = mat(smooth=104, f0=F0_ROCK, porosity=6, relief=0.4, pom=0.3,
             layers=[("fbm", 1.0, dict(octaves=3, scale=6)),
                     ("grain", 0.3, dict(axis="v", amp=0.15))])

PRISMARINE = mat(smooth=124, f0=F0_ROCK, porosity=10, relief=0.7, pom=0.5,
                 layers=[("scales", 1.0, dict(size=4, depth=0.45)),
                         ("fbm", 0.3, dict(octaves=3, scale=6))])

SCULK = mat(smooth=44, f0=F0_ORGANIC, porosity=0, sss=150, relief=0.9, pom=0.55,
            layers=[("organic", 1.0, dict(amp=0.7)),
                    ("speckle", 0.3, dict(density=0.4))])

OBSIDIAN = mat(smooth=172, f0=F0_GEM, porosity=0, relief=0.5, pom=0.35,
               layers=[("crystal", 1.0, dict(facets=6)),
                       ("fbm", 0.4, dict(octaves=3, scale=5))])

LAMP = mat(smooth=120, f0=F0_GLASS, porosity=0, emission=1.0, relief=0.4, pom=0.3,
           layers=[("grid", 1.0, dict(n=2, groove=1, depth=0.5)),
                   ("fbm", 0.3, dict(octaves=2, scale=4))])


# ---------------------------------------------------------------------------
# Catalogue : nom de texture (sans extension) -> materiau
# ---------------------------------------------------------------------------

COLORS = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink",
          "gray", "light_gray", "cyan", "purple", "blue", "brown", "green",
          "red", "black"]

WOODS = ["oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry"]
STEMS = ["crimson", "warped"]

# Textures animees en vanilla (PNG vertical multi-images + .mcmeta).
# Une carte _n/_s de dimensions differentes casserait l'atlas : on ne les
# genere qu'en mode --vanilla, ou l'on connait la taille et l'animation reelles.
ANIMATED = {
    "sea_lantern", "magma", "prismarine", "nether_portal",
    "fire_0", "fire_1", "soul_fire_0", "soul_fire_1",
    "water_still", "water_flow", "lava_still", "lava_flow",
    "kelp", "kelp_plant", "seagrass", "tall_seagrass_top", "tall_seagrass_bottom",
    "campfire_fire", "campfire_log_lit", "soul_campfire_fire",
    "blast_furnace_front_on", "smoker_front_on", "furnace_front_on",
    "stonecutter_saw", "respawn_anchor_top", "sculk", "sculk_vein",
    "sculk_sensor_tendril_active", "sculk_sensor_tendril_inactive",
    "calibrated_sculk_sensor_input_side",
}

TEXTURES = {}


def add(names, base, **over):
    """Enregistre une ou plusieurs textures avec le meme materiau."""
    if isinstance(names, str):
        names = [names]
    for n in names:
        TEXTURES[n] = derive(base, **over) if over else dict(base)


# --- Pierre ----------------------------------------------------------------
add(["stone", "andesite", "diorite", "granite", "tuff", "dripstone_block",
     "deepslate", "deepslate_top", "basalt_top", "basalt_side", "smooth_basalt"],
    ROUGH_STONE)
add(["cobblestone", "mossy_cobblestone", "cobbled_deepslate", "blackstone",
     "blackstone_top", "gilded_blackstone"], COBBLE)
add(["polished_andesite", "polished_diorite", "polished_granite", "smooth_stone",
     "smooth_stone_slab_side", "polished_deepslate", "polished_tuff",
     "polished_basalt_top", "polished_basalt_side", "polished_blackstone",
     "calcite"], POLISHED_STONE)
add(["stone_bricks", "mossy_stone_bricks", "cracked_stone_bricks",
     "deepslate_bricks", "cracked_deepslate_bricks", "tuff_bricks",
     "polished_blackstone_bricks", "cracked_polished_blackstone_bricks",
     "end_stone_bricks", "mud_bricks"], STONE_BRICK)
add(["deepslate_tiles", "cracked_deepslate_tiles"], TILE)
add(["chiseled_stone_bricks", "chiseled_deepslate", "chiseled_polished_blackstone",
     "chiseled_tuff", "chiseled_tuff_top", "chiseled_tuff_bricks",
     "chiseled_tuff_bricks_top", "chiseled_sandstone", "chiseled_red_sandstone",
     "chiseled_nether_bricks", "chiseled_bookshelf_empty"],
    derive(STONE_BRICK, relief=1.05, pom=0.85,
           layers=[("frame", 1.0, dict(border=1, depth=0.6, inner=0.85)),
                   ("fbm", 0.35, dict(octaves=3, scale=6))]))
add(["bedrock"], derive(COBBLE, smooth=8, porosity=44, relief=1.3))
add(["obsidian"], OBSIDIAN)
add(["crying_obsidian"], derive(OBSIDIAN, emission=0.55, smooth=178,
                                emissive_layers=[("speckle", 1.0, dict(density=0.22))]))
add(["bricks"], CLAY_BRICK)
add(["nether_bricks", "cracked_nether_bricks", "red_nether_bricks"],
    derive(CLAY_BRICK, smooth=28, porosity=40))
add(["reinforced_deepslate_top", "reinforced_deepslate_side",
     "reinforced_deepslate_bottom"], derive(POLISHED_STONE, smooth=64, relief=0.6))

# --- Sable, gres, terre ----------------------------------------------------
add(["sand", "red_sand"], SAND)
add(["sandstone", "sandstone_top", "sandstone_bottom", "cut_sandstone",
     "red_sandstone", "red_sandstone_top", "red_sandstone_bottom",
     "cut_red_sandstone"],
    derive(SAND, smooth=26, porosity=44, relief=0.7, pom=0.45,
           layers=[("strips", 1.0, dict(axis="h", width=4, depth=0.45)),
                   ("fbm", 0.35, dict(octaves=3, scale=4)),
                   ("speckle", 0.12, dict(density=0.4))]))
add(["dirt", "coarse_dirt", "rooted_dirt", "podzol_top", "podzol_side",
     "farmland", "farmland_moist", "dirt_path_top", "dirt_path_side",
     "mycelium_top", "mycelium_side", "mud", "packed_mud", "clay",
     "muddy_mangrove_roots_top", "muddy_mangrove_roots_side"], SOIL)
add(["grass_block_top", "grass_block_side", "grass_block_snow",
     "grass_block_side_overlay"],
    derive(SOIL, smooth=16, sss=170, porosity=0, relief=0.9,
           layers=[("organic", 1.0, dict(amp=0.65)),
                   ("speckle", 0.4, dict(density=0.5))]))
add(["gravel"], GRAVELLY)
add(["snow", "powder_snow"], SNOW)
add(["ice", "packed_ice", "blue_ice"], ICE)

# --- Minerais --------------------------------------------------------------
for _o in ["coal", "iron", "copper", "gold", "redstone", "emerald", "lapis", "diamond"]:
    add(["%s_ore" % _o, "deepslate_%s_ore" % _o], ORE)
add(["nether_gold_ore", "nether_quartz_ore"], derive(ORE, porosity=40, smooth=40))
add(["ancient_debris_top", "ancient_debris_side"],
    derive(ORE, smooth=96, f0=METAL_GENERIC, porosity=0, relief=1.05))
add(["raw_iron_block", "raw_copper_block", "raw_gold_block"],
    derive(ORE, smooth=88, f0=METAL_GENERIC, porosity=0, relief=1.1, pom=0.8))

# --- Metaux et blocs precieux ---------------------------------------------
add("iron_block", derive(METAL_SMOOTH, smooth=200, f0=METAL_IRON))
add("gold_block", derive(METAL_SMOOTH, smooth=226, f0=METAL_GOLD))
add("netherite_block", derive(METAL_SMOOTH, smooth=150, f0=METAL_GENERIC, relief=0.55,
                              layers=[("cells", 1.0, dict(size=4, jitter=0.3)),
                                      ("fbm", 0.4, dict(octaves=3, scale=5))]))
add("redstone_block", derive(METAL_SMOOTH, smooth=120, f0=METAL_GENERIC, relief=0.8,
                             layers=[("fbm", 1.0, dict(octaves=4, scale=5)),
                                     ("speckle", 0.4, dict(density=0.5))]))
add("diamond_block", derive(GEM_BLOCK, smooth=214))
add("emerald_block", derive(GEM_BLOCK, smooth=206))
add("lapis_block", derive(GEM_BLOCK, smooth=140, f0=F0_ROCK, porosity=12,
                          layers=[("fbm", 1.0, dict(octaves=4, scale=5)),
                                  ("speckle", 0.4, dict(density=0.5))]))
add(["amethyst_block", "budding_amethyst"],
    derive(GEM_BLOCK, smooth=192, sss=120, porosity=0, relief=0.9))

# Cuivre : la patine rend la surface plus rugueuse et moins metallique
add(["copper_block", "cut_copper", "chiseled_copper"],
    derive(METAL_SMOOTH, smooth=192, f0=METAL_COPPER))
add(["exposed_copper", "exposed_cut_copper", "exposed_chiseled_copper"],
    derive(METAL_SMOOTH, smooth=140, f0=METAL_COPPER, relief=0.5))
add(["weathered_copper", "weathered_cut_copper", "weathered_chiseled_copper"],
    derive(METAL_SMOOTH, smooth=86, f0=METAL_COPPER, porosity=18, relief=0.75,
           layers=[("scales", 1.0, dict(size=4, depth=0.35)),
                   ("fbm", 0.6, dict(octaves=3, scale=5))]))
add(["oxidized_copper", "oxidized_cut_copper", "oxidized_chiseled_copper"],
    derive(METAL_SMOOTH, smooth=52, f0=F0_ROCK, porosity=30, relief=0.9,
           layers=[("scales", 1.0, dict(size=3, depth=0.45)),
                   ("fbm", 0.7, dict(octaves=4, scale=6)),
                   ("speckle", 0.3, dict(density=0.45))]))
add(["copper_grate"], derive(METAL_SMOOTH, smooth=180, f0=METAL_COPPER, relief=1.1, pom=0.9,
                             layers=[("slats", 1.0, dict(n=4, axis="h", depth=0.85, thickness=2)),
                                     ("slats", 0.8, dict(n=4, axis="v", depth=0.85, thickness=2))]))
add(["exposed_copper_grate"], derive(TEXTURES["copper_grate"], smooth=130))
add(["weathered_copper_grate"], derive(TEXTURES["copper_grate"], smooth=80, porosity=18))
add(["oxidized_copper_grate"], derive(TEXTURES["copper_grate"], smooth=48, f0=F0_ROCK, porosity=30))
for _pfx in ["", "exposed_", "weathered_", "oxidized_"]:
    add(["%scopper_bulb" % _pfx, "%scopper_bulb_powered" % _pfx],
        derive(METAL_SMOOTH, smooth=170, f0=METAL_COPPER, relief=0.5,
               layers=[("grid", 1.0, dict(n=2, groove=1, depth=0.5)),
                       ("fbm", 0.3, dict(octaves=2, scale=4))]))
    add(["%scopper_bulb_lit" % _pfx, "%scopper_bulb_lit_powered" % _pfx],
        derive(LAMP, smooth=170, f0=METAL_COPPER, emission=0.95))

# --- Bois ------------------------------------------------------------------
for _w in WOODS:
    add("%s_planks" % _w, PLANK)
    add("%s_log" % _w, LOG_SIDE)
    add("%s_log_top" % _w, LOG_TOP)
    add("stripped_%s_log" % _w, STRIPPED_LOG)
    add("stripped_%s_log_top" % _w, LOG_TOP)
    add("%s_leaves" % _w, FOLIAGE)
for _s in STEMS:
    add("%s_planks" % _s, derive(PLANK, porosity=36, sss=0))
    add("%s_stem" % _s, LOG_SIDE)
    add("%s_stem_top" % _s, LOG_TOP)
    add("stripped_%s_stem" % _s, STRIPPED_LOG)
    add("stripped_%s_stem_top" % _s, LOG_TOP)
add(["azalea_leaves", "flowering_azalea_leaves"], FOLIAGE)
add(["bamboo_planks"], derive(PLANK, layers=[("planks", 1.0, dict(count=8, axis="h", groove=1, depth=0.6)),
                                             ("grain", 0.5, dict(axis="v", amp=0.2))]))
add(["bamboo_mosaic"], derive(PLANK, layers=[("grid", 1.0, dict(n=2, groove=1, depth=0.55)),
                                             ("planks", 0.7, dict(count=8, axis="h", groove=1, depth=0.5))]))
add(["bamboo_block", "stripped_bamboo_block"],
    derive(LOG_SIDE, layers=[("strips", 1.0, dict(axis="v", width=2, depth=0.5))]))
add(["bamboo_block_top", "stripped_bamboo_block_top"], LOG_TOP)
add(["bookshelf", "chiseled_bookshelf_occupied"],
    derive(PLANK, smooth=30, porosity=40, relief=1.0, pom=0.8,
           layers=[("planks", 1.0, dict(count=2, axis="h", groove=2, depth=0.9)),
                   ("strips", 0.6, dict(axis="v", width=2, depth=0.5))]))
add(["crafting_table_top", "crafting_table_side", "crafting_table_front"], PLANK)
add(["barrel_top", "barrel_side", "barrel_bottom", "barrel_top_open"],
    derive(PLANK, layers=[("strips", 1.0, dict(axis="v", width=2, depth=0.45)),
                          ("planks", 0.5, dict(count=4, axis="h", groove=1, depth=0.5))]))
add(["ladder", "scaffolding_top", "scaffolding_side", "scaffolding_bottom"],
    derive(PLANK, relief=0.9, pom=0.7))

# --- Nether ----------------------------------------------------------------
add(["netherrack", "crimson_nylium", "crimson_nylium_side", "warped_nylium",
     "warped_nylium_side", "soul_soil"], NETHER_ROCK)
add(["soul_sand"], derive(SAND, porosity=62, smooth=8, sss=90, relief=0.9))
add(["nether_wart_block", "warped_wart_block"],
    derive(FOLIAGE, smooth=18, sss=190, relief=1.0, pom=0.7))
add(["shroomlight"], derive(FOLIAGE, smooth=30, sss=200, emission=0.9, relief=0.9))
add(["glowstone"], derive(LAMP, emission=1.0, smooth=64, f0=F0_ROCK, relief=0.9, pom=0.7,
                          layers=[("cells", 1.0, dict(size=4, jitter=0.45)),
                                  ("speckle", 0.5, dict(density=0.5))]))
for _f in ["ochre", "verdant", "pearlescent"]:
    add(["%s_froglight_top" % _f, "%s_froglight_side" % _f],
        derive(LAMP, emission=0.95, smooth=110, sss=140, porosity=0))
add(["quartz_block_top", "quartz_block_side", "quartz_block_bottom",
     "quartz_bricks", "quartz_pillar", "quartz_pillar_top",
     "chiseled_quartz_block", "chiseled_quartz_block_top"], QUARTZ)

# --- End -------------------------------------------------------------------
add(["end_stone"], derive(ROUGH_STONE, smooth=26, porosity=34))
add(["purpur_block", "purpur_pillar", "purpur_pillar_top"],
    derive(POLISHED_STONE, smooth=72, porosity=14, relief=0.5))
add(["end_portal_frame_top", "end_portal_frame_side"],
    derive(POLISHED_STONE, smooth=80, relief=0.7))
add(["end_rod"], derive(LAMP, emission=1.0, smooth=140, relief=0.5))

# --- Ocean -----------------------------------------------------------------
add(["prismarine_bricks", "dark_prismarine"], PRISMARINE)
add(["sponge", "wet_sponge"], derive(FOLIAGE, smooth=6, porosity=64, sss=0, relief=1.0, pom=0.8))

# --- Sculk -----------------------------------------------------------------
add(["sculk_catalyst_top", "sculk_catalyst_side", "sculk_catalyst_bottom",
     "sculk_shrieker_top", "sculk_shrieker_side", "sculk_shrieker_bottom",
     "sculk_sensor_top", "sculk_sensor_side", "sculk_sensor_bottom",
     "calibrated_sculk_sensor_top", "calibrated_sculk_sensor_side"], SCULK)
add(["sculk_catalyst_top_bloom", "sculk_catalyst_side_bloom"],
    derive(SCULK, emission=0.55, emissive_layers=[("organic", 1.0, dict(amp=0.8))]))
add(["sculk_shrieker_inner_top", "sculk_shrieker_can_summon_inner_top"],
    derive(SCULK, emission=0.6))

# --- Verre, terre cuite, beton, laine -------------------------------------
add(["glass", "glass_pane_top", "tinted_glass"], GLASS)
add(["terracotta"], TERRACOTTA)
for _c in COLORS:
    add("%s_stained_glass" % _c, GLASS)
    add("%s_stained_glass_pane_top" % _c, GLASS)
    add("%s_terracotta" % _c, TERRACOTTA)
    add("%s_glazed_terracotta" % _c, GLAZED)
    add("%s_concrete" % _c, CONCRETE)
    add("%s_concrete_powder" % _c, CONCRETE_POWDER)
    add("%s_wool" % _c, WOOL)
    add("%s_shulker_box" % _c, derive(POLISHED_STONE, smooth=110, relief=0.6, pom=0.4))
add(["shulker_box"], derive(POLISHED_STONE, smooth=110, relief=0.6, pom=0.4))

# --- Blocs lumineux et redstone -------------------------------------------
add(["redstone_lamp"], derive(LAMP, emission=0.0, smooth=70))
add(["redstone_lamp_on"], derive(LAMP, emission=0.9, smooth=90))
add(["lantern", "soul_lantern"], derive(LAMP, emission=1.0, smooth=150, f0=METAL_IRON))
add(["torch", "soul_torch", "redstone_torch"], derive(LAMP, emission=1.0, smooth=40, f0=F0_WOOD))
add(["redstone_torch_off"], derive(PLANK, smooth=40, emission=0.0))
add(["jack_o_lantern"], derive(FOLIAGE, smooth=30, emission=0.9, sss=120))
add(["beacon"], derive(GLASS, emission=0.85, smooth=240))
add(["conduit"], derive(GEM_BLOCK, emission=0.7, smooth=180))
add(["glow_lichen"], derive(FOLIAGE, emission=0.35, sss=180))
add(["amethyst_cluster", "large_amethyst_bud", "medium_amethyst_bud",
     "small_amethyst_bud"], derive(GEM_BLOCK, smooth=196, sss=140, emission=0.15))
add(["furnace_top", "furnace_side", "furnace_front", "blast_furnace_top",
     "blast_furnace_side", "blast_furnace_front", "smoker_top", "smoker_side",
     "smoker_front", "smoker_bottom"], derive(COBBLE, smooth=30, relief=0.8))
add(["observer_top", "observer_side", "observer_front", "observer_back",
     "dispenser_front", "dropper_front", "piston_top", "piston_side",
     "piston_bottom", "piston_inner", "sticky_piston_top"],
    derive(COBBLE, smooth=40, relief=0.7))
add(["hopper_top", "hopper_outside", "hopper_inside"],
    derive(METAL_SMOOTH, smooth=120, f0=METAL_IRON, relief=0.8, pom=0.6))
add(["anvil", "anvil_top", "chipped_anvil_top", "damaged_anvil_top"],
    derive(METAL_SMOOTH, smooth=140, f0=METAL_IRON, relief=0.9, pom=0.7))
add(["iron_bars", "iron_trapdoor", "iron_door_top", "iron_door_bottom",
     "chain", "cauldron_side", "cauldron_top", "cauldron_bottom", "cauldron_inner"],
    derive(METAL_SMOOTH, smooth=160, f0=METAL_IRON, relief=0.7, pom=0.5))
add(["target_top", "target_side"], derive(WOOL, smooth=14, porosity=52))
add(["honeycomb_block", "honey_block_top", "honey_block_side",
     "honey_block_bottom"], derive(GLASS, smooth=180, sss=210, porosity=0, relief=0.6))
add(["slime_block"], derive(GLASS, smooth=200, sss=230, porosity=0, relief=0.5))
add(["moss_block", "pale_moss_block"], derive(FOLIAGE, smooth=14, sss=190, relief=1.0))
add(["hay_block_top", "hay_block_side", "dried_kelp_top", "dried_kelp_side",
     "dried_kelp_bottom"],
    derive(WOOL, smooth=16, porosity=56,
           layers=[("strips", 1.0, dict(axis="h", width=2, depth=0.45)),
                   ("speckle", 0.4, dict(density=0.5))]))
add(["melon_top", "melon_side", "pumpkin_top", "pumpkin_side", "carved_pumpkin"],
    derive(FOLIAGE, smooth=60, sss=150, relief=0.8))
add(["mushroom_block_inside", "brown_mushroom_block", "red_mushroom_block"],
    derive(FOLIAGE, smooth=26, sss=170, relief=0.9))
add(["note_block", "jukebox_side", "jukebox_top"], derive(PLANK, smooth=48))
add(["obsidian_pillar"], OBSIDIAN)


# --- Menuiseries, mobilier et blocs utilitaires ---------------------------
for _w in WOODS + STEMS + ["bamboo"]:
    add(["%s_door_top" % _w, "%s_door_bottom" % _w, "%s_trapdoor" % _w],
        derive(PLANK, relief=0.85, pom=0.65))

add(["rail", "rail_corner", "powered_rail", "powered_rail_on", "detector_rail",
     "detector_rail_on", "activator_rail", "activator_rail_on"],
    derive(METAL_SMOOTH, smooth=155, f0=METAL_IRON, relief=1.0, pom=0.75,
           layers=[("slats", 1.0, dict(n=8, axis="h", depth=0.7, thickness=1)),
                   ("strips", 0.6, dict(axis="v", width=6, depth=0.5))]))

add(["bone_block_top", "bone_block_side"],
    derive(POLISHED_STONE, smooth=54, porosity=26, relief=0.6, pom=0.4,
           layers=[("strips", 1.0, dict(axis="v", width=3, depth=0.4)),
                   ("fbm", 0.4, dict(octaves=3, scale=5))]))
add(["bell_top", "bell_side", "bell_bottom"],
    derive(METAL_SMOOTH, smooth=214, f0=METAL_GOLD, relief=0.5))
add(["lodestone_top", "lodestone_side"], derive(POLISHED_STONE, smooth=88, relief=0.7))
add(["brewing_stand", "brewing_stand_base"],
    derive(METAL_SMOOTH, smooth=140, f0=METAL_IRON, relief=0.7))
add(["spawner"], derive(METAL_SMOOTH, smooth=70, f0=METAL_IRON, relief=1.2, pom=0.9,
                        layers=[("slats", 1.0, dict(n=4, axis="h", depth=0.9, thickness=1)),
                                ("slats", 0.9, dict(n=4, axis="v", depth=0.9, thickness=1))]))

for _t in ["smithing_table_top", "smithing_table_side", "smithing_table_front",
           "smithing_table_bottom", "fletching_table_top", "fletching_table_side",
           "fletching_table_front", "cartography_table_top", "cartography_table_side1",
           "cartography_table_side2", "cartography_table_side3", "loom_top",
           "loom_side", "loom_front", "loom_bottom", "composter_top",
           "composter_side", "composter_bottom"]:
    add(_t, PLANK)
add(["grindstone_side", "grindstone_pivot", "grindstone_round",
     "stonecutter_top", "stonecutter_side", "stonecutter_bottom"],
    derive(COBBLE, smooth=44, relief=0.8))
add(["enchanting_table_top", "enchanting_table_side", "enchanting_table_bottom"],
    derive(OBSIDIAN, smooth=150, relief=0.7, pom=0.5))

for _b in ["beehive_end", "beehive_side", "beehive_front", "beehive_front_honey",
           "bee_nest_top", "bee_nest_side", "bee_nest_front", "bee_nest_front_honey",
           "bee_nest_bottom"]:
    add(_b, derive(PLANK, smooth=36, sss=120, porosity=0, relief=0.8,
                   layers=[("scales", 1.0, dict(size=4, depth=0.4)),
                           ("grain", 0.5, dict(axis="v", amp=0.25))]))

# --- Coraux ----------------------------------------------------------------
for _c in ["tube", "brain", "bubble", "fire", "horn"]:
    add(["%s_coral_block" % _c, "%s_coral" % _c, "%s_coral_fan" % _c],
        derive(FOLIAGE, smooth=40, sss=200, relief=1.0, pom=0.7))
    add(["dead_%s_coral_block" % _c, "dead_%s_coral" % _c, "dead_%s_coral_fan" % _c],
        derive(ROUGH_STONE, smooth=16, porosity=54, relief=0.95))

# --- Vegetation et divers --------------------------------------------------
add(["cobweb", "vine", "lily_pad", "chorus_flower", "chorus_plant",
     "mushroom_stem", "sea_pickle", "mangrove_roots_top", "mangrove_roots_side"],
    derive(FOLIAGE, smooth=20, sss=180, relief=0.85))
add(["cake_top", "cake_side", "cake_bottom", "cake_inner"],
    derive(WOOL, smooth=22, porosity=44, relief=0.6))
add(["tnt_top", "tnt_side", "tnt_bottom"], derive(WOOL, smooth=18, porosity=40))
add(["dragon_egg"], derive(OBSIDIAN, smooth=196, emission=0.25, sss=90, porosity=0,
                           relief=0.8, pom=0.55))
add(["respawn_anchor_bottom"], OBSIDIAN)
add(["respawn_anchor_side0"], derive(OBSIDIAN, smooth=168))
for _i in range(1, 5):
    add("respawn_anchor_side%d" % _i,
        derive(OBSIDIAN, smooth=168, emission=0.20 * _i,
               emissive_layers=[("crystal", 1.0, dict(facets=4))]))
