# Stunt Typhoon / Stunt Typhoon Plus Format RE

Reposistory aims to provide tools and information on all formats that is used in the 2001 Arcade Game for the Taito Type Zero hardware.

Collection of tools and format research - **currently a WIP**

### styphp.chd
Public MAME dump has the following charactistics:
- Every 2-byte pair is reversed.
- Real size of the game is 218 MB (228,611,751 bytes)
- 512 byte sectors
- File table starts at offset `0x0`, then followed by table entries which are exactly 32 bytes long, each.

Each entry in the file table contains:
- file name
- flags
- checksum
- start sector
- sector count
- actual file size

After swapping the image:
- 16-bit byte pairs swapped
- File table location at the very start of the image, offset `0x0`
- Entry size	Each file table entry is exactly `32 bytes`
- Filename field are at the	first `16 bytes` of each entry
- Filename encoding	Null-terminated ASCII
- Numeric fields `Big-endian`
- Files are addressed by 512-byte sectors

File table format onced swapped:
- `0x00`	`16 bytes`	File name
- `0x10`	`2 bytes`	Flag
- `0x12`	`2 bytes`	Checksum
- `0x14`	`4 bytes`	Start sector
- `0x18`	`4 bytes`	Sector count
- `0x1C`	`4 bytes`	Actual file size

---

### Reverse Engineering of Formats

## PDZ
Hypothesis for extension "*Polygon Data Zlib*" 

`.PDZ` zlib-wrapped geometry payload, decompresses into `.pd`

Header information:
| Offset | Size   | Meaning                                               |
| ------ | ------:| ----------------------------------------------------- |
| `0x00` | `0x10` | NUL-padded lowercase internal filename `.pd`          |
| `0x10` | `4`    | Version, observed as `1`                              |
| `0x14` | `8`    | Zero/reserved in files                                |
| `0x1c` | `4`    | Decompressed payload size, big-endian                 |
| `0x20` | ...    | zlib stream                                           |

## TDZ
Hypothesis for extension "*Texture Data Zlib*" 

`*.TDZ` files use the same `0x20`-byte zlib wrapper pattern as `*.PDZ`, but the internal file extension is usually `.td`.

| Offset | Size    | Meaning                                           |
| ------ | -------:| ------------------------------------------------- |
| `0x00` | `4`     | Entry count                                       |
| `0x04` | `4`     | Entry table offset, observed as `0x10`            |
| `0x08` | `4`     | Entry table end, equals `0x10 + entry_count * 8`  |
| `0x0c` | `4`     | First data/mesh-related offset or size-like value |
| `0x10` | `8 * n` | Entry records: `node_table_offset`, `node_count`  |

## MTZ
Hypothesis for extension "*Motion Table Zlib*" 

`.MTZ`: zlib-compressed motion/animation tables. 
The container header is `0x20` bytes: `0x00..0x0f` is a null-padded embedded `.dat` name, `0x10..0x13` is big-endian version `1`, `0x1c..0x1f` is the big-endian decompressed size, and the zlib stream starts at `0x20`.

Decompresses to `.dat`

## Credits
Wouldn't of been possible without the word over at mamedev with the taitotz driver source
https://github.com/mamedev/mame/blob/master/src/mame/taito/taitotz.cpp
