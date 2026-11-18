# Version: v1 (2026-11-18) — Sangani Skyz 545 Wp panel geometry, read off the 2D layout v1.2 (proposal v1.1 p.3)
# Pixel coordinates are in the layout picture (2338 x 1654) — north up, rows rotated ~7° (rise to the east).
import math
K = 1.169                       # displayed -> original pixels
A = math.radians(6.9)           # row rotation (rows rise towards the east)
c, s = math.cos(A), math.sin(A)
PPM = 31.0 * K                  # pixels per metre (panel pitch 1.154 m across a row)
PU = 1.154 * PPM                # pitch along a row
PV = 2.26 * PPM                 # pitch between rows (2.278 m portrait panel at 10 deg tilt)
U = (c, -s)                     # one metre along a row, to the east
N = (-s, -c)                    # one metre across rows, to the north


def P(x, y):
    return x * K, y * K


# block: (SW corner of col 0 / row 0 in displayed px, columns, rows, height m)
BLOCKS = {
    'B1':  (P(219, 1189), 20, 2, 2.0),
    'B2':  (P(217, 1028), 19, 2, 2.0),
    'B3W': (P(262, 862), 6, 2, 3.5),      # + 1 amber panel west of the north row (col -1)
    'B3E': (P(648, 817), 5, 2, 3.5),
    'B4W': (P(212, 703), 7, 2, 3.5),
    'B4E': (P(596, 648), 7, 2, 3.5),
    'B5':  (P(139, 548), 21, 3, 4.0),
}
CABIN = [P(465, 510), P(578, 504), P(583, 680), P(480, 686)]   # staircase cabin 13 ft (corners NW, NE, SE, SW)


def panel_poly(b, col, row):
    (x0, y0), *_ = BLOCKS[b]
    pts = []
    for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
        u = (col + du * 0.98) * PU
        v = (row + dv * 0.97) * PV
        pts.append((x0 + U[0] * u + N[0] * v, y0 + U[1] * u + N[1] * v))
    return pts


def panel_centre(b, col, row):
    pts = panel_poly(b, col, row)
    return sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4
