// ============================================================================
// AERYNDOR: AGE OF LEGENDS – ADVANCED GAMEMASTER IDENTIFICATION SYSTEM
// ============================================================================
// Next-Generation Modern 3D Overhead Insignia & Team Emblems
// High-Definition Canvas 2D Vector Insignia (Full 512x512 Texture Detail)
// Features:
//  - Modern AAA MMORPG styling (Astrolabe rings, 3-tier heraldic wings, 3D metallic bevels)
//  - "Leicht Blinken": Periodischer Glanz-Aufblitz (Specular Gleam) & sanftes Atmen
//  - Dynamisches Farb- und Helligkeits-Overdrive für lebendigen Metall-Glanz
//  - Partikel-Synchronisation & Distanzskalierung
// ============================================================================

import * as THREE from '../../vendor/three.module.js';

export const TEAM_RANK_METADATA = {
  SA: {
    tag: 'SA',
    title: 'SERVER ADMINISTRATOR',
    primaryColor: '#ffd700',
    secondaryColor: '#f59e0b',
    glowColor: 'rgba(251, 191, 36, 0.90)',
    particleHex: 0xfbbf24,
    hasParticles: true,
  },
  SGA: {
    tag: 'SGA',
    title: 'SENIOR GAME ADMIN',
    primaryColor: '#3b82f6',
    secondaryColor: '#f59e0b',
    glowColor: 'rgba(59, 130, 246, 0.90)',
    particleHex: 0x3b82f6,
    hasParticles: true,
  },
  GA: {
    tag: 'GA',
    title: 'GAME ADMINISTRATOR',
    primaryColor: '#60a5fa',
    secondaryColor: '#e2e8f0',
    glowColor: 'rgba(59, 130, 246, 0.90)',
    particleHex: 0x60a5fa,
    hasParticles: true,
  },
  TM: {
    tag: 'TM',
    title: 'TEAM MANAGER',
    primaryColor: '#c084fc',
    secondaryColor: '#fbbf24',
    glowColor: 'rgba(168, 85, 247, 0.90)',
    particleHex: 0xc084fc,
    hasParticles: true,
  },
  CM: {
    tag: 'CM',
    title: 'COMMUNITY MANAGER',
    primaryColor: '#fb7185',
    secondaryColor: '#f43f5e',
    glowColor: 'rgba(244, 63, 94, 0.90)',
    particleHex: 0xfb7185,
    hasParticles: true,
  },
  SGM: {
    tag: 'SGM',
    title: 'SUPER GAME MASTER',
    primaryColor: '#38bdf8',
    secondaryColor: '#e2e8f0',
    glowColor: 'rgba(56, 189, 248, 0.90)',
    particleHex: 0x38bdf8,
    hasParticles: true,
  },
  GM: {
    tag: 'GM',
    title: 'GAME MASTER',
    primaryColor: '#22d3ee',
    secondaryColor: '#e0f2fe',
    glowColor: 'rgba(34, 211, 238, 0.95)',
    particleHex: 0x22d3ee,
    hasParticles: true,
  },
  TGM: {
    tag: 'TGM',
    title: 'TRIAL GAME MASTER',
    primaryColor: '#2dd4bf',
    secondaryColor: '#99f6e4',
    glowColor: 'rgba(45, 212, 191, 0.85)',
    particleHex: 0x2dd4bf,
    hasParticles: true,
  },
  JGM: {
    tag: 'JGM',
    title: 'JUNIOR GAME MASTER',
    primaryColor: '#38bdf8',
    secondaryColor: '#bae6fd',
    glowColor: 'rgba(56, 189, 248, 0.80)',
    particleHex: 0x38bdf8,
    hasParticles: false,
  },
  DEV: {
    tag: 'DEV',
    title: 'DEVELOPER',
    primaryColor: '#a855f7',
    secondaryColor: '#f472b6',
    glowColor: 'rgba(168, 85, 247, 0.95)',
    particleHex: 0xa855f7,
    hasParticles: true,
  },
  EM: {
    tag: 'EM',
    title: 'EVENT MANAGER',
    primaryColor: '#f97316',
    secondaryColor: '#fde047',
    glowColor: 'rgba(249, 115, 22, 0.90)',
    particleHex: 0xf97316,
    hasParticles: true,
  },
  SUP: {
    tag: 'SUP',
    title: 'SUPPORT',
    primaryColor: '#34d399',
    secondaryColor: '#ecfdf5',
    glowColor: 'rgba(52, 211, 153, 0.90)',
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

  // Liefert die gecachte CanvasTexture für einen Rang
  getOrCreateTexture(rank) {
    const meta = this.getRankMeta(rank);
    const cacheKey = `${meta.tag}_modern_v2`;
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

  // Zeichnet das vollständige moderne 2D-Canvas-Wappen
  drawEmblem(ctx, meta) {
    const cx = 256;
    const cy = 256;

    ctx.save();
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    // 1. Weicher atmosphärischer Hintergrund-Aura-Glow
    const auraRadius = 242;
    const auraGrad = ctx.createRadialGradient(cx, cy, 20, cx, cy, auraRadius);
    auraGrad.addColorStop(0, meta.glowColor);
    auraGrad.addColorStop(0.35, meta.glowColor.replace(/[\d\.]+\)$/, '0.45)'));
    auraGrad.addColorStop(0.70, meta.glowColor.replace(/[\d\.]+\)$/, '0.12)'));
    auraGrad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = auraGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, auraRadius, 0, Math.PI * 2);
    ctx.fill();

    // 2. Moderner äußerer Astrolabium-Runenring mit 4 Himmelsrichtungs-Diamanten
    this.drawModernAstrolabeRings(ctx, cx, cy, meta);

    // 3. Rang-spezifische 3D-Insignia-Geometrie
    switch (meta.tag) {
      case 'SA':
        this.drawModernServerAdminEmblem(ctx, cx, cy);
        break;
      case 'GA':
      case 'SGA':
        this.drawModernGameAdminEmblem(ctx, cx, cy, meta.tag === 'SGA');
        break;
      case 'GM':
      case 'SGM':
      case 'JGM':
        this.drawModernGameMasterEmblem(ctx, cx, cy, meta.tag);
        break;
      case 'TGM':
        this.drawModernTrialGameMasterEmblem(ctx, cx, cy);
        break;
      case 'SUP':
        this.drawModernSupportEmblem(ctx, cx, cy);
        break;
      case 'DEV':
        this.drawModernDeveloperEmblem(ctx, cx, cy);
        break;
      case 'TM':
        this.drawModernTeamManagerEmblem(ctx, cx, cy);
        break;
      case 'CM':
        this.drawModernCommunityManagerEmblem(ctx, cx, cy);
        break;
      default:
        this.drawModernGameMasterEmblem(ctx, cx, cy, 'GM');
        break;
    }

    ctx.restore();
  }

  // Moderner äußerer Astrolabium- / Runenring
  drawModernAstrolabeRings(ctx, cx, cy, meta) {
    ctx.save();

    // Äußerer dünner Präzisionsring
    ctx.strokeStyle = meta.glowColor.replace(/[\d\.]+\)$/, '0.55)');
    ctx.lineWidth = 2.0;
    ctx.beginPath();
    ctx.arc(cx, cy, 218, 0, Math.PI * 2);
    ctx.stroke();

    // Zweiter gestrichelter Runen-Segmentring
    ctx.save();
    ctx.setLineDash([8, 8]);
    ctx.strokeStyle = meta.glowColor.replace(/[\d\.]+\)$/, '0.40)');
    ctx.lineWidth = 3.0;
    ctx.beginPath();
    ctx.arc(cx, cy, 206, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();

    // Dritter Innenring mit feinen radialen Grad-Teilstrichen
    ctx.strokeStyle = 'rgba(255,255,255,0.45)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, 194, 0, Math.PI * 2);
    ctx.stroke();

    for (let i = 0; i < 32; i++) {
      const a = (i * Math.PI * 2) / 32;
      const rInner = i % 4 === 0 ? 186 : 190;
      const rOuter = 194;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a) * rInner, cy + Math.sin(a) * rInner);
      ctx.lineTo(cx + Math.cos(a) * rOuter, cy + Math.sin(a) * rOuter);
      ctx.stroke();
    }

    // 4 Kardinal-Diamantprismen an den 4 Himmelsrichtungen
    const drawCardinalDiamond = (x, y) => {
      ctx.save();
      ctx.translate(x, y);
      ctx.fillStyle = '#ffffff';
      ctx.shadowColor = meta.primaryColor;
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.moveTo(0, -9);
      ctx.lineTo(6, 0);
      ctx.lineTo(0, 9);
      ctx.lineTo(-6, 0);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = meta.primaryColor;
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.restore();
    };

    drawCardinalDiamond(cx, cy - 218); // Oben
    drawCardinalDiamond(cx + 218, cy); // Rechts
    drawCardinalDiamond(cx, cy + 218); // Unten
    drawCardinalDiamond(cx - 218, cy); // Links

    ctx.restore();
  }

  // =========================================================================
  // [SA] SERVER ADMINISTRATOR – Modernes Goldenes Kaiser-Insignia mit Krone
  // =========================================================================
  drawModernServerAdminEmblem(ctx, cx, cy) {
    ctx.save();

    // 1. Dreischichtige goldene Engelsflügel (Layered Wing Blades)
    const drawGoldWing = (side) => {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.scale(side, 1);

      // Große Hauptfeder (Außen)
      const g1 = ctx.createLinearGradient(30, -140, 220, 20);
      g1.addColorStop(0, '#fffbeb');
      g1.addColorStop(0.2, '#fde047');
      g1.addColorStop(0.65, '#d97706');
      g1.addColorStop(1, '#78350f');

      ctx.fillStyle = g1;
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2.5;

      ctx.beginPath();
      ctx.moveTo(40, -10);
      ctx.bezierCurveTo(90, -110, 180, -120, 215, -45);
      ctx.bezierCurveTo(185, -10, 130, 25, 45, 40);
      ctx.bezierCurveTo(105, 5, 115, -60, 40, -10);
      ctx.closePath();
      ctx.shadowColor = 'rgba(0,0,0,0.85)';
      ctx.shadowBlur = 14;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.stroke();

      // Sekundärfeder (Mitte)
      const g2 = ctx.createLinearGradient(40, -20, 195, 60);
      g2.addColorStop(0, '#fef08a');
      g2.addColorStop(0.4, '#eab308');
      g2.addColorStop(1, '#92400e');
      ctx.fillStyle = g2;

      ctx.beginPath();
      ctx.moveTo(45, 15);
      ctx.bezierCurveTo(100, -25, 175, -15, 192, 35);
      ctx.bezierCurveTo(155, 55, 105, 65, 45, 58);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Tertiärfeder (Unten/Innen)
      ctx.beginPath();
      ctx.moveTo(45, 50);
      ctx.bezierCurveTo(95, 40, 150, 60, 160, 95);
      ctx.bezierCurveTo(125, 105, 80, 100, 42, 85);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Leuchtende goldene Energielinie entlang der Hauptfeder
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2.0;
      ctx.shadowColor = '#fef08a';
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.moveTo(55, -8);
      ctx.bezierCurveTo(100, -85, 165, -95, 195, -42);
      ctx.stroke();
      ctx.shadowBlur = 0;

      ctx.restore();
    };

    drawGoldWing(1);
    drawGoldWing(-1);

    // 2. Zentrales 3D-Kaiserschild (Faceted Gold Shield Base)
    const shieldGrad = ctx.createLinearGradient(cx - 105, cy - 110, cx + 105, cy + 120);
    shieldGrad.addColorStop(0, '#ffffff');
    shieldGrad.addColorStop(0.25, '#fde047');
    shieldGrad.addColorStop(0.70, '#b45309');
    shieldGrad.addColorStop(1, '#451a03');

    ctx.beginPath();
    ctx.moveTo(cx, cy - 118);
    ctx.lineTo(cx + 98, cy - 65);
    ctx.lineTo(cx + 90, cy + 42);
    ctx.lineTo(cx, cy + 138);
    ctx.lineTo(cx - 90, cy + 42);
    ctx.lineTo(cx - 98, cy - 65);
    ctx.closePath();

    ctx.shadowColor = 'rgba(0,0,0,0.95)';
    ctx.shadowBlur = 18;
    ctx.fillStyle = shieldGrad;
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 4.5;
    ctx.stroke();

    // Innerer dunkel-kaiserlicher Schildspiegel mit Facettenschnitt
    ctx.beginPath();
    ctx.moveTo(cx, cy - 100);
    ctx.lineTo(cx + 78, cy - 54);
    ctx.lineTo(cx + 72, cy + 34);
    ctx.lineTo(cx, cy + 115);
    ctx.lineTo(cx - 72, cy + 34);
    ctx.lineTo(cx - 78, cy - 54);
    ctx.closePath();

    const innerGrad = ctx.createLinearGradient(cx, cy - 100, cx, cy + 115);
    innerGrad.addColorStop(0, '#291402');
    innerGrad.addColorStop(0.5, '#451a03');
    innerGrad.addColorStop(1, '#180901');
    ctx.fillStyle = innerGrad;
    ctx.fill();
    ctx.strokeStyle = '#fde047';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // 3. Majestätische 5-spitzige 3D-Krone mit Edelsteinen
    const crownY = cy - 20;
    const crownGrad = ctx.createLinearGradient(cx - 65, crownY - 65, cx + 65, crownY + 30);
    crownGrad.addColorStop(0, '#ffffff');
    crownGrad.addColorStop(0.28, '#fde047');
    crownGrad.addColorStop(0.75, '#d97706');
    crownGrad.addColorStop(1, '#78350f');

    ctx.fillStyle = crownGrad;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3.0;

    ctx.beginPath();
    ctx.moveTo(cx - 62, crownY + 22);
    ctx.lineTo(cx - 68, crownY - 32); // Linke äußere Zinne
    ctx.lineTo(cx - 34, crownY - 10);
    ctx.lineTo(cx - 38, crownY - 58); // Linke Zwischenzinne
    ctx.lineTo(cx, crownY - 20);
    ctx.lineTo(cx, crownY - 82); // Hohe Kaiserspitze mit Fleur-de-lis
    ctx.lineTo(cx, crownY - 20);
    ctx.lineTo(cx + 38, crownY - 58); // Rechte Zwischenzinne
    ctx.lineTo(cx + 34, crownY - 10);
    ctx.lineTo(cx + 68, crownY - 32); // Rechte äußere Zinne
    ctx.lineTo(cx + 62, crownY + 22);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Edelsteine an den Kronenspitzen (Zentraler Diamant & Rubine)
    const drawFacetGem = (gx, gy, rad, isDiamond) => {
      const gGrad = ctx.createRadialGradient(gx - rad * 0.35, gy - rad * 0.35, 1, gx, gy, rad);
      if (isDiamond) {
        gGrad.addColorStop(0, '#ffffff');
        gGrad.addColorStop(0.45, '#e0f2fe');
        gGrad.addColorStop(1, '#0284c7');
      } else {
        gGrad.addColorStop(0, '#ffe4e6');
        gGrad.addColorStop(0.40, '#f43f5e');
        gGrad.addColorStop(1, '#881337');
      }
      ctx.fillStyle = gGrad;
      ctx.beginPath();
      ctx.arc(gx, gy, rad, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    };

    drawFacetGem(cx, crownY - 82, 8.0, true); // Zentraler Hochdiamant
    drawFacetGem(cx - 38, crownY - 58, 6.0, false); // Rubin links
    drawFacetGem(cx + 38, crownY - 58, 6.0, false); // Rubin rechts
    drawFacetGem(cx - 68, crownY - 32, 4.8, true);
    drawFacetGem(cx + 68, crownY - 32, 4.8, true);

    // Kronenreif mit Edelstein-Intarsien
    ctx.fillStyle = '#291402';
    ctx.fillRect(cx - 52, crownY + 10, 104, 12);
    ctx.strokeStyle = '#fef08a';
    ctx.lineWidth = 2.0;
    ctx.strokeRect(cx - 52, crownY + 10, 104, 12);
    drawFacetGem(cx - 35, crownY + 16, 3.5, true);
    drawFacetGem(cx, crownY + 16, 4.5, false);
    drawFacetGem(cx + 35, crownY + 16, 3.5, true);

    // 4. Zentrales erhabenes "SA"-Zentralsiegel (3D-Gold-Prägung)
    ctx.save();
    ctx.font = '900 36px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 7;
    ctx.strokeText('SA', cx, cy + 62);

    const txtGrad = ctx.createLinearGradient(cx, cy + 42, cx, cy + 82);
    txtGrad.addColorStop(0, '#ffffff');
    txtGrad.addColorStop(0.35, '#fde047');
    txtGrad.addColorStop(1, '#b45309');
    ctx.fillStyle = txtGrad;
    ctx.shadowColor = '#f59e0b';
    ctx.shadowBlur = 14;
    ctx.fillText('SA', cx, cy + 62);
    ctx.shadowBlur = 0;
    ctx.restore();

    ctx.restore();
  }

  // =========================================================================
  // [GA] / [SGA] GAME ADMINISTRATOR – Moderner Paladin-Schild & Titanschwerter
  // =========================================================================
  drawModernGameAdminEmblem(ctx, cx, cy, isSGA = false) {
    ctx.save();

    // 1. Gekreuzte Breitschwerter aus Titan & Chrom mit Runenklingen
    const drawTitanSword = (angle) => {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(angle);

      const bladeG = ctx.createLinearGradient(-10, -180, 10, 180);
      bladeG.addColorStop(0, '#ffffff');
      bladeG.addColorStop(0.35, '#cbd5e1');
      bladeG.addColorStop(0.75, '#475569');
      bladeG.addColorStop(1, '#0f172a');

      ctx.fillStyle = bladeG;
      ctx.strokeStyle = isSGA ? '#fde047' : '#e2e8f0';
      ctx.lineWidth = 2.0;

      // Schwertklinge
      ctx.beginPath();
      ctx.moveTo(0, -195);
      ctx.lineTo(12, -172);
      ctx.lineTo(10, 105);
      ctx.lineTo(-10, 105);
      ctx.lineTo(-12, -172);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Leuchtende Hohlkehlen-Runenlinie
      ctx.strokeStyle = isSGA ? '#fde047' : '#38bdf8';
      ctx.lineWidth = 2.5;
      ctx.shadowColor = isSGA ? '#f59e0b' : '#0284c7';
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.moveTo(0, -180);
      ctx.lineTo(0, 95);
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Parierstange
      ctx.fillStyle = isSGA ? '#d97706' : '#334155';
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.fillRect(-30, 105, 60, 12);
      ctx.strokeRect(-30, 105, 60, 12);

      // Knauf
      ctx.beginPath();
      ctx.arc(0, 142, 9, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.restore();
    };

    drawTitanSword(Math.PI / 4);
    drawTitanSword(-Math.PI / 4);

    // 2. Äußerer Heaterschild mit dreifach facettiertem Silber/Gold-Rand
    const shieldGrad = ctx.createLinearGradient(cx - 105, cy - 110, cx + 105, cy + 130);
    if (isSGA) {
      shieldGrad.addColorStop(0, '#ffffff');
      shieldGrad.addColorStop(0.3, '#3b82f6');
      shieldGrad.addColorStop(0.7, '#1e3a8a');
      shieldGrad.addColorStop(1, '#d97706');
    } else {
      shieldGrad.addColorStop(0, '#ffffff');
      shieldGrad.addColorStop(0.25, '#cbd5e1');
      shieldGrad.addColorStop(0.65, '#334155');
      shieldGrad.addColorStop(1, '#020617');
    }

    ctx.beginPath();
    ctx.moveTo(cx - 102, cy - 105);
    ctx.lineTo(cx + 102, cy - 105);
    ctx.lineTo(cx + 102, cy + 22);
    ctx.bezierCurveTo(cx + 100, cy + 96, cx + 46, cy + 138, cx, cy + 158);
    ctx.bezierCurveTo(cx - 46, cy + 138, cx - 100, cy + 96, cx - 102, cy + 22);
    ctx.closePath();

    ctx.shadowColor = 'rgba(0,0,0,0.95)';
    ctx.shadowBlur = 18;
    ctx.fillStyle = shieldGrad;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = isSGA ? '#fde047' : '#ffffff';
    ctx.lineWidth = 4.5;
    ctx.stroke();

    // 3. Inneres tiefblaues Emaille-Feld mit Glanzkante
    ctx.beginPath();
    ctx.moveTo(cx - 80, cy - 86);
    ctx.lineTo(cx + 80, cy - 86);
    ctx.lineTo(cx + 80, cy + 18);
    ctx.bezierCurveTo(cx + 78, cy + 76, cx + 36, cy + 112, cx, cy + 132);
    ctx.bezierCurveTo(cx - 36, cy + 112, cx - 78, cy + 76, cx - 80, cy + 18);
    ctx.closePath();

    const blueGrad = ctx.createLinearGradient(cx, cy - 86, cx, cy + 132);
    blueGrad.addColorStop(0, '#2563eb');
    blueGrad.addColorStop(0.45, '#1e3a8a');
    blueGrad.addColorStop(1, '#09152e');
    ctx.fillStyle = blueGrad;
    ctx.fill();
    ctx.strokeStyle = isSGA ? '#fbbf24' : '#60a5fa';
    ctx.lineWidth = 3.0;
    ctx.stroke();

    // 4. Zentraler facettierter Saphir-Stern
    ctx.save();
    ctx.translate(cx, cy + 10);

    const starG = ctx.createLinearGradient(-50, -50, 50, 50);
    starG.addColorStop(0, '#ffffff');
    starG.addColorStop(0.35, '#93c5fd');
    starG.addColorStop(0.75, '#2563eb');
    starG.addColorStop(1, '#0f172a');

    ctx.fillStyle = starG;
    ctx.beginPath();
    ctx.moveTo(0, -60);
    ctx.lineTo(16, -16);
    ctx.lineTo(60, 0);
    ctx.lineTo(16, 16);
    ctx.lineTo(0, 60);
    ctx.lineTo(-16, 16);
    ctx.lineTo(-60, 0);
    ctx.lineTo(-16, -16);
    ctx.closePath();

    ctx.shadowColor = '#38bdf8';
    ctx.shadowBlur = 16;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Facetten-Glanzlinien
    ctx.strokeStyle = 'rgba(255,255,255,0.85)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, -60);
    ctx.lineTo(0, 60);
    ctx.moveTo(-60, 0);
    ctx.lineTo(60, 0);
    ctx.stroke();
    ctx.restore();

    // Rang-Monogramm GA / SGA oben
    ctx.font = '900 28px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 6;
    ctx.strokeText(isSGA ? 'SGA' : 'GA', cx, cy - 50);
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#60a5fa';
    ctx.shadowBlur = 10;
    ctx.fillText(isSGA ? 'SGA' : 'GA', cx, cy - 50);
    ctx.shadowBlur = 0;

    ctx.restore();
  }

  // =========================================================================
  // [GM] GAME MASTER – Modernes Eis-Cyan-Kristallwappen mit GM-Sigil
  // =========================================================================
  drawModernGameMasterEmblem(ctx, cx, cy, rankTag = 'GM') {
    ctx.save();

    // 1. Dreischichtige Eis-Kristall-Energieschwingen
    const drawCyanCrystalWing = (side) => {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.scale(side, 1);

      // Große äußere Energieklinge
      const g1 = ctx.createLinearGradient(20, -120, 215, 30);
      g1.addColorStop(0, '#ffffff');
      g1.addColorStop(0.25, '#67e8f9');
      g1.addColorStop(0.70, '#0284c7');
      g1.addColorStop(1, '#082f49');

      ctx.fillStyle = g1;
      ctx.strokeStyle = '#e0f2fe';
      ctx.lineWidth = 2.5;

      ctx.beginPath();
      ctx.moveTo(45, -35);
      ctx.lineTo(185, -140); // Hohe spitze Kristallflügellanze
      ctx.lineTo(210, -75);
      ctx.lineTo(145, 15);
      ctx.lineTo(180, 35);
      ctx.lineTo(110, 80);
      ctx.lineTo(45, 45);
      ctx.closePath();

      ctx.shadowColor = '#06b6d4';
      ctx.shadowBlur = 18;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.stroke();

      // Sekundäre innere Kristallklaue
      ctx.beginPath();
      ctx.moveTo(45, 10);
      ctx.lineTo(140, -45);
      ctx.lineTo(150, 5);
      ctx.lineTo(85, 40);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Leuchtende Cyan-Ader
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2.2;
      ctx.shadowColor = '#22d3ee';
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.moveTo(55, -25);
      ctx.lineTo(175, -120);
      ctx.stroke();
      ctx.shadowBlur = 0;

      ctx.restore();
    };

    drawCyanCrystalWing(1);
    drawCyanCrystalWing(-1);

    // 2. Zentrale Kristallraute (Diamond Prism Shield)
    const diamondGrad = ctx.createLinearGradient(cx - 95, cy - 120, cx + 95, cy + 120);
    diamondGrad.addColorStop(0, '#ffffff');
    diamondGrad.addColorStop(0.22, '#67e8f9');
    diamondGrad.addColorStop(0.65, '#0891b2');
    diamondGrad.addColorStop(1, '#083344');

    ctx.beginPath();
    ctx.moveTo(cx, cy - 130);
    ctx.lineTo(cx + 96, cy - 12);
    ctx.lineTo(cx, cy + 138);
    ctx.lineTo(cx - 96, cy - 12);
    ctx.closePath();

    ctx.shadowColor = 'rgba(0,0,0,0.95)';
    ctx.shadowBlur = 18;
    ctx.fillStyle = diamondGrad;
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 4.5;
    ctx.stroke();

    // Innerer dunkel-kristalliner Arkan-Spiegel
    ctx.beginPath();
    ctx.moveTo(cx, cy - 108);
    ctx.lineTo(cx + 76, cy - 12);
    ctx.lineTo(cx, cy + 114);
    ctx.lineTo(cx - 76, cy - 12);
    ctx.closePath();

    const innerGrad = ctx.createLinearGradient(cx, cy - 108, cx, cy + 114);
    innerGrad.addColorStop(0, '#042f2e');
    innerGrad.addColorStop(0.5, '#083344');
    innerGrad.addColorStop(1, '#021824');
    ctx.fillStyle = innerGrad;
    ctx.fill();
    ctx.strokeStyle = '#22d3ee';
    ctx.lineWidth = 3.0;
    ctx.stroke();

    // 3. ORIGINALE HYPER-MODERNE GM-MONOGRAMM-SIGIL-GEOMETRIE
    ctx.save();
    ctx.translate(cx, cy - 2);

    const sigilGrad = ctx.createLinearGradient(-50, -55, 50, 55);
    sigilGrad.addColorStop(0, '#ffffff');
    sigilGrad.addColorStop(0.25, '#cffafe');
    sigilGrad.addColorStop(0.70, '#22d3ee');
    sigilGrad.addColorStop(1, '#0284c7');

    ctx.fillStyle = sigilGrad;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3.5;
    ctx.shadowColor = '#06b6d4';
    ctx.shadowBlur = 18;

    // Stylisiertes heraldisches "G" (Links / Mitte)
    ctx.beginPath();
    ctx.moveTo(14, -40);
    ctx.lineTo(-20, -40);
    ctx.lineTo(-40, -18);
    ctx.lineTo(-40, 20);
    ctx.lineTo(-20, 40);
    ctx.lineTo(20, 40);
    ctx.lineTo(34, 26);
    ctx.lineTo(34, 6);
    ctx.lineTo(0, 6);
    ctx.lineTo(0, 20);
    ctx.lineTo(16, 20);
    ctx.lineTo(12, 28);
    ctx.lineTo(-12, 28);
    ctx.lineTo(-26, 12);
    ctx.lineTo(-26, -12);
    ctx.lineTo(-12, -28);
    ctx.lineTo(14, -28);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Stylisiertes erhöhtes "M" (Mitte / Rechts verschlungen)
    ctx.beginPath();
    ctx.moveTo(-14, 30);
    ctx.lineTo(-14, -26);
    ctx.lineTo(-3, -12);
    ctx.lineTo(16, -38);
    ctx.lineTo(40, -8);
    ctx.lineTo(40, 30);
    ctx.lineTo(28, 30);
    ctx.lineTo(28, 2);
    ctx.lineTo(16, -18);
    ctx.lineTo(-3, 2);
    ctx.lineTo(-3, 30);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Zentraler leuchtender Nexus-Stern
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(0, 0, 5.0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    ctx.restore();
  }

  // =========================================================================
  // [TGM] TRIAL GAME MASTER – Modernes Türkis-Kristall-Insignia
  // =========================================================================
  drawModernTrialGameMasterEmblem(ctx, cx, cy) {
    ctx.save();

    // 8-spitziger facettierter Diamantstern
    const starGrad = ctx.createLinearGradient(cx - 100, cy - 100, cx + 100, cy + 100);
    starGrad.addColorStop(0, '#ffffff');
    starGrad.addColorStop(0.3, '#5eead4');
    starGrad.addColorStop(0.7, '#14b8a6');
    starGrad.addColorStop(1, '#042f2e');

    ctx.beginPath();
    ctx.moveTo(cx, cy - 130);
    ctx.lineTo(cx + 38, cy - 38);
    ctx.lineTo(cx + 130, cy);
    ctx.lineTo(cx + 38, cy + 38);
    ctx.lineTo(cx, cy + 130);
    ctx.lineTo(cx - 38, cy + 38);
    ctx.lineTo(cx - 130, cy);
    ctx.lineTo(cx - 38, cy - 38);
    ctx.closePath();

    ctx.shadowColor = '#2dd4bf';
    ctx.shadowBlur = 18;
    ctx.fillStyle = starGrad;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 4.0;
    ctx.stroke();

    // Innerer dunkler Jade-Kern
    ctx.beginPath();
    ctx.moveTo(cx, cy - 95);
    ctx.lineTo(cx + 26, cy - 26);
    ctx.lineTo(cx + 95, cy);
    ctx.lineTo(cx + 26, cy + 26);
    ctx.lineTo(cx, cy + 95);
    ctx.lineTo(cx - 26, cy + 26);
    ctx.lineTo(cx - 95, cy);
    ctx.lineTo(cx - 26, cy - 26);
    ctx.closePath();
    ctx.fillStyle = '#042f2e';
    ctx.fill();
    ctx.strokeStyle = '#2dd4bf';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // TGM Monogramm
    ctx.font = '900 32px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#2dd4bf';
    ctx.shadowBlur = 12;
    ctx.fillText('TGM', cx, cy);
    ctx.restore();
  }

  // =========================================================================
  // [SUP] SUPPORT – Modernes Smaragd-Schutzwappen mit Lebenskristall
  // =========================================================================
  drawModernSupportEmblem(ctx, cx, cy) {
    ctx.save();

    const shieldGrad = ctx.createLinearGradient(cx - 95, cy - 110, cx + 95, cy + 120);
    shieldGrad.addColorStop(0, '#ffffff');
    shieldGrad.addColorStop(0.25, '#6ee7b7');
    shieldGrad.addColorStop(0.65, '#059669');
    shieldGrad.addColorStop(1, '#064e3b');

    ctx.beginPath();
    ctx.moveTo(cx - 92, cy - 95);
    ctx.lineTo(cx + 92, cy - 95);
    ctx.lineTo(cx + 92, cy + 15);
    ctx.bezierCurveTo(cx + 90, cy + 85, cx + 40, cy + 125, cx, cy + 142);
    ctx.bezierCurveTo(cx - 40, cy + 125, cx - 90, cy + 85, cx - 92, cy + 15);
    ctx.closePath();

    ctx.shadowColor = '#10b981';
    ctx.shadowBlur = 18;
    ctx.fillStyle = shieldGrad;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 4.5;
    ctx.stroke();

    // Innerer dunkelgrüner Spiegel
    ctx.beginPath();
    ctx.moveTo(cx - 72, cy - 76);
    ctx.lineTo(cx + 72, cy - 76);
    ctx.lineTo(cx + 72, cy + 12);
    ctx.bezierCurveTo(cx + 70, cy + 66, cx + 30, cy + 102, cx, cy + 118);
    ctx.bezierCurveTo(cx - 30, cy + 102, cx - 70, cy + 66, cx - 72, cy + 12);
    ctx.closePath();
    ctx.fillStyle = '#022c22';
    ctx.fill();
    ctx.strokeStyle = '#34d399';
    ctx.lineWidth = 3.0;
    ctx.stroke();

    // Zentrales weiß-grünes Kreuz des Lebens
    ctx.save();
    ctx.translate(cx, cy + 10);
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#34d399';
    ctx.shadowBlur = 16;
    ctx.fillRect(-10, -36, 20, 72);
    ctx.fillRect(-36, -10, 72, 20);

    // Innerer Smaragd-Edelstein
    ctx.fillStyle = '#059669';
    ctx.beginPath();
    ctx.arc(0, 0, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();

    // SUP Text oben
    ctx.font = '900 24px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('SUP', cx, cy - 50);

    ctx.restore();
  }

  // =========================================================================
  // [DEV] DEVELOPER – Moderne Techno-Arkane Sechskant-Rune
  // =========================================================================
  drawModernDeveloperEmblem(ctx, cx, cy) {
    ctx.save();
    const hexGrad = ctx.createLinearGradient(cx - 100, cy - 100, cx + 100, cy + 100);
    hexGrad.addColorStop(0, '#ffffff');
    hexGrad.addColorStop(0.25, '#c084fc');
    hexGrad.addColorStop(0.70, '#7e22ce');
    hexGrad.addColorStop(1, '#3b0764');

    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = (i * Math.PI) / 3;
      const x = cx + Math.cos(a) * 115;
      const y = cy + Math.sin(a) * 115;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.shadowColor = '#a855f7';
    ctx.shadowBlur = 18;
    ctx.fillStyle = hexGrad;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#f0abfc';
    ctx.lineWidth = 4.5;
    ctx.stroke();

    ctx.font = '900 32px "Cinzel", "Courier New", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#c084fc';
    ctx.shadowBlur = 14;
    ctx.fillText('DEV', cx, cy);
    ctx.restore();
  }

  // =========================================================================
  // [TM] TEAM MANAGER & [CM] COMMUNITY MANAGER
  // =========================================================================
  drawModernTeamManagerEmblem(ctx, cx, cy) {
    ctx.save();
    const grad = ctx.createLinearGradient(cx - 95, cy - 105, cx + 95, cy + 115);
    grad.addColorStop(0, '#fde047');
    grad.addColorStop(0.3, '#c084fc');
    grad.addColorStop(0.8, '#581c87');
    grad.addColorStop(1, '#3b0764');

    ctx.beginPath();
    ctx.moveTo(cx, cy - 115);
    ctx.lineTo(cx + 95, cy - 45);
    ctx.lineTo(cx + 72, cy + 65);
    ctx.lineTo(cx, cy + 130);
    ctx.lineTo(cx - 72, cy + 65);
    ctx.lineTo(cx - 95, cy - 45);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.strokeStyle = '#fde047';
    ctx.lineWidth = 4.5;
    ctx.stroke();

    ctx.font = '900 34px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('TM', cx, cy);
    ctx.restore();
  }

  drawModernCommunityManagerEmblem(ctx, cx, cy) {
    ctx.save();
    const grad = ctx.createLinearGradient(cx - 95, cy - 105, cx + 95, cy + 115);
    grad.addColorStop(0, '#ffffff');
    grad.addColorStop(0.25, '#fda4af');
    grad.addColorStop(0.7, '#e11d48');
    grad.addColorStop(1, '#881337');

    ctx.beginPath();
    ctx.moveTo(cx, cy - 110);
    ctx.bezierCurveTo(cx + 85, cy - 110, cx + 105, cy - 25, cx + 85, cy + 45);
    ctx.bezierCurveTo(cx + 60, cy + 100, cx + 20, cy + 125, cx, cy + 135);
    ctx.bezierCurveTo(cx - 20, cy + 125, cx - 60, cy + 100, cx - 85, cy + 45);
    ctx.bezierCurveTo(cx - 105, cy - 25, cx - 85, cy - 110, cx, cy - 110);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 4.5;
    ctx.stroke();

    ctx.font = '900 34px "Cinzel", "Times New Roman", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('CM', cx, cy);
    ctx.restore();
  }

  // --- 3D THREE.JS INTEGRATION ---

  getParticleTexture() {
    if (this._particleTex) return this._particleTex;
    const pCanvas = document.createElement('canvas');
    pCanvas.width = 64;
    pCanvas.height = 64;
    const pCtx = pCanvas.getContext('2d');
    const grad = pCtx.createRadialGradient(32, 32, 0, 32, 32, 30);
    grad.addColorStop(0, '#ffffff');
    grad.addColorStop(0.35, 'rgba(255,255,255,0.95)');
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

    // Feine Orbit-Partikel für höhere Ränge (SA, GA, GM, DEV, TM, SGA)
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
        const radius = 0.58 + (i % 3) * 0.12;
        pSprite.position.set(Math.cos(angle) * radius, (Math.sin(angle * 2) * 0.18), Math.sin(angle) * radius);
        pSprite.scale.set(0.14, 0.14, 1);
        pSprite.userData = {
          baseAngle: angle,
          radius,
          speed: 0.95 + (i % 2) * 0.50,
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

  // Animation & Distanzskalierungs-Update mit "Leicht Blinken" (Specular Gleam)
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
      group.position.y = (ud.baseY || 3.75) + bob;

      // 2. "Leicht Blinken" & Pulsierender Shimmer-Effekt
      let flash = 0;
      if (sprite?.material) {
        if (showGlow) {
          // A. Sanftes Grund-Atmen (Atmosphärischer Glow)
          const breathe = 0.92 + Math.sin(elapsed * 2.4 + ud.seed) * 0.08;

          // B. Periodisches edles "Blinken" (Glanz-Aufblitzen alle ~2.8 Sekunden)
          const blinkPeriod = 2.8;
          const blinkPhase = ((elapsed + ud.seed * 0.5) % blinkPeriod) / blinkPeriod;
          // Kurzer, weicher Glanz-Peak (Dauer ~0.45 Sek)
          if (blinkPhase < 0.16) {
            flash = Math.sin((blinkPhase / 0.16) * Math.PI); // 0 -> 1 -> 0
          }

          // Opazität variiert sanft
          sprite.material.opacity = Math.min(1.0, breathe + flash * 0.08);

          // Farbmodulation für echten Glanz/Blink-Effekt (übersteuert sanft ins Helle!)
          const brightness = 1.0 + flash * 0.52; // Glanz blitz bis zu +52% Helligkeit auf!
          sprite.material.color.setRGB(brightness, brightness, brightness);

          // Dezenter Mikro-Puls der Größe beim Aufblitzen
          ud.flashScaleMult = 1.0 + flash * 0.07;
        } else {
          sprite.material.opacity = 1.0;
          sprite.material.color.setRGB(1.0, 1.0, 1.0);
          ud.flashScaleMult = 1.0;
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
            const baseOp = 0.55 + Math.sin(elapsed * 3.5 + pud.baseAngle) * 0.35;
            p.material.opacity = Math.min(1.0, baseOp + flash * 0.40);
          }
        } else {
          pGroup.visible = false;
        }
      }

      // 4. Dynamische Kamera- & Distanz-Skalierung mit Blink-Puls
      if (sprite) {
        let zoomFactor = 1.0;
        if (ud.isLocal) {
          zoomFactor = 0.38 * Math.min(1.0, Math.max(0.42, camDist / 13.5));
        } else if (camPos) {
          const distToCam = camPos.distanceTo(group.parent.position);
          zoomFactor = 0.38 * Math.min(1.25, Math.max(0.42, distToCam / 14.0));
        }
        const mult = ud.flashScaleMult || 1.0;
        const sW = zoomFactor * 4.4 * mult;
        const sH = zoomFactor * 4.4 * mult;
        sprite.scale.set(sW, sH, 1);
      }
    }
  }
}
