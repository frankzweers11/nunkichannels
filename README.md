# nunkichannels

Statische site (nunkichannels.nl): een verzameling scrollende "wanden", elk één zelfstandige HTML-pagina met inline JavaScript en Canvas 2D. Geen framework, geen bundler.

## Indeling

```
httpdocs/            wat live gaat (rsync-doel)
  <slug>/index.html  één wand (de bron, en de Nederlandse pagina op /<slug>/)
  index.html         homepage (kaarten worden door build.py ingevuld)
  en/                gegenereerd: de Engelse homepage en wanden (/en/, /en/<slug>/)
  nav.js, nav.css    gedeelde navigatie onder elke wand
  site.json          naam en baseUrl
  pages.json         gegenereerd door build.py
  images/og, thumbs  gegenereerd door build.py (Engelse versies in og/en, thumbs/en)
  sitemap.xml, robots.txt   sitemap met beide talen
scripts/
  build.py           scant wanden, maakt OG-beelden, thumbs, pages.json, homepage, nav, SEO
  touch.js           geluid, vinger-als-hand, kantelen/schudden en trillen op telefoon en iPad; build.py zet het inline in elke wand
  lees.js            de leeslaag op de telefoon: zinnen per vel in NL/EN onderin beeld; build.py zet het inline in elke wand met een tekstbestand
  lees/<slug>.json   die zinnen, per vel
  taal.js            de getekende tekst van een wand in de gekozen taal (NUNKI_T); build.py zet het inline in elke wand met een vertaalbestand
  taal/<slug>.json   per wand: zin → vertaling, en regels voor zinnen met getallen
  i18n.json          site-teksten in NL en EN: navigatie, homepage-kaarten, label linksboven, en titels per wand
  deploy.sh          build + rsync naar de VPS
  descriptions.json, seo.json   meta-beschrijving en SEO-tekst per wand, per taal ({nl, en})
  shots.json         screenshot-posities
documentatie/        achtergrondmateriaal per wand (cel, film, one-6gmatrix, oude veld-wand)
```

Twee series: `zelfportret-*` (zelfportretten van Claude-modellen) en alle andere wanden. `zelfportret/` is alleen een doorverwijzing.

## Twee talen

Elk adres heeft één taal: Nederlands op `/` en `/<slug>/`, Engels op `/en/` en `/en/<slug>/`. Er is één bronbestand per wand; `build.py` schrijft het terug als Nederlandse pagina en maakt de Engelse in `httpdocs/en/`, met `<title>`, `<html lang>`, meta, OG-beeld, SEO-tekst, canonical en `hreflang` in de eigen taal. De taalwissel rechtsboven is een link naar het andere adres en houdt je scrollplek vast. Op de server is `/en/` gewoon een map: geen extra regels nodig.

## Bouwen

```sh
python3 -m pip install -r requirements.txt   # Pillow
python3 scripts/build.py
```

Voor de screenshots is Google Chrome nodig (headless). Draai de build na elke wijziging aan een wand.

## Testen

```sh
npm install && npx playwright-core install webkit   # eenmalig
node scripts/test.mjs <slug> --shot                 # of --prof, --phone, --engine chrome
```

Welke software waarvoor dient staat in [documentatie/software.md](documentatie/software.md).

## Een nieuwe wand toevoegen

1. Maak `httpdocs/<slug>/index.html`. Zet `<title>naam · ondertitel</title>` (Nederlands; schrijf je de wand in het Engels, zet dan beide talen in `scripts/i18n.json`) en een `background:#hex` als themakleur.
2. De pagina moet zonder externe bestanden werken (ook vanaf `file://`) en met `?fast` synchroon een goed still tonen.
3. Laat de linkerbovenhoek vrij: build.py plaatst daar het naamlabel.
4. Voeg een beschrijving toe in `scripts/descriptions.json` en `scripts/seo.json` (`{"nl": …, "en": …}`), de titel in de andere taal in `scripts/i18n.json`, en een scrollpositie in `scripts/shots.json`. Getekende tekst vertaal je in `scripts/taal/<slug>.json`.
5. `python3 scripts/build.py`.

## Deployen

```sh
scripts/deploy.sh
```

Draait de build en synchroniseert `httpdocs/` met `--delete` naar de VPS (`NUNKI_RSYNC_TARGET` en `NUNKI_RSYNC_PATH` overschrijven het doel). Dit publiceert direct, dus alleen draaien als je dat echt wilt.
