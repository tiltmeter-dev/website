#!/usr/bin/env python3
"""Draw the home page's isometric scenes and write them into index.html.

Four scenes, each between <!-- iso:NAME:start --> and <!-- iso:NAME:end -->:

- provider: a provider's signed notice reaches Tiltmeter, which finds and fixes the code
- drift: no provider; Tiltmeter catches a changed response itself
- scan: `tiltmeter scan` sweeps a repository for API changes that already shipped
- fix: the agent edits a sandboxed worktree and the pull request is merged

home.js animates them. Without JavaScript, or with reduced motion, each SVG shows its
final state. Rerun after changing a scene: python3 scripts/iso_scene.py
"""

from __future__ import annotations

import math
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PAPER = {"top": "#26262b", "left": "#1b1b1f", "right": "#141417"}
LIGHT = {"top": "#f2efe7", "left": "#dcd7ca", "right": "#c9c3b4"}
DARK = {"top": "#2b2b2f", "left": "#141416", "right": "#1e1e22"}
RED = {"top": "#e2552d", "left": "#c0401b", "right": "#a9381a"}
BLUE = {"top": "#3a76d8", "left": "#2c5fb4", "right": "#234e96"}
MINT = {"top": "#d9eee1", "left": "#bcdcc8", "right": "#a9d1b8"}
GLASS = {"top": "rgba(44,102,201,0.04)", "left": "rgba(44,102,201,0.07)", "right": "rgba(44,102,201,0.1)"}

Point = tuple[float, float, float]


class Iso:
    """An isometric drawing: x runs down to the right, y down to the left, z up."""

    def __init__(self, unit: float) -> None:
        self.unit = unit
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

    def box(self, x, y, z, w, d, h, pal=PAPER, cls="", top_cls="", extra="", attrs="") -> str:
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
        if face == "right":
            words = self.text("right", x + w, y + d - 0.3, 0.12, label, 7, "lab")
        else:
            words = self.text("left", x + 0.35, y + d, 0.14, label, 7.5, "lab")
        return self.box(x, y, 0, w, d, h, cls=cls) + words

    def billboard(self, x, y, z, states: list[list[str]], cls="", size=10.0, stem=0.0) -> str:
        """A flat card floating at (x, y, z), one text block per state; CSS shows one at a time."""
        sx, sy = self.p(x, y, z)
        longest = max(len(line) for state in states for line in state)
        rows = max(len(state) for state in states)
        w = longest * size * 0.62 + 26
        h = rows * size * 1.4 + 12
        top = sy - h - (stem * self.unit + 6)
        if self.tracking:
            self.xs += [sx - w / 2, sx + w / 2]
            self.ys += [top - 4]
        body = [f'<rect x="{sx - w / 2:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8"/>']
        if stem:
            body.append(f'<line class="stem" x1="{sx:.1f}" y1="{top + h:.1f}" x2="{sx:.1f}" y2="{sy:.1f}"/>')
        for n, state in enumerate(states):
            lines = "".join(
                f'<tspan x="{sx:.1f}" dy="{0 if i == 0 else size * 1.4:.1f}">{escape(line)}</tspan>'
                for i, line in enumerate(state)
            )
            body.append(
                f'<text class="s{n}" x="{sx:.1f}" y="{top + 6 + size * 1.05:.1f}" font-size="{size}" '
                f'text-anchor="middle">{lines}</text>'
            )
        multi = " multi" if len(states) > 1 else ""
        return f'<g class="bb{multi} {cls}">{"".join(body)}</g>'

    def mover(self, draw, cls: str, at: tuple[float, float], **data: str) -> str:
        """Something home.js moves: drawn around the origin, placed at `at` by a transform."""
        self.tracking = False
        inner = draw()
        self.tracking = True
        attrs = "".join(f' data-{k}="{v}"' for k, v in data.items())
        return f'<g class="mv {cls}" transform="translate({at[0]:.1f},{at[1]:.1f})"{attrs}><g class="in">{inner}</g></g>'

    def floor(self, x0, x1, y0, y1) -> str:
        self.tracking = False
        rows = [self.line([(i, y0, 0), (i, y1, 0)], "grid") for i in range(x0, x1 + 1)]
        rows += [self.line([(x0, j, 0), (x1, j, 0)], "grid") for j in range(y0, y1 + 1)]
        self.tracking = True
        return f'<g class="floor">{"".join(rows)}</g>'

    def arc(self, a: tuple[float, float], b: tuple[float, float], lift: float) -> str:
        """A quadratic curve from a to b that rises `lift` pixels: also the flight path."""
        cx, cy = (a[0] + b[0]) / 2, min(a[1], b[1]) - lift
        self.ys.append(cy)
        return f"{a[0]:.1f},{a[1]:.1f} {cx:.1f},{cy:.1f} {b[0]:.1f},{b[1]:.1f}"

    def svg(self, label: str, pad: float = 18) -> str:
        x0, x1 = min(self.xs) - pad, max(self.xs) + pad
        y0, y1 = min(self.ys) - pad, max(self.ys) + pad
        return (
            f'<svg class="iso-svg" viewBox="{x0:.0f} {y0:.0f} {x1 - x0:.0f} {y1 - y0:.0f}" role="img" '
            f'aria-label="{escape(label)}">{"".join(self.parts)}</svg>'
        )


