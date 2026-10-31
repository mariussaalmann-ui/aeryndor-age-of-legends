// ============================================================================
// AERYNDOR: LEGACY OF THE MONOLITHS – Sonne, Mond, Atmosphäre & Tag/Nacht-System
// ============================================================================
//  - 24h-Weltzeit (Server-Sync), 8 Mondphasen, Rayleigh/Mie-Himmelsstreuung
//  - Volumetrische God-Rays (Sun-/Moonbeams) & Texel-Snapping-Schatten
// ============================================================================

import * as THREE from '../../vendor/three.module.js';
import { VolumetricCloudManager, CLOUD_TYPES } from './cloudSystem.js?v=v20261024_0300';

export { VolumetricCloudManager, CLOUD_TYPES };

// ============================================================================
// 1. WORLD TIME MANAGER
// ============================================================================
export class WorldTimeManager {
  constructor(options = {}) {
    this.dayLengthMinutes = Number(options.dayLengthMinutes || 60);
    this.hourOfDay = Number(options.hourOfDay ?? 13.5); // 0.0 .. 24.0
    this.timeSpeed = Number(options.timeSpeed ?? 1.0);
    this.timeMode = options.timeMode || 'server'; // 'server' | 'local'
    this.paused = false;

    this.serverSyncHour = null;
    this.lastSyncTime = 0;
  }

  update(dt = 0) {
    if (this.paused || dt <= 0) return this.hourOfDay;

    if (this.timeMode === 'server' && this.serverSyncHour !== null) {
      let diff = this.serverSyncHour - this.hourOfDay;
      while (diff > 12.0) diff -= 24.0;
      while (diff < -12.0) diff += 24.0;

      const blendRate = Math.abs(diff) > 2.0 ? 3.5 : 0.85;
      this.hourOfDay += diff * Math.min(1.0, dt * blendRate);
    } else {
      const effectiveSpeed = Math.max(0.0, this.timeSpeed);
      if (effectiveSpeed > 0.0) {
        const totalSec = Math.max(10, this.dayLengthMinutes * 60);
        const hoursDelta = (dt / totalSec) * 24.0 * effectiveSpeed;
        this.hourOfDay += hoursDelta;
      }
    }

    this.hourOfDay = ((this.hourOfDay % 24.0) + 24.0) % 24.0;
    return this.hourOfDay;
  }

  syncWithServer(serverTimestamp) {
    if (!serverTimestamp || isNaN(serverTimestamp)) return;
    const totalSec = Math.max(10, this.dayLengthMinutes * 60);
    const cycleSec = ((serverTimestamp % totalSec) + totalSec) % totalSec;
    this.serverSyncHour = (cycleSec / totalSec) * 24.0;
    this.lastSyncTime = performance.now();
  }

  setHour(h) {
    this.hourOfDay = ((Number(h) % 24.0) + 24.0) % 24.0;
    if (this.timeMode === 'server') {
      this.serverSyncHour = this.hourOfDay;
    }
  }

  setTimeSpeed(speed) {
    this.timeSpeed = Math.max(0.0, Number(speed));
  }

  pause() {
    this.paused = true;
  }

  resume() {
    this.paused = false;
  }

  isPaused() {
    return this.paused || this.timeSpeed === 0;
  }

  getHour() {
    return this.hourOfDay;
  }

  getTimeFormatted() {
    const totalSeconds = Math.floor(this.hourOfDay * 3600);
    const hours = Math.floor(totalSeconds / 3600) % 24;
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const pad = (n) => (n < 10 ? '0' + n : '' + n);
    return {
      hours,
      minutes,
      seconds,
      timeString: `${pad(hours)}:${pad(minutes)}`,
      timeStringFull: `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`,
    };
  }
}

// ============================================================================
// 2. CELESTIAL MANAGER (SONNE, MOND & ASTRONOMISCHE BELEUCHTUNG)
// ============================================================================
export const MOON_PHASES = [
  { id: 0, name: 'Neumond', illumination: 0.04, icon: '🌑' },
  { id: 1, name: 'Zunehmende Sichel', illumination: 0.28, icon: '🌒' },
  { id: 2, name: 'Erstes Viertel', illumination: 0.54, icon: '🌓' },
  { id: 3, name: 'Zunehmender Dreiviertelmond', illumination: 0.80, icon: '🌔' },
  { id: 4, name: 'Vollmond', illumination: 1.00, icon: '🌕' },
  { id: 5, name: 'Abnehmender Dreiviertelmond', illumination: 0.80, icon: '🌖' },
  { id: 6, name: 'Letztes Viertel', illumination: 0.54, icon: '🌗' },
  { id: 7, name: 'Abnehmende Sichel', illumination: 0.28, icon: '🌘' },
];

// Konstante Farbpaletten (einmalig angelegt statt ~25 `new THREE.Color()` pro Frame in update())
const C = (hex) => Object.freeze(new THREE.Color(hex));
const SKY_PALETTE = Object.freeze({
  dawnSun: C(0xffb36b),
  duskSun: C(0xff9438),
  noonSun: C(0xfffdf5),
  autumnSunTint: C(0xffe8a3),
  winterSunTint: C(0xf1f5f9),
  fullMoonTint: C(0xd2e6ff),
  day: { zenith: C(0x1a5696), horizon: C(0x9dc7e8), hemiSky: C(0xbce0fd), hemiGround: C(0x3a5829) },
  dawn: { zenith: C(0x1f4b7a), horizon: C(0xf2a663), hemiSky: C(0xfcd39b), hemiGround: C(0x3d4b2c) },
  dusk: { zenith: C(0x183c66), horizon: C(0xf58c38), hemiSky: C(0xfdba74), hemiGround: C(0x52391e) },
  night: { zenith: C(0x060e1c), horizon: C(0x112642), hemiSky: C(0x4876a8), hemiGround: C(0x1a2a3e) },
  overcastDay: { zenith: C(0x3b4959), horizon: C(0x6c7d8e), hemiSky: C(0x9cb0c4), hemiGround: C(0x3a4a38) },
  overcastNight: { zenith: C(0x101c2c), horizon: C(0x1c2d42), hemiSky: C(0x4a6685), hemiGround: C(0x223244) },
  winterGround: C(0x8fa3b8),
});

// Wetterklassen als Sets (O(1)-Lookup, eine Quelle für alle Teilsysteme)
const RAIN_OR_STORM_WEATHER = new Set(['light_rain', 'rain', 'heavy_rain', 'thunderstorm', 'severe_thunderstorm', 'heavy_snow', 'blizzard']);
const CLOUD_SHADOW_DAMP_WEATHER = new Set([...RAIN_OR_STORM_WEATHER, 'fog']);
const HEAVY_STORM_WEATHER = new Set(['blizzard', 'heavy_snow', 'heavy_rain', 'severe_thunderstorm']);

export class CelestialManager {
  constructor(options = {}) {
    this.latitude = options.latitude ?? 36.0;
    this.moonPhase = options.moonPhase ?? 4; // Standard: Vollmond
    this.season = options.season || 'summer';

    // Wiederverwendbare mathematische Vektoren & Farben
    this.sunDirection = new THREE.Vector3(0.3, 0.8, 0.4).normalize();
    this.moonDirection = new THREE.Vector3(-0.3, 0.8, -0.4).normalize();
    this.activeLightDirection = new THREE.Vector3(0.3, 0.8, 0.4).normalize();

    this.sunColor = new THREE.Color(0xfffdf5);
    this.moonColor = new THREE.Color(0xb4d6f8);
    this.activeLightColor = new THREE.Color(0xfffdf5);
    this.zenithColor = new THREE.Color(0x1b5699);
    this.horizonColor = new THREE.Color(0x9ec6e6);
    this.fogColor = this.horizonColor;
    this.ambientSkyColor = new THREE.Color(0x7dd3fc);
    this.hemiSkyColor = this.ambientSkyColor;
    this.ambientGroundColor = new THREE.Color(0x334e26);
    this.hemiGroundColor = this.ambientGroundColor;

    this.sunElevation = 0.8;
    this.sunAzimuth = 0.0;
    this.moonElevation = -0.8;
    this.moonAzimuth = Math.PI;

    this.sunIntensity = 1.65;
    this.moonIntensity = 0.0;
    this.activeLightIntensity = 1.65;
    this.ambientIntensity = 1.10;
    this.ambientFloor = 0.22;
    this.starOpacity = 0.0;

    this.isDay = true;
    this.isMoonlitNight = false;
    this.twilightFactor = 0.0; // 0 = Tag/Nacht, 1 = Dämmerung / Golden Hour
    this.dawnFactor = 0.0;
    this.duskFactor = 0.0;
  }

  get isNight() {
    return !this.isDay;
  }

  get hemiIntensity() {
    return this.ambientIntensity;
  }

  setSeason(season) {
    this.season = season || 'summer';
  }

  setMoonPhase(phaseIndex) {
    this.moonPhase = Math.max(0, Math.min(7, Math.floor(phaseIndex)));
  }

