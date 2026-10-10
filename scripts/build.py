#!/usr/bin/env python3
"""Scan httpdocs/*/index.html, write pages.json, OG images, and social meta in head."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def write_public(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o644)

ROOT = Path(__file__).resolve().parents[1]
HTTPDOCS = ROOT / "httpdocs"
SITE_JSON = HTTPDOCS / "site.json"
PAGES_JSON = HTTPDOCS / "pages.json"
OG_DIR = HTTPDOCS / "images" / "og"
THUMB_DIR = HTTPDOCS / "images" / "thumbs"
SHOTS_JSON = ROOT / "scripts" / "shots.json"
CACHE_DIR = ROOT / ".cache" / "shots"
SHOT_VERSION = "2"  # ophogen om alle screenshots opnieuw te maken
# "zelfportret" is de oude URL van de fable-wand: alleen een doorverwijzing
SKIP_DIRS = {"images", "css", "js", "assets", "zelfportret"}

W, H = 1200, 630
CREAM = (246, 241, 228)
MUTED = (180, 172, 158)

SOCIAL_START = "<!-- nunki:social -->"
SOCIAL_END = "<!-- /nunki:social -->"
NAV_START = "<!-- nunki:nav -->"
NAV_END = "<!-- /nunki:nav -->"
MARK_START = "<!-- nunki:mark -->"
MARK_END = "<!-- /nunki:mark -->"

# De wanden staan in twee series: de zelfportretten van de modellen, en de andere wanden.
SERIES = [
    ("self", "zelfportretten", lambda p: p["slug"].startswith("zelfportret-")),
    ("walls", "wanden", lambda p: not p["slug"].startswith("zelfportret-")),
]


def series_of(pages: list[dict]) -> list[tuple[str, str, list[dict]]]:
    out = []
    for key, label, test in SERIES:
        items = sorted((p for p in pages if test(p)), key=lambda p: p["title"].casefold())
        out.append((key, label, items))
    return out


def load_site() -> dict:
    data = json.loads(SITE_JSON.read_text(encoding="utf-8"))
    base = (data.get("baseUrl") or "").rstrip("/")
    env = __import__("os").environ.get("NUNKI_BASE_URL", "").rstrip("/")
    if env:
        base = env
    data["baseUrl"] = base
    return data


def slug_dirs() -> list[Path]:
    out = []
    for p in sorted(HTTPDOCS.iterdir()):
        if not p.is_dir() or p.name in SKIP_DIRS:
            continue
        if (p / "index.html").is_file():
            out.append(p)
    return out


def parse_theme(html: str) -> str:
    m = re.search(r"background:(#[0-9a-fA-F]{3,8})", html)
    return m.group(1) if m else "#181410"


def parse_comment_subtitle(html: str) -> str | None:
    m = re.search(
        r"//\s*-+\s*\n//\s*[^\n]+—\s*([^\n]+)",
        html,
        re.MULTILINE,
    )
    if not m:
        return None
    line = m.group(1).strip()
    if line.endswith("."):
        line = line[:-1]
    return line.strip()


def parse_page(slug: str, html: str) -> dict:
    tm = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    raw = (tm.group(1).strip() if tm else slug)
    title, subtitle = raw, None
    if " · " in raw:
        title, subtitle = raw.split(" · ", 1)
        title, subtitle = title.strip(), subtitle.strip()
    if not subtitle:
        subtitle = parse_comment_subtitle(html) or ""
    theme = parse_theme(html)
    path = f"/{slug}/"
    og_image = f"/images/og/{slug}.jpg"
    return {
        "slug": slug,
        "path": path,
        "title": title,
        "subtitle": subtitle,
        "theme": theme,
        "ogImage": og_image,
    }


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Avenir Next.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            try:
                index = 1 if bold and path.endswith(".ttc") else 0
                return ImageFont.truetype(path, size, index=index)
            except OSError:
                continue
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    cur = words[0]
    for word in words[1:]:
        trial = f"{cur} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def generate_og_fallback(page: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bg = hex_to_rgb(page["theme"])
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # soft vignette / band
    for y in range(H):
        t = y / H
        shade = 1.0 - 0.22 * t
        row = tuple(int(c * shade) for c in bg)
        draw.line([(0, y), (W, y)], fill=row)

    accent = tuple(min(255, c + 28) for c in bg)
    draw.rectangle([0, H - 8, W, H], fill=accent)

    slug = page["slug"]
    extra = HTTPDOCS / "images" / "claude-self-portrait-website.webp"
    if slug == "zelfportret" and extra.is_file():
        try:
            art = Image.open(extra).convert("RGB")
            art.thumbnail((520, H), Image.Resampling.LANCZOS)
            img.paste(art, (W - art.width - 48, (H - art.height) // 2))
        except OSError:
            pass

    title_font = load_font(72, bold=True)
    sub_font = load_font(32)
    brand_font = load_font(22)

    margin_x, margin_y = 64, 72
    max_text_w = 640 if slug == "zelfportret" else W - margin_x * 2

    title = page["title"]
    subtitle = page.get("subtitle") or ""

    draw.text((margin_x, margin_y), title, font=title_font, fill=CREAM)

    y = margin_y + 88
    for line in wrap_text(subtitle, sub_font, max_text_w, draw):
        draw.text((margin_x, y), line, font=sub_font, fill=MUTED)
        y += 40

    draw.text((margin_x, H - 56), "nunkichannels", font=brand_font, fill=accent)

    img.save(out_path, "JPEG", quality=88, optimize=True, progressive=True)



# ---------------------------------------------------------------------------
# Screenshots van de wanden (headless Chrome) → social cards
# ---------------------------------------------------------------------------

def find_chrome() -> str | None:
    candidates = [
        os.environ.get("NUNKI_CHROME"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("chrome"),
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    return None


def clean_for_shot(html: str) -> str:
    """HTML zonder social-meta en zonder externe badges (Julius), voor reproduceerbare shots."""
    html = re.sub(
        re.escape(SOCIAL_START) + r".*?" + re.escape(SOCIAL_END), "", html, flags=re.DOTALL
    )
    html = re.sub(
        re.escape(NAV_START) + r".*?" + re.escape(NAV_END), "", html, flags=re.DOTALL
    )
    html = re.sub(
        re.escape(MARK_START) + r".*?" + re.escape(MARK_END), "", html, flags=re.DOTALL
    )
    return strip_julius(html)


def load_shot_positions() -> dict[str, int]:
    if not SHOTS_JSON.is_file():
        return {}
    data = json.loads(SHOTS_JSON.read_text(encoding="utf-8"))
    return {k: int(v) for k, v in data.items() if not k.startswith("_")}


def scroll_injection(html: str, y: int) -> str:
    """Zet de wand op positie y (zonder echt te scrollen) en activeer de tegels die in beeld komen."""
    m = re.search(r"const LW=(\d+)", html)
    lw = int(m.group(1)) if m else 1600
    k = W / lw
    inj = (
        "<style>html,body{overflow:hidden!important;height:100%!important}"
        f"#wall{{position:fixed!important;left:0;top:{-y * k:.2f}px}}</style>"
        "<script>if(typeof TILES!=='undefined')TILES.forEach(t=>{"
        f"if(t.y0>{y}-1300&&t.y0<{y}+{int(H / k) + 200})t.active=true}});</script>"
    )
    return html.replace("</body>", inj + "</body>", 1)


def capture_page(slug: str, html: str, y: int = 0) -> Image.Image | None:
    """Screenshot (1200x630) van de wand op scrollpositie y, na het intekenen. Gecachet op inhoud."""
    clean = clean_for_shot(html)
    key = hashlib.sha1(f"{SHOT_VERSION}|{y}|{clean}".encode("utf-8")).hexdigest()[:12]
    cached = CACHE_DIR / f"{slug}-{key}.png"
    if cached.is_file():
        return Image.open(cached).convert("RGB")

    chrome = find_chrome()
    if not chrome:
        print(f"  ! geen Chrome gevonden, fallback-kaart voor {slug} (zet NUNKI_CHROME)")
        return None

    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "index.html"
        out = Path(td) / "shot.png"
        src.write_text(scroll_injection(clean, y) if y else clean, encoding="utf-8")
        try:
            subprocess.run(
                [
                    chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    "--force-device-scale-factor=1",
                    f"--window-size={W},{H}",
                    "--virtual-time-budget=20000",
                    f"--screenshot={out}",
                    src.as_uri() + "?fast",
                ],
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"  ! screenshot van {slug} mislukt: {e}")
            return None
        if not out.is_file():
            print(f"  ! screenshot van {slug} mislukt")
            return None
        img = Image.open(out).convert("RGB")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        for old in CACHE_DIR.glob(f"{slug}-*.png"):
            old.unlink()
        img.save(cached, "PNG")
        return img


def cover(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    resized = img.resize((max(w, round(img.width * scale)), max(h, round(img.height * scale))), Image.Resampling.LANCZOS)
    left = (resized.width - w) // 2
    top = (resized.height - h) // 2
    return resized.crop((left, top, left + w, top + h))


def luminance(img: Image.Image) -> float:
    px = img.convert("L").resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    return float(px)


def generate_og(page: dict, site: dict, shot: Image.Image | None, out_path: Path) -> None:
    """Social card: screenshot van de wand, met een rustig label onderin."""
    if shot is None:
        generate_og_fallback(page, out_path)
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = cover(shot, W, H).convert("RGBA")

    band = 150
    strip = img.crop((0, H - band, W, H))
    light = luminance(strip) > 128
    tone = (246, 241, 228) if not light else (42, 37, 31)
    wash = (24, 20, 17) if not light else (246, 241, 228)

    grad = Image.new("RGBA", (W, band), (*wash, 0))
    gp = grad.load()
    for y in range(band):
        a = int(170 * (y / band) ** 1.6)
        for x in range(W):
            gp[x, y] = (*wash, a)
    img.alpha_composite(grad, (0, H - band))

    draw = ImageDraw.Draw(img)
    brand = load_font(28, bold=True)
    small = load_font(24)
    draw.text((56, H - 62), site["name"], font=brand, fill=(*tone, 235))
    tag = f"/{page['slug']}/"
    tw = draw.textlength(tag, font=small)
    draw.text((W - 56 - tw, H - 60), tag, font=small, fill=(*tone, 190))

    img.convert("RGB").save(out_path, "JPEG", quality=88, optimize=True, progressive=True)


def generate_index_og(site: dict, rows: list[list[Image.Image]], out_path: Path, tagline: str) -> None:
    """Social card voor de homepage: per serie een rij screenshots, met een naamplaat."""
    from PIL import ImageFilter

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [r[:4] for r in rows if r]
    gap = 8
    paper = (238, 227, 197)
    canvas = Image.new("RGB", (W, H), paper)
    ch = (H - gap * (len(rows) + 1)) // len(rows)
    y = gap
    for row in rows:
        cols = len(row)
        cw = (W - gap * (cols + 1)) // cols
        for c, shot in enumerate(row):
            canvas.paste(cover(shot, cw, ch), (gap + c * (cw + gap), y))
        y += ch + gap

    canvas = canvas.convert("RGBA")
    pw, ph = 520, 88
    px, py = (W - pw) // 2, (H - ph) // 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([px, py + 8, px + pw, py + ph + 8], 10, fill=(24, 20, 17, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    canvas.alpha_composite(shadow)

    plate = ImageDraw.Draw(canvas)
    plate.rounded_rectangle([px, py, px + pw, py + ph], 8, fill=(246, 241, 228, 255))
    plate.rounded_rectangle([px + 8, py + 8, px + pw - 8, py + ph - 8], 4, outline=(42, 37, 31, 40), width=1)

    title_font = load_font(58, bold=True)
    name = site["name"]
    nw = plate.textlength(name, font=title_font)
    plate.text((px + (pw - nw) / 2, py + 12), name, font=title_font, fill=(42, 37, 31, 255))

    canvas.convert("RGB").save(out_path, "JPEG", quality=88, optimize=True, progressive=True)



# ---------------------------------------------------------------------------
# Footer-navigatie onderaan elke wand: kleine kaartjes van de andere wanden
# ---------------------------------------------------------------------------

LOGO_SVG = (
    '<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">'
    '<path d="M18 48V30c0-7 6-12 14-12s12 5 12 12v18" fill="none" stroke="#ac5036" stroke-width="7.5" '
    'stroke-linecap="round" stroke-linejoin="round"/><circle cx="48" cy="15" r="4" fill="#d6b26c"/></svg>'
)

NAV_CSS = """
.nunki-nav{--paper:#eee3c5;--card:#f6f1e4;--ink:#2a251f;--muted:#7a6f5c;--clay:#ac5036;
  position:relative;z-index:2;margin-top:-14px;box-sizing:border-box;
  filter:drop-shadow(0 -8px 14px rgba(0,0,0,.28));
  font-family:"Avenir Next","Helvetica Neue",Helvetica,Arial,sans-serif;color:var(--ink);-webkit-font-smoothing:antialiased}