def cube(s: Iso, size: float, pal=RED, stripes: bool = False) -> str:
    h = size / 2
    extra = ""
    if stripes:
        extra = "".join(
            s.line([(-h + 0.12, -h + 0.14 + k * 0.16, h), (h - 0.14, -h + 0.14 + k * 0.16, h)], "stripe")
            for k in range(3)
        )
    return s.box(-h, -h, -h, size, size, size, pal, extra=extra)


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
    """The Tiltmeter: a dark box with a seismograph on its face and the red needle on top."""
    s.add(s.box(x, y, z, w, d, h, LIGHT, cls="device"))
    face = y + d
    s.add(s.quad([(x + 0.22, face, z + 0.22), (x + w - 0.22, face, z + 0.22),
                  (x + w - 0.22, face, z + h - 0.22), (x + 0.22, face, z + h - 0.22)], "screen"))
    mid = z + h / 2
    s.add(wave(s, x + 0.3, x + w - 0.3, face, mid, 0.05, "wave calm"))
    s.add(wave(s, x + 0.3, x + w - 0.3, face, mid, 0.05, "wave quake", quake=True))
    cx, cy = x + w / 2, y + d / 2
    needle = s.line([(cx - w * 0.27, cy + d * 0.13, z + h), (cx + w * 0.27, cy - d * 0.13, z + h)], "needle-l")
    s.add(f'<g class="needle">{needle}</g>')
    s.add(s.dot(x + w, y + d * 0.3, z + h * 0.72, 2.2, "led red"))
    r = min(w, d) * 0.42
    s.add(s.ring(cx, cy, z + h, r, "pulse p1"), s.ring(cx, cy, z + h, r, "pulse p2"))


def glyphs(s: Iso, x, y, z, long=0.85, short=0.5, gap=0.3) -> str:
    return "".join(
        s.line([(x, y + k * gap, z), (x + (long if k else short), y + k * gap, z)], "glyph") for k in range(3)
    )


# -- 1. With the provider ---------------------------------------------------------


