"""
pngio.py - Lecture / ecriture PNG en pur Python (aucune dependance externe).

Suffisant pour les textures Minecraft : PNG non entrelaces, 8 ou 16 bits par
canal, types de couleur 0 (gris), 2 (RVB), 3 (palette), 4 (gris+alpha),
6 (RVBA). Tout est normalise en RVBA 8 bits en interne.

Ecrit systematiquement du RVBA 8 bits, ce qui est le format attendu par les
shaders LabPBR (le canal alpha porte la hauteur dans les _n et l'emission
dans les _s : il ne doit jamais etre absent).
"""

import struct
import zlib

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class Image:
    """Image RVBA 8 bits. Les pixels sont stockes a plat dans un bytearray."""

    __slots__ = ("w", "h", "data")

    def __init__(self, w, h, data=None, fill=(0, 0, 0, 0)):
        self.w = w
        self.h = h
        if data is None:
            self.data = bytearray(bytes(fill) * (w * h))
        else:
            if len(data) != w * h * 4:
                raise ValueError("taille de buffer incoherente")
            self.data = bytearray(data)

    def get(self, x, y):
        i = (y * self.w + x) * 4
        return tuple(self.data[i:i + 4])

    def put(self, x, y, rgba):
        i = (y * self.w + x) * 4
        self.data[i] = rgba[0] & 0xFF
        self.data[i + 1] = rgba[1] & 0xFF
        self.data[i + 2] = rgba[2] & 0xFF
        self.data[i + 3] = rgba[3] & 0xFF

    def copy(self):
        return Image(self.w, self.h, bytes(self.data))

    def scaled(self, factor):
        """Agrandissement entier au plus proche voisin (nearest neighbour)."""
        if factor == 1:
            return self.copy()
        nw, nh = self.w * factor, self.h * factor
        out = Image(nw, nh)
        for y in range(nh):
            sy = y // factor
            row = (sy * self.w) * 4
            orow = (y * nw) * 4
            for x in range(nw):
                sx = x // factor
                si = row + sx * 4
                oi = orow + x * 4
                out.data[oi:oi + 4] = self.data[si:si + 4]
        return out


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter(raw, w, h, bpp, stride):
    out = bytearray(h * stride)
    prev = bytearray(stride)
    pos = 0
    for y in range(h):
        ft = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if ft == 0:
            pass
        elif ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                c = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(a, prev[i], c)) & 0xFF
        else:
            raise ValueError("filtre PNG inconnu: %d" % ft)
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return out


def read_png(path):
    """Charge un PNG et renvoie une Image RVBA 8 bits."""
    with open(path, "rb") as fh:
        blob = fh.read()
    if not blob.startswith(PNG_MAGIC):
        raise ValueError("%s n'est pas un PNG" % path)

    pos = len(PNG_MAGIC)
    idat = bytearray()
    palette = None
    trns = None
    w = h = depth = ctype = interlace = None

    while pos < len(blob):
        (length,) = struct.unpack(">I", blob[pos:pos + 4])
        ctag = blob[pos + 4:pos + 8]
        body = blob[pos + 8:pos + 8 + length]
        pos += 12 + length  # 4 longueur + 4 type + data + 4 CRC
        if ctag == b"IHDR":
            w, h, depth, ctype, _comp, _filt, interlace = struct.unpack(">IIBBBBB", body)
        elif ctag == b"PLTE":
            palette = body
        elif ctag == b"tRNS":
            trns = body
        elif ctag == b"IDAT":
            idat += body
        elif ctag == b"IEND":
            break

    if w is None:
        raise ValueError("IHDR manquant dans %s" % path)
    if interlace:
        raise ValueError("PNG entrelace (Adam7) non supporte: %s" % path)
    if depth not in (8, 16):
        # 1/2/4 bits : uniquement rencontre sur des palettes, on refuse proprement
        raise ValueError("profondeur %d bits non supportee: %s" % (depth, path))

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    sample = depth // 8
    bpp = max(1, channels * sample)
    stride = w * channels * sample
    raw = _unfilter(zlib.decompress(bytes(idat)), w, h, bpp, stride)

    img = Image(w, h)
    step = channels * sample
    for y in range(h):
        base = y * stride
        for x in range(w):
            i = base + x * step
            if sample == 2:
                vals = [raw[i + k * 2] for k in range(channels)]  # octet de poids fort
            else:
                vals = [raw[i + k] for k in range(channels)]
            if ctype == 0:
                g = vals[0]
                a = 255
                if trns and len(trns) >= 2 and struct.unpack(">H", trns[:2])[0] == g:
                    a = 0
                px = (g, g, g, a)
            elif ctype == 4:
                px = (vals[0], vals[0], vals[0], vals[1])
            elif ctype == 2:
                px = (vals[0], vals[1], vals[2], 255)
            elif ctype == 6:
                px = (vals[0], vals[1], vals[2], vals[3])
            else:  # palette
                idx = vals[0]
                if palette is None or idx * 3 + 2 >= len(palette):
                    px = (0, 0, 0, 0)
                else:
                    a = trns[idx] if (trns and idx < len(trns)) else 255
                    px = (palette[idx * 3], palette[idx * 3 + 1], palette[idx * 3 + 2], a)
            img.put(x, y, px)
    return img


def _chunk(tag, body):
    return (struct.pack(">I", len(body)) + tag + body
            + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))


def write_png(path, img):
    """Ecrit une Image en PNG RVBA 8 bits, compression maximale."""
    stride = img.w * 4
    raw = bytearray()
    for y in range(img.h):
        raw.append(0)  # filtre None : les textures 16x16 se compressent tres bien
        raw += img.data[y * stride:(y + 1) * stride]
    blob = (PNG_MAGIC
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", img.w, img.h, 8, 6, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(blob)
