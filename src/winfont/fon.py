# SPDX-License-Identifier: MIT
# SPDX-File-CopyrightText: Copyright 2001 Simon Tatham
"""Read and write .FON font library files."""

from collections.abc import Iterable

from winfont.util import asciz, byte, dword, fromdword, fromword, word


def direntry(f):
    """Return the FONTDIRENTRY, given the data in a .FNT file."""
    device = fromdword(f[0x65:])
    face = fromdword(f[0x69:])
    if device == 0:
        devname = b""
    else:
        devname = asciz(f[device:])
    facename = asciz(f[face:])
    return f[0:0x71] + devname + b"\0" + facename + b"\0"


stubcode = [
    0xBA,
    0x0E,
    0x00,  # mov dx,0xe
    0x0E,  # push cs
    0x1F,  # pop ds
    0xB4,
    0x09,  # mov ah,0x9
    0xCD,
    0x21,  # int 0x21
    0xB8,
    0x01,
    0x4C,  # mov ax,0x4c01
    0xCD,
    0x21,  # int 0x21
]
stubmsg = b"This is not a program!\r\nFont library created by mkwinfont.\r\n"


def stub():
    """Create a small MZ executable."""
    file = b""
    file = file + b"MZ" + word(0) + word(0)
    file = file + word(0)  # no relocations
    file = file + word(4)  # 4-para header
    file = file + word(0x10)  # 16 extra para for stack
    file = file + word(0xFFFF)  # maximum extra paras: LOTS
    file = file + word(0) + word(0x100)  # SS:SP = 0000:0100
    file = file + word(0)  # no checksum
    file = file + word(0) + word(0)  # CS:IP = 0:0, start at beginning
    file = file + word(0x40)  # reloc table beyond hdr
    file = file + word(0)  # overlay number
    file = file + 4 * word(0)  # reserved
    file = file + word(0) + word(0)  # OEM id and OEM info
    file = file + 10 * word(0)  # reserved
    file = file + dword(0)  # offset to NE header
    assert len(file) == 0x40
    for i in stubcode:
        file = file + byte(i)
    file = file + stubmsg + b"$"
    n = len(file)
    # pages = (n+511) / 512
    pages = (n + 511) // 512
    lastpage = n - (pages - 1) * 512
    file = file[:2] + word(lastpage) + word(pages) + file[6:]
    # Now assume there will be a NE header. Create it and fix up the
    # offset to it.
    while len(file) % 16:
        file = file + b"\0"
    file = file[:0x3C] + dword(len(file)) + file[0x40:]
    return file


def fnts_to_fon_bytes(name: str, fnts: list[bytes]) -> bytes:
    """Create a .FON font library, given a bunch of .FNT file contents."""
    name = bytes(name, encoding="windows-1252")

    # Construct the FONTDIR.
    fontdir = word(len(fnts))
    for i in range(len(fnts)):
        fontdir = fontdir + word(i + 1)
        fontdir = fontdir + direntry(fnts[i])

    # The MZ stub.
    stubdata = stub()
    # Non-resident name table should contain a FONTRES line.
    nonres = b"FONTRES 100,96,96 : " + name
    nonres = byte(len(nonres)) + nonres + b"\0\0\0"
    # Resident name table should just contain a module name.
    mname = b""
    for c in name:
        if c in b"0123546789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz":
            mname = mname + bytes([c])
    res = byte(len(mname)) + mname + b"\0\0\0"
    # Entry table / imported names table should contain a zero word.
    entry = word(0)

    # Compute length of resource table.
    # 12 (2 for the shift count, plus 2 for end-of-table, plus 8 for the
    #    "FONTDIR" resource name), plus
    # 20 for FONTDIR (TYPEINFO and NAMEINFO), plus
    # 8 for font entry TYPEINFO, plus
    # 12 for each font's NAMEINFO

    # Resources are currently one FONTDIR plus n fonts.
    # TODO: a VERSIONINFO resource would be nice too.
    resrcsize = 12 + 20 + 8 + 12 * len(fnts)
    resrcpad = ((resrcsize + 15) & ~15) - resrcsize

    # Now position all of this after the NE header.
    p = 0x40  # NE header size
    off_segtable = off_restable = p
    p = p + resrcsize + resrcpad
    off_res = p
    p = p + len(res)
    off_modref = off_import = off_entry = p
    p = p + len(entry)
    off_nonres = p
    p = p + len(nonres)

    pad = ((p + 15) & ~15) - p
    p = p + pad
    q = p + len(stubdata)

    # Now q is file offset where the real resources begin. So we can
    # construct the actual resource table, and the resource data too.
    restable = word(4)  # shift count
    resdata = b""
    # The FONTDIR resource.
    restable = restable + word(0x8007) + word(1) + dword(0)
    restable = restable + word((q + len(resdata)) >> 4)
    start = len(resdata)
    resdata = resdata + fontdir
    while len(resdata) % 16:
        resdata = resdata + b"\0"
    restable = restable + word((len(resdata) - start) >> 4)
    restable = restable + word(0x0C50) + word(resrcsize - 8) + dword(0)
    # The font resources.
    restable = restable + word(0x8008) + word(len(fnts)) + dword(0)
    for i in range(len(fnts)):
        restable = restable + word((q + len(resdata)) >> 4)
        start = len(resdata)
        resdata = resdata + fnts[i]
        while len(resdata) % 16:
            resdata = resdata + b"\0"
        restable = restable + word((len(resdata) - start) >> 4)
        restable = restable + word(0x1C30) + word(0x8001 + i) + dword(0)
    # The zero word.
    restable = restable + word(0)
    assert len(restable) == resrcsize - 8
    restable = restable + b"\007FONTDIR"
    restable = restable + b"\0" * resrcpad

    file = stubdata + b"NE" + byte(5) + byte(10)
    file = file + word(off_entry) + word(len(entry))
    file = file + dword(0)  # no CRC
    file = file + word(0x8308)  # the Mysterious Flags
    file = file + word(0) + word(0) + word(0)  # no autodata, no heap, no stk
    file = file + dword(0) + dword(0)  # CS:IP == SS:SP == 0
    file = file + word(0) + word(0)  # segment table len, modreftable len
    file = file + word(len(nonres))
    file = file + word(off_segtable) + word(off_restable)
    file = file + word(off_res) + word(off_modref) + word(off_import)
    file = file + dword(len(stubdata) + off_nonres)
    file = file + word(0)  # no movable entries
    file = file + word(4)  # seg align shift count
    file = file + word(0)  # no resource segments
    file = file + byte(2) + byte(8)  # target OS and more Mysterious Flags
    file = file + word(0) + word(0) + word(0) + word(0x300)

    # Now add in all the other stuff.
    file = file + restable + res + entry + nonres + b"\0" * pad + resdata

    return file


