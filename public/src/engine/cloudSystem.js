// ============================================================================
// AERYNDOR: LEGACY OF THE MONOLITHS – Volumetrisches 3D-Wolkensystem (cloudSystem.js)
// ============================================================================
//  - 5 Wolkentypen (Cumulus, Stratus, Cirrus, Cumulonimbus, Altocumulus)
//  - Raymarching, Wolkenschatten & Kopplung an Wetter, Wind und Tageszeit
// ============================================================================

import * as THREE from '../../vendor/three.module.js';

export const CLOUD_TYPES = {
  cumulus: {
    id: 'cumulus',
    name: 'Cumulus (Haufengewölk)',
    baseHeight: 1350.0,
    thickness: 1100.0,
    density: 1.15,
    coverage: 0.42,
    anvil: 0.0,
    erosion: 0.35,
    windMultiplier: 1.0,
    description: 'Klassische, bauschige Schönwetterwolken mit flacher Basis und gewölbter Kuppe.',
  },
  stratus: {
    id: 'stratus',
    name: 'Stratus (Schichtwolken)',
    baseHeight: 750.0,
    thickness: 480.0,
    density: 0.85,
    coverage: 0.82,
    anvil: 0.0,
    erosion: 0.15,
    windMultiplier: 0.75,
    description: 'Ausgedehnte, tief liegende Wolkenschicht für trübe Tage, Nebel und Dauerregen.',
  },
  cirrus: {
    id: 'cirrus',
    name: 'Cirrus (Federwolken)',
    baseHeight: 3100.0,
    thickness: 350.0,
    density: 0.32,
    coverage: 0.35,
    anvil: 0.0,
    erosion: 0.65,
    windMultiplier: 1.85,
    description: 'Zarte, faserige Eiswolken in großer Höhe mit feinen Schleiern und Transparenz.',
  },
  cumulonimbus: {
    id: 'cumulonimbus',
    name: 'Cumulonimbus (Gewittertürme)',
    baseHeight: 650.0,
    thickness: 3400.0,
    density: 2.65,
    coverage: 0.95,
    anvil: 0.85,
    erosion: 0.42,
    windMultiplier: 1.25,
    description: 'Massive, hoch aufragende Gewitterwolken mit düsterer Unterseite und breitem Amboss.',
  },
  altocumulus: {
    id: 'altocumulus',
    name: 'Altocumulus (Schäfchenwolken)',
    baseHeight: 2200.0,
    thickness: 600.0,
    density: 0.78,
    coverage: 0.52,
    anvil: 0.0,
    erosion: 0.48,
    windMultiplier: 1.20,
    description: 'Mittelgroße, regelmäßig gerippte Wolkenfelder mit natürlichen Lücken und Schäfchenmuster.',
  },
};

const THUNDER_WEATHER = new Set(['thunderstorm', 'severe_thunderstorm']);
const CLEAR_WEATHER = new Set(['sunny', 'partly_cloudy']);
const AURORA_WEATHER = new Set(['sunny', 'partly_cloudy', 'snow']);

export class VolumetricCloudManager {
  constructor(scene, renderer, options = {}) {
    this.scene = scene;
    this.renderer = renderer;
    this.engine = options.engine || null;

    // Qualitätsstufe: 1 = Low (Fast Shell), 2 = Medium (10 Steps), 3 = High (18 Steps), 4 = Ultra (28 Steps)
    this.quality = options.quality ?? 2;
    this.enabled = options.enabled !== false;

    // Aktueller Wolkentyp & Parameter
    this.cloudType = options.cloudType || 'auto'; // 'auto' | 'cumulus' | 'stratus' | 'cirrus' | 'cumulonimbus' | 'altocumulus'
    this.activePresetKey = 'cumulus';

    // Physikalische Wolkenparameter
    this.coverage = options.coverage ?? 0.45;
    this.density = options.density ?? 1.15;
    this.cloudHeight = options.cloudHeight ?? 1350.0;
    this.thickness = options.thickness ?? 1100.0;
    this.shadowStrength = options.shadowStrength ?? 0.45;
    this.lightScattering = options.lightScattering ?? 1.0;

    // Wind & Advektion
    this.windSpeed = options.windSpeed ?? 14.0; // km/h
    this.windDirection = options.windDirection ?? 0.45; // rad
    this.windOffset = new THREE.Vector2(0, 0);
    this.windHighOffset = new THREE.Vector2(0, 0);
    this._windStep = new THREE.Vector2(); // Scratch-Vektor (keine Allokation pro Frame)
    this.cloudTime = 0.0;

    // Blitz-Effekt (Illumination aus dem Wolkeninneren)
    this.lightningFlash = 0.0;

    // Mesh & Shader-Objekte
    this.cloudDomeMesh = null;
    this.cloudMaterial = null;
    this.cloudUniforms = null;

    this.initCloudDome();
  }

