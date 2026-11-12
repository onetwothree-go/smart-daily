"""生成 Windows .ico 图标（纯 Python，无第三方依赖）。

为什么自己写：
    沙箱禁止 COM（WScript.Shell）且环境无 PIL，但桌面启动器需要像"软件"的图标。
    ICO 格式足够简单——一个 BITMAPINFOHEADER + BGRA 像素 + AND 掩码，手写即可。

用法：
    python make_icon.py <输出.ico> <十六进制颜色RRGGBB> <字符> [尺寸]

设计：
    圆角方形纯色底 + 居中白色字符（内置 5x7 点阵字体，覆盖 A-Z 与 0-9）。
"""

from __future__ import annotations

import struct
import sys

# ---------------------------------------------------------------- 5x7 点阵字体
# 每字符 7 行，每行 5 位（1=实心）。横向 bit4..bit0 对应左..右。
_FONT: dict[str, list[int]] = {
    "A": [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    "B": [0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
    "C": [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
    "D": [0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110],
    "E": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
    "F": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
    "G": [0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01110],
    "H": [0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    "I": [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "J": [0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100],
    "K": [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
    "L": [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    "M": [0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001],
    "N": [0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001],
    "O": [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "P": [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    "Q": [0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10011, 0b01111],
    "R": [0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
    "S": [0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110],
    "T": [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    "U": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "V": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    "W": [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
    "X": [0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
    "Y": [0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
    "Z": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
    "0": [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
    "1": [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "2": [0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111],
    "3": [0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110],
    "4": [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    "5": [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    "6": [0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    "7": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    "8": [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    "9": [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100],
    # 兜底字形：空心方框（用于字体表未覆盖的字符，如中文）
    "?": [0b11111, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11111],
}

_CORNER = 6  # 圆角半径（32px 画布下约 19%）


def _in_rounded_rect(x: int, y: int, w: int, h: int, r: int) -> bool:
    """判断点 (x,y) 是否落在圆角矩形内。"""
    if x < r and y < r:  # 左上
        return (x - r) ** 2 + (y - r) ** 2 <= r * r
    if x >= w - r and y < r:  # 右上
        return (x - (w - r - 1)) ** 2 + (y - r) ** 2 <= r * r
    if x < r and y >= h - r:  # 左下
        return (x - r) ** 2 + (y - (h - r - 1)) ** 2 <= r * r
    if x >= w - r and y >= h - r:  # 右下
        return (x - (w - r - 1)) ** 2 + (y - (h - r - 1)) ** 2 <= r * r
    return True


def build_icon(size: int, rgb: tuple[int, int, int], char: str) -> bytes:
    """渲染 32bpp RGBA 位图并封装为 ICO（BGRA，底部在上）。"""
    r, g, b = rgb
    glyph = _FONT.get(char.upper(), _FONT["?"])
    # 字符在画布中的起始坐标：5x7 点阵放大 3 倍 -> 15x21，居中
    scale = max(1, size // 11)
    gw, gh = 5 * scale, 7 * scale
    ox, oy = (size - gw) // 2, (size - gh) // 2

    pixels = bytearray()
    for y in range(size - 1, -1, -1):  # BMP 行序自下而上
        for x in range(size):
            inside = _in_rounded_rect(x, y, size, size, _CORNER)
            if not inside:
                pixels += b"\x00\x00\x00\x00"
                continue
            # 判断是否命中字符笔画
            gx, gy = (x - ox) // scale, (y - oy) // scale
            on = False
            if 0 <= gx < 5 and 0 <= gy < 7:
                row = glyph[gy]
                on = bool(row & (1 << (4 - gx)))
            if on:
                pixels += bytes((0xFF, 0xFF, 0xFF, 0xFF))  # 白色字符
            else:
                pixels += bytes((b, g, r, 0xFF))  # 底色（BGRA）
    xor = bytes(pixels)

    # AND 掩码：1bpp，32bpp 已有 alpha，全部填 0 表示不透明
    row_bytes = ((size + 31) // 32) * 4
    mask = b"\x00" * (row_bytes * size)

    # BITMAPINFOHEADER：高度取双倍（XOR + AND）
    bih = struct.pack(
        "<IiiHHIIiiII",
        40, size, size * 2, 1, 32, 0, 0, 0, 0, 0, 0,
    )
    image = bih + xor + mask

    # ICONDIR + ICONDIRENTRY
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack(
        "<BBBBHHII",
        size if size < 256 else 0,
        size if size < 256 else 0,
        0, 0, 1, 32, len(image), 6 + 16,
    )
    return header + entry + image


def main() -> int:
    if len(sys.argv) < 4:
        print("用法: python make_icon.py <输出.ico> <RRGGBB> <字符> [尺寸]")
        return 2
    out, hexrgb, char = sys.argv[1], sys.argv[2], sys.argv[3]
    size = int(sys.argv[4]) if len(sys.argv) > 4 else 32
    rgb = tuple(int(hexrgb[i : i + 2], 16) for i in (0, 2, 4))
    data = build_icon(size, rgb, char)  # type: ignore[arg-type]
    with open(out, "wb") as fh:
        fh.write(data)
    print(f"已生成 {out}（{size}x{size}，底色 #{hexrgb}，字符 '{char}'，{len(data)} 字节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
