"""Versioned interpretation of a 256-bit Wi-Fi monster genome.

V1 remains readable. V2 makes every access point a monster identity, balances
the six types, separates optional-part presence from part shape, and exposes
all sixteen semantic palettes. Events and biomes are generated from a separate
Wi-Fi environment snapshot in wifi_world.py.
"""
from versions import GENE_SCHEMA_VERSION, SUPPORTED_GENE_SCHEMAS

GENOME_BITS = 256

FIELD_LAYOUT_V1 = (
    ('encounter_kind', 0, 1), ('type_code', 1, 3),
    ('head', 4, 4), ('body', 8, 4), ('arms', 12, 4), ('legs', 16, 4),
    ('horns', 20, 4), ('tail', 24, 4), ('eyes', 28, 4), ('wings', 32, 4),
    ('palette_code', 36, 4), ('biome_roll', 40, 8), ('event_roll', 48, 8),
    ('encounter_variant', 56, 8), ('dungeon_theme', 64, 4),
    ('dungeon_layout', 68, 4), ('dungeon_reward_code', 72, 4),
    ('dungeon_difficulty_code', 76, 4), ('xp_roll', 80, 8),
    ('item_code', 88, 4), ('item_amount_code', 92, 4),
    ('personality', 96, 4), ('temperament', 100, 4), ('rare_trait', 104, 8),
)
USED_BITS_V1 = 112
RESERVED_BITS_V1 = GENOME_BITS - USED_BITS_V1

# V2 is deliberately compact. The remaining 184 bits can be assigned without
# moving an existing field; incompatible changes require a V3 decoder.
FIELD_LAYOUT_V2 = (
    ('type_roll', 0, 8),
    ('head', 8, 4), ('body', 12, 4), ('arms', 16, 4), ('legs', 20, 4),
    ('horns', 24, 4), ('tail', 28, 4), ('eyes', 32, 4), ('wings', 36, 4),
    ('palette_code', 40, 4), ('optional_mask', 44, 3), ('shape_trait', 47, 1),
    ('personality', 48, 4), ('temperament', 52, 4), ('rare_trait', 56, 8),
    ('combat_trait', 64, 4), ('lineage_tendency', 68, 4),
)
USED_BITS_V2 = 72
RESERVED_BITS_V2 = GENOME_BITS - USED_BITS_V2

EVENT_TABLE_V1 = ((115, 'experience'), (218, 'item'), (256, 'dungeon'))


def read_bits(raw, offset, width):
    if offset < 0 or width < 1 or offset + width > len(raw) * 8:
        raise ValueError('gene field outside genome')
    value = 0
    for position in range(offset, offset + width):
        value = (value << 1) | ((raw[position // 8] >> (7 - position % 8)) & 1)
    return value


def write_bits(raw, offset, width, value):
    if offset < 0 or width < 1 or offset + width > len(raw) * 8 or not 0 <= value < (1 << width):
        raise ValueError('invalid gene field')
    for index, position in enumerate(range(offset, offset + width)):
        bit = (value >> (width - 1 - index)) & 1
        mask = 1 << (7 - position % 8)
        if bit: raw[position // 8] |= mask
        else: raw[position // 8] &= 255 ^ mask


def _event_name(value):
    for upper, name in EVENT_TABLE_V1:
        if value < upper: return name
    raise ValueError('invalid event roll')


def _fields(raw, layout):
    if len(raw) != 32: raise ValueError('a Wi-Fi genome must be 32 bytes')
    return {name: read_bits(raw, offset, width) for name, offset, width in layout}


def _decode_v1(raw):
    values = _fields(raw, FIELD_LAYOUT_V1)
    values['schema_version'] = 1
    values['type'] = values['type_code'] % 6
    values['parts'] = [values[name] for name in
                       ('head','body','arms','legs','horns','tail','eyes','wings')]
    values['present'] = [True, True, True, True, values['horns'] != 0,
                         values['tail'] != 0, True, values['wings'] != 0]
    values['palette'] = values['palette_code'] * 3 // 16
    values['biome'] = values['biome_roll'] * 7 // 256
    values['event_kind'] = ('battle' if values['encounter_kind'] == 0
                            else _event_name(values['event_roll']))
    values['enemy_level_delta'] = values['encounter_variant'] % 3 - 1
    values['xp_amount'] = 10 + values['xp_roll'] * 31 // 256
    values['item_amount'] = 1 + values['item_amount_code'] * 4 // 16
    values['dungeon_reward'] = values['dungeon_reward_code'] % 4
    values['dungeon_difficulty'] = 1 + values['dungeon_difficulty_code'] * 3 // 16
    values['combat_trait'] = values['rare_trait'] & 15
    values['lineage_tendency'] = values['temperament']
    return values


def _decode_v2(raw):
    values = _fields(raw, FIELD_LAYOUT_V2)
    values['schema_version'] = 2
    values['type'] = values['type_roll'] * 6 // 256
    values['parts'] = [values[name] for name in
                       ('head','body','arms','legs','horns','tail','eyes','wings')]
    mask = values['optional_mask']
    values['present'] = [True, True, True, True, bool(mask & 4),
                         bool(mask & 2), True, bool(mask & 1)]
    values['palette'] = values['palette_code']
    return values


DECODERS = {1: _decode_v1, 2: _decode_v2}


def decode(raw, version=GENE_SCHEMA_VERSION):
    decoder = DECODERS.get(version)
    if decoder is None: raise ValueError('unsupported gene schema')
    return decoder(raw)


def supported(version):
    return version in SUPPORTED_GENE_SCHEMAS and version in DECODERS


def type_roll(kind):
    if not 0 <= kind < 6: raise ValueError('invalid monster type')
    return min(255, (kind * 256 + 128) // 6)


def encode_v2(seed, kind, parts, palette, present=None, personality=0,
              temperament=0, rare_trait=0, combat_trait=0, lineage_tendency=0):
    """Return a V2 genome while retaining unused entropy from seed."""
    if len(seed) != 32 or len(parts) != 8: raise ValueError('invalid genome template')
    raw = bytearray(seed)
    values = {'type_roll':type_roll(kind), 'palette_code':palette,
              'personality':personality, 'temperament':temperament,
              'rare_trait':rare_trait, 'combat_trait':combat_trait,
              'lineage_tendency':lineage_tendency, 'shape_trait':raw[5] & 1}
    for name, value in zip(('head','body','arms','legs','horns','tail','eyes','wings'), parts):
        values[name] = value
    if present is None: present = [True] * 8
    values['optional_mask'] = ((4 if present[4] else 0) |
                               (2 if present[5] else 0) |
                               (1 if present[7] else 0))
    for name, offset, width in FIELD_LAYOUT_V2:
        if name in values: write_bits(raw, offset, width, int(values[name]))
    return bytes(raw)


def validate_layout(layout=None):
    layout = FIELD_LAYOUT_V2 if layout is None else layout
    names, occupied = set(), set()
    for name, offset, width in layout:
        if name in names or offset < 0 or width < 1 or offset + width > GENOME_BITS: return False
        names.add(name); bits = set(range(offset, offset + width))
        if bits & occupied: return False
        occupied |= bits
    return True
