import struct
# Private 128-bit service UUID, little-endian bytes; no vendor company ID.
UUID = bytes.fromhex('9b37b44e725547c59b5816a6f9ab041e')


def advertise(token, species):
    body = UUID + struct.pack('<BIB', 1, token, species)
    return b'\x02\x01\x06' + bytes((len(body) + 1, 0x21)) + body


def parse(payload):
    i = 0
    while i < len(payload):
        n = payload[i]
        if n == 0:
            break
        if i + n + 1 > len(payload):
            return None
        if payload[i+1] == 0x21:
            body = payload[i+2:i+n+1]
            if len(body) == 22 and body[:16] == UUID:
                version, token, species = struct.unpack('<BIB', body[16:])
                if version == 1 and species < 32:
                    return token, species
        i += n + 1
    return None