def provider() -> str:
    s = Iso(24)
    s.add(s.floor(-1, 21, -1, 7))
    s.add(s.line([(5, 2.5, 0), (7, 2.5, 0)], "path"), s.line([(12, 3, 0), (14, 3, 0)], "path"))

    s.add(s.slab(0, 0, 5, 5, "YOUR API"))
    for k in range(3):
        z = 0.5 + k * 0.85
        s.add(s.box(1.1, 1.1, z, 2.8, 2.8, 0.7, cls="server"))
        s.add(*(s.dot(1.5 + n * 0.42, 3.9, z + 0.36, 1.7, f"led g{(k + n) % 3}") for n in range(3)))
    s.add(s.ring(2.5, 2.5, 2.9, 0.75, "shadow"))

    def notice() -> str:
        sheet = s.box(-1.1, -0.85, 0, 2.2, 1.7, 0.1, LIGHT, cls="sheet")
        lines = "".join(s.line([(-0.8, -0.45 + k * 0.32, 0.1), (0.15, -0.45 + k * 0.32, 0.1)], "ink-line") for k in range(3))
        return sheet + lines + s.ring(0.55, 0.35, 0.1, 0.26, "seal") + s.text("top", -0.85, 0.78, 0.1, "SIGNED", 4.6, "seal-t")

    home = s.p(2.5, 2.5, 3.55)
    target = s.p(9.5, 2.5, 2.05)
    flight = s.arc(home, target, 64)
    a, c, b = flight.split()
    s.add(f'<path class="trail" d="M{a} Q{c} {b}"/>')

    s.add(s.slab(7, 0, 5, 5, "TILTMETER"))
    device(s, 8, 1, 0.5, 3, 3, 1.5)

    s.add(s.slab(14, 0, 6, 6, "YOUR CUSTOMERS' CODE"))
    hits = {(0, 2): "a", (1, 1): "b", (2, 0): "c"}
    centers = {}
    for i, j in sorted(((i, j) for i in range(3) for j in range(3)), key=lambda q: (q[0] + q[1], q[0])):
        x, y = 14.5 + i * 1.75, 0.5 + j * 1.75
        hit = hits.get((i, j))
        cls = f"tile hit h-{hit}" if hit else "tile"
        at = f' data-at="{(x + 0.67 - 14.2) / 5.6:.2f}"'
        s.add(s.box(x, y, 0.5, 1.35, 1.35, 0.4, cls=cls, top_cls="tt", extra=glyphs(s, x + 0.25, y + 0.35, 0.9), attrs=at))
        centers[(i, j)] = (x + 0.67, y + 0.67)

    beam = s.quad([(14.2, 0.2, 0.5), (14.2, 5.8, 0.5), (14.2, 5.8, 2.3), (14.2, 0.2, 2.3)], "curtain")
    beam += s.line([(14.2, 0.2, 2.3), (14.2, 5.8, 2.3)], "curtain-edge")
    beam += s.quad([(14.0, 0.2, 0.92), (14.4, 0.2, 0.92), (14.4, 5.8, 0.92), (14.0, 5.8, 0.92)], "curtain-floor")
    s.add(f'<g class="beam" data-dx="{5.6 * s.c:.1f}" data-dy="{5.6 * s.s:.1f}">{beam}</g>')

    start = s.p(11.0, 3.0, 1.0)
    for (i, j), name in sorted(hits.items()):
        cx, cy = centers[(i, j)]
        route = [start, s.p(12.2, 3.0, 0.35), s.p(14.0, 3.0, 0.8), s.p(cx, 3.0, 1.1), s.p(cx, cy, 1.1)]
        s.add(s.mover(lambda: cube(s, 0.42, BLUE), f"fixer f-{name}", route[0], path=path_attr(route)))
    for (i, j), name in sorted(hits.items()):
        cx, cy = centers[(i, j)]
        stem = 1.75 if name == "b" else 0.95
        s.add(s.billboard(cx, cy, 0.9, [["PR opened"], ["Merged"]], f"prb prb-{name}", 8.5, stem=stem))

    s.add(s.mover(notice, "notice", home, arc=flight))
    return s.svg("A provider publishes a signed notice. Tiltmeter scans its customers' repositories, "
                 "finds the three that call what changed, and opens a pull request in each; all three merge.")


# -- 2. Without the provider: drift ----------------------------------------------


