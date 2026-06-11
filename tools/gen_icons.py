#!/usr/bin/env python3
"""간다 GO 브랜드 아이콘 생성기 (의존성 없는 순수 Python).

assets/favicon.svg 와 같은 G 모노그램을 래스터로 그려
favicon·앱 아이콘·OG 이미지를 만든다. 실행: python3 tools/gen_icons.py
"""
import math
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

NAVY = (10, 17, 32)        # #0a1120
GOLD = (200, 162, 94)      # #c8a25e
GOLD_SOFT = (233, 215, 171)  # #e9d7ab


def write_png(path, w, h, pixels):
    """pixels: list of rows, each row list of (r,g,b,a)."""
    raw = b"".join(
        b"\x00" + b"".join(struct.pack("4B", *px) for px in row) for row in pixels
    )
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(png)


def render_mark(size, bg=None):
    """size×size 캔버스에 다크 디스크 + 골드 링 + G 모노그램.
    bg=None 이면 디스크 밖 투명, 튜플이면 해당 색으로 채움."""
    S = size / 512.0
    cx = cy = size / 2.0
    disc_r = 246 * S
    ring_r, ring_w = 237 * S, 18 * S
    ring2_r, ring2_w = 208 * S, 4 * S
    # G 모노그램 기하 (favicon.svg 와 동일 비례)
    gx, gy = 256 * S + cx - 256 * S, 250 * S + cy - 256 * S
    gx, gy = cx, cy - 6 * S
    g_r, g_w = 124 * S, 52 * S
    bar_x0, bar_x1 = cx + 12 * S, cx + 124 * S
    bar_y0, bar_y1 = gy - 26 * S + 32 * S, gy + 26 * S + 32 * S

    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            px, py = x + 0.5, y + 0.5
            d = math.hypot(px - cx, py - cy)
            if d > disc_r:
                row.append(bg + (255,) if bg else (0, 0, 0, 0))
                continue
            color = NAVY
            if abs(d - ring_r) <= ring_w / 2:
                color = GOLD
            elif abs(d - ring2_r) <= ring2_w / 2:
                color = tuple(
                    int(n * 0.35 + b * 0.65) for n, b in zip(GOLD, NAVY)
                )
            # G 본체 (열린 구간: 오른쪽 위 -72°~ -8°)
            gd = math.hypot(px - gx, py - gy)
            if abs(gd - g_r) <= g_w / 2:
                ang = math.degrees(math.atan2(py - gy, px - gx))  # y 아래 양수
                if not (-72 <= ang <= -8):
                    color = GOLD_SOFT
            # G 가로 바
            if bar_x0 <= px <= bar_x1 and bar_y0 <= py <= bar_y1:
                color = GOLD_SOFT
            row.append(color + (255,))
        rows.append(row)
    return rows


def downsample(rows, factor):
    size = len(rows) // factor
    out = []
    for y in range(size):
        row = []
        for x in range(size):
            acc = [0, 0, 0, 0]
            for dy in range(factor):
                for dx in range(factor):
                    px = rows[y * factor + dy][x * factor + dx]
                    for i in range(4):
                        acc[i] += px[i]
            n = factor * factor
            row.append(tuple(v // n for v in acc))
        out.append(row)
    return out


def main():
    master = render_mark(512)
    targets = {
        "icon-512.png": 1,
        # 512/2=256 → icon-192 는 별도 렌더
    }
    write_png(os.path.join(ASSETS, "icon-512.png"), 512, 512, master)
    for name, size in (
        ("icon-192.png", 192),
        ("apple-touch-icon.png", 180),
        ("favicon-32.png", 32),
        ("favicon-16.png", 16),
    ):
        big = render_mark(size * 4)
        small = downsample(big, 4)
        write_png(os.path.join(ASSETS, name), size, size, small)

    # favicon.ico — 48px PNG 를 담은 ICO 컨테이너
    big = render_mark(192)
    small = downsample(big, 4)
    import io
    buf = io.BytesIO()
    raw = b"".join(
        b"\x00" + b"".join(struct.pack("4B", *px) for px in row) for row in small
    )
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 48, 48, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    ico = struct.pack("<HHH", 0, 1, 1) + struct.pack(
        "<BBBBHHII", 48, 48, 0, 0, 1, 32, len(png), 22
    ) + png
    with open(os.path.join(ROOT, "favicon.ico"), "wb") as f:
        f.write(ico)

    # OG 이미지 1200×630 — 네이비 배경 중앙에 마크
    mark_big = render_mark(1440, bg=NAVY)
    mark = downsample(mark_big, 4)  # 360px
    W, H = 1200, 630
    canvas = [[NAVY + (255,)] * W for _ in range(H)]
    ox, oy = (W - 360) // 2, (H - 360) // 2
    for y in range(360):
        for x in range(360):
            canvas[oy + y][ox + x] = mark[y][x]
    # 상하단 골드 라인
    for x in range(W):
        for ly in (8, 9, H - 10, H - 9):
            canvas[ly][x] = GOLD + (255,)
    write_png(os.path.join(ASSETS, "og-image.png"), W, H, canvas)
    print("아이콘 생성 완료:", sorted(os.listdir(ASSETS)))


if __name__ == "__main__":
    main()
