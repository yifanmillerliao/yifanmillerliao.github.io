#!/usr/bin/env python3
"""
Rebuild the photography page's images and data.

  python3 tools/build_photos.py

Reads the originals in photos-source/, and for each one:
  - renames it to YYYY-MM-DD-NN.jpg from its EXIF capture date (an id, not a
    claim: the camera clock stays on Beijing time abroad, so check the date
    field in photos.yml before publishing),
  - writes two web copies, converted to sRGB and stripped of every metadata
    segment, including the GPS coordinates several of these carry,
  - adds an entry to photos.yml if the photo is new, keeping any words that
    are already there. Nothing written by hand is ever overwritten.
  - regenerates _photo-grid.qmd, the markup the page includes.

Originals are never copied into _site; see the resources block in _quarto.yml.
"""
import hashlib, os, re, struct, subprocess, sys, pathlib

ROOT   = pathlib.Path(__file__).resolve().parent.parent
SRC    = ROOT / "photos-source"
GRID   = ROOT / "assets/photos/grid"
FULL   = ROOT / "assets/photos/full"
DATA   = ROOT / "photos.yml"
PARTIAL= ROOT / "_photo-grid.qmd"
GRID_W, FULL_W = 800, 2000
SRGB = "/System/Library/ColorSync/Profiles/sRGB Profile.icc"

# ---------- JPEG / EXIF ----------------------------------------------------
def segments(d):
    i = 2
    while i < len(d) - 1 and d[i] == 0xFF:
        m = d[i + 1]
        if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7:
            i += 2; continue
        ln = struct.unpack(">H", d[i + 2:i + 4])[0]
        yield i, m, d[i + 4:i + 2 + ln], ln
        if m == 0xDA: break
        i += 2 + ln

def strip_metadata(src, dst):
    """Copy the compressed image across without any APPn or comment segment."""
    d = pathlib.Path(src).read_bytes()
    out = bytearray(d[:2]); i = 2
    while i < len(d) - 1:
        if d[i] != 0xFF: break
        m = d[i + 1]
        if m == 0xD9: out += d[i:]; break
        if m == 0xDA: out += d[i:]; break
        ln = struct.unpack(">H", d[i + 2:i + 4])[0]
        drop = m in range(0xE1, 0xF0) or m == 0xFE      # APP1..APP15 and COM
        if not drop: out += d[i:i + 2 + ln]
        i += 2 + ln
    pathlib.Path(dst).write_bytes(bytes(out))

def exif_date(path):
    d = pathlib.Path(path).read_bytes()
    for _, m, body, _ in segments(d):
        if m == 0xE1 and body[:6] == b"Exif\0\0":
            t = body[6:]; le = t[:2] == b"II"
            u = lambda o, f: struct.unpack(("<" if le else ">") + f, t[o:o + struct.calcsize(f)])[0]
            def walk(off, depth=0):
                if depth > 3 or off + 2 > len(t): return None
                for k in range(u(off, "H")):
                    e = off + 2 + k * 12
                    tag, typ, cnt = u(e, "H"), u(e + 2, "H"), u(e + 4, "I")
                    if tag == 0x8769:
                        r = walk(u(e + 8, "I"), depth + 1)
                        if r: return r
                    if tag in (0x9003, 0x0132) and typ == 2:
                        return t[u(e + 8, "I"):u(e + 8, "I") + cnt].split(b"\0")[0].decode("ascii", "replace")
                return None
            try:
                v = walk(u(4, "I"))
                if v: return v[:10].replace(":", "-")
            except Exception: pass
    return None

def dims(path):
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
                         capture_output=True, text=True).stdout
    w = re.search(r"pixelWidth:\s*(\d+)", out); h = re.search(r"pixelHeight:\s*(\d+)", out)
    return (int(w.group(1)), int(h.group(1))) if w and h else (0, 0)

def web_copy(src, dst, long_edge):
    tmp = f"/tmp/_pc_{os.getpid()}.jpg"
    cmd = ["sips", "-Z", str(long_edge), "-s", "format", "jpeg", "-s", "formatOptions", "78"]
    if os.path.exists(SRGB):                      # several originals are Display P3
        cmd += ["--matchTo", SRGB]
    subprocess.run(cmd + [str(src), "--out", tmp], capture_output=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    strip_metadata(tmp, dst)
    os.remove(tmp)

# ---------- photos.yml -----------------------------------------------------
def read_yaml(path):
    """Small reader for the flat list this file holds. No dependency needed."""
    if not path.exists(): return []
    items, cur = [], None
    for raw in path.read_text().splitlines():
        if raw.startswith("- "):
            cur = {}; items.append(cur); raw = "  " + raw[2:]
        if cur is None or not raw.strip() or raw.strip().startswith("#"): continue
        m = re.match(r"\s+([a-z_]+):\s*(.*)$", raw)
        if m:
            v = m.group(2).strip()
            if len(v) > 1 and v[0] == v[-1] == '"': v = v[1:-1]
            cur[m.group(1)] = v
    return items

def q(s):  # always quote, so an apostrophe or colon in a caption is safe
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'

FIELDS = ["id", "image", "full", "width", "height", "title", "description",
          "place", "date", "alt", "camera"]

def write_yaml(items):
    out = ["# One entry per photograph. File order is display order — reorder freely.",
           "#",
           "# Generated fields (id, image, full, width, height) are rewritten by",
           "# tools/build_photos.py. The words are yours: title, description, place,",
           "# date, alt, camera. Leave a field empty and the page omits it.",
           "#",
           "# date is prefilled from EXIF. The camera clock stays on Beijing time",
           "# abroad, so a photo taken late in the day overseas can be dated a day",
           "# ahead. Correct it here; nothing regenerates it.",
           ""]
    for it in items:
        first = True
        for k in FIELDS:
            v = it.get(k, "")
            lead = "- " if first else "  "; first = False
            out.append(f"{lead}{k}: {q(v) if v != '' else '\"\"'}")
        out.append("")
    DATA.write_text("\n".join(out))

# ---------- page markup ----------------------------------------------------
def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))

