# nunkichannels

Statische site (nunkichannels.nl): een verzameling scrollende "wanden", elk één zelfstandige HTML-pagina met inline JavaScript en Canvas 2D. Geen framework, geen bundler.

## Indeling

```
httpdocs/            wat live gaat (rsync-doel)
  <slug>/index.html  één wand
  index.html         homepage (kaarten worden door build.py ingevuld)
  nav.js, nav.css    gedeelde navigatie onder elke wand
  site.json          naam en baseUrl
  pages.json         gegenereerd door build.py
  images/og, thumbs  gegenereerd door build.py
  sitemap.xml, robots.txt
scripts/
  build.py           scant wanden, maakt OG-beelden, thumbs, pages.json, homepage, nav, SEO
  touch.js           geluid, vinger-als-hand, kantelen/schudden en trillen op telefoon en iPad; build.py zet het inline in elke wand
  lees.js            de leeslaag: zinnen per vel in NL/EN onderin beeld, taalkeuze nl · en; build.py zet het inline in elke wand met een tekstbestand
  lees/<slug>.json   die zinnen, per vel
  deploy.sh          build + rsync naar de VPS
  descriptions.json, seo.json, shots.json   beschrijvingen, SEO-teksten, screenshot-posities
documentatie/        achtergrondmateriaal per wand (cel, film, one-6gmatrix, oude veld-wand)
```

Twee series: `zelfportret-*` (zelfportretten van Claude-modellen) en alle andere wanden. `zelfportret/` is alleen een doorverwijzing.

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

1. Maak `httpdocs/<slug>/index.html`. Zet `<title>naam · ondertitel</title>` en een `background:#hex` als themakleur.
2. De pagina moet zonder externe bestanden werken (ook vanaf `file://`) en met `?fast` synchroon een goed still tonen.
3. Laat de linkerbovenhoek vrij: build.py plaatst daar het naamlabel.
4. Voeg zo nodig een beschrijving toe in `scripts/descriptions.json` en `scripts/seo.json`, en een scrollpositie in `scripts/shots.json`.
5. `python3 scripts/build.py`.

## Deployen

```sh
scripts/deploy.sh
```

Draait de build en synchroniseert `httpdocs/` met `--delete` naar de VPS (`NUNKI_RSYNC_TARGET` en `NUNKI_RSYNC_PATH` overschrijven het doel). Dit publiceert direct, dus alleen draaien als je dat echt wilt.
