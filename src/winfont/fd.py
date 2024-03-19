# SPDX-License-Identifier: MIT
# SPDX-File-CopyrightText: Copyright 2001 Simon Tatham
"""Read and write .fd font description files."""

import typing

from winfont.models import Char, Font
from winfont.util import bool_to_str

FD_TRANSLATE = {ord("."): "0", ord("-"): "0", ord("x"): "1", ord("#"): "1"}

INTEGER_ATTRS_MAP = {
    "ascent": "ascent",
    "charset": "charset",
    "exleading": "exleading",
    "font_width": "width",
    "height": "height",
    "inleading": "inleading",
    "pointsize": "pointsize",
    "res_x": "res_x",
    "res_y": "res_y",
    "weight": "weight",
}

BOOL_ATTRS_MAP = {
    "italic": "italic",
    "underline": "underline",
    "strikeout": "strikeout",
}


def write_font_to_fd(f: Font, file: typing.IO[str]) -> None:
    """Write out a .fd form of an internal font description."""
    file.write("# .fd font description generated by dewinfont.\n\n")
    file.write(f"facename {f.facename}\n")
    file.write(f"copyright {f.copyright}\n\n")
    for file_attr, font_attr in sorted(INTEGER_ATTRS_MAP.items()):
        file.write(f"{file_attr} {getattr(f, font_attr)}\n")
    for file_attr, font_attr in sorted(BOOL_ATTRS_MAP.items()):
        file.write(f"{file_attr} {bool_to_str(getattr(f, font_attr))}\n")
    for i in range(256):
        file.write(f"char {int(i)}\nwidth {int(f.chars[i].width)}\n")
        if f.chars[i].width != 0:
            for j in range(f.height):
                v = f.chars[i].data[j]
                m = 1 << (f.chars[i].width - 1)
                for _k in range(f.chars[i].width):
                    if v & m:
                        file.write("x")  # "1")
                    else:
                        file.write(".")  # "0")
                    v = v << 1
                file.write("\n")
        file.write("\n")


def read_fd_to_font(fp: typing.IO) -> Font:
    """Load a font description from an FD text file."""
    f = Font(
        copyright="(unknown)",
        facename="(unknown)",
        width=0,
        height=0,
        ascent=0,
        pointsize=0,
        chars=[],
    )
    chars = {}

    lineno = 0
    while 1:
        s = fp.readline()
        if s == "":
            break
        lineno = lineno + 1
        s = s.rstrip("\r\n").lstrip(" ")
        if s == "" or s[0:1] == "#":
            continue
        # space = string.find(s, " ")
        space = s.find(" ")
        if space == -1:
            space = len(s)
        w = s[:space]
        a = s[space + 1 :]
        if w == "copyright":
            if len(a) > 59:
                raise ValueError("Copyright too long")
            f.copyright = a
            continue
        if w == "facename":
            f.facename = a
            continue
        if w in INTEGER_ATTRS_MAP:
            setattr(f, INTEGER_ATTRS_MAP[w], int(a))
            continue
        if w in BOOL_ATTRS_MAP:
            setattr(f, BOOL_ATTRS_MAP[w], a == "yes")
            continue
        if w == "char":
            char_index = int(a)
            data_y = 0
            chars[char_index] = Char(width=0, data=[0] * f.height)
            continue
        if w == "width":
            chars[char_index].width = int(a)
            continue
        try:
            w = w.translate(FD_TRANSLATE)
            value = int(w, 2)
            bits = len(w)
            if bits < chars[char_index].width:
                value = value << (chars[char_index].width - bits)
            elif bits > chars[char_index].width:
                value = value >> (bits - chars[char_index].width)
            chars[char_index].data[data_y] = value
            data_y += 1
        except ValueError as ve:
            raise ValueError(f"Unknown keyword {w} at line {int(lineno)}\n") from ve

    if not f.pointsize:
        # hightish * 72 ppi / nominal vertical resolution dpi
        f.pointsize = round((f.height - f.inleading) * 72 / 96)

    missing_chars = {i for i in range(256)} - set(chars)
    if missing_chars:
        raise ValueError(f"Missing characters {missing_chars}\n")
    f.chars = [chars[i] for i in range(256)]
    return f
