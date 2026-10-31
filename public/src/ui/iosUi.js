// ============================================================================
// AERYNDOR: LEGACY OF THE MONOLITHS – Dynamic Island & Moderne UI-Steuerung (iosUi.js)
// ============================================================================
//  - Dynamic Island (Kompass, Monster-/Rissmonolith-/Weltboss- & Spieler-Ziel)
//  - Dynamic Sidebar [L], Island-Toasts, Chat-Ruhemodus & Hell/Dunkel/Auto-Theme
// ============================================================================

const SB_STORAGE_KEY = 'aeryndor_dyn_sidebar_v1';
const CHAT_IDLE_MS = 9000;

const ICONS = {
  teleport:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2a10 10 0 0 1 10 10"/><path d="M12 22A10 10 0 0 1 2 12"/><path d="M5.6 5.6A9 9 0 0 1 12 3"/><path d="M18.4 18.4A9 9 0 0 1 12 21"/></svg>',
  map: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>',
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/></svg>',
  shop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l1.5-5h15L21 9"/><path d="M3 9h18v2a3 3 0 0 1-6 0 3 3 0 0 1-6 0 3 3 0 0 1-6 0z"/><path d="M5 13.5V21h14v-7.5"/><path d="M10 21v-4h4v4"/></svg>',
  potion:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2h6"/><path d="M10 2v5.5L5.2 16.2A3.5 3.5 0 0 0 8.3 21h7.4a3.5 3.5 0 0 0 3.1-4.8L14 7.5V2"/><path d="M7 14h10"/></svg>',
  hammer:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 6.5 18 3l3 3-3.5 3.5"/><path d="M13 8l3 3"/><path d="M11.5 9.5 3 18l3 3 8.5-8.5"/><path d="M12 5l4-2"/></svg>',
  rune: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 20 7v10l-8 5-8-5V7z"/><path d="M12 7v10"/><path d="M8.5 9.5 12 12l3.5-2.5"/></svg>',
  sword:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 17.5 3 6V3h3l11.5 11.5"/><path d="M13 19l6-6"/><path d="M16 16l4 4"/><path d="M19 21l2-2"/></svg>',
  paw: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="5.5" cy="10" r="2"/><circle cx="9.5" cy="5.5" r="2"/><circle cx="14.5" cy="5.5" r="2"/><circle cx="18.5" cy="10" r="2"/><path d="M8 17.5c0-2.5 1.8-5 4-5s4 2.5 4 5a2.6 2.6 0 0 1-2.6 2.5c-.6 0-1-.3-1.4-.3s-.8.3-1.4.3A2.6 2.6 0 0 1 8 17.5z"/></svg>',
  scroll:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 21h10a2 2 0 0 0 2-2V5"/><path d="M6 3h12a2 2 0 0 1 2 2"/><path d="M6 3a2 2 0 0 0-2 2v2h4V5a2 2 0 0 0-2-2z"/><path d="M8 5v14a2 2 0 0 1-4 0v-2"/><path d="M11 8h6M11 12h6M11 16h4"/></svg>',
  calendar:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4.5" width="18" height="16.5" rx="3"/><path d="M3 9.5h18M8 2.5v4M16 2.5v4"/><path d="m9.5 15 2 2 3.5-4"/></svg>',
  chat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 21l1.9-5.4A8 8 0 1 1 21 12z"/></svg>',
  gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.604.852.997 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  power:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/></svg>',
  pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 4h6l-1 6 3 3v2H7v-2l3-3z"/><path d="M12 15v6"/></svg>',
  chevron:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>',
};

function getSidebarGroups() {
  return [
    {
      title: 'Reisen',
      items: [
        { id: 'teleport', label: 'Teleport', sub: 'Schnellreise & Portale', icon: 'teleport', tint: '#0ea5e9', win: 'worldmap', act: 'teleport' },
        { id: 'worldmap', label: 'Weltkarte', sub: 'Regionen & Wegpunkte', key: 'M', icon: 'map', tint: '#16a34a', win: 'worldmap' },
        { id: 'town', label: 'Sanktuarium', sub: 'Zurück ins Dorf', icon: 'home', tint: '#d97706', act: 'town' },
      ],
    },
    {
      title: 'Handel',
      items: [
        { id: 'market', label: 'Offlineshop', sub: 'Spielermarkt & Suche', key: 'B', icon: 'shop', tint: '#ca8a04', win: 'market' },
        { id: 'generalstore', label: 'Händlerin', sub: 'Tränke & Auto-Verkauf', key: 'V', icon: 'potion', tint: '#dc2626', win: 'generalstore' },
      ],
    },
    {
      title: 'Handwerk',
      items: [
        { id: 'blacksmith', label: 'Schmied', sub: 'Verbessern +0 – +9', key: 'U', icon: 'hammer', tint: '#ea580c', win: 'blacksmith' },
        { id: 'runeweaver', label: 'Runenweberin', sub: 'Boni & Seelensteine', key: 'N', icon: 'rune', tint: '#9333ea', win: 'runeweaver' },
      ],
    },
    {
      title: 'Abenteuer',
      items: [
        { id: 'autofarm', label: 'Auto-Jagd', sub: 'Radar & Drop-Filter', key: 'O', icon: 'sword', tint: '#059669', win: 'autofarm', live: 'autofarm' },
        { id: 'pet', label: 'Begleiter', sub: 'Pets, Reittiere & Skins', key: 'P', icon: 'paw', tint: '#db2777', win: 'pet' },
        { id: 'quests', label: 'Quests', sub: 'Aufträge & Kapitel', key: 'J', icon: 'scroll', tint: '#b45309', win: 'quests' },
        { id: 'events', label: 'Events', sub: 'Welt-Events & Zeitplan', icon: 'calendar', tint: '#e11d48', win: 'events', live: 'event' },
      ],
    },
    {
      title: 'System & Sozial',
      items: [
        { id: 'friends', label: 'Messenger', sub: 'Freunde & Gespräche', key: 'H', icon: 'chat', tint: '#2563eb', win: 'friends' },
        { id: 'options', label: 'Optionen', sub: 'Grafik, Wetter & UI', icon: 'gear', tint: '#6366f1', win: 'options' },
        { id: 'gamemenu', label: 'Spielmenü', sub: 'Charakterwahl & Logout', key: 'ESC', icon: 'power', tint: '#f59e0b', win: 'gamemenu' },
      ],
    },
  ];
}

