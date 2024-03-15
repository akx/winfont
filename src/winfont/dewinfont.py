# SPDX-License-Identifier: MIT
# SPDX-File-CopyrightText: Copyright 2001 Simon Tatham
"""Extract bitmap font data from a Windows .FON or .FNT file."""

import argparse

from winfont.fd import write_font_to_fd
from winfont.helpers import parse_fonts_from_windows


def main():  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--outfile")
    ap.add_argument("-p", "--prefix")
    ap.add_argument("file")
    args = ap.parse_args()

    with open(args.file, "rb") as fp:
        fonts = parse_fonts_from_windows(fp.read())

    for i, font in enumerate(fonts):
        print(font.facename, font.pointsize, end="")
        if args.outfile:
            if len(fonts) > 1:
                ap.error("more than one font in file; use -p prefix instead of -o outfile")
            fname = args.outfile
        elif args.prefix:
            fname = f"{args.prefix}{int(i):02}.fd"
        else:
            fname = None
        if fname:
            with open(fname, "w") as fp:
                write_font_to_fd(fonts[i], fp)
            print(" =>", fname, end="")
        print()


if __name__ == "__main__":
    main()
