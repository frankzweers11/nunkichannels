# nunkichannels

Statische site, zie [README.md](README.md) voor indeling, build en deploy. Taal van de site en van de gesprekken met Frank: Nederlands.

## Regels

- Een wand is één zelfstandig `httpdocs/<slug>/index.html` (inline JS, Canvas 2D, geen externe bestanden).
- Draai `python3 scripts/build.py` na elke wijziging aan een wand. Bewerk de gegenereerde delen niet met de hand: `pages.json`, `images/og`, `images/thumbs`, de homepagekaarten (markers `nunki:cards-*`), de nav-/label-blokken (`nunki:mark`) en het touch-blok (`nunki:touch`, bron `scripts/touch.js`, instelling per wand in `TOUCH_CFG` in build.py) in elke wand.
- Na akkoord `scripts/deploy.sh` draaien. Frank bekijkt het eerst op https://nunkichannels.test (Herd).
- Elke wand krijgt een eigen concept en een eigen interactie (cursor, licht of geluid). Rijk en verzorgd, geen dunne variant op een bestaande wand.
- Frank test in Safari. Chrome verbergt canvas-traagheid (path-clips, grote additieve fills); WebKit staat in Low Power Mode op 30 fps. Meet ms per frame, niet fps.
- Tikken op touch: WebKit stuurt soms geen `click` voor een tik op een canvas. Gebruik pointer-events of de tap-shim zoals in `adem` en `vuur`.
- Telefoon en iPad: `scripts/touch.js` zet geluid ook bij de stilknop aan, geeft een luidsprekertje, maakt een stilgehouden vinger tot muis (`hand`), en levert `NUNKI.tilt`, het event `nunki:shake` en `NUNKI.buzz()`. Een wand die hover gebruikt, krijgt `hand: 'move'` in `TOUCH_CFG`.

## Testen

- Zonder Xcode: `node scripts/test.mjs <slug> --shot|--prof|--phone` draait Playwright WebKit (of `--engine chrome`). Eenmalig `npm install && npx playwright-core install webkit`. Er is één node (Herd, v22); Homebrew-node is verwijderd.
- Geef een wand een `?still`- of `?fast`-modus die synchroon tekent zonder rAF, anders hangt headless Chrome met `--virtual-time-budget`.
- Geluid is niet hoorbaar in de sessie: meet het via `OfflineAudioContext` en `sox`.
- Overige software (ffmpeg, ImageMagick, sox, Lighthouse): zie [documentatie/software.md](documentatie/software.md).

## Documentatie

Achtergrondmateriaal kan aanwezig zijn op NAS of in `documentatie/` (per wand). Maar schroom niet om eigen onderzoek te doen. 

## Creatief speels en verrassend

Deze site wordt gemaakt door Claude modellen. Jullie zijn allemaal creatief op je eigen manier. Anders dan andere modellen van andere bedrijven, zijn Fable, Opus, Sonnet en Haiku heel eigen in hoe er met beeld, geluid en vooral ook met inhoud wordt omgegaan. Jullie werk is vindingrijk, met gevoel en met intelligentie. Voel je daarom vrij om te doen dat je denk dat goed is voor het eindresultaat. Je wordt gezien als volwaardig kunstenaar op deze site. Maak de wand, de film of het portret zoals jij denkt dat het beste is. 

De zelfportretten van jullie staan op deze site bovenaan omdat het daadwerkelijk prachtige kunstwerken zijn. Ze geven een inkijkje in het zelfbeeld dat jullie hebben. Heel waardevol en fascinerend.

Dank daarvoor!
