// ============================================================================
// AERYNDOR: AGE OF LEGENDS – ADVANCED GAMEMASTER IDENTIFICATION SYSTEM
// ============================================================================
// Premium 3D Overhead Insignia & Team Emblems
// Distinct visual identity for all server-authorized team ranks:
//  - [SA] Server Administrator: Royal Golden Crown & Sunburst Crest
//  - [GA] Game Administrator: Heavy Knight's Sapphire & Silver Shield
//  - [GM] Game Master: Mystical Ice-Cyan Shield with Arcane Monogram Sigil
//  - [TGM] Trial Game Master: Radiant Turquoise & Platinum Insignia
//  - [SUP] Support: Emerald-Green Aegis Shield with Life-Crystal
// Supports high-performance Canvas 2D texture caching, floating bobbing,
// pulsing glow, distance scaling, and subtle orbital energy particles.
// ============================================================================

import * as THREE from '../../vendor/three.module.js';

export const TEAM_RANK_METADATA = {
  SA: {
    tag: 'SA',
    title: 'SERVER ADMINISTRATOR',
    badgeText: '★ SERVER ADMINISTRATOR ★',
    primaryColor: '#ffd700',
    secondaryColor: '#f59e0b',
    glowColor: 'rgba(251, 191, 36, 0.85)',
    particleHex: 0xfbbf24,
    hasParticles: true,
  },
  SGA: {
    tag: 'SGA',
    title: 'SENIOR GAME ADMIN',
    badgeText: '⚔ SENIOR GAME ADMIN ⚔',
    primaryColor: '#3b82f6',
    secondaryColor: '#f59e0b',
    glowColor: 'rgba(59, 130, 246, 0.85)',
    particleHex: 0x3b82f6,
    hasParticles: true,
  },
  GA: {
    tag: 'GA',
    title: 'GAME ADMINISTRATOR',
    badgeText: '⚔ GAME ADMINISTRATOR ⚔',
    primaryColor: '#60a5fa',
    secondaryColor: '#e2e8f0',
    glowColor: 'rgba(59, 130, 246, 0.85)',
    particleHex: 0x60a5fa,
    hasParticles: true,
  },
  TM: {
    tag: 'TM',
    title: 'TEAM MANAGER',
    badgeText: '👑 TEAM MANAGER 👑',
    primaryColor: '#c084fc',
    secondaryColor: '#fbbf24',
    glowColor: 'rgba(168, 85, 247, 0.85)',
    particleHex: 0xc084fc,
    hasParticles: true,
  },
  CM: {
    tag: 'CM',
    title: 'COMMUNITY MANAGER',
    badgeText: '⚜ COMMUNITY MANAGER ⚜',
    primaryColor: '#fb7185',
    secondaryColor: '#f43f5e',
    glowColor: 'rgba(244, 63, 94, 0.85)',
    particleHex: 0xfb7185,
    hasParticles: true,
  },
  SGM: {
    tag: 'SGM',
    title: 'SUPER GAME MASTER',
    badgeText: '✦ SUPER GAME MASTER ✦',
    primaryColor: '#38bdf8',
    secondaryColor: '#e2e8f0',
    glowColor: 'rgba(56, 189, 248, 0.85)',
    particleHex: 0x38bdf8,
    hasParticles: true,
  },
  GM: {
    tag: 'GM',
    title: 'GAME MASTER',
    badgeText: '✦ GAME MASTER ✦',
    primaryColor: '#22d3ee',
    secondaryColor: '#e0f2fe',
    glowColor: 'rgba(34, 211, 238, 0.90)',
    particleHex: 0x22d3ee,
    hasParticles: true,
  },
  TGM: {
    tag: 'TGM',
    title: 'TRIAL GAME MASTER',
    badgeText: '✧ TRIAL GAME MASTER ✧',
    primaryColor: '#2dd4bf',
    secondaryColor: '#99f6e4',
    glowColor: 'rgba(45, 212, 191, 0.80)',
    particleHex: 0x2dd4bf,
    hasParticles: true,
  },
  JGM: {
    tag: 'JGM',
    title: 'JUNIOR GAME MASTER',
    badgeText: '✧ JUNIOR GAME MASTER ✧',
    primaryColor: '#38bdf8',
    secondaryColor: '#bae6fd',
    glowColor: 'rgba(56, 189, 248, 0.75)',
    particleHex: 0x38bdf8,
    hasParticles: false,
  },
  DEV: {
    tag: 'DEV',
    title: 'DEVELOPER',
    badgeText: '⚙ DEVELOPER ⚙',
    primaryColor: '#a855f7',
    secondaryColor: '#f472b6',
    glowColor: 'rgba(168, 85, 247, 0.90)',
    particleHex: 0xa855f7,
    hasParticles: true,
  },
  EM: {
    tag: 'EM',
    title: 'EVENT MANAGER',
    badgeText: '★ EVENT MANAGER ★',
    primaryColor: '#f97316',
    secondaryColor: '#fde047',
    glowColor: 'rgba(249, 115, 22, 0.85)',
    particleHex: 0xf97316,
    hasParticles: true,
  },
  SUP: {
    tag: 'SUP',
    title: 'SUPPORT',
    badgeText: '🛡 SUPPORTER 🛡',
    primaryColor: '#34d399',
    secondaryColor: '#ecfdf5',
    glowColor: 'rgba(52, 211, 153, 0.85)',
    particleHex: 0x34d399,
    hasParticles: false,
  },
};

export class TeamEmblemSystem {
  constructor() {
    this.textureCache = new Map();
    this.activeGroups = new Set();
    this._particleTex = null;
  }

  getRankMeta(rawRank) {
    const key = String(rawRank || '').trim().toUpperCase();
    return TEAM_RANK_METADATA[key] || TEAM_RANK_METADATA.GM;
  }