def write_partial(items):
    rows = []
    for it in items:
        if not it.get("image"): continue
        w, h = it.get("width", ""), it.get("height", "")
        ratio = f"{w} / {h}" if w and h else "3 / 2"
        gl = []
        if it.get("title"): gl.append("title: " + str(it["title"]).replace(";", ","))
        desc_bits = [b for b in (it.get("description"), " · ".join(
            [x for x in (it.get("place"), it.get("date"), it.get("camera")) if x])) if b]
        if desc_bits: gl.append("description: " + " — ".join(desc_bits).replace(";", ","))
        meta_left, meta_right = it.get("place", ""), it.get("date", "")
        cap = []
        if it.get("title"): cap.append(f'<span class="photo-cap__title">{esc(it["title"])}</span>')
        if it.get("description"): cap.append(f'<span class="photo-cap__desc">{esc(it["description"])}</span>')
        if meta_left or meta_right:
            cap.append('<span class="photo-cap__meta">'
                       f'<span>{esc(meta_left)}</span><span>{esc(meta_right)}</span></span>')
        # Caption beside a portrait, under a landscape.
        pos = "right" if (w and h and int(h) > int(w)) else "bottom"
        rows.append(
f'''<figure class="photo-item">
  <a class="lightbox photo-item__link" href="{esc(it["full"])}" data-gallery="photos"
     data-desc-position="{pos}" data-glightbox="{esc("; ".join(gl))}">
    <img src="{esc(it["image"])}" srcset="{esc(it["image"])} {GRID_W}w, {esc(it["full"])} {FULL_W}w"
         sizes="(min-width: 1000px) 32vw, (min-width: 620px) 48vw, 92vw"
         width="{w}" height="{h}" style="aspect-ratio: {ratio}" loading="lazy" decoding="async"
         alt="{esc(it.get("alt",""))}">
  </a>
  {'<figcaption class="photo-cap">' + "".join(cap) + "</figcaption>" if cap else ""}
</figure>''')
    years = sorted({str(it.get("date", ""))[:4] for it in items if it.get("date")})
    span = years[0] if len(years) == 1 else (f"{years[0]}–{years[-1]}" if years else "")
    count = len([i for i in items if i.get("image")])
    meta = f"{count} photograph{'s' if count != 1 else ''}" + (f", {span}" if span else "")
    PARTIAL.write_text(
        "```{=html}\n"
        f'<p class="photo-count mono">{esc(meta)}</p>\n'
        '<div class="photo-grid" data-columns="3">\n' + "\n".join(rows) + "\n</div>\n"
        "```\n")

# ---------- main -----------------------------------------------------------
def main():
    if not SRC.is_dir():
        sys.exit(f"no {SRC}")
    existing = {it["id"]: it for it in read_yaml(DATA) if it.get("id")}
    order    = [it["id"] for it in read_yaml(DATA) if it.get("id")]
    seen, used, fresh = {}, set(), []

    files = sorted(p for p in SRC.iterdir()
                   if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    for p in files:
        sha = hashlib.sha1(p.read_bytes()).hexdigest()[:12]
        if sha in seen:
            print(f"  duplicate, skipped: {p.name} (same file as {seen[sha]})"); continue
        seen[sha] = p.name
        date = exif_date(p) or "0000-00-00"
        n = 1
        while f"{date}-{n:02d}" in used: n += 1
        pid = f"{date}-{n:02d}"; used.add(pid)
        if p.name != pid + p.suffix.lower():
            target = p.with_name(pid + ".jpg")
            p.rename(target); p = target
            print(f"  renamed → {p.name}")
        g, f = GRID / f"{pid}.jpg", FULL / f"{pid}.jpg"
        if not g.exists(): web_copy(p, g, GRID_W)
        if not f.exists(): web_copy(p, f, FULL_W)
        w, h = dims(g)          # the served file's own size, not the original's
        it = existing.get(pid, {})
        it.update({"id": pid, "image": f"assets/photos/grid/{pid}.jpg",
                   "full": f"assets/photos/full/{pid}.jpg", "width": w, "height": h})
        it.setdefault("date", date)
        for k in ("title", "description", "place", "alt", "camera"): it.setdefault(k, "")
        existing[pid] = it
        if pid not in order: fresh.append(pid)

    items = [existing[i] for i in order if i in existing] + [existing[i] for i in fresh]
    items = [it for it in items if (SRC / f"{it['id']}.jpg").exists()]
    write_yaml(items); write_partial(items)
    print(f"  {len(items)} photographs · photos.yml and _photo-grid.qmd rewritten")

if __name__ == "__main__":
    main()
