from __future__ import annotations

import argparse
import dataclasses
import json
import os.path
import sys

from winfont.helpers import parse_fonts_from_windows
from winfont.models import Char

STYLE_KEY = ("weight", "copyright", "charset", "italic", "underline", "strikeout", "inleading", "exleading")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", metavar="font-file", nargs="+")
    args = ap.parse_args()

    fonts_json_data = []

    for file in args.files:
        with open(file, "rb") as fp:
            for i, font in enumerate(parse_fonts_from_windows(fp.read())):
                font_json_data = dataclasses.asdict(font)
                font_json_data.pop("chars")
                font_json_data["src"] = (os.path.basename(file).lower(), i)
                font_json_data["copyright"] = font_json_data["copyright"].strip()
                if font_json_data["weight"] == 400:
                    font_json_data.pop("weight")
                for style_key in STYLE_KEY:
                    if not font_json_data.get(style_key):
                        font_json_data.pop(style_key, None)
                font_json_data["chars"] = [pack_char(char) for char in font.chars]
                fonts_json_data.append(font_json_data)

    fonts_json_data.sort(key=lambda font: (font["facename"], font["pointsize"]))
    json.dump(fonts_json_data, sys.stdout)


def pack_char(char: Char) -> tuple[int, int, dict | list[int]] | tuple[int, dict | list[int]] | int:
    """
    Pack a character into a fairly compact form.

    The forms are:

    * an integer (blank glyph)
    * a tuple of 2 entries (width, scanlines | R object)
    * a tuple of 3 entries (width, y offset, scanlines | R object)

    where the "R" object is a dictionary with a single entry, "r", which is a list of 2 integers; the first is the value of the scanline, and the second is the number of times it repeats.

    If `y_offset` is 0, it is omitted; if `y_offset` is non-zero, assume that `data` is offset by `y` lines.

    """
    data = char.data[:]
    while data and data[-1] == 0:
        data.pop()
    y = 0
    while data and data[0] == 0:
        data.pop(0)
        y += 1
    if not data:
        return char.width
    if all(data[0] == x for x in data):
        data = {"r": [data[0], len(data)]}
    if y != 0:
        return (char.width, y, data)
    return (char.width, data)


if __name__ == "__main__":  # pragma: no cover
    main()
