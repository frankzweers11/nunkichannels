#!/usr/bin/env python3
"""Scan httpdocs/*/index.html, write pages.json, OG images, and social meta in head."""
from __future__ import annotations

import datetime
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
SKIP_DIRS = {"images", "css", "js", "assets", "zelfportret", "en"}

# Elke pagina bestaat in twee talen, uit één bron: Nederlands op /<slug>/ (het
# bronbestand zelf), Engels op /en/<slug>/ (gegenereerd, niet bewerken).
LANGS = ("nl", "en")
BASE_LANG = "nl"


def lang_path(path: str, lang: str) -> str:
    """Het adres van een pagina in een taal: /hart/ → /en/hart/."""
    path = "/" + path.lstrip("/")
    return path if lang == BASE_LANG else f"/{lang}{path}"


def lang_file(rel: str, lang: str) -> Path:
    """Waar de taalversie van httpdocs/<rel> op schijf staat."""
    return HTTPDOCS / rel if lang == BASE_LANG else HTTPDOCS / lang / rel


def other_lang(lang: str) -> str:
    return "en" if lang == "nl" else "nl"

W, H = 1200, 630
CREAM = (246, 241, 228)
MUTED = (180, 172, 158)

DESC_JSON = ROOT / "scripts" / "descriptions.json"
SEO_JSON = ROOT / "scripts" / "seo.json"
SEO_START = "<!-- nunki:seo -->"
SEO_END = "<!-- /nunki:seo -->"
SOCIAL_START = "<!-- nunki:social -->"
SOCIAL_END = "<!-- /nunki:social -->"
NAV_START = "<!-- nunki:nav -->"
NAV_END = "<!-- /nunki:nav -->"
MARK_START = "<!-- nunki:mark -->"
MARK_END = "<!-- /nunki:mark -->"
TOUCH_START = "<!-- nunki:touch -->"
TOUCH_END = "<!-- /nunki:touch -->"
TOUCH_JS = Path(__file__).resolve().parent / "touch.js"
LEES_START = "<!-- nunki:lees -->"
LEES_END = "<!-- /nunki:lees -->"
LEES_JS = Path(__file__).resolve().parent / "lees.js"
LEES_DIR = Path(__file__).resolve().parent / "lees"
TAAL_START = "<!-- nunki:taal -->"
TAAL_END = "<!-- /nunki:taal -->"
TAAL_JS = Path(__file__).resolve().parent / "taal.js"
TAAL_DIR = Path(__file__).resolve().parent / "taal"
I18N_JSON = Path(__file__).resolve().parent / "i18n.json"
I18N = json.loads(I18N_JSON.read_text(encoding="utf-8")) if I18N_JSON.is_file() else {"site": {}, "pages": {}}

# De taal van een pagina is de taal van haar adres: / is Nederlands, /en/ Engels.
# Dit script staat vroeg in elke pagina. Het zet data-lang op <html>, zodat CSS meteen
# de goede tekst toont (.t-nl / .t-en), en bewaart die taal als keuze (nunki:lang),
# ook als de bezoeker eerder de andere koos: het adres is wat je ziet, en wie
# verder klikt blijft in die taal. ?lang= gaat voor (screenshots, testen); zonder
# vaste taal (P) beslist de bewaarde keuze. NUNKI_SETLANG(taal) gaat naar het adres in
# die taal, op dezelfde plek: de scrollfractie gaat mee via sessionStorage (nunki:ry),
# en NUNKI_RELOADED laat een wand met een poort die overslaan. Ook vanaf file://.
def lang_js(page_lang: str | None = None, alt: dict | None = None) -> str:
    return (
        "(function(){var D=document.documentElement,P=" + json.dumps(page_lang) + ",A=" + json.dumps(alt)
        + ",K='nunki:lang',q=null,l=null;"
        "try{q=new URLSearchParams(location.search).get('lang')}catch(e){}if(q!=='nl'&&q!=='en')q=null;"
        "try{l=localStorage.getItem(K)}catch(e){}"
        "l=q||P||(l==='en'?'en':'nl');"
        "if(q||P)try{localStorage.setItem(K,l)}catch(e){}"
        "window.NUNKI_LANG=l;D.setAttribute('data-lang',l);"
        "function href(v){var u=new URL(location.href),c=P&&A&&A[P],p=u.pathname.replace(/index\\.html$/,'');"
        "u.searchParams.delete('lang');"
        "if(!c||!A[v]||(u.protocol==='file:'&&p.slice(-c.length)!==c)){u.searchParams.set('lang',v);return u.href}"
        "u.pathname=u.protocol==='file:'?p.slice(0,p.length-c.length)+A[v]+'index.html':A[v];return u.href}"
        "window.NUNKI_HREF=href;"
        "window.NUNKI_SETLANG=function(v){v=v==='en'?'en':'nl';if(v===l)return;var u=href(v);"
        "try{localStorage.setItem(K,v)}catch(e){}"
        "try{sessionStorage.setItem('nunki:ry',JSON.stringify({p:new URL(u).pathname,f:scrollY/Math.max(1,D.scrollHeight)}))}catch(e){}"
        "location.href=u};"
        "var r=null;try{r=JSON.parse(sessionStorage.getItem('nunki:ry'));sessionStorage.removeItem('nunki:ry')}catch(e){}"
        "if(r&&r.p===location.pathname){window.NUNKI_RELOADED=true;if(r.f>0){"
        "var mv=0,go=function(){if(!mv)scrollTo(0,r.f*D.scrollHeight)},st=function(){mv=1};"
        "addEventListener('load',function(){go();[120,400,900,1600].forEach(function(t){setTimeout(go,t)});"
        "setTimeout(function(){addEventListener('wheel',st,{passive:true,once:true});"
        "addEventListener('touchstart',st,{passive:true,once:true});addEventListener('keydown',st,{once:true})},0)})}}"
        "})();"
    )


def alt_paths(path: str) -> dict:
    return {l: lang_path(path, l) for l in LANGS}
LANG_CSS = 'html:not([data-lang="en"]) .t-en{display:none!important}html[data-lang="en"] .t-nl{display:none!important}'


