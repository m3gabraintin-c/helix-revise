#!/usr/bin/env python3
"""Regenerate icons/*.png from the brand mark in index.html (stdlib only). Run: python3 scripts/make-icons.py"""
import zlib, struct, math, os
BG, FG = (0x16, 0x15, 0x12), (0xe3, 0xdd, 0xd0)
def bez(p0, p1, p2, p3, n=40):
    return [tuple((1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*d for a, b, c, d in zip(p0, p1, p2, p3)) for t in (i/n for i in range(n+1))]
STRANDS = [bez((10,7),(10,13),(22,13),(22,19)) + bez((22,19),(22,25),(10,19),(10,25)),
           bez((22,7),(22,13),(10,13),(10,19)) + bez((10,19),(10,25),(22,19),(22,25))]
SEGS = [(p[i], p[i+1]) for p in STRANDS for i in range(len(p)-1)]
def dist(x, y, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]; L = dx*dx+dy*dy
    t = max(0, min(1, ((x-a[0])*dx+(y-a[1])*dy)/L)) if L else 0
    return math.hypot(x-a[0]-t*dx, y-a[1]-t*dy)
def render(size, scale, rounded):
    # scale: size of the 32-unit mark relative to the canvas (maskable/apple keep it inside the safe zone)
    ss, u = 3, size/32*scale; off = (size - 32*u)/2
    raw = bytearray()
    for py in range(size):
        raw.append(0)
        for px in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    X, Y = px+(sx+.5)/ss, py+(sy+.5)/ss
                    if rounded:  # rounded square, radius 12/32 like the SVG
                        r = size*12/32; cx = min(max(X, r), size-r); cy = min(max(Y, r), size-r)
                        if math.hypot(X-cx, Y-cy) > r: continue
                    ux, uy = (X-off)/u, (Y-off)/u
                    col = FG if min(dist(ux, uy, a, b) for a, b in SEGS) <= 1.1 else BG
                    acc = [acc[0]+col[0], acc[1]+col[1], acc[2]+col[2], acc[3]+1]
            n = ss*ss
            raw += bytes([acc[0]//acc[3], acc[1]//acc[3], acc[2]//acc[3], acc[3]*255//n]) if acc[3] else bytes(4)
    def chunk(t, d): c = struct.pack(">I", len(d)) + t + d; return c + struct.pack(">I", zlib.crc32(t+d))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
os.makedirs("icons", exist_ok=True)
for name, size, scale, rounded in [("icon-192", 192, 1, True), ("icon-512", 512, 1, True), ("icon-maskable-512", 512, 0.62, False), ("apple-touch-icon", 180, 0.8, False)]:
    open(f"icons/{name}.png", "wb").write(render(size, scale, rounded))