const isTyping = () => {
  const tag = document.activeElement?.tagName;
  return Boolean(tag && ['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) || document.activeElement?.isContentEditable;
};

const loadSbState = () => {
  try {
    const raw = JSON.parse(localStorage.getItem(SB_STORAGE_KEY) || '{}');
    return { open: Boolean(raw.open), pinned: Boolean(raw.pinned) };
  } catch (_) {
    return { open: false, pinned: false };
  }
};

const saveSbState = (st) => {
  try {
    localStorage.setItem(SB_STORAGE_KEY, JSON.stringify({ open: st.open, pinned: st.pinned }));
  } catch (_) {}
};

// ============================================================================
// 1. DYNAMIC ISLAND MORPH & INTERAKTIVE ERWEITERUNGEN
// ============================================================================
let _morphBg = null;
let _morphState = null;

function ensureMorphBg() {
  if (_morphBg && document.body.contains(_morphBg)) return _morphBg;
  _morphBg = document.createElement('div');
  _morphBg.id = 'di-morph-bg';
  _morphBg.className = 'di-morph-bg';
  _morphBg.setAttribute('aria-hidden', 'true');
  _morphBg.style.willChange = 'left, top, width, height, border-radius, transform, box-shadow';
  document.body.appendChild(_morphBg);
  return _morphBg;
}

/** Liest Form, Rahmenfarbe & Schatten einer Insel-Kapsel für den Morph aus. */
export function captureIslandStyle(el) {
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  let radius = rect.height / 2;
  let borderColor = 'rgba(212, 168, 72, 0.65)';
  let boxShadow = '0 10px 28px rgba(0, 0, 0, 0.55)';
  try {
    const cs = window.getComputedStyle(el);
    const r = parseFloat(cs.borderTopLeftRadius);
    if (Number.isFinite(r)) radius = Math.min(r, rect.height / 2);
    if (cs.borderTopColor && cs.borderTopColor !== 'rgba(0, 0, 0, 0)') borderColor = cs.borderTopColor;
    if (cs.boxShadow && cs.boxShadow !== 'none') boxShadow = cs.boxShadow;
  } catch (_) {}
  return { rect, radius, borderColor, boxShadow };
}

function cancelActiveMorph() {
  if (!_morphState) return;
  try {
    _morphState.anim?.cancel();
  } catch (_) {}
  _morphState.dstEl?.classList.remove('di-morph-dst');
  if (_morphBg) _morphBg.style.display = 'none';
  _morphState = null;
}

/**
 * 5-Stufen iOS Dynamic Island Spring-Morph:
 * Interpoliert Position, Breite, Höhe, Radius, Rahmenfarbe & Glow butterweich
 * mit natürlichem Elastizitäts-Overshoot.
 */
export function morphIsland({ from, toEl, contentEls = [], duration = 420 }) {
  if (!from || !toEl || typeof toEl.animate !== 'function') return false;
  const to = captureIslandStyle(toEl);
  if (!to || to.rect.width < 4 || from.rect.width < 4) return false;

  cancelActiveMorph();
  const bg = ensureMorphBg();
  const fr = from.rect;
  const tr = to.rect;

  const isShrinking = tr.width < fr.width;
  const over = (a, b, f) => b + (b - a) * f;
  const fcx = fr.left + fr.width / 2;
  const tcx = tr.left + tr.width / 2;

  const overFactor = isShrinking ? 0.095 : 0.065;
  const ow = Math.max(12, over(fr.width, tr.width, overFactor));
  const oh = Math.max(12, over(fr.height, tr.height, overFactor));
  const ocx = over(fcx, tcx, overFactor);
  const otop = over(fr.top, tr.top, overFactor);

  const settleW = isShrinking ? tr.width * 1.028 : tr.width * 0.99;
  const settleH = isShrinking ? tr.height * 1.045 : tr.height * 0.99;

  const frame = (cx, top, w, h, radius, color, shadow) => ({
    left: `${(cx - w / 2).toFixed(2)}px`,
    top: `${top.toFixed(2)}px`,
    width: `${w.toFixed(2)}px`,
    height: `${h.toFixed(2)}px`,
    borderRadius: `${Math.max(6, radius).toFixed(1)}px`,
    borderColor: color,
    boxShadow: shadow || to.boxShadow,
  });

  bg.style.display = 'block';
  toEl.classList.add('di-morph-dst');

  let anim = null;
  try {
    anim = bg.animate(
      [
        { ...frame(fcx, fr.top, fr.width, fr.height, from.radius, from.borderColor, from.boxShadow), offset: 0 },
        {
          ...frame(
            (fcx + ocx) * 0.5,
            (fr.top + otop) * 0.5,
            (fr.width + ow) * 0.5,
            (fr.height + oh) * 0.5,
            Math.min(oh / 2, (from.radius + to.radius) * 0.5),
            to.borderColor,
            '0 14px 36px rgba(0, 0, 0, 0.65), 0 0 18px rgba(250, 204, 21, 0.22)'
          ),
          offset: 0.28,
        },
        { ...frame(ocx, otop, ow, oh, Math.min(oh / 2, to.radius), to.borderColor, to.boxShadow), offset: 0.60 },
        {
          ...frame(
            tcx,
            tr.top - (settleH - tr.height) * 0.5,
            settleW,
            settleH,
            Math.min(settleH / 2, to.radius),
            to.borderColor,
            to.boxShadow
          ),
          offset: 0.84,
        },
        { ...frame(tcx, tr.top, tr.width, tr.height, to.radius, to.borderColor, to.boxShadow), offset: 1 },
      ],
      { duration, easing: 'cubic-bezier(0.22, 1, 0.36, 1)', fill: 'both' }
    );
  } catch (_) {
    bg.style.display = 'none';
    toEl.classList.remove('di-morph-dst');
    return false;
  }

  // Sanfter elastischer Impuls auf der Ziel-Kapsel
  try {
    toEl.animate(
      isShrinking
        ? [
            { transform: 'scale3d(0.90, 0.84, 1)' },
            { transform: 'scale3d(1.032, 1.055, 1)', offset: 0.66 },
            { transform: 'scale3d(0.994, 0.992, 1)', offset: 0.86 },
            { transform: 'scale3d(1, 1, 1)' },
          ]
        : [
            { transform: 'scale3d(0.94, 0.90, 1)' },
            { transform: 'scale3d(1.018, 1.026, 1)', offset: 0.68 },
            { transform: 'scale3d(1, 1, 1)' },
          ],
      {
        duration: Math.round(duration * 0.92),
        delay: Math.round(duration * 0.14),
        easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
      }
    );
  } catch (_) {}

  const state = { anim, dstEl: toEl };
  _morphState = state;

  const finish = () => {
    if (_morphState !== state) return;
    toEl.classList.remove('di-morph-dst');
    bg.style.display = 'none';
    try {
      anim.cancel();
    } catch (_) {}
    _morphState = null;
  };
  anim.onfinish = finish;
  anim.oncancel = finish;

  contentEls.filter(Boolean).forEach((el, idx) => {
    if (typeof el.animate !== 'function') return;
    try {
      el.animate(
        [
          { opacity: 0, filter: 'blur(4px)', transform: 'translate3d(0, 2px, 0) scale3d(0.95, 0.95, 1)' },
          { opacity: 1, filter: 'blur(0px)', transform: 'translate3d(0, 0, 0) scale3d(1, 1, 1)' },
        ],
        {
          duration: 240,
          delay: Math.round(duration * 0.24) + idx * 22,
          easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
          fill: 'backwards',
        }
      );
    } catch (_) {}
  });
  return true;
}

/** Inhalt der Quell-Insel schnell & weich ausblenden. */
export function fadeOutIslandContent(contentEls = [], duration = 120) {
  let last = null;
  contentEls.filter(Boolean).forEach((el) => {
    if (typeof el.animate !== 'function') return;
    try {
      last = el.animate(
        [
          { opacity: 1, filter: 'blur(0px)', transform: 'scale3d(1, 1, 1)' },
          { opacity: 0, filter: 'blur(3.5px)', transform: 'scale3d(0.93, 0.93, 1)' },
        ],
        { duration, easing: 'cubic-bezier(0.4, 0, 1, 1)', fill: 'forwards' }
      );
    } catch (_) {}
  });
  return last;
}

/** Elastisches Aufploppen einer Insel ohne Vorgänger. */
export function popIsland(el) {
  if (!el || typeof el.animate !== 'function') return;
  try {
    el.animate(
      [
        { transform: 'scale3d(0.48, 0.72, 1)', opacity: 0, filter: 'blur(4px)' },
        { transform: 'scale3d(1.032, 1.055, 1)', opacity: 1, filter: 'blur(0px)', offset: 0.62 },
        { transform: 'scale3d(0.995, 0.992, 1)', offset: 0.84 },
        { transform: 'scale3d(1, 1, 1)', opacity: 1 },
      ],
      { duration: 420, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' }
    );
  } catch (_) {}
}

/**
 * Macht die Dynamic Island interaktiver:
 * - Sanfte elastische Hover-Reaktion (Micro-Breathing)
 * - Doppelklick auf den Kompass-Streifen öffnet die Weltkarte [M]
 * - Rechtsklick auf die Kompass-Insel öffnet das ESC-Spielmenü
 */
export function initDynamicIslandInteractions(app) {
  const compassEl = document.getElementById('hud-compass');
  const targetEl = document.getElementById('hud-target-frame');

  const attachHoverSpring = (shellSelector) => {
    const shell = document.querySelector(shellSelector);
    if (!shell || shell._diHoverBound) return;
    shell._diHoverBound = true;
    shell.style.willChange = 'transform, box-shadow';

    shell.addEventListener('pointerenter', () => {
      if (app.isReducedMotion?.() || _morphState) return;
      try {
        shell._hoverAnim?.cancel();
        shell._hoverAnim = shell.animate(
          [
            { transform: 'scale3d(1, 1, 1)' },
            { transform: 'scale3d(1.022, 1.035, 1)', offset: 0.65 },
            { transform: 'scale3d(1.014, 1.02, 1)' },
          ],
          { duration: 240, easing: 'cubic-bezier(0.22, 1, 0.36, 1)', fill: 'forwards' }
        );
      } catch (_) {}
    });

    shell.addEventListener('pointerleave', () => {
      if (!shell._hoverAnim) return;
      try {
        shell._hoverAnim.cancel();
        shell._hoverAnim = null;
        shell.animate(
          [{ transform: 'scale3d(1.014, 1.02, 1)' }, { transform: 'scale3d(1, 1, 1)' }],
          { duration: 200, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' }
        );
      } catch (_) {}
    });
  };

  attachHoverSpring('#hud-compass .nw-compass-strip-wrap');
  attachHoverSpring('#hud-target-frame .nw-target-shell');

  if (compassEl && !compassEl._diExtraBound) {
    compassEl._diExtraBound = true;
    compassEl.querySelector('.nw-compass-strip-wrap')?.addEventListener('dblclick', (ev) => {
      ev.stopPropagation();
      app.toggleWindow?.('worldmap');
    });
    compassEl.addEventListener('contextmenu', (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      app.toggleWindow?.('gamemenu');
    });
  }

  if (targetEl && !targetEl._diExtraBound) {
    targetEl._diExtraBound = true;
    targetEl.querySelector('#target-name-label')?.addEventListener('dblclick', (ev) => {
      ev.stopPropagation();
      document.getElementById('btn-target-focus')?.click();
    });
  }
}

// ============================================================================
// 2. DYNAMIC SIDEBAR (LINKS) + GLOBALE ESC-BUTTON ABSICHERUNG
// ============================================================================
function buildSidebarHtml() {
  const groups = getSidebarGroups();
  return `
    <button type="button" class="dyn-sb-handle" id="dyn-sb-handle" aria-expanded="false" title="Schnellzugriff ein-/ausfahren [L]">
      <span class="dyn-sb-handle-grip" aria-hidden="true"></span>
      <span class="dyn-sb-handle-chev" aria-hidden="true">${ICONS.chevron}</span>
      <span class="dyn-sb-handle-dot" aria-hidden="true"></span>
    </button>
    <div class="dyn-sb-panel" id="dyn-sb-panel" role="menu">
      <div class="dyn-sb-head">
        <div class="dyn-sb-head-txt">
          <span class="dyn-sb-title">Schnellzugriff</span>
          <span class="dyn-sb-sub">Taste [L]</span>
        </div>
        <button type="button" class="dyn-sb-pin" id="dyn-sb-pin" title="Leiste anheften (bleibt nach Auswahl offen)">${ICONS.pin}</button>
      </div>
      <div class="dyn-sb-scroll">
        ${groups
          .map(
            (g) => `
          <div class="dyn-sb-group">
            <div class="dyn-sb-group-title">${g.title}</div>
            <div class="dyn-sb-group-list">
              ${g.items
                .map(
                  (it) => `
                <button type="button" class="dyn-sb-item" role="menuitem" data-sb-id="${it.id}" style="--sb-tint:${it.tint};" title="${it.label}${it.key ? ` [${it.key}]` : ''}">
                  <span class="dyn-sb-ico">${ICONS[it.icon] || ''}${it.live ? '<span class="dyn-sb-live" aria-hidden="true"></span>' : ''}</span>
                  <span class="dyn-sb-txt">
                    <span class="dyn-sb-lbl">${it.label}</span>
                    <span class="dyn-sb-desc">${it.sub || ''}</span>
                  </span>
                  ${it.key ? `<kbd class="dyn-sb-key">${it.key}</kbd>` : `<span class="dyn-sb-chev">${ICONS.chevron}</span>`}
                </button>`
                )
                .join('')}
            </div>
          </div>`
          )
          .join('')}
      </div>
    </div>
  `;
}

function isWindowOpen(app, item) {
  if (!item.win) return false;
  if (item.win === 'quests') {
    const el = document.getElementById('win-character');
    return Boolean(el && !el.classList.contains('hidden') && !el.classList.contains('ui-win-closing') && app.charWindowTab === 'quests');
  }
  const el = document.getElementById(`win-${item.win}`);
  if (!el || el.classList.contains('hidden') || el.classList.contains('ui-win-closing')) return false;
  if (item.act === 'teleport') return app.worldMapSidebarTab === 'teleport';
  if (item.id === 'worldmap') return app.worldMapSidebarTab !== 'teleport';
  return true;
}

export function initDynamicSidebar(app) {
  let root = document.getElementById('hud-dyn-sidebar');
  if (!root) {
    root = document.createElement('nav');
    root.id = 'hud-dyn-sidebar';
    document.body.appendChild(root);
  }
  root.className = 'dyn-sidebar';
  root.setAttribute('aria-label', 'Schnellzugriff');
  root.innerHTML = buildSidebarHtml();

  const items = new Map();
  getSidebarGroups().forEach((g) => g.items.forEach((it) => items.set(it.id, it)));

  const state = loadSbState();
  const handle = root.querySelector('#dyn-sb-handle');
  const pinBtn = root.querySelector('#dyn-sb-pin');
  const reduced = () => Boolean(app.isReducedMotion?.());

  const staggerItems = () => {
    if (reduced()) return;
    root.querySelectorAll('.dyn-sb-group-title, .dyn-sb-item').forEach((el, idx) => {
      if (typeof el.animate !== 'function') return;
      try {
        el.animate(
          [
            { opacity: 0, transform: 'translate3d(-12px, 0, 0) scale3d(0.96, 0.96, 1)' },
            { opacity: 1, transform: 'translate3d(0, 0, 0) scale3d(1, 1, 1)' },
          ],
          { duration: 260, delay: 30 + idx * 14, easing: 'cubic-bezier(0.22, 1, 0.36, 1)', fill: 'backwards' }
        );
      } catch (_) {}
    });
  };

  const apply = (animate = true) => {
    root.classList.toggle('is-open', state.open);
    root.classList.toggle('is-pinned', state.pinned);
    handle.setAttribute('aria-expanded', state.open ? 'true' : 'false');
    pinBtn.classList.toggle('active', state.pinned);
    pinBtn.title = state.pinned ? 'Angeheftet – klicken zum Lösen' : 'Leiste anheften (bleibt nach Auswahl offen)';
    if (state.open && animate) staggerItems();
    saveSbState(state);
  };

  const setOpen = (open, animate = true) => {
    if (state.open === open) return;
    state.open = open;
    apply(animate);
    if (open) sync();
  };

  app.toggleDynamicSidebar = (force) => setOpen(typeof force === 'boolean' ? force : !state.open);

  handle.addEventListener('click', (ev) => {
    ev.stopPropagation();
    setOpen(!state.open);
  });

  pinBtn.addEventListener('click', (ev) => {
    ev.stopPropagation();
    state.pinned = !state.pinned;
    apply(false);
    app.animateGoldenPulse?.(pinBtn);
  });

  const origGetOrigin = app.getWindowOriginButton?.bind(app);
  if (origGetOrigin) {
    app.getWindowOriginButton = (winKey) => {
      const o = app._sbOrigin;
      if (o && o.win === winKey && Date.now() - o.ts < 900 && o.el?.isConnected) {
        const r = o.el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) return o.el;
      }
      return origGetOrigin(winKey);
    };
  }

  const runItem = (it, btn) => {
    app._sbOrigin = { win: it.win, el: btn, ts: Date.now() };
    if (it.act === 'teleport') {
      const wmEl = document.getElementById('win-worldmap');
      const wmOpen = wmEl && !wmEl.classList.contains('hidden') && !wmEl.classList.contains('ui-win-closing');
      app.worldMapSidebarTab = 'teleport';
      if (wmOpen) {
        app.renderWorldMapWindow?.();
        app.updateHudActiveWindowButtons?.();
      } else {
        app.openWindow('worldmap');
      }
      app.showToast?.('🌀 Teleport – wähle dein Reiseziel');
    } else if (it.act === 'town') {
      const curMap = app.selfState?.map_id || 'morgenwacht';
      app.sendAction?.('change_map', { mapId: curMap, spawnX: 0, spawnZ: 148 });
      app.showToast?.('🏛️ Rückkehr ins Dorf-Sanktuarium …');
    } else if (it.id === 'worldmap') {
      const wmEl = document.getElementById('win-worldmap');
      const wmOpen = wmEl && !wmEl.classList.contains('hidden') && !wmEl.classList.contains('ui-win-closing');
      if (wmOpen && app.worldMapSidebarTab === 'teleport') {
        app.worldMapSidebarTab = 'weltkarte';
        app.renderWorldMapWindow?.();
        app.updateHudActiveWindowButtons?.();
      } else {
        if (!wmOpen) app.worldMapSidebarTab = 'weltkarte';
        app.toggleWindow('worldmap');
      }
    } else if (it.win) {
      app.toggleWindow(it.win);
    }
    sync();
    if (!state.pinned) setTimeout(() => setOpen(false), 140);
  };

  root.querySelectorAll('[data-sb-id]').forEach((btn) => {
    btn.addEventListener('click', (ev) => {
      ev.stopPropagation();
      const it = items.get(btn.getAttribute('data-sb-id'));
      if (!it) return;
      if (!reduced() && typeof btn.animate === 'function') {
        try {
          btn.animate(
            [{ transform: 'scale3d(1,1,1)' }, { transform: 'scale3d(0.95,0.95,1)', offset: 0.4 }, { transform: 'scale3d(1,1,1)' }],
            { duration: 210, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' }
          );
        } catch (_) {}
      }
      runItem(it, btn);
    });
  });

  document.addEventListener(
    'pointerdown',
    (ev) => {
      if (!state.open || state.pinned) return;
      if (root.contains(ev.target)) return;
      if (ev.target.closest?.('.ornate-window, #modal-overlay, #item-tooltip')) return;
      setOpen(false);
    },
    true
  );

  window.addEventListener('keydown', (ev) => {
    if (!app.inWorld || ev.repeat || ev.ctrlKey || ev.altKey || ev.metaKey) return;
    if (isTyping()) return;
    if (ev.key === 'l' || ev.key === 'L') {
      ev.preventDefault();
      setOpen(!state.open);
    } else if (ev.key === 'Escape' && state.open && !state.pinned) {
      setOpen(false);
    }
  });

  let edgeStartX = null;
  window.addEventListener('pointerdown', (ev) => {
    if (app.inWorld && !state.open && ev.clientX <= 16) {
      edgeStartX = ev.clientX;
    } else {
      edgeStartX = null;
    }
  });
  window.addEventListener('pointermove', (ev) => {
    if (edgeStartX !== null && ev.clientX - edgeStartX > 28) {
      edgeStartX = null;
      setOpen(true);
    }
  });
  window.addEventListener('pointerup', () => {
    edgeStartX = null;
  });

  const getItemBadgeCount = (it) => {
    const s = app.selfState;
    if (!s) return 0;
    if (it.id === 'character') return Number(s.stat_points || 0);
    if (it.id === 'skills') return Number(s.skill_points || 0);
    if (it.id === 'quests') {
      const qList = Array.isArray(s.quests)
        ? s.quests
        : typeof app.getEnrichedQuests === 'function'
        ? app.getEnrichedQuests()
        : Object.values(s.quests || {});
      return (Array.isArray(qList) ? qList : []).filter(
        (q) => q && (q.status === 'ready' || q.readyToTurnIn || (q.progress >= q.required && q.required > 0 && !q.completed))
      ).length;
    }
    if (it.id === 'pet') return Number(s.petData?.skillPoints || 0);
    return 0;
  };

  const sync = () => {
    try {
      root.querySelectorAll('[data-sb-id]').forEach((btn) => {
        const it = items.get(btn.getAttribute('data-sb-id'));
        if (!it) return;
        btn.classList.toggle('is-open', isWindowOpen(app, it));
        if (it.live === 'autofarm') {
          const on = Boolean(app.selfState?.autoFarmActive || app.selfState?.autofarm?.enabled || app.engine?.autoHuntActive);
          btn.classList.toggle('is-live', on);
        } else if (it.live === 'event') {
          const ev = app.snapshot?.worldEvent;
          btn.classList.toggle('is-live', Boolean(ev && ev.active !== false));
        }
        const badgeCount = getItemBadgeCount(it);
        let badgeEl = btn.querySelector('.dyn-sb-badge');
        if (badgeCount > 0) {
          if (!badgeEl) {
            badgeEl = document.createElement('span');
            badgeEl.className = 'dyn-sb-badge';
            badgeEl.style.cssText =
              'margin-left:auto;margin-right:4px;padding:1px 6px;border-radius:999px;background:rgba(239,68,68,0.9);color:#fff;font-size:10px;font-weight:800;line-height:1.3;';
            btn.appendChild(badgeEl);
          }
          badgeEl.textContent = String(badgeCount);
        } else if (badgeEl) {
          badgeEl.remove();
        }
      });
      const anyLive = Boolean(root.querySelector('.dyn-sb-item.is-live'));
      root.classList.toggle('has-live', anyLive);
    } catch (_) {}
  };
  app.syncDynamicSidebar = sync;

  const origUpdateBtns = app.updateHudActiveWindowButtons?.bind(app);
  if (origUpdateBtns) {
    app.updateHudActiveWindowButtons = (...args) => {
      try {
        origUpdateBtns(...args);
      } finally {
        sync();
      }
    };
  }
  setInterval(() => {
    if (app.inWorld) sync();
  }, 3000);

  apply(false);
  sync();
}

// ============================================================================
// 3. CHAT-RUHEMODUS (unten links)
// ============================================================================
export function initChatIdleFade(app) {
  const box = document.getElementById('hud-chat-box');
  if (!box) return;
  let timer = null;
  let hover = false;

  const smileyOpen = () => {
    const p = document.getElementById('chat-smiley-popup');
    return Boolean(p && !p.classList.contains('hidden'));
  };
  const isEngaged = () => hover || box.contains(document.activeElement) || smileyOpen();

  const schedule = (ms = CHAT_IDLE_MS) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (isEngaged()) {
        schedule();
        return;
      }
      box.classList.toggle('chat-idle-noshrink', Boolean(box.style.top && box.style.top !== 'auto'));
      box.classList.add('chat-idle');
    }, ms);
  };

  const wake = (ms) => {
    box.classList.remove('chat-idle');
    schedule(ms);
  };
  app.wakeChatBox = wake;

  box.addEventListener('pointerenter', () => {
    hover = true;
    wake();
  });
  box.addEventListener('pointerleave', () => {
    hover = false;
    schedule();
  });
  box.addEventListener('focusin', () => wake());
  box.addEventListener('focusout', () => schedule());

  const origUpdateChat = app.updateChatBox?.bind(app);
  if (origUpdateChat) {
    app.updateChatBox = (list, force = false) => {
      origUpdateChat(list, force);
      const l = app.latestChatList || [];
      const last = l[l.length - 1];
      if (!last) return;
      if (app._chatIdleLastId === undefined) {
        app._chatIdleLastId = last.id;
        return;
      }
      if (last.id !== app._chatIdleLastId) {
        app._chatIdleLastId = last.id;
        const ch = last.channel || 'normal';
        if (ch !== 'drops' && (!app.doesChatMessageMatchFilter || app.doesChatMessageMatchFilter(last, app.chatFilter)) && box.classList.contains('chat-idle')) {
          box.classList.add('chat-peek');
          wake(5200);
          setTimeout(() => box.classList.remove('chat-peek'), 700);
        }
      }
    };
  }

  ['openChatBox', 'minimizeChatBox'].forEach((fn) => {
    const orig = app[fn]?.bind(app);
    if (!orig) return;
    app[fn] = (...args) => {
      const r = orig(...args);
      wake();
      return r;
    };
  });

  schedule();
}

// ============================================================================
// 4. ISLAND-TOASTS
// ============================================================================
export function initIslandToasts(app) {
  const el = document.getElementById('toast-banner');
  if (!el) return;
  el.classList.add('di-toast');

  const islandSrcEl = () => {
    const frame = document.getElementById('hud-target-frame');
    const compass = document.getElementById('hud-compass');
    return (
      (frame && !frame.classList.contains('hidden') && !frame.classList.contains('ui-target-closing') && frame.querySelector('.nw-target-shell')) ||
      (compass && !compass.classList.contains('hidden') && !compass.classList.contains('ui-compass-closing') && compass.querySelector('.nw-compass-strip-wrap')) ||
      null
    );
  };

  const pulseIsland = (open, delay = 0) => {
    const isl = islandSrcEl();
    if (!isl || typeof isl.animate !== 'function') return;
    if (isl._diPulse) {
      try {
        isl._diPulse.cancel();
      } catch (_) {}
    }
    const kf = open
      ? [
          { transform: 'scale3d(1, 1, 1)' },
          { offset: 0.35, transform: 'scale3d(1.04, 1.10, 1)' },
          { offset: 0.72, transform: 'scale3d(0.992, 0.968, 1)' },
          { transform: 'scale3d(1, 1, 1)' },
        ]
      : [
          { transform: 'scale3d(1, 1, 1)' },
          { offset: 0.45, transform: 'scale3d(1.05, 1.13, 1)' },
          { offset: 0.78, transform: 'scale3d(0.988, 0.96, 1)' },
          { transform: 'scale3d(1, 1, 1)' },
        ];
    try {
      isl._diPulse = isl.animate(kf, {
        duration: open ? 480 : 420,
        delay,
        easing: 'cubic-bezier(0.34, 1.3, 0.64, 1)',
        composite: 'add',
      });
    } catch (_) {
      isl._diPulse = isl.animate(kf, { duration: open ? 480 : 420, delay, easing: 'ease-out' });
    }
  };

  const islandOffset = (target) => {
    const src = islandSrcEl();
    const tr = target.getBoundingClientRect();
    if (!src) return { dy: -40, sx: 0.2 };
    const ir = src.getBoundingClientRect();
    const islandMidY = ir.top + ir.height / 2;
    const dy = islandMidY - (tr.top + tr.height / 2);
    const sx = Math.max(0.12, Math.min(0.6, (ir.width * 0.35) / Math.max(1, tr.width)));
    return { dy, sx };
  };

  app.islandPop = (target, open, done) => {
    if (!target) return done?.();
    if (target._diAnim) {
      try {
        target._diAnim.cancel();
      } catch (_) {}
      target._diAnim = null;
    }
    if (app.isReducedMotion?.() || typeof target.animate !== 'function') return done?.();
    const { dy, sx } = islandOffset(target);
    const hidden = {
      transform: `translate3d(-50%, ${dy.toFixed(1)}px, 0) scale3d(${sx.toFixed(3)}, 0.35, 1)`,
      opacity: 0,
      filter: 'blur(3px)',
    };
    const shown = { transform: 'translate3d(-50%, 0, 0) scale3d(1, 1, 1)', opacity: 1, filter: 'blur(0px)' };
    const kf = open
      ? [
          hidden,
          { offset: 0.56, transform: 'translate3d(-50%, 2.5px, 0) scale3d(1.032, 1.05, 1)', opacity: 1, filter: 'blur(0px)' },
          { offset: 0.82, transform: 'translate3d(-50%, -0.8px, 0) scale3d(0.994, 0.988, 1)', opacity: 1, filter: 'blur(0px)' },
          shown,
        ]
      : [
          shown,
          { offset: 0.24, transform: 'translate3d(-50%, 2px, 0) scale3d(1.018, 1.018, 1)', opacity: 1, filter: 'blur(0px)' },
          hidden,
        ];
    const anim = target.animate(kf, {
      duration: open ? 520 : 340,
      easing: open ? 'cubic-bezier(0.22, 1, 0.36, 1)' : 'cubic-bezier(0.55, 0, 0.75, 0.3)',
      fill: 'forwards',
    });
    pulseIsland(open, open ? 0 : 220);
    target._diAnim = anim;
    anim.onfinish = () => {
      done?.();
      if (target._diAnim === anim) {
        anim.cancel();
        target._diAnim = null;
      }
    };
  };

  const drainToastQueue = () => {
    if (!app._toastQueue || app._toastQueue.length === 0) return;
    const banner = document.getElementById('quest-event-banner');
    if (banner && !banner.classList.contains('hidden')) {
      if (!app._toastQueueTimer) {
        app._toastQueueTimer = setTimeout(() => {
          app._toastQueueTimer = null;
          drainToastQueue();
        }, 280);
      }
      return;
    }
    if (el.classList.contains('visible')) return;
    const nextMsg = app._toastQueue.shift();
    if (nextMsg) app.showToast(nextMsg);
  };

  const hideToast = () => {
    if (!el.classList.contains('visible')) return;
    app.islandPop(el, false, () => {
      el.classList.remove('visible');
      setTimeout(drainToastQueue, 110);
    });
  };
  app.hideIslandToast = hideToast;

  app.showToast = (text) => {
    const msg = String(text ?? '');
    if (!msg) return;
    const banner = document.getElementById('quest-event-banner');
    const bannerVisible = Boolean(banner && !banner.classList.contains('hidden'));
    if (bannerVisible) {
      if (!app._toastQueue) app._toastQueue = [];
      if (app._toastQueue[app._toastQueue.length - 1] !== msg) app._toastQueue.push(msg);
      if (app._toastQueue.length > 5) app._toastQueue.shift();
      drainToastQueue();
      return;
    }
    app.positionIslandNotices?.();
    const wasVisible = el.classList.contains('visible');
    el.textContent = msg;
    el.classList.add('visible');
    if (!wasVisible || el._diAnim) app.islandPop(el, true);
    clearTimeout(app.toastTimer);
    const dur = Math.min(5000, Math.max(2300, msg.length * 52));
    app.toastTimer = setTimeout(hideToast, dur);
  };
}

// ============================================================================
// 5. LIGHT- & DARK-MODE
// ============================================================================
const THEME_KEY = 'aeryndor_ui_theme';
const THEME_ORDER = ['light', 'dark', 'auto'];
let _themeTimer = null;
let _effectiveTheme = null;

export function getUiThemePref() {
  try {
    const v = localStorage.getItem(THEME_KEY);
    if (THEME_ORDER.includes(v)) return v;
    const hudRaw = JSON.parse(localStorage.getItem('aeryndor_hud_vis_v422') || 'null');
    if (hudRaw && THEME_ORDER.includes(hudRaw.uiTheme)) {
      localStorage.setItem(THEME_KEY, hudRaw.uiTheme);
      return hudRaw.uiTheme;
    }
    return 'dark';
  } catch (_) {
    return 'dark';
  }
}

function resolveTheme(app, pref) {
  if (pref !== 'auto') return pref;
  let hour = null;
  try {
    hour = Number(app?.engine?.getEnvironmentSnapshot?.()?.hourOfDay);
  } catch (_) {}
  if (!Number.isFinite(hour)) hour = new Date().getHours() + new Date().getMinutes() / 60;
  return hour >= 6.5 && hour < 19.5 ? 'light' : 'dark';
}

function syncThemeControls(pref) {
  document.querySelectorAll('[data-ui-theme]:not(body):not(html)').forEach((el) => {
    const on = el.getAttribute('data-ui-theme') === pref;
    el.classList.toggle('active', on);
    el.setAttribute('aria-checked', on ? 'true' : 'false');
  });
  document.querySelectorAll('.ui-theme-seg').forEach((seg) => {
    seg.style.setProperty('--seg-idx', String(Math.max(0, THEME_ORDER.indexOf(pref))));
  });
  document.querySelectorAll('[data-ui-theme-effective]').forEach((el) => {
    const effTxt = _effectiveTheme === 'light' ? 'Hell' : 'Dunkel';
    el.textContent = pref === 'auto' ? `Aktuell: Auto • ${effTxt}` : `Aktuell: ${effTxt}`;
  });
}

export function applyUiTheme(app = null, animate = false) {
  const body = document.body;
  if (!body) return;
  const pref = getUiThemePref();
  const eff = resolveTheme(app, pref);
  const changed = eff !== _effectiveTheme;
  _effectiveTheme = eff;
  if (changed) {
    if (animate && !app?.isReducedMotion?.()) {
      body.classList.add('ui-theme-switching');
      clearTimeout(body._themeSwitchTimer);
      body._themeSwitchTimer = setTimeout(() => body.classList.remove('ui-theme-switching'), 520);
    }
    body.classList.toggle('ui-theme-light', eff === 'light');
    body.classList.toggle('ui-theme-dark', eff === 'dark');
    body.setAttribute('data-ui-theme', eff);
  }
  body.setAttribute('data-ui-theme-pref', pref);
  if (app?.clientSettings) app.clientSettings.uiTheme = pref;
  syncThemeControls(pref);

  clearTimeout(_themeTimer);
  if (pref === 'auto') {
    _themeTimer = setTimeout(() => applyUiTheme(app, true), 15000);
  }
}

export function setUiTheme(app, pref) {
  if (!THEME_ORDER.includes(pref)) return;
  try {
    localStorage.setItem(THEME_KEY, pref);
  } catch (_) {}
  if (app?.clientSettings) {
    app.clientSettings.uiTheme = pref;
  }
  applyUiTheme(app, true);
  try {
    app?.updateHudElementsVisibility?.();
    app?.savePlatformGraphicsProfile?.();
  } catch (_) {}
  const names = {
    light: '☀️ Light Mode – klares Glas',
    dark: '🌙 Dark Mode – dunkles Glas',
    auto: '◐ Automatisch – folgt der Tageszeit',
  };
  app?.showToast?.(names[pref]);
}

export function initUiTheme(app) {
  app.getUiThemePref = getUiThemePref;
  app.setUiTheme = (pref) => setUiTheme(app, pref);
  app.applyUiTheme = (animate = false) => applyUiTheme(app, animate);
  document.addEventListener(
    'click',
    (ev) => {
      const btn = ev.target?.closest?.('[data-ui-theme]:not(body):not(html)');
      if (!btn) return;
      ev.preventDefault();
      const pref = btn.getAttribute('data-ui-theme');
      if (pref === getUiThemePref()) return;
      setUiTheme(app, pref);
    },
    true
  );
  applyUiTheme(app, false);
}

try {
  applyUiTheme(null, false);
} catch (_) {}

// ============================================================================
// 6. HELFER & ESC-MENÜ-GARANTIE
// ============================================================================
export function shakeElement(el) {
  if (!el || typeof el.animate !== 'function') return;
  try {
    el.animate(
      [
        { transform: 'translateX(0)' },
        { transform: 'translateX(-9px)' },
        { transform: 'translateX(8px)' },
        { transform: 'translateX(-6px)' },
        { transform: 'translateX(4px)' },
        { transform: 'translateX(-2px)' },
        { transform: 'translateX(0)' },
      ],
      { duration: 420, easing: 'cubic-bezier(0.36, 0.07, 0.19, 0.97)' }
    );
  } catch (_) {}
}

/**
 * Stellt sicher, dass jeder Klick auf den ESC-/Spielmenü-Button unten rechts
 * im HUD (oder in den Optionen) das ESC-Menü garantiert öffnet/schließt.
 */
function initEscButtonFallback(app) {
  document.addEventListener(
    'click',
    (ev) => {
      if (app.hudEditModeActive) return;
      const escTrigger = ev.target?.closest?.(
        '[data-open-win="gamemenu"], [data-open-win="esc"], #btn-quick-esc, #btn-open-gamemenu'
      );
      if (!escTrigger) return;
      ev.preventDefault();
      ev.stopPropagation();
      ev.stopImmediatePropagation?.();
      app.toggleWindow?.('gamemenu');
    },
    true
  );
}

/** Einmaliger Einstiegspunkt – nach bindHUDControls() aufrufen. */
export function initIosUi(app) {
  try { ensureEscMenuWorks(app); } catch (e) { console.warn(e); }
  try { initAdaptiveViewportScaler(app); } catch (e) { console.warn('[iOS-UI] ViewportScaler:', e); }
  if (!app || app._iosUiReady) return;
  app._iosUiReady = true;
  try {
    initUiTheme(app);
  } catch (err) {
    console.warn('[iOS-UI] Theme:', err);
  }
  try {
    initIslandToasts(app);
  } catch (err) {
    console.warn('[iOS-UI] Toasts:', err);
  }
  try {
    initDynamicSidebar(app);
  } catch (err) {
    console.warn('[iOS-UI] Sidebar:', err);
  }
  try {
    initChatIdleFade(app);
  } catch (err) {
    console.warn('[iOS-UI] Chat-Idle:', err);
  }
  try {
    initDynamicIslandInteractions(app);
  } catch (err) {
    console.warn('[iOS-UI] DynamicIsland:', err);
  }
  try {
    initEscButtonFallback(app);
  } catch (err) {
    console.warn('[iOS-UI] EscFallback:', err);
  }
}


// ============================================================================
// GARANTIERTER ESC-BUTTON & SPIELMENÜ / OPTIONEN FIX
// ============================================================================
function ensureEscMenuWorks(app) {
  if (!app || app._escMenuPatched) return;
  app._escMenuPatched = true;

  const ensureGameMenuDom = () => {
    const gm = app.ensureGameMenuWindowDom ? app.ensureGameMenuWindowDom() : document.getElementById('win-gamemenu');
    if (gm) {
      gm.style.setProperty('z-index', '9999', 'important');
      gm.style.setProperty('pointer-events', 'auto', 'important');
    }
    return gm;
  };

  ensureGameMenuDom();

  // Alle ESC-Buttons im HUD unten rechts (#hud-quick-menu) eindeutig markieren
  const bindQuickMenuEsc = () => {
    const qm = document.getElementById('hud-quick-menu');
    if (!qm) return;
    const btns = Array.from(qm.querySelectorAll('button, .nw-quick-btn, [data-open-win]'));
    btns.forEach((btn, idx) => {
      const attr = btn.getAttribute('data-open-win') || '';
      const txt = (btn.textContent || '').toUpperCase();
      if (
        attr === 'gamemenu' ||
        attr === 'esc' ||
        attr === 'menu' ||
        txt.includes('ESC') ||
        txt.includes('MENÜ') ||
        (idx === btns.length - 1 && !['inventory', 'character', 'skills', 'quests'].includes(attr))
      ) {
        btn.setAttribute('data-open-win', 'gamemenu');
      }
    });
  };
  bindQuickMenuEsc();
  setTimeout(bindQuickMenuEsc, 600);

  // openWindow & closeWindow absichern, damit gamemenu & options nie unsichtbar oder nicht-klickbar bleiben
  const origOpen = app.openWindow?.bind(app);
  if (origOpen) {
    app.openWindow = (winKey) => {
      if (winKey === 'esc' || winKey === 'menu') winKey = 'gamemenu';
      if (winKey === 'gamemenu') ensureGameMenuDom();
      origOpen(winKey);
      if (winKey === 'gamemenu' || winKey === 'options') {
        const el = document.getElementById('win-' + winKey);
        if (el) {
          el.classList.remove('hidden', 'ui-win-closing');
          el.style.removeProperty('display');
          if (window.getComputedStyle(el).display === 'none') {
            el.style.setProperty('display', 'flex', 'important');
          }
          el.style.setProperty('visibility', 'visible', 'important');
          el.style.setProperty('opacity', '1', 'important');
          el.style.setProperty('pointer-events', 'auto', 'important');
          if (winKey === 'gamemenu') {
            el.style.setProperty('z-index', '9999', 'important');
            const r = el.getBoundingClientRect();
            if (r.width < 40 || r.left < 0 || r.top < 0 || r.left > window.innerWidth - 40) {
              el.style.left = Math.max(12, Math.round((window.innerWidth - (r.width || 360)) * 0.5)) + 'px';
              el.style.top = Math.max(24, Math.round((window.innerHeight - (r.height || 440)) * 0.5)) + 'px';
            }
          }
        }
      }
    };
  }

  const origClose = app.closeWindow?.bind(app);
  if (origClose) {
    app.closeWindow = (winKey) => {
      if (winKey === 'esc' || winKey === 'menu') winKey = 'gamemenu';
      origClose(winKey);
      const el = document.getElementById('win-' + winKey);
      if (el) {
        setTimeout(() => {
          if (el.classList.contains('hidden')) {
            el.classList.remove('ui-win-closing');
            el.style.removeProperty('display');
          }
        }, 240);
      }
    };
  }

  // 1. Capture-Phase Shield für pointerdown/mousedown auf #win-gamemenu, damit 3D-Welt / Dragging keine Klicks schluckt
  ['pointerdown', 'mousedown'].forEach((evType) => {
    document.addEventListener(
      evType,
      (ev) => {
        const gm = ev.target?.closest?.('#win-gamemenu');
        if (!gm) return;
        const interactive = ev.target?.closest?.(
          'button, [data-esc-ch], [data-ui-theme], [data-close-win="gamemenu"]'
        );
        if (interactive) {
          ev.stopPropagation();
        }
      },
      true
    );
  });

  // 2. Delegierter Capture-Click-Handler für ALLE Buttons im ESC-Menü (#win-gamemenu)
  document.addEventListener(
    'click',
    (ev) => {
      const btn = ev.target?.closest?.(
        '#win-gamemenu button, #win-gamemenu [data-esc-ch], #win-gamemenu [data-ui-theme], #win-gamemenu [data-close-win="gamemenu"]'
      );
      if (!btn) return;
      ev.preventDefault();
      ev.stopPropagation();
      ev.stopImmediatePropagation?.();

      if (btn.matches('[data-close-win="gamemenu"]')) {
        app.closeWindow('gamemenu');
        return;
      }
      if (btn.hasAttribute('data-ui-theme')) {
        const pref = btn.getAttribute('data-ui-theme');
        app.setUiTheme?.(pref);
        app.renderGameMenuWindow?.();
        return;
      }
      if (btn.hasAttribute('data-esc-ch')) {
        const ch = Number(btn.getAttribute('data-esc-ch') || 1);
        app.selectedChannel = ch;
        try {
          localStorage.setItem('aeryndor_channel', String(ch));
        } catch (_) {}
        const snap = app.engine?.getEnvironmentSnapshot?.();
        if (snap) app.updateClimateHUD(snap);
        app.renderGameMenuWindow?.();
        app.showToast?.(`🌐 Gewechselt auf Channel CH ${ch}`);
        return;
      }

      const safeCloseEsc = () => {
        try {
          app.closeWindow('gamemenu');
        } catch (_) {
          document.getElementById('win-gamemenu')?.classList.add('hidden');
        }
      };

      switch (btn.id) {
        case 'esc-btn-gfx-perf':
          app.applyQuickGraphicsMode?.(0);
          break;
        case 'esc-btn-gfx-ultra':
          app.applyQuickGraphicsMode?.(2);
          break;
        case 'esc-btn-options':
          safeCloseEsc();
          app.openWindow('options');
          break;
        case 'esc-btn-worldmap':
          safeCloseEsc();
          app.openWindow('worldmap');
          break;
        case 'esc-btn-charselect':
          safeCloseEsc();
          app.showCharSelectPortal?.();
          break;
        case 'esc-btn-logout':
          safeCloseEsc();
          app.showLoginPortal?.();
          break;
        case 'esc-btn-quit':
          safeCloseEsc();
          app.showToast?.('â» Spiel wird beendet... Bis bald in Aeryndor!');
          setTimeout(() => {
            app.showLoginPortal?.();
            try {
              window.close?.();
            } catch (_) {}
          }, 320);
          break;
        case 'esc-btn-town': {
          const curMap = app.selfState?.map_id || 'morgenwacht';
          app.sendAction?.('change_map', { mapId: curMap, spawnX: 0, spawnZ: 148 });
          safeCloseEsc();
          app.showToast?.('🏛️ Rückkehr ins Dorf-Sanktuarium...');
          break;
        }
        case 'esc-btn-hud-edit':
          safeCloseEsc();
          app.toggleHudEditMode?.(true);
          break;
        case 'esc-btn-fullscreen':
          app.toggleFullscreen?.();
          safeCloseEsc();
          break;
      }
    },
    true
  );

  // 3. Globaler Klick-Handler (Capture) für den ESC-Button unten rechts im HUD
  document.addEventListener(
    'click',
    (ev) => {
      if (app.hudEditModeActive) return;
      const trg = ev.target?.closest?.(
        '#hud-quick-menu [data-open-win="gamemenu"], [data-open-win="esc"], #btn-quick-esc, #btn-open-gamemenu'
      );
      if (!trg) return;
      ev.preventDefault();
      ev.stopPropagation();
      ev.stopImmediatePropagation?.();
      const gmEl = ensureGameMenuDom();
      const optEl = document.getElementById('win-options');
      if (optEl && !optEl.classList.contains('hidden')) {
        app.closeWindow('options');
        return;
      }
      if (gmEl && !gmEl.classList.contains('hidden') && !gmEl.classList.contains('ui-win-closing')) {
        app.closeWindow('gamemenu');
      } else {
        app.openWindow('gamemenu');
      }
    },
    true
  );
}
setTimeout(() => {
  if (window.app) {
    ensureEscMenuWorks(window.app);
    initAdaptiveViewportScaler(window.app);
  } else {
    evaluateBrowserViewportAndScale(null);
  }
}, 100);

// ============================================================================
// 7. BROWSER-DATEN AUSWERTUNG & AUTOMATISCHE AUFLÖSUNGS-SKALIERUNG (iPhone / iPad / Desktop)
// ============================================================================
export function evaluateBrowserViewportAndScale(app = window.app || null) {
  const vv = window.visualViewport;
  const vw = Math.max(280, Math.round(vv?.width || window.innerWidth || document.documentElement.clientWidth || 1280));
  const vh = Math.max(240, Math.round(vv?.height || window.innerHeight || document.documentElement.clientHeight || 720));
  const dpr = Number((window.devicePixelRatio || 1).toFixed(2));
  const ua = navigator.userAgent || '';

  const isIOS = /iPhone|iPad|iPod/i.test(ua) || (navigator.platform === 'MacIntel' && (navigator.maxTouchPoints || 0) > 1);
  const isIPhone = /iPhone|iPod/i.test(ua) || (isIOS && Math.min(vw, vh) <= 480);
  const isAndroid = /Android/i.test(ua);
  const coarsePointer = Boolean(window.matchMedia?.('(pointer: coarse)')?.matches);
  const hasTouch = Boolean(coarsePointer || (navigator.maxTouchPoints || 0) > 0 || 'ontouchstart' in window || isIOS || isAndroid);

  const shortSide = Math.min(vw, vh);
  const longSide = Math.max(vw, vh);
  const orientation = vw >= vh ? 'landscape' : 'portrait';

  const isPhone = isIPhone || (isAndroid && shortSide <= 540) || shortSide <= 520 || vw <= 640;
  const isTablet = !isPhone && ((hasTouch && shortSide <= 960) || (vw <= 1080 && shortSide <= 860));
  const isMobile = isPhone || isTablet;

  let deviceTier = 'desktop';
  if (isPhone) {
    deviceTier = orientation === 'portrait' ? 'phone-portrait' : 'phone-landscape';
  } else if (isTablet) {
    deviceTier = 'tablet';
  } else if (vw <= 1440 || vh <= 840) {
    deviceTier = 'compact-desktop';
  }

  let hudScale = 1.0;
  let bottomBarScale = 1.0;
  let portalScale = 1.0;

  if (deviceTier === 'phone-portrait') {
    hudScale = Number(Math.max(0.56, Math.min(0.72, vw / 570)).toFixed(3));
    bottomBarScale = Number(Math.max(0.48, Math.min(0.66, (vw - 14) / 600)).toFixed(3));
    portalScale = 1.0;
  } else if (deviceTier === 'phone-landscape') {
    hudScale = Number(Math.max(0.58, Math.min(0.74, vh / 530)).toFixed(3));
    bottomBarScale = Number(Math.max(0.56, Math.min(0.74, (vw - 270) / 600)).toFixed(3));
    portalScale = 1.0;
  } else if (deviceTier === 'tablet') {
    hudScale = Number(Math.max(0.74, Math.min(0.90, Math.min(vw / 1280, vh / 820))).toFixed(3));
    bottomBarScale = Number(Math.max(0.70, Math.min(0.88, (vw - 200) / 650)).toFixed(3));
    portalScale = Number(Math.max(0.72, Math.min(0.92, Math.min(vw / 1400, vh / 860))).toFixed(3));
  } else if (deviceTier === 'compact-desktop') {
    hudScale = Number(Math.max(0.84, Math.min(0.96, Math.min(vw / 1620, vh / 920))).toFixed(3));
    bottomBarScale = Number(Math.max(0.84, Math.min(0.96, vw / 1600)).toFixed(3));
    portalScale = Number(Math.max(0.80, Math.min(0.96, Math.min(vw / 1680, vh / 920))).toFixed(3));
  }

  const telemetry = {
    vw,
    vh,
    dpr,
    shortSide,
    longSide,
    orientation,
    isIOS,
    isIPhone,
    isAndroid,
    hasTouch,
    isPhone,
    isTablet,
    isMobile,
    deviceTier,
    hudScale,
    bottomBarScale,
    portalScale,
  };

  const applyTargets = [document.documentElement, document.body].filter(Boolean);
  for (const el of applyTargets) {
    el.setAttribute('data-device-tier', deviceTier);
    el.setAttribute('data-orientation', orientation);
    el.setAttribute('data-touch', hasTouch ? 'true' : 'false');
    el.setAttribute('data-mobile', isMobile ? 'true' : 'false');
    el.setAttribute('data-phone', isPhone ? 'true' : 'false');
    el.setAttribute('data-ios', isIOS ? 'true' : 'false');
    el.style.setProperty('--agy-vw', `${vw}px`);
    el.style.setProperty('--agy-vh', `${vh}px`);
    el.style.setProperty('--agy-hud-scale', String(hudScale));
    el.style.setProperty('--agy-bottombar-scale', String(bottomBarScale));
    el.style.setProperty('--agy-portal-scale', String(portalScale));
  }

  if (app) {
    const prevTier = app.browserTelemetry?.deviceTier;
    app.browserTelemetry = telemetry;

    const mobCtrl = document.getElementById('mobile-controls');
    if (mobCtrl) {
      const showMob = Boolean(app.inWorld && (isMobile || hasTouch));
      mobCtrl.classList.toggle('is-visible-mobile', showMob);
    }

    if (isPhone && (!app._mobileInitialCollapseDone || prevTier !== deviceTier)) {
      app._mobileInitialCollapseDone = true;
      const chatBox = document.getElementById('hud-chat-box');
      if (chatBox && !chatBox.contains(document.activeElement)) {
        chatBox.classList.add('chat-idle');
      }
    }

    clampOpenWindowsToViewport(telemetry);

    try {
      app.engine?.onResize?.();
      app.showcase3D?.onResize?.();
    } catch (_) {}
  }

  return telemetry;
}

export function clampOpenWindowsToViewport(telemetry = null) {
  const vw = telemetry?.vw || Math.round(window.visualViewport?.width || window.innerWidth || 1280);
  const vh = telemetry?.vh || Math.round(window.visualViewport?.height || window.innerHeight || 720);
  const isPhone = Boolean(telemetry?.isPhone ?? (Math.min(vw, vh) <= 520 || vw <= 640));

  document.querySelectorAll('#windows-layer > .ornate-window:not(.hidden)').forEach((winEl) => {
    if (isPhone) {
      winEl.style.left = '6px';
      winEl.style.right = '6px';
      winEl.style.top = '46px';
      return;
    }
    const rect = winEl.getBoundingClientRect();
    const w = Math.min(rect.width || 420, vw - 16);
    const h = Math.min(rect.height || 360, vh - 64);
    const curLeft = parseFloat(winEl.style.left);
    const curTop = parseFloat(winEl.style.top);
    if (Number.isFinite(curLeft)) {
      const clampedLeft = Math.max(8, Math.min(vw - w - 8, curLeft));
      winEl.style.left = `${Math.round(clampedLeft)}px`;
    } else if (rect.left < 6 || rect.right > vw - 6) {
      winEl.style.left = `${Math.max(8, Math.round((vw - w) * 0.5))}px`;
      winEl.style.right = 'auto';
    }
    if (Number.isFinite(curTop)) {
      const clampedTop = Math.max(8, Math.min(vh - Math.min(h, 140) - 8, curTop));
      winEl.style.top = `${Math.round(clampedTop)}px`;
    }
  });
}

export function initAdaptiveViewportScaler(app) {
  evaluateBrowserViewportAndScale(app);
  if (window._agyViewportListenersBound) return;
  window._agyViewportListenersBound = true;

  let rafId = null;
  const scheduleEval = () => {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(() => {
      rafId = null;
      evaluateBrowserViewportAndScale(window.app || app);
    });
  };

  window.addEventListener('resize', scheduleEval, { passive: true });
  window.addEventListener('orientationchange', () => {
    scheduleEval();
    setTimeout(scheduleEval, 120);
    setTimeout(scheduleEval, 350);
  });
  document.addEventListener('fullscreenchange', scheduleEval);
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', scheduleEval, { passive: true });
    window.visualViewport.addEventListener('scroll', scheduleEval, { passive: true });
  }

  document.addEventListener(
    'gesturestart',
    (e) => {
      e.preventDefault();
    },
    { passive: false }
  );

  if (app && !app._mobileUiHooksBound) {
    app._mobileUiHooksBound = true;
    const origOpenWin = app.openWindow?.bind(app);
    if (origOpenWin) {
      app.openWindow = (winKey) => {
        const isPhone = Boolean(app.browserTelemetry?.isPhone);
        if (isPhone && winKey !== 'gamemenu') {
          const allWins = ['character', 'inventory', 'pet', 'generalstore', 'blacksmith', 'runeweaver', 'friends', 'autofarm', 'market', 'worldmap', 'options', 'events'];
          const normalizedTarget = winKey === 'skills' || winKey === 'quests' ? 'character' : winKey;
          allWins.forEach((wk) => {
            if (wk !== normalizedTarget) {
              const el = document.getElementById(`win-${wk}`);
              if (el && !el.classList.contains('hidden')) {
                app.closeWindow?.(wk);
              }
            }
          });
        }
        origOpenWin(winKey);
        evaluateBrowserViewportAndScale(app);
      };
    }

    setInterval(() => {
      if (!app.inWorld) {
        const mobCtrl = document.getElementById('mobile-controls');
        if (mobCtrl) mobCtrl.classList.remove('is-visible-mobile');
        return;
      }
      const mobCtrl = document.getElementById('mobile-controls');
      if (mobCtrl) {
        const showMob = Boolean(app.browserTelemetry?.isMobile || app.browserTelemetry?.hasTouch);
        mobCtrl.classList.toggle('is-visible-mobile', showMob);
      }
      const afBtn = document.getElementById('btn-mobile-autofarm');
      if (afBtn) {
        const afOn = Boolean(app.selfState?.autoFarmActive || app.selfState?.autofarm?.enabled || app.engine?.isServerAutoFarming);
        afBtn.classList.toggle('is-active', afOn);
      }
      const mountBtn = document.getElementById('btn-mobile-mount');
      if (mountBtn) {
        const mounted = Boolean(app.selfState?.mounted || app.selfState?.mountId || app.engine?.localPlayerActor?.mountGroup?.visible);
        mountBtn.classList.toggle('is-active', mounted);
      }
    }, 600);
  }
}

try {
  evaluateBrowserViewportAndScale(null);
} catch (_) {}
