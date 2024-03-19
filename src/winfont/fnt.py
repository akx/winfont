# SPDX-License-Identifier: MIT
# SPDX-File-CopyrightText: Copyright 2001 Simon Tatham
"""Read and write .FNT font files."""

import struct

from winfont.models import Char, Font
from winfont.util import asciz, byte, dword, frombyte, fromdword, fromword, word


def fnt_bytes_to_font(fnt: bytes) -> Font:
    """Create an internal font description from a .FNT-shaped string."""
    (
        version,
        size,
        copyright_bytes,
        ftype,
        pointsize,
        res_y,
        res_x,
        ascent,
        inleading,
        exleading,
        italic,
        underline,
        strikeout,
        weight,
        charset,
        width,
        height,
        pitchfamily,
        avgwidth,
        maxwidth,
        firstchar,
        lastchar,
        defaultchar,
        breakchar,
        widthbytes,
        deviceptr,
        off_facename,
        bitsptr,
    ) = struct.unpack(
        "< "
        "H I 60s "  # version, size, copyright
        "H H H H "  # ftype, pointsize, res_y, res_x
        "H H H "  # ascent, inleading, exleading
        "? ? ? "  # italic, underline, strikeout
        "H B H H"  # weight, charset, width, height
        "B H H"  # pitch-and-family, avg width, max width
        "B B B B"  # first char, last char, default char, break char
        "H I I I",  # widthbytes, device-ptr, facename-ptr, bits-ptr
        fnt[:113],
    )

    if ftype & 1:
        raise Exception("This font is a vector font")
    if off_facename < 0 or off_facename > len(fnt):
        raise Exception("Face name not contained within font data")

    copyright = copyright_bytes.rstrip(b"\0").decode("windows-1252")
    facename = str(asciz(fnt[off_facename:]), encoding="windows-1252")

    # Read the char table.
    if version == 0x200:
        ctstart = 0x76
        ctsize = 4
    else:
        ctstart = 0x94
        ctsize = 6
    chars = [Char(width=0, data=[0] * height) for i in range(256)]
    for i in range(firstchar, lastchar + 1):
        entry = ctstart + ctsize * (i - firstchar)
        w = fromword(fnt[entry:])
        chars[i].width = w
        if ctsize == 4:
            off = fromword(fnt[entry + 2 :])
        else:
            off = fromdword(fnt[entry + 2 :])
        widthbytes = (w + 7) // 8
        for j in range(height):
            for k in range(widthbytes):
                bytepos = off + k * height + j
                chars[i].data[j] = chars[i].data[j] << 8
                chars[i].data[j] = chars[i].data[j] | frombyte(fnt[bytepos:])
            chars[i].data[j] = chars[i].data[j] >> (8 * widthbytes - w)
    return Font(
        ascent=ascent,
        chars=chars,
        charset=charset,
        copyright=copyright,
        exleading=exleading,
        facename=facename,
        height=height,
        res_x=res_x,
        inleading=inleading,
        italic=italic,
        pointsize=pointsize,
        strikeout=strikeout,
        underline=underline,
        res_y=res_y,
        weight=weight,
        width=width,
    )


def font_to_fnt_bytes(font: Font) -> bytes:
    """Generate the contents of a .FNT file, given a font description."""
    # Average width is defined by Windows to be the width of 'X'.
    avgwidth = font.chars[ord("X")].width
    # Max width we calculate from the font. During this loop we also
    # check if the font is fixed-pitch.
    maxwidth = 0
    fixed = 1
    for i in range(0, 256):
        if avgwidth != font.chars[i].width:
            fixed = 0
        if maxwidth < font.chars[i].width:
            maxwidth = font.chars[i].width
    # Work out how many 8-pixel wide columns we need to represent a char.
    # widthbytes = 3 # FIXME!
    # widthbytes = (maxwidth+7)/8
    # widthbytes = (widthbytes+1) &~ 1  # round up to multiple of 2
    widthbytes = ((maxwidth - 1) // 16 + 1) * 2

    file = b""
    file = file + word(0x0300)  # file version
    file = file + dword(0)  # file size (come back and fix later)
    copyright = font.copyright + ("\0" * 60)
    copyright = copyright[0:60]
    file = file + bytes(copyright, encoding="windows-1252")
    file = file + word(0)  # font type (raster, bits in file)
    file = file + word(font.pointsize)  # nominal point size
    file = file + word(96)  # nominal vertical resolution (dpi)
    file = file + word(96)  # nominal horizontal resolution (dpi)
    file = file + word(font.ascent)  # top of font <--> baseline
    file = file + word(font.inleading)  # internal leading
    file = file + word(font.exleading)  # external leading
    file = file + byte(font.italic)
    file = file + byte(font.underline)
    file = file + byte(font.strikeout)
    file = file + word(font.weight)  # 1 to 1000 (100-900); 400 is normal.
    file = file + byte(font.charset)
    if fixed:
        pixwidth = avgwidth
    else:
        pixwidth = 0
    file = file + word(pixwidth)  # width, or 0 if var-width
    file = file + word(font.height)  # height
    if fixed:
        pitchfamily = 0
    else:
        pitchfamily = 1
    file = file + byte(pitchfamily)  # pitch and family
    file = file + word(avgwidth)
    file = file + word(maxwidth)
    file = file + byte(0)  # first char
    file = file + byte(255)  # last char
    file = file + byte(63)  # default char "?" (relative to first char)
    file = file + byte(32)  # break char (relative to first char)
    file = file + word(widthbytes)  # dfWidthBytes
    file = file + dword(0)  # device
    file = file + dword(0)  # face name
    file = file + dword(0)  # BitsPointer (used at load time)
    file = file + dword(0)  # pointer to bitmap data
    file = file + byte(0)  # reserved
    if fixed:
        dfFlags = 1
    else:
        dfFlags = 2
    file = file + dword(dfFlags)  # dfFlags
    file = file + word(0) + word(0) + word(0)  # Aspace, Bspace, Cspace
    file = file + dword(0)  # colour pointer
    file = file + (b"\0" * 16)  # dfReserved1

    # Now the char table.
    offset_chartbl = len(file)
    offset_bitmaps = offset_chartbl + 257 * 6
    # Fix up the offset-to-bitmaps at 0x71.
    file = file[:0x71] + dword(offset_bitmaps) + file[0x71 + 4 :]
    bitmaps = b""
    for i in range(0, 257):
        if i < 256:
            width = font.chars[i].width
        else:
            width = avgwidth
        file = file + word(width)
        file = file + dword(offset_bitmaps + len(bitmaps))
        for j in range(widthbytes):
            for k in range(font.height):
                if i < 256:
                    chardata = font.chars[i].data[k]
                else:
                    chardata = 0
                chardata = chardata << (8 * widthbytes - width)
                bitmaps = bitmaps + byte(chardata >> (8 * (widthbytes - j - 1)))

    file = file + bitmaps
    # Now the face name. Fix up the face name offset at 0x69.
    file = file[:0x69] + dword(len(file)) + file[0x69 + 4 :]
    file = file + bytes(font.facename, encoding="windows-1252") + b"\0"
    # And finally fix up the file size at 0x2.
    file = file[:0x2] + dword(len(file)) + file[0x2 + 4 :]

    # Done.
    return file