def drift() -> str:
    s = Iso(22)
    s.add(s.floor(-1, 18, -1, 6))
    s.add(s.line([(4.4, 2.2, 0), (6.4, 2.2, 0)], "path"))
    s.add(s.line([(10.8, 1.2, 0), (12.8, 1.2, 0)], "path"), s.line([(10.8, 3.2, 0), (12.8, 3.2, 0)], "path"))

    s.add(s.slab(0, 0, 4.4, 4.4, "THIRD-PARTY API"))
    s.add(s.box(0.8, 0.8, 0.5, 2.8, 2.8, 2.2, cls="server"))
    s.add(s.text("left", 0.98, 3.6, 2.15, "api.vendor.com", 6.4, "srv"))
    s.add(s.text("left", 0.98, 3.6, 1.84, "GET /v1/customers", 5.0, "srv dim"))
    s.add(*(s.dot(1.25 + n * 0.4, 3.6, 0.95, 1.7, f"led g{n % 3}") for n in range(4)))

    s.add(s.slab(6.4, 0, 4.4, 4.4, "TILTMETER"))
    entry = [s.p(3.6, 2.2, 1.1), s.p(4.7, 2.2, 0.85), s.p(6.5, 2.2, 0.85), s.p(7.05, 2.2, 0.95)]
    for n in range(4):
        s.add(s.mover(lambda: cube(s, 0.62, MINT, stripes=True), f"resp r{n}", entry[0], path=path_attr(entry)))
    s.add(s.mover(lambda: cube(s, 0.62, RED, stripes=True), "resp odd", entry[0], path=path_attr(entry)))
    device(s, 7.1, 0.7, 0.5, 3, 3, 1.4)

    s.add(s.slab(12.8, 0, 4.4, 4.4, "YOUR CI AND AGENTS"))
    s.add(s.box(13.3, 0.4, 0.5, 1.6, 1.6, 1.1, cls="ci"))
    s.add(s.text("left", 13.45, 2.0, 0.85, "CI", 7.5, "srv"))
    s.add(s.ring(14.1, 1.2, 1.6, 0.42, "ci-light"))
    s.add(s.box(13.3, 2.4, 0.5, 1.6, 1.6, 1.1, cls="agent"))
    s.add(s.text("left", 13.45, 4.0, 0.85, "agent", 7.5, "srv"))
    s.add(*(s.ring(13.75 + n * 0.55, 3.2, 1.6, 0.12, "eye") for n in range(2)))

    for name, y in (("to-ci", 1.2), ("to-agent", 3.2)):
        route = [s.p(10.1, y, 0.9), s.p(11.0, y, 0.6), s.p(12.9, y, 0.6), s.p(13.4, y, 0.85)]
        s.add(s.mover(lambda: s.dot(0, 0, 0, 3.6, "alert"), f"ping {name}", route[0], path=path_attr(route)))

    s.add(s.billboard(14.1, 1.2, 1.6, [["exit 2"], ["exit 0"]], "ci-bb", 8.5, stem=0.7))
    s.add(s.billboard(12.3, 3.6, 0.6, [["has_drifted: true"]], "agent-bb", 8.5, stem=1.0))
    s.add(s.billboard(5.8, 2.3, 0.6, [["phone → phone_number"]], "diff-bb", 8.5, stem=0.55))
    s.add(s.billboard(10.6, 1.0, 3.0, [["tiltmeter fix", "PR opened"], ["tiltmeter fix", "Merged"]], "fix-bb", 8.5))
    return s.svg("A third-party API's responses reach Tiltmeter. One comes back with phone renamed to "
                 "phone_number; Tiltmeter fails CI, tells the agent, and opens the pull request that fixes the code.")


# -- 3. Already shipped: scan -----------------------------------------------------


