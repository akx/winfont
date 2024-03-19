import dataclasses


@dataclasses.dataclass
class Char:
    width: int
    data: list[int]


@dataclasses.dataclass
class Font:
    facename: str
    copyright: str
    pointsize: int
    width: int
    height: int
    ascent: int
    res_x: int = 0
    res_y: int = 0
    inleading: int = 0
    exleading: int = 0
    italic: bool = False
    underline: bool = False
    strikeout: bool = False
    weight: int = 400
    charset: int = 0
    chars: list[Char] = dataclasses.field(default_factory=list)
