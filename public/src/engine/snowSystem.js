// ============================================================================
// AERYNDOR – VOLUMETRISCHES 3D-SCHNEE- & SCHNEESTURMSYSTEM
// ============================================================================
// Renderer: Three.js r160 / WebGL2 (das Projekt nutzt keinen WebGPU-Renderer;
// alle Simulationen laufen GPU-seitig im Vertex-Shader – keine CPU-Updates
// einzelner Flocken, keine JS-Objekte pro Flocke).
//
// Module (logisch getrennt, gemeinsame Wetter-/Windparameter):
//  - SNOW_INTENSITY_LEVELS  Snow Weather Controller (4 stufenlose Intensitäten)
//  - SNOW_QUALITY_PROFILES  Snow Quality Profiles (Performance/Normal/Ultra)
//  - Flake Layers           Snow Particle Simulation (Nah 0–15m, Mittel 15–60m)
//  - Veil Shells            Snow Volume / Fog (Fernbereich, windgetriebene Schleier)
//  - Ground Drift           Bodennahe Schneeverwehungen / Pulverschnee
//  - Burst Pool             Snow Interaction Effects (Fußtritte, Landung, Kampf)
//  - Occlusion Map          Schnee-Abschattung unter Dächern, Brücken, Baumkronen
// ============================================================================

import * as THREE from '../../vendor/three.module.js';

export const SNOW_WEATHER_KEYS = ['light_snow', 'snow', 'heavy_snow', 'blizzard'];
export const isSnowWeather = (w) => SNOW_WEATHER_KEYS.includes(w);

// Wetter-Controller: Basisparameter je Intensitätsstufe (stufenlos interpoliert über st.snowRate)
export const SNOW_INTENSITY_LEVELS = {
  light_snow: { rate: 0.30, windBase: 12, gustiness: 0.22, turbulence: 0.12, maxCover: 0.42, accumRate: 0.010, tempCap: -0.8, tempMod: -7 },
  snow: { rate: 0.60, windBase: 22, gustiness: 0.38, turbulence: 0.25, maxCover: 0.90, accumRate: 0.020, tempCap: -2.5, tempMod: -11 },
  heavy_snow: { rate: 0.85, windBase: 40, gustiness: 0.62, turbulence: 0.48, maxCover: 0.94, accumRate: 0.028, tempCap: -4.0, tempMod: -14 },
  blizzard: { rate: 1.00, windBase: 78, gustiness: 1.00, turbulence: 0.90, maxCover: 0.96, accumRate: 0.034, tempCap: -10.0, tempMod: -18 },
};

// Grafikprofile: nur visuelle Qualität & kosmetische Simulation, identische Wetterzustände
export const SNOW_QUALITY_PROFILES = {
  0: { name: 'performance', near: 3000, nearR: 11, mid: 9000, midR: 40, veils: 0, drift: 0, puffs: 96, occlusion: false, occRes: 0, occHalf: 0, canopy: false, minPx: 1.25 },
  1: { name: 'normal', near: 7000, nearR: 14, mid: 22000, midR: 56, veils: 2, drift: 1200, puffs: 256, occlusion: true, occRes: 128, occHalf: 48, canopy: true, minPx: 1.4 },
  2: { name: 'ultra', near: 12000, nearR: 16, mid: 40000, midR: 68, veils: 3, drift: 2600, puffs: 384, occlusion: true, occRes: 256, occHalf: 64, canopy: true, minPx: 1.5 },
};

// Gebietsprofil (zukünftige Regionen können eigene Schneeparameter setzen, ohne das System zu duplizieren)
export const DEFAULT_SNOW_REGION = {
  flakeSizeMult: 1.0,
  densityMult: 1.0,
  fogMult: 1.0,
  windMult: 1.0,
  veilMult: 1.0,
  driftMult: 1.0,
};

// Regionsvorlagen (für setRegionPreset) – alle Werte relativ zu DEFAULT_SNOW_REGION
export const SNOW_REGION_PRESETS = {
  default: {},
  valley: { densityMult: 0.85, fogMult: 0.85, windMult: 0.8, driftMult: 0.7 },
  frozen_forest: { flakeSizeMult: 1.15, densityMult: 0.9, fogMult: 1.1, windMult: 0.6, veilMult: 0.8, driftMult: 0.5 },
  mountain_pass: { flakeSizeMult: 0.9, densityMult: 1.1, fogMult: 1.3, windMult: 1.35, veilMult: 1.3, driftMult: 1.4 },
  glacier_peak: { flakeSizeMult: 0.8, densityMult: 1.2, fogMult: 1.5, windMult: 1.6, veilMult: 1.5, driftMult: 1.7 },
  dungeon_ice: { flakeSizeMult: 0.7, densityMult: 0.4, fogMult: 0.6, windMult: 0.2, veilMult: 0.0, driftMult: 0.2 },
};

// Adaptive Qualität: Bildzeit-Schwellen (s) & Haltezeiten (s) mit Hysterese gegen Flackern zwischen Stufen
const ADAPTIVE_DOWN_DT = 1 / 38;
const ADAPTIVE_UP_DT = 1 / 56;
const ADAPTIVE_DOWN_HOLD = 3.0;
const ADAPTIVE_UP_HOLD = 12.0;

// Interaktions-Presets für emitInteraction()
const BURST_PRESETS = {
  step: { count: 4, strength: 0.7, size: 0.1, life: 0.6 },
  sprint: { count: 7, strength: 1.05, size: 0.12, life: 0.75 },
  mount: { count: 10, strength: 1.35, size: 0.16, life: 0.9 },
  land: { count: 16, strength: 1.6, size: 0.17, life: 1.0 },
  impact: { count: 20, strength: 1.9, size: 0.15, life: 0.85 },
  roll: { count: 12, strength: 1.2, size: 0.14, life: 0.8 },
};

const Q = 16; // Quantisierung von Fall-/Windfaktoren (verlustfreies Offset-Wrapping ohne Sprünge)
const CANOPY_LAYER = 5;

