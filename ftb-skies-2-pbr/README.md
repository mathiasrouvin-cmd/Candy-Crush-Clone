# Skies PBR — pack de textures PBR pour shaders

**Minecraft 1.21.1 · NeoForge · FTB Skies 2 · format LabPBR 1.3**

Un pack de ressources qui donne du **relief, de la brillance, du métal et de la
lumière** à tes blocs sous shaders, sans changer une seule couleur du jeu.

![Aperçu des matériaux générés](docs/preview.png)

*Aperçu calculé à partir des cartes du pack (albédo volontairement neutre : on
juge le relief et la matière, pas la couleur). Produit par `tools/preview.py`.*

---

## À lire en premier : ce que fait (et ne fait pas) ce pack

Ce pack **ne remplace aucune texture**. Il ajoute, à côté de chaque texture, deux
cartes que les shaders savent lire :

| Fichier | Rôle |
|---|---|
| `stone_n.png` | relief : normales, occlusion ambiante, hauteur pour le parallaxe (POM) |
| `stone_s.png` | matière : brillance, réflectance/métal, porosité ou diffusion, émission |

Conséquences directes :

- **Sans shader, tu ne verras strictement aucune différence.** C'est normal :
  Minecraft vanilla ignore ces cartes. Il faut Iris + un shader compatible LabPBR.
- Tes textures gardent exactement l'apparence de FTB Skies 2. Le pack est
  **cumulable** avec n'importe quel pack de textures : mets-le simplement
  au-dessus dans la liste.
- Le pack ne contient **aucune texture du jeu** : uniquement des cartes générées.
  Rien de redistribué, rien qui puisse entrer en conflit visuel.

Concrètement, sous shaders : la pierre accroche la lumière, le métal réfléchit
vraiment, la laine devient mate, le verre devient net, la pierre de lumière et
les lanternes éclairent par elles-mêmes, et les briques prennent du creux.

---

## Installation dans FTB Skies 2

### 1. Le shader : il est déjà là

Pas besoin d'installer Iris. FTB Skies 2 embarque déjà toute la pile de rendu —
**Iris 1.8.12 + Embeddium + Monocle** — et livre même un shader **déjà
décompressé** dans `shaderpacks/` : *Complementary Reimagined + Euphoria Patches*.

Il faut seulement l'activer : *Options → Video Settings → Shader Packs* → clique
sur le shader. **Aucun shader n'est actif d'origine** (`shaderPack=` est vide
dans `config/iris.properties`), c'est pour ça que le dossier pré-installé semble
ne rien faire.

> **Ne remplace pas Embeddium par Sodium.** Le conseil « installe Sodium + Iris »
> qu'on lit partout pour 1.21.1 **casse ce modpack** : Monocle est précisément là
> pour qu'Iris rende à travers Embeddium. Idem pour Oculus et Rubidium, qui sont
> des mods Forge de l'ère 1.20.1 et n'existent pas pour NeoForge 1.21.1.

Si l'écran de sélection des shaders apparaît **vide ou juste flou** alors qu'il
répond aux clics : c'est un défaut d'affichage connu d'Iris avec le flou de
menu. Mets `menuBackgroundBlurriness:0` dans l'`options.txt` de l'instance.

Tu peux évidemment mettre un autre shader (BSL, Photon, Rethinking Voxels…) dans
`shaderpacks/` — voir le tableau de réglages plus bas.

### 2. Le pack

1. Récupère **`dist/SkiesPBR-1.0.0.zip`** (déjà construit dans ce dépôt), ou
   reconstruis-le toi-même — voir *Construire le pack* plus bas.
2. Ouvre le dossier de l'instance. **Ne cherche pas le chemin à la main** : selon
   l'âge de ton installation, le dossier s'appelle `ftb skies 2` ou porte un
   identifiant du genre `e978a054-423f-…`.
   - **FTB App** : bouton `...` sur l'instance → *Settings* → **Open Folder**
   - **CurseForge** : `...` → *Open Folder*
   - **Prism / MultiMC** : clic droit → *Folder* → *.minecraft*