def site_t(key: str, lang: str) -> str:
    return I18N.get("site", {}).get(lang, {}).get(key, "")


def both(page: dict) -> dict:
    """Titel en ondertitel van een wand in beide talen."""
    out = {}
    for lang in ("nl", "en"):
        tr = I18N.get("pages", {}).get(page["slug"], {}).get(lang, {})
        out[lang] = {
            "title": tr.get("title") or page["title"],
            "subtitle": tr.get("subtitle") or page.get("subtitle") or "",
        }
    return out


def bi(nl: str, en: str) -> str:
    """Tekst in twee talen voor HTML: twee spans als ze verschillen."""
    if nl == en:
        return esc(nl)
    return f'<span class="t-nl">{esc(nl)}</span><span class="t-en" lang="en">{esc(en)}</span>'

# De wanden staan in twee series: de zelfportretten van de modellen, en de andere wanden.
SERIES = [
    ("self", "zelfportretten", lambda p: p["slug"].startswith("zelfportret-")),
    ("walls", "andere wanden", lambda p: not p["slug"].startswith("zelfportret-")),
]


# wanden die voorop mogen staan, in deze volgorde, vóór de rest (alfabetisch)
PINNED = ["hart"]


def series_of(pages: list[dict]) -> list[tuple[str, str, list[dict]]]:
    out = []
    for key, label, test in SERIES:
        items = sorted(
            (p for p in pages if test(p)),
            key=lambda p: (PINNED.index(p["slug"]) if p["slug"] in PINNED else len(PINNED), p["title"].casefold()),
        )
        out.append((key, label, items))
    return out


def series_label(key: str, lang: str) -> str:
    return site_t(key, lang) or dict((k, l) for k, l, _t in SERIES)[key]


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
    # the language the wall itself is written in: data-wand-lang once build.py has
    # given <html> the language of its address, before that its own lang
    lm = re.search(r"<html[^>]*\bdata-wand-lang=[\"']([a-zA-Z-]+)", html) or re.search(
        r"<html[^>]*\slang=[\"']([a-zA-Z-]+)", html
    )
    return {
        "slug": slug,
        "wallLang": (lm.group(1).lower() if lm else "nl"),
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


def load_script_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf",
        "/System/Library/Fonts/Supplemental/ChalkboardSE.ttc",
        "/System/Library/Fonts/Supplemental/Chalkboard.ttc",
    ]
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return load_font(size)


INK = (42, 37, 31)
CLAY = (172, 80, 54)
LOGO_TAN = (214, 178, 108)

LOGO_SVG = (
    '<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">'
    '<path d="M18 48V30c0-7 6-12 14-12s12 5 12 12v18" fill="none" stroke="#ac5036" stroke-width="7.5" '
    'stroke-linecap="round" stroke-linejoin="round"/><circle cx="48" cy="15" r="4" fill="#d6b26c"/></svg>'
)


def _bezier_points(p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float], steps: int = 36) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        out.append((x, y))
    return out