const clamp01 = (v) => Math.max(0, Math.min(1, v));
const smooth = (a, b, x) => {
  const t = clamp01((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};

// ---------------------------------------------------------------------------
// GLSL-Bausteine
// ---------------------------------------------------------------------------
const OCC_GLSL = /* glsl */ `
uniform sampler2D uOccTex;
uniform sampler2D uCanopyTex;
uniform vec4 uOccParams;   // centerX, centerZ, halfSize, enabled
uniform vec3 uOccCam;      // camY, near, far
uniform float uCanopyOn;
uniform float uGroundY;

vec2 snowOccUv(vec2 xz) {
  vec2 r = (xz - uOccParams.xy) / (uOccParams.z * 2.0);
  return vec2(r.x + 0.5, 0.5 - r.y);
}
bool snowOccInside(vec2 uv) {
  return uv.x > 0.004 && uv.y > 0.004 && uv.x < 0.996 && uv.y < 0.996;
}
float snowTopY(sampler2D tex, vec2 uv) {
  float d = texture2D(tex, uv).r;
  return d >= 0.9999 ? -100000.0 : uOccCam.x - (uOccCam.y + d * (uOccCam.z - uOccCam.y));
}
`;

const FLAKE_VERT = /* glsl */ `
attribute vec4 aSeed;
attribute vec4 aProps;
attribute float aAtlas;

uniform float uTime;
uniform vec3 uCamPos;
uniform vec3 uBoxSize;
uniform float uBoxYOffset;
uniform float uFallOffset;
uniform vec2 uWindOffset;
uniform float uFallSpeed;
uniform vec2 uWindVel;
uniform vec2 uWindDir;
uniform float uWindGust;
uniform float uWindTurb;
uniform float uWindStrength;
uniform float uDensity;
uniform vec4 uFade;
uniform float uSizeMult;
uniform float uSway;
uniform float uStreak;
uniform float uMinPx;
uniform float uViewportH;
uniform vec3 uSunDir;
uniform vec3 uSunColor;
uniform vec3 uAmbient;
uniform float uScatter;
${OCC_GLSL}

varying vec2 vUv;
varying vec2 vLocal;
varying float vPx;
varying float vAlpha;
varying float vDist;
varying vec3 vLight;

void main() {
  float size = aProps.x * uSizeMult;
  float fallMult = aProps.y;
  float drag = aProps.z;
  float phase = aProps.w;
  float t = uTime;

  // 1. Kontinuierliche GPU-Bewegung (integrierte Fall- & Windoffsets von der CPU, nie zurückgesetzt)
  vec3 p = aSeed.xyz * uBoxSize;
  p.y -= uFallOffset * fallMult;
  p.xz += uWindOffset * drag;

  // 2. Natürliches Taumeln (spiralförmiges Absinken)
  float fl = t * (1.7 + phase * 2.3) + phase * 31.4;
  float swayA = uSway * (0.6 + phase * 0.8);
  p.x += sin(fl) * swayA;
  p.z += cos(fl * 0.87 + 1.3) * swayA;
  p.y += sin(fl * 1.31) * swayA * 0.35;

  // 3. Kamerabezogenes Partikel-Recycling (toroidales Volumen -> weltstabile Flocken, kein Pop-in)
  vec3 boxMin = uCamPos + vec3(0.0, uBoxYOffset, 0.0) - uBoxSize * 0.5;
  p = mod(p - boxMin, uBoxSize) + boxMin;

  // 4. Lokale Turbulenz-Wirbel (weltkohärent, böen- & windstärkeabhängig)
  float e1 = t * (0.7 + drag * 0.5) + p.y * 0.23 + p.x * 0.051 + phase * 6.283;
  float e2 = t * (0.6 + drag * 0.4) + p.y * 0.19 - p.z * 0.047 + phase * 4.11;
  float eddyAmp = uWindTurb * (0.35 + 1.25 * drag) * min(1.6, uWindStrength);
  p.x += sin(e1) * eddyAmp;
  p.z += cos(e2) * eddyAmp;
  p.y += sin(e1 * 0.7 + e2) * eddyAmp * 0.35;

  // 5. Wandernde Böenfronten (gleiche Windrichtung wie Gras, Bäume & Regen)
  float front = dot(p.xz, uWindDir) * 0.045 - t * (0.35 + uWindStrength * 0.25);
  float gw = smoothstep(0.2, 1.0, sin(front) * 0.5 + 0.5);
  p.xz += uWindDir * gw * uWindGust * drag * 2.6;
  p.y += gw * uWindGust * (drag - 0.85) * 1.2;

  // 6. Distanzbereiche (weich überblendet), Volumenränder & Dichte
  vec3 toC = p - uCamPos;
  float dist = length(toC);
  float fade = smoothstep(uFade.x, uFade.y, dist) * (1.0 - smoothstep(uFade.z, uFade.w, dist));
  float relY = (p.y - boxMin.y) / uBoxSize.y;
  fade *= smoothstep(0.0, 0.1, relY) * (1.0 - smoothstep(0.88, 1.0, relY));
  fade *= clamp((uDensity - aSeed.w) * 16.0, 0.0, 1.0);

  // 7. Abschattung: Boden-Landung, Dächer, Brücken (voll) & Baumkronen (teilweise)
  bool occDone = false;
  if (uOccParams.w > 0.5) {
    vec2 ouv = snowOccUv(p.xz);
    if (snowOccInside(ouv)) {
      float topY = snowTopY(uOccTex, ouv);
      fade *= smoothstep(topY - 0.05, topY + 0.55, p.y);
      if (uCanopyOn > 0.5) {
        float cy = snowTopY(uCanopyTex, ouv);
        float under = 1.0 - smoothstep(cy - 1.2, cy + 0.2, p.y);
        fade *= clamp((fract(aSeed.w * 7.31 + phase) - 0.74 * under) * 10.0, 0.0, 1.0);
      }
      occDone = true;
    }
  }
  if (!occDone) {
    fade *= smoothstep(uGroundY - 9.0, uGroundY - 3.0, p.y);
  }

  // 8. Billboard + Mindestpixelgröße (kein Flimmern in der Ferne, energieerhaltend)
  vec4 mv = viewMatrix * vec4(p, 1.0);
  float depth = max(0.05, -mv.z);
  float px = size * projectionMatrix[1][1] * uViewportH * 0.5 / depth;
  float grow = max(1.0, uMinPx / max(px, 0.0001));
  size *= grow;
  fade /= (grow * grow);

  // 9. Bewegungsunschärfe bei Sturm: Streckung entlang der projizierten Flugbahn
  vec3 vel = vec3(uWindVel.x * drag, -uFallSpeed * fallMult, uWindVel.y * drag);
  vec2 vv = (mat3(viewMatrix) * vel).xy;
  float vl = length(vv);
  float stretch = 1.0 + min(5.0, vl * uStreak / max(size, 0.004));
  vec2 ay = vl > 0.0001 ? vv / vl : vec2(0.0, 1.0);
  vec2 ax = vec2(ay.y, -ay.x);
  vec2 corner = position.xy;
  float atlas = aAtlas;
#ifdef SNOW_NEAR
  float ang = phase * 6.2831 + t * (0.5 + phase * 1.6) * (phase > 0.5 ? 1.0 : -1.0);
  float ca = cos(ang);
  float sa = sin(ang);
  vec2 rc = vec2(ca * corner.x - sa * corner.y, sa * corner.x + ca * corner.y);
  rc.x *= 0.5 + 0.5 * abs(cos(t * (0.9 + phase * 1.4) + phase * 17.0)); // Eigenrotation / Taumeln
  vec2 sc = ax * corner.x + ay * corner.y * stretch;
  float sMix = clamp((stretch - 1.0) * 0.7, 0.0, 1.0);
  vec2 off = mix(rc, sc, sMix);
  if (sMix > 0.6) atlas = 0.0;
#else
  vec2 off = ax * corner.x + ay * corner.y * stretch;
  atlas = stretch > 1.6 ? 0.0 : atlas;
#endif
  fade /= sqrt(stretch);
  mv.xy += off * size;
  gl_Position = projectionMatrix * mv;

  vUv = uv * 0.5 + vec2(mod(atlas, 2.0), floor(atlas / 2.0)) * 0.5;
  vLocal = uv;
  vPx = px * grow;
  vAlpha = fade;
  vDist = depth;

  // 10. Beleuchtung: Umgebung + Sonne/Mond mit Vorwärtsstreuung (Gegenlicht-Aufleuchten)
  vec3 V = toC / max(dist, 0.001);
  float fwd = pow(max(dot(V, uSunDir), 0.0), 7.0);
  float back = 0.22 * max(dot(-V, uSunDir), 0.0);
  vLight = uAmbient + uSunColor * (0.55 + back + fwd * uScatter);
}
`;

const FLAKE_FRAG = /* glsl */ `
uniform sampler2D uFlakeTex;
uniform vec3 uFogColor;
uniform float uFogDensity;
uniform float uOpacity;
uniform float uLightClamp;
uniform vec2 uFlakeLift;
varying vec2 vUv;
varying vec2 vLocal;
varying float vPx;
varying float vAlpha;
varying float vDist;
varying vec3 vLight;

void main() {
  vec4 tx = texture2D(uFlakeTex, vUv);
  // Kleine Flocken (wenige Pixel): analytische weiche Scheibe statt verwaschener Mip-Stufe -> klar sichtbar
  float disc = 1.0 - smoothstep(0.30, 1.0, length(vLocal * 2.0 - 1.0));
  float shapeA = mix(disc, tx.a, smoothstep(4.0, 11.0, vPx));
  float a = shapeA * vAlpha * uOpacity;
  if (a < 0.003) discard;
  vec3 lit = max(vLight, uFogColor * uFlakeLift.x + vec3(uFlakeLift.y));
  vec3 col = min(lit, vec3(uLightClamp)) * mix(vec3(0.86, 0.92, 1.0), vec3(1.0), tx.r);
  float fd = uFogDensity * vDist;
  float f = 1.0 - exp(-fd * fd);
  col = mix(col, uFogColor * 1.15, f * 0.75);
  gl_FragColor = vec4(col, min(a, 1.0));
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

const VEIL_VERT = /* glsl */ `
varying vec3 vWorld;
varying float vH;
void main() {
  vec4 wp = modelMatrix * vec4(position, 1.0);
  vWorld = wp.xyz;
  vH = uv.y;
  gl_Position = projectionMatrix * viewMatrix * wp;
}
`;

const VEIL_FRAG = /* glsl */ `
uniform float uTime;
uniform vec2 uWindOffset;
uniform float uFallOffset;
uniform vec2 uWindDir;
uniform float uOpacity;
uniform vec3 uFogColor;
uniform vec3 uLitColor;
uniform vec3 uSunDir;
uniform vec3 uCamPos;
uniform float uStreakiness;
uniform float uScale;
uniform float uSeed;
${OCC_GLSL}
varying vec3 vWorld;
varying float vH;

float h31(vec3 p) {
  p = fract(p * 0.1031);
  p += dot(p, p.zyx + 31.32);
  return fract((p.x + p.y) * p.z);
}
float vnoise(vec3 x) {
  vec3 i = floor(x);
  vec3 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(mix(h31(i), h31(i + vec3(1, 0, 0)), f.x), mix(h31(i + vec3(0, 1, 0)), h31(i + vec3(1, 1, 0)), f.x), f.y),
    mix(mix(h31(i + vec3(0, 0, 1)), h31(i + vec3(1, 0, 1)), f.x), mix(h31(i + vec3(0, 1, 1)), h31(i + vec3(1, 1, 1)), f.x), f.y),
    f.z);
}

void main() {
  vec3 w = vWorld;
  vec2 wd = uWindDir;
  vec2 wp = vec2(-wd.y, wd.x);
  vec2 rel = w.xz - uWindOffset;
  vec2 q = vec2(dot(rel, wd) / (1.0 + uStreakiness * 3.0), dot(rel, wp));
  vec3 nc = vec3(q * uScale, (w.y + uFallOffset) * uScale * 0.8) + uSeed;
  float n = vnoise(nc) * 0.6 + vnoise(nc * 2.13 + 7.1) * 0.3 + vnoise(nc * 4.7 + 3.3) * 0.1;
  float density = smoothstep(0.22, 0.85, n);

  float vf = smoothstep(0.0, 0.2, vH) * (1.0 - smoothstep(0.55, 1.0, vH));

  // Tiefenbewusste, weiche Bodenanbindung (keine harte Schnittkante, wo der Schleier das Gelände kreuzt)
  float gY = uGroundY - 1.5;
  if (uOccParams.w > 0.5) {
    vec2 ouv = snowOccUv(w.xz);
    if (snowOccInside(ouv)) {
      float ty = snowTopY(uOccTex, ouv);
      if (ty > -1000.0) gY = ty;
    }
  }
  float gf = smoothstep(gY - 0.3, gY + 4.0, w.y);

  vec3 V = normalize(w - uCamPos);
  float sunPhase = pow(max(dot(V, uSunDir), 0.0), 5.0);
  vec3 col = mix(uFogColor, uLitColor, 0.30 + sunPhase * 0.70);
  float a = uOpacity * (0.40 + 0.60 * density) * vf * gf;
  if (a < 0.002) discard;
  gl_FragColor = vec4(col, a);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

const DRIFT_VERT = /* glsl */ `
attribute vec4 aSeed;   // x, z, Höhe, Dichte-Rang
attribute vec4 aProps;  // Länge, Geschwindigkeitsfaktor, Phase, Breite
uniform float uTime;
uniform vec3 uCamPos;
uniform vec2 uBox;
uniform vec2 uDriftOffset;
uniform vec2 uWindDir;
uniform float uWindStrength;
uniform float uWindGust;
uniform float uAmount;
uniform float uFarFade;
uniform vec3 uSunColor;
uniform vec3 uAmbient;
${OCC_GLSL}
varying vec2 vUv;
varying float vAlpha;
varying float vDist;
varying vec3 vLight;
varying float vSeed;

void main() {
  vec2 perp = vec2(-uWindDir.y, uWindDir.x);
  vec2 pxz = aSeed.xy * uBox + uDriftOffset * aProps.y;
  pxz += perp * sin(uTime * 0.8 + aProps.z * 6.2831 + dot(pxz, uWindDir) * 0.15) * 0.6;
  vec2 bmin = uCamPos.xz - uBox * 0.5;
  pxz = mod(pxz - bmin, uBox) + bmin;

  float h = 0.03 + pow(aSeed.z, 2.3) * 1.25;
  h += abs(sin(uTime * (2.0 + aProps.z * 3.0) + aSeed.w * 40.0)) * 0.12 * (1.0 - aSeed.z);

  float gy = uGroundY;
  float valid = 1.0;
  if (uOccParams.w > 0.5) {
    vec2 ouv = snowOccUv(pxz);
    if (snowOccInside(ouv)) {
      float ty = snowTopY(uOccTex, ouv);
      if (ty > -1000.0) gy = ty; else valid = 0.0;
    }
  }
  vec3 p = vec3(pxz.x, gy + h, pxz.y);
  float dist = length(p - uCamPos);
  float fade = smoothstep(1.5, 4.0, dist) * (1.0 - smoothstep(uFarFade * 0.65, uFarFade, dist));

  // Sichtbare Böen über freien Flächen
  float front = dot(pxz, uWindDir) * 0.06 - uTime * (0.5 + uWindStrength * 0.3);
  float patchN = (sin(front) * 0.5 + 0.5) * (0.6 + 0.4 * sin(dot(pxz, perp) * 0.11 + 1.7));
  float gustVis = mix(0.40, 1.0, smoothstep(0.3, 0.9, patchN)) * (1.0 + uWindGust * 0.8);
  fade *= gustVis * (1.0 - aSeed.z * 0.55) * valid;
  fade *= clamp((uAmount - aSeed.w) * 12.0, 0.0, 1.0);

  vec4 mv = viewMatrix * vec4(p, 1.0);
  vec2 vv = (mat3(viewMatrix) * vec3(uWindDir.x, 0.0, uWindDir.y)).xy;
  float vl = length(vv);
  vec2 ay = vl > 0.001 ? vv / vl : vec2(1.0, 0.0);
  vec2 ax = vec2(ay.y, -ay.x);
  float len = aProps.x * (0.6 + uWindStrength * 0.7) * max(vl, 0.25);
  mv.xy += ax * position.x * aProps.w + ay * position.y * len;
  gl_Position = projectionMatrix * mv;

  vUv = uv;
  vAlpha = fade;
  vDist = -mv.z;
  vSeed = aSeed.w;
  vLight = uAmbient + uSunColor * 0.45;
}
`;

const DRIFT_FRAG = /* glsl */ `
uniform vec3 uFogColor;
uniform float uFogDensity;
uniform float uOpacity;
uniform float uLightClamp;
varying vec2 vUv;
varying float vAlpha;
varying float vDist;
varying vec3 vLight;
varying float vSeed;
void main() {
  vec2 c = vUv * 2.0 - 1.0;
  float a = exp(-c.x * c.x * 3.2) * (1.0 - c.y * c.y);
  a *= 0.65 + 0.35 * sin(c.y * 9.0 + vSeed * 60.0);
  a *= vAlpha * uOpacity;
  if (a < 0.003) discard;
  vec3 col = min(max(vLight, uFogColor * 1.25 + vec3(0.05)), vec3(uLightClamp));
  float fd = uFogDensity * vDist;
  col = mix(col, uFogColor, (1.0 - exp(-fd * fd)) * 0.8);
  gl_FragColor = vec4(col, a);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

const PUFF_VERT = /* glsl */ `
attribute vec4 aSpawn;  // x, y, z, Startzeit
attribute vec4 aVel;    // vx, vy, vz, Lebensdauer
attribute vec2 aMisc;   // Größe, Zufall
uniform float uTime;
uniform vec2 uWindVel;
uniform vec3 uSunColor;
uniform vec3 uAmbient;
varying vec2 vUv;
varying float vAlpha;
varying vec3 vLight;
varying float vSeed;
void main() {
  float age = uTime - aSpawn.w;
  float life = aVel.w;
  if (age < 0.0 || age > life || life <= 0.0) {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    vAlpha = 0.0;
    return;
  }
  float k = 3.2; // Luftwiderstand von Pulverschnee
  float dragInt = (1.0 - exp(-k * age)) / k;
  vec3 p = aSpawn.xyz + aVel.xyz * dragInt;
  p.y -= 1.1 * age * age;
  p.xz += uWindVel * age * 0.45;
  float life01 = age / life;
  float size = aMisc.x * (0.55 + life01 * 1.6);
  vec4 mv = viewMatrix * vec4(p, 1.0);
  float ang = aMisc.y * 6.2831 + age * 0.8;
  vec2 c = position.xy;
  mv.xy += vec2(cos(ang) * c.x - sin(ang) * c.y, sin(ang) * c.x + cos(ang) * c.y) * size;
  gl_Position = projectionMatrix * mv;
  vUv = uv;
  vAlpha = pow(1.0 - life01, 1.4) * smoothstep(0.0, 0.05, age);
  vLight = uAmbient + uSunColor * 0.5;
  vSeed = aMisc.y;
}
`;

const PUFF_FRAG = /* glsl */ `
uniform float uOpacity;
uniform float uLightClamp;
varying vec2 vUv;
varying float vAlpha;
varying vec3 vLight;
varying float vSeed;
void main() {
  vec2 c = vUv * 2.0 - 1.0;
  float r = length(c);
  float n = 0.75 + 0.25 * sin(c.x * 7.0 + vSeed * 40.0) * sin(c.y * 6.0 - vSeed * 23.0);
  float a = smoothstep(1.0, 0.15, r) * n * vAlpha * uOpacity;
  if (a < 0.004) discard;
  gl_FragColor = vec4(min(max(vLight, vec3(0.12, 0.14, 0.18)), vec3(uLightClamp)), a);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

// ---------------------------------------------------------------------------
// Prozeduraler Flocken-Atlas (2x2: weich, Dendrit, Aggregat, Plättchen)
// ---------------------------------------------------------------------------
function createFlakeAtlas() {
  const S = 256;
  const C = S / 2;
  const cv = document.createElement('canvas');
  cv.width = S;
  cv.height = S;
  const g = cv.getContext('2d');
  g.clearRect(0, 0, S, S);

  const soft = (cx, cy, r, a = 1) => {
    const gr = g.createRadialGradient(cx, cy, 0, cx, cy, r);
    gr.addColorStop(0, `rgba(255,255,255,${a})`);
    gr.addColorStop(0.35, `rgba(250,252,255,${a * 0.75})`);
    gr.addColorStop(1, 'rgba(240,246,255,0)');
    g.fillStyle = gr;
    g.beginPath();
    g.arc(cx, cy, r, 0, Math.PI * 2);
    g.fill();
  };

  // 0: weiche runde Flocke (auch für Sturm-Schlieren)
  soft(C * 0.5, C * 0.5, C * 0.42, 1);

  // 1: Dendrit-Kristall
  {
    const cx = C * 1.5;
    const cy = C * 0.5;
    soft(cx, cy, C * 0.40, 0.45);
    g.strokeStyle = 'rgba(255,255,255,0.95)';
    g.lineCap = 'round';
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      const ex = cx + Math.cos(a) * C * 0.36;
      const ey = cy + Math.sin(a) * C * 0.36;
      g.lineWidth = 3.2;
      g.beginPath();
      g.moveTo(cx, cy);
      g.lineTo(ex, ey);
      g.stroke();
      g.lineWidth = 2.0;
      for (const f of [0.45, 0.7]) {
        const bx = cx + Math.cos(a) * C * 0.36 * f;
        const by = cy + Math.sin(a) * C * 0.36 * f;
        for (const s of [-1, 1]) {
          const ba = a + s * 0.75;
          g.beginPath();
          g.moveTo(bx, by);
          g.lineTo(bx + Math.cos(ba) * C * 0.11, by + Math.sin(ba) * C * 0.11);
          g.stroke();
        }
      }
    }
    soft(cx, cy, C * 0.12, 1);
  }

  // 2: Aggregat (verklumpte Flocken)
  {
    const cx = C * 0.5;
    const cy = C * 1.5;
    const pts = [[0, 0, 0.26], [0.14, -0.08, 0.18], [-0.13, 0.07, 0.19], [0.05, 0.15, 0.15], [-0.08, -0.14, 0.14]];
    for (const [ox, oy, r] of pts) soft(cx + ox * C, cy + oy * C, r * C, 0.85);
  }

  // 3: Sechseckiges Plättchen mit Glanzpunkt
  {
    const cx = C * 1.5;
    const cy = C * 1.5;
    soft(cx, cy, C * 0.38, 0.55);
    g.fillStyle = 'rgba(255,255,255,0.7)';
    g.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2 + 0.3;
      const x = cx + Math.cos(a) * C * 0.22;
      const y = cy + Math.sin(a) * C * 0.22;
      if (i === 0) g.moveTo(x, y);
      else g.lineTo(x, y);
    }
    g.closePath();
    g.fill();
    soft(cx - C * 0.05, cy - C * 0.05, C * 0.08, 1);
  }

  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.NoColorSpace;
  tex.generateMipmaps = true;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.needsUpdate = true;
  return tex;
}

// ---------------------------------------------------------------------------
// Hauptsystem
// ---------------------------------------------------------------------------
export class SnowWeatherSystem {
  constructor({ scene, renderer, windField, hooks = {} }) {
    this.scene = scene;
    this.renderer = renderer;
    this.wind = windField;
    this.hooks = hooks; // { getSolidHideList(): Object3D[], getCanopyObjects(): Object3D[] }
    this.region = { ...DEFAULT_SNOW_REGION };
    this.tier = -1;
    this.profile = SNOW_QUALITY_PROFILES[1];
    this.group = new THREE.Group();
    this.group.name = 'AeryndorSnowWeather';
    this.group.visible = false;
    this.group.frustumCulled = false;
    scene.add(this.group);

    this.flakeTex = createFlakeAtlas();
    this.intensity = 0;
    this.storm = 0;
    this.driftAmount = 0;
    this.time = 0;
    this._fall = { near: 0, mid: 0, veil: 0 };
    this._windOff = { near: new THREE.Vector2(), mid: new THREE.Vector2(), veil: new THREE.Vector2(), drift: new THREE.Vector2() };
    this._puffIdx = 0;
    this._puffActiveUntil = 0;
    this._occ = null;
    this._occLast = { x: 1e9, z: 1e9, t: -1e9, valid: false };
    this.stats = { occUpdates: 0, lastOccMs: 0, bursts: 0 };
    this._tmpV2 = new THREE.Vector2();
    this._vp = new THREE.Vector2();
    this.snowCover = 0;
    // Adaptive Qualität (standardmäßig aus; enableAdaptiveQuality(true) zum Aktivieren)
    this._adaptive = { enabled: false, cap: 2, avgDt: 1 / 60, slowFor: 0, fastFor: 0, changes: 0 };
    this._requestedTier = 1;
    // Dirty-Range des Burst-Ringpuffers (nur geänderte Instanzen hochladen statt des ganzen Puffers)
    this._puffDirtyMin = Infinity;
    this._puffDirtyMax = -1;

    // Gemeinsame Uniforms (per Referenz in allen Schnee-Materialien)
    this.shared = {
      uTime: { value: 0 },
      uCamPos: { value: new THREE.Vector3() },
      uWindDir: windField ? windField.uniforms.uWindDir : { value: new THREE.Vector2(0.82, 0.57) },
      uWindGust: windField ? windField.uniforms.uWindGust : { value: 0 },
      uWindTurb: windField ? windField.uniforms.uWindTurb : { value: 0.2 },
      uWindStrength: windField ? windField.uniforms.uWindStrength : { value: 0.3 },
      uWindVel: { value: new THREE.Vector2() },
      uFallSpeed: { value: 1.0 },
      uSunDir: { value: new THREE.Vector3(0.3, 0.8, 0.4).normalize() },
      uSunColor: { value: new THREE.Color(0.5, 0.5, 0.5) },
      uAmbient: { value: new THREE.Color(0.5, 0.55, 0.6) },
      uScatter: { value: 2.2 },
      uFogColor: { value: new THREE.Color(0xc8d2dc) },
      uFogDensity: { value: 0.002 },
      uLightClamp: { value: 1.15 },
      uFlakeLift: { value: new THREE.Vector2(1.32, 0.07) },
      uViewportH: { value: 1080 },
      uOccTex: { value: null },
      uCanopyTex: { value: null },
      uOccParams: { value: new THREE.Vector4(0, 0, 1, 0) },
      uOccCam: { value: new THREE.Vector3(0, 0.5, 140) },
      uCanopyOn: { value: 0 },
      uGroundY: { value: 0 },
    };
    this._dummyTex = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
    this._dummyTex.needsUpdate = true;
    this.shared.uOccTex.value = this._dummyTex;
    this.shared.uCanopyTex.value = this._dummyTex;
  }

  // ---------------------------------------------------------------- Aufbau
  setRegion(params = {}) {
    this.region = { ...DEFAULT_SNOW_REGION, ...params };
    for (const k of Object.keys(DEFAULT_SNOW_REGION)) {
      const v = Number(this.region[k]);
      this.region[k] = Number.isFinite(v) ? Math.max(0, v) : DEFAULT_SNOW_REGION[k];
    }
    this.regionName = 'custom';
  }

  /** Setzt eine Regionsvorlage (siehe SNOW_REGION_PRESETS), optional mit Einzel-Overrides. */
  setRegionPreset(name, overrides = {}) {
    const preset = SNOW_REGION_PRESETS[name] || SNOW_REGION_PRESETS.default;
    this.setRegion({ ...preset, ...overrides });
    this.regionName = SNOW_REGION_PRESETS[name] ? name : 'default';
    return this.region;
  }

  /**
   * Adaptive Qualität: senkt die Schnee-Qualitätsstufe bei dauerhaft niedriger Bildrate
   * und hebt sie bei stabiler Bildrate wieder bis zur gewünschten Stufe (ctx.tier) an.
   */
  enableAdaptiveQuality(enabled = true) {
    const a = this._adaptive;
    a.enabled = Boolean(enabled);
    a.slowFor = 0;
    a.fastFor = 0;
    if (!a.enabled) {
      a.cap = 2;
      this.setQuality(this._requestedTier);
    }
  }

  _updateAdaptive(dtRaw) {
    const a = this._adaptive;
    if (!a.enabled || !(dtRaw > 0) || dtRaw > 0.5) return; // Tab-Wechsel/Hänger ignorieren
    a.avgDt += (dtRaw - a.avgDt) * 0.05;
    if (a.avgDt > ADAPTIVE_DOWN_DT) {
      a.slowFor += dtRaw;
      a.fastFor = 0;
    } else if (a.avgDt < ADAPTIVE_UP_DT) {
      a.fastFor += dtRaw;
      a.slowFor = 0;
    } else {
      a.slowFor = Math.max(0, a.slowFor - dtRaw);
      a.fastFor = Math.max(0, a.fastFor - dtRaw);
    }
    const current = Math.min(a.cap, this._requestedTier);
    if (a.slowFor > ADAPTIVE_DOWN_HOLD && current > 0) {
      a.cap = current - 1;
      a.slowFor = 0;
      a.changes++;
    } else if (a.fastFor > ADAPTIVE_UP_HOLD && a.cap < this._requestedTier) {
      a.cap++;
      a.fastFor = 0;
      a.changes++;
    }
  }

  setQuality(tier) {
    const t = Math.max(0, Math.min(2, Number(tier) || 0));
    if (t === this.tier) return;
    this.tier = t;
    this.profile = SNOW_QUALITY_PROFILES[t];
    this._disposeLayers();
    this._buildLayers();
  }

  _disposeLayers() {
    for (const key of ['near', 'mid', 'drift']) {
      const L = this[key];
      if (L) {
        this.group.remove(L.mesh);
        L.mesh.geometry.dispose();
        L.mesh.material.dispose();
        this[key] = null;
      }
    }
    if (this.veils) {
      for (const v of this.veils) {
        this.group.remove(v);
        v.geometry.dispose();
        v.material.dispose();
      }
    }
    this.veils = [];
    if (this._occ && (!this.profile.occlusion || this._occ.res !== this.profile.occRes)) {
      this._occ.solid.dispose();
      this._occ.canopy.dispose();
      this._occ.mat.dispose(); // Override-Material wurde bisher nicht freigegeben
      this._occ = null;
      this._occPending = null;
      this.shared.uOccParams.value.w = 0;
      this.shared.uOccTex.value = this._dummyTex;
      this.shared.uCanopyTex.value = this._dummyTex;
    }
    this._occLast.valid = false;
  }

  _rng(seed) {
    let s = seed >>> 0;
    return () => {
      s = (s + 0x6d2b79f5) >>> 0;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  _makeFlakeLayer(kind, count, radius) {
    const near = kind === 'near';
    const rnd = this._rng(near ? 1337 : 7331);
    const base = new THREE.PlaneGeometry(1, 1);
    const geo = new THREE.InstancedBufferGeometry();
    geo.index = base.index;
    geo.setAttribute('position', base.getAttribute('position'));
    geo.setAttribute('uv', base.getAttribute('uv'));
    const seed = new Float32Array(count * 4);
    const props = new Float32Array(count * 4);
    const atlas = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      seed[i * 4] = rnd();
      seed[i * 4 + 1] = rnd();
      seed[i * 4 + 2] = rnd();
      seed[i * 4 + 3] = (i + rnd()) / count; // Dichte-Rang: stufenlos ein-/ausblendbar
      const big = rnd();
      const sz = near
        ? 0.030 + Math.pow(big, 2.0) * 0.080
        : 0.050 + Math.pow(big, 1.6) * 0.070;
      props[i * 4] = sz;
      // Quantisierte Fall- & Windfaktoren (n/16) -> Offset-Wrapping ohne Sprünge
      const fallN = Math.round((0.62 + rnd() * 0.75 + big * 0.12) * Q);
      const dragN = Math.round((1.18 - big * 0.32 + (rnd() - 0.5) * 0.12) * Q);
      props[i * 4 + 1] = fallN / Q;
      props[i * 4 + 2] = Math.max(10, dragN) / Q;
      props[i * 4 + 3] = rnd();
      const r = rnd();
      atlas[i] = near ? (r < 0.34 ? 0 : r < 0.6 ? 1 : r < 0.84 ? 2 : 3) : (r < 0.7 ? 0 : 3);
    }
    geo.setAttribute('aSeed', new THREE.InstancedBufferAttribute(seed, 4));
    geo.setAttribute('aProps', new THREE.InstancedBufferAttribute(props, 4));
    geo.setAttribute('aAtlas', new THREE.InstancedBufferAttribute(atlas, 1));
    geo.instanceCount = count;
    base.dispose();

    // Flaches, bodenverankertes Volumen: keine Flocken unter dem Gelände verschwendet
    const boxH = near ? Math.max(14, radius * 1.15) : Math.max(28, radius * 0.6);
    const boxXZ = near ? radius * 2 + 4 : radius * 2 + 10;
    const uniforms = {
      ...this.shared,
      uFlakeTex: { value: this.flakeTex },
      uBoxSize: { value: new THREE.Vector3(boxXZ, boxH, boxXZ) },
      uBoxYOffset: { value: 0.0 },
      uFallOffset: { value: 0 },
      uWindOffset: { value: new THREE.Vector2() },
      uDensity: { value: 0 },
      uFade: {
        value: near
          ? new THREE.Vector4(0.25, 0.9, radius * 0.72, radius)
          : new THREE.Vector4(this.profile.nearR * 0.45, this.profile.nearR * 0.9, radius * 0.72, radius * 0.98),
      },
      uSizeMult: { value: 1 },
      uSway: { value: 0.1 },
      uStreak: { value: 0.004 },
      uMinPx: { value: this.profile.minPx },
      uOpacity: { value: near ? 0.95 : 0.82 },
    };
    const mat = new THREE.ShaderMaterial({
      uniforms,
      vertexShader: FLAKE_VERT,
      fragmentShader: FLAKE_FRAG,
      defines: near ? { SNOW_NEAR: 1 } : {},
      transparent: true,
      depthWrite: false,
      depthTest: true,
      blending: THREE.NormalBlending,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.frustumCulled = false;
    mesh.renderOrder = near ? 12 : 11;
    mesh.name = near ? 'SnowNearFlakes' : 'SnowMidFlakes';
    this.group.add(mesh);
    return { mesh, uniforms, count, box: uniforms.uBoxSize.value, kind };
  }

  _makeVeils(n) {
    const radii = [26, 42, 60].slice(0, n);
    const out = [];
    radii.forEach((r, i) => {
      const geo = new THREE.CylinderGeometry(r, r, 46, 48, 1, true);
      const uniforms = {
        ...this.shared,
        uWindOffset: { value: new THREE.Vector2() },
        uFallOffset: { value: 0 },
        uOpacity: { value: 0 },
        uLitColor: { value: new THREE.Color(1, 1, 1) },
        uStreakiness: { value: 0 },
        uScale: { value: 0.16 - i * 0.03 },
        uSeed: { value: i * 17.3 },
      };
      const mat = new THREE.ShaderMaterial({
        uniforms,
        vertexShader: VEIL_VERT,
        fragmentShader: VEIL_FRAG,
        transparent: true,
        depthWrite: false,
        depthTest: true,
        side: THREE.BackSide,
      });
      const m = new THREE.Mesh(geo, mat);
      m.frustumCulled = false;
      m.renderOrder = 10 - i;
      m.name = `SnowVeil${i}`;
      m.userData.radius = r;
      this.group.add(m);
      out.push(m);
    });
    return out;
  }

  _makeDrift(count) {
    const rnd = this._rng(4242);
    const base = new THREE.PlaneGeometry(1, 1);
    const geo = new THREE.InstancedBufferGeometry();
    geo.index = base.index;
    geo.setAttribute('position', base.getAttribute('position'));
    geo.setAttribute('uv', base.getAttribute('uv'));
    const seed = new Float32Array(count * 4);
    const props = new Float32Array(count * 4);
    for (let i = 0; i < count; i++) {
      seed[i * 4] = rnd();
      seed[i * 4 + 1] = rnd();
      seed[i * 4 + 2] = rnd();
      seed[i * 4 + 3] = (i + rnd()) / count;
      props[i * 4] = 0.9 + rnd() * 2.2;
      props[i * 4 + 1] = Math.round((1.15 + rnd() * 0.7) * Q) / Q;
      props[i * 4 + 2] = rnd();
      props[i * 4 + 3] = 0.10 + rnd() * 0.22;
    }
    geo.setAttribute('aSeed', new THREE.InstancedBufferAttribute(seed, 4));
    geo.setAttribute('aProps', new THREE.InstancedBufferAttribute(props, 4));
    geo.instanceCount = count;
    base.dispose();
    const box = 72;
    const uniforms = {
      ...this.shared,
      uBox: { value: new THREE.Vector2(box, box) },
      uDriftOffset: { value: new THREE.Vector2() },
      uAmount: { value: 0 },
      uFarFade: { value: box * 0.48 },
      uOpacity: { value: 0.32 },
    };
    const mat = new THREE.ShaderMaterial({
      uniforms,
      vertexShader: DRIFT_VERT,
      fragmentShader: DRIFT_FRAG,
      transparent: true,
      depthWrite: false,
      depthTest: true,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.frustumCulled = false;
    mesh.renderOrder = 9;
    mesh.name = 'SnowGroundDrift';
    this.group.add(mesh);
    return { mesh, uniforms, count, box };
  }

  _makePuffs(count) {
    const base = new THREE.PlaneGeometry(1, 1);
    const geo = new THREE.InstancedBufferGeometry();
    geo.index = base.index;
    geo.setAttribute('position', base.getAttribute('position'));
    geo.setAttribute('uv', base.getAttribute('uv'));
    const spawn = new THREE.InstancedBufferAttribute(new Float32Array(count * 4), 4);
    const vel = new THREE.InstancedBufferAttribute(new Float32Array(count * 4), 4);
    const misc = new THREE.InstancedBufferAttribute(new Float32Array(count * 2), 2);
    spawn.setUsage(THREE.DynamicDrawUsage);
    vel.setUsage(THREE.DynamicDrawUsage);
    misc.setUsage(THREE.DynamicDrawUsage);
    for (let i = 0; i < count; i++) spawn.array[i * 4 + 3] = -1e6;
    geo.setAttribute('aSpawn', spawn);
    geo.setAttribute('aVel', vel);
    geo.setAttribute('aMisc', misc);
    geo.instanceCount = count;
    base.dispose();
    const uniforms = { ...this.shared, uOpacity: { value: 0.62 } };
    const mat = new THREE.ShaderMaterial({
      uniforms,
      vertexShader: PUFF_VERT,
      fragmentShader: PUFF_FRAG,
      transparent: true,
      depthWrite: false,
      depthTest: true,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.frustumCulled = false;
    mesh.renderOrder = 13;
    mesh.name = 'SnowBurstPool';
    mesh.visible = false;
    this.scene.add(mesh); // eigenständig: Pulverschnee-Aufwirbelungen auch ohne aktiven Schneefall
    return { mesh, uniforms, count, spawn, vel, misc };
  }

  _buildLayers() {
    const p = this.profile;
    this.near = this._makeFlakeLayer('near', p.near, p.nearR);
    this.mid = this._makeFlakeLayer('mid', p.mid, p.midR);
    this.veils = p.veils > 0 ? this._makeVeils(p.veils) : [];
    this.drift = p.drift > 0 ? this._makeDrift(p.drift) : null;
    if (this.puffs) {
      this.scene.remove(this.puffs.mesh);
      this.puffs.mesh.geometry.dispose();
      this.puffs.mesh.material.dispose();
    }
    this.puffs = this._makePuffs(p.puffs);
    this._puffIdx = 0;
    if (p.occlusion && !this._occ) this._createOcclusion(p.occRes, p.occHalf);
  }

  // ---------------------------------------------------------------- Abschattung
  _createOcclusion(res, half) {
    const mk = () => {
      const depthTex = new THREE.DepthTexture(res, res);
      depthTex.type = THREE.UnsignedIntType;
      depthTex.minFilter = THREE.NearestFilter;
      depthTex.magFilter = THREE.NearestFilter;
      return new THREE.WebGLRenderTarget(res, res, {
        depthBuffer: true,
        depthTexture: depthTex,
        minFilter: THREE.NearestFilter,
        magFilter: THREE.NearestFilter,
        generateMipmaps: false,
      });
    };
    const near = 0.5;
    const far = 140;
    const cam = new THREE.OrthographicCamera(-half, half, half, -half, near, far);
    cam.rotation.set(-Math.PI / 2, 0, 0);
    this._occ = {
      res,
      half,
      near,
      far,
      cam,
      solid: mk(),
      canopy: mk(),
      mat: new THREE.MeshBasicMaterial({ colorWrite: false, side: THREE.DoubleSide }),
    };
  }

  _renderOcclusion(cx, cy, cz, stage = 'both') {
    const o = this._occ;
    const r = this.renderer;
    if (!o || !r) return;
    const t0 = performance.now();
    const step = Math.max(1, (o.half * 2) / o.res) * 4;
    const sx = Math.round(cx / step) * step;
    const sz = Math.round(cz / step) * step;
    const camY = cy + 60;
    o.cam.position.set(sx, camY, sz);
    o.cam.updateMatrixWorld(true);
    const doCanopy = stage !== 'solid';
    const doSolid = stage !== 'canopy';

    const prevTarget = r.getRenderTarget();
    const prevOverride = this.scene.overrideMaterial;
    const prevShadowAuto = r.shadowMap.autoUpdate;
    const prevShadowNeeds = r.shadowMap.needsUpdate;
    const prevGroupVis = this.group.visible;
    r.shadowMap.autoUpdate = false;
    r.shadowMap.needsUpdate = false;
    this.group.visible = false;
    this.scene.overrideMaterial = o.mat;

    // A) Baumkronen-/Busch-Pass (nur Layer 5 -> teilweise Abschirmung)
    if (doCanopy && this.profile.canopy && this.hooks.getCanopyObjects) {
      const canopy = this.hooks.getCanopyObjects() || [];
      for (const obj of canopy) if (obj) obj.layers.enable(CANOPY_LAYER);
      o.cam.layers.set(CANOPY_LAYER);
      r.setRenderTarget(o.canopy);
      r.clear(true, true, false);
      r.render(this.scene, o.cam);
    }

    // B) Massive Strukturen: Terrain, Gebäude, Dächer, Brücken, Felsen, Stämme
    if (doSolid) {
      const hidden = [];
      const hideList = this.hooks.getSolidHideList ? this.hooks.getSolidHideList() || [] : [];
      for (const obj of hideList) {
        if (obj && obj.visible) {
          obj.visible = false;
          hidden.push(obj);
        }
      }
      o.cam.layers.set(0);
      r.setRenderTarget(o.solid);
      r.clear(true, true, false);
      r.render(this.scene, o.cam);
      for (let i = 0; i < hidden.length; i++) hidden[i].visible = true;
    }

    this.scene.overrideMaterial = prevOverride;
    this.group.visible = prevGroupVis;
    r.setRenderTarget(prevTarget);
    r.shadowMap.autoUpdate = prevShadowAuto;
    r.shadowMap.needsUpdate = prevShadowNeeds;

    const sh = this.shared;
    if (doSolid) {
      sh.uOccTex.value = o.solid.depthTexture;
      sh.uOccParams.value.set(sx, sz, o.half, 1);
      sh.uOccCam.value.set(camY, o.near, o.far);
      this._occLast = { x: cx, z: cz, t: this.time, valid: true };
      this.stats.occUpdates++;
    }
    if (doCanopy) {
      sh.uCanopyTex.value = o.canopy.depthTexture;
      sh.uCanopyOn.value = this.profile.canopy ? 1 : 0;
    }
    const ms = performance.now() - t0;
    this.stats.lastOccMs = +ms.toFixed(2);
    // Ringpuffer der letzten 16 Messungen (ohne neues Array pro Messung)
    const samples = this.stats.occMsSamples || (this.stats.occMsSamples = []);
    samples.push(+ms.toFixed(2));
    if (samples.length > 16) samples.shift();
  }

  invalidateOcclusion() {
    this._occLast.valid = false;
  }

  // ---------------------------------------------------------------- Interaktion
  /**
   * Pulverschnee-Aufwirbelung (Fußtritt, Sprint, Landung, Kampf-Bodenkontakt).
   * Ringpuffer auf der GPU – beliebig viele Charaktere ohne neue Objekte/Materialien.
   */
  emitBurst(x, y, z, opts = {}) {
    const P = this.puffs;
    if (!P || !Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) return;
    const count = Math.max(1, Math.min(24, Math.round(opts.count ?? 5)));
    const strength = opts.strength ?? 1.0;
    const dirX = opts.dirX ?? 0;
    const dirZ = opts.dirZ ?? 0;
    const size = opts.size ?? 0.12;
    const life = opts.life ?? 0.75;
    const now = this.time;
    for (let i = 0; i < count; i++) {
      const idx = this._puffIdx;
      this._puffIdx = (this._puffIdx + 1) % P.count;
      const a = Math.random() * Math.PI * 2;
      const sp = (0.35 + Math.random() * 0.9) * strength;
      P.spawn.setXYZW(idx, x + Math.cos(a) * 0.06, y + 0.03, z + Math.sin(a) * 0.06, now + Math.random() * 0.04);
      P.vel.setXYZW(
        idx,
        Math.cos(a) * sp + dirX * strength * 0.9,
        (0.55 + Math.random() * 0.9) * strength,
        Math.sin(a) * sp + dirZ * strength * 0.9,
        life * (0.7 + Math.random() * 0.6)
      );
      P.misc.setXY(idx, size * (0.7 + Math.random() * 0.8), Math.random());
      if (idx < this._puffDirtyMin) this._puffDirtyMin = idx;
      if (idx > this._puffDirtyMax) this._puffDirtyMax = idx;
    }
    // Upload wird gebündelt einmal pro Frame in update() ausgelöst (_flushPuffUploads)
    this._puffDirty = true;
    P.mesh.visible = true;
    this._puffActiveUntil = Math.max(this._puffActiveUntil, now + life * 1.4 + 0.1);
    this.stats.bursts++;
  }

  /** Lädt nur den geänderten Bereich des Burst-Ringpuffers hoch (statt aller Instanzen pro emitBurst). */
  _flushPuffUploads() {
    const P = this.puffs;
    if (!P || !this._puffDirty) return;
    const lo = this._puffDirtyMin;
    const hi = this._puffDirtyMax;
    const partial = typeof P.spawn.addUpdateRange === 'function' && hi >= lo && hi - lo < P.count - 1;
    for (const [attr, size] of [
      [P.spawn, 4],
      [P.vel, 4],
      [P.misc, 2],
    ]) {
      if (partial) {
        attr.clearUpdateRanges?.();
        attr.addUpdateRange(lo * size, (hi - lo + 1) * size);
      }
      attr.needsUpdate = true;
    }
    this._puffDirty = false;
    this._puffDirtyMin = Infinity;
    this._puffDirtyMax = -1;
  }

  /**
   * Komfort-API für Gameplay-Code: Aufwirbelung nach Interaktionsart.
   * Skaliert automatisch mit der Schneedecke – ohne Schnee am Boden kein Pulverschnee.
   * @param {'step'|'sprint'|'mount'|'land'|'impact'|'roll'} type
   * @param {{dirX?:number, dirZ?:number, scale?:number, force?:boolean}} opts
   */
  emitInteraction(type, x, y, z, opts = {}) {
    const preset = BURST_PRESETS[type] || BURST_PRESETS.step;
    const coverFactor = opts.force ? 1 : smooth(0.08, 0.5, this.snowCover);
    if (coverFactor <= 0.01) return false;
    const scale = Math.max(0.1, Number(opts.scale) || 1) * (0.5 + 0.5 * coverFactor);
    this.emitBurst(x, y, z, {
      count: Math.max(1, Math.round(preset.count * scale)),
      strength: preset.strength * scale,
      size: preset.size * (0.85 + 0.15 * scale),
      life: preset.life,
      dirX: opts.dirX ?? 0,
      dirZ: opts.dirZ ?? 0,
    });
    return true;
  }

  // ---------------------------------------------------------------- Atmosphäre
  /** Vom Wetter-/Lichtsystem genutzt: Nebel-Multiplikator, Nebelfarbe & Lichtdämpfung */
  getAtmosphere() {
    const I = this.intensity;
    const s = this.storm;
    const g = this.wind ? this.wind.gust * this.wind.gustiness : 0;
    const fogMult = (1.0 + I * 1.5 + I * s * 4.0 + g * s * I * 1.2) * this.region.fogMult;
    return {
      active: I > 0.01,
      intensity: I,
      storm: s,
      fogMult,
      fogTintAmount: Math.min(0.7, 0.18 + I * 0.32 + s * I * 0.2),
      sunDamp: 1 - Math.min(0.55, I * 0.18 + s * I * 0.37),
      contrastDamp: Math.min(0.5, I * 0.12 + s * I * 0.3),
    };
  }

  // ---------------------------------------------------------------- Update
  /**
   * @param {number} dt
   * @param {object} ctx { camera, snowRate, snowCover, tempC, sunDir, sunColor, sunIntensity,
   *   ambientColor, ambientIntensity, fogColor, fogDensity, groundY, tier, isNight }
   */
  update(dt, ctx) {
    if (!ctx || !ctx.camera) return;
    const dtRaw = Math.max(0, Number(dt) || 0);
    const d = Math.min(0.1, dtRaw);
    this.time += d;
    if (ctx.tier !== undefined) this._requestedTier = Math.max(0, Math.min(2, Number(ctx.tier) || 0));
    this._updateAdaptive(dtRaw);
    const effTier = this._adaptive.enabled ? Math.min(this._adaptive.cap, this._requestedTier) : this._requestedTier;
    if (ctx.tier !== undefined || this._adaptive.enabled || !this.near) this.setQuality(effTier);
    this._flushPuffUploads();
    const sh = this.shared;
    sh.uTime.value = this.time;

    const wind = this.wind;
    const rate = clamp01(ctx.snowRate || 0) * this.region.densityMult;
    // Leichte Glättung, damit Wetterwechsel immer stufenlos verlaufen
    this.intensity += (Math.min(1, rate) - this.intensity) * Math.min(1, d * 1.5);
    const I = this.intensity;
    const windStrength = wind ? wind.strength : 0.3;
    this.storm = smooth(0.55, 1.65, windStrength);
    const S = this.storm;
    const cover = clamp01(ctx.snowCover || 0);
    this.snowCover = cover;
    const targetDrift = this.drift
      ? smooth(0.45, 1.4, windStrength) * clamp01(Math.max(cover * 1.1, I * 0.8)) * this.region.driftMult
      : 0;
    this.driftAmount += (targetDrift - this.driftAmount) * Math.min(1, d * 0.8);

    const flakesOn = I > 0.008;
    const driftOn = this.driftAmount > 0.01;
    this.group.visible = flakesOn || driftOn;
    if (this.puffs && this.puffs.mesh.visible && this.time > this._puffActiveUntil) this.puffs.mesh.visible = false;
    this._updateLighting(ctx);
    if (!this.group.visible) return;

    const cam = ctx.camera;
    sh.uCamPos.value.copy(cam.position);
    sh.uGroundY.value = ctx.groundY ?? cam.position.y - 8;
    if (this.renderer) {
      this.renderer.getDrawingBufferSize(this._vp);
      sh.uViewportH.value = Math.max(240, this._vp.y);
    }

    // Wind & Fall (gemeinsame Windquelle)
    const windMult = this.region.windMult;
    const wvx = (wind ? wind.velocity.x : 1.5) * windMult;
    const wvz = (wind ? wind.velocity.y : 0.8) * windMult;
    sh.uWindVel.value.set(wvx, wvz);
    const sleet = clamp01(((ctx.tempC ?? -3) - 0.0) / 3.0);
    const fallSpeed = (0.95 + I * 0.25 + S * 0.25) * (1 + sleet * 0.9);
    sh.uFallSpeed.value = fallSpeed;

    // Integrierte Offsets (gewrappt auf 16x Volumengröße -> exakt sprungfrei)
    const integrate = (key, box) => {
      const fy = Q * box.y;
      const fx = Q * box.x;
      this._fall[key] = (this._fall[key] + fallSpeed * d) % fy;
      const wo = this._windOff[key];
      wo.x = (wo.x + wvx * d) % fx;
      wo.y = (wo.y + wvz * d) % fx;
    };

    // Nah- & Mittelbereich
    for (const L of [this.near, this.mid]) {
      if (!L) continue;
      L.mesh.visible = flakesOn;
      if (!flakesOn) continue;
      integrate(L.kind, L.box);
      const u = L.uniforms;
      u.uFallOffset.value = this._fall[L.kind];
      u.uWindOffset.value.copy(this._windOff[L.kind]);
      const isNear = L.kind === 'near';
      // Volumenunterkante knapp unter dem Boden verankern (weich nachgeführt -> keine Sprünge)
      const groundY = sh.uGroundY.value;
      const bottomPad = isNear ? 1.5 : 3.0;
      const targetOff = Math.max(-L.box.y * 0.5 + 2.0, groundY - bottomPad + L.box.y * 0.5 - cam.position.y);
      u.uBoxYOffset.value = targetOff;
      u.uDensity.value = isNear ? 0.12 + 0.88 * Math.pow(I, 0.9) : 0.08 + 0.92 * I;
      u.uSizeMult.value = this.region.flakeSizeMult * (isNear ? 1.0 + I * 0.25 - sleet * 0.35 : 1.0 - sleet * 0.25);
      u.uSway.value = (0.11 - S * 0.05) * (1 - sleet * 0.6);
      u.uStreak.value = 0.002 + 0.006 * S + sleet * 0.006;
      u.uOpacity.value = (isNear ? 1.0 : 0.92) * (1 - sleet * 0.35);
    }

    // Fernbereich: windgetriebene Schneeschleier (tiefenweich angebunden)
    if (this.veils.length) {
      this._fall.veil = (this._fall.veil + fallSpeed * d) % 4096;
      const wo = this._windOff.veil;
      wo.x = (wo.x + wvx * d) % 8192;
      wo.y = (wo.y + wvz * d) % 8192;
      const op = (0.025 + 0.10 * I + 0.15 * I * S) * this.region.veilMult;
      for (const v of this.veils) {
        v.visible = flakesOn;
        v.position.set(cam.position.x, cam.position.y + 4, cam.position.z);
        const u = v.material.uniforms;
        u.uWindOffset.value.copy(wo);
        u.uFallOffset.value = this._fall.veil;
        u.uOpacity.value = op;
        u.uStreakiness.value = S;
      }
    }

    // Bodennahe Verwehungen
    if (this.drift) {
      this.drift.mesh.visible = driftOn;
      if (driftOn) {
        const u = this.drift.uniforms;
        const box = this.drift.box;
        const dw = u.uDriftOffset.value;
        dw.x = (dw.x + wvx * 1.15 * d) % (Q * box);
        dw.y = (dw.y + wvz * 1.15 * d) % (Q * box);
        u.uAmount.value = this.driftAmount;
        u.uOpacity.value = 0.22 + 0.2 * S;
      }
    }

    // Abschattungskarte nur bei Bewegung/zeitlich gestaffelt neu rendern (statische Welt)
    if (this._occ && this.profile.occlusion) {
      const L = this._occLast;
      const moved = Math.hypot(cam.position.x - L.x, cam.position.z - L.z);
      if (this._occPending) {
        // Zweiter Frame: Baumkronen-Pass mit identischem Zentrum
        const pnd = this._occPending;
        this._occPending = null;
        this._renderOcclusion(pnd.x, pnd.y, pnd.z, 'canopy');
      } else if (!L.valid || moved > this._occ.half * 0.22 || this.time - L.t > 12.0) {
        const gy = ctx.groundY ?? cam.position.y - 6;
        this._renderOcclusion(cam.position.x, gy, cam.position.z, 'solid');
        if (this.profile.canopy) this._occPending = { x: cam.position.x, y: gy, z: cam.position.z };
      }
    } else {
      sh.uOccParams.value.w = 0;
    }
  }

  _updateLighting(ctx) {
    const sh = this.shared;
    if (ctx.sunDir) sh.uSunDir.value.copy(ctx.sunDir).normalize();
    const sunI = Math.max(0, ctx.sunIntensity ?? 1);
    const ambI = Math.max(0, ctx.ambientIntensity ?? 1);
    const atmo = this.getAtmosphere();
    if (ctx.sunColor) sh.uSunColor.value.copy(ctx.sunColor).multiplyScalar(Math.min(1.0, sunI * 0.42) * atmo.sunDamp);
    if (ctx.ambientColor) sh.uAmbient.value.copy(ctx.ambientColor).multiplyScalar(Math.min(1.15, ambI * 0.78));
    sh.uScatter.value = ctx.isNight ? 1.2 : 2.4 * (1 - this.storm * 0.4);
    if (ctx.fogColor) sh.uFogColor.value.copy(ctx.fogColor);
    sh.uFogDensity.value = ctx.fogDensity ?? 0.002;
    sh.uLightClamp.value = ctx.isNight ? 1.0 : 1.6;
    // Nachts heben sich Flocken stärker vom dunklen Grund ab (Mond-/Restlicht wird an Kristallen gestreut)
    sh.uFlakeLift.value.set(ctx.isNight ? 1.9 : 1.32, ctx.isNight ? 0.13 : 0.07);
    if (this.veils && this.veils.length) {
      const tmp = this._tmpLit || (this._tmpLit = new THREE.Color());
      const lit = this.veils[0].material.uniforms.uLitColor.value;
      tmp.copy(sh.uSunColor.value).add(sh.uAmbient.value);
      lit.copy(sh.uFogColor.value).lerp(tmp, 0.35);
      for (const v of this.veils) v.material.uniforms.uLitColor.value.copy(lit);
    }
  }

  getStats() {
    const p = this.profile;
    return {
      tier: this.tier,
      profile: p.name,
      intensity: +this.intensity.toFixed(3),
      storm: +this.storm.toFixed(3),
      driftAmount: +this.driftAmount.toFixed(3),
      visible: this.group.visible,
      nearInstances: this.near ? this.near.count : 0,
      midInstances: this.mid ? this.mid.count : 0,
      activeNear: this.near ? Math.round(this.near.count * this.near.uniforms.uDensity.value) : 0,
      activeMid: this.mid ? Math.round(this.mid.count * this.mid.uniforms.uDensity.value) : 0,
      veils: this.veils ? this.veils.length : 0,
      driftInstances: this.drift ? this.drift.count : 0,
      puffPool: this.puffs ? this.puffs.count : 0,
      occlusion: Boolean(this._occ && this.shared.uOccParams.value.w > 0.5),
      occRes: this._occ ? this._occ.res : 0,
      occUpdates: this.stats.occUpdates,
      lastOccMs: this.stats.lastOccMs,
      occMsSamples: this.stats.occMsSamples || [],
      bursts: this.stats.bursts,
      region: this.regionName || 'custom',
      requestedTier: this._requestedTier,
      adaptive: this._adaptive.enabled
        ? { cap: this._adaptive.cap, avgFps: +(1 / this._adaptive.avgDt).toFixed(1), changes: this._adaptive.changes }
        : null,
    };
  }

  dispose() {
    this._disposeLayers();
    if (this.puffs) {
      this.scene.remove(this.puffs.mesh);
      this.puffs.mesh.geometry.dispose();
      this.puffs.mesh.material.dispose();
      this.puffs = null;
    }
    if (this._occ) {
      this._occ.solid.dispose();
      this._occ.canopy.dispose();
      this._occ.mat.dispose();
      this._occ = null;
    }
    this.flakeTex.dispose();
    this._dummyTex.dispose();
    this.scene.remove(this.group);
  }
}