  update(hourOfDay, season = this.season, opts = {}) {
    this.season = season;
    const sunMult = Number(opts.sunIntensityMult ?? 1.0);
    const moonMult = Number(opts.moonIntensityMult ?? 1.0);
    const cloudiness = Number(opts.cloudiness ?? 0.2);
    const sunOcclusion = Number(opts.sunOcclusion ?? 0.0);
    const weather = opts.weather || 'sunny';

    const radLat = (this.latitude * Math.PI) / 180.0;

    // 1. Jahreszeitliche Sonnendeklination
    let declinationDeg = 12.5; // Sommer
    if (this.season === 'spring') declinationDeg = 3.0;
    else if (this.season === 'autumn') declinationDeg = -4.5;
    else if (this.season === 'winter') declinationDeg = -13.0;

    const radDec = (declinationDeg * Math.PI) / 180.0;

    // 2. Stundenwinkel (Mittag 12:00 = 0 rad, 06:00 = -pi/2, 18:00 = +pi/2)
    const hourAngle = ((hourOfDay - 12.0) / 12.0) * Math.PI;

    // 3. Sonnenhöhe (Elevation) und Azimut
    const sinElevation =
      Math.sin(radLat) * Math.sin(radDec) +
      Math.cos(radLat) * Math.cos(radDec) * Math.cos(hourAngle);
    this.sunElevation = Math.asin(Math.max(-1.0, Math.min(1.0, sinElevation)));

    const cosAzimuth =
      (Math.sin(radDec) - Math.sin(radLat) * Math.sin(this.sunElevation)) /
      (Math.cos(radLat) * Math.cos(this.sunElevation) + 0.0001);
    this.sunAzimuth = Math.acos(Math.max(-1.0, Math.min(1.0, cosAzimuth)));
    if (Math.sin(hourAngle) > 0) {
      this.sunAzimuth = 2.0 * Math.PI - this.sunAzimuth;
    }

    const sx = -Math.sin(hourAngle) * Math.cos(radDec);
    const sy = Math.sin(this.sunElevation);
    const sz = Math.cos(hourAngle) * Math.cos(radDec) * Math.sin(radLat) - Math.sin(radDec) * Math.cos(radLat);
    this.sunDirection.set(sx, sy, sz).normalize();

    // 4. Mondposition (orbitaler Phasenversatz gegenüber der Sonne)
    const moonPhaseAngle = ((this.moonPhase - 4) * Math.PI) / 4.0;
    const moonHourAngle = hourAngle + Math.PI + moonPhaseAngle * 0.35;
    const moonDec = -radDec * 0.75 + 0.14;

    const sinMoonElev =
      Math.sin(radLat) * Math.sin(moonDec) +
      Math.cos(radLat) * Math.cos(moonDec) * Math.cos(moonHourAngle);
    this.moonElevation = Math.asin(Math.max(-1.0, Math.min(1.0, sinMoonElev)));

    const mx = -Math.sin(moonHourAngle) * Math.cos(moonDec);
    const my = Math.sin(this.moonElevation);
    const mz = Math.cos(moonHourAngle) * Math.cos(moonDec) * Math.sin(radLat) - Math.sin(moonDec) * Math.cos(radLat);
    // Wenn es Nacht ist und der Mond durch den Phasenversatz tief stünde, heben wir die Mondbahn sanft an,
    // damit klare Vollmond-/Sichelmondnächte (wie in Bild 3 Unten) stets einen sichtbaren atmosphärischen Mond am Himmel bieten
    if (this.sunElevation < -0.02 && my < 0.22) {
      const nightBoost = Math.min(1.0, (-this.sunElevation) / 0.35);
      const liftedY = Math.max(my, 0.28 + 0.26 * nightBoost);
      this.moonDirection.set(mx, liftedY, mz).normalize();
      this.moonElevation = Math.asin(this.moonDirection.y);
    } else {
      this.moonDirection.set(mx, my, mz).normalize();
    }

    // 5. Physikalische Lichtstärken & Farbkurven
    const sunElevDeg = (this.sunElevation * 180.0) / Math.PI;
    const moonElevDeg = (this.moonElevation * 180.0) / Math.PI;

    const dayFactor = THREE.MathUtils.smoothstep(sunElevDeg, -3.8, 16.0);
    this.isDay = sunElevDeg > -3.8;

    // Golden Hour / Dämmerung (Sonne sinkt vollständig bis unter die Horizontlinie [-4.2° .. +18.5°] statt in der Luft zu verblassen!)
    const sunHorizonVis = THREE.MathUtils.smoothstep(sunElevDeg, -4.2, 1.2);
    const goldenWindow =
      sunElevDeg >= -4.2 && sunElevDeg <= 18.5
        ? Math.sin((THREE.MathUtils.clamp((sunElevDeg + 4.2) / 22.7, 0.0, 1.0)) * Math.PI) * sunHorizonVis
        : 0.0;
    this.twilightFactor = goldenWindow;
    this.dawnFactor = hourOfDay < 12.0 ? goldenWindow : 0.0;
    this.duskFactor = hourOfDay >= 12.0 ? goldenWindow : 0.0;

    // Wolken-Abschwächung des direkten Sonnenlichts (verhindert harte Schlagschatten bei starker Bewölkung/Regen)
    const isRainOrStorm = RAIN_OR_STORM_WEATHER.has(weather);
    const cloudDirectAtten = (1.0 - cloudiness * 0.48) * (1.0 - sunOcclusion * 0.35) * (isRainOrStorm ? 0.62 : 1.0);

    // A) Sonnenlicht-Farbe & Intensität
    if (goldenWindow > 0.01) {
      // Morgens: sanftes kühles Rosa-Gold -> warmes Bernstein
      // Abends (Bild 3 Oben): sattes Golden-Amber & warmes Abendgold (NIEMALS unnatürliches Lila/Magenta!)
      const targetGolden = hourOfDay >= 12.0 ? SKY_PALETTE.duskSun : SKY_PALETTE.dawnSun;
      this.sunColor.copy(SKY_PALETTE.noonSun).lerp(targetGolden, Math.min(1.0, goldenWindow * 0.94));
      const baseSun = (0.85 + dayFactor * 0.85) * sunHorizonVis;
      this.sunIntensity = baseSun * cloudDirectAtten * sunMult;
    } else if (this.isDay) {
      // Neutrales, natürliches Tageslicht am Mittag
      this.sunColor.setHex(0xfffdf6);
      if (this.season === 'autumn') {
        this.sunColor.lerp(SKY_PALETTE.autumnSunTint, 0.18);
      } else if (this.season === 'winter') {
        this.sunColor.lerp(SKY_PALETTE.winterSunTint, 0.22);
      }
      const elevSin = Math.sin(Math.max(0.0, this.sunElevation));
      this.sunIntensity = (1.35 + elevSin * 0.42) * sunHorizonVis * cloudDirectAtten * sunMult;
    } else {
      this.sunIntensity = 0.0;
    }

    // B) Mondlicht-Farbe & Intensität (Bild 3 Unten: kühle silberblaue Lichtstimmung, keine zweite Sonne!)
    const phaseMeta = MOON_PHASES[this.moonPhase] || MOON_PHASES[4];
    const moonHeightFactor = THREE.MathUtils.smoothstep(moonElevDeg, -2.0, 22.0);
    const moonCloudAtten = (1.0 - cloudiness * 0.55) * (isRainOrStorm ? 0.55 : 1.0);
    const moonNightGate = 1.0 - THREE.MathUtils.smoothstep(sunElevDeg, -1.2, 1.2);
    this.moonIntensity = (0.24 + phaseMeta.illumination * 0.48) * moonHeightFactor * moonCloudAtten * moonMult * moonNightGate;
    this.isMoonlitNight = !this.isDay && this.moonIntensity > 0.06;

    this.moonColor.setHex(0xa8ccf0);
    if (this.moonPhase === 4) {
      this.moonColor.lerp(SKY_PALETTE.fullMoonTint, 0.45);
    }

    // C) Atmosphärische Himmelsfarben (Zenit, Horizont, Hemisphäre & Boden)
    // Farbbasen: siehe SKY_PALETTE (Tag, Morgen, Abend, Nacht – ohne unnatürliches Lila/Magenta)
    const { day, dawn, dusk, night } = SKY_PALETTE;

    // Interpolation zwischen Nacht und Tag
    this.zenithColor.copy(night.zenith).lerp(day.zenith, dayFactor);
    this.horizonColor.copy(night.horizon).lerp(day.horizon, dayFactor);
    this.ambientSkyColor.copy(night.hemiSky).lerp(day.hemiSky, dayFactor);
    this.ambientGroundColor.copy(night.hemiGround).lerp(day.hemiGround, dayFactor);

    // Dämmerungs-/Golden-Hour-Überblendung (ohne jedes unnatürliche Lila!)
    if (this.dawnFactor > 0.01) {
      this.zenithColor.lerp(dawn.zenith, this.dawnFactor * 0.85);
      this.horizonColor.lerp(dawn.horizon, this.dawnFactor * 0.92);
      this.ambientSkyColor.lerp(dawn.hemiSky, this.dawnFactor * 0.85);
      this.ambientGroundColor.lerp(dawn.hemiGround, this.dawnFactor * 0.70);
    }
    if (this.duskFactor > 0.01) {
      this.zenithColor.lerp(dusk.zenith, this.duskFactor * 0.88);
      this.horizonColor.lerp(dusk.horizon, this.duskFactor * 0.95);
      this.ambientSkyColor.lerp(dusk.hemiSky, this.duskFactor * 0.88);
      this.ambientGroundColor.lerp(dusk.hemiGround, this.duskFactor * 0.75);
    }

    // D) Haupt-Lichtquellen-Handover (Sonne am Tag -> Mond in der Nacht)
    if (sunElevDeg >= -3.8) {
      this.activeLightDirection.copy(this.sunDirection);
      this.activeLightColor.copy(this.sunColor);
      this.activeLightIntensity = this.sunIntensity;
    } else if (moonElevDeg >= -1.0 && this.moonIntensity > 0.03) {
      this.activeLightDirection.copy(this.moonDirection);
      this.activeLightColor.copy(this.moonColor);
      this.activeLightIntensity = this.moonIntensity;
    } else {
      const blend = THREE.MathUtils.clamp((sunElevDeg + 6.5) / 2.7, 0.0, 1.0);
      this.activeLightDirection.copy(this.moonDirection).lerp(this.sunDirection, blend).normalize();
      this.activeLightColor.copy(this.moonColor).lerp(this.sunColor, blend);
      this.activeLightIntensity = THREE.MathUtils.lerp(this.moonIntensity, this.sunIntensity, blend);
    }

    // E) Indirekte Umgebungsbeleuchtung (verhindert komplett schwarze Schatten bei Regen, Gewitter & Nacht!)
    const baseDayAmb = 1.04 + dayFactor * 0.28;
    const baseNightAmb = 0.64 + phaseMeta.illumination * 0.24 * moonMult;
    this.ambientIntensity = THREE.MathUtils.lerp(baseNightAmb, baseDayAmb, dayFactor);

    // Bei Bewölkung, Regen und Gewitter streuen die Wolken das Himmelslicht diffus in alle Schattenbereiche:
    if (cloudiness > 0.35 || isRainOrStorm) {
      const overcastBlend = Math.min(1.0, Math.max(cloudiness - 0.25, isRainOrStorm ? 0.75 : 0.0));
      const overcast = this.isDay ? SKY_PALETTE.overcastDay : SKY_PALETTE.overcastNight;
      this.zenithColor.lerp(overcast.zenith, overcastBlend * 0.78);
      this.horizonColor.lerp(overcast.horizon, overcastBlend * 0.82);
      this.ambientSkyColor.lerp(overcast.hemiSky, overcastBlend * 0.75);
      this.ambientGroundColor.lerp(overcast.hemiGround, overcastBlend * 0.75);
      // Diffuses Fülllicht bei Regen/Bewölkung leicht anheben, damit Terrain NIEMALS schwarz absäuft (Fix Bild 2!)
      this.ambientIntensity = Math.max(this.ambientIntensity, this.isDay ? 1.08 : 0.76);
    }

    if (this.season === 'winter') {
      this.ambientGroundColor.lerp(SKY_PALETTE.winterGround, 0.48);
    }

    // Minimaler indirekter Lichtboden für Terrain & Gras-Shader
    this.ambientFloor = this.isDay
      ? (isRainOrStorm ? 0.34 : 0.26)
      : (isRainOrStorm ? 0.28 : 0.24 + phaseMeta.illumination * 0.08);
  }
}

// ============================================================================
// 3. ATMOSPHERE MANAGER (HIMMELSKUPPEL, LIMB-DARKENING-SONNE, MOND & STERNE)
// ============================================================================
export class AtmosphereManager {
  constructor(scene, engine = null, options = {}) {
    this.scene = scene;
    this.engine = engine;
    this.turbidity = options.turbidity ?? 2.4;
    this.rayleigh = options.rayleigh ?? 1.4;
    this.mieCoefficient = options.mieCoefficient ?? 0.005;
    this.scatteringIntensity = options.scatteringIntensity ?? 1.0;

    this.skyDome = null;
    this.starField = null;
    this.moonMesh = null;

    this.initAtmosphere();
  }

