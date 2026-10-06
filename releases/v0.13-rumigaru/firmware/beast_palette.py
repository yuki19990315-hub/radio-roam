"""Readable fur, cream muzzle/chest and amber eyes for the new beast art."""
from part_catalog import _BASE_PALETTES

def colors(index):
    c=_BASE_PALETTES[index%len(_BASE_PALETTES)]
    return (c[0],c[1],c[2],c[3],c[4],(204,180,145),(248,232,192),
            c[3],(238,173,54),c[4],c[4],(255,255,245))
