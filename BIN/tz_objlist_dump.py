#!/usr/bin/env python3
"""
tz_objlist_dump.py

- SOBJLIST.BIN: sequential entries: header (w,h) stored with 16-bit byteswap, followed by raw 16bpp pixels.
  IMPORTANT: pixel payload appears to be already in correct endian; do NOT byteswap pixels by default.

- DOBJLIST.BIN: file is 16-bit byteswapped; byteswap16(file) -> parse (w,h)+zlib blocks.
  Decompressed pixels still need byteswap16 before decode

Usage:
  python tz_objlist_dump.py --sobj SOBJLIST.BIN --dobj DOBJLIST.BIN --outdir out_objlists
  or
  python3 tz_objlist_dump.py --sobj SOBJLIST.BIN --dobj DOBJLIST.BIN --outdir out_objlists

Optional:
  --sobj-pixel-swap16    (test swapping SOBJLIST pixel words)
  --sobj-bgr             (swap R/B channels for SOBJLIST output)
  --sobj-flip-y          (vertical flip for SOBJLIST)
"""

import argparse
import json
import os
import struct
import zlib
from collections import Counter

try:
    from PIL import Image
except ImportError as e:
    raise SystemExit("Pillow is required: pip install pillow") from e


def bswap16(data: bytes) -> bytes:
    ba = bytearray(data)
    n = len(ba) & ~1
    for i in range(0, n, 2):
        ba[i], ba[i + 1] = ba[i + 1], ba[i]
    return bytes(ba)


def argb1555_to_rgba8888(px: int, bgr: bool = False):
    # px = 0bA RRRRR GGGGG BBBBB (ARGB1555-ish)
    a = 255 if (px & 0x8000) else 0
    r = (px >> 10) & 0x1F
    g = (px >> 5) & 0x1F
    b = px & 0x1F

    if bgr:
        r, b = b, r

    return (r * 255 // 31, g * 255 // 31, b * 255 // 31, a)


def dump_16bpp_png(raw_16bpp_bytes_le: bytes, w: int, h: int, out_path: str, bgr: bool = False, flip_y: bool = False):
    exp = w * h * 2
    if len(raw_16bpp_bytes_le) != exp:
        raise ValueError(f"Expected {exp} bytes for {w}x{h}x16bpp, got {len(raw_16bpp_bytes_le)}")

    vals = struct.unpack_from("<" + "H" * (w * h), raw_16bpp_bytes_le, 0)
    pixels = [argb1555_to_rgba8888(v, bgr=bgr) for v in vals]

    img = Image.new("RGBA", (w, h))
    img.putdata(pixels)

    if flip_y:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path)


def parse_sobj(sobj_path: str, outdir: str, pixel_swap16: bool, bgr: bool, flip_y: bool):
    b = open(sobj_path, "rb").read()
    off = 0
    idx = 0
    recs = []

    while off + 8 <= len(b):
        # header is 16-bit byteswapped
        w, h = struct.unpack("<II", bswap16(b[off:off+8]))
        payload_len = w * h * 2
        if payload_len <= 0 or off + 8 + payload_len > len(b):
            break

        payload = b[off + 8 : off + 8 + payload_len]

        # KEY FIX: do NOT swap pixels by default
        if pixel_swap16:
            payload = bswap16(payload)

        out_png = os.path.join(outdir, "SOBJLIST", f"sobj_{idx:04d}_{w}x{h}.png")
        dump_16bpp_png(payload, w, h, out_png, bgr=bgr, flip_y=flip_y)

        recs.append({"index": idx, "offset": off, "w": w, "h": h, "bytes": payload_len})
        idx += 1
        off += 8 + payload_len

    os.makedirs(os.path.join(outdir, "SOBJLIST"), exist_ok=True)
    with open(os.path.join(outdir, "SOBJLIST", "sobj_meta.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "file": os.path.abspath(sobj_path),
                "size_bytes": len(b),
                "records_dumped": len(recs),
                "note": "SOBJLIST: header byteswap16; pixels assumed little-endian u16 unless --sobj-pixel-swap16 is used.",
            },
            f,
            indent=2,
        )

    return len(recs)


def parse_dobj(dobj_path: str, outdir: str):
    b = open(dobj_path, "rb").read()

    # Whole file is byteswapped in 16-bit units
    sw = bswap16(b)

    blocks = []
    dim_counts = Counter()

    off = 0
    idx = 0
    while off + 8 <= len(sw):
        w, h = struct.unpack_from("<II", sw, off)
        if off + 10 > len(sw):
            break

        zhdr = sw[off + 8 : off + 10]
        if zhdr not in (b"\x78\x9c", b"\x78\xda", b"\x78\x01"):
            break

        decomp = zlib.decompressobj()
        dec = decomp.decompress(sw[off + 8 :])
        if not decomp.eof:
            break

        comp_len = (len(sw) - (off + 8)) - len(decomp.unused_data)
        exp = w * h * 2
        if len(dec) != exp:
            raise RuntimeError(f"Block {idx} size mismatch: w={w} h={h} exp={exp} got={len(dec)} at off=0x{off:X}")

        # DOBJLIST pixels need byteswap16 (this is the path you said looks perfect)
        dec_fixed = bswap16(dec)

        out_png = os.path.join(outdir, "DOBJLIST", f"dobj_{idx:04d}_{w}x{h}.png")
        dump_16bpp_png(dec_fixed, w, h, out_png, bgr=False, flip_y=False)

        blocks.append({"index": idx, "offset": off, "w": w, "h": h, "comp_len": comp_len, "dec_len": len(dec)})
        dim_counts[(w, h)] += 1

        idx += 1
        off = off + 8 + comp_len

    os.makedirs(os.path.join(outdir, "DOBJLIST"), exist_ok=True)
    with open(os.path.join(outdir, "DOBJLIST", "dobj_meta.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "file": os.path.abspath(dobj_path),
                "size_bytes": len(b),
                "blocks_dumped": len(blocks),
                "top_dims": [{"w": k[0], "h": k[1], "count": v} for k, v in dim_counts.most_common(50)],
                "note": "DOBJLIST: byteswap16(file), parse (w,h)+zlib; decompressed pixels byteswap16 then ARGB1555 decode.",
            },
            f,
            indent=2,
        )

    return len(blocks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sobj", required=True, help="Path to SOBJLIST.BIN")
    ap.add_argument("--dobj", required=True, help="Path to DOBJLIST.BIN")
    ap.add_argument("--outdir", required=True, help="Output directory")
    ap.add_argument("--sobj-pixel-swap16", action="store_true", help="TEST: byteswap16 SOBJLIST pixel payload (usually NOT needed)")
    ap.add_argument("--sobj-bgr", action="store_true", help="Swap R/B channels for SOBJLIST output")
    ap.add_argument("--sobj-flip-y", action="store_true", help="Flip SOBJLIST images vertically")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    n_s = parse_sobj(args.sobj, args.outdir, args.sobj_pixel_swap16, args.sobj_bgr, args.sobj_flip_y)
    n_d = parse_dobj(args.dobj, args.outdir)

    print(f"[OK] SOBJLIST dumped: {n_s} images -> {os.path.join(args.outdir, 'SOBJLIST')}")
    print(f"[OK] DOBJLIST dumped: {n_d} images -> {os.path.join(args.outdir, 'DOBJLIST')}")


if __name__ == "__main__":
    main()