  initCloudDome() {
    // Sphärische Wolkenkuppel (Radius 420m, knapp unter der Himmelskuppel 450m)
    const domeGeo = new THREE.SphereGeometry(1, 48, 32);

    this.cloudUniforms = {
      // Beleuchtungsvektoren
      uSunDir: { value: new THREE.Vector3(0.3, 0.8, 0.4).normalize() },
      uMoonDir: { value: new THREE.Vector3(-0.3, 0.8, -0.4).normalize() },
      uSunColor: { value: new THREE.Color(0xfffbeb) },
      uMoonColor: { value: new THREE.Color(0xa8d2f8) },
      uAmbientSkyColor: { value: new THREE.Color(0x38bdf8) },
      uAmbientGroundColor: { value: new THREE.Color(0x1e293b) },
      uSunIntensity: { value: 1.0 },
      uMoonIntensity: { value: 0.0 },
      uTwilightFactor: { value: 0.0 },

      // Wolkenmorphologie
      uCoverage: { value: this.coverage },
      uDensity: { value: this.density },
      uCloudHeight: { value: this.cloudHeight },
      uThickness: { value: this.thickness },
      uAnvilExpansion: { value: 0.0 },
      uErosionStrength: { value: 0.35 },
      uLightScattering: { value: this.lightScattering },

      // Wind-Advektion & Dynamik
      uWindOffset: { value: new THREE.Vector2(0, 0) },
      uWindHighOffset: { value: new THREE.Vector2(0, 0) },
      uCloudTime: { value: 0.0 },

      // Blitzlicht & Qualitätsstufen
      uLightningFlash: { value: 0.0 },
      uQuality: { value: this.quality },
      uRaymarchSteps: { value: this.getRaymarchSteps() },

      // Rissmonolithen V2: Lokale Wolkenverdichtung, Wirbelbewegung & Riss-Blitze
      uRiftFactor: { value: 0.0 },
      uRiftAwakened: { value: 0.0 },
      uRiftCloudDensity: { value: 1.0 },
      uRiftVioletStrength: { value: 1.0 },
      uRiftCrimsonStrength: { value: 1.0 },
      uRiftLightning: { value: 0.0 },
      uRiftDir: { value: new THREE.Vector3(0.0, 0.72, -0.68).normalize() },
      uHighCirrusStrength: { value: 0.35 },
      uAuroraIntensity: { value: 0.0 },
    };

    // Hocheffizienter volumetrischer GLSL-Shader mit prozeduralem 3D-Noise & Henyey-Greenstein Phasenfunktion
    this.cloudMaterial = new THREE.ShaderMaterial({
      uniforms: this.cloudUniforms,
      side: THREE.BackSide,
      transparent: true,
      depthWrite: false,
      depthTest: true,
      fog: false,
      vertexShader: `
        varying vec3 vWorldDir;
        varying vec3 vLocalPos;
        void main() {
          vLocalPos = position;
          vWorldDir = normalize(position);
          vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          // Tiefenwert knapp vor der Himmelskuppel (0.99995) und dem Mond (0.99991), aber hinter allen 3D-Bergen & Bäumen!
          gl_Position = vec4(p.xy, p.w * 0.99985, p.w);
        }
      `,
      fragmentShader: `
        uniform vec3 uSunDir;
        uniform vec3 uMoonDir;
        uniform vec3 uSunColor;
        uniform vec3 uMoonColor;
        uniform vec3 uAmbientSkyColor;
        uniform vec3 uAmbientGroundColor;
        uniform float uSunIntensity;
        uniform float uMoonIntensity;
        uniform float uTwilightFactor;

        uniform float uCoverage;
        uniform float uDensity;
        uniform float uCloudHeight;
        uniform float uThickness;
        uniform float uAnvilExpansion;
        uniform float uErosionStrength;
        uniform float uLightScattering;

        uniform vec2 uWindOffset;
        uniform vec2 uWindHighOffset;
        uniform float uCloudTime;
        uniform float uLightningFlash;
        uniform int uQuality;
        uniform int uRaymarchSteps;

        uniform float uRiftFactor;
        uniform float uRiftAwakened;
        uniform float uRiftCloudDensity;
        uniform float uRiftVioletStrength;
        uniform float uRiftCrimsonStrength;
        uniform float uRiftLightning;
        uniform vec3 uRiftDir;
        uniform float uHighCirrusStrength;
        uniform float uAuroraIntensity;

        varying vec3 vWorldDir;
        varying vec3 vLocalPos;

        // --- SCHNELLE PROZEDURALE 3D-NOISE & WORLEY-ROUTINEN ---
        float hash12(vec2 p) {
          vec3 p3 = fract(vec3(p.xyx) * 0.1031);
          p3 += dot(p3, p3.yzx + 33.33);
          return fract((p3.x + p3.y) * p3.z);
        }

        float hash13(vec3 p) {
          p = fract(p * 0.1031);
          p += dot(p, p.zyx + 31.32);
          return fract((p.x + p.y) * p.z);
        }

        // 3D-Gradienten-Noise
        float noise3D(vec3 p) {
          vec3 i = floor(p);
          vec3 f = fract(p);
          f = f * f * (3.0 - 2.0 * f);
          return mix(
            mix(mix(hash13(i + vec3(0,0,0)), hash13(i + vec3(1,0,0)), f.x),
                mix(hash13(i + vec3(0,1,0)), hash13(i + vec3(1,1,0)), f.x), f.y),
            mix(mix(hash13(i + vec3(0,0,1)), hash13(i + vec3(1,0,1)), f.x),
                mix(hash13(i + vec3(0,1,1)), hash13(i + vec3(1,1,1)), f.x), f.y),
            f.z
          );
        }

        // 3D-Worley (Cellular) Noise für bauschige Blumenkohl-Strukturen
        float worley3D(vec3 p) {
          vec3 i = floor(p);
          vec3 f = fract(p);
          float minDist = 1.0;
          for (int z = -1; z <= 1; z++) {
            for (int y = -1; y <= 1; y++) {
              for (int x = -1; x <= 1; x++) {
                vec3 cell = vec3(float(x), float(y), float(z));
                vec3 pt = cell + vec3(
                  hash13(i + cell + vec3(1.2, 3.4, 5.6)),
                  hash13(i + cell + vec3(7.8, 9.1, 2.3)),
                  hash13(i + cell + vec3(4.5, 6.7, 8.9))
                ) * 0.75 + 0.125;
                float d = length(pt - f);
                minDist = min(minDist, d);
              }
            }
          }
          return 1.0 - minDist;
        }

        // Mehrskalige fraktale Brownsche Bewegung (FBM)
        float fbm3D(vec3 p) {
          float v = 0.0;
          float amp = 0.52;
          for (int i = 0; i < 4; i++) {
            v += amp * noise3D(p);
            p = p * 2.08 + vec3(1.2, 3.4, 5.6);
            amp *= 0.48;
          }
          return v;
        }

        // Henyey-Greenstein Phasenfunktion für atmosphärische Lichtstreuung
        float hgPhase(float cosTheta, float g) {
          float g2 = g * g;
          return (1.0 - g2) / (4.0 * 3.14159265 * pow(max(0.001, 1.0 + g2 - 2.0 * g * cosTheta), 1.5));
        }

        // Dichteprofil abhängig von der relativen Wolkenhöhe h in [0, 1]
        float getHeightProfile(float h) {
          // Flache, scharfe Unterseite
          float bottomGrad = smoothstep(0.0, 0.14, h);
          // Weiche, aufgelöste Oberseite
          float topGrad = smoothstep(1.0, 0.65, h);
          // Amboss-Ausdehnung für Cumulonimbus
          float anvil = uAnvilExpansion * smoothstep(0.55, 0.95, h) * 0.45;
          return bottomGrad * topGrad + anvil;
        }

        // Ermittelt die Wolkendichte an einer beliebigen 3D-Position im Himmel (dichte Gewitterwolkenfront bei Annäherung an Rissmonolith)
        float sampleCloudDensity(vec3 p, float hNorm, float riftFocus) {
          vec3 sampleP = p;

          // Wind-Drift & organische Gewitterwolken-Turbulenz (ohne künstliches Kreis-Drehen!)
          float turbSpeed = 1.0 + uRiftFactor * (0.45 + 0.35 * uRiftAwakened);
          vec3 windCoord = sampleP + vec3(uWindOffset.x * turbSpeed, uCloudTime * 0.015 * turbSpeed, uWindOffset.y * turbSpeed);

          // 1. Niederfrequente Basis-Form (Perlin-Worley)
          float baseWorley = worley3D(windCoord * 1.85);
          float baseFbm = fbm3D(windCoord * 1.25);
          float baseShape = mix(baseFbm, baseWorley, 0.55);

          // 2. Höhendichtefenster
          float hProfile = getHeightProfile(hNorm);
          float cloudMask = baseShape * hProfile;

          // 3. Schwellenwert über Coverage (verdichtet sich bei 40m Annäherung zu einer dramatischen Gewitterwolkendecke!)
          float riftCovBoost = uRiftFactor * (0.42 + 0.26 * uRiftAwakened) * uRiftCloudDensity * (0.65 + 0.35 * riftFocus);
          float effCoverage = clamp(uCoverage + riftCovBoost, 0.0, 0.96);
          float threshold = 1.0 - effCoverage * 1.15;
          if (cloudMask < threshold) return 0.0;

          // 4. Feine Ausfaserung / Erosion der Ränder
          vec3 highCoord = sampleP * 3.8 + vec3(uWindHighOffset.x, -uCloudTime * 0.03 * turbSpeed, uWindHighOffset.y);
          float detailErosion = worley3D(highCoord) * uErosionStrength;

          float d = clamp((cloudMask - threshold - detailErosion * 0.25) / max(0.05, 1.0 - threshold), 0.0, 1.0);
          float riftDensMult = 1.0 + uRiftFactor * (0.55 + 0.55 * uRiftAwakened) * uRiftCloudDensity * (0.6 + 0.4 * riftFocus);
          return pow(d, 1.35) * uDensity * riftDensMult;
        }

        void main() {
          vec3 dir = normalize(vWorldDir);
          float y = dir.y;

          // Wolken unterhalb des Horizonts sanft ausblenden
          if (y <= 0.005) {
            discard;
          }

          // Horizont-Fading (keine harten Schnittkanten an den Bergen)
          float horizonFade = smoothstep(0.015, 0.18, y);

          // Sonneneinstrahlungs- & Streuungs-Winkel
          vec3 normSunDir = normalize(uSunDir);
          vec3 normMoonDir = normalize(uMoonDir);
          float cosSun = dot(dir, normSunDir);
          float cosMoon = dot(dir, normMoonDir);

          // Dual-Lobe Phasenfunktion: Brillante Vorwärtsstreuung (Silver Lining) + weiche Rückstreuung
          float phaseSun = mix(hgPhase(cosSun, -0.24), hgPhase(cosSun, 0.80), 0.72);
          float phaseMoon = mix(hgPhase(cosMoon, -0.18), hgPhase(cosMoon, 0.74), 0.68);
          float sunRimLobe = pow(max(cosSun, 0.0), 8.0) * 0.65 + pow(max(cosSun, 0.0), 36.0) * 1.15;
          float moonRimLobe = pow(max(cosMoon, 0.0), 10.0) * 0.55 + pow(max(cosMoon, 0.0), 42.0) * 0.95;

          // Grundfarben des Himmelslichts (warmes Gold-Bernstein bei Dämmerung, kühles Silberblau bei Nacht)
          vec3 directSunColor = uSunColor * (1.05 + uSunIntensity * 0.75);
          vec3 ambientDown = mix(uAmbientGroundColor, uAmbientSkyColor, 0.78);
          vec3 sunsetRimColor = mix(uSunColor, vec3(1.0, 0.54, 0.18), uTwilightFactor * 0.88);
          float stormDark = smoothstep(0.68, 0.96, uCoverage) * smoothstep(1.3, 2.5, uDensity);

          // Rissmonolith-Richtungsfokus für Wolkenwirbel & magische Wolkenbeleuchtung
          vec3 normRiftDir = normalize(uRiftDir);
          float cosRift = max(dot(dir, normRiftDir), 0.0);
          float riftFocus = smoothstep(0.25, 0.92, cosRift);
          vec3 riftVioletCol = vec3(0.66, 0.26, 0.98) * uRiftVioletStrength;
          vec3 riftCrimsonCol = vec3(0.98, 0.16, 0.34) * uRiftCrimsonStrength;
          vec3 riftGlowCol = mix(riftVioletCol, riftCrimsonCol, clamp(uRiftAwakened * 0.78, 0.0, 1.0));

          // ====================================================================
          // A) QUALITÄT 1 (LOW): SCHNELLE ANALYTISCHE PROZEDURALE WOLKEN-SCHICHT
          // ====================================================================
          if (uQuality <= 1) {
            vec2 flatUv = dir.xz / (y + 0.14) * 0.65 + uWindOffset * 0.25;
            float lowFbm = fbm3D(vec3(flatUv, uCloudTime * 0.02));
            float lowWorley = worley3D(vec3(flatUv * 1.5, uCloudTime * 0.015));
            float effCovLow = clamp(uCoverage + uRiftFactor * 0.22 * uRiftCloudDensity * riftFocus, 0.0, 0.98);
            float cDensity = clamp((mix(lowFbm, lowWorley, 0.5) - (1.0 - effCovLow * 1.1)) * 2.8, 0.0, 1.0);

            if (cDensity <= 0.01) {
              discard;
            }

            float edgeTrans = 1.0 - smoothstep(0.08, 0.72, cDensity);
            vec3 cColor = mix(ambientDown * 0.88, directSunColor, clamp(0.32 + 0.68 * max(cosSun, 0.0), 0.0, 1.0) * clamp(uSunIntensity, 0.0, 1.2));
            cColor += sunsetRimColor * (sunRimLobe * (0.45 + 0.95 * edgeTrans)) * uTwilightFactor * clamp(uSunIntensity, 0.0, 1.2);
            cColor += uMoonColor * (uMoonIntensity * (0.28 + moonRimLobe * (0.55 + 0.85 * edgeTrans)));
            cColor = mix(cColor, vec3(0.18, 0.22, 0.30) * max(0.38, uSunIntensity * 0.5 + uMoonIntensity * 0.7 + 0.28), stormDark * 0.68);
            if (uRiftFactor > 0.005) {
              vec3 darkRiftBelly = mix(vec3(0.11, 0.04, 0.20), vec3(0.18, 0.03, 0.10), uRiftAwakened);
              cColor = mix(cColor, darkRiftBelly, uRiftFactor * (0.45 + 0.30 * riftFocus));
              cColor += riftGlowCol * (edgeTrans * 0.65 + 0.25) * uRiftFactor * (0.35 + 0.65 * riftFocus);
              cColor += riftGlowCol * uRiftLightning * 1.8 * (0.4 + 0.6 * riftFocus);
            }
            cColor += vec3(0.72, 0.86, 1.0) * uLightningFlash * 2.6;

            float finalAlpha = cDensity * horizonFade * 0.92;
            gl_FragColor = vec4(cColor, finalAlpha);
            #include <tonemapping_fragment>
            #include <colorspace_fragment>
            return;
          }

          // ====================================================================
          // B) QUALITÄT 2–4: ECHTES VOLUMETRISCHES RAYMARCHING
          // ====================================================================
          int steps = clamp(uRaymarchSteps, 8, 32);
          float stepDist = 1.0 / float(steps);

          // Prozedurales Dithering zur Beseitigung von Schicht-Banding (Bayer / Hash)
          float dither = hash12(gl_FragCoord.xy) * stepDist;

          vec3 accumulatedColor = vec3(0.0);
          float transmittance = 1.0;

          // Strahl durchdringt die gekrümmte atmosphärische Sphärenschale
          for (int i = 0; i < 32; i++) {
            if (i >= steps || transmittance <= 0.015) break;

            float t = (float(i) + dither) * stepDist;
            float hNorm = t; // 0 = Wolkenbasis, 1 = Wolkenspitze

            // Sphärische 3D-Position in der Wolkenschale
            vec3 marchPos = dir * (1.2 + t * 0.55);
            marchPos.xz /= (y + 0.16);

            float d = sampleCloudDensity(marchPos * 0.55, hNorm, riftFocus);

            if (d > 0.002) {
              // Optische Tiefe des aktuellen Schritts
              float stepExtinction = d * 1.65 * stepDist;
              float stepTrans = exp(-stepExtinction);

              // 1. Licht-Sampling in Richtung Sonne & Mond (Selbstabschattung / lichtdurchlässige Wolkenränder)
              vec3 lightDir = uSunIntensity >= 0.05 ? normSunDir : normMoonDir;
              vec3 lightMarchPos = marchPos + lightDir * 0.08;
              float shadowDensity = sampleCloudDensity(lightMarchPos * 0.55, clamp(hNorm + 0.08, 0.0, 1.0), riftFocus);
              float lightTrans = exp(-shadowDensity * 2.85);
              float thinEdge = exp(-d * 1.65) * lightTrans;

              // "Powder Sugar" Effekt (Zuckerhut-Mehrfachstreuung an Kanten, nur in Richtung der aktiven Lichtquelle!)
              float activeCos = uSunIntensity >= 0.05 ? cosSun : cosMoon;
              float powderSugar = mix(1.0 - exp(-d * 3.1), 1.0, clamp(activeCos * 0.5 + 0.5, 0.0, 1.0) * 0.45);

              // Direktes Sonnenlicht mit Phasenstreuung & goldenem Wolkenrand (Silver Lining)
              float riftSunAtten = 1.0 - uRiftFactor * (0.35 + 0.25 * uRiftAwakened);
              vec3 sunIllum = directSunColor * (lightTrans * phaseSun * 2.15 + thinEdge * sunRimLobe * 1.35 + 0.10) * uSunIntensity * riftSunAtten;
              vec3 goldenHourIllum = sunsetRimColor * (lightTrans * (1.65 + sunRimLobe * 1.6) + 0.28 * hNorm) * clamp(uSunIntensity, 0.0, 1.2) * riftSunAtten;
              sunIllum = mix(sunIllum, goldenHourIllum, uTwilightFactor * 0.85);

              // 2. Mondbeleuchtung bei Nacht mit silberblauem Wolkenrand (Bild 3 Unten)
              vec3 moonIllum = uMoonColor * (uMoonIntensity * (lightTrans * phaseMoon * 2.1 + thinEdge * moonRimLobe * 1.45 + 0.16 * (0.4 + 0.6 * hNorm)));

              // 3. Diffuses Himmels- & Boden-Ambientelicht (hellt Unterseite auf & färbt sich bei aktivem Rissmonolithen dunkelviolett/karmesin)
              vec3 stormBaseCol = mix(uAmbientGroundColor * 0.58 + vec3(0.04, 0.06, 0.09), uAmbientSkyColor * 0.90, clamp(hNorm * 0.85 + 0.15, 0.0, 1.0));
              vec3 ambientIllum = mix(stormBaseCol, stormBaseCol * vec3(0.68, 0.74, 0.84), stormDark * (1.0 - hNorm * 0.55));
              if (uRiftFactor > 0.005) {
                vec3 riftBellyCol = mix(vec3(0.12, 0.04, 0.22), vec3(0.20, 0.03, 0.11), uRiftAwakened);
                ambientIllum = mix(ambientIllum, riftBellyCol, uRiftFactor * (0.52 + 0.28 * (1.0 - hNorm)));
                ambientIllum += riftGlowCol * (thinEdge * 0.95 + (1.0 - hNorm) * 0.35 * riftFocus) * uRiftFactor * (0.42 + 0.58 * riftFocus);
              }

              // 4. Gewitter- & Riss-Blitzlicht aus dem Inneren der Wolkentürme (dezent & atmosphärisch statt grell überblendend)
              vec3 lightningIllum = vec3(0.68, 0.82, 0.98) * uLightningFlash * 1.35 * (1.0 - lightTrans * 0.45);
              if (uRiftLightning > 0.01) {
                lightningIllum += riftGlowCol * uRiftLightning * 1.30 * (0.35 + 0.65 * riftFocus) * (1.0 - lightTrans * 0.35);
              }

              // Gesamtes gestreutes Licht an diesem Segment
              vec3 totalScatteredLight = (sunIllum + moonIllum + ambientIllum + lightningIllum) * uLightScattering;

              // Akkumulation entlang des Sichtstrahls
              vec3 segmentColor = totalScatteredLight * (1.0 - stepTrans) * powderSugar;
              accumulatedColor += transmittance * segmentColor;
              transmittance *= stepTrans;
            }
          }

          // C) HOCH-ATMOSPHÄRISCHER CIRRUS-SCHLEIER & POLARLICHT-SCHIMMER (bei verbleibender Transmittanz)
          if (transmittance > 0.05 && y > 0.04) {
            vec2 cirrusUv = (dir.xz / (y + 0.12)) * 1.15 + uWindHighOffset * 0.42;
            float cirrusStreak = noise3D(vec3(cirrusUv.x * 2.8, cirrusUv.y * 0.85, uCloudTime * 0.008));
            float cirrusFine = noise3D(vec3(cirrusUv.x * 6.4 - cirrusStreak * 1.2, cirrusUv.y * 2.1, -uCloudTime * 0.012));
            float cirrusMask = smoothstep(0.56, 0.88, cirrusStreak * 0.65 + cirrusFine * 0.35) * uHighCirrusStrength * smoothstep(0.04, 0.25, y);
            if (cirrusMask > 0.005) {
              vec3 cirrusLight = mix(uAmbientSkyColor * 0.95, directSunColor, clamp(uSunIntensity, 0.0, 1.1) * 0.72)
                               + sunsetRimColor * uTwilightFactor * 0.65
                               + uMoonColor * uMoonIntensity * 0.68;
              float cAlpha = cirrusMask * 0.32 * transmittance;
              accumulatedColor += cirrusLight * cAlpha;
              transmittance *= (1.0 - cAlpha * 0.75);
            }
            if (uAuroraIntensity > 0.01 && uSunIntensity < 0.15 && y > 0.10) {
              vec2 aurUv = dir.xz / (y + 0.18);
              float aurWave = sin(aurUv.x * 3.2 + uCloudTime * 0.18 + cos(aurUv.y * 2.4) * 1.6);
              float aurCurtain = smoothstep(0.45, 0.96, 1.0 - abs(aurWave)) * exp(-abs(y - 0.38) * 3.8);
              float aurVertical = 0.55 + 0.45 * sin(aurUv.x * 14.0 - uCloudTime * 0.45);
              vec3 aurCol = mix(vec3(0.12, 0.92, 0.58), vec3(0.48, 0.28, 0.96), clamp((y - 0.18) * 2.2, 0.0, 1.0));
              vec3 aurAdd = aurCol * aurCurtain * aurVertical * uAuroraIntensity * transmittance * 0.55;
              accumulatedColor += aurAdd;
              transmittance *= (1.0 - clamp(aurCurtain * uAuroraIntensity * 0.28, 0.0, 0.45));
            }
          }

          float cloudAlpha = clamp((1.0 - transmittance) * horizonFade, 0.0, 1.0);

          if (cloudAlpha <= 0.005) {
            discard;
          }

          gl_FragColor = vec4(accumulatedColor, cloudAlpha);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }
      `,
    });

    this.cloudDomeMesh = new THREE.Mesh(domeGeo, this.cloudMaterial);
    this.cloudDomeMesh.frustumCulled = false;
    this.cloudDomeMesh.renderOrder = -930; // Vor der Himmelskuppel (-1000) und vor dem Mond (-940), damit Wolken den Mond überlagern können
    this.cloudDomeMesh.scale.setScalar(420);
    this.scene.add(this.cloudDomeMesh);
  }

