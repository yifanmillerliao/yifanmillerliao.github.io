#!/usr/bin/env python3
"""
Rebuild the chess project's cover image.

  python3 tools/build_project_card.py

A chessboard on the left dissolving into the game's evaluation curve on the
right. Writes assets/img/project-card-chess@2x.png (the master) and the
1200x910 copy the card actually uses.

The canvas is authored at 1.32, the aspect of the card's image box, so the
cover is not cropped at the sides there and the board can sit flush left.
"""
import pathlib, subprocess, sys

ROOT  = pathlib.Path(__file__).resolve().parent.parent
BOARD = ROOT / "assets/img/source/card_fig_1.png"
OUT2X = ROOT / "assets/img/project-card-chess@2x.png"
OUT1X = ROOT / "projects/lichess-evaluation-selection/images/card_thumbnail.png"
OUTJPG= ROOT / "assets/img/project-card-chess.jpg"
WORK  = pathlib.Path("/tmp/_card_build"); WORK.mkdir(exist_ok=True)

W, H = 1200, 910
MID, SCALE = 455.0, 100.0         # y of eval 0, and pixels per pawn. The scale
                                  # is set so the game's own swing, -2.7 to
                                  # +3.6, reaches most of the frame; the grid
                                  # then rules the rest of it rather than
                                  # standing in for a curve that is too small.
X0, X1 = 470.0, 1098.0            # the curve's span; the gutter past X1 holds
                                  # the axis labels
FILL_FROM = 585.0                 # tinted area starts after the blend, so it
                                  # never washes over the board
INK, LINE = "#2B2723", "#E5DFD5"
GRIDMAJ = "#DAD3C7"               # every second line, the ones that carry a number
MUT = "#8C837A"
COL = {"blunder": "#C0392B", "mistake": "#E08A3C", "great": "#3E7CA6"}

# A plausible game: quiet opening, a mistake, a blunder that flips it, a great
# move that holds the position, another mistake, a blunder back the other way.
EVALS = [
 (.20,None),(.15,None),(.25,None),(.18,None),(.30,None),(.22,None),(.35,None),(.28,None),
 (1.15,"mistake"),(1.05,None),(1.20,None),(1.10,None),(1.25,None),(1.15,None),
 (-2.60,"blunder"),(-2.45,None),(-2.70,None),(-2.55,None),(-2.65,None),(-2.50,None),
 (-2.55,"great"),(-2.60,None),(-2.45,None),(-2.55,None),(-2.40,None),(-2.50,None),
 (-1.20,"mistake"),(-1.30,None),(-1.15,None),(-1.25,None),(-1.10,None),(-1.20,None),
 (3.40,"blunder"),(3.30,None),(3.45,None),(3.35,None),(3.50,None),(3.40,None),
 (3.45,"great"),(3.55,None),
]
# Which dot carries a word. One of each kind: the colour only has to be taught
# once, and six labels would crowd the picture.
LABELLED = {8: ("mistake", "MISTAKE",  22,  -34, "start"),
            14: ("blunder", "BLUNDER",  22,   46, "start"),
            38: ("great",   "GREAT",   -20, -40, "middle")}
# GREAT sits over its own dot, nudged into the gap between the red dot at ply
# 32 and the axis gutter: spelled out in full and right-aligned it read as the
# red dot's label, and dead-centred it ran into the "+4".

