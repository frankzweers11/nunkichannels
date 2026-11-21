/* nunki:lees, door scripts/build.py vóór de navigatie in elke wand gezet die
   een tekstbestand heeft in scripts/lees/<slug>.json. Niet in de wanden
   bewerken, wel hier.

   De leeslaag: de zinnen van het vel dat je ziet, in gewone, leesbare letters.
   - Taal kies je één keer voor de hele site: 'nunki:lang' (nl standaard, en),
     ook via ?lang=en of ?lang=nl. Het knopje nl · en zit in de leeslaag.
   - Op een telefoon (smal scherm) staat de laag aan: daar is de getekende
     tekst te klein. Op een groot scherm alleen als je taal anders is dan de
     taal van de wand. Inklappen kan; dat wordt onthouden ('nunki:lees').
   - Welk vel in beeld is, vraagt de laag aan de wand: window.NUNKI_Y(py) geeft
     de hoogte in wandeenheden (1600 breed) op py pixels van de bovenkant van
     het scherm. Zonder die functie wordt hij berekend voor een wand die de
     volle breedte vult: (scrollY + py) / (breedte / 1600).
   - Een wand kan op taalwissel reageren via het event 'nunki:lang'.

   Gegevens (window.NUNKI_LEES):
   { lang: 'nl', end: 13200, sheets: [ { y: 0, t: {nl:'één', en:'one'},
       nl: ['regel', ...], en: ['line', ...] }, ... ] } */