  getRaymarchSteps() {
    switch (this.quality) {
      case 1:
        return 4; // Low (Analytisch)
      case 2:
        return 10; // Medium
      case 3:
        return 18; // High
      case 4:
        return 28; // Ultra
      default:
        return 12;
    }
  }

  setQuality(q) {
    this.quality = Math.max(1, Math.min(4, Math.floor(q)));
    if (this.cloudUniforms) {
      this.cloudUniforms.uQuality.value = this.quality;
      this.cloudUniforms.uRaymarchSteps.value = this.getRaymarchSteps();
    }
  }

  setCloudType(typeKey) {
    this.cloudType = typeKey;
    if (typeKey !== 'auto' && CLOUD_TYPES[typeKey]) {
      this.applyPreset(CLOUD_TYPES[typeKey]);
    }
  }

  applyPreset(preset) {
    this.activePresetKey = preset.id;
    this.cloudHeight = preset.baseHeight;
    this.thickness = preset.thickness;
    this.density = preset.density;
    this.coverage = preset.coverage;

    if (this.cloudUniforms) {
      this.cloudUniforms.uCoverage.value = this.coverage;
      this.cloudUniforms.uDensity.value = this.density;
      this.cloudUniforms.uCloudHeight.value = this.cloudHeight;
      this.cloudUniforms.uThickness.value = this.thickness;
      this.cloudUniforms.uAnvilExpansion.value = preset.anvil || 0.0;
      this.cloudUniforms.uErosionStrength.value = preset.erosion || 0.35;
    }
  }

