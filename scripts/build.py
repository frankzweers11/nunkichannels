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
SKIP_DIRS = {"images", "css", "js", "assets"}

W, H = 1200, 630
CREAM = (246, 241, 228)
MUTED = (180, 172, 158)

SOCIAL_START = "<!-- nunki:social -->"
SOCIAL_END = "<!-- /nunki:social -->"


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


def generate_index_og(site: dict, shots: list[Image.Image], out_path: Path, tagline: str) -> None:
    """Social card voor de homepage: collage van de wanden met een naamplaat."""
    from PIL import ImageFilter

    out_path.parent.mkdir(parents=True, exist_ok=True)
    shots = shots[:6]
    n = len(shots)
    cols, rows = {1: (1, 1), 2: (2, 1), 3: (2, 2), 4: (2, 2), 5: (3, 2), 6: (3, 2)}[n]
    gap = 8
    paper = (238, 227, 197)
    canvas = Image.new("RGB", (W, H), paper)
    cw = (W - gap * (cols + 1)) // cols
    ch = (H - gap * (rows + 1)) // rows
    for i, shot in enumerate(shots):
        r, c = divmod(i, cols)
        tile = cover(shot, cw, ch)
        canvas.paste(tile, (gap + c * (cw + gap), gap + r * (ch + gap)))

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


def render_cards(pages: list[dict]) -> str:
    items = []
    ordered = sorted(pages, key=lambda p: p["title"].casefold())
    for i, p in enumerate(ordered):
        sub = f'<span class="sub">{esc(p["subtitle"])}</span>' if p.get("subtitle") else ""
        items.append(
            f'''      <li>
        <a class="card" href="{esc(p["path"])}" style="--i:{i};--theme:{esc(p["theme"])}">
          <span class="tape" aria-hidden="true"></span>
          <span class="thumb"><img src="{esc(p["thumb"])}?v={p["ogVersion"]}" alt="" width="800" height="420" loading="{"eager" if i < 3 else "lazy"}" decoding="async"></span>
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
        block = social_block(page, site)
        write_public(html_path, inject_social(html, block))
        pages.append(page)

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
        ordered = sorted(pages, key=lambda p: p["title"].casefold())
        home_shots = [shots[p["slug"]] for p in ordered if p["slug"] in shots]
        if home_shots:
            generate_index_og(site, home_shots, home_og, tagline)
        else:
            generate_og_fallback({**home, "slug": "index", "theme": "#13202b"}, home_og)
        html = index_path.read_text(encoding="utf-8")
        html = replace_block(html, "cards", render_cards(pages))
        n = len(pages)
        html = replace_block(html, "count", f"{n} {'wand' if n == 1 else 'wanden'}")
        write_public(
            index_path,
            inject_social(html, social_block(home, site, is_home=True)),
        )

    print(f"Built {len(pages)} pages → {PAGES_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