  initAtmosphere() {
    // 1. Atmosphärische Himmelskuppel mit physikalischem Rayleigh-/Mie-Streuungs- & Solar-Limb-Darkening-Shader
    const skyGeo = new THREE.SphereGeometry(1, 48, 32);
    this.skyUniforms = {
      uSunDir: { value: new THREE.Vector3(0.3, 0.8, 0.4) },
      uMoonDir: { value: new THREE.Vector3(-0.3, 0.8, -0.4) },
      uSunColor: { value: new THREE.Color(0xfffdf5) },
      uMoonColor: { value: new THREE.Color(0xb4d6f8) },
      uZenithColor: { value: new THREE.Color(0x1a5696) },
      uHorizonColor: { value: new THREE.Color(0x9dc7e8) },
      uGroundColor: { value: new THREE.Color(0x334155) },
      uZenith: { value: new THREE.Color(0x1a5696) },
      uHorizon: { value: new THREE.Color(0x9dc7e8) },
      uGround: { value: new THREE.Color(0x334155) },
      uSunIntensity: { value: 1.0 },
      uMoonIntensity: { value: 0.0 },
      uSunStrength: { value: 1.0 },
      uRayleigh: { value: 1.4 },
      uMieHalo: { value: 1.0 },
      uScattering: { value: 1.0 },
      uTwilight: { value: 0.0 },
      uCloudiness: { value: 0.0 },
      uSunOcclusion: { value: 0.0 },
      uTime: { value: 0.0 },
      uRiftFactor: { value: 0.0 },
      uRiftAwakened: { value: 0.0 },
      uRiftVioletStrength: { value: 1.0 },
      uRiftCrimsonStrength: { value: 1.0 },
      uRiftVortexScale: { value: 1.0 },
      uRiftLightning: { value: 0.0 },
      uRiftDir: { value: new THREE.Vector3(0.0, 0.72, -0.68).normalize() },
    };

    const skyMat = new THREE.ShaderMaterial({
      uniforms: this.skyUniforms,
      side: THREE.BackSide,
      depthWrite: false,
      depthTest: false,
      fog: false,
      vertexShader: `
        varying vec3 vWorldDir;
        void main() {
          vWorldDir = normalize(position);
          vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          gl_Position = vec4(p.xy, p.w * 0.99995, p.w);
        }
      `,
      fragmentShader: `
        uniform vec3 uSunDir;
        uniform vec3 uMoonDir;
        uniform vec3 uSunColor;
        uniform vec3 uMoonColor;
        uniform vec3 uZenithColor;
        uniform vec3 uHorizonColor;
        uniform vec3 uGroundColor;
        uniform float uSunIntensity;
        uniform float uMoonIntensity;
        uniform float uRayleigh;
        uniform float uMieHalo;
        uniform float uScattering;
        uniform float uTwilight;
        uniform float uCloudiness;
        uniform float uSunOcclusion;
        uniform float uTime;
        uniform float uRiftFactor;
        uniform float uRiftAwakened;
        uniform float uRiftVioletStrength;
        uniform float uRiftCrimsonStrength;
        uniform float uRiftVortexScale;
        uniform float uRiftLightning;
        uniform vec3 uRiftDir;
        varying vec3 vWorldDir;

        void main() {
          vec3 dir = normalize(vWorldDir);
          float y = dir.y;

          // 1. Atmosphärischer Rayleigh-Gradient (Zenit -> Horizont -> Dunst)
          float zenithCurve = pow(clamp(y, 0.0, 1.0), 0.42 / max(0.25, uRayleigh));
          vec3 sky = mix(uHorizonColor, uZenithColor, zenithCurve);

          // Horizont-Aerosol-Gürtel (warmer goldener Horizontsaum bei Sonnenaufgang/-untergang wie in Bild 3 Oben)
          vec3 normSun = normalize(uSunDir);
          float sunDot = max(dot(dir, normSun), 0.0);
          float horizonBand = exp(-abs(y) * 5.2);
          vec3 goldenBandCol = mix(uSunColor, vec3(1.0, 0.56, 0.20), uTwilight * 0.78);
          sky += goldenBandCol * horizonBand * (0.12 + 0.42 * pow(sunDot, 2.2)) * uTwilight * uScattering * (1.0 - uCloudiness * 0.55);

          // 1B. Rissmonolithen V2: Dramatischer Gewitter- & Sturmhimmel mit Wolkenbänken, Dunst & gezackten Himmelsblitzen (ab 40m Annäherung)
          float riftDampen = 1.0;
          if (uRiftFactor > 0.002) {
            float rf = clamp(uRiftFactor, 0.0, 1.0);
            float aw = clamp(uRiftAwakened, 0.0, 1.0);
            riftDampen = 1.0 - rf * (0.38 + 0.22 * aw);

            float skyLum = clamp(dot(sky, vec3(0.2126, 0.7152, 0.0722)), 0.025, 0.65);
            float lumScale = clamp(0.28 + skyLum * 1.35, 0.30, 1.12);

            // Dunkle, bedrohliche Gewitter-Schiefer-/Indigo-Töne im Zenit + neblig-violettes/karmesinrotes Sturmglühen am Horizont
            vec3 violZen = vec3(0.06, 0.04, 0.16) * uRiftVioletStrength * lumScale;
            vec3 violHor = vec3(0.22, 0.10, 0.38) * uRiftVioletStrength * lumScale;
            vec3 crimZen = vec3(0.11, 0.03, 0.12) * uRiftCrimsonStrength * lumScale;
            vec3 crimHor = vec3(0.38, 0.08, 0.22) * uRiftCrimsonStrength * lumScale;

            vec3 riftSkyInstabil = mix(violHor, violZen, zenithCurve);
            vec3 riftSkyErwacht  = mix(crimHor, crimZen, zenithCurve);
            vec3 targetRiftSky   = mix(riftSkyInstabil, riftSkyErwacht, aw * 0.75);

            // Sanfte Überblendung ab 40m Annäherung bis direkt zum Rissmonolithen
            sky = mix(sky, targetRiftSky, rf * (0.72 + 0.18 * aw));

            // Atmosphärischer Gewitterdunst-Gürtel am Horizont
            float mistBand = exp(-abs(y - 0.04) * 6.5) * rf;
            vec3 mistCol = mix(vec3(0.32, 0.18, 0.52), vec3(0.52, 0.14, 0.28), aw) * lumScale;
            sky = mix(sky, mistCol, mistBand * 0.45);

            // Epischer, stationärer Himmelsriss & gezackte Gewitterblitze über dem Rissmonolithen (ohne künstliche Drehung!)
            vec3 rCenter = normalize(uRiftDir);
            vec3 upRef = abs(rCenter.y) > 0.92 ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 1.0, 0.0);
            vec3 rRight = normalize(cross(upRef, rCenter));
            vec3 rUp = cross(rCenter, rRight);
            vec2 vPlane = vec2(dot(dir, rRight), dot(dir, rUp)) / max(0.35, uRiftVortexScale * (0.78 + 0.35 * aw));
            float vDist = length(vPlane);
            float forwardMask = smoothstep(0.10, 0.62, dot(dir, rCenter)) * smoothstep(-0.02, 0.14, y);

            if (forwardMask > 0.001 && vDist < 1.35) {
              float vAngle = atan(vPlane.y, vPlane.x);
              // Gezackte, verästelte Gewitteradern statt rotierender Zielscheiben-Spirale
              float jag1 = abs(sin(vAngle * 6.0 + sin(vDist * 18.0) * 1.4));
              float jag2 = abs(cos(vAngle * 9.0 - cos(vDist * 24.0) * 1.6));
              float crackLine = smoothstep(0.86, 0.985, jag1 * 0.6 + jag2 * 0.4);
              float cloudGlowEnv = exp(-vDist * 2.6) * smoothstep(1.3, 0.05, vDist);
              float coreTear = exp(-pow(vPlane.x * 6.5 + sin(vPlane.y * 12.0) * 0.45, 2.0)) * exp(-abs(vPlane.y) * 3.8);

              vec3 veinViolet = vec3(0.72, 0.38, 1.0) * uRiftVioletStrength * (0.55 + 0.45 * lumScale);
              vec3 veinCrimson = vec3(1.0, 0.22, 0.40) * uRiftCrimsonStrength * (0.55 + 0.45 * lumScale);
              vec3 riftCol = mix(veinViolet, veinCrimson, clamp(aw * 0.72, 0.0, 1.0));

              float riftPattern = cloudGlowEnv * 0.42 + crackLine * cloudGlowEnv * 0.65 + coreTear * (0.75 + 0.25 * sin(uTime * 3.4));
              float riftStrength = rf * (0.42 + 0.52 * aw) * forwardMask;
              sky += riftCol * riftPattern * riftStrength * 0.78;

              // Gezackte Gewitter-Blitzeinschläge in den Wolken über dem Riss
              if (uRiftLightning > 0.01) {
                float boltBranch = smoothstep(0.90, 0.995, sin(vAngle * 8.0 + sin(vDist * 22.0 + uTime * 14.0) * 1.8)) * cloudGlowEnv;
                vec3 flashCol = mix(vec3(0.86, 0.72, 1.0), vec3(1.0, 0.42, 0.58), aw * 0.65);
                sky += flashCol * (boltBranch * 1.45 + coreTear * 0.95 + cloudGlowEnv * 0.48) * uRiftLightning * forwardMask;
              }
            }
          }

          // Unterhalb des Horizonts sanft in die Boden-/Nebelfarbe überblenden
          sky = mix(sky, mix(uHorizonColor, uGroundColor, 0.65), smoothstep(0.02, -0.22, y));

          // 2. Physikalisch plausible Mie-Vorwärtsstreuung (weiche atmosphärische Korona ohne künstliche 2D-Strahlen)
          float cloudTrans = (1.0 - uCloudiness * 0.72) * (1.0 - uSunOcclusion * 0.65) * riftDampen;
          float mieWide = pow(sunDot, 5.5) * 0.16;
          float mieInner = pow(sunDot, 36.0) * 0.34 + pow(sunDot, 160.0) * 0.48;
          vec3 coronaCol = mix(uSunColor, vec3(1.0, 0.68, 0.32), uTwilight * 0.65);
          if (uRiftFactor > 0.01) {
            coronaCol = mix(coronaCol, mix(vec3(0.78, 0.42, 1.0), vec3(1.0, 0.25, 0.38), uRiftAwakened), uRiftFactor * 0.55);
          }
          sky += coronaCol * (mieWide + mieInner * cloudTrans) * uMieHalo * uScattering * clamp(uSunIntensity * 0.75, 0.0, 1.5);

          // 3. Natürlich wirkende Sonnenscheibe mit physikalischem Limb-Darkening (sinkt vollständig bis hinter den Horizont!)
          float cosSunRadius = 0.99945; // ~1.9° scheinbarer Durchmesser für harmonische MMORPG-Optik
          if (sunDot > cosSunRadius && y > -0.10) {
            float mu = sqrt(clamp((sunDot - cosSunRadius) / (1.0 - cosSunRadius), 0.0, 1.0));
            // Eddington Limb-Darkening: Zentrum warm-hell, Rand weich abfallend in die Korona
            float limbDarkening = (0.38 + 0.62 * mu) * smoothstep(0.0, 0.22, mu);
            vec3 discColor = mix(vec3(1.0, 0.62, 0.28), vec3(1.0, 0.98, 0.92), mu * (1.0 - uTwilight * 0.52));
            float discVis = cloudTrans * smoothstep(-0.095, -0.025, y) * smoothstep(-0.08, -0.015, normSun.y);
            // Kontrolliertes Soft-Knee gegen Überbelichtung
            float discStrength = max(clamp(uSunIntensity, 0.0, 1.6), smoothstep(-0.075, 0.01, normSun.y) * 1.15);
            vec3 solarDisc = discColor * limbDarkening * 1.65 * discVis * discStrength;
            sky += solarDisc / (vec3(1.0) + solarDisc * 0.32);
          }

          // 4. Kühler silberblauer Mond-Halo + Dezentes Milchstraßen-Nebelband bei klarer Nacht (Bild 3 Unten)
          vec3 normMoon = normalize(uMoonDir);
          float moonDot = max(dot(dir, normMoon), 0.0);
          float moonCloudTrans = 1.0 - uCloudiness * 0.68;
          float moonHalo = (pow(moonDot, 18.0) * 0.10 + pow(moonDot, 120.0) * 0.28 + pow(moonDot, 480.0) * 0.38) * uMoonIntensity * moonCloudTrans * uScattering;
          sky += uMoonColor * moonHalo;

          if (normSun.y < -0.05 && y > 0.06 && uCloudiness < 0.75) {
            float nightClear = clamp((-normSun.y - 0.05) * 4.5, 0.0, 1.0) * (1.0 - uCloudiness * 1.15) * riftDampen;
            float galPlane = dir.x * 0.64 + dir.z * 0.48 - (y - 0.52) * 0.58;
            float galBand = exp(-galPlane * galPlane * 14.0) * smoothstep(0.06, 0.32, y);
            float galDust = 0.55 + 0.45 * sin(dir.x * 9.5 + dir.z * 7.2 + sin(dir.y * 11.0) * 1.4);
            vec3 milkyWayCol = mix(vec3(0.08, 0.15, 0.28), vec3(0.18, 0.26, 0.42), galDust);
            sky += milkyWayCol * galBand * nightClear * 0.24;
          }

          gl_FragColor = vec4(sky, 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }
      `,
    });

    this.skyDome = new THREE.Mesh(skyGeo, skyMat);
    this.skyDome.frustumCulled = false;
    this.skyDome.renderOrder = -1000;
    this.skyDome.scale.setScalar(800);
    this.scene.add(this.skyDome);

    // 2. Dynamisches Sternenfeld
    this.initStarField();

    // 3. Sichtbare 3D-Mondkugel mit Krater-Relief, Mondphasen & echter Tiefenverdeckung durch Berge/Bäume
    this.initCelestialBodies();

    if (this.engine) {
      this.engine.skyDome = this.skyDome;
      this.engine._skyUniforms = this.skyUniforms;
      this.engine.starField = this.starField;
      this.engine.moonMesh = this.moonMesh;
    }
  }