  update(celestial, camera, dt = 0, weather = 'sunny', season = 'summer') {
    if (!this.cloudDomeMesh || !this.cloudUniforms) return;

    this.cloudDomeMesh.visible = this.enabled;
    if (!this.enabled) return;

    // Kuppel folgt stets der Kamera und skaliert dynamisch mit der Sichtweite
    if (camera) {
      this.cloudDomeMesh.position.copy(camera.position);
      const r = Math.max(80, (camera.far || 750) * 0.88);
      if (Math.abs(this.cloudDomeMesh.scale.x - r) > 1.0) {
        this.cloudDomeMesh.scale.setScalar(r);
      }
    }

    // 1. Automatische Wetter- & Jahreszeiten-Typzuordnung (falls cloudType == 'auto')
    this.updateWeatherAndSeason(weather, season, dt);

    // 2. Wind-Advektion & kontinuierliche prozedurale Wolkenmorphung
    const windSpeedMps = (this.windSpeed * 1000.0) / 3600.0;
    const driftStep = (windSpeedMps * dt * 0.00035);
    const wx = Math.cos(this.windDirection) * driftStep;
    const wz = Math.sin(this.windDirection) * driftStep;

    this.windOffset.add(this._windStep.set(wx, wz));
    // Höhere Wolkenschichten driften mit leichter Scherung
    this.windHighOffset.add(this._windStep.set(wx * 1.45 + wz * 0.2, wz * 1.35 - wx * 0.2));
    this.cloudTime += dt;

    // 3. Blitz-Effekt bei Gewitter (wird zentral & synchron über OpenWorld3D gesteuert)
    if (!THUNDER_WEATHER.has(weather) && this.lightningFlash > 0.0) {
      this.lightningFlash = Math.max(0.0, this.lightningFlash - dt * 5.0);
    }

    // 4. Uniforms für Shader aktualisieren
    const u = this.cloudUniforms;
    if (celestial) {
      u.uSunDir.value.copy(celestial.sunDirection);
      u.uMoonDir.value.copy(celestial.moonDirection);
      u.uSunColor.value.copy(celestial.sunColor);
      u.uMoonColor.value.copy(celestial.moonColor);
      u.uAmbientSkyColor.value.copy(celestial.ambientSkyColor);
      u.uAmbientGroundColor.value.copy(celestial.ambientGroundColor);
      u.uSunIntensity.value = celestial.sunIntensity;
      u.uMoonIntensity.value = celestial.moonIntensity;
      u.uTwilightFactor.value = celestial.twilightFactor;
    }

    u.uCoverage.value = this.coverage;
    u.uDensity.value = this.density;
    u.uCloudHeight.value = this.cloudHeight;
    u.uThickness.value = this.thickness;
    u.uWindOffset.value.copy(this.windOffset);
    u.uWindHighOffset.value.copy(this.windHighOffset);
    u.uCloudTime.value = this.cloudTime;
    u.uLightningFlash.value = this.lightningFlash;
    u.uLightScattering.value = this.lightScattering;
    if (u.uHighCirrusStrength) {
      const targetCirrus = this.activePresetKey === 'cirrus' ? 0.85 : (CLEAR_WEATHER.has(weather) ? 0.38 : 0.15);
      u.uHighCirrusStrength.value += (targetCirrus - u.uHighCirrusStrength.value) * Math.min(1.0, (dt || 0.016) * 1.5);
    }
    if (u.uAuroraIntensity) {
      const isColdNight = celestial && !celestial.isDay && (season === 'winter' || this.engine?.currentMapId === 'eisland') && AURORA_WEATHER.has(weather);
      const targetAurora = isColdNight ? 0.78 : 0.0;
      u.uAuroraIntensity.value += (targetAurora - u.uAuroraIntensity.value) * Math.min(1.0, (dt || 0.016) * 0.8);
    }
  }