3. Dépose le `.zip` dans **`resourcepacks/`**.

   > Sous FTB App et CurseForge, **le dossier d'instance est déjà le dossier de
   > jeu** : `resourcepacks/` est directement à la racine, à côté de `mods/` et
   > `config/`. Il n'y a **pas** de sous-dossier `.minecraft` — contrairement à
   > Prism. C'est l'erreur la plus fréquente.

4. En jeu : *Options → Packs de ressources* → passe **Skies PBR** à droite, puis
   **glisse-le tout en haut** de la colonne de droite.

   FTB Skies 2 épingle son pack de police (*Slightly-Improved-Font*) en haut de
   la pile : tu peux le faire redescendre, il n'est pas verrouillé. En revanche
   les paquets de ressources des mods sont verrouillés tout en bas — c'est une
   bonne nouvelle, ton pack passe toujours devant eux.

   Si tu as activé un des packs de retexture livrés avec le modpack
   (*AE2 Blackout*, *Better Replication Pipes*, *Pretty X Smart Pipez*),
   place-les **sous** Skies PBR — sinon ces blocs prendraient leurs couleurs
   d'un pack et leur relief d'un autre.

### 3. Les réglages du shader (l'étape qu'on oublie)

Un pack LabPBR parfait ne fait **rien** tant que le shader n'est pas réglé pour
lire les cartes.

> **Iris n'a aucun bouton « Normal maps » / « Specular maps ».** Ces bascules
> n'existent que sous OptiFine. Tous les tutoriels qui te disent de les activer
> « dans l'écran de sélection des shaders » décrivent OptiFine. Sous Iris, tout
> se passe dans les options **du shader lui-même** :
> *Options → Vidéo → Shaders → (roue dentée) Shader Options*.

| Shader | Réglages à changer |
|---|---|
| **Complementary Reimagined / Unbound**, **Rethinking Voxels** | `RP Support` → **labPBR (RP Required)** (écran racine) · puis *Materials → labPBR/seuspbr Materials → Parallax Occlusion Mapping* → ON · et *Performance Settings → Block Reflect Quality* → au-dessus de *Basic*, sinon aucune réflexion spéculaire |
| **BSL** | *Material → Advanced Materials* → ON · *Material → Material Format* → **labPBR 1.3** (et non SEUS/Old PBR) · *Material → Normals & Parallax → Parallax Occlusion Mapping* → ON |
| **Photon** | *Materials* → **trois** bascules distinctes, toutes désactivées d'origine : `Normal Mapping`, `Specular Mapping`, `Parallax Occlusion Mapping` · *Materials → Resource Pack Settings → Texture Format* → `labPBR` |
| **Kappa / Nostalgia** | *Terrain → Parallax Occlusion Mapping* → ON · *Reflections → Resourcepack Reflections* → ON |

Deux pièges fréquents :

- Sur Complementary et Rethinking Voxels, **les curseurs POM restent visibles et
  cliquables même quand `RP Support` est sur *Basic* ou *Integrated PBR+*** — ils
  ne font alors strictement rien. Règle `RP Support` **en premier**.
- Sur BSL, toute option dont le libellé finit par `*` est inerte tant que
  *Advanced Materials* est désactivé. Et un mauvais *Material Format* ne produit
  pas d'erreur : juste des reflets faux, mais crédibles.

### ⚠️ Important : le shader livré avec FTB Skies 2 ignore ce pack par défaut

*Complementary Reimagined + Euphoria Patches*, celui que le modpack pré-installe,
est livré sur `RP Support = Integrated PBR+`. Dans ce mode il **ignore purement
et simplement** les cartes `_n` / `_s`. Tant que tu ne passes pas ce réglage sur
**labPBR (RP Required)**, le pack ne changera rien — quoi que tu fasses par
ailleurs. C'est de loin la cause n°1 de « j'ai installé le pack, je ne vois rien ».

