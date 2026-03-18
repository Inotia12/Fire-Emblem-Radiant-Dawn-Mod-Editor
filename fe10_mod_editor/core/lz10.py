"""LZ10 compression and decompression for Nintendo DS/Wii binary formats."""

import struct


def decompress_lz10(data: bytes) -> bytes:
    """Decompress an LZ10-compressed byte string.

    LZ10 header: byte 0 = 0x10, bytes 1-3 = decompressed size (LE, 24-bit).
    """
    if data[0] != 0x10:
        raise ValueError("Not LZ10 compressed (first byte != 0x10)")

    decomp_size = struct.unpack('<I', data[1:4] + b'\x00')[0]
    output = bytearray()
    pos = 4

    while len(output) < decomp_size and pos < len(data):
        flags = data[pos]; pos += 1
        for bit in range(8):
            if len(output) >= decomp_size:
                break
            if flags & (0x80 >> bit):
                # Back-reference
                if pos + 1 >= len(data):
                    break
                b1, b2 = data[pos], data[pos + 1]; pos += 2
                length = ((b1 >> 4) & 0x0F) + 3
                offset = ((b1 & 0x0F) << 8) | b2
                offset += 1
                for _ in range(length):
                    if len(output) >= decomp_size:
                        break
                    output.append(output[-offset])
            else:
                # Literal byte
                if pos >= len(data):
                    break
                output.append(data[pos]); pos += 1

    return bytes(output[:decomp_size])


def compress_lz10(data: bytes) -> bytes:
    """Compress a byte string using LZ10 (brute-force sliding window)."""
    output = bytearray()
    size = len(data)

    # 4-byte header: 0x10 tag + 24-bit decompressed size (LE)
    output.append(0x10)
    output.append(size & 0xFF)
    output.append((size >> 8) & 0xFF)
    output.append((size >> 16) & 0xFF)

    pos = 0
    while pos < len(data):
        flag_byte_pos = len(output)
        output.append(0)
        flags = 0

        for bit in range(8):
            if pos >= len(data):
                break

            best_len = 0
            best_off = 0
            max_search = min(pos, 4096)
            max_len = min(len(data) - pos, 18)

            for off in range(1, max_search + 1):
                match_len = 0
                while (match_len < max_len and
                       data[pos + match_len] == data[pos - off + (match_len % off)]):
                    match_len += 1
                if match_len >= 3 and match_len > best_len:
                    best_len = match_len
                    best_off = off
                    if best_len == 18:
                        break

            if best_len >= 3:
                flags |= (0x80 >> bit)
                b1 = ((best_len - 3) << 4) | (((best_off - 1) >> 8) & 0x0F)
                b2 = (best_off - 1) & 0xFF
                output.append(b1)
                output.append(b2)
                pos += best_len
            else:
                output.append(data[pos])
                pos += 1

        output[flag_byte_pos] = flags

    return bytes(output)
