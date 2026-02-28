# DOBJLIST.BIN Format (Stunt Typhoon Plus / Taito Type Zero)

## Summary
`DOBJLIST.BIN` is a sequential bundle of many texture blocks. The entire file is stored with a **16-bit byteswap** (word-swap) applied. After undoing that swap, each block contains a `(width,height)` header followed by a **zlib stream**. The zlib stream decompresses to **16bpp pixel data** whose u16 words are also byteswapped.

This file decodes cleanly into correct-looking textures using the pipeline described below.

---

## Endianness / Swapping

### File-level storage
All bytes in the file are stored with a **byteswap16** applied:

- Stored: `B1 B0 B3 B2 B5 B4 ...`
- Logical: `B0 B1 B2 B3 B4 B5 ...`

Undo this first to make headers and zlib headers readable.

### Pixel-level storage
After zlib decompression, the resulting 16bpp pixel stream still appears to require **byteswap16 per u16** to produce correct colors/alpha.

---

## High-level structure

After undoing file-level byteswap16:


DOBJLIST := block_0 | block_1 | ... | block_N

block := header | zlib_stream

header := u32_le width
u32_le height

zlib_stream := standard zlib stream starting with one of:
78 9C, 78 DA, or 78 01


Blocks are stored back-to-back. The end of a block is determined by zlib’s end-of-stream (EOF).

---

## Decompressed payload

For each block:

- `expected_decompressed_size = width * height * 2`

This strongly indicates **16 bits per pixel**.

After decompression, apply byteswap16 to the decompressed buffer, then decode pixels as 16bpp.

---

## Pixel format (working hypothesis)
The decoded output looks correct when interpreted as **ARGB1555**:


bit 15: 1-bit alpha
bits 10-14: red (5 bits)
bits 5-9: green (5 bits)
bits 0-4: blue (5 bits)


Note: RGB565 is possible in general, but ARGB1555 matched observed alpha usage and produced visually correct results in this dataset.

---

## Recommended decode pipeline (reference)

1. Read file bytes.
2. `buf = byteswap16(buf)`  (undo file storage swap)
3. Loop:
   - read `width = u32_le`, `height = u32_le`
   - zlib-decompress starting at current offset
   - verify `len(decompressed) == width * height * 2`
   - `pixels = byteswap16(decompressed)`  (fix pixel word order)
   - decode `pixels` as ARGB1555 into RGBA8888
4. Advance offset by `8 + compressed_length_consumed` and continue until parsing fails.

---

## Validation signals
When decoded correctly:
- Images “look right” (correct orientation and colors).
- Decompressed sizes always match `w*h*2`.
- Common dimensions include many small sprites (e.g. 32x32) and larger UI/background assets.

---
