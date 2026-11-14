# Software voor het maken en testen van wanden

Wat op deze Mac staat en waarvoor het dient. De site zelf heeft geen build-afhankelijkheden; dit zijn alleen hulpmiddelen.

| Tool | Waarvoor | Installatie |
|---|---|---|
| Python 3 + Pillow | `scripts/build.py` (OG-beelden, thumbs, pages.json) | `python3 -m pip install -r requirements.txt` |
| Google Chrome | headless screenshots in de build; tweede testengine | app |
| Safari | de echte test (Frank bekijkt het hier) | app |
| Herd | lokale site op https://nunkichannels.test; levert ook node 22 (nvm) | app |
| node (Herd, v22) | draait `scripts/test.mjs`. Homebrew-node is verwijderd, er is één node | via Herd |
| playwright-core 1.50.1 | WebKit/Chrome aansturen | `npm install` |
| Playwright WebKit | Safari-engine voor tests | `npx playwright-core install webkit` (komt in `~/Library/Caches/ms-playwright`) |
| ffmpeg / ffprobe | film- en geluidsbestanden maken, knippen, analyseren (filmwand) | `brew install ffmpeg` |
| ImageMagick (`magick`) | beelden bijwerken, formaten omzetten | `brew install imagemagick` |
| sox | geluid meten en vergelijken (RMS, spectrogram), omdat Claude niet kan luisteren | `brew install sox` |
| Lighthouse | SEO, toegankelijkheid en prestaties van een pagina | `npx lighthouse https://nunkichannels.test/<slug>/ --view` |

## Een wand testen

```sh
node scripts/test.mjs <slug> --shot               # still als PNG in .cache/test
node scripts/test.mjs <slug> --prof               # ms per frame in WebKit
node scripts/test.mjs <slug> --phone --shot       # telefoon (390x844, touch)
node scripts/test.mjs <slug> --engine chrome      # in Chrome
node scripts/test.mjs <slug> --scroll 6000 --shot # een lager blad
node scripts/test.mjs <slug> --url https://nunkichannels.test
```

- Via `file://` meldt de test altijd dat `/nav.js` niet laadt. Dat is geen fout, de nav hoort bij de echte server.
- Een lage ms per frame in Chrome zegt weinig; kijk naar WebKit. Meet je ~33 ms, dan staat Low Power Mode aan of beperkt headless WebKit het. Vergelijk dan wanden onderling.
- De headless Chrome in `build.py` kan hangen bij een lopende rAF-lus: geef een wand daarom een `?fast`- of `?still`-modus die synchroon tekent.

## Geluid meten

Claude kan niet luisteren. Bouw de audiograaf van de wand op een `OfflineAudioContext`, render hem, en bekijk de uitvoer met `sox`:

```sh
sox uit.wav -n stat             # RMS en piek
sox uit.wav -n spectrogram -o uit.png
```

Streefwaarden uit adem: tik-whoosh piekt rond -35 dB RMS, adem -39, drone -50, donder -26.

## Lighthouse

Draai het tegen de Herd-site, niet tegen `file://`. De SEO-onderdelen (sitemap, JSON-LD, beschrijvingen) staan in `scripts/seo.json` en `scripts/descriptions.json`.
