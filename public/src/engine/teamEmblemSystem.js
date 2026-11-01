// ============================================================================
// AERYNDOR: AGE OF LEGENDS – HIGH-DEFINITION TEAM & GAMEMASTER INSIGNIA SYSTEM
// ============================================================================
// Dezente, hochauflösende 3D-Überkopf-Insignien (1024x1024 Supersampled Vector
// Canvas + Trilinear Mipmaps + Anisotropic Filtering):
//  - Feingliedriges heraldisches Metall-Relief ohne klobige Außenringe
//  - Dezenter atmosphärischer Halo & sanfter Spekular-Schimmer
//  - Feine Sternenstaub-Mikropartikel & kompakte Welt-Skalierung
// ============================================================================

import * as THREE from '../../vendor/three.module.js';

export const TEAM_RANK_METADATA = {
  SA: {
    tag: 'SA',
    title: 'SERVER ADMINISTRATOR',
    primaryColor: '#fde047',
    secondaryColor: '#d97706',
    metalLight: '#fffbeb',
    metalMid: '#eab308',
    metalDark: '#78350f',
    coreTop: '#241607',
    coreBottom: '#0e0803',
    glowColor: 'rgba(250, 204, 21, 0.24)',
    accentHex: '#fef08a',
    particleHex: 0xfde68a,
    hasParticles: true,
    hasWings: true,
    hasCrown: true,
  },
  SGA: {
    tag: 'SGA',
    title: 'SENIOR GAME ADMIN',
    primaryColor: '#60a5fa',
    secondaryColor: '#f59e0b',
    metalLight: '#fef9c3',
    metalMid: '#60a5fa',
    metalDark: '#1e3a8a',
    coreTop: '#102347',
    coreBottom: '#070f21',
    glowColor: 'rgba(96, 165, 250, 0.22)',
    accentHex: '#fde047',
    particleHex: 0x93c5fd,
    hasParticles: true,
    hasWings: true,
    hasCrown: true,
  },
  GA: {
    tag: 'GA',
    title: 'GAME ADMINISTRATOR',
    primaryColor: '#60a5fa',
    secondaryColor: '#cbd5e1',
    metalLight: '#f8fafc',
    metalMid: '#60a5fa',
    metalDark: '#1e3a8a',
    coreTop: '#0f2142',
    coreBottom: '#060d1c',
    glowColor: 'rgba(96, 165, 250, 0.20)',
    accentHex: '#bae6fd',
    particleHex: 0x93c5fd,
    hasParticles: true,
    hasWings: true,
    hasCrown: false,
  },
  TM: {
    tag: 'TM',
    title: 'TEAM MANAGER',
    primaryColor: '#c084fc',
    secondaryColor: '#fbbf24',
    metalLight: '#faf5ff',
    metalMid: '#c084fc',
    metalDark: '#581c87',
    coreTop: '#26103d',
    coreBottom: '#10061c',
    glowColor: 'rgba(192, 132, 252, 0.21)',
    accentHex: '#fde68a',
    particleHex: 0xd8b4fe,
    hasParticles: true,
    hasWings: true,
    hasCrown: false,
  },
  CM: {
    tag: 'CM',
    title: 'COMMUNITY MANAGER',
    primaryColor: '#fb7185',
    secondaryColor: '#fda4af',
    metalLight: '#fff1f2',
    metalMid: '#fb7185',
    metalDark: '#881337',
    coreTop: '#330d19',
    coreBottom: '#14040a',
    glowColor: 'rgba(251, 113, 133, 0.20)',
    accentHex: '#fecdd3',
    particleHex: 0xfda4af,
    hasParticles: true,
    hasWings: false,
    hasCrown: false,
  },
  SGM: {
    tag: 'SGM',
    title: 'SUPER GAME MASTER',
    primaryColor: '#38bdf8',
    secondaryColor: '#e0f2fe',
    metalLight: '#f0f9ff',
    metalMid: '#38bdf8',
    metalDark: '#0c4a6e',
    coreTop: '#09283c',
    coreBottom: '#03111c',
    glowColor: 'rgba(56, 189, 248, 0.22)',
    accentHex: '#bae6fd',
    particleHex: 0x7dd3fc,
    hasParticles: true,
    hasWings: true,
    hasCrown: false,
  },
  GM: {
    tag: 'GM',
    title: 'GAME MASTER',
    primaryColor: '#22d3ee',
    secondaryColor: '#cffafe',
    metalLight: '#ecfeff',
    metalMid: '#22d3ee',
    metalDark: '#155e75',
    coreTop: '#082633',
    coreBottom: '#031017',
    glowColor: 'rgba(34, 211, 238, 0.22)',
    accentHex: '#a5f3fc',
    particleHex: 0x67e8f9,
    hasParticles: true,
    hasWings: true,
    hasCrown: false,
  },
  TGM: {
    tag: 'TGM',
    title: 'TRIAL GAME MASTER',
    primaryColor: '#2dd4bf',
    secondaryColor: '#99f6e4',
    metalLight: '#f0fdfa',
    metalMid: '#2dd4bf',
    metalDark: '#115e59',
    coreTop: '#072926',
    coreBottom: '#021210',
    glowColor: 'rgba(45, 212, 191, 0.18)',
    accentHex: '#99f6e4',
    particleHex: 0x5eead4,
    hasParticles: false,
    hasWings: false,
    hasCrown: false,
  },
  JGM: {
    tag: 'JGM',
    title: 'JUNIOR GAME MASTER',
    primaryColor: '#38bdf8',
    secondaryColor: '#bae6fd',
    metalLight: '#f0f9ff',
    metalMid: '#38bdf8',
    metalDark: '#075985',
    coreTop: '#082336',
    coreBottom: '#030f18',
    glowColor: 'rgba(56, 189, 248, 0.18)',
    accentHex: '#bae6fd',
    particleHex: 0x7dd3fc,
    hasParticles: false,
    hasWings: false,
    hasCrown: false,
  },
  DEV: {
    tag: 'DEV',
    title: 'DEVELOPER',
    primaryColor: '#a855f7',
    secondaryColor: '#f0abfc',
    metalLight: '#faf5ff',
    metalMid: '#a855f7',
    metalDark: '#4c1d95',
    coreTop: '#210c3d',
    coreBottom: '#0c0418',
    glowColor: 'rgba(168, 85, 247, 0.22)',
    accentHex: '#e9d5ff',
    particleHex: 0xd8b4fe,
    hasParticles: true,
    hasWings: true,
    hasCrown: false,
  },
  EM: {
    tag: 'EM',
    title: 'EVENT MANAGER',
    primaryColor: '#fb923c',
    secondaryColor: '#fde047',
    metalLight: '#fff7ed',
    metalMid: '#f97316',
    metalDark: '#7c2d12',
    coreTop: '#2e1307',
    coreBottom: '#130702',
    glowColor: 'rgba(249, 115, 22, 0.20)',
    accentHex: '#fed7aa',
    particleHex: 0xfdba74,
    hasParticles: true,
    hasWings: false,
    hasCrown: false,
  },
  SUP: {
    tag: 'SUP',
    title: 'SUPPORT',
    primaryColor: '#34d399',
    secondaryColor: '#a7f3d0',
    metalLight: '#ecfdf5',
    metalMid: '#10b981',
    metalDark: '#065f46',
    coreTop: '#06291f',
    coreBottom: '#02120d',
    glowColor: 'rgba(52, 211, 153, 0.18)',
    accentHex: '#a7f3d0',
    particleHex: 0x6ee7b7,
    hasParticles: false,
    hasWings: false,
    hasCrown: false,
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

  // Liefert eine 1024x1024 Supersampled CanvasTexture mit Trilinear-Mipmapping
  getOrCreateTexture(rank) {
    const meta = this.getRankMeta(rank);
    const cacheKey = `${meta.tag}_hd1024_v3`;
    if (this.textureCache.has(cacheKey)) {
      return this.textureCache.get(cacheKey);
    }

    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 1024;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 2x Retina-Supersampling auf logischem 512x512 Koordinatenraum
    ctx.save();
    ctx.scale(2, 2);
    this.drawEmblem(ctx, meta);
    ctx.restore();

    const texture = new THREE.CanvasTexture(canvas);
    texture.generateMipmaps = true;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.anisotropy = 8;
    if (THREE.SRGBColorSpace) {
      texture.colorSpace = THREE.SRGBColorSpace;
    }

    this.textureCache.set(cacheKey, texture);
    return texture;
  }

  drawEmblem(ctx, meta) {
    const cx = 256;
    const cy = 258;

    ctx.save();
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    // 1. Dezenter, eng fokussierter Hintergrund-Halo (kein großflächiger Nebelkreis!)
    const auraRadius = 165;
    const auraGrad = ctx.createRadialGradient(cx, cy - 4, 12, cx, cy - 4, auraRadius);
    auraGrad.addColorStop(0, meta.glowColor);
    auraGrad.addColorStop(0.48, meta.glowColor.replace(/[\d.]+\)$/, '0.08)'));
    auraGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = auraGrad;
    ctx.beginPath();
    ctx.arc(cx, cy - 4, auraRadius, 0, Math.PI * 2);
    ctx.fill();

    // 2. Feiner, dezenter Filigran-Bogen (statt klobigem gestricheltem Außenring)
    this.drawSubtleFiligreeArcs(ctx, cx, cy - 2, meta);

    // 3. Schlanke, mehrschichtige Metall-Schwingen für höhere Ränge (SA, GM, GA, SGA, SGM, DEV, TM)
    if (meta.hasWings) {
      this.drawSculptedWings(ctx, cx, cy + 4, meta);
    }

    // 4. Facettiertes Heraldisches Wappenschild / Kristall-Medaillon
    this.drawFacetedCrestShield(ctx, cx, cy + 2, meta);

    // 5. Krone (SA / SGA) oder feines Kristall-Sternsiegel (GM / GA / etc.)
    if (meta.hasCrown) {
      this.drawRoyalCrown(ctx, cx, cy - 28, meta);
    } else {
      this.drawStarFinial(ctx, cx, cy - 38, meta);
    }

    // 6. Hochauflösendes, gestochen scharfes Rang-Monogramm
    this.drawCrispMonogram(ctx, cx, meta.hasCrown ? cy + 36 : cy + 16, meta);

    ctx.restore();
  }

  drawSubtleFiligreeArcs(ctx, cx, cy, meta) {
    ctx.save();

    // Zwei zarte seitliche Filigran-Bögen (oben und unten offen -> kein Überlappen mit Gildenname!)
    const rOuter = 136;
    const rInner = 128;

    ctx.strokeStyle = meta.glowColor.replace(/[\d.]+\)$/, '0.36)');
    ctx.lineWidth = 1.25;
    // Linker & rechter eleganter Sichelbogen
    ctx.beginPath();
    ctx.arc(cx, cy, rOuter, -0.78, 0.72);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, rOuter, Math.PI - 0.72, Math.PI + 0.78);
    ctx.stroke();

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)';
    ctx.lineWidth = 0.85;
    ctx.beginPath();
    ctx.arc(cx, cy, rInner, -0.58, 0.54);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, rInner, Math.PI - 0.54, Math.PI + 0.58);
    ctx.stroke();

    // Dezenter kleiner oberer Zenith-Diamant
    ctx.save();
    ctx.translate(cx, cy - 126);
    ctx.fillStyle = meta.metalLight;
    ctx.shadowColor = meta.primaryColor;
    ctx.shadowBlur = 5;
    ctx.beginPath();
    ctx.moveTo(0, -5.5);
    ctx.lineTo(3.6, 0);
    ctx.lineTo(0, 5.5);
    ctx.lineTo(-3.6, 0);
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    ctx.restore();
  }

  drawSculptedWings(ctx, cx, cy, meta) {
    const drawSide = (dir) => {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.scale(dir, 1);

      // 4 schlanke, scharf geschnittene Metall-Schwingenfedern pro Seite
      const feathers = [
        // [startX, startY, cp1X, cp1Y, cp2X, cp2Y, tipX, tipY, backCpX, backCpY, endX, endY]
        [52, -24, 96, -82, 148, -94, 186, -64, 148, -32, 62, -4],
        [56, -4, 104, -44, 152, -46, 176, -20, 140, 2, 62, 12],
        [56, 12, 98, -10, 138, -6, 156, 16, 124, 30, 58, 28],
        [52, 26, 86, 18, 118, 26, 130, 44, 102, 50, 50, 42],
      ];

      for (let i = 0; i < feathers.length; i++) {
        const f = feathers[i];
        const grad = ctx.createLinearGradient(f[0], f[3], f[6], f[11]);
        grad.addColorStop(0, meta.metalLight);
        grad.addColorStop(0.28, meta.primaryColor);
        grad.addColorStop(0.72, meta.metalMid);
        grad.addColorStop(1, meta.metalDark);

        ctx.save();
        ctx.shadowColor = 'rgba(0, 0, 0, 0.72)';
        ctx.shadowBlur = 8;
        ctx.shadowOffsetY = 2;

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(f[0], f[1]);
        ctx.bezierCurveTo(f[2], f[3], f[4], f[5], f[6], f[7]);
        ctx.quadraticCurveTo(f[8], f[9], f[10], f[11]);
        ctx.closePath();
        ctx.fill();
        ctx.restore();

        // Feine metallische Glanzkante statt dicker weißer Cartoon-Kontur
        ctx.strokeStyle = i === 0 ? 'rgba(255, 255, 255, 0.78)' : 'rgba(255, 255, 255, 0.48)';
        ctx.lineWidth = i === 0 ? 1.15 : 0.85;
        ctx.stroke();

        // Feine Innengravur-Linie entlang der Federachse
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.32)';
        ctx.lineWidth = 0.7;
        ctx.beginPath();
        ctx.moveTo(f[0] + 8, (f[1] + f[11]) * 0.5);
        ctx.quadraticCurveTo((f[2] + f[8]) * 0.5, (f[3] + f[9]) * 0.5, f[6] - 10, f[7] + 3);
        ctx.stroke();
      }

      ctx.restore();
    };

    drawSide(1);
    drawSide(-1);
  }

  drawFacetedCrestShield(ctx, cx, cy, meta) {
    ctx.save();

    // Edle schlanke Wappenschild-Silhouette
    const traceShield = (scale) => {
      const wTop = 70 * scale;
      const wMid = 76 * scale;
      const wLow = 56 * scale;
      const yTop = -86 * scale;
      const yShoulder = -56 * scale;
      const yWaist = 18 * scale;
      const yTip = 96 * scale;

      ctx.beginPath();
      ctx.moveTo(cx, cy + yTop);
      ctx.lineTo(cx + wTop, cy + yShoulder);
      ctx.quadraticCurveTo(cx + wMid, cy - 12 * scale, cx + wLow, cy + yWaist);
      ctx.quadraticCurveTo(cx + 32 * scale, cy + 66 * scale, cx, cy + yTip);
      ctx.quadraticCurveTo(cx - 32 * scale, cy + 66 * scale, cx - wLow, cy + yWaist);
      ctx.quadraticCurveTo(cx - wMid, cy - 12 * scale, cx - wTop, cy + yShoulder);
      ctx.closePath();
    };

    // Äußerer Metallrahmen mit weichem Tiefenschatten
    const frameGrad = ctx.createLinearGradient(cx - 72, cy - 88, cx + 72, cy + 96);
    frameGrad.addColorStop(0, meta.metalLight);
    frameGrad.addColorStop(0.24, meta.primaryColor);
    frameGrad.addColorStop(0.62, meta.metalMid);
    frameGrad.addColorStop(1, meta.metalDark);

    ctx.save();
    ctx.shadowColor = 'rgba(0, 0, 0, 0.82)';
    ctx.shadowBlur = 14;
    ctx.shadowOffsetY = 3;
    traceShield(1.0);
    ctx.fillStyle = frameGrad;
    ctx.fill();
    ctx.restore();

    // Feine Spekular-Außenkante
    traceShield(1.0);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.82)';
    ctx.lineWidth = 1.35;
    ctx.stroke();

    // Dunkler, tief-emaillierter Innenspiegel
    const coreGrad = ctx.createLinearGradient(cx, cy - 74, cx, cy + 84);
    coreGrad.addColorStop(0, meta.coreTop);
    coreGrad.addColorStop(0.55, meta.coreBottom);
    coreGrad.addColorStop(1, '#040508');

    traceShield(0.84);
    ctx.fillStyle = coreGrad;
    ctx.fill();

    // Subtiler diagonaler Kristall-Glanz im Schildinneren
    ctx.save();
    traceShield(0.84);
    ctx.clip();
    const sheenGrad = ctx.createLinearGradient(cx - 65, cy - 75, cx + 35, cy + 25);
    sheenGrad.addColorStop(0, 'rgba(255, 255, 255, 0.14)');
    sheenGrad.addColorStop(0.45, 'rgba(255, 255, 255, 0.03)');
    sheenGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = sheenGrad;
    ctx.fillRect(cx - 80, cy - 90, 160, 180);
    ctx.restore();

    // Haarfeine metallische Innenfassung
    traceShield(0.84);
    ctx.strokeStyle = meta.primaryColor;
    ctx.lineWidth = 1.2;
    ctx.stroke();

    // Untere kleine Zier-Raute im Schildfuß
    ctx.fillStyle = meta.accentHex;
    ctx.beginPath();
    ctx.moveTo(cx, cy + 64);
    ctx.lineTo(cx + 4, cy + 70);
    ctx.lineTo(cx, cy + 76);
    ctx.lineTo(cx - 4, cy + 70);
    ctx.closePath();
    ctx.fill();

    ctx.restore();
  }

  drawRoyalCrown(ctx, cx, cy, meta) {
    ctx.save();

    const crownGrad = ctx.createLinearGradient(cx - 36, cy - 32, cx + 36, cy + 16);
    crownGrad.addColorStop(0, meta.metalLight);
    crownGrad.addColorStop(0.32, meta.primaryColor);
    crownGrad.addColorStop(0.75, meta.metalMid);
    crownGrad.addColorStop(1, meta.metalDark);

    ctx.shadowColor = 'rgba(0, 0, 0, 0.75)';
    ctx.shadowBlur = 6;
    ctx.shadowOffsetY = 1.5;

    ctx.fillStyle = crownGrad;
    ctx.beginPath();
    ctx.moveTo(cx - 34, cy + 12);
    ctx.lineTo(cx - 38, cy - 14);
    ctx.lineTo(cx - 19, cy - 2);
    ctx.lineTo(cx - 20, cy - 26);
    ctx.lineTo(cx - 6, cy - 7);
    ctx.lineTo(cx, cy - 36);
    ctx.lineTo(cx + 6, cy - 7);
    ctx.lineTo(cx + 20, cy - 26);
    ctx.lineTo(cx + 19, cy - 2);
    ctx.lineTo(cx + 38, cy - 14);
    ctx.lineTo(cx + 34, cy + 12);
    ctx.closePath();
    ctx.fill();

    ctx.shadowBlur = 0;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.85)';
    ctx.lineWidth = 1.1;
    ctx.stroke();

    // Feiner Kronenreif
    ctx.fillStyle = meta.coreBottom;
    ctx.fillRect(cx - 30, cy + 5, 60, 6);
    ctx.strokeStyle = meta.accentHex;
    ctx.lineWidth = 0.9;
    ctx.strokeRect(cx - 30, cy + 5, 60, 6);

    // Dezente Edelstein-Punkte
    const drawTinyGem = (gx, gy, r, col) => {
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.arc(gx, gy, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 0.7;
      ctx.stroke();
    };

    drawTinyGem(cx, cy - 36, 3.2, '#e0f2fe');
    drawTinyGem(cx - 20, cy - 26, 2.4, '#fda4af');
    drawTinyGem(cx + 20, cy - 26, 2.4, '#fda4af');
    drawTinyGem(cx, cy + 8, 2.2, '#fda4af');

    // Feine horizontale Trennlinie unter der Krone
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.28)';
    ctx.lineWidth = 0.9;
    ctx.beginPath();
    ctx.moveTo(cx - 34, cy + 20);
    ctx.lineTo(cx + 34, cy + 20);
    ctx.stroke();

    ctx.restore();
  }

  drawStarFinial(ctx, cx, cy, meta) {
    ctx.save();
    ctx.translate(cx, cy);

    const starGrad = ctx.createLinearGradient(-16, -16, 16, 16);
    starGrad.addColorStop(0, '#ffffff');
    starGrad.addColorStop(0.45, meta.accentHex);
    starGrad.addColorStop(1, meta.primaryColor);

    ctx.shadowColor = meta.primaryColor;
    ctx.shadowBlur = 8;
    ctx.fillStyle = starGrad;

    // 4-spitziger arkaner Nordstern
    ctx.beginPath();
    ctx.moveTo(0, -18);
    ctx.lineTo(4.5, -4.5);
    ctx.lineTo(18, 0);
    ctx.lineTo(4.5, 4.5);
    ctx.lineTo(0, 18);
    ctx.lineTo(-4.5, 4.5);
    ctx.lineTo(-18, 0);
    ctx.lineTo(-4.5, -4.5);
    ctx.closePath();
    ctx.fill();

    ctx.shadowBlur = 0;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.85)';
    ctx.lineWidth = 0.9;
    ctx.stroke();

    // Feine horizontale Filigran-Linie unter dem Stern
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.26)';
    ctx.lineWidth = 0.9;
    ctx.beginPath();
    ctx.moveTo(-34, 24);
    ctx.lineTo(34, 24);
    ctx.stroke();

    ctx.restore();
  }

  drawCrispMonogram(ctx, cx, cy, meta) {
    ctx.save();
    const tag = meta.tag;
    const fontSize = tag.length >= 3 ? 28 : 35;
    ctx.font = `800 ${fontSize}px "Cinzel", "Georgia", "Times New Roman", serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // Scharfe dunkle Relief-Kontur für perfekte Lesbarkeit aus jeder Distanz
    ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
    ctx.shadowBlur = 5;
    ctx.shadowOffsetY = 2;
    ctx.strokeStyle = 'rgba(5, 8, 15, 0.95)';
    ctx.lineWidth = 4.2;
    ctx.strokeText(tag, cx, cy);

    ctx.shadowColor = meta.primaryColor;
    ctx.shadowBlur = 6;
    ctx.shadowOffsetY = 0;

    const txtGrad = ctx.createLinearGradient(cx, cy - fontSize * 0.5, cx, cy + fontSize * 0.5);
    txtGrad.addColorStop(0, '#ffffff');
    txtGrad.addColorStop(0.38, meta.accentHex);
    txtGrad.addColorStop(0.82, meta.primaryColor);
    txtGrad.addColorStop(1, meta.metalMid);

    ctx.fillStyle = txtGrad;
    ctx.fillText(tag, cx, cy);

    ctx.restore();
  }

  // --- 3D THREE.JS INTEGRATION ---

  getParticleTexture() {
    if (this._particleTex) return this._particleTex;
    const pCanvas = document.createElement('canvas');
    pCanvas.width = 64;
    pCanvas.height = 64;
    const pCtx = pCanvas.getContext('2d');

    // Feiner, weicher Sternenfunken statt großem rundem Blob
    const grad = pCtx.createRadialGradient(32, 32, 0, 32, 32, 28);
    grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
    grad.addColorStop(0.22, 'rgba(255, 255, 255, 0.75)');
    grad.addColorStop(0.55, 'rgba(255, 255, 255, 0.16)');
    grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
    pCtx.fillStyle = grad;
    pCtx.beginPath();
    pCtx.arc(32, 32, 28, 0, Math.PI * 2);
    pCtx.fill();

    this._particleTex = new THREE.CanvasTexture(pCanvas);
    this._particleTex.minFilter = THREE.LinearFilter;
    this._particleTex.magFilter = THREE.LinearFilter;
    return this._particleTex;
  }

  createEmblemGroup(rank, opts = {}) {
    const meta = this.getRankMeta(rank);
    const texture = this.getOrCreateTexture(meta.tag);

    const group = new THREE.Group();
    group.name = `teamEmblem_${meta.tag}`;

    const mat = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
      depthWrite: false,
    });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(0.82, 0.82, 1);
    sprite.layers.set(1);
    group.add(sprite);

    // Dezente, feine Sternenstaub-Mikropartikel
    let particleGroup = null;
    if (meta.hasParticles) {
      particleGroup = new THREE.Group();
      const pCount = 5;
      const pTex = this.getParticleTexture();
      const pMat = new THREE.SpriteMaterial({
        map: pTex,
        color: meta.particleHex,
        transparent: true,
        opacity: 0.3,
        blending: THREE.AdditiveBlending,
        depthTest: false,
        depthWrite: false,
      });

      for (let i = 0; i < pCount; i++) {
        const pSprite = new THREE.Sprite(pMat.clone());
        const angle = (i / pCount) * Math.PI * 2;
        const radius = 0.25 + (i % 2) * 0.05;
        pSprite.position.set(
          Math.cos(angle) * radius,
          Math.sin(angle * 2) * 0.07,
          Math.sin(angle) * radius
        );
        pSprite.scale.set(0.048, 0.048, 1);
        pSprite.layers.set(1);
        pSprite.userData = {
          baseAngle: angle,
          radius,
          speed: 0.42 + (i % 2) * 0.18,
          yOffset: ((i % 3) - 1) * 0.04,
        };
        particleGroup.add(pSprite);
      }
      group.add(particleGroup);
    }

    group.userData = {
      rank: meta.tag,
      isLocal: Boolean(opts.isLocal),
      baseY: 3.22,
      seed: Math.random() * Math.PI * 2,
      sprite,
      particleGroup,
      flashScaleMult: 1.0,
    };

    this.activeGroups.add(group);
    return group;
  }

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

  // Ruhige, dezente Schweb- & Edelmetall-Schimmer-Animation
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

      if (!showEmblems) {
        group.visible = false;
        continue;
      }

      const ud = group.userData;
      const sprite = ud.sprite;
      const pGroup = ud.particleGroup;

      // 1. Ruhiges, dezentes Schweben (inkl. harmonischem Nahzoom-Framing über dem Gildennamen)
      const localZoomRatio = ud.isLocal ? Math.min(1.0, Math.max(0.46, camDist / 13.5)) : 1.0;
      const zoomYOffset = ud.isLocal ? -(1.0 - localZoomRatio) * 0.22 : 0.0;
      const bob = Math.sin(elapsed * 1.25 + ud.seed) * 0.02;
      group.position.y = (ud.baseY || 3.22) + zoomYOffset + bob;

      // 2. Dezenter Spekular-Schimmer (kein grelles Blinken oder Pumpen)
      let flash = 0;
      if (sprite?.material) {
        if (showGlow) {
          const breathe = 0.95 + Math.sin(elapsed * 1.6 + ud.seed) * 0.03;
          const gleamPeriod = 4.6;
          const gleamPhase = ((elapsed + ud.seed * 0.5) % gleamPeriod) / gleamPeriod;
          if (gleamPhase < 0.18) {
            flash = Math.sin((gleamPhase / 0.18) * Math.PI);
          }

          sprite.material.opacity = Math.min(1.0, breathe + flash * 0.04);
          const brightness = 1.0 + flash * 0.12;
          sprite.material.color.setRGB(brightness, brightness, brightness);
          ud.flashScaleMult = 1.0 + flash * 0.014;
        } else {
          sprite.material.opacity = 0.96;
          sprite.material.color.setRGB(1.0, 1.0, 1.0);
          ud.flashScaleMult = 1.0;
        }
      }

      // 3. Feine, dezente Sternenstaub-Funken
      if (pGroup) {
        if (showParticles) {
          pGroup.visible = true;
          for (let i = 0; i < pGroup.children.length; i++) {
            const p = pGroup.children[i];
            const pud = p.userData;
            const curAngle = pud.baseAngle + elapsed * pud.speed;
            p.position.x = Math.cos(curAngle) * pud.radius;
            p.position.z = Math.sin(curAngle) * pud.radius;
            p.position.y = pud.yOffset + Math.sin(elapsed * 1.8 + pud.baseAngle) * 0.045;
            const baseOp = 0.18 + Math.sin(elapsed * 2.4 + pud.baseAngle * 1.7) * 0.12;
            p.material.opacity = Math.max(0.04, Math.min(0.45, baseOp + flash * 0.12));
          }
        } else {
          pGroup.visible = false;
        }
      }

      // 4. Kompakte, harmonische Distanzskalierung passend zum verfeinerten Nametag
      if (sprite) {
        let zoomFactor = 0.38;
        if (ud.isLocal) {
          zoomFactor = 0.38 * Math.min(1.0, Math.max(0.46, camDist / 13.5));
        } else if (camPos) {
          const distToCam = camPos.distanceTo(group.parent.position);
          zoomFactor = 0.38 * Math.min(1.18, Math.max(0.46, distToCam / 14.0));
        }
        const mult = ud.flashScaleMult || 1.0;
        const s = zoomFactor * 2.18 * mult;
        sprite.scale.set(s, s, 1);
      }
    }
  }
}