def nunki_logo_rgba(size: int) -> Image.Image:
    """n-logo gerasterd uit hetzelfde SVG-pad als op de site (geen hoekige PIL-benadering)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size / 64.0
    w = max(2, round(7.5 * s))

    # M18 48 V30 c0-7 6-12 14-12 s12 5 12 12 v18
    pts: list[tuple[float, float]] = [(18.0, 48.0), (18.0, 30.0)]
    pts.extend(_bezier_points((18.0, 30.0), (18.0, 23.0), (24.0, 18.0), (32.0, 18.0))[1:])
    pts.extend(_bezier_points((32.0, 18.0), (40.0, 18.0), (44.0, 23.0), (44.0, 30.0))[1:])
    pts.append((44.0, 48.0))

    scaled = [(x * s, y * s) for x, y in pts]
    for i in range(len(scaled) - 1):
        draw.line([scaled[i], scaled[i + 1]], fill=CLAY, width=w, joint="curve")

    cx, cy, r = 48.0 * s, 15.0 * s, 4.0 * s
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=LOGO_TAN)
    return img


def composite_wand_badge(img: Image.Image, title: str, *, x: int = 24, y: int = 18) -> Image.Image:
    """Pill-badge zoals nunki-mark: logo + wandtitel linksboven op de OG."""
    from PIL import ImageFilter

    base = img.convert("RGBA") if img.mode != "RGBA" else img
    label = title.strip().lower()
    icon = 32
    pad_l, pad_r, gap = 8, 16, 7
    font_size = 28
    script = load_script_font(font_size)
    probe = ImageDraw.Draw(base)
    tw = probe.textlength(label, font=script)
    badge_h = 52
    badge_w = int(pad_l + icon + gap + tw + pad_r)
    radius = badge_h // 2

    bleed = 28
    canvas_w, canvas_h = badge_w + bleed * 2, badge_h + bleed * 2
    bx, by = bleed, bleed

    mask = Image.new("L", (badge_w, badge_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, badge_w - 1, badge_h - 1], radius, fill=255)
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 72)), (bx, by + 6), mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))

    pill = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(pill)
    dr.rounded_rectangle([0, 0, badge_w - 1, badge_h - 1], radius, fill=(246, 241, 228, 255))
    dr.rounded_rectangle([0, 0, badge_w - 1, badge_h - 1], radius, outline=(42, 37, 31, 14), width=1)
    logo = nunki_logo_rgba(icon * 2).resize((icon, icon), Image.Resampling.LANCZOS)
    pill.alpha_composite(logo, (pad_l, (badge_h - icon) // 2))
    tx = pad_l + icon + gap
    ty = (badge_h - font_size) // 2 - 2
    dr.text((tx, ty), label, font=script, fill=(*INK, 255))

    layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    layer.alpha_composite(shadow)
    layer.paste(pill, (bx, by), mask)

    base.alpha_composite(layer, (x - bleed, y - bleed))
    return base


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

    margin_x, margin_y = 64, 72
    max_text_w = 640 if slug == "zelfportret" else W - margin_x * 2

    title = page["title"]
    subtitle = page.get("subtitle") or ""

    draw.text((margin_x, margin_y), title, font=title_font, fill=CREAM)

    y = margin_y + 88
    for line in wrap_text(subtitle, sub_font, max_text_w, draw):
        draw.text((margin_x, y), line, font=sub_font, fill=MUTED)
        y += 40

    img = composite_wand_badge(img.convert("RGBA"), page["title"])
    img.convert("RGB").save(out_path, "JPEG", quality=88, optimize=True, progressive=True)



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
    html = re.sub(
        re.escape(SEO_START) + r".*?" + re.escape(SEO_END), "", html, flags=re.DOTALL
    )
    html = re.sub(
        re.escape(TOUCH_START) + r".*?" + re.escape(TOUCH_END), "", html, flags=re.DOTALL
    )
    html = re.sub(
        re.escape(LEES_START) + r".*?" + re.escape(LEES_END), "", html, flags=re.DOTALL
    )
    # the language still has to be known (?lang= in the shot's address), so that script stays,
    # and the taal block too: it draws a wall's words in the other language
    html = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + f"<script>{lang_js()}</script>", html, count=1, flags=re.IGNORECASE)
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


def capture_page(slug: str, html: str, y: int = 0, lang: str = "nl") -> Image.Image | None:
    """Screenshot (1200x630) van de wand op scrollpositie y, na het intekenen, in taal lang. Gecachet op inhoud."""
    clean = clean_for_shot(html)
    key = hashlib.sha1(f"{SHOT_VERSION}|{y}|{lang}|{clean}".encode("utf-8")).hexdigest()[:12]
    cached = CACHE_DIR / f"{slug}-{lang}-{key}.png"
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
                    src.as_uri() + "?fast&lang=" + lang,
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
            if re.fullmatch(re.escape(slug) + r"-(" + re.escape(lang) + r"-)?[0-9a-f]{12}\.png", old.name):
                old.unlink()
        img.save(cached, "PNG")
        return img


def cover(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    resized = img.resize((max(w, round(img.width * scale)), max(h, round(img.height * scale))), Image.Resampling.LANCZOS)
    left = (resized.width - w) // 2
    top = (resized.height - h) // 2
    return resized.crop((left, top, left + w, top + h))


def generate_og(page: dict, site: dict, shot: Image.Image | None, out_path: Path) -> None:
    """Social card: screenshot van de wand, met nunki-mark badge als titel."""
    if shot is None:
        generate_og_fallback(page, out_path)
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = composite_wand_badge(cover(shot, W, H), page["title"])
    img.convert("RGB").save(out_path, "JPEG", quality=88, optimize=True, progressive=True)


def generate_index_og(site: dict, rows: list[list[Image.Image]], out_path: Path, tagline: str) -> None:
    """Social card voor de homepage: collage van wand-screenshots, badge linksboven."""
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

    canvas = composite_wand_badge(canvas, site["name"])
    canvas.convert("RGB").save(out_path, "JPEG", quality=88, optimize=True, progressive=True)



# ---------------------------------------------------------------------------
# Footer-navigatie onderaan elke wand: kleine kaartjes van de andere wanden
# ---------------------------------------------------------------------------

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
@media (min-width:720px){
  .nunki-grid.nunki-n-4{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));max-width:520px;gap:1.9rem 1.4rem}
  .nunki-grid.nunki-n-4 li{flex:none;width:100%;max-width:240px;justify-self:center}
  .nunki-grid.nunki-n-5{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));max-width:780px;gap:1.9rem 1.4rem}
  .nunki-grid.nunki-n-5 li{flex:none;width:100%;max-width:240px;justify-self:center;grid-column:span 2}
  .nunki-grid.nunki-n-5 li:nth-child(4){grid-column:2/span 2}
  .nunki-grid.nunki-n-6{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));max-width:780px;gap:1.9rem 1.4rem}
  .nunki-grid.nunki-n-6 li{flex:none;width:100%;max-width:240px;justify-self:center}
}
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
.nunki-home{position:relative;margin:clamp(1.8rem,4vw,2.4rem) 0 0;text-align:center;line-height:1}
__LANGCSS__
.nunki-home-mark{display:inline-flex;align-items:center;height:40px;padding:0 16px 0 8px;box-sizing:border-box;border-radius:20px;
  color:var(--ink);text-decoration:none;background:rgba(246,241,228,.97);
  box-shadow:0 1px 0 rgba(255,255,255,.6) inset,0 0 0 1px rgba(42,37,31,.07),0 8px 20px -12px rgba(0,0,0,.55);
  -webkit-tap-highlight-color:transparent;transition:transform .35s cubic-bezier(.2,.8,.2,1),box-shadow .3s ease,background-color .3s ease}
.nunki-home-mark svg{display:block;width:26px;height:26px;flex:none;transition:transform .45s cubic-bezier(.2,.8,.2,1)}
.nunki-home-mark .nm-name{display:block;margin-left:8px;white-space:nowrap;font:400 1.15rem/1.25 "Bradley Hand","Segoe Print","Chalkboard SE","Noteworthy","Avenir Next","Helvetica Neue",Helvetica,sans-serif;
  text-transform:lowercase;transform:translateY(1px)}
.nunki-home-mark:hover,.nunki-home-mark:focus-visible{outline:none;transform:translateY(-2px);background:rgba(251,248,239,.97);
  box-shadow:0 1px 0 rgba(255,255,255,.6) inset,0 0 0 1px rgba(42,37,31,.07),0 12px 28px -12px rgba(0,0,0,.5)}
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


NAV_JS = r"""/* nunki:nav, gegenereerd door scripts/build.py. Niet met de hand aanpassen. */
(function () {
  var DATA = __DATA__;
  var LOGO = __LOGO__;
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }
  // text in both languages: two spans, css shows the chosen one (html[data-lang])
  function bi(tag, cls, t) {
    if (typeof t === 'string' || t.nl === t.en) return el(tag, cls, typeof t === 'string' ? t : t.nl);
    var e = el(tag, cls);
    var a = el('span', 't-nl', t.nl), b = el('span', 't-en', t.en);
    b.lang = 'en';
    e.appendChild(a); e.appendChild(b);
    return e;
  }
  function T(k) { return { nl: (DATA.t.nl || {})[k] || '', en: (DATA.t.en || {})[k] || '' }; }
  // the links stay inside the language of the page: /hart/ or /en/hart/
  var L = window.NUNKI_LANG === 'en' ? 'en' : 'nl';
  function card(p) {
    var li = el('li');
    var a = el('a', 'nunki-card');
    a.href = p.path[L];
    a.style.setProperty('--theme', p.theme);
    a.appendChild(el('span', 'nunki-tape')).setAttribute('aria-hidden', 'true');
    var th = el('span', 'nunki-thumb');
    var img = new Image();
    img.src = p.thumb[L] + '?v=' + p.v[L];
    img.alt = '';
    img.width = 800;
    img.height = 420;
    img.loading = 'lazy';
    img.decoding = 'async';
    th.appendChild(img);
    a.appendChild(th);
    var cap = el('span', 'nunki-cap');
    cap.appendChild(bi('span', 'nunki-name', p.title));
    if (p.subtitle && p.subtitle.nl) cap.appendChild(bi('span', 'nunki-sub', p.subtitle));
    a.appendChild(cap);
    li.appendChild(a);
    return li;
  }
  function build() {
    if (document.querySelector('.nunki-nav')) return;
    var here = location.pathname.replace(/index\.html$/, '');
    if (here.slice(-1) !== '/') here += '/';
    var nav = el('nav', 'nunki-nav');
    nav.setAttribute('aria-label', T('nav')[L]);
    var sheet = el('div', 'nunki-sheet');
    sheet.appendChild(bi('p', 'nunki-kicker', T('more')));
    var any = false;
    DATA.series.forEach(function (g) {
      var others = g.pages.filter(function (p) { return p.path[L] !== here; });
      if (!others.length) return;
      any = true;
      sheet.appendChild(bi('p', 'nunki-group', g.label));
      var n = others.length;
      var ul = el('ul', 'nunki-grid nunki-' + g.key + (n >= 4 && n <= 6 ? ' nunki-n-' + n : ''));
      others.forEach(function (p) { ul.appendChild(card(p)); });
      sheet.appendChild(ul);
    });
    if (!any) return;
    var home = el('p', 'nunki-home');
    var a = el('a', 'nunki-home-mark');
    a.href = L === 'en' ? '/en/' : '/';
    a.title = DATA.name;
    a.setAttribute('aria-label', DATA.name + ', ' + T('home')[L]);
    a.innerHTML = LOGO + '<span class="nm-name"></span>';
    a.querySelector('.nm-name').textContent = DATA.name;
    home.appendChild(a);
    sheet.appendChild(home);
    nav.appendChild(sheet);
    document.body.appendChild(nav);
  }
  var css = document.createElement('link');
  css.rel = 'stylesheet';
  css.href = '/nav.css';
  document.head.appendChild(css);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
"""


def write_nav_assets(pages: list[dict], site: dict) -> None:
    """De navigatie onderaan elke wand staat op één plek: /nav.css en /nav.js."""
    series = [
        {
            "key": key,
            "label": {"nl": series_label(key, "nl"), "en": series_label(key, "en")},
            "pages": [
                {
                    "path": {l: p["l"][l]["path"] for l in LANGS},
                    "title": {l: both(p)[l]["title"] for l in LANGS},
                    "subtitle": {l: both(p)[l]["subtitle"] for l in LANGS},
                    "theme": p["theme"],
                    "thumb": {l: p["l"][l]["thumb"] for l in LANGS},
                    "v": {l: p["l"][l]["v"] for l in LANGS},
                }
                for p in items
            ],
        }
        for key, label, items in series_of(pages)
    ]
    data = {"name": site["name"], "series": series, "t": I18N.get("site", {})}
    js = NAV_JS.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace(
        "__LOGO__", json.dumps(LOGO_SVG)
    )
    write_public(HTTPDOCS / "nav.js", js)
    write_public(HTTPDOCS / "nav.css", NAV_CSS.replace("__TORN__", torn_edge()).replace("__LANGCSS__", LANG_CSS).strip() + "\n")


def nav_block() -> str:
    return f'{NAV_START}<script src="/nav.js" defer></script>{NAV_END}'


MARK_CSS = LANG_CSS + """
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


# Rechtsboven, op dezelfde hoogte en in dezelfde stijl als het label linksboven:
# de taalwissel, en daarnaast de eigen knoppen van een wand (geluid, film, bewaard).
# Een wand zet data-nunki-bar op zo'n knop, of roept NUNKI_BAR(el) aan; de knop
# schuift dan links naast de taalwissel in de rij.
BAR_CSS = """
.nunki-bar{position:fixed;z-index:61;top:clamp(10px,1.7vh,18px);right:clamp(10px,1.5vw,22px);display:flex;align-items:center;gap:8px;pointer-events:none}
.nunki-bar>*{pointer-events:auto;position:relative!important;inset:auto!important;margin:0!important;flex:none}
.nunki-lng{display:flex;align-items:center;height:34px;padding:0 13px;box-sizing:border-box;border:0;border-radius:17px;cursor:pointer;color:#2a251f;
  background:rgba(246,241,228,.93);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  box-shadow:0 1px 0 rgba(255,255,255,.6) inset,0 0 0 1px rgba(42,37,31,.07),0 8px 20px -12px rgba(0,0,0,.55);
  font:400 1.06rem/1 "Bradley Hand","Segoe Print","Chalkboard SE","Noteworthy","Avenir Next","Helvetica Neue",Helvetica,sans-serif;
  text-decoration:none;-webkit-tap-highlight-color:transparent;-webkit-font-smoothing:antialiased;transition:background-color .3s ease}
.nunki-lng span{display:block;transform:translateY(1px);opacity:.34;transition:opacity .3s ease}
.nunki-lng i{display:block;width:3px;height:3px;margin:2px 7px 0;border-radius:2px;background:currentColor;opacity:.3}
html:not([data-lang="en"]) .nunki-lng .l-nl,html[data-lang="en"] .nunki-lng .l-en{opacity:1}
.nunki-lng:hover{background:rgba(251,248,239,.97)}
.nunki-lng:hover span{opacity:.72}
html:not([data-lang="en"]) .nunki-lng:hover .l-nl,html[data-lang="en"] .nunki-lng:hover .l-en{opacity:1}
.nunki-lng:focus-visible{outline:none;box-shadow:0 0 0 2px #ac5036,0 8px 20px -12px rgba(0,0,0,.55)}
.nunki-bar .nunki-pill{display:flex!important;align-items:center;justify-content:center;gap:6px;height:34px!important;min-width:34px;padding:0 13px!important;box-sizing:border-box;
  border:0!important;border-radius:17px!important;cursor:pointer;color:#2a251f!important;background:rgba(246,241,228,.93)!important;
  -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  box-shadow:0 1px 0 rgba(255,255,255,.6) inset,0 0 0 1px rgba(42,37,31,.07),0 8px 20px -12px rgba(0,0,0,.55)!important;
  font:400 1.06rem/1 "Bradley Hand","Segoe Print","Chalkboard SE","Noteworthy","Avenir Next","Helvetica Neue",Helvetica,sans-serif!important;
  letter-spacing:0!important;text-transform:lowercase!important;text-decoration:none!important;white-space:nowrap;
  -webkit-tap-highlight-color:transparent;-webkit-font-smoothing:antialiased;transition:background-color .3s ease,color .3s ease,opacity .4s ease}
.nunki-bar .nunki-pill:hover{background:rgba(251,248,239,.97)!important}
.nunki-bar [hidden]{display:none!important}
.nunki-bar .nunki-pill[aria-pressed="false"],.nunki-bar .nunki-pill.off{color:rgba(42,37,31,.52)!important}
.nunki-bar .nunki-pill:focus-visible{outline:none!important;box-shadow:0 0 0 2px #ac5036,0 8px 20px -12px rgba(0,0,0,.55)!important}
@media (max-width:600px){.nunki-bar{gap:6px}.nunki-lng{padding:0 11px}.nunki-lng i{margin:2px 5px 0}.nunki-bar .nunki-pill{padding:0 11px!important;font-size:1rem!important}}
@media (prefers-reduced-motion:reduce){.nunki-lng,.nunki-lng span{transition:none}}
@media print{.nunki-bar{display:none}}
"""

def bar_html(lang: str, alt: dict) -> str:
    """De taalwissel: een link naar dit adres in de andere taal."""
    o = other_lang(lang)
    return (
        f'<div class="nunki-bar"><a class="nunki-lng" href="{esc(alt[o])}" hreflang="{o}">'
        '<span class="l-nl" lang="nl">nl</span><i aria-hidden="true"></i><span class="l-en" lang="en">en</span></a></div>'
    )


# De wissel is een gewone link (ook voor zoekmachines, en cmd-klik opent een tab);
# een klik gaat via NUNKI_SETLANG, zodat je op dezelfde plek uitkomt.
BAR_JS = (
    "(function(){var b=document.querySelector('.nunki-bar');if(!b)return;var k=b.querySelector('.nunki-lng'),"
    "en=window.NUNKI_LANG==='en',o=en?'nl':'en';"
    "k.setAttribute('aria-label',en?'language: english. switch to dutch':'taal: nederlands. wissel naar engels');"
    "k.title=en?'nederlands':'english';"
    "try{k.href=window.NUNKI_HREF(o)}catch(e){}"
    "k.addEventListener('click',function(e){e.stopPropagation();if(e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||e.button)return;"
    "e.preventDefault();window.NUNKI_SETLANG(o)});"
    "['pointerdown','mousedown','touchstart'].forEach(function(t){b.addEventListener(t,function(e){e.stopPropagation()},{passive:true})});"
    "window.NUNKI_BAR=function(el){if(el&&el.parentNode!==b)b.insertBefore(el,k)};"
    "function dock(){[].forEach.call(document.querySelectorAll('[data-nunki-bar]'),window.NUNKI_BAR)}"
    "if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',dock);else dock()})();"
)


def mark_block(page: dict, lang: str) -> str:
    """Het vaste label linksboven: het logo en de naam van de wand, en een weg naar huis; rechtsboven de taalwissel."""
    b = both(page)
    name = esc(b[lang]["title"])
    alt = alt_paths(page["path"])
    home = lang_path("/", lang)
    aria = f"{name}, on nunkichannels. to all walls" if lang == "en" else f"{name}, op nunkichannels. naar alle wanden"
    return (
        f"{MARK_START}\n<script>{lang_js(lang, alt)}</script>\n<style>{MARK_CSS}</style>\n"
        f'<a class="nunki-mark" href="{home}" title="{esc(site_t("home", lang))}" aria-label="{aria}">'
        f'{LOGO_SVG}<span class="nm-name">{bi(b["nl"]["title"], b["en"]["title"])}</span></a>\n'
        f"<style>{BAR_CSS}</style>{bar_html(lang, alt)}\n"
        f"<script>{MARK_JS}{BAR_JS}</script>\n{MARK_END}"
    )


def inject_mark(html: str, block: str) -> str:
    html = re.sub(r"\s*" + re.escape(MARK_START) + r".*?" + re.escape(MARK_END), "", html, flags=re.DOTALL)
    m = re.search(r"<body[^>]*>", html, re.IGNORECASE)
    if not m:
        return html
    return html[: m.end()] + "\n" + block + html[m.end():]


# Hoe een wand op een touch-scherm meedoet (zie scripts/touch.js).
# hand: 'move' = vinger stilhouden en bewegen is de muis, 'press' = ook ingedrukt
# (tekenen), 'off' = de wand regelt touch zelf. motion: kantelen/schudden gebruikt.
# shake: 'tap' = schudden is een tik midden in beeld, 'own' = de wand doet het zelf.
TOUCH_CFG = {
    "getij": {"hand": "move", "motion": True, "shake": "own"},
    "ringen": {"hand": "move", "motion": True, "shake": "own"},
    "velden": {"hand": "press", "motion": True, "shake": "tap"},
    "patronen": {"hand": "move", "motion": True, "shake": "tap"},
    "adem": {"hand": "move", "motion": True, "shake": "own"},
    "hart": {"hand": "move", "motion": True, "shake": "tap"},
    "vuur": {"hand": "move", "motion": True, "shake": "own"},
    "cel": {"hand": "off"},
    "zelfportret-fable-5": {"hand": "off", "sound": False},
    "zelfportret-haiku-5-5": {"hand": "off", "sound": False},
}
TOUCH_DEFAULT = {"hand": "off"}


def touch_block(page: dict) -> str:
    """Geluid, de vinger als hand, kantelen en trillen op telefoon en iPad."""
    cfg = TOUCH_CFG.get(page["slug"], TOUCH_DEFAULT)
    js = TOUCH_JS.read_text(encoding="utf-8")
    return (
        f"{TOUCH_START}\n<script>window.NUNKI_CFG={json.dumps(cfg)};</script>\n"
        f"<script>{js}</script>\n{TOUCH_END}"
    )


def inject_touch(html: str, block: str) -> str:
    html = re.sub(r"\s*" + re.escape(TOUCH_START) + r".*?" + re.escape(TOUCH_END), "", html, flags=re.DOTALL)
    i = html.find(MARK_END)
    if i != -1:
        i += len(MARK_END)
    else:
        m = re.search(r"<body[^>]*>", html, re.IGNORECASE)
        if not m:
            return html
        i = m.end()
    return html[:i] + "\n" + block + html[i:]


def taal_block(page: dict) -> str:
    """De getekende tekst van een wand in de andere taal, uit scripts/taal/<slug>.json."""
    src = TAAL_DIR / f"{page['slug']}.json"
    if not src.is_file():
        return ""
    data = json.loads(src.read_text(encoding="utf-8"))
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    js = TAAL_JS.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"{TAAL_START}\n<script>window.NUNKI_TAAL={payload};</script>\n<script>{js}</script>\n{TAAL_END}"


def inject_taal(html: str, block: str) -> str:
    """Direct na het label, vóór de eigen scripts van de wand."""
    html = re.sub(r"\s*" + re.escape(TAAL_START) + r".*?" + re.escape(TAAL_END), "", html, flags=re.DOTALL)
    if not block:
        return html
    i = html.find(MARK_END)
    if i == -1:
        return html
    i += len(MARK_END)
    return html[:i] + "\n" + block + html[i:]


def lees_block(page: dict) -> str:
    """De leeslaag: de zinnen per vel in NL en EN, uit scripts/lees/<slug>.json."""
    src = LEES_DIR / f"{page['slug']}.json"
    if not src.is_file():
        return ""
    data = json.loads(src.read_text(encoding="utf-8"))
    js = LEES_JS.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"{LEES_START}\n<script>window.NUNKI_LEES={payload};</script>\n<script>{js}</script>\n{LEES_END}"


def inject_lees(html: str, block: str) -> str:
    html = re.sub(r"\s*" + re.escape(LEES_START) + r".*?" + re.escape(LEES_END), "", html, flags=re.DOTALL)
    if not block:
        return html
    i = html.find(NAV_START)
    if i == -1:
        i = html.lower().rfind("</body>")
    if i == -1:
        return html + "\n" + block
    return html[:i] + block + "\n" + html[i:]


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


def text_for(table: dict, key: str, lang: str, own: str = "nl") -> str:
    """Een tekst uit descriptions.json of seo.json in een taal ({"nl": .., "en": ..}, of één tekst in de taal van de wand)."""
    v = table.get(key, "")
    if isinstance(v, dict):
        return v.get(lang, "")
    return v if lang == own else ""


LOCALES = {"nl": "nl_NL", "en": "en_US"}


def social_block(page: dict, site: dict, lang: str, *, is_home: bool = False) -> str:
    """De kop van een pagina in een taal: description, canonical naar zichzelf, hreflang naar beide talen, OG/Twitter en JSON-LD."""
    descs = json.loads(DESC_JSON.read_text(encoding="utf-8")) if DESC_JSON.is_file() else {}
    if is_home:
        title = site["name"]
        sub = site_t("tagline", lang) or site["name"]
        desc = text_for(descs, "_home", lang) or sub
        alt = alt_paths("/")
        img = abs_url(site, page["og"][lang])
        alt_text = f"{site['name']} — {sub}"
    else:
        b = both(page)[lang]
        title = b["title"]
        sub = b["subtitle"] or site["name"]
        desc = text_for(descs, page["slug"], lang, page["wallLang"]) or b["subtitle"] or site["name"]
        alt = alt_paths(page["path"])
        img = abs_url(site, page["l"][lang]["ogImage"])
        alt_text = f"{title} — {sub}"
    url = abs_url(site, alt[lang])
    links = "\n".join(
        f'<link rel="alternate" hreflang="{l}" href="{esc(abs_url(site, alt[l]))}">' for l in LANGS
    ) + f'\n<link rel="alternate" hreflang="x-default" href="{esc(abs_url(site, alt[BASE_LANG]))}">'
    locale = LOCALES.get(lang, lang)
    locale_alt = "\n".join(
        f'<meta property="og:locale:alternate" content="{LOCALES.get(l, l)}">' for l in LANGS if l != lang
    )
    if is_home:
        ld = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": site["name"],
            "url": url,
            "description": desc,
            "inLanguage": lang,
        }
    else:
        ld = {
            "@context": "https://schema.org",
            "@type": "CreativeWork",
            "name": title,
            "headline": f"{title} · {sub}" if sub else title,
            "description": desc,
            "url": url,
            "image": img,
            "inLanguage": lang,
            "isPartOf": {"@type": "WebSite", "name": site["name"], "url": abs_url(site, lang_path("/", lang))},
        }
    ld_json = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    lines = [
        SOCIAL_START,
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{esc(url)}">',
        links,
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
        '<link rel="icon" href="/favicon.ico" sizes="any">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        f'<meta property="og:site_name" content="{esc(site["name"])}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:locale" content="{locale}">',
        locale_alt,
        f'<meta property="og:url" content="{esc(url)}">',
        f'<meta property="og:image" content="{esc(img)}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{esc(alt_text)}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{esc(img)}">',
        f'<meta name="twitter:image:alt" content="{esc(alt_text)}">',
        f'<script type="application/ld+json">{ld_json}</script>',
        SOCIAL_END,
    ]
    return "\n".join(lines)


