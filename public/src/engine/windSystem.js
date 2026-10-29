// ============================================================================
// AERYNDOR – ZENTRALES WINDFELD (eine gemeinsame Windquelle für alle Systeme)
// ============================================================================
// Liefert Richtung, Stärke, Böen, Turbulenz & höhenabhängigen Wind für:
// Schnee, Schneenebel, Pulverschnee, Regen, Gras, Bäume, Büsche, Laub,
// Luftpartikel, Feuer/Rauch und Wasser-/Pfützenoberflächen.
// Keine Abhängigkeiten außer Three.js (r160, WebGL2).
// ============================================================================

import * as THREE from '../../vendor/three.module.js';

export const WIND_SPEED_PER_STRENGTH = 6.9; // m/s pro normierter Windstärke (Legacy-Regenvektor 6.5/2.4)
const TWO_PI = Math.PI * 2;
// Normierung des Grenzschichtprofils: log(13.6) = log(1 + h * 1.6) bei h ≈ 7.9 m (der alte Kommentar "12 m" war falsch;
// Wert bewusst beibehalten, damit sich das Windverhalten nicht ändert)
const LOG_REF_HEIGHT = Math.log(13.6);

/** Wetter-Presets für das zentrale Windfeld (Werte werden stufenlos angefahren). */
export const WIND_PRESETS = Object.freeze({
  calm: { strength: 0.08, gustiness: 0.1, turbulence: 0.05, gustInterval: 14 },
  breeze: { strength: 0.3, gustiness: 0.35, turbulence: 0.2, gustInterval: 9 },
  windy: { strength: 0.75, gustiness: 0.55, turbulence: 0.35, gustInterval: 7 },
  rain: { strength: 0.55, gustiness: 0.45, turbulence: 0.3, gustInterval: 8 },
  storm: { strength: 1.3, gustiness: 0.8, turbulence: 0.6, gustInterval: 5 },
  snow: { strength: 0.4, gustiness: 0.3, turbulence: 0.25, gustInterval: 10 },
  blizzard: { strength: 1.7, gustiness: 0.9, turbulence: 0.75, gustInterval: 4 },
});

export class WindField {
  constructor({ baseAngle = 0.61 } = {}) {
    this.baseAngle = baseAngle; // Vorherrschende Richtung (rad, 0 = +X, PI/2 = +Z)
    this.angle = baseAngle;
    this.dir = new THREE.Vector2(Math.cos(baseAngle), Math.sin(baseAngle));
    this.prevailingDir = this.dir.clone(); // stabil – für Schneewehen-Ausrichtung
    this.strength = 0.3; // normierte Grundstärke (0 = still, ~1.7 = Schneesturm)
    this.gust = 0.0; // aktuelle Böenhüllkurve 0..1
    this.gustiness = 0.35; // Böenstärke 0..1
    this.gustInterval = 9.0; // mittleres Böenintervall in s
    this.turbulence = 0.2; // lokale Verwirbelung 0..1
    this.speedMs = 2.0; // effektive Windgeschwindigkeit inkl. Böe (m/s)
    this.velocity = new THREE.Vector2(); // m/s (x, z)
    this.time = 0;
    this._targetStrength = 0.3;
    this._targetGustiness = 0.35;
    this._targetTurbulence = 0.2;

    // Gemeinsame Shader-Uniforms (per Referenz in alle Materialien gebunden)
    this.uniforms = {
      uWindDir: { value: this.dir.clone() },
      uWindStrength: { value: this.strength },
      uWindGust: { value: 0.0 },
      uWindTurb: { value: this.turbulence },
      uWindSpeedMs: { value: this.speedMs },
    };
  }

