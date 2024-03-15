import io
import pathlib

import pytest
from winfont.fd import read_fd_to_font, write_font_to_fd
from winfont.fnt import fnt_bytes_to_font, font_to_fnt_bytes
from winfont.fon import fnts_to_fon_bytes
from winfont.helpers import parse_fonts_from_windows

fonts_path = pathlib.Path(__file__).parent.parent / "fonts"


@pytest.mark.parametrize("path", sorted(fonts_path.glob("*.fon")), ids=lambda p: p.stem)
def test_winfont(path):
    fonts = parse_fonts_from_windows(path.read_bytes())
    font_fnts = []
    assert fonts
    for font in fonts:
        sio = io.StringIO()
        write_font_to_fd(font, sio)
        sio.seek(0)
        assert read_fd_to_font(sio) == font  # roundtrip
        fnt_bytes = font_to_fnt_bytes(font)
        assert fnt_bytes_to_font(fnt_bytes) == font  # roundtrip
        font_fnts.append(fnt_bytes)
    fon_bytes = fnts_to_fon_bytes(fonts[0].facename, font_fnts)
    assert list(parse_fonts_from_windows(fon_bytes)) == fonts  # roundtrip