def set_title(html: str, text: str) -> str:
    """De <title> van de pagina, in de taal van het adres."""
    return re.sub(r"<title>[^<]*</title>", lambda _m: f"<title>{esc(text)}</title>", html, count=1, flags=re.IGNORECASE)


def set_html_lang(html: str, lang: str, wall_lang: str | None = None) -> str:
    """<html lang> in de taal van het adres; data-wand-lang onthoudt in welke taal de wand zelf geschreven is."""
    def fix(m: re.Match) -> str:
        tag = m.group(0)
        tag = re.sub(r'\s(lang|data-wand-lang)="[^"]*"', "", tag)
        extra = f' data-wand-lang="{wall_lang}"' if wall_lang else ""
        return tag[:5] + f' lang="{lang}"{extra}' + tag[5:]
    return re.sub(r"<html\b[^>]*>", fix, html, count=1, flags=re.IGNORECASE)


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def last_modified(path: Path) -> str:
    """Datum van de laatste commit die dit bestand raakte (fallback: mtime)."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    return datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()


def write_sitemap(site: dict, pages: list[dict]) -> None:
    """Elke pagina in beide talen, met de taalversies als xhtml:link-alternates."""
    entries = [("/", last_modified(HTTPDOCS / "index.html"), "1.0")]
    for p in pages:
        entries.append((p["path"], last_modified(HTTPDOCS / p["slug"] / "index.html"), "0.8"))
    # de homepage verandert mee met de nieuwste wand
    entries[0] = ("/", max(e[1] for e in entries), "1.0")
    urls = []
    for path, lm, pr in entries:
        alts = "".join(
            f'\n    <xhtml:link rel="alternate" hreflang="{l}" href="{esc(abs_url(site, lang_path(path, l)))}"/>'
            for l in LANGS
        ) + f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{esc(abs_url(site, path))}"/>'
        for lang in LANGS:
            urls.append(
                f"  <url>\n    <loc>{esc(abs_url(site, lang_path(path, lang)))}</loc>{alts}\n"
                f"    <lastmod>{lm}</lastmod>\n    <priority>{pr}</priority>\n  </url>"
            )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    write_public(HTTPDOCS / "sitemap.xml", xml)
    write_public(
        HTTPDOCS / "robots.txt",
        f"User-agent: *\nAllow: /\n\nSitemap: {abs_url(site, '/sitemap.xml')}\n",
    )


SEO_CSS = (
    "position:absolute;width:1px;height:1px;margin:-1px;padding:0;"
    "overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap;border:0"
)


def seo_block(page: dict, html: str, text: str, lang: str) -> str:
    """Leesbare tekst voor zoekmachines en schermlezers (visueel verborgen), in de taal van het adres."""
    plain = re.sub(re.escape(SEO_START) + r".*?" + re.escape(SEO_END), "", html, flags=re.DOTALL)
    has_h1 = re.search(r"<h1[\s>]", plain, re.IGNORECASE) is not None
    head = "" if has_h1 else f"<h1>{esc(both(page)[lang]['title'])}</h1>"
    return (
        f'{SEO_START}\n<div style="{SEO_CSS}" lang="{lang}">{head}<p>{esc(text)}</p></div>\n{SEO_END}'
    )


def inject_seo(html: str, block: str) -> str:
    html = re.sub(
        r"\s*" + re.escape(SEO_START) + r".*?" + re.escape(SEO_END), "", html, flags=re.DOTALL
    )
    if not block:
        return html
    m = re.search(r"<body[^>]*>", html, re.IGNORECASE)
    if not m:
        return html
    return html[: m.end()] + "\n" + block + html[m.end() :]


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


def render_cards(pages: list[dict], start: int, lang: str) -> str:
    items = []
    for k, p in enumerate(pages):
        i = start + k
        b = both(p)
        v = p["l"][lang]
        sub = f'<span class="sub">{bi(b["nl"]["subtitle"], b["en"]["subtitle"])}</span>' if p.get("subtitle") else ""
        items.append(
            f'''      <li>
        <a class="card" href="{esc(v["path"])}" style="--i:{i};--theme:{esc(p["theme"])}">
          <span class="tape" aria-hidden="true"></span>
          <span class="thumb"><img src="{esc(v["thumb"])}?v={v["v"]}" alt="" width="800" height="420" loading="{"eager" if i < 4 else "lazy"}" decoding="async"></span>
          <span class="caption">
            <span class="no">{i + 1:02d}</span>
            <span class="name">{bi(b["nl"]["title"], b["en"]["title"])}</span>
            <span class="go" aria-hidden="true">→</span>
            {sub}
          </span>
        </a>
      </li>'''
        )
    return "\n".join(items)


def render_wall(html: str, page: dict, site: dict, lang: str) -> str:
    """De wand in een taal: dezelfde bron, met kop, label, taalwissel en SEO-tekst in die taal."""
    b = both(page)[lang]
    html = set_html_lang(html, lang, page["wallLang"])
    html = set_title(html, f"{b['title']} · {b['subtitle']}" if b["subtitle"] else b["title"])
    html = inject_social(html, social_block(page, site, lang))
    seo_text = text_for(json.loads(SEO_JSON.read_text(encoding="utf-8")), page["slug"], lang, page["wallLang"])
    html = inject_seo(html, seo_block(page, html, seo_text, lang) if seo_text else "")
    html = inject_mark(html, mark_block(page, lang))
    html = inject_touch(html, touch_block(page))
    html = inject_taal(html, taal_block(page))
    html = inject_nav(html, nav_block())
    return inject_lees(html, lees_block(page))


def render_home(html: str, pages: list[dict], site: dict, home: dict, lang: str) -> str:
    """De homepage in een taal: kaarten naar de wanden in die taal, kop en taalwissel in die taal."""
    alt = alt_paths("/")
    start = 0
    counts = []
    for key, label, items in series_of(pages):
        html = replace_block(html, f"cards-{key}", render_cards(items, start, lang))
        start += len(items)
        counts.append(bi(f"{len(items)} {series_label(key, 'nl')}", f"{len(items)} {series_label(key, 'en')}"))
    html = replace_block(html, "count", " · ".join(counts))
    html = replace_block(html, "lang", f"<script>{lang_js(lang, alt)}</script><style>{LANG_CSS}{BAR_CSS}</style>")
    html = replace_block(html, "bar", f"{bar_html(lang, alt)}<script>{BAR_JS}</script>")
    html = set_html_lang(html, lang)
    if lang != BASE_LANG:
        # the logo links home: the home of this language
        html = html.replace('href="/"', f'href="{lang_path("/", lang)}"')
    return inject_social(html, social_block(home, site, lang, is_home=True))


def write_lang_file(rel: str, lang: str, html: str) -> None:
    path = lang_file(rel, lang)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_public(path, html)


def same_image(a: Image.Image, b: Image.Image) -> bool:
    from PIL import ImageChops

    return a.size == b.size and ImageChops.difference(a, b).getbbox() is None


def save_jpeg(img: Image.Image, path: Path, quality: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    os.chmod(path, 0o644)


def og_rel(name: str, lang: str) -> str:
    return f"/images/og/{name}.jpg" if lang == BASE_LANG else f"/images/og/{lang}/{name}.jpg"


def thumb_rel(name: str, lang: str) -> str:
    return f"/images/thumbs/{name}.jpg" if lang == BASE_LANG else f"/images/thumbs/{lang}/{name}.jpg"


def disk(rel: str) -> Path:
    return HTTPDOCS / rel.lstrip("/")


def drop(rel: str) -> None:
    """Een beeld per taal dat niet meer nodig is (de taalversie ziet er hetzelfde uit)."""
    path = disk(rel)
    if path.is_file():
        path.unlink()


def wall_images(page: dict, site: dict, html: str, y: int) -> dict[str, Image.Image | None]:
    """Screenshot, OG-kaart en thumbnail per taal. Een taal krijgt alleen eigen
    beelden als hij er anders uitziet: zelfde shot en zelfde titel = de Nederlandse."""
    slug = page["slug"]
    shots: dict[str, Image.Image | None] = {}
    page["l"] = {}
    base = None
    for lang in LANGS:
        shot = capture_page(slug, html, y, lang)
        shots[lang] = shot
        b = both(page)[lang]
        view = {**page, "title": b["title"], "subtitle": b["subtitle"]}
        same_shot = base is not None and shot is not None and shots[BASE_LANG] is not None and same_image(shot, shots[BASE_LANG])
        og = og_rel(slug, lang)
        if same_shot and b["title"] == base["title"]:
            drop(og)
            og = base["ogImage"]
        else:
            generate_og(view, site, shot, disk(og))
            os.chmod(disk(og), 0o644)
        th = thumb_rel(slug, lang)
        if shot is None:
            drop(th)
            th = og
        elif same_shot:
            drop(th)
            th = base["thumb"]
        else:
            # schone thumbnail (zonder label) voor de kaarten op de homepage en onder de wanden
            save_jpeg(cover(shot, 800, 420), disk(th), 84)
        page["l"][lang] = {
            "path": lang_path(page["path"], lang),
            "title": b["title"],
            "subtitle": b["subtitle"],
            "ogImage": og,
            "thumb": th,
            "v": hashlib.sha1(disk(th).read_bytes()).hexdigest()[:8],
        }
        if lang == BASE_LANG:
            base = page["l"][lang]
    page["ogImage"] = base["ogImage"]
    page["thumb"] = base["thumb"]
    return shots


def main() -> None:
    site = load_site()
    pages: list[dict] = []
    shots: dict[str, dict[str, Image.Image | None]] = {}
    positions = load_shot_positions()
    sources: list[tuple[str, dict]] = []
    for d in slug_dirs():
        slug = d.name
        html = (d / "index.html").read_text(encoding="utf-8")
        page = parse_page(slug, html)
        shots[slug] = wall_images(page, site, html, positions.get(slug, 0))
        pages.append(page)
        sources.append((html, page))

    # één bron per wand: Nederlands op /<slug>/ (het bronbestand), Engels op /en/<slug>/
    for html, page in sources:
        for lang in LANGS:
            write_lang_file(f"{page['slug']}/index.html", lang, render_wall(html, page, site, lang))

    public_pages = [
        {**{k: v for k, v in p.items() if k != "l"}, "languages": {l: {k: v for k, v in p["l"][l].items() if k != "v"} for l in LANGS}}
        for p in pages
    ]
    payload = {"site": {"name": site["name"], "baseUrl": site["baseUrl"]}, "pages": public_pages}
    write_public(
        PAGES_JSON,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )

    index_path = HTTPDOCS / "index.html"
    if index_path.is_file():
        source = index_path.read_text(encoding="utf-8")
        home = {"title": site["name"], "path": "/", "og": {}}
        for lang in LANGS:
            tagline = site_t("tagline", lang)
            rel = og_rel("index", lang)
            home["og"][lang] = rel
            rows = [[shots[p["slug"]][lang] for p in items if shots[p["slug"]][lang] is not None] for _k, _l, items in series_of(pages)]
            if any(rows):
                generate_index_og(site, rows, disk(rel), tagline)
            else:
                generate_og_fallback({**home, "subtitle": tagline, "slug": "index", "theme": "#13202b"}, disk(rel))
            os.chmod(disk(rel), 0o644)
            write_lang_file("index.html", lang, render_home(source, pages, site, home, lang))

    write_sitemap(site, pages)
    write_nav_assets(pages, site)
    print(f"Built {len(pages)} pages in {len(LANGS)} languages → {PAGES_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