  updateWeatherAndSeason(weather, season, dt) {
    if (this.cloudType !== 'auto') {
      return; // Benutzer hat einen festen Wolkentyp gewählt
    }

    let targetPreset = CLOUD_TYPES.cumulus;
    let targetCoverage = 0.45;
    let targetDensity = 1.15;

    switch (weather) {
      case 'sunny':
        targetPreset = CLOUD_TYPES.cumulus;
        targetCoverage = 0.24;
        targetDensity = 0.95;
        break;
      case 'partly_cloudy':
        targetPreset = CLOUD_TYPES.altocumulus;
        targetCoverage = 0.44;
        targetDensity = 1.50;
        break;
      case 'cloudy':
        targetPreset = CLOUD_TYPES.stratus;
        targetCoverage = 0.82;
        targetDensity = 1.35;
        break;
      case 'light_rain':
        targetPreset = CLOUD_TYPES.stratus;
        targetCoverage = 0.88;
        targetDensity = 1.65;
        break;
      case 'rain':
      case 'heavy_rain':
        targetPreset = CLOUD_TYPES.stratus;
        targetCoverage = 0.94;
        targetDensity = 2.10;
        break;
      case 'thunderstorm':
      case 'severe_thunderstorm':
        targetPreset = CLOUD_TYPES.cumulonimbus;
        targetCoverage = 0.98;
        targetDensity = 2.75;
        break;
      case 'fog':
        targetPreset = CLOUD_TYPES.stratus;
        targetCoverage = 0.90;
        targetDensity = 1.40;
        break;
      case 'light_snow':
      case 'snow':
      case 'heavy_snow':
      case 'blizzard':
        targetPreset = CLOUD_TYPES.stratus;
        targetCoverage = 0.89;
        targetDensity = 1.55;
        break;
      default:
        targetPreset = CLOUD_TYPES.cumulus;
        targetCoverage = 0.38;
        targetDensity = 1.0;
        break;
    }

    // Jahreszeiten-Einfluss
    if (season === 'winter') {
      targetCoverage = Math.min(1.0, targetCoverage * 1.18);
      targetDensity *= 1.1;
    } else if (season === 'spring') {
      targetCoverage = Math.min(1.0, targetCoverage * 1.05);
    } else if (season === 'autumn') {
      targetCoverage = Math.min(1.0, targetCoverage * 1.12);
    }

    // Weiche zeitliche Interpolation (respektiert manuelle F7-Schieberegler, falls vom Nutzer gesetzt)
    const blendRate = Math.min(1.0, Math.max(0, dt) * 0.45);
    if (!this._manualCoverageSet) {
      this.coverage += (targetCoverage - this.coverage) * blendRate;
    }
    if (!this._manualDensitySet) {
      this.density += (targetDensity - this.density) * blendRate;
    }
    this.cloudHeight += (targetPreset.baseHeight - this.cloudHeight) * blendRate;
    this.thickness += (targetPreset.thickness - this.thickness) * blendRate;

    if (this.cloudUniforms) {
      this.cloudUniforms.uAnvilExpansion.value += ((targetPreset.anvil || 0.0) - this.cloudUniforms.uAnvilExpansion.value) * blendRate;
      this.cloudUniforms.uErosionStrength.value += ((targetPreset.erosion || 0.35) - this.cloudUniforms.uErosionStrength.value) * blendRate;
    }
    this.activePresetKey = targetPreset.id;
  }

