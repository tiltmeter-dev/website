#!/usr/bin/env python3
"""Draw the home page's isometric scenes and write them into index.html.

Each scene goes between <!-- iso:NAME:start --> and <!-- iso:NAME:end -->:

- provider-wide: a provider's signed notice reaches Tiltmeter, which finds and fixes the code
- provider-tall: the same story stacked for narrow screens, with larger labels
- fix: the agent edits a sandboxed worktree and the pull request is merged

The palettes are the design tokens in tokens.css (ink, paper, vermilion); CSS colours the
states. Without JavaScript, or with reduced motion, each SVG shows its final state, and
home.js steps through the story. Rerun after changing a scene: python3 scripts/iso_scene.py
"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The three faces of a box, as in tokens.css: --ink-face-t / -l / -r and --paper / --paper-edge-l / -r.
INK = {"top": "#26262b", "left": "#1b1b1f", "right": "#141417"}
PAPER = {"top": "#f2efe7", "left": "#dcd7ca", "right": "#c9c3b4"}

MONO_ADVANCE = 0.6        # IBM Plex Mono: every glyph is 600/1000 em
STENCIL_TRACKING = 0.08   # --tracking-stencil

Point = tuple[float, float, float]


@lru_cache(maxsize=None)
def _sans_widths(weight: int):
    """Advance widths of Schibsted Grotesk at a weight, so labels are measured, not guessed."""
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib.instancer import instantiateVariableFont
    except ImportError:
        return None
    font = TTFont(ROOT / "fonts" / "schibsted-grotesk-latin.woff2")
    font = instantiateVariableFont(font, {"wght": weight})
    upm = font["head"].unitsPerEm
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    return {code: hmtx[name][0] / upm for code, name in cmap.items()}


def sans_width(text: str, size: float, weight: int = 500) -> float:
    widths = _sans_widths(weight)
    if widths is None:
        return len(text) * size * 0.56
    return sum(widths.get(ord(ch), 0.56) for ch in text) * size


class Iso:
    """An isometric drawing: x runs down to the right, y down to the left, z up."""

    def __init__(self, unit: float, label: float = 8.5, card: float = 9.5) -> None:
        self.unit = unit
        self.label = label      # stencil label size, in drawing units
        self.card = card        # billboard text size
        self.c = unit * math.cos(math.pi / 6)
        self.s = unit * math.sin(math.pi / 6)
        self.parts: list[str] = []
        self.xs: list[float] = []
        self.ys: list[float] = []
        self.tracking = True

    # -- projection ----------------------------------------------------------------

    def p(self, x: float, y: float, z: float = 0.0) -> tuple[float, float]:
        sx, sy = (x - y) * self.c, (x + y) * self.s - z * self.unit
        if self.tracking:
            self.xs.append(sx)
            self.ys.append(sy)
        return sx, sy

    def pts(self, *points: Point) -> str:
        return " ".join("%.1f,%.1f" % self.p(*q) for q in points)

    def add(self, *parts: str) -> None:
        self.parts.extend(parts)

    # -- shapes --------------------------------------------------------------------

    def box(self, x, y, z, w, d, h, pal=INK, cls="", top_cls="", extra="", attrs="") -> str:
        """A box with its three visible faces: top, front-left (y + d), front-right (x + w)."""
        top = self.pts((x, y, z + h), (x + w, y, z + h), (x + w, y + d, z + h), (x, y + d, z + h))
        left = self.pts((x, y + d, z), (x + w, y + d, z), (x + w, y + d, z + h), (x, y + d, z + h))
        right = self.pts((x + w, y, z), (x + w, y + d, z), (x + w, y + d, z + h), (x + w, y, z + h))
        group = (f' class="{cls}"' if cls else "") + attrs
        tcls = f"ft {top_cls}".strip()
        return (
            f'<g{group}><polygon class="fl" points="{left}" fill="{pal["left"]}"/>'
            f'<polygon class="fr" points="{right}" fill="{pal["right"]}"/>'
            f'<polygon class="{tcls}" points="{top}" fill="{pal["top"]}"/>{extra}</g>'
        )

    def wire(self, x, y, z, w, d, h, cls) -> str:
        """The visible edges of a box, as dashed linework with no faces: a boundary, not a thing."""
        edges = [
            [(x, y, z + h), (x + w, y, z + h), (x + w, y + d, z + h), (x, y + d, z + h), (x, y, z + h)],
            [(x, y + d, z), (x + w, y + d, z), (x + w, y, z)],
            [(x, y + d, z), (x, y + d, z + h)],
            [(x + w, y + d, z), (x + w, y + d, z + h)],
            [(x + w, y, z), (x + w, y, z + h)],
        ]
        return f'<g class="{cls}">' + "".join(self.line(e, "edge") for e in edges) + "</g>"

    def line(self, points: list[Point], cls: str) -> str:
        return f'<polyline class="{cls}" points="{self.pts(*points)}"/>'

    def quad(self, points: list[Point], cls: str) -> str:
        return f'<polygon class="{cls}" points="{self.pts(*points)}"/>'

    def ring(self, x, y, z, r, cls) -> str:
        """A circle lying on a horizontal plane."""
        cx, cy = self.p(x, y, z)
        rx, ry = r * self.c * math.sqrt(2), r * self.s * math.sqrt(2)
        return f'<ellipse class="{cls}" cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"/>'

    def dot(self, x, y, z, r, cls) -> str:
        cx, cy = self.p(x, y, z)
        return f'<circle class="{cls}" cx="{cx:.1f}" cy="{cy:.1f}" r="{r}"/>'

    def text(self, plane, x, y, z, words, size=8.0, cls="", anchor="start") -> str:
        """Text painted on a face: the top plane, the front-left face or the front-right face."""
        sx, sy = self.p(x, y, z)
        k = 1 / self.unit
        c, s = self.c * k, self.s * k
        a, b, cc, d = {"top": (c, s, -c, s), "left": (c, s, 0, 1), "right": (c, -s, 0, 1)}[plane]
        return (
            f'<text class="it {cls}" transform="matrix({a:.4f},{b:.4f},{cc:.4f},{d:.4f},{sx:.1f},{sy:.1f})" '
            f'font-size="{size}" text-anchor="{anchor}">{escape(words)}</text>'
        )

    def slab(self, x, y, w, d, label, h=0.5, cls="slab", face="left") -> str:
        size = self.label
        length = len(label) * size * MONO_ADVANCE * (1 + STENCIL_TRACKING) / self.unit
        room = (d if face == "right" else w) - 0.5
        if length > room:
            raise SystemExit(f"label {label!r} needs {length:.2f} units on a {room:.2f}-unit face; shorten it or shrink --label")
        if face == "right":
            words = self.text("right", x + w, y + d - 0.3, 0.12, label, size * 0.94, "lab")
        else:
            words = self.text("left", x + 0.35, y + d, 0.14, label, size, "lab")
        return self.box(x, y, 0, w, d, h, cls=cls) + words

    def billboard(self, x, y, z, states: list[list[str]], cls="", size=None, stem=0.0, marks=None) -> str:
        """A flat card floating at (x, y, z), one text block per state; CSS shows one at a time.

        marks gives each state an optional status mark drawn before its first line: "open" is a
        hollow square, "merged" a filled one, as in tokens.css.
        """
        size = size or self.card
        sx, sy = self.p(x, y, z)
        marks = marks or [None] * len(states)
        mark = size * 0.62
        gap = size * 0.5
        pad = size * 0.85
        widths = []
        for state, m in zip(states, marks):
            first = sans_width(state[0], size) + (mark + gap if m else 0)
            widths.append(max([first] + [sans_width(line, size) for line in state[1:]]))
        rows = max(len(state) for state in states)
        w = max(widths) + pad * 2
        h = rows * size * 1.35 + size * 0.9
        top = sy - h - (stem * self.unit + 6)
        left = sx - w / 2
        if self.tracking:
            self.xs += [left, left + w]
            self.ys += [top - 4]
        body = [f'<rect class="plate" x="{left:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" rx="3"/>']
        if stem:
            body.append(f'<line class="stem" x1="{sx:.1f}" y1="{top + h:.1f}" x2="{sx:.1f}" y2="{sy:.1f}"/>')
        for n, (state, m) in enumerate(zip(states, marks)):
            # Each state is centred on its own width, so a short "Merged" sits as centred as "PR opened".
            x0 = sx - widths[n] / 2
            base = top + size * 0.45 + size * 1.0
            parts = []
            tx = x0
            if m:
                parts.append(
                    f'<rect class="status {m}" x="{x0:.1f}" y="{base - mark * 0.98:.1f}" '
                    f'width="{mark:.1f}" height="{mark:.1f}"/>'
                )
                tx = x0 + mark + gap
            lines = "".join(
                f'<tspan x="{tx:.1f}" dy="{0 if i == 0 else size * 1.35:.1f}">{escape(line)}</tspan>'
                for i, line in enumerate(state)
            )
            parts.append(f'<text x="{tx:.1f}" y="{base:.1f}" font-size="{size}">{lines}</text>')
            body.append(f'<g class="s{n}">{"".join(parts)}</g>')
        multi = " multi" if len(states) > 1 else ""
        return f'<g class="bb{multi} {cls}">{"".join(body)}</g>'

    def mover(self, draw, cls: str, at: tuple[float, float], **data: str) -> str:
        """Something home.js moves: drawn around the origin, placed at `at` by a transform."""
        self.tracking = False
        inner = draw()
        self.tracking = True
        attrs = "".join(f' data-{k}="{v}"' for k, v in data.items())
        return f'<g class="mv {cls}" transform="translate({at[0]:.1f},{at[1]:.1f})"{attrs}><g class="in">{inner}</g></g>'

    def floor(self, *rects: tuple[int, int, int, int]) -> str:
        """The isometric floor under the scene: one or more rectangles of grid."""
        self.tracking = False
        rows = []
        for x0, x1, y0, y1 in rects:
            rows += [self.line([(i, y0, 0), (i, y1, 0)], "grid") for i in range(x0, x1 + 1)]
            rows += [self.line([(x0, j, 0), (x1, j, 0)], "grid") for j in range(y0, y1 + 1)]
        self.tracking = True
        return f'<g class="floor">{"".join(rows)}</g>'

    def arc(self, a: tuple[float, float], b: tuple[float, float], lift: float) -> str:
        """A quadratic curve from a to b that rises `lift` pixels: also the flight path."""
        cx, cy = (a[0] + b[0]) / 2, min(a[1], b[1]) - lift
        self.ys.append(cy)
        return f"{a[0]:.1f},{a[1]:.1f} {cx:.1f},{cy:.1f} {b[0]:.1f},{b[1]:.1f}"

    def svg(self, label: str, cls: str = "", pad: float = 18) -> str:
        x0, x1 = min(self.xs) - pad, max(self.xs) + pad
        y0, y1 = min(self.ys) - pad, max(self.ys) + pad
        classes = f"iso-svg {cls}".strip()
        return (
            f'<svg class="{classes}" viewBox="{x0:.0f} {y0:.0f} {x1 - x0:.0f} {y1 - y0:.0f}" role="img" '
            f'aria-label="{escape(label)}">{"".join(self.parts)}</svg>'
        )


def cube(s: Iso, size: float, pal=PAPER) -> str:
    h = size / 2
    return s.box(-h, -h, -h, size, size, size, pal)


def sheet(s: Iso, w: float, d: float, lines: int = 0) -> str:
    """A sheet of paper lying flat, drawn around the origin: the notice, or a pull request."""
    body = s.box(-w / 2, -d / 2, 0, w, d, w * 0.045, PAPER, cls="sheet")
    gap = d / (lines + 1.6) if lines else 0
    for k in range(lines):
        y = -d / 2 + gap * (k + 0.9)
        body += s.line([(-w / 2 + w * 0.14, y, w * 0.045), (-w / 2 + w * (0.58 if k else 0.44), y, w * 0.045)], "ink-line")
    return body


def path_attr(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def wave(s: Iso, x0, x1, y, z, amp, cls, quake=False) -> str:
    points = []
    for n in range(49):
        t = n / 48
        a = amp + (0.36 * math.exp(-((t - 0.55) ** 2) / 0.006) if quake else 0)
        points.append((x0 + t * (x1 - x0), y, z + math.sin(t * 38) * a))
    return s.line(points, cls)


def device(s: Iso, x, y, z, w, d, h) -> None:
    """The Tiltmeter: a paper box with a seismograph on its face and the vermilion needle on top."""
    s.add(s.box(x, y, z, w, d, h, PAPER, cls="device"))
    face = y + d
    s.add(s.quad([(x + 0.22, face, z + 0.22), (x + w - 0.22, face, z + 0.22),
                  (x + w - 0.22, face, z + h - 0.22), (x + 0.22, face, z + h - 0.22)], "screen"))
    mid = z + h / 2
    s.add(wave(s, x + 0.3, x + w - 0.3, face, mid, 0.05, "wave calm"))
    s.add(wave(s, x + 0.3, x + w - 0.3, face, mid, 0.05, "wave quake", quake=True))
    cx, cy = x + w / 2, y + d / 2
    needle = s.line([(cx - w * 0.27, cy + d * 0.13, z + h), (cx + w * 0.27, cy - d * 0.13, z + h)], "needle-l")
    s.add(f'<g class="needle">{needle}</g>')
    r = min(w, d) * 0.42
    s.add(s.ring(cx, cy, z + h, r, "pulse p1"), s.ring(cx, cy, z + h, r, "pulse p2"))


def glyphs(s: Iso, x, y, z, long=0.85, short=0.5, gap=0.3) -> str:
    return "".join(
        s.line([(x, y + k * gap, z), (x + (long if k else short), y + k * gap, z)], "glyph") for k in range(3)
    )


# -- 1. With the provider ---------------------------------------------------------
#
# The wide layout runs left to right along x. The tall one turns at the Tiltmeter and runs
# down along y, so it fits a phone held upright at a size where the labels can be read.

LAYOUTS = {
    "wide": {
        "label": 8.5, "card": 9.5,
        "code_label": "YOUR CUSTOMERS' CODE", "raise": 1.75, "tilt_face": "left",
        "code": (14.0, 0.0),
        "floor": [(-1, 21, -1, 7)],
        "out": [(12, 3, 0), (14, 3, 0)],
        "sweep": "x",
    },
    "tall": {
        "label": 13, "card": 13.5,
        "code_label": "CUSTOMERS' CODE", "raise": 2.5, "tilt_face": "right",
        "code": (6.5, 7.0),
        "floor": [(-1, 13, -1, 6), (5, 13, 6, 14)],
        "out": [(10.2, 5, 0), (10.2, 7, 0)],
        "sweep": "y",
    },
}

PROVIDER_LABEL = (
    "A provider publishes a signed notice. Tiltmeter scans its customers' repositories, finds the three "
    "that still call what changed, and opens a pull request in each; all three are merged."
)


def provider(layout: str) -> str:
    cfg = LAYOUTS[layout]
    s = Iso(24, label=cfg["label"], card=cfg["card"])
    ox, oy = cfg["code"]
    s.add(s.floor(*cfg["floor"]))
    s.add(s.line([(5, 2.5, 0), (7, 2.5, 0)], "path"), s.line(cfg["out"], "path"))

    s.add(s.slab(0, 0, 5, 5, "YOUR API"))
    for k in range(3):
        z = 0.5 + k * 0.85
        s.add(s.box(1.1, 1.1, z, 2.8, 2.8, 0.7, cls="server"))
        s.add(*(s.dot(1.5 + n * 0.42, 3.9, z + 0.36, 1.7, "led") for n in range(3)))
    s.add(s.ring(2.5, 2.5, 2.9, 0.75, "shadow"))

    def notice() -> str:
        body = sheet(s, 2.2, 1.7)
        lines = "".join(s.line([(-0.8, -0.45 + k * 0.32, 0.1), (0.15, -0.45 + k * 0.32, 0.1)], "ink-line") for k in range(3))
        return body + lines + s.ring(0.55, 0.35, 0.1, 0.26, "seal") + s.text("top", -0.85, 0.78, 0.1, "SIGNED", 4.6, "seal-t")

    home = s.p(2.5, 2.5, 3.55)
    target = s.p(9.5, 2.5, 2.05)
    flight = s.arc(home, target, 64)
    a, c, b = flight.split()
    s.add(f'<path class="trail" d="M{a} Q{c} {b}"/>')

    s.add(s.slab(7, 0, 5, 5, "TILTMETER", face=cfg["tilt_face"]))
    device(s, 8, 1, 0.5, 3, 3, 1.5)

    s.add(s.slab(ox, oy, 6, 6, cfg["code_label"]))
    hits = {(0, 2): "a", (1, 1): "b", (2, 0): "c"}
    centers = {}
    for i, j in sorted(((i, j) for i in range(3) for j in range(3)), key=lambda q: (q[0] + q[1], q[0])):
        x, y = ox + 0.5 + i * 1.75, oy + 0.5 + j * 1.75
        cx, cy = x + 0.67, y + 0.67
        hit = hits.get((i, j))
        cls = f"tile hit h-{hit}" if hit else "tile"
        reach = (cx - ox - 0.2) if cfg["sweep"] == "x" else (cy - oy - 0.2)
        at = f' data-at="{reach / 5.6:.2f}"'
        s.add(s.box(x, y, 0.5, 1.35, 1.35, 0.4, cls=cls, top_cls="tt", extra=glyphs(s, x + 0.25, y + 0.35, 0.9), attrs=at))
        centers[(i, j)] = (cx, cy)

    # The scan: a vertical curtain of light that crosses the customers' code.
    if cfg["sweep"] == "x":
        x0, y0, y1 = ox + 0.2, oy + 0.2, oy + 5.8
        beam = s.quad([(x0, y0, 0.5), (x0, y1, 0.5), (x0, y1, 2.3), (x0, y0, 2.3)], "curtain")
        beam += s.line([(x0, y0, 2.3), (x0, y1, 2.3)], "curtain-edge")
        beam += s.quad([(x0 - 0.2, y0, 0.92), (x0 + 0.2, y0, 0.92), (x0 + 0.2, y1, 0.92), (x0 - 0.2, y1, 0.92)], "curtain-floor")
        dx, dy = 5.6 * s.c, 5.6 * s.s
    else:
        y0, x0, x1 = oy + 0.2, ox + 0.2, ox + 5.8
        beam = s.quad([(x0, y0, 0.5), (x1, y0, 0.5), (x1, y0, 2.3), (x0, y0, 2.3)], "curtain")
        beam += s.line([(x0, y0, 2.3), (x1, y0, 2.3)], "curtain-edge")
        beam += s.quad([(x0, y0 - 0.2, 0.92), (x1, y0 - 0.2, 0.92), (x1, y0 + 0.2, 0.92), (x0, y0 + 0.2, 0.92)], "curtain-floor")
        dx, dy = -5.6 * s.c, 5.6 * s.s
    s.add(f'<g class="beam" data-dx="{dx:.1f}" data-dy="{dy:.1f}">{beam}</g>')

    # The pull requests leave the Tiltmeter as sheets of paper, one per repository it found.
    for (i, j), name in sorted(hits.items()):
        cx, cy = centers[(i, j)]
        if cfg["sweep"] == "x":
            route = [s.p(11.0, 3.0, 1.0), s.p(12.2, 3.0, 0.35), s.p(14.0, 3.0, 0.8), s.p(cx, 3.0, 1.1), s.p(cx, cy, 1.1)]
        else:
            route = [s.p(10.2, 4.0, 1.0), s.p(10.2, 5.4, 0.35), s.p(10.2, 7.0, 0.8), s.p(10.2, cy, 1.1), s.p(cx, cy, 1.1)]
        s.add(s.mover(lambda: sheet(s, 0.9, 0.7, lines=2), f"fixer f-{name}", route[0], path=path_attr(route)))
    for (i, j), name in sorted(hits.items()):
        cx, cy = centers[(i, j)]
        stem = cfg["raise"] if name == "b" else 0.95
        s.add(s.billboard(cx, cy, 0.9, [["PR opened"], ["Merged"]], f"prb prb-{name}", stem=stem, marks=["open", "merged"]))

    s.add(s.mover(notice, "notice", home, arc=flight))
    return s.svg(PROVIDER_LABEL, cls=f"iso-{layout}")


# -- 2. The pull request ----------------------------------------------------------


def fix() -> str:
    s = Iso(22, label=7.5, card=8.5)
    s.add(s.floor((-4, 15, -1, 6)))
    s.add(s.slab(-3.2, 1.3, 2.2, 2.2, "AGENT", h=0.4))
    s.add(s.slab(0, 0, 5.6, 4.6, "FRESH WORKTREE"))
    files = {"ok1": (0.7, 0.8), "dead": (2.6, 0.8), "broken": (0.7, 2.6), "ok2": (2.6, 2.6)}
    for name, (x, y) in files.items():
        s.add(s.box(x, y, 0.5, 1.6, 1.5, 0.17, cls=f"file {name}", top_cls="tt",
                    extra=glyphs(s, x + 0.25, y + 0.35, 0.67, long=1.0, short=0.6, gap=0.32)))
    home = s.p(-2.1, 2.4, 0.7)
    land = s.p(1.5, 3.35, 0.97)
    s.add(s.mover(lambda: cube(s, 0.6, PAPER), "agent-cube", home, arc=s.arc(home, land, 46)))
    s.add(s.wire(0.3, 0.3, 0.5, 5.0, 4.0, 1.25, "sandbox"))
    s.add(s.billboard(3.4, 1.55, 0.67, [["unused", "skipped"]], "dead-bb", stem=2.1))
    s.add(s.billboard(1.5, 3.35, 0.67, [["+1 −1"]], "edit-bb", stem=1.3))

    s.add(s.slab(6.3, 0.3, 1.3, 4.0, "TESTS", h=0.4, face="right"))
    for k in range(5):
        s.add(s.box(6.65, 0.6 + k * 0.72, 0.4, 0.55, 0.55, 0.55, cls=f"test t{k}", top_cls="tt"))

    s.add(s.slab(9.8, 0, 4.4, 4.4, "PULL REQUEST"))
    s.add(s.box(10.4, 0.6, 0.5, 3.2, 3.2, 0.25, cls="pr-desk"))
    takeoff = s.p(2.8, 2.3, 2.9)
    landing = s.p(12.0, 2.2, 1.1)
    flight = s.arc(takeoff, landing, 40)

    def card() -> str:
        return s.billboard(0, 0, 0, [["fix: retired model", "Pull request opened"], ["fix: retired model", "Merged"]],
                           "card", marks=[None, None])

    lx, ly = landing
    s.xs += [lx - 70, lx + 70]
    s.ys += [ly - 44]
    s.add(s.mover(card, "pr-card", landing, arc=flight))
    return s.svg("An agent edits the affected file in a sandboxed worktree, skips a file nothing imports, "
                 "runs the tests, and the pull request travels out and is merged.")


SCENES = {
    "provider-wide": lambda: provider("wide"),
    "provider-tall": lambda: provider("tall"),
    "fix": fix,
}


def main() -> None:
    page = ROOT / "index.html"
    html = page.read_text(encoding="utf-8")
    for name, draw in SCENES.items():
        svg = draw()
        html, count = re.subn(
            rf"<!-- iso:{name}:start -->.*?<!-- iso:{name}:end -->",
            lambda _: f"<!-- iso:{name}:start -->{svg}<!-- iso:{name}:end -->",
            html,
            flags=re.S,
        )
        if count != 1:
            raise SystemExit(f"index.html needs one <!-- iso:{name}:start --> ... <!-- iso:{name}:end --> block")
        print(f"{name}: {len(svg):,} bytes")
    page.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
