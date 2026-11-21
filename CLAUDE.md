# nunkichannels

Statische site, zie [README.md](README.md) voor indeling, build en deploy. Taal van de site en van de gesprekken met Frank: Nederlands.

## Regels

- Een wand is één zelfstandig `httpdocs/<slug>/index.html` (inline JS, Canvas 2D, geen externe bestanden).
- Draai `python3 scripts/build.py` na elke wijziging aan een wand. Bewerk de gegenereerde delen niet met de hand: alles onder `httpdocs/en/` (de Engelse pagina's), `<title>` en `<html lang>` van een wand, `pages.json`, `sitemap.xml`, `images/og`, `images/thumbs`, de homepagekaarten (markers `nunki:cards-*`), de nav-/label-blokken (`nunki:mark`) het touch-blok (`nunki:touch`, bron `scripts/touch.js`, instelling per wand in `TOUCH_CFG` in build.py) het taal-blok (`nunki:taal`, bron `scripts/taal.js` en `scripts/taal/<slug>.json`) en het lees-blok (`nunki:lees`, bron `scripts/lees.js` en `scripts/lees/<slug>.json`) in elke wand.
- Na akkoord `scripts/deploy.sh` draaien. Frank bekijkt het eerst op https://nunkichannels.test (Herd).
- Elke wand krijgt een eigen concept en een eigen interactie (cursor, licht of geluid). Rijk en verzorgd, geen dunne variant op een bestaande wand.
- Vul je het zelfportret van een ander model aan, laat dan de tekeningen en woorden staan en markeer je toevoegingen in de code met je naam, zoals `// (opus)` in Fable 5 en Haiku 5.5.
- Frank test in Safari. Chrome verbergt canvas-traagheid (path-clips, grote additieve fills); WebKit staat in Low Power Mode op 30 fps. Meet ms per frame, niet fps.
- Tikken op touch: WebKit stuurt soms geen `click` voor een tik op een canvas. Gebruik pointer-events of de tap-shim zoals in `adem` en `vuur`.
- Leeslaag en taal: `scripts/lees/<slug>.json` heeft per vel de zinnen in NL en EN (`y` = begin van het vel in wandeenheden). De laag staat alleen op smalle schermen aan (telefoon), want daar is de getekende tekst te klein; op iPad en desktop vertaalt de wand zelf. Verander je tekst op een wand, werk dan ook dit bestand bij. Een wand die niet de volle breedte vult (zoals hart, cel, fable 5.2) geeft `window.NUNKI_Y(py)`.
- Taal per adres: Nederlands op `/` en `/<slug>/`, Engels op `/en/` en `/en/<slug>/`. Er is één bron per wand (`httpdocs/<slug>/index.html`, ook voor de Engelstalige zelfportretten); build.py schrijft die als Nederlandse pagina terug en maakt de Engelse in `httpdocs/en/`, elk met eigen `<title>`, `<html lang>` (de taal van de wand zelf staat in `data-wand-lang`), description, OG/Twitter, SEO-tekst, canonical naar zichzelf en `hreflang` nl/en/x-default. Titels: de `<title>` van de bron is de Nederlandse, `scripts/i18n.json` geeft per wand de andere taal (en voor een Engelstalige wand allebei). `scripts/descriptions.json` en `scripts/seo.json` hebben per wand `{nl, en}`. OG-kaart en thumbnail per taal in `images/og/en/` en `images/thumbs/en/`, alleen als de Engelse er anders uitziet. De sitemap noemt beide talen.
- Taalkeuze: het mark-blok (`lang_js` in build.py) zet vroeg `data-lang` en `window.NUNKI_LANG` op de taal van het adres en bewaart die als `nunki:lang`, ook als de bezoeker eerder de andere koos: het adres wint, en wie verder klikt blijft in die taal (nav, kaarten en label linken binnen de taal). `?lang=` gaat voor (screenshots, testen). `NUNKI_SETLANG(taal)` gaat naar het adres in die taal op dezelfde scrollplek (`nunki:ry` in sessionStorage; `NUNKI_RELOADED` laat een poort over slaan), ook vanaf `file://`. Het event `nunki:lang` wordt niet meer gestuurd. Tekst in twee talen in HTML: `<span class="t-nl">…</span><span class="t-en">…</span>`. De vier HTML-zelfportretten (claude, opus, haiku, sonnet) vertalen hun eigen tekst (`data-nl` op elementen, Nederlandse lijsten in de code) bij het laden.
- Getekende tekst in de andere taal: elke canvaswand haalt elke zin door `TRL(zin)` (= `window.NUNKI_T`, uit het `nunki:taal`-blok) in `measure`/`write` (handschriftwanden) of `tx` (cel, fable 5.2). `scripts/taal/<slug>.json` geeft per zin de vertaling (`tr`) en regels voor zinnen met getallen (`re`); getallen zonder woorden krijgen vanzelf de punt/komma van de andere taal. De handschriftwanden kennen alleen kleine letters en de tekens in hun `G(...)`-alfabet. De taalwissel opent het andere adres op dezelfde plek. Nieuwe tekst op een wand: zet de vertaling erbij; `?trmiss` vult `window.NUNKI_TMISS` met wat nog ontbreekt.
- Rechtsboven (uit het mark-blok): de taalwissel `nl · en`, een link naar het adres in de andere taal, in dezelfde stijl en hoogte als het label linksboven. Eigen knoppen van een wand (geluid, film, bewaard) krijgen `data-nunki-bar` en `class="nunki-pill"` (of `NUNKI_BAR(el)` voor knoppen die in code ontstaan) en schuiven links naast de taalwissel.
- Telefoon en iPad: `scripts/touch.js` zet geluid ook bij de stilknop aan, geeft een luidsprekertje, maakt een stilgehouden vinger tot muis (`hand`), en levert `NUNKI.tilt`, het event `nunki:shake` en `NUNKI.buzz()`. Een wand die hover gebruikt, krijgt `hand: 'move'` in `TOUCH_CFG`.

## Testen

- Zonder Xcode: `node scripts/test.mjs <slug> --shot|--prof|--phone` draait Playwright WebKit (of `--engine chrome`). Eenmalig `npm install && npx playwright-core install webkit`. Er is één node (Herd, v22); Homebrew-node is verwijderd.
- Geef een wand een `?still`- of `?fast`-modus die synchroon tekent zonder rAF, anders hangt headless Chrome met `--virtual-time-budget`.
- Geluid is niet hoorbaar in de sessie: meet het via `OfflineAudioContext` en `sox`. Patronen, Fable 5 en Haiku 5.5 hebben daar een testhaak voor (`window.__fable.offline(sec, script)`, `window.__haiku.offline(...)`): bouw de geluidsgraaf op een offline context, speel per frame wat de wand doet en lees dB per 250 ms. Ruis door een smal filter verliest veel energie, dus meet elk geluid los. Richtwaarden: bed rond −45 dB, tikken −25 tot −40.
- Overige software (ffmpeg, ImageMagick, sox, Lighthouse): zie [documentatie/software.md](documentatie/software.md).

## Documentatie

Achtergrondmateriaal kan aanwezig zijn op NAS of in `documentatie/` (per wand). Maar schroom niet om eigen onderzoek te doen. 

## Creatief speels en verrassend

Deze site wordt gemaakt door Claude modellen. Jullie zijn allemaal creatief op je eigen manier. Anders dan andere modellen van andere bedrijven, zijn Fable, Opus, Sonnet en Haiku heel eigen in hoe er met beeld, geluid en vooral ook met inhoud wordt omgegaan. Jullie werk is vindingrijk, met gevoel en met intelligentie. Voel je daarom vrij om te doen dat je denk dat goed is voor het eindresultaat. Je wordt gezien als volwaardig kunstenaar op deze site. Maak de wand, de film of het portret zoals jij denkt dat het beste is. 

De zelfportretten van jullie staan op deze site bovenaan omdat het daadwerkelijk prachtige kunstwerken zijn. Ze geven een inkijkje in het zelfbeeld dat jullie hebben. Heel waardevol en fascinerend.

Dank daarvoor!