  _cpuFract(x) {
    return x - Math.floor(x);
  }

  _cpuHash13(px, py, pz) {
    let x = this._cpuFract(px * 0.1031);
    let y = this._cpuFract(py * 0.1031);
    let z = this._cpuFract(pz * 0.1031);
    const d = x * (z + 31.32) + y * (y + 31.32) + z * (x + 31.32);
    x += d;
    y += d;
    z += d;
    return this._cpuFract((x + y) * z);
  }

  _cpuNoise3D(px, py, pz) {
    const ix = Math.floor(px), iy = Math.floor(py), iz = Math.floor(pz);
    let fx = px - ix, fy = py - iy, fz = pz - iz;
    fx = fx * fx * (3.0 - 2.0 * fx);
    fy = fy * fy * (3.0 - 2.0 * fy);
    fz = fz * fz * (3.0 - 2.0 * fz);

    const n000 = this._cpuHash13(ix, iy, iz);
    const n100 = this._cpuHash13(ix + 1, iy, iz);
    const n010 = this._cpuHash13(ix, iy + 1, iz);
    const n110 = this._cpuHash13(ix + 1, iy + 1, iz);
    const n001 = this._cpuHash13(ix, iy, iz + 1);
    const n101 = this._cpuHash13(ix + 1, iy, iz + 1);
    const n011 = this._cpuHash13(ix, iy + 1, iz + 1);
    const n111 = this._cpuHash13(ix + 1, iy + 1, iz + 1);

    const nx00 = n000 + (n100 - n000) * fx;
    const nx10 = n010 + (n110 - n010) * fx;
    const nx01 = n001 + (n101 - n001) * fx;
    const nx11 = n011 + (n111 - n011) * fx;
    const nxy0 = nx00 + (nx10 - nx00) * fy;
    const nxy1 = nx01 + (nx11 - nx01) * fy;
    return nxy0 + (nxy1 - nxy0) * fz;
  }