.nunki-nav *{box-sizing:border-box}
.nunki-sheet{position:relative;padding:clamp(2.6rem,6vw,4rem) clamp(1rem,4vw,2.5rem) clamp(2.2rem,5vw,3.2rem);
  background:radial-gradient(120% 80% at 50% 0%,rgba(255,252,240,.6),transparent 65%),var(--paper);
  clip-path:polygon(__TORN__)}
.nunki-sheet::before{content:"";position:absolute;inset:0;pointer-events:none;opacity:.3;mix-blend-mode:multiply;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 .45  0 0 0 0 .38  0 0 0 0 .25  0 0 0 .5 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")}
.nunki-kicker{position:relative;margin:0 0 clamp(1.6rem,4vw,2.2rem);text-align:center;font-size:clamp(1.5rem,4vw,2rem);line-height:1.1;
  font-family:"Bradley Hand","Segoe Print","Chalkboard SE","Noteworthy","Avenir Next","Helvetica Neue",Helvetica,sans-serif;font-weight:400;text-transform:lowercase;color:var(--ink)}
.nunki-kicker::after{content:"";display:block;width:110px;height:3px;margin:.55rem auto 0;border-radius:3px;background:var(--clay);opacity:.85;transform:rotate(-1deg)}
.nunki-group{position:relative;display:flex;align-items:center;justify-content:center;gap:.9rem;max-width:1000px;margin:0 auto 1.4rem;
  font-family:"Bradley Hand","Segoe Print","Chalkboard SE","Noteworthy","Avenir Next","Helvetica Neue",Helvetica,sans-serif;font-size:1.15rem;line-height:1;
  text-transform:lowercase;color:var(--muted)}
.nunki-group::before,.nunki-group::after{content:"";flex:0 1 70px;height:1px;background:rgba(42,37,31,.16)}
.nunki-grid+.nunki-group{margin-top:clamp(2.2rem,5vw,3rem)}
.nunki-grid{position:relative;list-style:none;margin:0 auto;padding:0;max-width:1000px;display:flex;flex-wrap:wrap;
  justify-content:center;gap:1.9rem 1.4rem}
.nunki-grid li{display:flex;flex:0 1 196px;min-width:min(100%,170px)}
.nunki-card{--tilt:-1deg;position:relative;display:flex;flex-direction:column;width:100%;padding:.5rem .5rem .7rem;color:inherit;text-decoration:none;
  background:var(--card);border-radius:3px;transform:rotate(var(--tilt));
  box-shadow:0 1px 0 rgba(255,255,255,.7) inset,0 1px 2px rgba(42,37,31,.18),0 12px 22px -14px rgba(42,37,31,.55);
  box-shadow:0 1px 0 rgba(255,255,255,.7) inset,0 1px 2px rgba(42,37,31,.18),0 12px 22px -14px color-mix(in srgb,var(--theme,#2a251f) 70%,transparent);
  transition:transform .35s cubic-bezier(.2,.8,.2,1),box-shadow .35s ease}
.nunki-grid li:nth-child(4n+2) .nunki-card{--tilt:.8deg}
.nunki-grid li:nth-child(4n+3) .nunki-card{--tilt:-.4deg}
.nunki-grid li:nth-child(4n+4) .nunki-card{--tilt:1.1deg}
.nunki-card:hover,.nunki-card:focus-visible{transform:rotate(0) translateY(-5px);outline:none;
  box-shadow:0 1px 0 rgba(255,255,255,.7) inset,0 2px 4px rgba(42,37,31,.2),0 22px 30px -16px rgba(42,37,31,.6)}
.nunki-card:focus-visible{outline:2px solid var(--clay);outline-offset:4px}
.nunki-tape{position:absolute;top:-9px;left:50%;width:64px;height:19px;margin-left:-32px;transform:rotate(-2.5deg);background:rgba(214,178,108,.55);
  box-shadow:0 1px 2px rgba(42,37,31,.12);z-index:2}
.nunki-grid li:nth-child(even) .nunki-tape{transform:rotate(2deg)}
.nunki-thumb{display:block;position:relative;overflow:hidden;aspect-ratio:800/420;background:#e6d9b6}
.nunki-thumb::after{content:"";position:absolute;inset:0;pointer-events:none;box-shadow:0 0 0 1px rgba(42,37,31,.16) inset}
.nunki-thumb img{display:block;width:100%;height:auto;aspect-ratio:800/420;object-fit:cover;transition:transform .7s cubic-bezier(.2,.8,.2,1)}
.nunki-card:hover .nunki-thumb img,.nunki-card:focus-visible .nunki-thumb img{transform:scale(1.05)}
.nunki-cap{display:block;padding:.6rem .15rem 0}
.nunki-name{display:block;font-size:1.3rem;line-height:1.1;text-transform:lowercase;
  font-family:"Bradley Hand","Segoe Print","Chalkboard SE","Noteworthy","Avenir Next","Helvetica Neue",Helvetica,sans-serif}
.nunki-sub{display:block;margin-top:.2rem;color:var(--muted);font-size:.8rem;line-height:1.35}
.nunki-home{position:relative;margin:clamp(1.8rem,4vw,2.4rem) 0 0;text-align:center;line-height:0}
.nunki-home-mark{display:inline-flex;align-items:center;height:34px;padding:0 14px 0 6px;box-sizing:border-box;border-radius:17px;
  color:var(--ink);text-decoration:none;background:rgba(246,241,228,.93);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  box-shadow:0 1px 0 rgba(255,255,255,.6) inset,0 0 0 1px rgba(42,37,31,.07),0 8px 20px -12px rgba(0,0,0,.55);
  -webkit-tap-highlight-color:transparent;transition:background-color .3s ease,box-shadow .3s ease,transform .35s cubic-bezier(.2,.8,.2,1)}
.nunki-home-mark svg{display:block;width:24px;height:24px;flex:none;transition:transform .45s cubic-bezier(.2,.8,.2,1)}
.nunki-home-mark .nm-name{display:block;margin-left:7px;white-space:nowrap;font:400 1.06rem/1.25 "Bradley Hand","Segoe Print","Chalkboard SE","Noteworthy","Avenir Next","Helvetica Neue",Helvetica,sans-serif;transform:translateY(1px)}
.nunki-home-mark:hover,.nunki-home-mark:focus-visible{background:rgba(251,248,239,.97);outline:none;transform:translateY(-1px)}
.nunki-home-mark:hover svg,.nunki-home-mark:focus-visible svg{transform:rotate(-8deg)}
.nunki-home-mark:focus-visible{box-shadow:0 0 0 2px var(--clay),0 8px 20px -12px rgba(0,0,0,.55)}
@media (prefers-reduced-motion:reduce){.nunki-card,.nunki-thumb img,.nunki-home-mark,.nunki-home-mark svg{transition:none}}
"""


def torn_edge(seed: int = 11) -> str:
    """Deterministische gescheurde bovenrand voor clip-path (x in %, y in px)."""
    import random

    rnd = random.Random(seed)
    pts = []
    n = 46
    for i in range(n + 1):
        x = i * 100 / n
        y = rnd.uniform(1, 13) if 0 < i < n else rnd.uniform(3, 8)
        pts.append(f"{x:.2f}% {y:.1f}px")
    pts += ["100% 100%", "0 100%"]
    return ", ".join(pts)


def nav_card(p: dict) -> str:
    sub = f'<span class="nunki-sub">{esc(p["subtitle"])}</span>' if p.get("subtitle") else ""
    return f"""      <li><a class="nunki-card" href="{esc(p["path"])}" style="--theme:{esc(p["theme"])}">
        <span class="nunki-tape" aria-hidden="true"></span>
        <span class="nunki-thumb"><img src="{esc(p["thumb"])}?v={p["ogVersion"]}" alt="" width="800" height="420" loading="lazy" decoding="async"></span>
        <span class="nunki-cap"><span class="nunki-name">{esc(p["title"])}</span>{sub}</span>
      </a></li>"""


def nav_home_badge(site: dict) -> str:
    name = esc(site["name"])
    return (
        f'  <p class="nunki-home">'
        f'<a class="nunki-home-mark" href="/" title="{name}" aria-label="{name}, alle wanden">'
        f"{LOGO_SVG}<span class=\"nm-name\">{name}</span></a></p>\n"
    )


def nav_block(current: dict, pages: list[dict], site: dict) -> str:
    groups = []
    for key, label, items in series_of(pages):
        others = [p for p in items if p["slug"] != current["slug"]]
        if not others:
            continue
        groups.append(
            f'  <p class="nunki-group">{esc(label)}</p>\n'
            f'  <ul class="nunki-grid nunki-{key}">\n' + "\n".join(nav_card(p) for p in others) + "\n  </ul>\n"
        )
    if not groups:
        return ""
    css = NAV_CSS.replace("__TORN__", torn_edge())
    return (
        f"{NAV_START}\n<style>{css}</style>\n"
        '<nav class="nunki-nav" aria-label="Andere wanden"><div class="nunki-sheet">\n'
        '  <p class="nunki-kicker">nog meer wanden</p>\n'
        + "".join(groups)
        + nav_home_badge(site)
        + f"</div></nav>\n{NAV_END}"
    )


MARK_CSS = """
.nunki-mark{position:fixed;z-index:60;top:clamp(10px,1.7vh,18px);left:clamp(10px,1.5vw,22px);display:flex;align-items:center;
  height:34px;padding:0 14px 0 6px;box-sizing:border-box;border-radius:17px;color:#2a251f;text-decoration:none;
  background:rgba(246,241,228,.93);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  box-shadow:0 1px 0 rgba(255,255,255,.6) inset,0 0 0 1px rgba(42,37,31,.07),0 8px 20px -12px rgba(0,0,0,.55);
  -webkit-tap-highlight-color:transparent;-webkit-font-smoothing:antialiased;transition:padding .4s ease,background-color .3s ease,box-shadow .3s ease}
.nunki-mark svg{display:block;width:24px;height:24px;flex:none;transition:transform .45s cubic-bezier(.2,.8,.2,1)}
.nunki-mark .nm-name{display:block;overflow:hidden;max-width:12em;margin-left:7px;white-space:nowrap;
  font:400 1.06rem/1.25 "Bradley Hand","Segoe Print","Chalkboard SE","Noteworthy","Avenir Next","Helvetica Neue",Helvetica,sans-serif;
  text-transform:lowercase;transform:translateY(1px);transition:max-width .45s ease,margin .45s ease,opacity .3s ease}
.nunki-mark.nm-min{padding:0 5px}
.nunki-mark.nm-min .nm-name{max-width:0;margin-left:0;opacity:0}
.nunki-mark:hover,.nunki-mark:focus-visible{padding:0 14px 0 6px;background:rgba(251,248,239,.97);outline:none}
.nunki-mark:hover .nm-name,.nunki-mark:focus-visible .nm-name{max-width:12em;margin-left:7px;opacity:1}
.nunki-mark:hover svg,.nunki-mark:focus-visible svg{transform:rotate(-8deg)}
.nunki-mark:focus-visible{box-shadow:0 0 0 2px #ac5036,0 8px 20px -12px rgba(0,0,0,.55)}
@media (max-width:600px){.nunki-mark,.nunki-mark:hover{padding:0 5px}.nunki-mark .nm-name{display:none}}
@media (prefers-reduced-motion:reduce){.nunki-mark,.nunki-mark svg,.nunki-mark .nm-name{transition:none}}
@media print{.nunki-mark{display:none}}
"""

MARK_JS = (
    "(function(){var m=document.querySelector('.nunki-mark');if(!m)return;var y=scrollY;"
    "addEventListener('scroll',function(){var s=scrollY;"
    "if(s>140&&s>y+3)m.classList.add('nm-min');else if(s<y-3||s<=140)m.classList.remove('nm-min');y=s},{passive:true})})();"
)


def mark_block(page: dict) -> str:
    """Het vaste label linksboven: het logo en de naam van de wand, en een weg naar huis."""
    name = esc(page["title"])
    return (
        f"{MARK_START}\n<style>{MARK_CSS}</style>\n"
        f'<a class="nunki-mark" href="/" title="alle wanden" aria-label="{name}, op nunkichannels. naar alle wanden">'
        f'{LOGO_SVG}<span class="nm-name">{name}</span></a>\n'
        f"<script>{MARK_JS}</script>\n{MARK_END}"
    )


def inject_mark(html: str, block: str) -> str:
    html = re.sub(r"\s*" + re.escape(MARK_START) + r".*?" + re.escape(MARK_END), "", html, flags=re.DOTALL)
    m = re.search(r"<body[^>]*>", html, re.IGNORECASE)
    if not m:
        return html
    return html[: m.end()] + "\n" + block + html[m.end():]


def inject_nav(html: str, block: str) -> str:
    html = re.sub(
        r"\s*" + re.escape(NAV_START) + r".*?" + re.escape(NAV_END), "", html, flags=re.DOTALL
    )
    if not block:
        return html
    i = html.lower().rfind("</body>")
    if i == -1:
        return html + "\n" + block
    return html[:i] + block + "\n" + html[i:]


def abs_url(site: dict, path: str) -> str:
    base = site.get("baseUrl") or ""
    if not base:
        return path
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def social_block(page: dict, site: dict, *, is_home: bool = False) -> str:
    title = page["title"]
    if is_home:
        title = site["name"]
    desc = page.get("subtitle") or site["name"]
    url = abs_url(site, page["path"] if not is_home else "/")
    img = abs_url(site, page["ogImage"])
    alt = f"{page['title']} — {desc}" if desc else page["title"]
    return textwrap.dedent(
        f"""
        {SOCIAL_START}
        <meta name="description" content="{esc(desc)}">
        <link rel="canonical" href="{esc(url)}">
        <link rel="icon" href="/favicon.svg" type="image/svg+xml">
        <link rel="icon" href="/favicon.ico" sizes="any">
        <link rel="apple-touch-icon" href="/apple-touch-icon.png">
        <meta property="og:site_name" content="{esc(site['name'])}">
        <meta property="og:title" content="{esc(title)}">
        <meta property="og:description" content="{esc(desc)}">
        <meta property="og:type" content="website">
        <meta property="og:url" content="{esc(url)}">
        <meta property="og:image" content="{esc(img)}">
        <meta property="og:image:width" content="1200">
        <meta property="og:image:height" content="630">
        <meta property="og:image:alt" content="{esc(alt)}">
        <meta name="twitter:card" content="summary_large_image">
        <meta name="twitter:title" content="{esc(title)}">
        <meta name="twitter:description" content="{esc(desc)}">
        <meta name="twitter:image" content="{esc(img)}">
        <meta name="twitter:image:alt" content="{esc(alt)}">
        {SOCIAL_END}
        """
    ).strip()


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def strip_julius(html: str) -> str:
    html = re.sub(
        r"\s*<iframe[^>]*data-julius-public-artifact-badge.*?</iframe>",
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(r"\s*<meta[^>]*data-julius-public-artifact-og[^>]*>", "", html)
    html = re.sub(
        r"\s*<script[^>]*data-julius-public-artifact-analytics[^>]*></script>",
        "",
        html,
    )
    return html


def inject_social(html: str, block: str) -> str:
    html = strip_julius(html)
    pattern = re.compile(
        re.escape(SOCIAL_START) + r".*?" + re.escape(SOCIAL_END),
        re.DOTALL,
    )
    if pattern.search(html):
        return pattern.sub(block, html)
    m = re.search(
        r'(<meta name="viewport"[^>]*>\s*)',
        html,
        re.IGNORECASE,
    )
    if m:
        return html[: m.end()] + "\n" + block + "\n" + html[m.end() :]
    m = re.search(r"(<head[^>]*>\s*)", html, re.IGNORECASE)
    if m:
        return html[: m.end()] + block + "\n" + html[m.end() :]
    return html


def replace_block(html: str, name: str, content: str) -> str:
    start, end = f"<!-- nunki:{name} -->", f"<!-- /nunki:{name} -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(html):
        print(f"  ! marker {start} ontbreekt in index.html")
        return html
    return pattern.sub(lambda _m: f"{start}\n{content}\n{end}" if "\n" in content else f"{start}{content}{end}", html)


def render_cards(pages: list[dict], start: int = 0) -> str:
    items = []
    for k, p in enumerate(pages):
        i = start + k
        sub = f'<span class="sub">{esc(p["subtitle"])}</span>' if p.get("subtitle") else ""
        items.append(
            f'''      <li>
        <a class="card" href="{esc(p["path"])}" style="--i:{i};--theme:{esc(p["theme"])}">
          <span class="tape" aria-hidden="true"></span>
          <span class="thumb"><img src="{esc(p["thumb"])}?v={p["ogVersion"]}" alt="" width="800" height="420" loading="{"eager" if i < 4 else "lazy"}" decoding="async"></span>
          <span class="caption">
            <span class="no">{i + 1:02d}</span>
            <span class="name">{esc(p["title"])}</span>
            <span class="go" aria-hidden="true">→</span>
            {sub}
          </span>
        </a>
      </li>'''
        )
    return "\n".join(items)


def main() -> None:
    site = load_site()
    pages: list[dict] = []
    shots: dict[str, Image.Image] = {}
    positions = load_shot_positions()
    sources: list[tuple[Path, str, dict]] = []
    for d in slug_dirs():
        slug = d.name
        html_path = d / "index.html"
        html = html_path.read_text(encoding="utf-8")
        page = parse_page(slug, html)
        og_path = OG_DIR / f"{slug}.jpg"
        shot = capture_page(slug, html, positions.get(slug, 0))
        if shot is not None:
            shots[slug] = shot
        generate_og(page, site, shot, og_path)
        # schone thumbnail (zonder label) voor de kaarten op de homepage
        if shot is not None:
            THUMB_DIR.mkdir(parents=True, exist_ok=True)
            thumb_path = THUMB_DIR / f"{slug}.jpg"
            cover(shot, 800, 420).save(thumb_path, "JPEG", quality=84, optimize=True, progressive=True)
            os.chmod(thumb_path, 0o644)
            page["thumb"] = f"/images/thumbs/{slug}.jpg"
        else:
            thumb_path = og_path
            page["thumb"] = page["ogImage"]
        page["ogVersion"] = hashlib.sha1(thumb_path.read_bytes()).hexdigest()[:8]
        pages.append(page)
        sources.append((html_path, html, page))

    for html_path, html, page in sources:
        html = inject_social(html, social_block(page, site))
        html = inject_mark(html, mark_block(page))
        write_public(html_path, inject_nav(html, nav_block(page, pages, site)))

    public_pages = [{k: v for k, v in p.items() if k != "ogVersion"} for p in pages]
    payload = {"site": {"name": site["name"], "baseUrl": site["baseUrl"]}, "pages": public_pages}
    write_public(
        PAGES_JSON,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )

    index_path = HTTPDOCS / "index.html"
    if index_path.is_file():
        tagline = "Wanden — getekend, scrollend, levend."
        home = {
            "title": site["name"],
            "subtitle": tagline,
            "path": "/",
            "ogImage": "/images/og/index.jpg",
        }
        home_og = OG_DIR / "index.jpg"
        rows = [[shots[p["slug"]] for p in items if p["slug"] in shots] for _k, _l, items in series_of(pages)]
        if any(rows):
            generate_index_og(site, rows, home_og, tagline)
        else:
            generate_og_fallback({**home, "slug": "index", "theme": "#13202b"}, home_og)
        html = index_path.read_text(encoding="utf-8")
        start = 0
        counts = []
        for key, label, items in series_of(pages):
            html = replace_block(html, f"cards-{key}", render_cards(items, start))
            start += len(items)
            counts.append(f"{len(items)} {label}")
        html = replace_block(html, "count", " · ".join(counts))
        write_public(
            index_path,
            inject_social(html, social_block(home, site, is_home=True)),
        )

    print(f"Built {len(pages)} pages → {PAGES_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
