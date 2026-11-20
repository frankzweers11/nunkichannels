/* nunki:touch, door scripts/build.py inline in elke wand gezet (direct na <body>,
   dus vóór de scripts van de wand zelf). Niet in de wanden bewerken, wel hier.

   Zorgt dat geluid en aanraking ook op telefoon en iPad overkomen:
   1. geluid klinkt ook als de stilknop van de iPhone aan staat (Audio Session 'playback');
   2. op touch-schermen een luidsprekertje: tik voor geluid, nog eens voor stil;
   3. vinger even stilhouden en dan bewegen: je vinger is dan de hand (de muis) op
      de wand, en de pagina scrolt niet. loslaten en vegen scrolt weer gewoon;
   4. kantelen, schudden en het kompas: NUNKI.tilt {x,y}, het event 'nunki:shake',
      NUNKI.heading. pas na een eerste tik, en iOS vraagt eerst toestemming;
   5. NUNKI.buzz(ms): een tik voelbaar maken waar het toestel dat kan.

   De wand kiest via window.NUNKI_CFG (ook door build.py gezet):
   hand: 'move' (de vinger beweegt de muis), 'press' (ook ingedrukt, voor tekenen), 'off'
   motion: true als de wand iets met kantelen of schudden doet
   shake: 'tap' = schudden is een tik midden in beeld, 'own' = de wand luistert zelf
          naar 'nunki:shake'. */