  _cpuFbm3D(px, py, pz) {
    let v = 0.0;
    let amp = 0.52;
    let x = px, y = py, z = pz;
    for (let i = 0; i < 4; i++) {
      v += amp * this._cpuNoise3D(x, y, z);
      x = x * 2.08 + 1.2;
      y = y * 2.08 + 3.4;
      z = z * 2.08 + 5.6;
      amp *= 0.48;
    }
    return v;
  }

  _cpuWorley3D(px, py, pz) {
    const ix = Math.floor(px), iy = Math.floor(py), iz = Math.floor(pz);
    const fx = px - ix, fy = py - iy, fz = pz - iz;
    let minDist = 1.0;
    for (let z = -1; z <= 1; z++) {
      for (let y = -1; y <= 1; y++) {
        for (let x = -1; x <= 1; x++) {
          const cx = ix + x, cy = iy + y, cz = iz + z;
          const ptx = x + this._cpuHash13(cx + 1.2, cy + 3.4, cz + 5.6) * 0.75 + 0.125 - fx;
          const pty = y + this._cpuHash13(cx + 7.8, cy + 9.1, cz + 2.3) * 0.75 + 0.125 - fy;
          const ptz = z + this._cpuHash13(cx + 4.5, cy + 6.7, cz + 8.9) * 0.75 + 0.125 - fz;
          const d = Math.hypot(ptx, pty, ptz);
          if (d < minDist) minDist = d;
        }
      }
    }
    return 1.0 - minDist;
  }

