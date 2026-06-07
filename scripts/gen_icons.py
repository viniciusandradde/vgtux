#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera os ícones PWA (pixel-art) usando só a stdlib (zlib).
- Painel (pai): coração branco em fundo azul.
- Aventura (filho): rosto de creeper preto em fundo verde (tema Minecraft).
Saída: PNG 192 e 512 em portal/ e terminal-shell/.
"""
import zlib, struct, os

GRID = 16  # arte 16x16, com emblema 8x8 centralizado (offset 4)

def png_bytes(pixels, w, h):
    """pixels: lista de linhas; cada linha lista de (r,g,b). Retorna PNG bytes."""
    raw = bytearray()
    for row in pixels:
        raw.append(0)  # filtro None
        for (r, g, b) in row:
            raw += bytes((r, g, b))
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit, color type 2 (RGB)
    idat = zlib.compress(bytes(raw), 9)
    return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')

def render(bg, fg, mask8, scale):
    """Monta grid 16x16 (fundo bg, emblema 8x8 em fg) e escala por 'scale'."""
    grid = [[bg for _ in range(GRID)] for _ in range(GRID)]
    for y in range(8):
        for x in range(8):
            if mask8[y][x]:
                grid[y + 4][x + 4] = fg
    W = GRID * scale
    out = []
    for gy in range(GRID):
        rowpix = []
        for gx in range(GRID):
            rowpix += [grid[gy][gx]] * scale
        for _ in range(scale):
            out.append(list(rowpix))
    return png_bytes(out, W, W)

def mask(rows):
    return [[1 if c == 'X' else 0 for c in r.replace(' ', '')] for r in rows]

CORACAO = mask([
    ".XX..XX.",
    "XXXXXXXX",
    "XXXXXXXX",
    "XXXXXXXX",
    ".XXXXXX.",
    "..XXXX..",
    "...XX...",
    "........",
])

CREEPER = mask([
    "........",
    ".XX..XX.",
    ".XX..XX.",
    "...XX...",
    "..XXXX..",
    "..XXXX..",
    "..X..X..",
    "........",
])

AZUL   = (31, 111, 235)
VERDE  = (67, 160, 71)
BRANCO = (245, 247, 250)
PRETO  = (20, 22, 28)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def salvar(destinos, bg, fg, mask8):
    for caminho, scale in destinos:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, 'wb') as f:
            f.write(render(bg, fg, mask8, scale))
        print("ok:", caminho)

# Painel (pai) → coração branco em azul
salvar([(os.path.join(ROOT, 'portal', 'icon-192.png'), 12),
        (os.path.join(ROOT, 'portal', 'icon-512.png'), 32)], AZUL, BRANCO, CORACAO)

# Aventura (filho) → creeper preto em verde
salvar([(os.path.join(ROOT, 'terminal-shell', 'icon-192.png'), 12),
        (os.path.join(ROOT, 'terminal-shell', 'icon-512.png'), 32)], VERDE, PRETO, CREEPER)