def scan() -> str:
    s = Iso(22)
    s.add(s.floor(-2, 13, -1, 7))
    s.add(s.slab(-0.6, 1.3, 2.8, 2.8, "SCAN"))
    device(s, -0.2, 1.7, 0.5, 2.0, 2.0, 1.2)

    s.add(s.slab(3.4, 0, 7.8, 5.4, "YOUR REPOSITORY"))
    hits = {(0, 2): "/rest/api/3/search", (2, 1): "files.upload", (3, 0): "llama-3.3-70b-versatile"}
    stems = {(0, 2): 1.0, (2, 1): 2.4, (3, 0): 1.0}
    spots = {}
    for i, j in sorted(((i, j) for i in range(4) for j in range(3)), key=lambda q: (q[0] + q[1], q[0])):
        x, y = 3.9 + i * 1.8, 0.45 + j * 1.65
        cls = f"file hit f{i}{j}" if (i, j) in hits else "file"
        at = f' data-at="{(x + 0.67 - 3.6) / 7.4:.2f}"'
        s.add(s.box(x, y, 0.5, 1.35, 1.3, 0.16, cls=cls, top_cls="tt", extra=glyphs(s, x + 0.2, y + 0.3, 0.66, gap=0.28), attrs=at))
        spots[(i, j)] = (x + 0.67, y + 0.65)

    beam = s.quad([(3.6, 0.1, 0.5), (3.6, 5.3, 0.5), (3.6, 5.3, 2.4), (3.6, 0.1, 2.4)], "curtain")
    beam += s.line([(3.6, 0.1, 2.4), (3.6, 5.3, 2.4)], "curtain-edge")
    beam += s.quad([(3.4, 0.1, 0.7), (3.8, 0.1, 0.7), (3.8, 5.3, 0.7), (3.4, 5.3, 0.7)], "curtain-floor")
    s.add(f'<g class="beam" data-dx="{7.4 * s.c:.1f}" data-dy="{7.4 * s.s:.1f}">{beam}</g>')

    for (i, j), words in sorted(hits.items()):
        x, y = spots[(i, j)]
        s.add(s.billboard(x, y, 0.66, [[words]], f"hit-tag t{i}{j}", 8.5, stem=stems[(i, j)]))
    s.add(s.billboard(9.4, -0.6, 3.5, [["$ uvx tiltmeter scan", "✗ 3 known API changes affect this repo"]], "result", 8.5))
    return s.svg("tiltmeter scan sweeps a repository and marks the three files that still use API changes "
                 "that already shipped: a retired Groq model, Jira's removed search endpoint and Slack's files.upload.")


# -- 4. The pull request ----------------------------------------------------------


def fix() -> str:
    s = Iso(22)
    s.add(s.floor(-4, 15, -1, 6))
    s.add(s.slab(-3.2, 1.3, 2.2, 2.2, "AGENT", h=0.4))
    s.add(s.slab(0, 0, 5.6, 4.6, "FRESH WORKTREE"))
    files = {"ok1": (0.7, 0.8), "dead": (2.6, 0.8), "broken": (0.7, 2.6), "ok2": (2.6, 2.6)}
    for name, (x, y) in files.items():
        s.add(s.box(x, y, 0.5, 1.6, 1.5, 0.17, cls=f"file {name}", top_cls="tt",
                    extra=glyphs(s, x + 0.25, y + 0.35, 0.67, long=1.0, short=0.6, gap=0.32)))
    home = s.p(-2.1, 2.4, 0.7)
    land = s.p(1.5, 3.35, 0.97)
    s.add(s.mover(lambda: cube(s, 0.6, LIGHT), "agent-cube", home, arc=s.arc(home, land, 46)))
    s.add(s.box(0.3, 0.3, 0.5, 5.0, 4.0, 1.25, GLASS, cls="glass"))
    s.add(s.billboard(3.4, 1.55, 0.67, [["unused", "skipped"]], "dead-bb", 8, stem=2.1))
    s.add(s.billboard(1.5, 3.35, 0.67, [["+1 −1"]], "edit-bb", 8.5, stem=1.3))

    s.add(s.slab(6.3, 0.3, 1.3, 4.0, "TESTS", h=0.4, face="right"))
    for k in range(5):
        s.add(s.box(6.65, 0.6 + k * 0.72, 0.4, 0.55, 0.55, 0.55, cls=f"test t{k}", top_cls="tt"))

    s.add(s.slab(9.8, 0, 4.4, 4.4, "PULL REQUEST"))
    s.add(s.box(10.4, 0.6, 0.5, 3.2, 3.2, 0.25, cls="pr-desk"))
    takeoff = s.p(2.8, 2.3, 2.9)
    landing = s.p(12.0, 2.2, 1.1)
    flight = s.arc(takeoff, landing, 40)

    def card() -> str:
        return s.billboard(0, 0, 0, [["fix: retired model", "PR · opened"], ["fix: retired model", "PR · merged"]], "card", 8.5)

    lx, ly = landing
    s.xs += [lx - 70, lx + 70]
    s.ys += [ly - 44]
    s.add(s.mover(card, "pr-card", landing, arc=flight))
    return s.svg("An agent edits the affected file in a sandboxed worktree, skips a file nothing imports, "
                 "runs the tests, and the pull request travels out and is merged.")


SCENES = {"provider": provider, "drift": drift, "scan": scan, "fix": fix}


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
