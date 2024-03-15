# SPDX-License-Identifier: MIT
# SPDX-File-CopyrightText: Copyright 2001 Simon Tatham
"""Generate Windows bitmap font files from a text description."""

import argparse

from winfont.fd import read_fd_to_font
from winfont.fnt import font_to_fnt_bytes
from winfont.fon import fnts_to_fon_bytes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--outfile")
    ap.add_argument("--facename")
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()

    fonts = []
    for fname in args.files:
        with open(fname) as fp:
            fonts.append(read_fd_to_font(fp))

    print(f"Read {len(fonts)} fonts")

    outfile = args.outfile
    if not outfile:
        print("No output file specified")
        return

    if outfile.endswith(".fnt"):
        if len(fonts) > 1:
            ap.error("Can only write one file to a .fnt; use a .fon for a family")
        with open(outfile, "wb") as fp:
            fp.write(font_to_fnt_bytes(fonts[0]))
    elif outfile.endswith(".fon"):
        if not args.facename:
            facenames = set(f.facename for f in fonts)
            if len(facenames) != 1:
                ap.error(f"Specify a face name explicitly; fonts have {facenames}")
            args.facename = facenames.pop()
        with open(outfile, "wb") as fp:
            fp.write(fnts_to_fon_bytes(args.facename, [font_to_fnt_bytes(f) for f in fonts]))
    else:
        ap.error(f"Unknown file type: {outfile}")


if __name__ == "__main__":  # pragma: no cover
    main()