Mais attention à ce que ce basculement entraîne :
passer `RP Support` sur **labPBR désactive Integrated PBR+** —
le système qui génère automatiquement du relief, des minerais brillants et du
verre travaillé pour *tous* les blocs, y compris ceux des mods.

Sur un modpack comme FTB Skies 2, la conséquence est très concrète : les blocs
des mods qui n'ont pas de cartes LabPBR deviennent **plats et ternes** à
l'instant où tu bascules. Tu as trois options :

1. **La bonne** : génère le pack en mode référence en incluant les mods
   (`--vanilla … --all-namespaces`, voir plus bas). Les blocs modés reçoivent
   alors eux aussi leurs cartes, et rien ne se dégrade.
2. Utilise un shader qui n'a pas ce couplage — **BSL** ou **Photon** — où
   activer les cartes n'éteint aucun système de secours.
3. Reste sur *Integrated PBR+* et renonce au POM : le pack ne servira presque
   à rien.

Ce point est la principale raison d'être du mode `--all-namespaces`.

## Ce que couvre le pack

**643 textures** de blocs vanilla 1.21.1, réparties par famille de matériau :

- pierres, roches profondes, tuf, blackstone, basalte, calcite
- briques, tuiles, blocs ciselés, grès et grès rouge
- tous les bois 1.21.1 (chêne, épicéa, bouleau, acajou, acacia, chêne noir,
  palétuvier, cerisier, bambou) + tiges du Nether
- terres, sables, graviers, argiles, neige, glaces
- tous les minerais (surface, roche profonde, Nether) et blocs bruts
- métaux avec leurs **indices LabPBR réels** : fer (230), or (231), cuivre (234)
  — le cuivre perd sa brillance au fil des quatre stades d'oxydation
- verres, verres teintés, terres cuites, terres cuites vernissées, bétons,
  poudres de béton, laines
- Nether, End, prismarine, sculk, améthyste, coraux
- portes, trappes, rails, établis, ruches, os, cloches, enchantement
- **41 textures émissives** : pierre lumineuse, lanternes, torches, lampes de
  redstone allumées, champilampes, grenouillumes, obsidienne pleureuse,
  ampoules de cuivre, tiges de l'End, catalyseurs sculk…

Les blocs de mods ne sont **pas** couverts par défaut : voir la section
suivante, qui règle exactement ce point.

---

## Aller plus loin : le mode référence (fortement recommandé)

Par défaut, le relief est **déduit de la famille du matériau** (une brique
reçoit un appareillage de briques, une bûche des fibres verticales, etc.). C'est
propre et cohérent, mais ça ne « voit » pas les vraies textures.

Si tu pointes le générateur vers les textures de ton instance, il fait beaucoup
mieux :

```bash
python3 tools/build.py --vanilla /chemin/vers/assets --all-namespaces --zip
```

Ce mode :

- **dérive le relief de la vraie image** (les creux suivent le dessin réel) ;
- **couvre les blocs de tous les mods** du modpack — Create, Mekanism, Ars
  Nouveau, etc. — en devinant le matériau d'après le nom du bloc, et en écrivant
  les cartes dans le namespace du mod (`assets/<modid>/textures/block/…`), seul
  endroit où Iris ira les chercher ;
- respecte la **transparence** : les pixels ajourés (feuillages, barreaux)
  reçoivent une normale neutre, ce qui évite les artefacts de parallaxe ;
- limite l'**émission aux pixels réellement lumineux** (les veines de
  l'obsidienne pleureuse, pas le bloc entier) ;
- gère les **textures animées** (taille exacte + `.mcmeta` recopié) et les
  textures **HD** d'un pack 32× ou 64×.

### En pratique, en deux commandes

`tools/collect_assets.py` fait le travail fastidieux : il parcourt le jar du
client **et tous les jars de `mods/`**, et en extrait les textures de blocs et
d'objets dans un seul arbre `assets/`.

