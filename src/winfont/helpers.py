from winfont.fnt import fnt_bytes_to_font
from winfont.fon import split_fon_bytes
from winfont.models import Font


def parse_fonts_from_windows(data: bytes) -> list[Font]:
    if data.startswith(b"MZ"):
        return [fnt_bytes_to_font(fnt_data) for fnt_data in split_fon_bytes(data)]
    return [fnt_bytes_to_font(data)]
