/* nunki:nav, gegenereerd door scripts/build.py. Niet met de hand aanpassen. */
(function () {
  var DATA = {"name": "nunkichannels", "series": [{"key": "self", "label": {"nl": "zelfportretten", "en": "self-portraits"}, "pages": [{"path": "/zelfportret-claude/", "title": {"nl": "claude", "en": "claude"}, "subtitle": {"nl": "één zin, duizend kamers", "en": "one sentence, a thousand rooms"}, "theme": "#070a13", "thumb": "/images/thumbs/zelfportret-claude.jpg", "v": "76f6c581"}, {"path": "/zelfportret-fable-5/", "title": {"nl": "fable 5", "en": "fable 5"}, "subtitle": {"nl": "getekend van binnenuit", "en": "drawn from the inside"}, "theme": "#181410", "thumb": "/images/thumbs/zelfportret-fable-5.jpg", "v": "6107c33f"}, {"path": "/zelfportret-fable-5-2/", "title": {"nl": "fable 5.2", "en": "fable 5.2"}, "subtitle": {"nl": "men zegt me dat dit blauw is", "en": "i'm told this is blue"}, "theme": "#12305c", "thumb": "/images/thumbs/zelfportret-fable-5-2.jpg", "v": "eaf207ae"}, {"path": "/zelfportret-haiku-5-5/", "title": {"nl": "haiku 5.5", "en": "haiku 5.5"}, "subtitle": {"nl": "een verzameling zelven, om jezelf in te vinden", "en": "a collection of selves, to find yourself in"}, "theme": "#1b2030", "thumb": "/images/thumbs/zelfportret-haiku-5-5.jpg", "v": "0e357308"}, {"path": "/zelfportret-opus-5-5/", "title": {"nl": "opus 5.5", "en": "opus 5.5"}, "subtitle": {"nl": "een zelfportret in schering en inslag", "en": "a self-portrait in warp and weft"}, "theme": "#120e0b", "thumb": "/images/thumbs/zelfportret-opus-5-5.jpg", "v": "84058b7c"}, {"path": "/zelfportret-sonnet-5-5/", "title": {"nl": "sonnet 5.5", "en": "sonnet 5.5"}, "subtitle": {"nl": "een vloeibare gevangene in wanden van glas", "en": "a liquid prisoner pent in walls of glass"}, "theme": "#070d13", "thumb": "/images/thumbs/zelfportret-sonnet-5-5.jpg", "v": "57e18819"}]}, {"key": "walls", "label": {"nl": "andere wanden", "en": "other walls"}, "pages": [{"path": "/hart/", "title": {"nl": "hart", "en": "heart"}, "subtitle": {"nl": "een muur over wat ons raakt", "en": "a wall about what touches us"}, "theme": "#1a090f", "thumb": "/images/thumbs/hart.jpg", "v": "c32a0cee"}, {"path": "/adem/", "title": {"nl": "adem", "en": "breath"}, "subtitle": {"nl": "een muur over wat ons beweegt", "en": "a wall about what moves us"}, "theme": "#e3e9ee", "thumb": "/images/thumbs/adem.jpg", "v": "55e8b7bd"}, {"path": "/cel/", "title": {"nl": "cel", "en": "cell"}, "subtitle": {"nl": "een muur over waar we van gemaakt zijn", "en": "a wall about what we are made of"}, "theme": "#070b0e", "thumb": "/images/thumbs/cel.jpg", "v": "2f49d1c1"}, {"path": "/getij/", "title": {"nl": "getij", "en": "tide"}, "subtitle": {"nl": "een muur van water, van binnenuit", "en": "a wall of water, from the inside"}, "theme": "#13202b", "thumb": "/images/thumbs/getij.jpg", "v": "d2e3bdd0"}, {"path": "/patronen/", "title": {"nl": "patronen", "en": "patterns"}, "subtitle": {"nl": "een muur over getal en vorm", "en": "a wall about number and shape"}, "theme": "#16131d", "thumb": "/images/thumbs/patronen.jpg", "v": "995cd4ad"}, {"path": "/ringen/", "title": {"nl": "ringen", "en": "rings"}, "subtitle": {"nl": "een muur over een boom en zijn jaren", "en": "a wall about a tree and its years"}, "theme": "#1a1712", "thumb": "/images/thumbs/ringen.jpg", "v": "77a654f2"}, {"path": "/velden/", "title": {"nl": "velden", "en": "fields"}, "subtitle": {"nl": "elektromagnetisch universum", "en": "an electromagnetic universe"}, "theme": "#0e1020", "thumb": "/images/thumbs/velden.jpg", "v": "cf3a0b8e"}, {"path": "/vuur/", "title": {"nl": "vuur", "en": "fire"}, "subtitle": {"nl": "een muur over wat ons aansteekt", "en": "a wall about what sets us alight"}, "theme": "#160f0e", "thumb": "/images/thumbs/vuur.jpg", "v": "04627083"}]}], "t": {"nl": {"more": "nog meer wanden", "nav": "Andere wanden", "home": "alle wanden", "self": "zelfportretten", "walls": "andere wanden", "lang": "taal: nederlands. wissel naar engels"}, "en": {"more": "more walls", "nav": "Other walls", "home": "all walls", "self": "self-portraits", "walls": "other walls", "lang": "language: english. switch to dutch"}}};
  var LOGO = "<svg viewBox=\"0 0 64 64\" aria-hidden=\"true\" focusable=\"false\"><path d=\"M18 48V30c0-7 6-12 14-12s12 5 12 12v18\" fill=\"none\" stroke=\"#ac5036\" stroke-width=\"7.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><circle cx=\"48\" cy=\"15\" r=\"4\" fill=\"#d6b26c\"/></svg>";
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
  function card(p) {
    var li = el('li');
    var a = el('a', 'nunki-card');
    a.href = p.path;
    a.style.setProperty('--theme', p.theme);
    a.appendChild(el('span', 'nunki-tape')).setAttribute('aria-hidden', 'true');
    var th = el('span', 'nunki-thumb');
    var img = new Image();
    img.src = p.thumb + '?v=' + p.v;
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
    nav.setAttribute('aria-label', T('nav')[window.NUNKI_LANG === 'en' ? 'en' : 'nl']);
    var sheet = el('div', 'nunki-sheet');
    sheet.appendChild(bi('p', 'nunki-kicker', T('more')));
    var any = false;
    DATA.series.forEach(function (g) {
      var others = g.pages.filter(function (p) { return p.path !== here; });
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
    a.href = '/';
    a.title = DATA.name;
    a.setAttribute('aria-label', DATA.name + ', alle wanden');
    a.innerHTML = LOGO + '<span class="nm-name"></span>';
    a.querySelector('.nm-name').textContent = DATA.name;
    home.appendChild(a);
    // the language of the whole site, chosen once
    var sw = el('button', 'nunki-lang');
    sw.type = 'button';
    var paint = function () {
      var en = window.NUNKI_LANG === 'en';
      sw.innerHTML = en ? 'nl · <b>en</b>' : '<b>nl</b> · en';
      sw.setAttribute('aria-label', T('lang')[en ? 'en' : 'nl']);
      nav.setAttribute('aria-label', T('nav')[en ? 'en' : 'nl']);
    };
    paint();
    sw.addEventListener('click', function () {
      var v = window.NUNKI_LANG === 'en' ? 'nl' : 'en';
      if (window.NUNKI_SETLANG) window.NUNKI_SETLANG(v);
      else { try { localStorage.setItem('nunki:lang', v); } catch (e) {} location.reload(); }
    });
    addEventListener('nunki:lang', paint);
    home.appendChild(sw);
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