def get_fnts_from_ne(fon: bytes, neoff: int):
    """Finish splitting up a NE-format FON file."""
    # Find the resource table.
    rtable = fromword(fon[neoff + 0x24 :])
    rtable = rtable + neoff
    # Read the shift count out of the resource table.
    shift = fromword(fon[rtable:])
    # Now loop over the rest of the resource table.
    p = rtable + 2
    while 1:
        rtype = fromword(fon[p:])
        if rtype == 0:
            break  # end of resource table
        count = fromword(fon[p + 2 :])
        p = p + 8  # type, count, 4 bytes reserved
        for _i in range(count):
            start = fromword(fon[p:]) << shift
            size = fromword(fon[p + 2 :]) << shift
            if start < 0 or size < 0 or start + size > len(fon):
                raise ValueError("Resource overruns file boundaries")
            if rtype == 0x8008:  # this is an actual font
                # print "Font at", start, "size", size
                yield fon[start : start + size]
            p = p + 12  # start, size, flags, name/id, 4 bytes reserved


def get_fnts_from_pe(fon, peoff):
    """Finish splitting up a PE-format FON file."""
    dirtables = []
    dataentries = []

    def gotoffset(off, dirtables=dirtables, dataentries=dataentries) -> None:
        if off & 0x80000000:
            off = off & ~0x80000000
            dirtables.append(off)
        else:
            dataentries.append(off)

    def dodirtable(rsrc, off, rtype, gotoffset=gotoffset) -> None:
        number = fromword(rsrc[off + 12 :]) + fromword(rsrc[off + 14 :])
        for i in range(number):
            entry = off + 16 + 8 * i
            thetype = fromdword(rsrc[entry:])
            theoff = fromdword(rsrc[entry + 4 :])
            if rtype == -1 or rtype == thetype:
                gotoffset(theoff)

    # We could try finding the Resource Table entry in the Optional
    # Header, but it talks about RVAs instead of file offsets, so
    # it's probably easiest just to go straight to the section table.
    # So let's find the size of the Optional Header, which we can
    # then skip over to find the section table.
    secentries = fromword(fon[peoff + 0x06 :])
    sectable = peoff + 0x18 + fromword(fon[peoff + 0x14 :])
    for i in range(secentries):
        secentry = sectable + i * 0x28
        secname = asciz(fon[secentry : secentry + 8])
        secrva = fromdword(fon[secentry + 0x0C :])
        secsize = fromdword(fon[secentry + 0x10 :])
        secptr = fromdword(fon[secentry + 0x14 :])
        if secname == b".rsrc":
            break
    else:
        raise ValueError("Unable to locate resource section\n")
    # Now we've found the resource section, let's throw away the rest.
    rsrc = fon[secptr : secptr + secsize]

    # Now the fun begins. To start with, we must find the initial
    # Resource Directory Table and look up type 0x08 (font) in it.
    # If it yields another Resource Directory Table, we stick the
    # address of that on a list. If it gives a Data Entry, we put
    # that in another list.
    dodirtable(rsrc, 0, 0x08)
    # Now process Resource Directory Tables until no more remain
    # in the list. For each of these tables, we accept _all_ entries
    # in it, and if they point to subtables we stick the subtables in
    # the list, and if they point to Data Entries we put those in
    # the other list.
    while len(dirtables) > 0:
        table = dirtables[0]
        del dirtables[0]
        dodirtable(rsrc, table, -1)  # accept all entries
    # Now we should be left with Resource Data Entries. Each of these
    # describes a font.
    ret = []
    for off in dataentries:
        rva = fromdword(rsrc[off:])
        start = rva - secrva
        size = fromdword(rsrc[off + 4 :])
        yield rsrc[start : start + size]
    return ret


def split_fon_bytes(fon: bytes) -> Iterable[bytes]:
    """Split a .FON up into .FNT data."""
    if not fon.startswith(b"MZ"):
        raise ValueError("MZ signature not found")
    # Find the NE header.
    neoff = fromdword(fon[0x3C:])
    if fon[neoff : neoff + 2] == b"NE":
        return get_fnts_from_ne(fon, neoff)
    if fon[neoff : neoff + 4] == b"PE\0\0":
        return get_fnts_from_pe(fon, neoff)
    raise ValueError("NE or PE signature not found")