(function () {
  'use strict';
  var C = window.NUNKI_CFG || {};
  var N = window.NUNKI = { tilt: { x: 0, y: 0, on: false }, heading: null, muted: false, ctx: [], hand: false, buzz: buzz, motion: motionOn };
  var coarse = matchMedia('(pointer:coarse)').matches || (navigator.maxTouchPoints > 0 && 'ontouchstart' in window);
  N.touch = coarse;
  var store = function (k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } };

  // ---- 1. sound that is heard, and that stays off when you turned it off ----
  var Orig = window.AudioContext || window.webkitAudioContext;
  if (Orig) {
    var Wrapped = function (o) { var c = o === undefined ? new Orig() : new Orig(o); track(c); return c; };
    Wrapped.prototype = Orig.prototype;
    try { window.AudioContext = Wrapped; if (window.webkitAudioContext) window.webkitAudioContext = Wrapped; } catch (e) {}
  }
  function track(c) {
    // without this an iPhone with its silent switch on plays nothing at all
    try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch (e) {}
    var resume = c.resume.bind(c);
    c.resume = function () { return N.muted ? Promise.resolve() : resume(); };
    c._nunkiResume = resume;
    N.ctx.push(c);
    if (N.muted) try { c.suspend(); } catch (e) {}
  }
  var playing = function () { for (var i = 0; i < N.ctx.length; i++) if (N.ctx[i].state === 'running') return true; return false; };

  // ---- 5. a tap you can feel ----
  var sw = null;
  function buzz(ms) {
    try {
      if (navigator.vibrate) { navigator.vibrate(ms || 10); return; }
      // safari on the iphone has no vibrate, but a switch that is flipped gives a small tick
      if (!coarse) return;
      if (!sw) {
        sw = document.createElement('label');
        sw.setAttribute('aria-hidden', 'true');
        sw.style.cssText = 'position:fixed;left:-99px;top:0;width:1px;height:1px;overflow:hidden;opacity:0;pointer-events:none';
        var i = document.createElement('input'); i.type = 'checkbox'; i.setAttribute('switch', ''); i.tabIndex = -1;
        sw.appendChild(i); document.body.appendChild(sw);
        // the switch's own clicks must not reach the wall, or every tap counts three times
        var stop = function (e) { e.stopPropagation(); };
        sw.addEventListener('click', stop); i.addEventListener('click', stop);
      }
      sw.click();
    } catch (e) {}
  }

  if (!coarse) return;
  var css = document.createElement('style');
  css.textContent =
    'html{touch-action:manipulation}body{-webkit-touch-callout:none;-webkit-user-select:none;user-select:none}' +
    '.nunki-snd{position:fixed;z-index:61;right:clamp(10px,1.5vw,22px);bottom:max(12px,env(safe-area-inset-bottom));width:42px;height:42px;border:0;border-radius:21px;padding:0;' +
    'display:flex;align-items:center;justify-content:center;color:#2a251f;background:rgba(246,241,228,.93);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);' +
    'box-shadow:0 1px 0 rgba(255,255,255,.6) inset,0 0 0 1px rgba(42,37,31,.07),0 8px 20px -12px rgba(0,0,0,.55);-webkit-tap-highlight-color:transparent;transition:opacity .4s}' +
    '.nunki-snd svg{width:22px;height:22px}.nunki-snd .w{opacity:0;transition:opacity .3s}.nunki-snd.on .w{opacity:1}.nunki-snd.on .x{opacity:0}.nunki-snd .x{transition:opacity .3s}' +
    '.nunki-tip{position:fixed;z-index:61;right:calc(clamp(10px,1.5vw,22px) + 50px);bottom:calc(max(12px,env(safe-area-inset-bottom)) + 6px);max-width:min(68vw,330px);padding:7px 12px;border-radius:15px;' +
    'font:400 .92rem/1.25 "Bradley Hand","Segoe Print","Chalkboard SE","Noteworthy","Avenir Next",Helvetica,sans-serif;color:#2a251f;background:rgba(246,241,228,.95);' +
    'box-shadow:0 0 0 1px rgba(42,37,31,.07),0 8px 20px -12px rgba(0,0,0,.55);opacity:0;transform:translateY(6px);transition:opacity .5s,transform .5s;pointer-events:none}' +
    '.nunki-tip.on{opacity:1;transform:none}' +
    '.nunki-hand{position:fixed;z-index:59;left:0;top:0;width:76px;height:76px;margin:-38px 0 0 -38px;border-radius:50%;pointer-events:none;opacity:0;transform:scale(.6);transition:opacity .25s,transform .25s;' +
    'box-shadow:0 0 0 2px rgba(255,248,228,.75),0 0 24px 6px rgba(255,226,160,.35),inset 0 0 18px rgba(255,236,190,.35)}' +
    '.nunki-hand.on{opacity:1;transform:scale(1)}' +
    '@media print{.nunki-snd,.nunki-tip,.nunki-hand{display:none}}';
  document.head.appendChild(css);

  // ---- 2. the little speaker ----
  var btn = null, tip = null;
  if (C.sound !== false) {
    btn = document.createElement('button');
    btn.className = 'nunki-snd';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'geluid aan of uit');
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M4 9.5h3.2L12 5.5v13l-4.8-4H4z" fill="currentColor" fill-opacity=".12"/>' +
      '<g class="w"><path d="M15.5 9.2a4 4 0 0 1 0 5.6"/><path d="M18 6.8a7.4 7.4 0 0 1 0 10.4"/></g>' +
      '<g class="x"><path d="M16 9.5l5 5M21 9.5l-5 5"/></g></svg>';
    document.body.appendChild(btn);
    tip = document.createElement('div'); tip.className = 'nunki-tip'; tip.setAttribute('aria-live', 'polite');
    document.body.appendChild(tip);
    var sync = function () { btn.classList.toggle('on', !N.muted && playing()); };
    setInterval(sync, 600);
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (N.muted) {
        N.muted = false;
        N.ctx.forEach(function (c) { c._nunkiResume(); });
      } else if (playing()) {
        N.muted = true;
        N.ctx.forEach(function (c) { try { c.suspend(); } catch (x) {} });
      } else {
        if (typeof window.audio === 'function') { try { window.audio(); } catch (x) {} }
        N.ctx.forEach(function (c) { c._nunkiResume(); });
        if (!N.ctx.length) say('tik op de wand, dan klinkt hij', 3500);
      }
      buzz(8);
      motionOn();
      setTimeout(sync, 80);
    });
  }
  var tipT = 0;
  function say(t, ms) {
    if (!tip) return;
    tip.textContent = t; tip.classList.add('on');
    clearTimeout(tipT); tipT = setTimeout(function () { tip.classList.remove('on'); }, ms || 4000);
  }
  // the first two visits: say once what the speaker and a still finger do
  var seen = +(store('nunki:touchtip') || 0);
  if (seen < 2 && btn) {
    store('nunki:touchtip', String(seen + 1));
    setTimeout(function () { if (!playing()) say('tik voor geluid', 3800); }, 2200);
    if (C.hand && C.hand !== 'off') setTimeout(function () { say('houd je vinger even stil en beweeg: dan voelt de wand je hand', 5200); }, 6800);
  }

  // ---- 3. a finger that is held still becomes the hand ----
  var mode = C.hand || 'off';
  if (mode !== 'off') {
    var ring = document.createElement('div'); ring.className = 'nunki-hand'; document.body.appendChild(ring);
    var st = null, timer = 0, last = null;
    var skip = function (el) { return el && el.closest && el.closest('a,button,nav,input,label,select,textarea,summary,.nunki-snd'); };
    var fire = function (type, x, y, buttons) {
      var el = document.elementFromPoint(x, y) || document.body, o = { bubbles: true, cancelable: true, view: window, clientX: x, clientY: y, screenX: x, screenY: y, button: type === 'pointermove' ? -1 : 0, buttons: buttons };
      try { el.dispatchEvent(new PointerEvent(type, Object.assign({ pointerType: 'mouse', pointerId: 1, isPrimary: true }, o))); } catch (e) {}
      var mt = type === 'pointermove' ? 'mousemove' : type === 'pointerdown' ? 'mousedown' : 'mouseup';
      try { el.dispatchEvent(new MouseEvent(mt, o)); } catch (e) {}
    };
    var start = function () {
      if (!st) return;
      st.on = true; N.hand = true;
      ring.style.left = st.x + 'px'; ring.style.top = st.y + 'px'; ring.classList.add('on');
      fire('pointermove', st.x, st.y, 0);
      if (mode === 'press') fire('pointerdown', st.x, st.y, 1);
      last = [st.x, st.y];
      buzz(8);
    };
    var end = function () {
      clearTimeout(timer);
      if (st && st.on) {
        if (mode === 'press' && last) fire('pointerup', last[0], last[1], 0);
        try { document.dispatchEvent(new MouseEvent('mouseout', { bubbles: true, relatedTarget: null })); } catch (e) {}
        ring.classList.remove('on'); N.hand = false;
      }
      st = null;
    };
    addEventListener('touchstart', function (e) {
      end();
      if (e.touches.length !== 1 || skip(e.target)) return;
      var t = e.touches[0];
      st = { x: t.clientX, y: t.clientY, on: false };
      timer = setTimeout(start, C.holdMs || 280);
    }, { passive: true });
    addEventListener('touchmove', function (e) {
      if (!st) return;
      var t = e.touches[0];
      if (!st.on) { if (e.touches.length > 1 || Math.hypot(t.clientX - st.x, t.clientY - st.y) > 10) end(); return; }
      if (e.cancelable) e.preventDefault();
      ring.style.left = t.clientX + 'px'; ring.style.top = t.clientY + 'px';
      last = [t.clientX, t.clientY];
      fire('pointermove', t.clientX, t.clientY, mode === 'press' ? 1 : 0);
    }, { passive: false });
    addEventListener('touchend', end, { passive: true });
    addEventListener('touchcancel', end, { passive: true });
    addEventListener('scroll', function () { if (st && !st.on) end(); }, { passive: true });
  }

  // ---- 4. tilt, shake, compass ----
  var asked = false;
  function motionOn() {
    if (asked || !C.motion) return;
    asked = true;
    var go = function () {
      addEventListener('deviceorientation', function (e) {
        if (e.beta == null) return;
        var a = (screen.orientation && screen.orientation.angle) || window.orientation || 0, g = e.gamma / 40, b = (e.beta - 40) / 40;
        var x = a === 90 ? b : a === -90 || a === 270 ? -b : a === 180 ? -g : g, y = a === 90 ? -g : a === -90 || a === 270 ? g : a === 180 ? -b : b;
        N.tilt.x = Math.max(-1, Math.min(1, x)); N.tilt.y = Math.max(-1, Math.min(1, y)); N.tilt.on = true;
        if (e.webkitCompassHeading != null) N.heading = e.webkitCompassHeading; else if (e.absolute && e.alpha != null) N.heading = (360 - e.alpha) % 360;
      });
      var prev = null, lastShake = 0;
      addEventListener('devicemotion', function (e) {
        var g = e.accelerationIncludingGravity; if (!g || g.x == null) return;
        if (prev) {
          var d = Math.abs(g.x - prev[0]) + Math.abs(g.y - prev[1]) + Math.abs(g.z - prev[2]), now = Date.now();
          if (d > 22 && now - lastShake > 700) { lastShake = now; dispatchEvent(new CustomEvent('nunki:shake', { detail: { power: Math.min(1, (d - 22) / 30 + .3) } })); }
        }
        prev = [g.x, g.y, g.z];
      });
    };
    try {
      var DM = window.DeviceMotionEvent, DO = window.DeviceOrientationEvent;
      if (DM && typeof DM.requestPermission === 'function') {
        var ps = [DM.requestPermission()];
        if (DO && typeof DO.requestPermission === 'function') ps.push(DO.requestPermission());
        Promise.all(ps).then(function (r) { if (r[0] === 'granted') go(); }).catch(function () {});
      } else if (DM || DO) go();
    } catch (e) {}
  }
  // shaking, where the wall has nothing of its own for it: a tap in the middle of the view
  if (C.shake === 'tap') addEventListener('nunki:shake', function () {
    if (document.hidden) return;
    var x = innerWidth * (.5 + (Math.random() - .5) * .3), y = innerHeight * (.5 + (Math.random() - .5) * .3);
    var el = document.elementFromPoint(x, y);
    if (!el || (el.closest && el.closest('a,button,nav'))) return;
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window, clientX: x, clientY: y }));
  });
  // every tap on the wall is a small tick you can feel
  var tap = null;
  addEventListener('touchstart', function (e) { var t = e.touches[0]; tap = e.touches.length === 1 ? { x: t.clientX, y: t.clientY, t: Date.now() } : null; }, { passive: true });
  addEventListener('touchend', function (e) {
    var t = e.changedTouches[0], d = tap; tap = null;
    if (!d || !t || Date.now() - d.t > 600 || Math.hypot(t.clientX - d.x, t.clientY - d.y) > 12) return;
    if (e.target && e.target.closest && e.target.closest('a,nav,input,select,textarea')) return;
    buzz(6);
  }, { passive: true });
  // the first real tap on the wall may ask for motion (it has to come from a finger)
  if (C.motion) addEventListener('touchend', function f(e) {
    if (e.target && e.target.closest && e.target.closest('a,nav,.nunki-snd')) return;
    removeEventListener('touchend', f);
    motionOn();
  }, { passive: true });
})();