  initStarField() {
    const starCount = 1600;
    const starGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(starCount * 3);
    const colors = new Float32Array(starCount * 3);
    const sizes = new Float32Array(starCount);

    for (let i = 0; i < starCount; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(Math.sqrt(v));

      const r = 1.0; // Einheitskugel, wird mit camera.far skaliert
      const x = r * Math.sin(phi) * Math.cos(theta);
      const y = Math.max(0.03, r * Math.cos(phi));
      const z = r * Math.sin(phi) * Math.sin(theta);

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      const starType = Math.random();
      const c = new THREE.Color();
      if (starType > 0.88) c.setHex(0xfde68a);
      else if (starType > 0.62) c.setHex(0xbfdbfe);
      else if (starType > 0.48) c.setHex(0xfecaca);
      else c.setHex(0xf8fafc);

      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;

      sizes[i] = 1.1 + Math.random() * 2.2;
    }

    starGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    starGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    starGeo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    const starMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0.0 },
        uOpacity: { value: 0.0 },
      },
      transparent: true,
      depthWrite: false,
      depthTest: true,
      vertexShader: `
        attribute float size;
        attribute vec3 color;
        varying vec3 vColor;
        varying float vTwinkle;
        uniform float uTime;
        void main() {
          vColor = color;
          vTwinkle = 0.5 + 0.5 * sin(uTime * 2.8 + position.x * 21.0 + position.z * 19.0);
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = size * (0.88 + 0.28 * vTwinkle);
          vec4 p = projectionMatrix * mvPosition;
          gl_Position = vec4(p.xy, p.w * 0.99993, p.w);
        }
      `,
      fragmentShader: `
        varying vec3 vColor;
        varying float vTwinkle;
        uniform float uOpacity;
        void main() {
          vec2 coord = gl_PointCoord - vec2(0.5);
          float d = length(coord);
          if (d > 0.5) discard;
          float core = exp(-d * 8.5);
          float crossRay = max(exp(-abs(coord.x) * 22.0) * exp(-abs(coord.y) * 5.5), exp(-abs(coord.y) * 22.0) * exp(-abs(coord.x) * 5.5)) * 0.45 * vTwinkle;
          float alpha = clamp((smoothstep(0.5, 0.04, d) * 0.72 + core * 0.45 + crossRay) * uOpacity * (0.68 + 0.32 * vTwinkle), 0.0, 1.0);
          gl_FragColor = vec4(vColor * (1.0 + core * 0.35), alpha);
        }
      `,
    });

    this.starField = new THREE.Points(starGeo, starMat);
    this.starField.frustumCulled = false;
    this.starField.renderOrder = -960;
    this.starField.scale.setScalar(760);
    this.scene.add(this.starField);
  }

  initCelestialBodies() {
    // 3D-Mond mit detaillierten Maria-Becken, Strahlenkratern, Phasen-Terminator & echter Tiefenverdeckung
    const moonGeo = new THREE.SphereGeometry(1.0, 36, 36);
    this.moonUniforms = {
      uSunDir: { value: new THREE.Vector3(0.3, 0.8, 0.4) },
      uMoonColor: { value: new THREE.Color(0xdbeafe) },
      uPhaseIllum: { value: 1.0 },
      uPhaseId: { value: 4.0 },
      uOpacity: { value: 1.0 },
    };

    const moonMat = new THREE.ShaderMaterial({
      uniforms: this.moonUniforms,
      transparent: true,
      depthWrite: false,
      depthTest: true, // WICHTIG: Berge, Bäume und Gebäude verdecken den Mond korrekt!
      vertexShader: `
        varying vec3 vLocalPos;
        varying vec3 vViewNormal;
        void main() {
          vLocalPos = normalize(position);
          vViewNormal = normalize(normalMatrix * normal);
          vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          // Hinter den Wolken (0.99985) und hinter allen 3D-Bergen, aber vor dem Sternenhimmel (0.99993)
          gl_Position = vec4(p.xy, p.w * 0.99991, p.w);
        }
      `,
      fragmentShader: `
        uniform vec3 uSunDir;
        uniform vec3 uMoonColor;
        uniform float uPhaseIllum;
        uniform float uPhaseId;
        uniform float uOpacity;
        varying vec3 vLocalPos;
        varying vec3 vViewNormal;

        float hash2(vec2 p) {
          return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
        }
        float noise2(vec2 p) {
          vec2 i = floor(p);
          vec2 f = fract(p);
          f = f * f * (3.0 - 2.0 * f);
          return mix(
            mix(hash2(i), hash2(i + vec2(1.0, 0.0)), f.x),
            mix(hash2(i + vec2(0.0, 1.0)), hash2(i + vec2(1.0, 1.0)), f.x),
            f.y
          );
        }
        float fbmMoon(vec2 p) {
          float v = 0.0;
          float a = 0.52;
          for (int i = 0; i < 4; i++) {
            v += a * noise2(p);
            p = p * 2.12 + vec2(3.7, 1.9);
            a *= 0.48;
          }
          return v;
        }
        float craterRing(vec2 uv, vec2 center, float rad) {
          float d = length(uv - center) / rad;
          if (d > 1.35) return 0.0;
          float bowl = -smoothstep(0.95, 0.15, d) * 0.22;
          float rim = exp(-pow((d - 0.96) * 6.5, 2.0)) * 0.28;
          return bowl + rim;
        }

        void main() {
          vec3 N = normalize(vViewNormal);
          vec2 diskUv = N.xy;
          float r2 = dot(diskUv, diskUv);
          float mu = sqrt(max(0.0, 1.0 - r2));

          // 1. Detaillierte Mondoberfläche (Maria-Tiefebenen + Hochland-Krater + Strahlenkrater)
          vec2 sphereUv = diskUv / (0.65 + 0.35 * mu);
          float mariaMacro = fbmMoon(sphereUv * 2.4 + vec2(1.2, 0.7));
          float mariaDetail = fbmMoon(sphereUv * 6.2 - vec2(0.8, 2.1));
          float mariaMask = smoothstep(0.44, 0.68, mariaMacro * 0.72 + mariaDetail * 0.28);

          float craters = 0.0;
          craters += craterRing(sphereUv, vec2(-0.18, -0.32), 0.24);
          craters += craterRing(sphereUv, vec2(0.28, 0.16), 0.19);
          craters += craterRing(sphereUv, vec2(-0.34, 0.24), 0.16);
          craters += craterRing(sphereUv, vec2(0.08, -0.08), 0.13);
          float microCraters = (noise2(sphereUv * 18.0) - 0.5) * 0.12;

          vec3 highlandCol = vec3(0.86, 0.90, 0.96);
          vec3 mariaCol = vec3(0.46, 0.52, 0.62);
          vec3 albedo = mix(highlandCol, mariaCol, mariaMask);
          albedo += vec3(craters + microCraters);

          // 2. Exakte Mondphasen-Beleuchtung (Vollmond = 4, Zunehmend 1..3, Abnehmend 5..7, Neumond = 0)
          float phaseAngle = ((uPhaseId - 4.0) / 4.0) * 3.14159265;
          vec3 phaseLightDir = normalize(vec3(sin(phaseAngle), 0.12, cos(phaseAngle)));
          float ndotl = dot(N, phaseLightDir);
          float terminator = smoothstep(-0.12, 0.16, ndotl);

          // Sphärisches Limb-Darkening & subtiler Erdschein auf der dunklen Mondhälfte
          float limb = 0.58 + 0.42 * pow(mu, 0.45);
          vec3 earthShine = vec3(0.06, 0.10, 0.16) * limb;
          vec3 litLunar = albedo * uMoonColor * 1.28 * limb;
          vec3 finalLunar = mix(earthShine, litLunar, terminator);

          // Silberblauer Korona-Saum am beleuchteten Mondrand
          float rimGlow = pow(1.0 - mu, 2.4) * 0.42 * terminator;
          finalLunar += uMoonColor * rimGlow;

          float edgeAlpha = smoothstep(0.0, 0.18, mu);
          float visAlpha = uOpacity * edgeAlpha * mix(0.22, 1.0, terminator);
          if (visAlpha <= 0.01) discard;

          gl_FragColor = vec4(finalLunar, visAlpha);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }
      `,
    });

    this.moonMesh = new THREE.Mesh(moonGeo, moonMat);
    this.moonMesh.renderOrder = -940; // Rendert vor den Wolken (-930), sodass Wolken vor dem Mond vorbeiziehen
    this.moonMesh.frustumCulled = false;
    this.scene.add(this.moonMesh);
  }

  update(celestial, camera, dt = 0, cloudiness = 0.0, sunOcclusion = 0.0) {
    if (!this.skyUniforms || !camera) return;

    const u = this.skyUniforms;
    u.uSunDir.value.copy(celestial.sunDirection);
    u.uMoonDir.value.copy(celestial.moonDirection);
    u.uSunColor.value.copy(celestial.sunColor);
    u.uMoonColor.value.copy(celestial.moonColor);
    u.uSunIntensity.value = celestial.sunIntensity;
    u.uMoonIntensity.value = celestial.moonIntensity;
    u.uSunStrength.value = celestial.sunIntensity;
    u.uScattering.value = this.scatteringIntensity;
    u.uTwilight.value = celestial.twilightFactor;
    u.uCloudiness.value = cloudiness;
    u.uSunOcclusion.value = sunOcclusion;
    u.uTime.value += dt;

    u.uZenithColor.value.copy(celestial.zenithColor);
    u.uHorizonColor.value.copy(celestial.horizonColor);
    u.uGroundColor.value.copy(celestial.ambientGroundColor);
    u.uZenith.value.copy(celestial.zenithColor);
    u.uHorizon.value.copy(celestial.horizonColor);
    u.uGround.value.copy(celestial.ambientGroundColor);

    const farR = Math.max(400, (camera.far || 900) * 0.92);
    if (this.skyDome) {
      this.skyDome.position.copy(camera.position);
      if (Math.abs(this.skyDome.scale.x - farR) > 1.0) {
        this.skyDome.scale.setScalar(farR);
      }
    }

    if (this.starField) {
      this.starField.position.copy(camera.position);
      const starR = farR * 0.96;
      if (Math.abs(this.starField.scale.x - starR) > 1.0) {
        this.starField.scale.setScalar(starR);
      }
      this.starField.material.uniforms.uTime.value += dt;
      const sunElevDeg = (celestial.sunElevation * 180.0) / Math.PI;
      const nightAlpha = THREE.MathUtils.clamp((-sunElevDeg - 1.5) / 8.0, 0.0, 1.0);
      const starClearSky = Math.max(0.0, 1.0 - cloudiness * 0.88);
      this.starField.material.uniforms.uOpacity.value = nightAlpha * starClearSky;
      this.starField.visible = this.starField.material.uniforms.uOpacity.value > 0.015;
    }

    if (this.moonMesh) {
      const moonDist = farR * 0.86;
      const moonRadius = moonDist * 0.036; // Stimmige astronomische Größe am Nachthimmel (wie in Bild 3 Unten)
      this.moonMesh.position.copy(camera.position).addScaledVector(celestial.moonDirection, moonDist);
      this.moonMesh.scale.setScalar(moonRadius);
      this.moonMesh.lookAt(camera.position);

      const phaseMeta = MOON_PHASES[celestial.moonPhase] || MOON_PHASES[4];
      this.moonUniforms.uSunDir.value.copy(celestial.sunDirection);
      this.moonUniforms.uMoonColor.value.copy(celestial.moonColor);
      this.moonUniforms.uPhaseIllum.value = phaseMeta.illumination;
      this.moonUniforms.uPhaseId.value = celestial.moonPhase;

      const moonElevVis = THREE.MathUtils.smoothstep(celestial.moonElevation, -0.05, 0.14);
      const dayFade = 1.0 - THREE.MathUtils.smoothstep((celestial.sunElevation * 180.0) / Math.PI, -2.0, 10.0) * 0.82;
      const cloudFade = Math.max(0.08, 1.0 - cloudiness * 0.78);
      this.moonUniforms.uOpacity.value = moonElevVis * dayFade * cloudFade;
      this.moonMesh.visible = this.moonUniforms.uOpacity.value > 0.02;
    }
  }

  dispose() {
    if (this.skyDome) {
      this.scene.remove(this.skyDome);
      this.skyDome.geometry.dispose();
      this.skyDome.material.dispose();
      this.skyDome = null;
    }
    if (this.starField) {
      this.scene.remove(this.starField);
      this.starField.geometry.dispose();
      this.starField.material.dispose();
      this.starField = null;
    }
    if (this.moonMesh) {
      this.scene.remove(this.moonMesh);
      this.moonMesh.geometry.dispose();
      this.moonMesh.material.dispose();
      this.moonMesh = null;
    }
  }
}

// ============================================================================
// 4. SUNBEAM & MOONBEAM RENDERER (WEBGL2 DEPTH-OCCLUDED GOD RAYS + BLOOM)
// ============================================================================
export class SunbeamRenderer {
  constructor(renderer, options = {}) {
    this.renderer = renderer;
    this.enabled = options.enabled !== false;
    this.quality = options.quality ?? 2; // 0=Off, 1=Low(24), 2=Med/High(48), 3=Ultra(64)
    this.intensity = options.intensity ?? 1.0;
    this.density = options.density ?? 0.92;
    this.bloomIntensity = options.bloomIntensity ?? 0.45;

    this.lightScreenPos = new THREE.Vector2(0.5, 0.5);
    this.tempVec3 = new THREE.Vector3();
    this._bufSize = new THREE.Vector2();
    this._frameTick = 0;

    this.occScene = new THREE.Scene();
    this.quadScene = new THREE.Scene();
    this.quadCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    this._prevClearColor = new THREE.Color();

    this.initPasses();
    this._applySampleCount();
  }

  _applySampleCount() {
    if (this.beamMaterial) {
      this.beamMaterial.uniforms.uSamples.value = this.quality >= 3 ? 64 : this.quality === 2 ? 48 : 28;
    }
  }

  setQuality(q) {
    this.quality = Math.max(0, Math.min(3, Math.floor(q)));
    this.enabled = this.quality > 0;
    this._applySampleCount();
  }