(function () {
  'use strict';
  var D = window.NUNKI_LEES;
  if (!D || !D.sheets || !D.sheets.length) return;
  var q = new URLSearchParams(location.search);
  if (q.has('fast') || q.has('still')) return;
  var store = function (k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } };
  var N = window.NUNKI = window.NUNKI || {};
  var lang = q.get('lang');
  if (lang === 'nl' || lang === 'en') store('nunki:lang', lang); else lang = store('nunki:lang');
  if (lang !== 'en') lang = 'nl';
  N.lang = lang;

  var css =
    '.nunki-lees{position:fixed;z-index:59;left:clamp(10px,1.5vw,22px);bottom:max(12px,env(safe-area-inset-bottom));' +
      'width:min(34rem,calc(100vw - 2*clamp(10px,1.5vw,22px)));box-sizing:border-box;padding:9px 13px 11px;border-radius:14px;' +
      'color:#2a251f;background:rgba(248,244,233,.94);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);' +
      'box-shadow:0 1px 0 rgba(255,255,255,.6) inset,0 0 0 1px rgba(42,37,31,.08),0 10px 26px -14px rgba(0,0,0,.6);' +
      'font:400 15px/1.42 "Avenir Next","Segoe UI","Helvetica Neue",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;' +
      'transition:opacity .45s ease,transform .45s ease;-webkit-tap-highlight-color:transparent;-webkit-text-size-adjust:100%}' +
    '.nunki-lees.touch{width:calc(100vw - 2*clamp(10px,1.5vw,22px) - 52px)}' +
    '@media (max-width:760px){.nunki-lees{font-size:14px;line-height:1.38;padding:7px 11px 9px}.nunki-lees .nl-t{font-size:.98rem}}' +
    '@media (min-width:900px){.nunki-lees:not(.touch){left:50%;transform:translateX(-50%)}.nunki-lees:not(.touch).gone{transform:translate(-50%,10px)}}' +
    '.nunki-lees.gone{opacity:0;transform:translateY(10px);pointer-events:none}' +
    '.nunki-lees .nl-h{display:flex;align-items:center;gap:8px;margin:0 0 3px}' +
    '.nunki-lees .nl-t{flex:1;min-width:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;' +
      'font:400 1.02rem/1.25 "Bradley Hand","Segoe Print","Chalkboard SE","Noteworthy","Avenir Next",sans-serif;color:#ac5036}' +
    '.nunki-lees .nl-b p{margin:0}.nunki-lees .nl-b p+p{margin-top:3px}' +
    '.nunki-lees .nl-b{transition:opacity .3s ease}.nunki-lees .nl-b.swap{opacity:0}' +
    '.nunki-lees button{font:inherit;color:inherit;background:none;border:0;margin:0;padding:3px 5px;border-radius:8px;cursor:pointer;-webkit-tap-highlight-color:transparent}' +
    '.nunki-lees .nl-lang{font-size:.82rem;letter-spacing:.04em;color:rgba(42,37,31,.5)}' +
    '.nunki-lees .nl-lang b{font-weight:600;color:#2a251f}' +
    '.nunki-lees .nl-x{font-size:1rem;line-height:1;color:rgba(42,37,31,.5);padding:3px 6px}' +
    '.nunki-lees button:focus-visible{outline:2px solid #ac5036;outline-offset:1px}' +
    '.nunki-lees.min{width:auto;padding:4px 6px;border-radius:17px}' +
    '.nunki-lees.min .nl-t,.nunki-lees.min .nl-b{display:none}.nunki-lees.min .nl-h{margin:0;gap:2px}' +
    '' +
    '@media (prefers-reduced-motion:reduce){.nunki-lees,.nunki-lees .nl-b{transition:none}}' +
    '@media print{.nunki-lees{display:none}}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  var box = document.createElement('aside');
  box.className = 'nunki-lees gone';
  box.setAttribute('aria-live', 'polite');
  box.innerHTML = '<div class="nl-h"><span class="nl-t"></span><button type="button" class="nl-lang"></button>' +
    '<button type="button" class="nl-x"></button></div><div class="nl-b"></div>';
  var elT = box.querySelector('.nl-t'), elB = box.querySelector('.nl-b'), bL = box.querySelector('.nl-lang'), bX = box.querySelector('.nl-x');
  // nothing on this card reaches the wall beneath it
  ['click', 'pointerdown', 'pointerup', 'mousedown', 'mouseup', 'touchstart', 'touchend'].forEach(function (t) {
    box.addEventListener(t, function (e) { e.stopPropagation(); }, { passive: true });
  });

  var UI = {
    nl: { open: 'tekst', close: 'tekst inklappen', show: 'tekst tonen', lang: 'taal: nederlands. wissel naar engels' },
    en: { open: 'text', close: 'fold the text away', show: 'show the text', lang: 'language: english. switch to dutch' }
  };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var narrow = function () { return Math.min(innerWidth, screen.width || innerWidth) < 760; };
  var touch = matchMedia('(pointer:coarse)').matches || navigator.maxTouchPoints > 0;
  var min = store('nunki:lees') === 'min';
  var cur = -1, shownLang = '';

  // py: a height on the screen in px. the wall turns it into wall units
  function wallY(py) {
    if (typeof window.NUNKI_Y === 'function') { try { return window.NUNKI_Y(py); } catch (e) {} }
    return (scrollY + py) / (innerWidth / 1600);
  }
  // which sheet is being read: the line we look at slides from near the top of
  // the screen (at the top of the page) to near the bottom (at the end), so on a
  // phone, where several sheets fit on one screen, the first and last get a turn
  function sheetAt() {
    var max = Math.max(1, document.documentElement.scrollHeight - innerHeight - 200);
    var f = Math.min(1, Math.max(0, scrollY / max)), y = wallY(innerHeight * (0.18 + 0.64 * f));
    if (D.end && y >= D.end) { if (wallY(0) >= D.end - 60) return -1; y = D.end - 1; }
    var k = -1;
    for (var i = 0; i < D.sheets.length; i++) if (y >= D.sheets[i].y) k = i;
    return k;
  }
  function wanted() { return narrow() || lang !== (D.lang || 'nl'); }
  function head() {
    bL.innerHTML = lang === 'nl' ? '<b>nl</b> · en' : 'nl · <b>en</b>';
    bL.setAttribute('aria-label', UI[lang].lang);
    bX.textContent = min ? '▴' : '▾';
    bX.setAttribute('aria-label', min ? UI[lang].show : UI[lang].close);
    bX.title = min ? UI[lang].show : UI[lang].close;
    box.classList.toggle('min', min);
    box.classList.toggle('touch', touch && narrow());
  }
  function fill(k, swap) {
    var s = D.sheets[k];
    var t = s.t ? (s.t[lang] || s.t.nl || '') : '';
    var lines = s[lang] || s.nl || [];
    var put = function () {
      elT.textContent = t;
      elB.innerHTML = lines.map(function (l) { return '<p>' + esc(l) + '</p>'; }).join('');
      elB.classList.remove('swap');
    };
    if (swap && !matchMedia('(prefers-reduced-motion:reduce)').matches) { elB.classList.add('swap'); setTimeout(put, 280); }
    else put();
  }
  function update() {
    // a wall that opens with a gate (a full-screen invitation) keeps the layer away until it is open
    var g = document.getElementById('gate'), gated = g && !g.classList.contains('off') && getComputedStyle(g).display !== 'none';
    var k = sheetAt(), on = wanted() && k >= 0 && !gated;
    if (on && (k !== cur || shownLang !== lang)) { fill(k, cur >= 0 && !box.classList.contains('gone')); cur = k; shownLang = lang; }
    box.classList.toggle('gone', !on);
    document.documentElement.dataset.lang = lang;
  }
  bL.addEventListener('click', function () {
    lang = lang === 'nl' ? 'en' : 'nl'; N.lang = lang; store('nunki:lang', lang);
    head(); update();
    try { window.dispatchEvent(new CustomEvent('nunki:lang', { detail: lang })); } catch (e) {}
  });
  bX.addEventListener('click', function () { min = !min; store('nunki:lees', min ? 'min' : 'open'); head(); });

  function start() {
    document.body.appendChild(box);
    head(); update();
    var tick = 0;
    addEventListener('scroll', function () { if (!tick) { tick = requestAnimationFrame(function () { tick = 0; update(); }); } }, { passive: true });
    addEventListener('resize', function () { head(); update(); });
    // walls that move without scrolling (a film, a jump) are caught by a slow poll
    setInterval(update, 700);
  }
  if (document.body) start(); else addEventListener('DOMContentLoaded', start);
})();