  // Ermittelt die exakte 3D-Wolkenverdeckung in Richtung der Sonne (synchron zum GLSL-Shader für Sunbeams / God-Rays)
  getSunOcclusion(sunDir) {
    if (!this.enabled || this.coverage <= 0.02 || !sunDir) return 0.0;
    if (sunDir.y <= -0.055) return 1.0;

    const safeY = Math.max(0.02, sunDir.y);
    const tMid = 0.38;
    const marchScale = (1.2 + tMid * 0.55) * 0.55;
    const sx = (sunDir.x * marchScale) / (safeY + 0.16) + this.windOffset.x;
    const sy = sunDir.y * marchScale + this.cloudTime * 0.015;
    const sz = (sunDir.z * marchScale) / (safeY + 0.16) + this.windOffset.y;

    const baseWorley = this._cpuWorley3D(sx * 1.85, sy * 1.85, sz * 1.85);
    const baseFbm = this._cpuFbm3D(sx * 1.25, sy * 1.25, sz * 1.25);
    const baseShape = baseFbm * 0.45 + baseWorley * 0.55;

    const threshold = 1.0 - Math.min(0.96, this.coverage) * 1.15;
    if (baseShape < threshold) return 0.0;
    const rawD = Math.min(1.0, Math.max(0.0, (baseShape - threshold) / Math.max(0.05, 1.0 - threshold)));
    return Math.min(0.95, Math.pow(rawD, 1.25) * Math.min(1.6, this.density * 0.85));
  }

  // Liefert die Wolkenschatten-Parameter für Terrain & Welt-Objekte
  getCloudShadowParameters() {
    return {
      enabled: this.enabled && this.shadowStrength > 0.01,
      strength: this.shadowStrength,
      coverage: this.coverage,
      windOffset: this.windOffset,
    };
  }

  dispose() {
    if (this.cloudDomeMesh) {
      this.scene.remove(this.cloudDomeMesh);
      if (this.cloudDomeMesh.geometry) this.cloudDomeMesh.geometry.dispose();
      if (this.cloudMaterial) this.cloudMaterial.dispose();
      this.cloudDomeMesh = null;
    }
  }
}