```bash
# 1. rassembler les textures de l'instance (le chemin = celui d'« Open Folder »)
python3 tools/collect_assets.py "/chemin/vers/instance/ftb skies 2" -o /tmp/mcassets

# 2. générer le pack qui couvre vanilla ET les mods
python3 tools/build.py --vanilla /tmp/mcassets --all-namespaces --items --zip
```

Avec les ~480 mods de FTB Skies 2, la seconde commande produit un pack
nettement plus complet que celui livré ici, et c'est **la** façon de garder des
blocs modés corrects si tu joues avec Complementary en mode labPBR.

Options utiles : `--no-client` pour ne traiter que les mods, `--verbose` pour
voir le détail par archive. En cas de doublon entre deux archives, la première
lue gagne.

> L'outil n'extrait que `textures/block` et `textures/item`, refuse toute entrée
> d'archive qui chercherait à écrire hors du dossier de sortie, et ces textures
> ne servent **que** de source de calcul : elles ne sont jamais copiées dans le
> pack produit — un test automatisé le vérifie.

## Construire le pack

Aucune dépendance : **Python 3.8+** et rien d'autre (le codec PNG est inclus).

```bash
python3 tools/build.py --zip          # génère build/pack/ et build/dist/*.zip
python3 tools/validate.py             # vérifie la conformité LabPBR
python3 tools/preview.py              # aperçu éclairé, sans lancer le jeu
python3 tests/test_pipeline.py        # 41 tests
```

Options utiles :

| Option | Effet |
|---|---|
| `--vanilla <dir>` | dérive les cartes des vraies textures |
| `--all-namespaces` | couvre aussi les blocs de mods |
| `--items` | traite aussi `textures/item` (mode référence) |
| `--no-pom` | aucun relief en volume (hauteur plate) — si le POM te gêne |
| `--no-ao` | désactive l'occlusion ambiante intégrée |
| `--blend 0..1` | dosage entre relief réel et motif procédural (0,65 par défaut) |
| `--zip` | produit l'archive installable |

`tools/preview.py` produit `build/preview.png` : une planche de vignettes
éclairées calculées à partir des cartes générées. C'est le moyen le plus rapide
de juger un réglage sans relancer Minecraft.

---

## Personnaliser un matériau

Tout se règle dans `tools/materials.py`. Exemple — rendre l'obsidienne plus
miroir et moins profonde :

```python
add(["obsidian"], derive(OBSIDIAN, smooth=210, pom=0.20))
```

Les champs disponibles :

| Champ | Plage | Rôle |
|---|---|---|
| `smooth` | 0–255 | brillance perçue (0 mat, 255 miroir) |
| `f0` | 0–229 ou `METAL_*` | réflectance ; au-delà de 229 c'est un métal |
| `porosity` | 0–64 | absorption d'eau (sable 64, laine 38, bois 12) |
| `sss` | 0–255 | diffusion sous la surface (feuillages, glace, slime) |
| `emission` | 0.0–1.0 | lumière propre |
| `relief` | ~0.1–1.5 | force du relief |
| `pom` | 0.0–1.0 | profondeur du parallaxe |
| `layers` | motifs | dessin du relief (17 motifs dans `patterns.py`) |

`porosity` et `sss` partagent le même canal : ils s'excluent mutuellement.

---

## Dépannage

**Je ne vois aucune différence.**
Vérifie dans l'ordre : (1) un shader est-il réellement sélectionné — aucun ne
l'est d'origine ; (2) `RP Support` est-il sur **labPBR** — c'est la cause n°1 ;
(3) le pack est-il **au-dessus** des autres dans la liste. Sans shader actif, il
est parfaitement normal de ne rien voir : c'est le principe même d'un pack PBR.

**Mon pack se désactive tout seul.**
Ce n'est pas un caprice : quand un rechargement de ressources échoue, FTB Skies 2
(via ResourcePackOverrides) réinitialise la sélection à sa liste par défaut,
jusqu'à cinq fois par session. La cause est donc un pack en erreur, pas le
mécanisme. Lance `python3 tools/validate.py` sur le pack décompressé.