  /**
   * @param {number} dt
   * @param {object} p { strength, gustiness, turbulence, gustInterval, baseAngle, enabled }
   */
  update(dt, p = {}) {
    const d = Math.min(0.1, Math.max(0, Number(dt) || 0));
    if (d <= 0 && !p.snap) {
      // Neutrales Verhalten bei Pausiertem Tab / dt = 0
      return;
    }
    this.time += d;
    if (p.baseAngle !== undefined && Number.isFinite(p.baseAngle)) this.baseAngle = p.baseAngle;
    const enabled = p.enabled !== false;
    this._targetStrength = enabled ? Math.max(0, p.strength ?? this._targetStrength) : 0;
    this._targetGustiness = Math.max(0, Math.min(1, p.gustiness ?? this._targetGustiness));
    this._targetTurbulence = Math.max(0, Math.min(1, p.turbulence ?? this._targetTurbulence));
    if (Number.isFinite(p.gustInterval)) this.gustInterval = Math.max(2.5, p.gustInterval);

    // Stufenlose Übergänge (kein Sprung bei Wetterwechsel)
    const k = p.snap ? 1 : Math.min(1, d * 0.35);
    this.strength += (this._targetStrength - this.strength) * k;
    this.gustiness += (this._targetGustiness - this.gustiness) * k;
    this.turbulence += (this._targetTurbulence - this.turbulence) * k;

    // Böenhüllkurve: überlagerte, inkommensurable Sinuswellen -> natürliche, unregelmäßige Böen
    const t = this.time;
    const w = TWO_PI / this.gustInterval;
    const raw =
      0.55 * Math.sin(t * w) +
      0.30 * Math.sin(t * w * 1.73 + 1.3) +
      0.15 * Math.sin(t * w * 3.11 + 4.1);
    // Smoothstep auf [0,1] (raw liegt in [-1,1]; negative Anteile = Windstille zwischen Böen)
    const env = Math.min(1, Math.max(0, raw));
    this.gust = env * env * (3 - 2 * env);

    // Richtung mäandert langsam um die vorherrschende Richtung (+ kleine böenbedingte Drehung)
    this.angle =
      this.baseAngle +
      0.16 * Math.sin(t * 0.021) +
      0.06 * Math.sin(t * 0.057 + 2.0) +
      this.gust * 0.05 * this.turbulence;
    this.dir.set(Math.cos(this.angle), Math.sin(this.angle));
    this.prevailingDir.set(Math.cos(this.baseAngle), Math.sin(this.baseAngle));

    const gustMult = 1 + this.gust * this.gustiness * 0.85;
    this.speedMs = this.strength * WIND_SPEED_PER_STRENGTH * gustMult;
    this.velocity.set(this.dir.x * this.speedMs, this.dir.y * this.speedMs);

    const u = this.uniforms;
    u.uWindDir.value.copy(this.dir);
    u.uWindStrength.value = this.strength * gustMult;
    u.uWindGust.value = this.gust * this.gustiness;
    u.uWindTurb.value = this.turbulence;
    u.uWindSpeedMs.value = this.speedMs;
  }

  /** Höhenabhängiger Wind (logarithmisches Grenzschichtprofil, 0 m = Boden) */
  heightFactor(heightAboveGround) {
    const h = Math.max(0.01, Number(heightAboveGround) || 0.0);
    return Math.min(1.25, Math.max(0.1, 0.42 + 0.58 * (Math.log(1.0 + h * 1.6) / LOG_REF_HEIGHT)));
  }

  /** CPU-Stichprobe einer lokalen Böenfront (identisch zur GLSL-Variante in den Schnee-Shadern) */
  sampleGustAt(x, z) {
    const front = (x * this.dir.x + z * this.dir.y) * 0.045 - this.time * (0.35 + this.strength * 0.25);
    const s = Math.sin(front) * 0.5 + 0.5;
    const g = Math.max(0, Math.min(1, (s - 0.2) / 0.8));
    return g * g * (3 - 2 * g) * this.gust * this.gustiness;
  }

  /** Legacy-Vektor (Regen, Laub, Partikel) – gleiche Richtung wie alle anderen Systeme */
  getLegacyVector(target = new THREE.Vector2()) {
    const s = this.strength * WIND_SPEED_PER_STRENGTH;
    return target.set(this.dir.x * s, this.dir.y * s);
  }

  /**
   * Liefert die Update-Parameter eines Presets (zur Übergabe an update()).
   * Unbekannte Namen fallen auf 'breeze' zurück.
   */
  static getPresetParams(name) {
    return { ...(WIND_PRESETS[name] || WIND_PRESETS.breeze) };
  }

  /** Setzt Zielwerte eines Presets direkt (weicher Übergang über die folgenden update()-Aufrufe). */
  applyPreset(name, { snap = false } = {}) {
    const p = WindField.getPresetParams(name);
    this._targetStrength = p.strength;
    this._targetGustiness = p.gustiness;
    this._targetTurbulence = p.turbulence;
    this.gustInterval = p.gustInterval;
    if (snap) {
      this.strength = p.strength;
      this.gustiness = p.gustiness;
      this.turbulence = p.turbulence;
    }
    this.presetName = WIND_PRESETS[name] ? name : 'breeze';
    return this;
  }

  /**
   * Lokaler Windvektor (m/s) an einer Weltposition inkl. Höhenprofil und lokaler Böenfront –
   * praktisch für Partikel, Fahnen, Projektil-Drift oder Segel.
   */
  sampleAt(x, z, heightAboveGround = 1.5, target = new THREE.Vector2()) {
    const base = this.strength * WIND_SPEED_PER_STRENGTH;
    const local = base * (1 + this.sampleGustAt(x, z) * 0.85) * this.heightFactor(heightAboveGround);
    return target.set(this.dir.x * local, this.dir.y * local);
  }

  /** Bindet die gemeinsamen Wind-Uniforms in ein Shader-Uniform-Objekt (per Referenz). */
  bindUniforms(targetUniforms) {
    if (targetUniforms) Object.assign(targetUniforms, this.uniforms);
    return targetUniforms;
  }

  getSnapshot() {
    const normAngle = ((this.angle % TWO_PI) + TWO_PI) % TWO_PI;
    return {
      angle: +normAngle.toFixed(3),
      dirX: +this.dir.x.toFixed(3),
      dirZ: +this.dir.y.toFixed(3),
      strength: +this.strength.toFixed(3),
      speedMs: +this.speedMs.toFixed(2),
      gust: +this.gust.toFixed(3),
      gustiness: +this.gustiness.toFixed(2),
      turbulence: +this.turbulence.toFixed(2),
      preset: this.presetName || null,
    };
  }
}
