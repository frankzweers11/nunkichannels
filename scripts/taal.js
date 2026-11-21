/* nunki:taal, door scripts/build.py direct na het label gezet in elke wand die
   een vertaalbestand heeft in scripts/taal/<slug>.json. Niet in de wanden
   bewerken, wel hier.

   De getekende tekst van een wand in de gekozen taal. De wand haalt elke zin
   die hij gaat tekenen door window.NUNKI_T(zin): is de gekozen taal (nunki:lang)
   gelijk aan die van de wand, dan komt de zin ongewijzigd terug, anders de
   vertaling. Een wand tekent zijn tekst één keer, dus bij een taalwissel laadt
   de pagina opnieuw en springt terug naar dezelfde plek (tenzij live: true;
   dan regelt de wand het zelf via het event 'nunki:lang').

   Gegevens (window.NUNKI_TAAL):
   { lang: 'nl', tr: { 'zin': 'sentence', ... },
     re: [ ['^(\\d+) jaar$', '$1 years'], ... ],   // voor zinnen met een getal
     live: false }
   ?trmiss in het adres: window.NUNKI_TMISS houdt bij welke zinnen nog geen
   vertaling hebben (om te testen). */
(function () {
  'use strict';
  var D = window.NUNKI_TAAL || {}, W = D.lang || 'nl', M = D.tr || {}, V = {}, miss = {};
  var X = (D.re || []).map(function (r) { return [new RegExp(r[0]), r[1]]; });
  for (var k in M) V[M[k]] = 1;
  var other = function () { return (window.NUNKI_LANG || 'nl') !== W; };
  window.NUNKI_T = function (s) {
    if (typeof s !== 'string' || !other() || V[s] === 1) return s;
    var v = M[s];
    if (v != null) return v;
    var t = s.trim();
    if (t && t !== s && M[t] != null) return s.replace(t, M[t]);
    for (var i = 0; i < X.length; i++) if (X[i][0].test(s)) { var o = s.replace(X[i][0], X[i][1]); V[o] = 1; return o; }
    // numbers without words: thousands and decimals the way the other language writes them (22.000 / 22,000, 1,618 / 1.618)
    if (!/[a-z]/i.test(s) && /\d[.,]\d/.test(s)) { var n = s.replace(/(\d)([.,])(?=\d)/g, function (m, d, c) { return d + (c === '.' ? ',' : '.'); }); V[n] = 1; return n; }
    if (/[a-zà-ÿ]{2}/i.test(s)) miss[s] = (miss[s] || 0) + 1;
    return s;
  };
  window.NUNKI_TMISS = miss;
  window.NUNKI_TWALL = W;

  // the wall drew its words once: a new language means drawing it again, from the same place
  var KEY = 'nunki:ry';
  addEventListener('nunki:lang', function () {
    if (D.live) return;
    var h = Math.max(1, document.documentElement.scrollHeight);
    try { sessionStorage.setItem(KEY, JSON.stringify({ p: location.pathname, f: scrollY / h })); } catch (e) {}
    location.reload();
  });
  var r = null;
  try { r = JSON.parse(sessionStorage.getItem(KEY)); sessionStorage.removeItem(KEY); } catch (e) {}
  // the visitor was already inside: a wall with a gate can skip it
  if (r && r.p === location.pathname) window.NUNKI_RELOADED = true;
  if (r && r.p === location.pathname && r.f > 0) {
    var moved = false, go = function () { if (!moved) scrollTo(0, r.f * document.documentElement.scrollHeight); };
    var stop = function () { moved = true; };
    addEventListener('load', function () {
      go();
      [120, 400, 900, 1600].forEach(function (t) { setTimeout(go, t); });
      setTimeout(function () {
        addEventListener('wheel', stop, { passive: true, once: true });
        addEventListener('touchstart', stop, { passive: true, once: true });
        addEventListener('keydown', stop, { once: true });
      }, 0);
    });
  }
})();