  initPasses() {
    // 1. Low-Res Occlusion RenderTarget (speichert sichtbare Himmels-/Wolkenlücken vs. schwarze 3D-Geometrie)
    this.occTarget = new THREE.WebGLRenderTarget(480, 270, {
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      format: THREE.RGBAFormat,
      depthBuffer: true,
      stencilBuffer: false,
    });

    // 2. Himmels- & Wolkenlücken-Emitter-Kuppel (berechnet exakt, wo Licht durch Wolkenlücken bricht!)
    this.emitterUniforms = {
      uLightDir: { value: new THREE.Vector3(0.3, 0.8, 0.4) },
      uLightColor: { value: new THREE.Color(0xfff1d0) },
      uCoverage: { value: 0.42 },
      uCloudDensity: { value: 1.15 },
      uWindOffset: { value: new THREE.Vector2(0, 0) },
      uCloudTime: { value: 0.0 },
      uIsMoon: { value: 0.0 },
      uSceneDepthTex: { value: null },
      uHasSceneDepth: { value: 0.0 },
    };

    this.emitterMaterial = new THREE.ShaderMaterial({
      uniforms: this.emitterUniforms,
      side: THREE.BackSide,
      depthWrite: false,
      depthTest: false,
      vertexShader: `
        varying vec3 vWorldDir;
        varying vec4 vClipPos;
        void main() {
          vWorldDir = normalize(position);
          vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          gl_Position = vec4(p.xy, p.w * 0.9999, p.w);
          vClipPos = gl_Position;
        }
      `,
      fragmentShader: `
        uniform vec3 uLightDir;
        uniform vec3 uLightColor;
        uniform float uCoverage;
        uniform float uCloudDensity;
        uniform vec2 uWindOffset;
        uniform float uCloudTime;
        uniform float uIsMoon;
        uniform sampler2D uSceneDepthTex;
        uniform float uHasSceneDepth;
        varying vec3 vWorldDir;
        varying vec4 vClipPos;

        float hash12(vec2 p) {
          vec3 p3 = fract(vec3(p.xyx) * 0.1031);
          p3 += dot(p3, p3.yzx + 33.33);
          return fract((p3.x + p3.y) * p3.z);
        }
        float noise2D(vec2 p) {
          vec2 i = floor(p);
          vec2 f = fract(p);
          f = f * f * (3.0 - 2.0 * f);
          return mix(
            mix(hash12(i), hash12(i + vec2(1.0, 0.0)), f.x),
            mix(hash12(i + vec2(0.0, 1.0)), hash12(i + vec2(1.0, 1.0)), f.x),
            f.y
          );
        }
        float fbmClouds(vec2 p) {
          float v = 0.0;
          float a = 0.54;
          for (int i = 0; i < 4; i++) {
            v += a * noise2D(p);
            p = p * 2.08 + vec2(1.7, 3.1);
            a *= 0.46;
          }
          return v;
        }

        void main() {
          // O(1) Hardware-Depth-Occlusion aus dem HDR-SceneTarget:
          // Alle 3D-Objekte (Bäume, Blätter, Berge, Gebäude, Charaktere) haben depth < 0.9996, während Himmel & Wolken depthWrite:false haben!
          // Dadurch sparen wir uns den kompletten zweiten Full-Scene-Override-Renderpass!
          if (uHasSceneDepth > 0.5) {
            vec2 screenUv = (vClipPos.xy / max(0.0001, vClipPos.w)) * 0.5 + 0.5;
            float hwDepth = texture2D(uSceneDepthTex, screenUv).r;
            if (hwDepth < 0.9995) {
              gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
              return;
            }
          }

          vec3 dir = normalize(vWorldDir);
          if (dir.y <= -0.02) {
            gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
            return;
          }

          vec3 L = normalize(uLightDir);
          float cosTheta = max(dot(dir, L), 0.0);

          // Enger, konzentrierter Lichtkegel direkt um die Sonnen-/Mondscheibe (verhindert großflächiges Überstrahlen des Himmels!)
          float cone = uIsMoon > 0.5
            ? (pow(cosTheta, 36.0) * 0.32 + pow(cosTheta, 120.0) * 0.55)
            : (pow(cosTheta, 48.0) * 0.28 + pow(cosTheta, 180.0) * 0.52);

          // Wolkenlücken-Maske: Dichte Wolken blockieren das Licht, während Wolkenlücken & dünne Wolkenränder helle Strahlen erzeugen!
          float gapTrans = 1.0;
          if (dir.y > 0.01 && uCoverage > 0.02) {
            vec2 cUv = dir.xz / (dir.y + 0.16) * 0.65 + uWindOffset * 0.25;
            float n1 = fbmClouds(cUv * 1.4 + vec2(uCloudTime * 0.012, -uCloudTime * 0.008));
            float n2 = fbmClouds(cUv * 3.1 - vec2(uCloudTime * 0.018, uCloudTime * 0.014));
            float cShape = n1 * 0.68 + n2 * 0.32;
            float thresh = 1.0 - uCoverage * 1.08;
            float cMask = smoothstep(thresh - 0.06, thresh + 0.22, cShape);
            float silverRim = smoothstep(thresh - 0.08, thresh + 0.04, cShape) * (1.0 - smoothstep(thresh + 0.04, thresh + 0.20, cShape));
            gapTrans = clamp(1.0 - cMask * clamp(uCloudDensity * 0.72, 0.25, 0.94) + silverRim * 0.25, 0.04, 1.05);
          }

          float horizonFade = smoothstep(-0.02, 0.12, dir.y);
          vec3 srcCol = uLightColor * cone * gapTrans * horizonFade;
          gl_FragColor = vec4(srcCol, 1.0);
        }
      `,
    });

    this.emitterDome = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 20), this.emitterMaterial);
    this.emitterDome.frustumCulled = false;
    this.occScene.add(this.emitterDome);

    // 3. Schneller 3D-Geometrie-Occluder-Shader (Berge, Terrain, Bäume mit Wind & Blattlücken, Gebäude, Ruinen)
    this.occluderMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0.0 },
        uWindStrength: { value: 0.45 },
      },
      side: THREE.DoubleSide,
      depthWrite: true,
      depthTest: true,
      vertexShader: `
        varying vec3 vWorldPos;
        varying float vIsInstancedCanopy;
        uniform float uTime;
        uniform float uWindStrength;
        void main() {
          vec3 transformed = position;
          vec4 wPos = vec4(transformed, 1.0);
          vIsInstancedCanopy = 0.0;
          #ifdef USE_INSTANCING
            vec3 instOrigin = (modelMatrix * instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
            float branchRadius = length(transformed.xz);
            if (transformed.y > 2.1 && branchRadius > 0.38) {
              vIsInstancedCanopy = 1.0;
              float swayWeight = smoothstep(0.12, 2.1, branchRadius + max(0.0, transformed.y - 0.25) * 0.32);
              float boughPhase = uTime * 1.55 + instOrigin.x * 0.17 + instOrigin.z * 0.13 + transformed.y * 0.30;
              float boughSway = sin(boughPhase) + 0.38 * cos(uTime * 2.4 - instOrigin.x * 0.23 + instOrigin.z * 0.19);
              transformed.x += boughSway * 0.20 * swayWeight * uWindStrength;
              transformed.z += boughSway * 0.14 * swayWeight * uWindStrength;
            }
            wPos = modelMatrix * instanceMatrix * vec4(transformed, 1.0);
          #else
            wPos = modelMatrix * vec4(transformed, 1.0);
          #endif
          vWorldPos = wPos.xyz;
          gl_Position = projectionMatrix * viewMatrix * wPos;
        }
      `,
      fragmentShader: `
        varying vec3 vWorldPos;
        varying float vIsInstancedCanopy;
        void main() {
          // Natürliche Blattlücken in Baumkronen, damit Sonnen- & Mondstrahlen malerisch zwischen Ästen und Blättern hindurchbrechen!
          if (vIsInstancedCanopy > 0.5) {
            float leafGap = sin(vWorldPos.x * 3.4 + vWorldPos.y * 2.9) * cos(vWorldPos.z * 3.2 - vWorldPos.y * 2.5);
            if (leafGap > 0.42) discard;
          }
          gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
        }
      `,
    });

    // 4. Screen-Space Volumetric Raymarching + Temporal Jitter + Controlled Atmospheric Bloom
    this.beamMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uOcclusionTex: { value: this.occTarget.texture },
        uLightScreenPos: { value: this.lightScreenPos },
        uLightColor: { value: new THREE.Color(0xfff1d0) },
        uVisibility: { value: 1.0 },
        uIntensity: { value: 1.0 },
        uDensity: { value: 0.92 },
        uBloomIntensity: { value: 0.45 },
        uSamples: { value: 48 },
        uFrameJitter: { value: 0.0 },
      },
      blending: THREE.AdditiveBlending,
      transparent: true,
      depthWrite: false,
      depthTest: false,
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position.xy, 0.0, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D uOcclusionTex;
        uniform vec2 uLightScreenPos;
        uniform vec3 uLightColor;
        uniform float uVisibility;
        uniform float uIntensity;
        uniform float uDensity;
        uniform float uBloomIntensity;
        uniform int uSamples;
        uniform float uFrameJitter;
        varying vec2 vUv;

        // Interleaved Gradient Noise für temporale Stabilisierung ohne Banding
        float ign(vec2 pixel) {
          return fract(52.9829189 * fract(0.06711056 * pixel.x + 0.00583715 * pixel.y) + uFrameJitter);
        }

        void main() {
          if (uVisibility <= 0.004) discard;

          vec2 delta = (vUv - uLightScreenPos) * clamp(uDensity, 0.25, 1.8);
          float dist = length(vUv - uLightScreenPos);
          int steps = clamp(uSamples, 16, 64);
          vec2 stepUv = delta / float(steps);

          // Jitter-Startpunkt für butterweiche Lichtkegel ohne Stufenartefakte
          float jitter = ign(gl_FragCoord.xy);
          vec2 sampleUv = vUv - stepUv * jitter;

          vec3 accumRays = vec3(0.0);
          float illuminationDecay = 1.0;
          float decay = 0.968;
          float weight = 1.0 / float(steps);

          for (int i = 0; i < 64; i++) {
            if (i >= steps) break;
            sampleUv -= stepUv;
            if (sampleUv.x >= 0.002 && sampleUv.x <= 0.998 && sampleUv.y >= 0.002 && sampleUv.y <= 0.998) {
              vec4 occSample = texture2D(uOcclusionTex, sampleUv);
              accumRays += occSample.rgb * illuminationDecay * weight;
            }
            illuminationDecay *= decay;
          }

          // Sanfte volumetrische Lichtstrahlen nahe der Sonne + kontrollierter atmosphärischer Golden-Hour-Bloom ohne Himmels-Washout
          float radialFalloff = pow(smoothstep(0.78, 0.0, dist), 1.65);
          float coreBloom = exp(-dist * 5.8) * clamp(uBloomIntensity, 0.0, 1.6) * 0.072;
          vec3 volumetricShafts = accumRays * (radialFalloff * 0.34 + coreBloom) * uVisibility * uIntensity;

          vec3 totalLight = volumetricShafts / (vec3(1.0) + volumetricShafts * 4.8);

          // Weiche Ausblendung am äußersten Bildschirmrand
          vec2 edge = smoothstep(vec2(0.0), vec2(0.08), vUv) * smoothstep(vec2(1.0), vec2(0.92), vUv);
          totalLight *= edge.x * edge.y;

          if (dot(totalLight, vec3(1.0)) <= 0.001) discard;
          gl_FragColor = vec4(totalLight, 1.0);
        }
      `,
    });

    this.quadMesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.beamMaterial);
    this.quadScene.add(this.quadMesh);
  }

  renderVolumetricPass(engine, camera, celestial, clouds, visibility = 1.0, isMoon = false) {
    if (!this.enabled || this.quality <= 0 || visibility <= 0.008 || !engine || !camera) {
      return false;
    }

    const lightDir = isMoon ? celestial.moonDirection : celestial.sunDirection;
    const lightColor = isMoon ? celestial.moonColor : celestial.sunColor;

    // 1. Prüfen, ob die Lichtquelle vor der Kamera liegt (Skalarprodukt mit Kamera-Blickrichtung)
    const camForward = this.tempVec3.set(0, 0, -1).applyQuaternion(camera.quaternion).normalize();
    const viewDot = camForward.dot(lightDir);
    if (viewDot <= 0.25) {
      return false;
    }

    // 2. Lichtquelle in Bildschirmkoordinaten [0, 1] projizieren
    const lightWorldPos = this.tempVec3.copy(camera.position).addScaledVector(lightDir, 500.0);
    lightWorldPos.project(camera);
    if (lightWorldPos.z >= 1.0) {
      return false;
    }

    this.lightScreenPos.x = lightWorldPos.x * 0.5 + 0.5;
    this.lightScreenPos.y = lightWorldPos.y * 0.5 + 0.5;

    if (
      this.lightScreenPos.x < -0.15 ||
      this.lightScreenPos.x > 1.15 ||
      this.lightScreenPos.y < -0.15 ||
      this.lightScreenPos.y > 1.15
    ) {
      return false;
    }
    const screenEdgeFadeX =
      THREE.MathUtils.smoothstep(this.lightScreenPos.x, -0.15, 0.12) *
      (1.0 - THREE.MathUtils.smoothstep(this.lightScreenPos.x, 0.88, 1.15));
    const screenEdgeFadeY =
      THREE.MathUtils.smoothstep(this.lightScreenPos.y, -0.15, 0.12) *
      (1.0 - THREE.MathUtils.smoothstep(this.lightScreenPos.y, 0.88, 1.15));
    const screenEdgeFade = screenEdgeFadeX * screenEdgeFadeY;
    if (screenEdgeFade <= 0.005) {
      return false;
    }

    // 3. Größe des Occlusion-RenderTargets an Qualitätsstufe anpassen
    this.renderer.getDrawingBufferSize(this._bufSize);
    const scale = this.quality >= 3 ? 0.42 : this.quality === 2 ? 0.34 : 0.25;
    const tw = Math.max(240, Math.floor(this._bufSize.x * scale));
    const th = Math.max(135, Math.floor(this._bufSize.y * scale));
    if (this.occTarget.width !== tw || this.occTarget.height !== th) {
      this.occTarget.setSize(tw, th);
    }

    // 4. Emitter-Uniforms aktualisieren
    this.emitterUniforms.uLightDir.value.copy(lightDir);
    this.emitterUniforms.uLightColor.value.copy(lightColor);
    this.emitterUniforms.uCoverage.value = clouds ? clouds.coverage : 0.35;
    this.emitterUniforms.uCloudDensity.value = clouds ? clouds.density : 1.0;
    if (clouds?.windOffset) {
      this.emitterUniforms.uWindOffset.value.copy(clouds.windOffset);
    }
    this.emitterUniforms.uCloudTime.value = clouds ? clouds.cloudTime : performance.now() * 0.001;
    this.emitterUniforms.uIsMoon.value = isMoon ? 1.0 : 0.0;

    this.emitterDome.position.copy(camera.position);
    this.emitterDome.scale.setScalar(Math.max(400, (camera.far || 900) * 0.9));

    if (engine._grassShaderUniforms) {
      this.occluderMaterial.uniforms.uTime.value = engine._grassShaderUniforms.uTime.value;
      this.occluderMaterial.uniforms.uWindStrength.value = engine._grassShaderUniforms.uWindStrength.value;
    }

    // 5. Occlusion-Pass rendern:
    //    Wenn das Post-Processing-HDR-SceneTarget aktiv ist, nutzen wir dessen bereits gerenderte Hardware-DepthTexture in O(1) (1 Draw-Call!),
    //    ohne die gesamte 3D-Szene ein zweites Mal mit overrideMaterial traversieren zu müssen!
    const prevTarget = this.renderer.getRenderTarget();
    const prevAutoClear = this.renderer.autoClear;
    const prevShadowAuto = this.renderer.shadowMap.autoUpdate;
    const prevOverride = engine.scene.overrideMaterial;
    // Clear-Farbe sichern: setClearColor(0, 0) darf die Hauptszene (beginScenePass -> clear()) nicht verfälschen
    this.renderer.getClearColor(this._prevClearColor);
    const prevClearAlpha = this.renderer.getClearAlpha();

    const ppDepthTex =
      engine.dayNightSystem?.postProcessing?.enabled &&
      (engine._ppTier ?? 1) > 0 &&
      (engine._masterTier ?? 1) > 0
        ? engine.dayNightSystem.postProcessing.sceneTarget?.depthTexture
        : null;

    if (ppDepthTex) {
      this.emitterUniforms.uSceneDepthTex.value = ppDepthTex;
      this.emitterUniforms.uHasSceneDepth.value = 1.0;

      this.renderer.shadowMap.autoUpdate = false;
      this.renderer.setRenderTarget(this.occTarget);
      this.renderer.autoClear = false;
      this.renderer.setClearColor(0x000000, 0.0);
      this.renderer.clear(true, true, false);
      this.renderer.render(this.occScene, camera);
      this.renderer.setRenderTarget(prevTarget);
      this.renderer.shadowMap.autoUpdate = prevShadowAuto;
    } else {
      this.emitterUniforms.uSceneDepthTex.value = null;
      this.emitterUniforms.uHasSceneDepth.value = 0.0;

      // Fallback (nur wenn Post-Processing deaktiviert ist): Jedes 2. Frame schlanker Occlusion-Pass
      this._occStrideTick = ((this._occStrideTick || 0) + 1) % 2;
      if (!this._occRenderedOnce || this._occStrideTick === 0) {
        this._occRenderedOnce = true;
        if (!this._hiddenBuffer) this._hiddenBuffer = [];
        const hidden = this._hiddenBuffer;
        hidden.length = 0;

        const hideObj = (o) => {
          if (o && o.visible) {
            o.visible = false;
            hidden.push(o);
          }
        };
        hideObj(engine.skyDome);
        hideObj(engine.starField);
        hideObj(engine.moonMesh);
        hideObj(clouds?.cloudDomeMesh);
        hideObj(engine.terrainMesh);
        if (engine.terrainChunks) {
          for (let i = 0; i < engine.terrainChunks.length; i++) hideObj(engine.terrainChunks[i]);
        }
        hideObj(engine.grassClumpInst);
        hideObj(engine.grassTallInst);
        hideObj(engine.grassTexturedInst);
        hideObj(engine.fernFoliageInst);
        hideObj(engine.groundLeafInst);
        hideObj(engine.fallenLogInst);
        hideObj(engine.bushFoliageInst);
        if (engine.naturePropChunks) {
          for (let i = 0; i < engine.naturePropChunks.length; i++) {
            hideObj(engine.naturePropChunks[i].group);
          }
        }
        if (engine._cullableStaticNodes) {
          for (let i = 0; i < engine._cullableStaticNodes.length; i++) {
            hideObj(engine._cullableStaticNodes[i].obj);
          }
        }
        hideObj(engine._fallingLeaves?.mesh);
        hideObj(engine.entityGroup);
        hideObj(engine.riverMesh);
        hideObj(engine.northRiverMesh);
        hideObj(engine.northLakeMesh);
        hideObj(engine.rainSystem);
        hideObj(engine.snowSystem);
        hideObj(engine.leafSystem);
        hideObj(engine.worldParticles);
        hideObj(engine.autoFarmRing);
        hideObj(engine.targetSelectionRing);
        hideObj(engine.clickIndicator);
        if (engine.treeChunks) {
          for (let i = 0; i < engine.treeChunks.length; i++) {
            const ch = engine.treeChunks[i];
            hideObj(ch.fol1);
            hideObj(ch.fol3);
            hideObj(ch.lodBillboard);
            if (ch.lodLevel >= 2) {
              hideObj(ch.trunk);
              hideObj(ch.fol2);
            }
          }
        }

        this.renderer.shadowMap.autoUpdate = false;
        this.renderer.setRenderTarget(this.occTarget);
        this.renderer.autoClear = false;
        this.renderer.setClearColor(0x000000, 0.0);
        this.renderer.clear(true, true, false);

        // 5a) Himmels- & Wolkenlücken-Quelle rendern
        this.renderer.render(this.occScene, camera);

        // 5b) Nahe Bäume als schnelle Tiefen-Occluder rendern
        engine.scene.overrideMaterial = this.occluderMaterial;
        this.renderer.render(engine.scene, camera);
        engine.scene.overrideMaterial = prevOverride;

        for (let i = 0; i < hidden.length; i++) {
          hidden[i].visible = true;
        }
        hidden.length = 0;
        this.renderer.setRenderTarget(prevTarget);
        this.renderer.shadowMap.autoUpdate = prevShadowAuto;
      }
    }

    this.renderer.setClearColor(this._prevClearColor, prevClearAlpha);

    // 6. Volumetrische Lichtstrahlen (Sunbeams / Moonbeams) + kontrolliertes Bloom additiv über die Szene blenden
    this._frameTick = (this._frameTick + 1) % 64;
    const u = this.beamMaterial.uniforms;
    u.uLightScreenPos.value.copy(this.lightScreenPos);
    u.uLightColor.value.copy(lightColor);
    u.uVisibility.value = visibility * screenEdgeFade * THREE.MathUtils.smoothstep(viewDot, 0.25, 0.62);
    u.uIntensity.value = this.intensity;
    u.uDensity.value = this.density;
    u.uBloomIntensity.value = this.bloomIntensity;
    u.uFrameJitter.value = (this._frameTick * 0.61803398875) % 1.0;

    this.renderer.autoClear = false;
    this.renderer.render(this.quadScene, this.quadCamera);
    this.renderer.autoClear = prevAutoClear;

    return true;
  }

  resize() {
    // Dynamische Skalierung erfolgt automatisch in renderVolumetricPass
  }

  dispose() {
    if (this.occTarget) this.occTarget.dispose();
    if (this.emitterDome) this.emitterDome.geometry.dispose();
    if (this.quadMesh) this.quadMesh.geometry.dispose();
    if (this.emitterMaterial) this.emitterMaterial.dispose();
    if (this.occluderMaterial) this.occluderMaterial.dispose();
    if (this.beamMaterial) this.beamMaterial.dispose();
  }
}

// ============================================================================
// 4B. NEXT-GEN HDR POST-PROCESSING COMPOSER (GTAO/SSAO + UNREAL BLOOM + CAS + ACES)
// ============================================================================
export class PostProcessingComposer {
  constructor(renderer, engine) {
    this.renderer = renderer;
    this.engine = engine;
    this.enabled = true;
    this._bufSize = new THREE.Vector2();
    this._frameTick = 0;

    this.quadScene = new THREE.Scene();
    this.quadCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.initTargetsAndPasses();
  }

  initTargetsAndPasses() {
    const w = 1280;
    const h = 720;

    const depthTex = new THREE.DepthTexture(w, h);
    depthTex.type = THREE.UnsignedIntType;
    depthTex.minFilter = THREE.NearestFilter;
    depthTex.magFilter = THREE.NearestFilter;

    this.sceneTarget = new THREE.WebGLRenderTarget(w, h, {
      type: THREE.HalfFloatType,
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      depthBuffer: true,
      depthTexture: depthTex,
    });

    this.ssaoTarget = new THREE.WebGLRenderTarget(Math.floor(w * 0.85), Math.floor(h * 0.85), {
      type: THREE.UnsignedByteType,
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      depthBuffer: false,
    });

    this.bloomTargetA = new THREE.WebGLRenderTarget(Math.floor(w * 0.35), Math.floor(h * 0.35), {
      type: THREE.HalfFloatType,
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      depthBuffer: false,
    });

    this.bloomTargetB = new THREE.WebGLRenderTarget(Math.floor(w * 0.35), Math.floor(h * 0.35), {
      type: THREE.HalfFloatType,
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      depthBuffer: false,
    });

    // 1. High-Res Dual-Scale GTAO / SSAO Shader (Mikro-Kontaktschatten an Stiefeln/Rüstungsfugen + Makro-Bodenverankerung)
    this.ssaoMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uDepthTex: { value: this.sceneTarget.depthTexture },
        uResolution: { value: new THREE.Vector2(w * 0.85, h * 0.85) },
        uCameraNear: { value: 0.35 },
        uCameraFar: { value: 900.0 },
        uRadius: { value: 1.38 },
        uIntensity: { value: 1.28 },
      },
      depthWrite: false,
      depthTest: false,
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position.xy, 0.0, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D uDepthTex;
        uniform vec2 uResolution;
        uniform float uCameraNear;
        uniform float uCameraFar;
        uniform float uRadius;
        uniform float uIntensity;
        varying vec2 vUv;

        float linearizeZ(float d) {
          float zn = 2.0 * d - 1.0;
          return (2.0 * uCameraNear * uCameraFar) / max(0.0001, uCameraFar + uCameraNear - zn * (uCameraFar - uCameraNear));
        }

        float ign(vec2 p) {
          return fract(52.9829189 * fract(0.06711056 * p.x + 0.00583715 * p.y));
        }

        void main() {
          float rawD = texture2D(uDepthTex, vUv).r;
          if (rawD >= 0.9995) {
            gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
            return;
          }
          float centerZ = linearizeZ(rawD);
          if (centerZ > 125.0) {
            gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
            return;
          }

          vec2 texel = 1.0 / max(vec2(1.0), uResolution);
          float zR = linearizeZ(texture2D(uDepthTex, vUv + vec2(texel.x, 0.0)).r);
          float zL = linearizeZ(texture2D(uDepthTex, vUv - vec2(texel.x, 0.0)).r);
          float zU = linearizeZ(texture2D(uDepthTex, vUv + vec2(0.0, texel.y)).r);
          float zD = linearizeZ(texture2D(uDepthTex, vUv - vec2(0.0, texel.y)).r);

          float slopeX = (abs(zR - centerZ) < abs(centerZ - zL)) ? (zR - centerZ) : (centerZ - zL);
          float slopeY = (abs(zU - centerZ) < abs(centerZ - zD)) ? (zU - centerZ) : (centerZ - zD);

          float noiseVal = ign(gl_FragCoord.xy);
          float rotAngle = noiseVal * 6.2831853;

          // Skala A: 4 enge Mikro-Kontaktschatten-Taps (Stiefelsohlen auf Kopfsteinpflaster, Kleidungsschichten, Rüstungskanten)
          float microRad = clamp(6.5 / max(1.8, centerZ * 0.45), 1.35, 6.0);
          float microOcc = 0.0;
          for (int m = 0; m < 4; m++) {
            float fm = float(m);
            float mAng = rotAngle + fm * 1.5707963;
            vec2 mOff = vec2(cos(mAng), sin(mAng)) * (microRad * (0.55 + 0.45 * fract(noiseVal + fm * 0.25)));
            float mRaw = texture2D(uDepthTex, vUv + mOff * texel).r;
            if (mRaw < 0.9995) {
              float mZ = linearizeZ(mRaw);
              float expZ = centerZ + slopeX * mOff.x + slopeY * mOff.y;
              float zDiff = expZ - mZ;
              float mRange = smoothstep(0.0, 1.0, 0.34 / max(0.03, abs(centerZ - mZ)));
              microOcc += step(0.009, zDiff) * smoothstep(0.009, 0.11, zDiff) * mRange;
            }
          }
          microOcc *= 0.25;

          // Skala B: 8 Golden-Angle Makro-GTAO-Taps (weiche Umgebungsverdeckung unter Charakteren, Pferden, Mauern & Felsen)
          float screenRad = clamp(uRadius * 23.0 / max(2.2, centerZ), 2.2, 22.0);
          float macroOcc = 0.0;
          for (int i = 0; i < 8; i++) {
            float fi = float(i);
            float r = (fi + 0.45) / 8.0;
            float ang = rotAngle + fi * 2.3999632;
            vec2 dir = vec2(cos(ang), sin(ang));
            vec2 offsetPx = dir * (r * screenRad);
            vec2 sUv = vUv + offsetPx * texel;
            float sRaw = texture2D(uDepthTex, sUv).r;
            if (sRaw < 0.9995) {
              float sampleZ = linearizeZ(sRaw);
              float expectedZ = centerZ + slopeX * offsetPx.x + slopeY * offsetPx.y;
              float zDiff = expectedZ - sampleZ;
              float rangeCheck = smoothstep(0.0, 1.0, (uRadius * 1.55) / max(0.07, abs(centerZ - sampleZ)));
              macroOcc += step(0.026, zDiff) * smoothstep(0.026, 0.46, zDiff) * rangeCheck;
            }
          }
          macroOcc *= 0.125;

          float occ = (microOcc * 0.48 + macroOcc * 0.64) * uIntensity;
          float distFade = 1.0 - smoothstep(58.0, 118.0, centerZ);
          float ao = clamp(1.0 - occ * distFade, 0.25, 1.0);
          gl_FragColor = vec4(ao, ao, ao, 1.0);
        }
      `,
    });

    // 2A. Unreal-Bloom Threshold & 9-Tap Karis Downsample
    this.bloomExtractMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uSceneTex: { value: this.sceneTarget.texture },
        uTexelSize: { value: new THREE.Vector2(1.0 / w, 1.0 / h) },
        uThreshold: { value: 0.82 },
        uSoftKnee: { value: 0.38 },
      },
      depthWrite: false,
      depthTest: false,
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position.xy, 0.0, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D uSceneTex;
        uniform vec2 uTexelSize;
        uniform float uThreshold;
        uniform float uSoftKnee;
        varying vec2 vUv;

        vec3 extractBright(vec3 c) {
          c = min(c, vec3(12.0)); // Clamp gegen extreme Fireflies
          float br = max(c.r, max(c.g, c.b));
          float knee = uThreshold * uSoftKnee + 0.0001;
          float soft = clamp(br - uThreshold + knee, 0.0, 2.0 * knee);
          soft = (soft * soft) / (4.0 * knee);
          float contrib = max(soft, br - uThreshold) / max(br, 0.0001);
          return c * max(0.0, contrib);
        }

        void main() {
          vec2 d = uTexelSize * 1.5;
          vec3 c0 = extractBright(texture2D(uSceneTex, vUv).rgb) * 0.28;
          vec3 c1 = extractBright(texture2D(uSceneTex, vUv + vec2(-d.x, -d.y)).rgb) * 0.18;
          vec3 c2 = extractBright(texture2D(uSceneTex, vUv + vec2( d.x, -d.y)).rgb) * 0.18;
          vec3 c3 = extractBright(texture2D(uSceneTex, vUv + vec2(-d.x,  d.y)).rgb) * 0.18;
          vec3 c4 = extractBright(texture2D(uSceneTex, vUv + vec2( d.x,  d.y)).rgb) * 0.18;
          gl_FragColor = vec4(c0 + c1 + c2 + c3 + c4, 1.0);
        }
      `,
    });

    // 2B. Unreal-Bloom 9-Tap Tent-Filter Blur
    this.bloomBlurMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uBloomTex: { value: this.bloomTargetA.texture },
        uTexelSize: { value: new THREE.Vector2(1.0 / (w * 0.35), 1.0 / (h * 0.35)) },
      },
      depthWrite: false,
      depthTest: false,
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position.xy, 0.0, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D uBloomTex;
        uniform vec2 uTexelSize;
        varying vec2 vUv;

        void main() {
          vec2 d = uTexelSize * 2.15;
          vec3 s = texture2D(uBloomTex, vUv).rgb * 0.25;
          s += texture2D(uBloomTex, vUv + vec2( d.x,  0.0)).rgb * 0.125;
          s += texture2D(uBloomTex, vUv + vec2(-d.x,  0.0)).rgb * 0.125;
          s += texture2D(uBloomTex, vUv + vec2( 0.0,  d.y)).rgb * 0.125;
          s += texture2D(uBloomTex, vUv + vec2( 0.0, -d.y)).rgb * 0.125;
          s += texture2D(uBloomTex, vUv + vec2( d.x,  d.y)).rgb * 0.0625;
          s += texture2D(uBloomTex, vUv + vec2(-d.x,  d.y)).rgb * 0.0625;
          s += texture2D(uBloomTex, vUv + vec2( d.x, -d.y)).rgb * 0.0625;
          s += texture2D(uBloomTex, vUv + vec2(-d.x, -d.y)).rgb * 0.0625;
          gl_FragColor = vec4(s, 1.0);
        }
      `,
    });

    // 3. Final Composite Pass (9-Tap Depth-Bilateral GTAO + Unreal-Bloom + AMD CAS Sharpening + ACES ToneMapping)
    this.compositeMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uSceneTex: { value: this.sceneTarget.texture },
        uDepthTex: { value: this.sceneTarget.depthTexture },
        uSsaoTex: { value: this.ssaoTarget.texture },
        uBloomTex: { value: this.bloomTargetB.texture },
        uResolution: { value: new THREE.Vector2(w, h) },
        uCameraNear: { value: 0.35 },
        uCameraFar: { value: 900.0 },
        uBloomStrength: { value: 0.34 },
        uAoStrength: { value: 0.84 },
        uSharpness: { value: 0.32 },
      },
      toneMapped: true,
      depthWrite: false,
      depthTest: false,
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position.xy, 0.0, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D uSceneTex;
        uniform sampler2D uDepthTex;
        uniform sampler2D uSsaoTex;
        uniform sampler2D uBloomTex;
        uniform vec2 uResolution;
        uniform float uCameraNear;
        uniform float uCameraFar;
        uniform float uBloomStrength;
        uniform float uAoStrength;
        uniform float uSharpness;
        varying vec2 vUv;

        float linearizeDepth(float d) {
          float zn = 2.0 * d - 1.0;
          return (2.0 * uCameraNear * uCameraFar) / max(0.0001, uCameraFar + uCameraNear - zn * (uCameraFar - uCameraNear));
        }

        void main() {
          vec2 texel = 1.0 / max(vec2(1.0), uResolution);
          vec3 center = texture2D(uSceneTex, vUv).rgb;

          // 1. Contrast Adaptive Sharpening (CAS) + Kanten-Glättung für gestochen scharfe Texturen
          vec3 n = texture2D(uSceneTex, vUv + vec2(0.0, texel.y)).rgb;
          vec3 s = texture2D(uSceneTex, vUv - vec2(0.0, texel.y)).rgb;
          vec3 e = texture2D(uSceneTex, vUv + vec2(texel.x, 0.0)).rgb;
          vec3 w = texture2D(uSceneTex, vUv - vec2(texel.x, 0.0)).rgb;
          vec3 minCol = min(center, min(min(n, s), min(e, w)));
          vec3 maxCol = max(center, max(max(n, s), max(e, w)));
          float localContrast = length(maxCol - minCol);
          float casWeight = -clamp(uSharpness * (1.0 - smoothstep(0.25, 1.1, localContrast)), 0.0, 0.16);
          vec3 hdrCol = clamp((center + (n + s + e + w) * casWeight) / (1.0 + 4.0 * casWeight), vec3(0.0), maxCol * 1.15);

          // 2. Echtes 9-Tap Depth-Bilaterales Denoising & Upsampling der GTAO / SSAO Kontaktschatten
          // (Kein Ausbluten über Charakter-Silhouetten, erhält feine Stiefel-/Pflaster-Kontaktschatten auch im hellen Sonnenlicht!)
          float dCenter = texture2D(uDepthTex, vUv).r;
          if (dCenter < 0.9994 && uAoStrength > 0.01) {
            float zC = linearizeDepth(dCenter);
            vec2 aoStep = texel * 1.35;
            float aoSum = texture2D(uSsaoTex, vUv).r * 0.28;
            float wSum = 0.28;

            #define TAP_AO(ox, oy, sw) { \
              vec2 sUv = vUv + vec2(ox, oy); \
              float zS = linearizeDepth(texture2D(uDepthTex, sUv).r); \
              float wTap = (sw) * exp(-abs(zS - zC) * 18.0); \
              aoSum += texture2D(uSsaoTex, sUv).r * wTap; \
              wSum += wTap; \
            }
            TAP_AO( aoStep.x,  0.0,      0.11)
            TAP_AO(-aoStep.x,  0.0,      0.11)
            TAP_AO( 0.0,       aoStep.y, 0.11)
            TAP_AO( 0.0,      -aoStep.y, 0.11)
            TAP_AO( aoStep.x,  aoStep.y, 0.07)
            TAP_AO(-aoStep.x,  aoStep.y, 0.07)
            TAP_AO( aoStep.x, -aoStep.y, 0.07)
            TAP_AO(-aoStep.x, -aoStep.y, 0.07)
            #undef TAP_AO
            float aoAvg = aoSum / max(0.001, wSum);
            float luma = dot(hdrCol, vec3(0.2126, 0.7152, 0.0722));
            // Nur echte selbstleuchtende HDR-Emitter (Feuer, Blitze, Magie > 1.45) vor AO schützen – sonnenbeschienenes Pflaster behält vollen Kontaktschatten!
            float aoMask = (1.0 - smoothstep(1.45, 3.20, luma)) * uAoStrength;
            float finalAo = mix(1.0, aoAvg, aoMask);
            // Organischer Halbschatten-Farbton (verhindert grauen Schmutzschleier und bindet Charaktere ans Pflaster)
            vec3 aoTint = mix(vec3(0.83, 0.87, 0.94) * finalAo, vec3(1.0), finalAo);
            hdrCol *= aoTint;
          }

          // 3. Unreal-Bloom additiv aufbessern (Feuer, Fackeln, Metin-Steine, Waffen-Glanz, Sonnenkorona)
          if (uBloomStrength > 0.005) {
            vec3 bloom = texture2D(uBloomTex, vUv).rgb;
            hdrCol += bloom * uBloomStrength;
          }

          // 4. Dezente kinoreife Rand-Vignette
          vec2 vigUv = vUv * (1.0 - vUv.yx);
          float vig = pow( clamp(vigUv.x * vigUv.y * 16.0, 0.0, 1.0), 0.11 );
          hdrCol *= mix(0.90, 1.0, vig);

          gl_FragColor = vec4(hdrCol, 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }
      `,
    });

    this.quadMesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.compositeMaterial);
    this.quadScene.add(this.quadMesh);
  }

  ensureSize() {
    this.renderer.getDrawingBufferSize(this._bufSize);
    const w = Math.max(320, Math.floor(this._bufSize.x));
    const h = Math.max(180, Math.floor(this._bufSize.y));
    const isHighAo = Boolean(this.engine?._isPcProfile || (this.engine?._ppTier ?? 1) >= 2);
    const aoScale = isHighAo ? 1.0 : 0.82;
    const sw = Math.max(240, Math.floor(w * aoScale));
    const sh = Math.max(135, Math.floor(h * aoScale));

    if (this.sceneTarget.width !== w || this.sceneTarget.height !== h) {
      this.sceneTarget.setSize(w, h);
      const bw = Math.max(120, Math.floor(w * 0.35));
      const bh = Math.max(68, Math.floor(h * 0.35));
      this.bloomTargetA.setSize(bw, bh);
      this.bloomTargetB.setSize(bw, bh);

      this.bloomExtractMaterial.uniforms.uTexelSize.value.set(1.0 / w, 1.0 / h);
      this.bloomBlurMaterial.uniforms.uTexelSize.value.set(1.0 / bw, 1.0 / bh);
      this.compositeMaterial.uniforms.uResolution.value.set(w, h);
    }
    if (this.ssaoTarget.width !== sw || this.ssaoTarget.height !== sh) {
      this.ssaoTarget.setSize(sw, sh);
      this.ssaoMaterial.uniforms.uResolution.value.set(sw, sh);
    }
  }

  beginScenePass() {
    this.ensureSize();
    this.renderer.setRenderTarget(this.sceneTarget);
    this.renderer.clear();
  }

  endAndComposite(camera) {
    const prevAutoClear = this.renderer.autoClear;
    this.renderer.autoClear = false;

    const ppTier = this.engine?._ppTier ?? 1;
    const isPc = Boolean(this.engine?._isPcProfile);

    // 1. GTAO / SSAO Pass (jeden Frame auf PC/Ultra, jeden 2. Frame auf Normal)
    this._frameTick = (this._frameTick + 1) % 2;
    if (ppTier >= 2 || isPc || this._frameTick === 0 || !this._ssaoDoneOnce) {
      this._ssaoDoneOnce = true;
      this.ssaoMaterial.uniforms.uCameraNear.value = camera.near;
      this.ssaoMaterial.uniforms.uCameraFar.value = camera.far;
      this.quadMesh.material = this.ssaoMaterial;
      this.renderer.setRenderTarget(this.ssaoTarget);
      this.renderer.render(this.quadScene, this.quadCamera);
    }

    // 2. Unreal-Bloom Pass (Threshold Downsample -> Tent Blur)
    this.quadMesh.material = this.bloomExtractMaterial;
    this.renderer.setRenderTarget(this.bloomTargetA);
    this.renderer.render(this.quadScene, this.quadCamera);

    this.quadMesh.material = this.bloomBlurMaterial;
    this.renderer.setRenderTarget(this.bloomTargetB);
    this.renderer.render(this.quadScene, this.quadCamera);

    // 3. Finaler Composite Pass auf den Bildschirm (null)
    const bloomCfg = Number(this.engine?.env?.bloomIntensity ?? 1.2);
    this.compositeMaterial.uniforms.uCameraNear.value = camera.near;
    this.compositeMaterial.uniforms.uCameraFar.value = camera.far;
    this.compositeMaterial.uniforms.uBloomStrength.value = Math.min(0.55, 0.24 * bloomCfg);
    this.compositeMaterial.uniforms.uAoStrength.value = ppTier >= 2 || isPc ? 0.88 : 0.70;
    this.compositeMaterial.uniforms.uSharpness.value = isPc ? 0.36 : 0.28;

    this.quadMesh.material = this.compositeMaterial;
    this.renderer.setRenderTarget(null);
    this.renderer.render(this.quadScene, this.quadCamera);

    this.renderer.autoClear = prevAutoClear;
  }

  dispose() {
    if (this.sceneTarget) this.sceneTarget.dispose();
    if (this.ssaoTarget) this.ssaoTarget.dispose();
    if (this.bloomTargetA) this.bloomTargetA.dispose();
    if (this.bloomTargetB) this.bloomTargetB.dispose();
    if (this.ssaoMaterial) this.ssaoMaterial.dispose();
    if (this.bloomExtractMaterial) this.bloomExtractMaterial.dispose();
    if (this.bloomBlurMaterial) this.bloomBlurMaterial.dispose();
    if (this.compositeMaterial) this.compositeMaterial.dispose();
    if (this.quadMesh) this.quadMesh.geometry.dispose();
  }
}

// ============================================================================
// 5. DAY NIGHT SYSTEM (ZENTRALER ORCHESTRATOR)
// ============================================================================
export class DayNightSystem {
  constructor(engine, options = {}) {
    this.engine = engine;
    this.scene = engine.scene;
    this.renderer = engine.renderer;

    this._shadowViewMatrix = new THREE.Matrix4();
    this._shadowInvViewMatrix = new THREE.Matrix4();
    this._shadowTargetVec = new THREE.Vector3();
    this._shadowLightEye = new THREE.Vector3();
    this._origin = new THREE.Vector3(0, 0, 0);
    this._up = new THREE.Vector3(0, 1, 0);
    this._sunOcclusion = 0.0;

    this.timeManager = new WorldTimeManager({
      hourOfDay: engine.env.hourOfDay ?? 17.75,
      timeSpeed: engine.env.timeSpeed ?? 0,
      timeMode: engine.env.timeMode || 'local',
      dayLengthMinutes: options.dayLengthMinutes || 60,
    });

    this.celestial = new CelestialManager({
      latitude: options.latitude ?? 36.0,
      season: engine.env.season || 'summer',
      moonPhase: options.moonPhase ?? 4,
    });

    this.atmosphere = new AtmosphereManager(this.scene, this.engine, {
      turbidity: options.turbidity ?? 2.4,
      rayleigh: options.rayleigh ?? 1.4,
      scatteringIntensity: engine.env.scatteringIntensity ?? 1.80,
    });

    this.clouds = new VolumetricCloudManager(this.scene, this.renderer, {
      engine: this.engine,
      enabled: engine.env.clouds !== false,
      quality: engine.env.cloudQuality ?? 4,
      cloudType: engine.env.cloudType || 'auto',
      coverage: engine.env.cloudCoverage ?? 0.44,
      density: engine.env.cloudDensity ?? 1.50,
      cloudHeight: engine.env.cloudHeight ?? 1350.0,
      thickness: engine.env.cloudThickness ?? 1100.0,
      shadowStrength: engine.env.cloudShadowStrength ?? 0.72,
      windSpeed: engine.env.windSpeed ?? 14.0,
      windDirection: engine.env.windDirection ?? 0.45,
    });

    this.sunbeams = new SunbeamRenderer(this.renderer, {
      enabled: engine.env.sunbeams !== false,
      quality: engine.env.sunbeamQuality ?? 3,
      intensity: engine.env.sunbeamIntensity ?? 1.35,
      density: engine.env.sunbeamDensity ?? 0.66,
      bloomIntensity: engine.env.bloomIntensity ?? 1.40,
    });

    this.postProcessing = new PostProcessingComposer(this.renderer, this.engine);
  }

  update(dt = 0, camera = this.engine.camera) {
    if (!camera) return;

    // 1. Live-Parameter aus engine.env synchronisieren
    const env = this.engine.env;
    if (this.atmosphere) {
      this.atmosphere.scatteringIntensity = Number(env.scatteringIntensity ?? 1.0);
    }
    if (this.sunbeams) {
      this.sunbeams.intensity = Number(env.sunbeamIntensity ?? 1.0);
      this.sunbeams.density = Number(env.sunbeamDensity ?? 0.92);
      this.sunbeams.bloomIntensity = Number(env.bloomIntensity ?? 0.45);
    }

    // 2. Zeit aktualisieren
    const hour = this.timeManager.update(dt);
    env.hourOfDay = hour;

    // 3. Wolkenbedeckung & Sonnenverdeckung für physikalische Lichtdämpfung ermitteln
    const cloudiness = this.clouds && this.clouds.enabled
      ? this.clouds.coverage
      : this.getCloudinessForWeather(env.weather);
    const sunOcclusion = this.clouds && this.clouds.enabled
      ? this.clouds.getSunOcclusion(this.celestial.sunDirection)
      : 0.0;
    this._sunOcclusion = sunOcclusion; // Cache für render() (spart eine zweite CPU-Noise-Auswertung pro Frame)

    // 4. Sonne, Mond & Himmelsfarben aktualisieren
    this.celestial.update(hour, env.season, {
      sunIntensityMult: env.sunIntensityMult ?? 1.0,
      moonIntensityMult: env.moonIntensityMult ?? 1.0,
      cloudiness,
      sunOcclusion,
      weather: env.weather,
    });

    // 5. Volumetrisches Wolkensystem aktualisieren
    if (this.clouds) {
      this.clouds.windSpeed = env.windSpeed ?? 14.0;
      this.clouds.windDirection = env.windDirection ?? 0.45;
      this.clouds.lightScattering = env.scatteringIntensity ?? 1.0;
      this.clouds.update(this.celestial, camera, dt, env.weather, env.season);

      const shadowParams = this.clouds.getCloudShadowParameters();
      this.applyCloudShadowsToEngine(shadowParams);
    }

    // 6. Lichtquellen & Texel-Snapping-Schatten der Engine ausrichten
    this.applyLightingToEngine(camera);

    // 7. Atmosphäre, Himmelskuppel, Mond & Sterne aktualisieren
    this.atmosphere.update(this.celestial, camera, dt, cloudiness, sunOcclusion);
  }

  applyCloudShadowsToEngine(shadowParams) {
    const eng = this.engine;
    if (!eng) return;

    // Bei starker Bewölkung, Regen, Gewitter oder tief in der Nacht werden Wolkenschatten weich gedämpft,
    // damit das Terrain niemals durch doppelte Abschattung schwarz wird (Fix Bild 2!)
    const isRainOrStorm = CLOUD_SHADOW_DAMP_WEATHER.has(eng.env.weather);
    const dayFactor = this.celestial.isDay ? Math.min(1.0, this.celestial.sunIntensity / 1.1) : 0.22;
    const weatherDamp = isRainOrStorm ? 0.18 : (1.0 - Math.max(0.0, shadowParams.coverage - 0.55) * 1.2);
    const effectiveStrength = Math.max(0.0, Math.min(0.42, shadowParams.strength * dayFactor * Math.max(0.15, weatherDamp)));

    if (eng._terrainSplatUniforms) {
      if (eng._terrainSplatUniforms.uCloudShadowEnabled) {
        eng._terrainSplatUniforms.uCloudShadowEnabled.value = shadowParams.enabled ? 1.0 : 0.0;
      }
      if (eng._terrainSplatUniforms.uCloudShadowStrength) {
        eng._terrainSplatUniforms.uCloudShadowStrength.value = effectiveStrength;
      }
      if (eng._terrainSplatUniforms.uCloudCoverage) {
        eng._terrainSplatUniforms.uCloudCoverage.value = shadowParams.coverage;
      }
      if (eng._terrainSplatUniforms.uCloudShadowOffset && shadowParams.windOffset) {
        eng._terrainSplatUniforms.uCloudShadowOffset.value.copy(shadowParams.windOffset);
      }
    }

    if (eng._objectWeatherUniforms) {
      if (eng._objectWeatherUniforms.uCloudShadowEnabled) {
        eng._objectWeatherUniforms.uCloudShadowEnabled.value = shadowParams.enabled ? 1.0 : 0.0;
      }
      if (eng._objectWeatherUniforms.uCloudShadowStrength) {
        eng._objectWeatherUniforms.uCloudShadowStrength.value = effectiveStrength;
      }
      if (eng._objectWeatherUniforms.uCloudCoverage) {
        eng._objectWeatherUniforms.uCloudCoverage.value = shadowParams.coverage;
      }
      if (eng._objectWeatherUniforms.uCloudShadowOffset && shadowParams.windOffset) {
        eng._objectWeatherUniforms.uCloudShadowOffset.value.copy(shadowParams.windOffset);
      }
    }
  }

  applyLightingToEngine() {
    const eng = this.engine;
    if (!eng.sunLight || !eng.hemiLight) return;

    const p = eng.localPlayerPos || { x: 0, y: 0, z: 0 };
    const pY = p.y || 0;

    // A) Hauptlicht (Sonne / Mond Handover) mit Texel-Grid-Snapping gegen Schattenflimmern bei Kamerabewegung!
    const activeDir = this.celestial.activeLightDirection;
    const shadowDist = (eng._shadowDistScale || 1.4) * 95.0;
    const clampedDirY = Math.max(0.32, activeDir.y);

    // Shadow-Kamera Bounds konfigurieren gegen Clipping (engere Box für maximale Pixeldichte & weiche Kontaktkanten)
    if (eng.sunLight && eng.sunLight.shadow && eng.sunLight.shadow.camera) {
      const sc = eng.sunLight.shadow.camera;
      const targetD = eng._targetShadowSpan || (eng._isPcProfile ? 56 : 48);
      if (sc.left !== -targetD || sc.right !== targetD) {
        const d = targetD;
        sc.left = -d;
        sc.right = d;
        sc.top = d;
        sc.bottom = -d;
        sc.near = 5;
        sc.far = Math.max(350, shadowDist * 2.2);
        sc.updateProjectionMatrix();
      }
    }

    // Zielpunkt auf das Texel-Raster der Shadow-Map einrasten (verhindert "Shadow Swimming" / Kantenflimmern!)
    const shadowCam = eng.sunLight.shadow.camera;
    const mapWidth = eng.sunLight.shadow.mapSize.width || 2048;
    const frustumSize = (shadowCam.right - shadowCam.left) || 180;
    const texelSize = frustumSize / mapWidth;

    let fwdOffX = 0.0;
    let fwdOffZ = 0.0;
    if (eng._isPcProfile && typeof eng.cameraYaw === 'number') {
      const fwdShift = Math.min(55.0, frustumSize * 0.18);
      fwdOffX = -Math.sin(eng.cameraYaw) * fwdShift;
      fwdOffZ = -Math.cos(eng.cameraYaw) * fwdShift;
    }

    this._shadowTargetVec.set(p.x + fwdOffX, pY, p.z + fwdOffZ);
    if (texelSize > 0.001) {
      const lightEye = this._shadowLightEye.set(activeDir.x * 100.0, clampedDirY * 100.0, activeDir.z * 100.0);
      this._shadowViewMatrix.lookAt(lightEye, this._origin, this._up);
      this._shadowInvViewMatrix.copy(this._shadowViewMatrix).invert();

      this._shadowTargetVec.applyMatrix4(this._shadowInvViewMatrix);
      this._shadowTargetVec.x = Math.round(this._shadowTargetVec.x / texelSize) * texelSize;
      this._shadowTargetVec.y = Math.round(this._shadowTargetVec.y / texelSize) * texelSize;
      this._shadowTargetVec.z = Math.round(this._shadowTargetVec.z / texelSize) * texelSize;
      this._shadowTargetVec.applyMatrix4(this._shadowViewMatrix);
    }

    eng.sunLight.position.set(
      this._shadowTargetVec.x + activeDir.x * shadowDist,
      this._shadowTargetVec.y + clampedDirY * shadowDist,
      this._shadowTargetVec.z + activeDir.z * shadowDist
    );
    eng.sunLight.target.position.copy(this._shadowTargetVec);
    eng.sunLight.target.updateMatrixWorld();

    // Weiche Farbanpassung & Intensität
    eng.sunLight.color.lerp(this.celestial.activeLightColor, 0.18);
    const scaledSunInt = this.celestial.activeLightIntensity * (eng._gfxSunMult ?? 1.0);
    eng.sunLight.intensity += (scaledSunInt - eng.sunLight.intensity) * 0.18;

    // Dynamischer Schatten-Bias abhängig vom Einfallswinkel (verhindert Shadow Acne UND Peter-Panning an Charakterfüßen!)
    const elev = Math.max(0.12, clampedDirY);
    eng.sunLight.shadow.bias = -0.00010 - (1.0 - elev) * 0.00013;
    eng.sunLight.shadow.normalBias = 0.0062 + (1.0 - elev) * 0.0042;
    eng.sunLight.shadow.radius = 1.65;

    // B) Hemisphärenlicht (Himmel & Bodenrückstrahlung)
    eng.hemiLight.color.lerp(this.celestial.ambientSkyColor, 0.18);
    eng.hemiLight.groundColor.lerp(this.celestial.ambientGroundColor, 0.18);
    const scaledHemiInt = this.celestial.ambientIntensity * (eng._gfxHemiMult ?? 1.0);
    eng.hemiLight.intensity += (scaledHemiInt - eng.hemiLight.intensity) * 0.18;

    // C) GLSL-Shader-Uniforms für Terrain, Objekte & Wasser aktualisieren
    if (eng._terrainSplatUniforms) {
      if (eng._terrainSplatUniforms.uSunDir?.value) {
        eng._terrainSplatUniforms.uSunDir.value.copy(activeDir);
      }
      if (eng._terrainSplatUniforms.uAmbientFloor) {
        eng._terrainSplatUniforms.uAmbientFloor.value = this.celestial.ambientFloor;
      }
      if (eng._terrainSplatUniforms.uAmbientSkyColor?.value) {
        eng._terrainSplatUniforms.uAmbientSkyColor.value.copy(this.celestial.ambientSkyColor);
      }
    }
    if (eng._objectWeatherUniforms) {
      if (eng._objectWeatherUniforms.uSunDir?.value) {
        eng._objectWeatherUniforms.uSunDir.value.copy(activeDir);
      }
      if (eng._objectWeatherUniforms.uAmbientFloor) {
        eng._objectWeatherUniforms.uAmbientFloor.value = this.celestial.ambientFloor;
      }
      if (eng._objectWeatherUniforms.uGiSunColor?.value) {
        eng._objectWeatherUniforms.uGiSunColor.value.copy(this.celestial.activeLightColor);
      }
    }
    if (eng._waterShaderUniforms) {
      if (eng._waterShaderUniforms.uSunDir?.value) {
        eng._waterShaderUniforms.uSunDir.value.copy(activeDir);
      }
      if (eng._waterShaderUniforms.uLightColor?.value) {
        eng._waterShaderUniforms.uLightColor.value.copy(this.celestial.activeLightColor);
      }
      if (eng._waterShaderUniforms.uLightIntensity) {
        eng._waterShaderUniforms.uLightIntensity.value = Math.max(0.32, this.celestial.activeLightIntensity);
      }
    }
  }

  getCloudinessForWeather(weather) {
    if (['rain', 'heavy_rain', 'thunderstorm', 'severe_thunderstorm', 'heavy_snow', 'blizzard'].includes(weather)) return 0.94;
    if (['cloudy', 'fog', 'light_snow', 'snow', 'light_rain'].includes(weather)) return 0.76;
    if (weather === 'partly_cloudy') return 0.38;
    return 0.14;
  }

  render(scene, camera) {
    const usePostProc = Boolean(
      this.postProcessing &&
      this.postProcessing.enabled &&
      (this.engine._ppTier ?? 1) > 0 &&
      (this.engine._masterTier ?? 1) > 0
    );

    if (usePostProc) {
      this.postProcessing.beginScenePass();
    }

    // 1. Hauptszene rendern (in HDR-SceneTarget mit Hardware-DepthTexture oder direkt auf das Canvas)
    this.renderer.render(scene, camera);

    // 2. Volumetrische Sunbeams (tagsüber/Dämmerung) & dezente Moonbeams (nachts bei hellem Mond)
    const canRenderSunbeams = Boolean(this.sunbeams && this.sunbeams.enabled && this.sunbeams.quality > 0);
    const weather = this.engine.env.weather || 'sunny';
    const isHeavyStorm = HEAVY_STORM_WEATHER.has(weather);

    if (canRenderSunbeams && !isHeavyStorm) {
      const wMeta = this.engine.getWeatherMeta ? this.engine.getWeatherMeta(weather, this.engine.env.hourOfDay) : { humidity: 50 };
      const humidityFactor = 0.72 + ((wMeta.humidity || 50) / 100.0) * 0.55; // Dunst & Luftfeuchtigkeit verstärken die Streuung

      if (this.celestial.isDay && this.celestial.sunIntensity > 0.08) {
        const sunOcclusion = this._sunOcclusion;
        const cloudCoverage = this.clouds ? this.clouds.coverage : this.getCloudinessForWeather(weather);
        // Am stärksten bei Sonnenaufgang / Golden Hour und wenn Sonnenstrahlen durch Wolkenlücken brechen!
        const goldenBoost = 1.0 + this.celestial.twilightFactor * 0.65;
        const visibility =
          (1.0 - sunOcclusion * 0.78) *
          (1.0 - Math.max(0.0, cloudCoverage - 0.35) * 0.85) *
          Math.min(1.2, this.celestial.sunIntensity / 1.25) *
          humidityFactor *
          goldenBoost;

        if (visibility > 0.01) {
          this.sunbeams.renderVolumetricPass(
            this.engine,
            camera,
            this.celestial,
            this.clouds,
            visibility,
            false
          );
        }
      } else if (this.celestial.isMoonlitNight && this.celestial.moonIntensity > 0.12) {
        // Dezente volumetrische Moonbeams (deutlich schwächer als Sonnenstrahlen, nur bei sichtbarem hellem Mond & Wolkenlücken/Nebel)
        const moonOcclusion = this.clouds ? this.clouds.getSunOcclusion(this.celestial.moonDirection) : 0.0;
        const cloudCoverage = this.clouds ? this.clouds.coverage : this.getCloudinessForWeather(weather);
        const moonVisibility =
          (1.0 - moonOcclusion * 0.82) *
          (1.0 - Math.max(0.0, cloudCoverage - 0.45) * 0.90) *
          Math.min(1.0, this.celestial.moonIntensity / 0.55) *
          humidityFactor *
          0.34; // Deutlich dezenter als Sonnenstrahlen!

        if (moonVisibility > 0.01) {
          this.sunbeams.renderVolumetricPass(
            this.engine,
            camera,
            this.celestial,
            this.clouds,
            moonVisibility,
            true
          );
        }
      }
    }

    // 3. Next-Gen Post-Processing Composite (GTAO/SSAO + HDR Unreal-Bloom + CAS + ACES ToneMapping)
    if (usePostProc) {
      this.postProcessing.endAndComposite(camera);
    }
  }

  onResize(w, h) {
    if (this.sunbeams) {
      this.sunbeams.resize(w, h);
    }
    if (this.postProcessing) {
      this.postProcessing.ensureSize();
    }
  }

  dispose() {
    if (this.clouds) this.clouds.dispose();
    if (this.atmosphere) this.atmosphere.dispose();
    if (this.sunbeams) this.sunbeams.dispose();
    if (this.postProcessing) this.postProcessing.dispose();
  }
}