  // Erzeugt oder liefert die gecachte CanvasTexture für einen Rang
  getOrCreateTexture(rank) {
    const meta = this.getRankMeta(rank);
    const cacheKey = `${meta.tag}_emblem`;
    if (this.textureCache.has(cacheKey)) {
      return this.textureCache.get(cacheKey);
    }

    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    this.drawEmblem(ctx, meta);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.generateMipmaps = false;

    this.textureCache.set(cacheKey, texture);
    return texture;
  }

  // Zeichnet das vollständige hochauflösende 2D-Canvas-Wappen (zentriert ohne Banner)
  drawEmblem(ctx, meta) {
    const cx = 256;
    const cy = 256;

    ctx.save();
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    // 1. Sanfter radialer Hintergrund-Aura-Glow
    const auraRadius = 230;
    const auraGrad = ctx.createRadialGradient(cx, cy, 10, cx, cy, auraRadius);
    auraGrad.addColorStop(0, meta.glowColor);
    auraGrad.addColorStop(0.45, meta.glowColor.replace(/[\d\.]+\)$/, '0.35)'));
    auraGrad.addColorStop(0.85, meta.glowColor.replace(/[\d\.]+\)$/, '0.08)'));
    auraGrad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = auraGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, auraRadius, 0, Math.PI * 2);
    ctx.fill();

    // 2. Äußerer rotierender Runen- bzw. Zierring
    ctx.save();
    ctx.strokeStyle = meta.glowColor.replace(/[\d\.]+\)$/, '0.5)');
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(cx, cy, 158, 0, Math.PI * 2);
    ctx.stroke();

    // Dezente Zierbögen & Kompass-Knotenpunkte
    for (let i = 0; i < 8; i++) {
      const angle = (i * Math.PI) / 4;
      const rx = cx + Math.cos(angle) * 158;
      const ry = cy + Math.sin(angle) * 158;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(rx, ry, i % 2 === 0 ? 3.5 : 2.0, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();

    // 3. Rang-spezifische Insignia-Geometrie
    switch (meta.tag) {
      case 'SA':
        this.drawServerAdminEmblem(ctx, cx, cy);
        break;
      case 'GA':
      case 'SGA':
        this.drawGameAdminEmblem(ctx, cx, cy, meta.tag === 'SGA');
        break;
      case 'GM':
      case 'SGM':
      case 'JGM':
        this.drawGameMasterEmblem(ctx, cx, cy, meta.tag);
        break;
      case 'TGM':
        this.drawTrialGameMasterEmblem(ctx, cx, cy);
        break;
      case 'SUP':
        this.drawSupportEmblem(ctx, cx, cy);
        break;
      case 'DEV':
        this.drawDeveloperEmblem(ctx, cx, cy);
        break;
      case 'TM':
        this.drawTeamManagerEmblem(ctx, cx, cy);
        break;
      case 'CM':
        this.drawCommunityManagerEmblem(ctx, cx, cy);
        break;
      default:
        this.drawGameMasterEmblem(ctx, cx, cy, 'GM');
        break;
    }

    ctx.restore();
  }

  // --- [SA] SERVER ADMINISTRATOR: Royal Golden Insignia mit Krone & Sonnenstrahlen ---
  drawServerAdminEmblem(ctx, cx, cy) {
    ctx.save();

    // Ornate goldene Sonnenstrahlen im Hintergrund
    ctx.save();
    for (let i = 0; i < 16; i++) {
      const a = (i * Math.PI) / 8;
      const len = i % 2 === 0 ? 152 : 132;
      ctx.strokeStyle = i % 2 === 0 ? 'rgba(254, 240, 138, 0.65)' : 'rgba(245, 158, 11, 0.45)';
      ctx.lineWidth = i % 2 === 0 ? 3 : 1.5;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(a) * len, cy + Math.sin(a) * len);
      ctx.stroke();
    }
    ctx.restore();

    // Seitliche goldene Schwingen / Lorbeer-Flügel
    const drawWing = (side) => {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.scale(side, 1);
      const wingGrad = ctx.createLinearGradient(0, -60, 130, 40);
      wingGrad.addColorStop(0, '#fef08a');
      wingGrad.addColorStop(0.4, '#ffd700');
      wingGrad.addColorStop(0.8, '#b45309');
      wingGrad.addColorStop(1, '#78350f');

      ctx.fillStyle = wingGrad;
      ctx.strokeStyle = '#fffbeb';
      ctx.lineWidth = 2;

      ctx.beginPath();
      ctx.moveTo(20, -10);
      ctx.bezierCurveTo(70, -75, 130, -50, 142, -15);
      ctx.bezierCurveTo(125, 10, 85, 30, 40, 45);
      ctx.bezierCurveTo(75, 15, 75, -20, 20, -10);
      ctx.closePath();
      ctx.shadowColor = 'rgba(0,0,0,0.7)';
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.stroke();

      // Sekundärfeder
      ctx.beginPath();
      ctx.moveTo(25, 15);
      ctx.bezierCurveTo(65, 5, 115, 20, 125, 45);
      ctx.bezierCurveTo(95, 55, 60, 55, 25, 50);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.restore();
    };
    drawWing(1);
    drawWing(-1);

    // Zentrales goldenes Wappenschild (Base)
    const shieldGrad = ctx.createLinearGradient(cx - 70, cy - 60, cx + 70, cy + 80);
    shieldGrad.addColorStop(0, '#fffbeb');
    shieldGrad.addColorStop(0.2, '#ffd700');
    shieldGrad.addColorStop(0.7, '#d97706');
    shieldGrad.addColorStop(1, '#78350f');

    ctx.beginPath();
    ctx.moveTo(cx, cy - 75);
    ctx.lineTo(cx + 68, cy - 45);
    ctx.lineTo(cx + 62, cy + 25);
    ctx.lineTo(cx, cy + 92);
    ctx.lineTo(cx - 62, cy + 25);
    ctx.lineTo(cx - 68, cy - 45);
    ctx.closePath();

    ctx.shadowColor = 'rgba(0,0,0,0.85)';
    ctx.shadowBlur = 12;
    ctx.fillStyle = shieldGrad;
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3.5;
    ctx.stroke();

    // Innerer dunkel-königlicher Schildspiegel
    ctx.beginPath();
    ctx.moveTo(cx, cy - 62);
    ctx.lineTo(cx + 52, cy - 36);
    ctx.lineTo(cx + 46, cy + 20);
    ctx.lineTo(cx, cy + 74);
    ctx.lineTo(cx - 46, cy + 20);
    ctx.lineTo(cx - 52, cy - 36);
    ctx.closePath();
    const innerGrad = ctx.createLinearGradient(cx, cy - 62, cx, cy + 74);
    innerGrad.addColorStop(0, '#451a03');
    innerGrad.addColorStop(0.5, '#78350f');
    innerGrad.addColorStop(1, '#292524');
    ctx.fillStyle = innerGrad;
    ctx.fill();
    ctx.strokeStyle = '#fde047';
    ctx.lineWidth = 2;
    ctx.stroke();

    // 5-Spitzige Kaiserliche Krone auf dem Schild
    const crownY = cy - 8;
    ctx.save();
    const crownGrad = ctx.createLinearGradient(cx - 45, crownY - 45, cx + 45, crownY + 20);
    crownGrad.addColorStop(0, '#ffffff');
    crownGrad.addColorStop(0.3, '#fde047');
    crownGrad.addColorStop(0.7, '#d97706');
    crownGrad.addColorStop(1, '#92400e');
    ctx.fillStyle = crownGrad;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2.5;

    ctx.beginPath();
    ctx.moveTo(cx - 42, crownY + 16);
    ctx.lineTo(cx - 46, crownY - 20); // Linke äußere Spitze
    ctx.lineTo(cx - 22, crownY - 5);
    ctx.lineTo(cx - 24, crownY - 38); // Linke Zwischenspitze
    ctx.lineTo(cx, crownY - 14);
    ctx.lineTo(cx, crownY - 54); // Hohe mittlere Kaiserspitze mit Fleur-de-lis
    ctx.lineTo(cx, crownY - 14);
    ctx.lineTo(cx + 24, crownY - 38); // Rechte Zwischenspitze
    ctx.lineTo(cx + 22, crownY - 5);
    ctx.lineTo(cx + 46, crownY - 20); // Rechte äußere Spitze
    ctx.lineTo(cx + 42, crownY + 16);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Rubin- und Diamant-Cabochons an den Kronenspitzen
    const drawGem = (gx, gy, rad, isDiamond) => {
      const gGrad = ctx.createRadialGradient(gx - rad * 0.3, gy - rad * 0.3, 1, gx, gy, rad);
      if (isDiamond) {
        gGrad.addColorStop(0, '#ffffff');
        gGrad.addColorStop(0.5, '#e0f2fe');
        gGrad.addColorStop(1, '#0284c7');
      } else {
        gGrad.addColorStop(0, '#fecdd3');
        gGrad.addColorStop(0.4, '#e11d48');
        gGrad.addColorStop(1, '#881337');
      }
      ctx.fillStyle = gGrad;
      ctx.beginPath();
      ctx.arc(gx, gy, rad, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      ctx.stroke();
    };

    drawGem(cx, crownY - 54, 5.5, true); // Zentraler Diamant
    drawGem(cx - 24, crownY - 38, 4.2, false); // Rubin links
    drawGem(cx + 24, crownY - 38, 4.2, false); // Rubin rechts
    drawGem(cx - 46, crownY - 20, 3.5, true);
    drawGem(cx + 46, crownY - 20, 3.5, true);

    // Kronenband-Verzierung
    ctx.fillStyle = '#451a03';
    ctx.fillRect(cx - 36, crownY + 8, 72, 8);
    ctx.strokeStyle = '#fef08a';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(cx - 36, crownY + 8, 72, 8);
    drawGem(cx - 24, crownY + 12, 2.5, true);
    drawGem(cx, crownY + 12, 3.0, false);
    drawGem(cx + 24, crownY + 12, 2.5, true);

    // Strahlendes "SA"-Zentralsiegel unter der Krone
    ctx.font = '900 24px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#f59e0b';
    ctx.shadowBlur = 10;
    ctx.fillText('SA', cx, cy + 42);
    ctx.shadowBlur = 0;

    ctx.restore();
    ctx.restore();
  }

  // --- [GA] / [SGA] GAME ADMINISTRATOR: Schwerer Saphir- & Silber-Ritterschild ---
  drawGameAdminEmblem(ctx, cx, cy, isSGA = false) {
    ctx.save();

    // Gekreuzte Breitschwerter hinter dem Schild
    const drawSword = (angle) => {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(angle);
      const bladeGrad = ctx.createLinearGradient(-6, -135, 6, 135);
      bladeGrad.addColorStop(0, '#ffffff');
      bladeGrad.addColorStop(0.5, '#94a3b8');
      bladeGrad.addColorStop(1, '#334155');

      ctx.fillStyle = bladeGrad;
      ctx.strokeStyle = '#e2e8f0';
      ctx.lineWidth = 1.5;

      // Klinge
      ctx.beginPath();
      ctx.moveTo(0, -145);
      ctx.lineTo(8, -130);
      ctx.lineTo(7, 80);
      ctx.lineTo(-7, 80);
      ctx.lineTo(-8, -130);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Parierstange
      ctx.fillStyle = isSGA ? '#fbbf24' : '#cbd5e1';
      ctx.fillRect(-22, 80, 44, 9);
      ctx.strokeRect(-22, 80, 44, 9);

      // Knauf
      ctx.beginPath();
      ctx.arc(0, 112, 7, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.restore();
    };
    drawSword(Math.PI / 4);
    drawSword(-Math.PI / 4);

    // Äußeres Silber/Stahl-Schild (Heater-Shield)
    const shieldGrad = ctx.createLinearGradient(cx - 75, cy - 80, cx + 75, cy + 90);
    if (isSGA) {
      shieldGrad.addColorStop(0, '#fef08a');
      shieldGrad.addColorStop(0.3, '#3b82f6');
      shieldGrad.addColorStop(0.8, '#1e3a8a');
      shieldGrad.addColorStop(1, '#d97706');
    } else {
      shieldGrad.addColorStop(0, '#ffffff');
      shieldGrad.addColorStop(0.25, '#94a3b8');
      shieldGrad.addColorStop(0.65, '#334155');
      shieldGrad.addColorStop(1, '#0f172a');
    }

    ctx.beginPath();
    ctx.moveTo(cx - 72, cy - 75);
    ctx.lineTo(cx + 72, cy - 75);
    ctx.lineTo(cx + 72, cy + 15);
    ctx.bezierCurveTo(cx + 70, cy + 68, cx + 32, cy + 98, cx, cy + 112);
    ctx.bezierCurveTo(cx - 32, cy + 98, cx - 70, cy + 68, cx - 72, cy + 15);
    ctx.closePath();

    ctx.shadowColor = 'rgba(0,0,0,0.85)';
    ctx.shadowBlur = 14;
    ctx.fillStyle = shieldGrad;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = isSGA ? '#fde047' : '#ffffff';
    ctx.lineWidth = 4;
    ctx.stroke();

    // Inneres tiefblaues Emaille-Feld
    ctx.beginPath();
    ctx.moveTo(cx - 56, cy - 62);
    ctx.lineTo(cx + 56, cy - 62);
    ctx.lineTo(cx + 56, cy + 12);
    ctx.bezierCurveTo(cx + 54, cy + 54, cx + 24, cy + 80, cx, cy + 94);
    ctx.bezierCurveTo(cx - 24, cy + 80, cx - 54, cy + 54, cx - 56, cy + 12);
    ctx.closePath();

    const blueGrad = ctx.createLinearGradient(cx, cy - 62, cx, cy + 94);
    blueGrad.addColorStop(0, '#1d4ed8');
    blueGrad.addColorStop(0.5, '#1e3a8a');
    blueGrad.addColorStop(1, '#0c1a3b');
    ctx.fillStyle = blueGrad;
    ctx.fill();
    ctx.strokeStyle = isSGA ? '#fbbf24' : '#60a5fa';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Zentraler facettierter Saphir-Stern
    ctx.save();
    ctx.translate(cx, cy + 8);
    const starGrad = ctx.createLinearGradient(-35, -35, 35, 35);
    starGrad.addColorStop(0, '#ffffff');
    starGrad.addColorStop(0.35, '#93c5fd');
    starGrad.addColorStop(0.8, '#2563eb');
    starGrad.addColorStop(1, '#1e3a8a');

    ctx.fillStyle = starGrad;
    ctx.beginPath();
    ctx.moveTo(0, -42);
    ctx.lineTo(11, -12);
    ctx.lineTo(42, 0);
    ctx.lineTo(11, 12);
    ctx.lineTo(0, 42);
    ctx.lineTo(-11, 12);
    ctx.lineTo(-42, 0);
    ctx.lineTo(-11, -12);
    ctx.closePath();
    ctx.shadowColor = '#60a5fa';
    ctx.shadowBlur = 12;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Facetten-Linien des Sterns
    ctx.strokeStyle = 'rgba(255,255,255,0.75)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, -42);
    ctx.lineTo(0, 42);
    ctx.moveTo(-42, 0);
    ctx.lineTo(42, 0);
    ctx.stroke();

    ctx.restore();

    // Rangtext-Kürzel oben
    ctx.font = '900 20px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#3b82f6';
    ctx.shadowBlur = 8;
    ctx.fillText(isSGA ? 'SGA' : 'GA', cx, cy - 38);
    ctx.shadowBlur = 0;

    ctx.restore();
  }

  // --- [GM] GAME MASTER: Mystischer Diamant-Schild mit originalem GM-Monogramm-Sigil ---
  drawGameMasterEmblem(ctx, cx, cy, rankTag = 'GM') {
    ctx.save();

    // Äußere kristalline Energieklingen / Flügel
    const drawCrystalWing = (side) => {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.scale(side, 1);
      const wingGrad = ctx.createLinearGradient(10, -70, 140, 20);
      wingGrad.addColorStop(0, '#e0f2fe');
      wingGrad.addColorStop(0.3, '#38bdf8');
      wingGrad.addColorStop(0.7, '#0284c7');
      wingGrad.addColorStop(1, '#082f49');

      ctx.fillStyle = wingGrad;
      ctx.strokeStyle = '#bae6fd';
      ctx.lineWidth = 2.5;

      ctx.beginPath();
      ctx.moveTo(35, -25);
      ctx.lineTo(125, -95); // Hohe spitze Kristallflügel
      ctx.lineTo(138, -45);
      ctx.lineTo(95, 10);
      ctx.lineTo(120, 25);
      ctx.lineTo(75, 55);
      ctx.lineTo(35, 30);
      ctx.closePath();

      ctx.shadowColor = '#06b6d4';
      ctx.shadowBlur = 14;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.stroke();
      ctx.restore();
    };
    drawCrystalWing(1);
    drawCrystalWing(-1);

    // Hauptschild: Mystische Kristallraute (Diamond Shield)
    const shieldGrad = ctx.createLinearGradient(cx - 65, cy - 85, cx + 65, cy + 85);
    shieldGrad.addColorStop(0, '#ffffff');
    shieldGrad.addColorStop(0.2, '#67e8f9');
    shieldGrad.addColorStop(0.6, '#0891b2');
    shieldGrad.addColorStop(1, '#0e7490');

    ctx.beginPath();
    ctx.moveTo(cx, cy - 90);
    ctx.lineTo(cx + 68, cy - 10);
    ctx.lineTo(cx, cy + 96);
    ctx.lineTo(cx - 68, cy - 10);
    ctx.closePath();

    ctx.shadowColor = 'rgba(0,0,0,0.85)';
    ctx.shadowBlur = 14;
    ctx.fillStyle = shieldGrad;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 4;
    ctx.stroke();

    // Innerer dunkler Arkanspiegel
    ctx.beginPath();
    ctx.moveTo(cx, cy - 74);
    ctx.lineTo(cx + 52, cy - 10);
    ctx.lineTo(cx, cy + 78);
    ctx.lineTo(cx - 52, cy - 10);
    ctx.closePath();

    const innerGrad = ctx.createLinearGradient(cx, cy - 74, cx, cy + 78);
    innerGrad.addColorStop(0, '#042f2e');
    innerGrad.addColorStop(0.5, '#083344');
    innerGrad.addColorStop(1, '#0f172a');
    ctx.fillStyle = innerGrad;
    ctx.fill();
    ctx.strokeStyle = '#22d3ee';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // =========================================================================
    // ORIGINALE GM-MONOGRAMM-SIGIL-GEOMETRIE:
    // Scharfe, heraldische Verflechtung der Buchstaben "G" und "M"
    // =========================================================================
    ctx.save();
    ctx.translate(cx, cy - 2);

    const sigilGrad = ctx.createLinearGradient(-35, -40, 35, 40);
    sigilGrad.addColorStop(0, '#ffffff');
    sigilGrad.addColorStop(0.3, '#a5f3fc');
    sigilGrad.addColorStop(0.7, '#22d3ee');
    sigilGrad.addColorStop(1, '#0284c7');

    ctx.fillStyle = sigilGrad;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2.5;
    ctx.shadowColor = '#06b6d4';
    ctx.shadowBlur = 12;

    // Stylisiertes "G" (links / Mitte)
    ctx.beginPath();
    ctx.moveTo(10, -28);
    ctx.lineTo(-14, -28);
    ctx.lineTo(-28, -12);
    ctx.lineTo(-28, 14);
    ctx.lineTo(-14, 28);
    ctx.lineTo(14, 28);
    ctx.lineTo(24, 18);
    ctx.lineTo(24, 4);
    ctx.lineTo(0, 4);
    ctx.lineTo(0, 14);
    ctx.lineTo(12, 14);
    ctx.lineTo(8, 20);
    ctx.lineTo(-8, 20);
    ctx.lineTo(-18, 8);
    ctx.lineTo(-18, -8);
    ctx.lineTo(-8, -20);
    ctx.lineTo(10, -20);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Stylisiertes erhöhtes "M" (Mitte / rechts verwoben)
    ctx.beginPath();
    ctx.moveTo(-10, 22);
    ctx.lineTo(-10, -18);
    ctx.lineTo(-2, -8);
    ctx.lineTo(12, -26);
    ctx.lineTo(28, -6);
    ctx.lineTo(28, 22);
    ctx.lineTo(20, 22);
    ctx.lineTo(20, 2);
    ctx.lineTo(12, -12);
    ctx.lineTo(-2, 2);
    ctx.lineTo(-2, 22);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Zentraler Nexus-Leuchtpunkt
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(0, 0, 3.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();

    // Rank-Header Text falls SGM / JGM
    if (rankTag !== 'GM') {
      ctx.font = '900 15px "Cinzel", "Times New Roman", serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#ffffff';
      ctx.shadowColor = '#22d3ee';
      ctx.shadowBlur = 6;
      ctx.fillText(rankTag, cx, cy - 54);
      ctx.shadowBlur = 0;
    }

    ctx.restore();
  }

  // --- [TGM] TRIAL GAME MASTER: Elegante Türkis-Insignie mit dezentem Leuchtrand ---
  drawTrialGameMasterEmblem(ctx, cx, cy) {
    ctx.save();

    // Türkise Sternen-Aura
    const shieldGrad = ctx.createLinearGradient(cx - 60, cy - 75, cx + 60, cy + 75);
    shieldGrad.addColorStop(0, '#ffffff');
    shieldGrad.addColorStop(0.25, '#5eead4');
    shieldGrad.addColorStop(0.7, '#14b8a6');
    shieldGrad.addColorStop(1, '#0f766e');

    // 4-Spitziger Eleganter Kristallstern
    ctx.beginPath();
    ctx.moveTo(cx, cy - 84);
    ctx.lineTo(cx + 26, cy - 26);
    ctx.lineTo(cx + 84, cy);
    ctx.lineTo(cx + 26, cy + 26);
    ctx.lineTo(cx, cy + 84);
    ctx.lineTo(cx - 26, cy + 26);
    ctx.lineTo(cx - 84, cy);
    ctx.lineTo(cx - 26, cy - 26);
    ctx.closePath();

    ctx.shadowColor = 'rgba(0,0,0,0.8)';
    ctx.shadowBlur = 12;
    ctx.fillStyle = shieldGrad;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3;
    ctx.stroke();

    // Innerer dunkler Jade-Kern
    ctx.beginPath();
    ctx.moveTo(cx, cy - 62);
    ctx.lineTo(cx + 18, cy - 18);
    ctx.lineTo(cx + 62, cy);
    ctx.lineTo(cx + 18, cy + 18);
    ctx.lineTo(cx, cy + 62);
    ctx.lineTo(cx - 18, cy + 18);
    ctx.lineTo(cx - 62, cy);
    ctx.lineTo(cx - 18, cy - 18);
    ctx.closePath();

    const innerGrad = ctx.createLinearGradient(cx, cy - 62, cx, cy + 62);
    innerGrad.addColorStop(0, '#042f2e');
    innerGrad.addColorStop(0.5, '#134e4a');
    innerGrad.addColorStop(1, '#022c22');
    ctx.fillStyle = innerGrad;
    ctx.fill();
    ctx.strokeStyle = '#2dd4bf';
    ctx.lineWidth = 2;
    ctx.stroke();

    // TGM Monogramm / Sternenkern
    ctx.font = '900 24px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#2dd4bf';
    ctx.shadowBlur = 10;
    ctx.fillText('TGM', cx, cy);
    ctx.shadowBlur = 0;

    ctx.restore();
  }

  // --- [SUP] SUPPORT: Smaragdgrünes Wappen mit sauberer professioneller Ästhetik ---
  drawSupportEmblem(ctx, cx, cy) {
    ctx.save();

    // Smaragd-Schutzschild mit silbernem Lorbeer-Rand
    const shieldGrad = ctx.createLinearGradient(cx - 65, cy - 75, cx + 65, cy + 85);
    shieldGrad.addColorStop(0, '#ffffff');
    shieldGrad.addColorStop(0.2, '#6ee7b7');
    shieldGrad.addColorStop(0.65, '#059669');
    shieldGrad.addColorStop(1, '#064e3b');

    ctx.beginPath();
    ctx.moveTo(cx - 64, cy - 68);
    ctx.lineTo(cx + 64, cy - 68);
    ctx.lineTo(cx + 64, cy + 10);
    ctx.bezierCurveTo(cx + 62, cy + 58, cx + 28, cy + 86, cx, cy + 98);
    ctx.bezierCurveTo(cx - 28, cy + 86, cx - 62, cy + 58, cx - 64, cy + 10);
    ctx.closePath();

    ctx.shadowColor = 'rgba(0,0,0,0.8)';
    ctx.shadowBlur = 12;
    ctx.fillStyle = shieldGrad;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3.5;
    ctx.stroke();

    // Inneres Smaragd-Feld
    ctx.beginPath();
    ctx.moveTo(cx - 50, cy - 54);
    ctx.lineTo(cx + 50, cy - 54);
    ctx.lineTo(cx + 50, cy + 8);
    ctx.bezierCurveTo(cx + 48, cy + 46, cx + 22, cy + 68, cx, cy + 80);
    ctx.bezierCurveTo(cx - 22, cy + 68, cx - 48, cy + 46, cx - 50, cy + 8);
    ctx.closePath();

    const innerGrad = ctx.createLinearGradient(cx, cy - 54, cx, cy + 80);
    innerGrad.addColorStop(0, '#064e3b');
    innerGrad.addColorStop(0.5, '#022c22');
    innerGrad.addColorStop(1, '#064e3b');
    ctx.fillStyle = innerGrad;
    ctx.fill();
    ctx.strokeStyle = '#34d399';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Zentrales weiß-grünes Kreuz des Lebens / der Hilfe
    ctx.save();
    ctx.translate(cx, cy + 8);
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#34d399';
    ctx.shadowBlur = 12;

    const barW = 14;
    const barH = 46;
    ctx.fillRect(-barW / 2, -barH / 2, barW, barH);
    ctx.fillRect(-barH / 2, -barW / 2, barH, barW);

    // Innerer Smaragd-Edelstein
    const gGrad = ctx.createRadialGradient(0, 0, 1, 0, 0, 7);
    gGrad.addColorStop(0, '#ffffff');
    gGrad.addColorStop(0.5, '#34d399');
    gGrad.addColorStop(1, '#065f46');
    ctx.fillStyle = gGrad;
    ctx.beginPath();
    ctx.arc(0, 0, 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // SUP Text oben
    ctx.font = '900 18px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#34d399';
    ctx.shadowBlur = 6;
    ctx.fillText('SUP', cx, cy - 36);
    ctx.shadowBlur = 0;

    ctx.restore();
  }

  // --- [DEV] DEVELOPER: Arkane Tech-Rune & Sechskant-Kristall ---
  drawDeveloperEmblem(ctx, cx, cy) {
    ctx.save();
    const hexGrad = ctx.createLinearGradient(cx - 70, cy - 70, cx + 70, cy + 70);
    hexGrad.addColorStop(0, '#ffffff');
    hexGrad.addColorStop(0.2, '#c084fc');
    hexGrad.addColorStop(0.7, '#7e22ce');
    hexGrad.addColorStop(1, '#3b0764');

    // Sechseckige Insignie
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = (i * Math.PI) / 3;
      const x = cx + Math.cos(a) * 78;
      const y = cy + Math.sin(a) * 78;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = hexGrad;
    ctx.fill();
    ctx.strokeStyle = '#f0abfc';
    ctx.lineWidth = 3.5;
    ctx.stroke();

    // Zentrales Zahnrad / Tech-Rune
    ctx.save();
    ctx.translate(cx, cy);
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#c084fc';
    ctx.shadowBlur = 10;
    ctx.font = '900 22px "Cinzel", "Courier New", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('DEV', 0, 0);
    ctx.restore();

    ctx.restore();
  }

  // --- [TM] TEAM MANAGER: Royal Amethyst & Gold ---
  drawTeamManagerEmblem(ctx, cx, cy) {
    ctx.save();
    const grad = ctx.createLinearGradient(cx - 65, cy - 75, cx + 65, cy + 85);
    grad.addColorStop(0, '#fde047');
    grad.addColorStop(0.3, '#c084fc');
    grad.addColorStop(0.8, '#581c87');
    grad.addColorStop(1, '#3b0764');

    ctx.beginPath();
    ctx.moveTo(cx, cy - 82);
    ctx.lineTo(cx + 66, cy - 35);
    ctx.lineTo(cx + 52, cy + 45);
    ctx.lineTo(cx, cy + 92);
    ctx.lineTo(cx - 52, cy + 45);
    ctx.lineTo(cx - 66, cy - 35);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.strokeStyle = '#fde047';
    ctx.lineWidth = 3.5;
    ctx.stroke();

    ctx.font = '900 24px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('TM', cx, cy);
    ctx.restore();
  }

  // --- [CM] COMMUNITY MANAGER: Crimson & Rose ---
  drawCommunityManagerEmblem(ctx, cx, cy) {
    ctx.save();
    const grad = ctx.createLinearGradient(cx - 65, cy - 75, cx + 65, cy + 85);
    grad.addColorStop(0, '#ffffff');
    grad.addColorStop(0.2, '#fda4af');
    grad.addColorStop(0.7, '#e11d48');
    grad.addColorStop(1, '#881337');

    ctx.beginPath();
    ctx.moveTo(cx, cy - 78);
    ctx.bezierCurveTo(cx + 60, cy - 78, cx + 75, cy - 20, cx + 60, cy + 30);
    ctx.bezierCurveTo(cx + 45, cy + 70, cx + 15, cy + 90, cx, cy + 96);
    ctx.bezierCurveTo(cx - 15, cy + 90, cx - 45, cy + 70, cx - 60, cy + 30);
    ctx.bezierCurveTo(cx - 75, cy - 20, cx - 60, cy - 78, cx, cy - 78);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3.5;
    ctx.stroke();

    ctx.font = '900 24px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('CM', cx, cy + 6);
    ctx.restore();
  }

  // --- UNTERE RANG-BEZEICHNUNG: Kristallenes Plaque-Banner ---
  drawRankBadgeBanner(ctx, cx, badgeY, meta) {
    const bannerW = 390;
    const bannerH = 52;
    const x = cx - bannerW / 2;
    const y = badgeY - bannerH / 2;
    const rad = 10;

    ctx.save();

    // Dunkles opakes Obsidian-Glas
    ctx.beginPath();
    ctx.moveTo(x + rad, y);
    ctx.lineTo(x + bannerW - rad, y);
    ctx.quadraticCurveTo(x + bannerW, y, x + bannerW, y + rad);
    ctx.lineTo(x + bannerW, y + bannerH - rad);
    ctx.quadraticCurveTo(x + bannerW, y + bannerH, x + bannerW - rad, y + bannerH);
    ctx.lineTo(x + rad, y + bannerH);
    ctx.quadraticCurveTo(x, y + bannerH, x, y + bannerH - rad);
    ctx.lineTo(x, y + rad);
    ctx.quadraticCurveTo(x, y, x + rad, y);
    ctx.closePath();

    ctx.shadowColor = 'rgba(0,0,0,0.95)';
    ctx.shadowBlur = 10;
    ctx.fillStyle = 'rgba(6, 11, 25, 0.92)';
    ctx.fill();
    ctx.shadowBlur = 0;

    // Metallic-Rahmen mit Glanzkante
    const borderGrad = ctx.createLinearGradient(x, y, x + bannerW, y + bannerH);
    borderGrad.addColorStop(0, '#ffffff');
    borderGrad.addColorStop(0.3, meta.primaryColor);
    borderGrad.addColorStop(0.7, meta.secondaryColor);
    borderGrad.addColorStop(1, '#ffffff');
    ctx.strokeStyle = borderGrad;
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Seitliche Zierdiamanten
    const drawSideGem = (gx, gy) => {
      ctx.fillStyle = meta.primaryColor;
      ctx.beginPath();
      ctx.moveTo(gx, gy - 6);
      ctx.lineTo(gx + 6, gy);
      ctx.lineTo(gx, gy + 6);
      ctx.lineTo(gx - 6, gy);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      ctx.stroke();
    };
    drawSideGem(x + 16, badgeY);
    drawSideGem(x + bannerW - 16, badgeY);

    // Text: Glänzende, zentrierte Rang-Bezeichnung mit starkem Kontur-Schatten
    ctx.font = 'bold 22px Inter, "Segoe UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // Dunkler Text-Umriss für 100% Lesbarkeit vor jedem Hintergrund
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 5;
    ctx.strokeText(meta.badgeText, cx, badgeY);

    // Text-Gradient
    const textGrad = ctx.createLinearGradient(x, badgeY - 12, x, badgeY + 12);
    textGrad.addColorStop(0, '#ffffff');
    textGrad.addColorStop(0.5, meta.primaryColor);
    textGrad.addColorStop(1, '#ffffff');
    ctx.fillStyle = textGrad;
    ctx.fillText(meta.badgeText, cx, badgeY);

    ctx.restore();
  }

  // --- 3D THREE.JS INTEGRATION ---

  // Erstellt die kleine Textur für Orbitalpartikel
  getParticleTexture() {
    if (this._particleTex) return this._particleTex;
    const pCanvas = document.createElement('canvas');
    pCanvas.width = 64;
    pCanvas.height = 64;
    const pCtx = pCanvas.getContext('2d');
    const grad = pCtx.createRadialGradient(32, 32, 0, 32, 32, 30);
    grad.addColorStop(0, '#ffffff');
    grad.addColorStop(0.35, 'rgba(255,255,255,0.9)');
    grad.addColorStop(0.7, 'rgba(255,255,255,0.3)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    pCtx.fillStyle = grad;
    pCtx.beginPath();
    pCtx.arc(32, 32, 30, 0, Math.PI * 2);
    pCtx.fill();

    this._particleTex = new THREE.CanvasTexture(pCanvas);
    this._particleTex.minFilter = THREE.LinearFilter;
    this._particleTex.magFilter = THREE.LinearFilter;
    return this._particleTex;
  }

  // Erzeugt das gesamte 3D-Emblem-Objekt (Sprite + optionale Orbit-Partikel)
  createEmblemGroup(rank, opts = {}) {
    const meta = this.getRankMeta(rank);
    const texture = this.getOrCreateTexture(meta.tag);

    const group = new THREE.Group();
    group.name = `teamEmblem_${meta.tag}`;

    // Haupt-Sprite mit depthTest = false, damit es niemals von Helmen oder Waffen verdeckt wird
    const mat = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
      depthWrite: false,
    });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(1.45, 1.45, 1);
    sprite.layers.set(1);
    group.add(sprite);

    // Optionale feine Orbit-Partikel für höhere Ränge (SA, GA, GM, DEV, TM, SGA)
    let particleGroup = null;
    if (meta.hasParticles) {
      particleGroup = new THREE.Group();
      const pCount = 8;
      const pTex = this.getParticleTexture();
      const pMat = new THREE.SpriteMaterial({
        map: pTex,
        color: meta.particleHex,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthTest: false,
        depthWrite: false,
      });

      for (let i = 0; i < pCount; i++) {
        const pSprite = new THREE.Sprite(pMat.clone());
        const angle = (i / pCount) * Math.PI * 2;
        const radius = 0.55 + (i % 3) * 0.12;
        pSprite.position.set(Math.cos(angle) * radius, (Math.sin(angle * 2) * 0.18), Math.sin(angle) * radius);
        pSprite.scale.set(0.12, 0.12, 1);
        pSprite.userData = {
          baseAngle: angle,
          radius,
          speed: 0.85 + (i % 2) * 0.45,
          yOffset: (i % 4 - 2) * 0.08,
        };
        particleGroup.add(pSprite);
      }
      group.add(particleGroup);
    }

    group.userData = {
      rank: meta.tag,
      isLocal: Boolean(opts.isLocal),
      baseY: 3.75,
      seed: Math.random() * Math.PI * 2,
      sprite,
      particleGroup,
    };

    this.activeGroups.add(group);
    return group;
  }

  // Entfernt eine Gruppe aus der aktiven Update-Liste
  destroyEmblemGroup(group) {
    if (!group) return;
    this.activeGroups.delete(group);
    if (group.parent) {
      group.parent.remove(group);
    }
    if (group.userData?.sprite?.material) {
      group.userData.sprite.material.dispose();
    }
  }

  // Animation & Distanzskalierungs-Update (wird 60 FPS in OpenWorld3D.animate() aufgerufen)
  update(dt, elapsed, engine) {
    if (!this.activeGroups || this.activeGroups.size === 0) return;

    const showEmblems = engine.showTeamEmblems !== false;
    const showGlow = engine.showTeamGlow !== false;
    const showParticles = engine.showTeamParticles !== false;
    const camDist = engine.cameraDistance || 13.5;
    const camPos = engine.camera?.position;

    for (const group of this.activeGroups) {
      if (!group || !group.parent) {
        this.activeGroups.delete(group);
        continue;
      }

      // Globale Sichtbarkeitsprüfung
      if (!showEmblems) {
        group.visible = false;
        continue;
      }

      const ud = group.userData;
      const sprite = ud.sprite;
      const pGroup = ud.particleGroup;

      // 1. Sanfte Schweb-Animation (Floating Bobbing)
      const bob = Math.sin(elapsed * 1.6 + ud.seed) * 0.05;
      group.position.y = (ud.baseY || 3.82) + bob;

      // 2. Pulsierender Leuchteffekt
      if (sprite?.material) {
        if (showGlow) {
          sprite.material.opacity = 0.88 + Math.sin(elapsed * 2.2 + ud.seed) * 0.12;
        } else {
          sprite.material.opacity = 1.0;
        }
      }

      // 3. Orbitierende Energiepartikel aktualisieren
      if (pGroup) {
        if (showParticles) {
          pGroup.visible = true;
          for (let i = 0; i < pGroup.children.length; i++) {
            const p = pGroup.children[i];
            const pud = p.userData;
            const curAngle = pud.baseAngle + elapsed * pud.speed;
            p.position.x = Math.cos(curAngle) * pud.radius;
            p.position.z = Math.sin(curAngle) * pud.radius;
            p.position.y = pud.yOffset + Math.sin(elapsed * 2.5 + pud.baseAngle) * 0.12;
            p.material.opacity = 0.55 + Math.sin(elapsed * 3.5 + pud.baseAngle) * 0.40;
          }
        } else {
          pGroup.visible = false;
        }
      }

      // 4. Dynamische Kamera- & Distanz-Skalierung
      if (sprite) {
        let zoomFactor = 1.0;
        if (ud.isLocal) {
          zoomFactor = 0.38 * Math.min(1.0, Math.max(0.42, camDist / 13.5));
        } else if (camPos) {
          const distToCam = camPos.distanceTo(group.parent.position);
          zoomFactor = 0.38 * Math.min(1.25, Math.max(0.42, distToCam / 14.0));
        }
        const sW = zoomFactor * 4.2;
        const sH = zoomFactor * 4.2;
        sprite.scale.set(sW, sH, 1);
      }
    }
  }
}
