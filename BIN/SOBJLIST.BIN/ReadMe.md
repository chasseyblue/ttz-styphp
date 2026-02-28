# SOBJLIST.BIN Format (Stunt Typhoon Plus / Taito Type Zero)

## Summary
`SOBJLIST.BIN` is a sequential list of raw 16bpp textures. Each entry begins with an 8-byte `(width,height)` header that is stored with a **16-bit byteswap** (word swap). Unlike `DOBJLIST.BIN`, the **pixel payload itself is already in the correct u16 endianness** and must NOT be byteswapped (by default).

---

## Endianness / Swapping

### Header storage
The 8-byte header is stored with byteswap16 applied. To interpret it:

1. Read 8 bytes
2. `header = byteswap16(header)`
3. Interpret as `<u32_le width, u32_le height>`

### Pixel payload storage
The payload is raw 16bpp pixels and should be interpreted as **little-endian u16 words** directly.

If you byteswap the payload, images tend to look “inverted/neon/wrong”.

---

## High-level structure


SOBJLIST := entry_0 | entry_1 | ... | entry_N

entry := header | pixel_data

header (stored byteswapped16) =>
u32_le width
u32_le height

pixel_data :=
width * height * 2 bytes
(raw 16bpp pixel stream, u16 little-endian)


Entries are stored back-to-back with no separate index table required for traversal.

---

## Pixel format (working hypothesis)
Decoding as **ARGB1555** produces correct-looking images:


bit 15: 1-bit alpha
bits 10-14: red (5)
bits 5-9: green (5)
bits 0-4: blue (5)


---

## Recommended decode pipeline (reference)

For each entry:

1. Read 8 bytes -> `hdr_raw`
2. `hdr = byteswap16(hdr_raw)`
3. `(w,h) = <u32_le, u32_le from hdr>`
4. Read `payload_len = w*h*2` bytes
5. Decode payload as little-endian u16 ARGB1555 (no payload swap)
6. Continue until bounds fail.

---

## Validation signals
When decoded correctly:
- Images look correct without swizzle/tiling.
- Dimensions vary (not limited to 16x32); entries like 64x72 can occur.
- No zlib headers (`78 9C`) appear at entry payload start (this is raw).

---