**Certains blocs de Chipped, Rechiseled ou les tuyaux ont un relief décalé.**
Le modpack embarque des mods de textures connectées (CTM, Athena, Fusion). Pour
ces blocs, les cartes doivent suivre la disposition en tuiles du mod ; le
générateur produit une carte par fichier, ce qui convient aux blocs ordinaires
mais pas aux atlas CTM. Ces blocs-là restent mieux servis sans PBR.

**Le pack est marqué « Incompatible » en rouge.**
Ce n'est qu'un avertissement de version : confirme, le pack se charge normalement.
Un pack qui **n'apparaît pas du tout** dans la liste, c'est un autre problème
(`pack.mcmeta` absent, ou zip contenant un dossier de trop à la racine).

**Les blocs de mods n'ont pas de relief.**
Attendu avec le pack par défaut. Iris cherche les cartes dans le namespace du
mod : relance avec `--vanilla … --all-namespaces`.

**Les bords des blocs bavent, il y a des trous.**
C'est le POM trop profond. Baisse *POM depth* dans le shader, ou régénère avec
`--no-pom`.

**Tout brille comme du plastique mouillé.**
Un `smooth` ou un `f0` trop haut sur une famille. Baisse `smooth` dans
`materials.py` et régénère.

**Le rendu est correct de près et bizarre de loin.**
Vérifie que `assets/minecraft/optifine/texture.properties` est bien présent dans
le pack : sans lui, Iris filtre les cartes `_s` en linéaire et mélange les
identifiants de métaux avec l'émission. `tools/validate.py` le contrôle.

**Les blocs des mods sont devenus ternes depuis que j'ai activé labPBR.**
Comportement attendu sur Complementary et Rethinking Voxels : voir
l'avertissement plus haut. Régénère avec `--all-namespaces`.

---

## Structure du dépôt

```
ftb-skies-2-pbr/
├── tools/
│   ├── pngio.py       codec PNG pur Python (lecture/écriture RGBA)
│   ├── patterns.py    17 motifs de relief tuilables + normales/occlusion
│   ├── materials.py   catalogue : 643 textures et leurs propriétés LabPBR
│   ├── build.py       génération du pack
│   ├── collect_assets.py  extrait les textures d'une instance (client + mods)
│   ├── validate.py    contrôle de conformité LabPBR
│   └── preview.py     rendu d'aperçu hors du jeu
├── tests/
│   └── test_pipeline.py   29 tests (codec, motifs, encodage, mode référence)
└── build/             produit par build.py (non versionné)
```

---

## Notes techniques

Le pack respecte la spécification **LabPBR 1.3** :

- `_n` : R/G = normale tangente en convention **DirectX / Y−** (le vert pointe
  vers le bas), B = occlusion ambiante, A = hauteur (jamais 0, ce qui casserait
  le POM de certains shaders) ;
- `_s` : R = brillance perçue, G = réflectance (les métaux utilisent les indices
  nommés 230–237, la plage 238–254 réservée est évitée), B = porosité (0–64) ou
  diffusion (65–255), A = émission — avec **255 = aucune émission**, le piège
  classique du format, qu'un test verrouille explicitement ;
- `assets/minecraft/optifine/texture.properties` déclare `format=lab-pbr/1.3` —
  chemin codé en dur dans Iris. Il active les macros
  `MC_TEXTURE_FORMAT_LAB_PBR` / `_1_3` côté shader et le filtrage adapté aux
  canaux discrets du `_s` (1.3 est la seule version qu'Iris accepte sans risque) ;
- toutes les cartes sont écrites en **PNG RGBA 32 bits** : l'alpha y est une
  donnée, pas une transparence.

`pack_format` vaut **34** (1.21 / 1.21.1), avec `supported_formats` `[34, 46]`
pour couvrir 1.21 → 1.21.4 sans avertissement.

---

## Licence

Contenu généré, libre d'utilisation, de modification et de redistribution.
Aucune ressource de Mojang ou d'un mod n'est incluse dans le pack.
