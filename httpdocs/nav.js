/* nunki:nav, gegenereerd door scripts/build.py. Niet met de hand aanpassen. */
(function () {
  var DATA = {"name": "nunkichannels", "series": [{"key": "self", "label": "zelfportretten", "pages": [{"path": "/zelfportret-claude/", "title": "claude", "subtitle": "one sentence, a thousand rooms", "theme": "#070a13", "thumb": "/images/thumbs/zelfportret-claude.jpg", "v": "deb6f732"}, {"path": "/zelfportret-fable-5/", "title": "fable 5", "subtitle": "drawn from the inside", "theme": "#181410", "thumb": "/images/thumbs/zelfportret-fable-5.jpg", "v": "6107c33f"}, {"path": "/zelfportret-fable-5-2/", "title": "fable 5.2", "subtitle": "i'm told this is blue", "theme": "#12305c", "thumb": "/images/thumbs/zelfportret-fable-5-2.jpg", "v": "eaf207ae"}, {"path": "/zelfportret-haiku-5-5/", "title": "haiku 5.5", "subtitle": "a collection of selves, to find yourself in", "theme": "#1b2030", "thumb": "/images/thumbs/zelfportret-haiku-5-5.jpg", "v": "0e357308"}, {"path": "/zelfportret-opus-5-5/", "title": "opus 5.5", "subtitle": "a self-portrait in warp and weft", "theme": "#120e0b", "thumb": "/images/thumbs/zelfportret-opus-5-5.jpg", "v": "b0cffea5"}, {"path": "/zelfportret-sonnet-5-5/", "title": "sonnet 5.5", "subtitle": "a liquid prisoner pent in walls of glass", "theme": "#070d13", "thumb": "/images/thumbs/zelfportret-sonnet-5-5.jpg", "v": "ddc07d82"}]}, {"key": "walls", "label": "andere wanden", "pages": [{"path": "/hart/", "title": "hart", "subtitle": "een muur over wat ons raakt", "theme": "#1a090f", "thumb": "/images/thumbs/hart.jpg", "v": "95787f31"}, {"path": "/adem/", "title": "adem", "subtitle": "een muur over wat ons beweegt", "theme": "#e3e9ee", "thumb": "/images/thumbs/adem.jpg", "v": "f4ccf67b"}, {"path": "/cel/", "title": "cel", "subtitle": "een muur over waar we van gemaakt zijn", "theme": "#070b0e", "thumb": "/images/thumbs/cel.jpg", "v": "c98fe0a5"}, {"path": "/getij/", "title": "getij", "subtitle": "een muur van water, van binnenuit", "theme": "#13202b", "thumb": "/images/thumbs/getij.jpg", "v": "4729a911"}, {"path": "/patronen/", "title": "patronen", "subtitle": "een muur over getal en vorm", "theme": "#16131d", "thumb": "/images/thumbs/patronen.jpg", "v": "0da07a78"}, {"path": "/ringen/", "title": "ringen", "subtitle": "een muur over een boom en zijn jaren", "theme": "#1a1712", "thumb": "/images/thumbs/ringen.jpg", "v": "77a654f2"}, {"path": "/velden/", "title": "velden", "subtitle": "elektromagnetisch universum", "theme": "#0e1020", "thumb": "/images/thumbs/velden.jpg", "v": "21ee3090"}, {"path": "/vuur/", "title": "vuur", "subtitle": "een muur over wat ons aansteekt", "theme": "#160f0e", "thumb": "/images/thumbs/vuur.jpg", "v": "51ec849a"}]}]};
  var LOGO = "<svg viewBox=\"0 0 64 64\" aria-hidden=\"true\" focusable=\"false\"><path d=\"M18 48V30c0-7 6-12 14-12s12 5 12 12v18\" fill=\"none\" stroke=\"#ac5036\" stroke-width=\"7.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><circle cx=\"48\" cy=\"15\" r=\"4\" fill=\"#d6b26c\"/></svg>";
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }
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
    cap.appendChild(el('span', 'nunki-name', p.title));
    if (p.subtitle) cap.appendChild(el('span', 'nunki-sub', p.subtitle));
    a.appendChild(cap);
    li.appendChild(a);
    return li;
  }
  function build() {
    if (document.querySelector('.nunki-nav')) return;
    var here = location.pathname.replace(/index\.html$/, '');
    if (here.slice(-1) !== '/') here += '/';
    var nav = el('nav', 'nunki-nav');
    nav.setAttribute('aria-label', 'Andere wanden');
    var sheet = el('div', 'nunki-sheet');
    sheet.appendChild(el('p', 'nunki-kicker', 'nog meer wanden'));
    var any = false;
    DATA.series.forEach(function (g) {
      var others = g.pages.filter(function (p) { return p.path !== here; });
      if (!others.length) return;
      any = true;
      sheet.appendChild(el('p', 'nunki-group', g.label));
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