px = lambda i: X0 + (X1 - X0) * i / (len(EVALS) - 1)
CLAMP = (MID - 20) / SCALE        # an off-the-chart eval stops at the frame edge
MAXEV = int(MID // SCALE)          # the outermost whole pawn the canvas holds
py = lambda e: MID - max(-CLAMP, min(CLAMP, e)) * SCALE
gy = lambda e: MID - e * SCALE

def svg():
    pts  = [(px(i), py(e)) for i, (e, _) in enumerate(EVALS)]
    line = " ".join(("M" if i == 0 else "L") + f"{x:.1f} {y:.1f}" for i, (x, y) in enumerate(pts))
    area = (f"M{pts[0][0]:.1f} {MID:.1f} " +
            " ".join(f"L{x:.1f} {y:.1f}" for x, y in pts) +
            f" L{pts[-1][0]:.1f} {MID:.1f} Z")

    grid, labels = [], []
    for ev in range(MAXEV, -MAXEV - 1, -1):
        if ev == 0: continue                      # the zero line is drawn heavier below
        y, major = gy(ev), ev % 2 == 0
        grid.append(f'<line x1="{X0-34:.1f}" y1="{y:.1f}" x2="{X1+14:.1f}" y2="{y:.1f}" '
                    f'stroke="{GRIDMAJ if major else LINE}" '
                    f'stroke-width="{1.7 if major else 1.2}"/>')
    for ev in range(MAXEV - MAXEV % 2, -MAXEV - 1, -2):
        y = gy(ev)
        txt = "0" if ev == 0 else (f"+{ev}" if ev > 0 else f"−{abs(ev)}")
        labels.append(f'<text x="{X1+30:.1f}" y="{y+9:.1f}" class="ax">{txt}</text>')

    dots, words = [], []
    for i, (e, kind) in enumerate(EVALS):
        if not kind: continue
        x, y = px(i), py(e)
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="{COL[kind]}" '
                    f'stroke="#F5F2EC" stroke-width="3.4"/>')
        if i in LABELLED:
            _, word, dx, dy, anchor = LABELLED[i]
            words.append(f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" class="ev" '
                         f'text-anchor="{anchor}" fill="{COL[kind]}">{word}</text>')

    return f'''<svg class="chart-svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"
     xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="a"><rect x="{FILL_FROM}" y="0" width="{W-FILL_FROM}" height="{MID:.1f}"/></clipPath>
    <clipPath id="b"><rect x="{FILL_FROM}" y="{MID:.1f}" width="{W-FILL_FROM}" height="{H-MID:.1f}"/></clipPath>
    <!-- An SVG mask reads luminance, so the stops have to be white; with the
         default black they hide everything they cover. -->
    <linearGradient id="fade" x1="{FILL_FROM}" x2="{FILL_FROM+150}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#fff" stop-opacity="0"/>
      <stop offset="1" stop-color="#fff" stop-opacity="1"/>
    </linearGradient>
    <mask id="fillMask"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>
  </defs>
  <g mask="url(#fillMask)">{"".join(grid)}</g>
  <g mask="url(#fillMask)">
    <path d="{area}" fill="rgba(196,98,60,.17)" clip-path="url(#a)"/>
    <path d="{area}" fill="rgba(110,129,104,.19)" clip-path="url(#b)"/>
  </g>
  <line x1="{X0-34:.1f}" y1="{MID:.1f}" x2="{X1+14:.1f}" y2="{MID:.1f}"
        stroke="rgba(43,39,35,.34)" stroke-width="1.9"/>
  <g mask="url(#fillMask)">{"".join(labels)}</g>
  <path d="{line}" fill="none" stroke="{INK}" stroke-width="4"
        stroke-linejoin="round" stroke-linecap="round"/>
  {"".join(dots)}
  {"".join(words)}
</svg>'''

HTML = '''<!doctype html><meta charset=utf-8>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  html,body{{margin:0;padding:0}}
  .card{{position:relative;width:{W}px;height:{H}px;background:#F5F2EC;overflow:hidden}}
  /* Board: flush left, filling top to bottom, scaled by height so the squares
     stay square. Shifted 4px left to cut the dark border the source carries.
     The mask is fully transparent by 62%, while the board material only ends
     at 76%, so no square or edge survives into the blend. */
  .board{{position:absolute;inset:0;
    background:url({board}) -4px center/auto {H}px no-repeat;
    -webkit-mask-image:linear-gradient(97deg,#000 0%,#000 33%,rgba(0,0,0,.88) 42%,rgba(0,0,0,.55) 50%,rgba(0,0,0,.22) 56%,transparent 62%);
            mask-image:linear-gradient(97deg,#000 0%,#000 33%,rgba(0,0,0,.88) 42%,rgba(0,0,0,.55) 50%,rgba(0,0,0,.22) 56%,transparent 62%)}}
  .chart{{position:absolute;inset:0;
    -webkit-mask-image:linear-gradient(97deg,transparent 34%,rgba(0,0,0,.30) 42%,rgba(0,0,0,.80) 52%,#000 60%,#000 100%);
            mask-image:linear-gradient(97deg,transparent 34%,rgba(0,0,0,.30) 42%,rgba(0,0,0,.80) 52%,#000 60%,#000 100%)}}
  .chart-svg{{display:block}}
  /* Inline, not an <img>, so the SVG can use the site's monospace. */
  text.ax{{font-family:"IBM Plex Mono",monospace;font-size:25px;fill:{mut};letter-spacing:.04em}}
  /* The words sit over the grid now, so they carry a knockout of the
     background rather than letting a hairline run through the letters. */
  text.ev{{font-family:"IBM Plex Mono",monospace;font-size:25px;font-weight:500;letter-spacing:.12em;
    paint-order:stroke;stroke:#F5F2EC;stroke-width:7px;stroke-linejoin:round}}
</style>
<div class="card"><div class="board"></div><div class="chart">{svg}</div></div>
'''

def main():
    if not BOARD.exists(): sys.exit(f"missing {BOARD}")
    page = WORK / "compose.html"
    (WORK / "board.png").write_bytes(BOARD.read_bytes())
    page.write_text(HTML.format(W=W, H=H, board="board.png", mut=MUT, svg=svg()))
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                    "--force-device-scale-factor=2", f"--window-size={W},{H}",
                    "--virtual-time-budget=12000", f"--screenshot={OUT2X}",
                    "file://" + str(page)], capture_output=True)
    for out, size, q in ((OUT1X, W, None), (OUTJPG, 1600, 84)):
        tmp = WORK / "tmp.png"
        subprocess.run(["sips", "-Z", str(size), "--out", str(tmp), str(OUT2X)], capture_output=True)
        if q:
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(q),
                            "--out", str(out), str(tmp)], capture_output=True)
        else:
            out.write_bytes(tmp.read_bytes())
    print(f"  wrote {OUT2X.name}, {OUT1X.name}, {OUTJPG.name}")

if __name__ == "__main__":
    main()
