# SPDX-License-Identifier: MIT
# SPDX-File-CopyrightText: Copyright 2001 Simon Tatham


def frombyte(s: bytes) -> int:
    return s[0]


def fromword(s: bytes) -> int:
    return frombyte(s[0:1]) + 256 * frombyte(s[1:2])


def fromdword(s: bytes) -> int:
    return fromword(s[0:2]) | (fromword(s[2:4]) << 16)


def asciz(s):
    return s.partition(b"\0")[0]


def bool_to_str(val) -> str:
    return "yes" if val else "no"


def byte(i: int) -> bytes:
    return bytes([i & 0xFF])


def word(i: int) -> bytes:
    return byte(i) + byte(i >> 8)


def dword(i: int) -> bytes:
    return word(i) + word(i >> 16)
