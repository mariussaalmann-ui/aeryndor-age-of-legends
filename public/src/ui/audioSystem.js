// ============================================================================
// AERYNDOR — PROZEDURALE & SAMPLE-BASIERTE 3D WEBAUDIO ENGINE (audioSystem.js)
// Inklusive dedizierter 2-Deck HTML5-BGM-Engine (unterbrechungsfrei, komplett
// entkoppelt vom SFX-Compressor) mit automatischem Map 1 <-> Map 2 Crossfade!
// ============================================================================

export const BGM_TRACKS = {
  login: {
    id: 'login',
    title: 'Legenden von Aeryndor (Login)',
    url: './assets/bgm/login.mp3',
  },
  select: {
    id: 'select',
    title: 'Runenterrasse (Charakterwahl & Erstellung)',
    url: './assets/bgm/select.mp3',
  },
  kingdom_one: {
    id: 'kingdom_one',
    title: 'Kingdom One (Map 1 • Nordreich)',
    url: './assets/bgm/kingdom_one.mp3',
  },
  kingdom_two: {
    id: 'kingdom_two',
    title: 'Kingdom Two (Map 2 • Südreich)',
    url: './assets/bgm/kingdom_two.mp3',
  },
  world: {
    id: 'world',
    title: 'Weiten von Aeryndor (Weltgebiete)',
    url: './assets/bgm/world.mp3',
  },
  dungeon: {
    id: 'dungeon',
    title: 'Schatten der Tiefe (Dungeon)',
    url: './assets/bgm/dungeon.mp3',
  },
};

const DUNGEON_MAP_IDS = new Set([
  'spinnendungeon',
  'spinnendungeon_2',
  'daimao_turm',
  'drachenkammer',
  'azrael_katakomben',
  'nemere_warte',
  'razador_festung',
]);

export class AudioSystem {
  constructor() {
    this.ctx = null;
    this.initialized = false;
    this.muted = false;
    this.bgmEnabled = true;
    this.bgmMode = 'auto'; // 'auto' | 'kingdom_one' | 'kingdom_two' | 'world' | 'dungeon' | 'login' | 'select'
    this.muteInBackground = false;
    this._windowBlurred = false;

    this.volumes = {
      master: 0.85,
      music: 0.65,
      sfx: 0.90,
      ambient: 0.80,
      ui: 0.85,
    };
    this.profile = 'balanced'; // 'balanced' | 'bass' | 'crisp' | 'cinematic' | 'night' | 'clear'
    this.uiClickStyle = 'classic'; // 'classic' | 'modern'

    this.nodes = {};
    this._stepToggle = 0;

    // Dedizierte BGM-Engine (zwei unabhängige HTML5 Audio-Decks für weiches Crossfading,
    // komplett getrennt vom WebAudio-SFX-Compressor -> wird NIEMALS durch Kampf-/UI-Sounds geduckt oder unterbrochen!)
    this._bgmContext = 'login'; // 'login' | 'select' | 'create' | 'world'
    this._worldMapId = 'morgenwacht';
    this._worldSection = 'map1'; // 'map1' | 'map2'
    this._worldInDungeon = false;
    this._currentBgmId = null;
    this._activeDeck = null;
    this._fadingOutDecks = new Set();
    this._bgmFadeTimer = null;

    this._setupLifecycleListeners();
  }

  _setupLifecycleListeners() {
    if (typeof window === 'undefined') return;
    const unlockBgm = () => {
      this.resume();
      this._ensureActiveBgmPlaying();
    };
    window.addEventListener('pointerdown', unlockBgm, { passive: true });
    window.addEventListener('keydown', unlockBgm, { passive: true });

    window.addEventListener('blur', () => {
      this._windowBlurred = true;
      if (this.muteInBackground) {
        this._syncBgmVolumeImmediate();
        this._syncWebAudioGains();
      }
    });
    window.addEventListener('focus', () => {
      this._windowBlurred = false;
      this._syncBgmVolumeImmediate();
      this._syncWebAudioGains();
      this._ensureActiveBgmPlaying();
    });
    document.addEventListener('visibilitychange', () => {
      this._windowBlurred = document.hidden;
      if (this.muteInBackground) {
        this._syncBgmVolumeImmediate();
        this._syncWebAudioGains();
      }
      // Beim Zurückkehren in den Tab: vom Browser suspendierten AudioContext & BGM-Deck wieder anwerfen
      if (!document.hidden) {
        if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume().catch(() => {});
        this._ensureActiveBgmPlaying();
      }
    });
  }

  init() {
    if (this.initialized) return;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;

    this.ctx = new AudioCtx();

    // Master & Equalizer-Kette (für SFX, Ambient & UI; BGM läuft über eigenen unkomprimierten Pfad!)
    this.nodes.master = this.ctx.createGain();
    this.nodes.bassFilter = this.ctx.createBiquadFilter();
    this.nodes.bassFilter.type = 'lowshelf';
    this.nodes.bassFilter.frequency.value = 160;

    this.nodes.trebleFilter = this.ctx.createBiquadFilter();
    this.nodes.trebleFilter.type = 'highshelf';
    this.nodes.trebleFilter.frequency.value = 3600;

    this.nodes.compressor = this.ctx.createDynamicsCompressor();
    this.nodes.compressor.threshold.value = -18;
    this.nodes.compressor.ratio.value = 4;

    // Sub-Busse
    this.nodes.music = this.ctx.createGain();
    this.nodes.sfx = this.ctx.createGain();
    this.nodes.ambient = this.ctx.createGain();
    this.nodes.ui = this.ctx.createGain();

    // WICHTIG: music-Node umgeht den SFX-Compressor direkt zum Master, damit Musik niemals durch SFX geduckt wird!
    this.nodes.music.connect(this.nodes.master);
    this.nodes.sfx.connect(this.nodes.bassFilter);
    this.nodes.ambient.connect(this.nodes.bassFilter);
    this.nodes.ui.connect(this.nodes.bassFilter);

    this.nodes.bassFilter.connect(this.nodes.trebleFilter);
    this.nodes.trebleFilter.connect(this.nodes.compressor);
    this.nodes.compressor.connect(this.nodes.master);
    this.nodes.master.connect(this.ctx.destination);

    this._initAmbientLoops();
    this.initialized = true;
    this.applySettings(this.volumes, this.profile);
    this._startBgmCrossfadeLoop();
  }

  resume() {
    if (!this.initialized) this.init();
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }
  }

  getEffectiveBgmVolume() {
    if (this.muted || !this.bgmEnabled) return 0;
    if (this.muteInBackground && this._windowBlurred) return 0;
    return Math.max(0, Math.min(1, this.volumes.master * this.volumes.music));
  }

  getCurrentBgmInfo() {
    const id = this._currentBgmId || this._resolveDesiredBgmId();
    return BGM_TRACKS[id] || BGM_TRACKS.kingdom_one;
  }

  _resolveDesiredBgmId() {
    if (this.bgmMode && this.bgmMode !== 'auto' && BGM_TRACKS[this.bgmMode]) {
      return this.bgmMode;
    }
    if (this._bgmContext === 'login') return 'login';
    if (this._bgmContext === 'select' || this._bgmContext === 'create') return 'select';
    // Ingame ('world')
    if (this._worldInDungeon || DUNGEON_MAP_IDS.has(this._worldMapId)) {
      return 'dungeon';
    }
    if (this._worldMapId === 'morgenwacht' || this._worldMapId === 'map_1' || this._worldMapId === 'map_2') {
      if (this._worldMapId === 'map_2') return 'kingdom_two';
      if (this._worldMapId === 'map_1') return 'kingdom_one';
      return this._worldSection === 'map2' ? 'kingdom_two' : 'kingdom_one';
    }
    return 'world';
  }

  setBgmContext(context = 'login') {
    this._bgmContext = context;
    this._updateTargetBgmTrack();
  }

  updateWorldBgmState({ mapId = 'morgenwacht', playerX = 0, playerZ = 0, riverZ = 0, inDungeon = false, forceWorld = false } = {}) {
    if (forceWorld) {
      this._bgmContext = 'world';
    }
    if (mapId) this._worldMapId = String(mapId);
    this._worldInDungeon = Boolean(inDungeon) || DUNGEON_MAP_IDS.has(this._worldMapId);

    // Zwischen Map 1 (nördlich des Silberstroms, z <= riverZ) und Map 2 (südlich des Silberstroms, z > riverZ)
    // mit sanfter 5m-Hysterese an der Flussmitte umschalten:
    // Map 1 -> kingdom_one.mp3 | Map 2 -> kingdom_two.mp3 (und umgekehrt!)
    if (this._worldMapId === 'morgenwacht') {
      const borderZ = Number.isFinite(riverZ) ? riverZ : 0.0;
      if (this._worldSection === 'map1' && playerZ > borderZ + 5.0) {
        this._worldSection = 'map2';
      } else if (this._worldSection === 'map2' && playerZ < borderZ - 5.0) {
        this._worldSection = 'map1';
      } else if (!this._currentBgmId || forceWorld) {
        this._worldSection = playerZ > borderZ ? 'map2' : 'map1';
      }
    }
    if (this._bgmContext === 'world') {
      this._updateTargetBgmTrack();
    }
  }

  _updateTargetBgmTrack() {
    const desiredId = this._resolveDesiredBgmId();
    if (!desiredId || !BGM_TRACKS[desiredId]) return;

    if (!this.bgmEnabled) {
      this._currentBgmId = desiredId;
      this._syncBgmVolumeImmediate();
      return;
    }

    if (this._currentBgmId === desiredId && this._activeDeck) {
      this._ensureActiveBgmPlaying();
      return;
    }

    this._currentBgmId = desiredId;
    const track = BGM_TRACKS[desiredId];

    // Vorheriges Deck sanft ausblenden
    if (this._activeDeck) {
      this._fadingOutDecks.add(this._activeDeck);
      this._activeDeck = null;
    }

    // Falls dasselbe Lied noch im Fade-Out war, reaktiviere es nahtlos
    for (const oldDeck of this._fadingOutDecks) {
      if (oldDeck._trackId === desiredId) {
        this._fadingOutDecks.delete(oldDeck);
        this._activeDeck = oldDeck;
        this._ensureActiveBgmPlaying();
        this._startBgmCrossfadeLoop();
        return;
      }
    }

    if (typeof Audio === 'undefined') return;
    const audio = new Audio(track.url);
    audio.loop = true;
    audio.preload = 'auto';
    audio._trackId = desiredId;
    audio._fadeWeight = 0.0;
    audio.volume = 0.0;
    // Fehlende/defekte Track-Datei: einmalig warnen statt endlos play() zu versuchen
    audio.addEventListener(
      'error',
      () => {
        if (!audio.getAttribute('src')) return; // absichtlich entladenes Deck
        console.warn(`[Audio] BGM-Track konnte nicht geladen werden: ${track.url}`);
        audio._loadFailed = true;
      },
      { once: true }
    );
    this._activeDeck = audio;
    this._ensureActiveBgmPlaying();
    this._startBgmCrossfadeLoop();
  }

  _ensureActiveBgmPlaying() {
    if (!this._activeDeck || !this.bgmEnabled || this._activeDeck._loadFailed) return;
    if (this._activeDeck.paused) {
      this._activeDeck.play().catch(() => {});
    }
  }

  _syncBgmVolumeImmediate() {
    const targetVol = this.getEffectiveBgmVolume();
    if (this._activeDeck) {
      const w = Number.isFinite(this._activeDeck._fadeWeight) ? this._activeDeck._fadeWeight : 1.0;
      this._activeDeck.volume = Math.max(0, Math.min(1, targetVol * w * this._duckFactor()));
      if (!this.bgmEnabled && !this._activeDeck.paused) {
        this._activeDeck.pause();
      } else if (this.bgmEnabled && this._activeDeck.paused) {
        this._activeDeck.play().catch(() => {});
      }
    }
    for (const d of this._fadingOutDecks) {
      const w = Number.isFinite(d._fadeWeight) ? d._fadeWeight : 0.0;
      d.volume = Math.max(0, Math.min(1, targetVol * w));
    }
  }

  _startBgmCrossfadeLoop() {
    if (this._bgmFadeTimer) return;
    this._bgmFadeTimer = setInterval(() => {
      const targetVol = this.getEffectiveBgmVolume();
      const step = 0.045; // ~1.1s sanftes Crossfade bei 50ms Tick
      let anyFading = false;

      if (this._activeDeck) {
        if (this.bgmEnabled && this._activeDeck.paused && !this._activeDeck._loadFailed) {
          this._activeDeck.play().catch(() => {});
        }
        const curW = Number.isFinite(this._activeDeck._fadeWeight) ? this._activeDeck._fadeWeight : 0.0;
        if (curW < 1.0) {
          this._activeDeck._fadeWeight = Math.min(1.0, curW + step);
          anyFading = true;
        }
        this._activeDeck.volume = Math.max(0, Math.min(1, targetVol * this._activeDeck._fadeWeight * this._duckFactor()));
        if (this._duckUntil && performance.now() < this._duckUntil + 600) anyFading = true; // Loop für Duck-Rückblende aktiv halten
      }

      for (const oldDeck of Array.from(this._fadingOutDecks)) {
        const curW = Number.isFinite(oldDeck._fadeWeight) ? oldDeck._fadeWeight : 0.0;
        const nextW = Math.max(0.0, curW - step);
        oldDeck._fadeWeight = nextW;
        oldDeck.volume = Math.max(0, Math.min(1, targetVol * nextW));
        if (nextW <= 0.005) {
          try {
            oldDeck.pause();
            // removeAttribute + load() gibt den Puffer frei, ohne (wie src = '') die Seiten-URL anzufragen
            oldDeck.removeAttribute('src');
            oldDeck.load();
          } catch (_) {}
          this._fadingOutDecks.delete(oldDeck);
        } else {
          anyFading = true;
        }
      }

      if (!anyFading && this._fadingOutDecks.size === 0) {
        clearInterval(this._bgmFadeTimer);
        this._bgmFadeTimer = null;
      }
    }, 50);
  }

  // --- Komfort-API: Stummschalten & Musik-Ducking ---
  setMuted(muted) {
    this.muted = Boolean(muted);
    this._syncBgmVolumeImmediate();
    this._syncWebAudioGains();
    return this.muted;
  }

  toggleMute() {
    return this.setMuted(!this.muted);
  }

  /**
   * Senkt die Hintergrundmusik kurzzeitig ab (z. B. für Dialoge, Boss-Ansagen, Level-Up-Fanfaren)
   * und blendet sie danach weich wieder ein.
   * @param {number} amount Absenkung 0..1 (0.5 = halbe Lautstärke)
   * @param {number} durationMs Haltezeit in ms
   */
  duckMusic(amount = 0.5, durationMs = 1500) {
    this._duckAmount = Math.max(0, Math.min(1, Number(amount) || 0));
    this._duckUntil = performance.now() + Math.max(0, Number(durationMs) || 0);
    this._syncBgmVolumeImmediate();
    this._startBgmCrossfadeLoop();
  }

  _duckFactor() {
    if (!this._duckUntil) return 1;
    const left = this._duckUntil - performance.now();
    const full = 1 - (this._duckAmount || 0);
    if (left > 0) return full;
    const release = Math.min(1, -left / 600); // 600 ms weiches Wiedereinblenden
    if (release >= 1) {
      this._duckUntil = 0;
      return 1;
    }
    return full + (1 - full) * release;
  }

  _syncWebAudioGains() {
    if (!this.initialized || !this.ctx || !this.nodes.master) return;
    const now = this.ctx.currentTime;
    const isBgMuted = this.muteInBackground && this._windowBlurred;
    const m = this.muted || isBgMuted ? 0 : this.volumes.master;
    this.nodes.master.gain.setTargetAtTime(m, now, 0.05);
    this.nodes.music.gain.setTargetAtTime(this.volumes.music, now, 0.05);
    this.nodes.sfx.gain.setTargetAtTime(this.volumes.sfx, now, 0.05);
    this.nodes.ambient.gain.setTargetAtTime(this.volumes.ambient, now, 0.05);
    this.nodes.ui.gain.setTargetAtTime(this.volumes.ui, now, 0.05);
  }

  applySettings(cfg = {}, profile = this.profile) {
    const normVol = (v) => {
      const n = Number(v);
      if (!Number.isFinite(n)) return 0.8;
      // Werte > 1 werden als Prozent (0..100) interpretiert; Ergebnis immer auf 0..1 begrenzt
      return Math.max(0, Math.min(1, n > 1.0 ? n / 100.0 : n));
    };
    if (cfg.masterVol !== undefined || cfg.masterVolume !== undefined) {
      this.volumes.master = normVol(cfg.masterVol ?? cfg.masterVolume);
    }
    if (cfg.musicVol !== undefined || cfg.musicVolume !== undefined) {
      this.volumes.music = normVol(cfg.musicVol ?? cfg.musicVolume);
    }
    if (cfg.sfxVol !== undefined || cfg.sfxVolume !== undefined) {
      this.volumes.sfx = normVol(cfg.sfxVol ?? cfg.sfxVolume);
    }
    if (cfg.ambientVol !== undefined || cfg.ambientVolume !== undefined) {
      this.volumes.ambient = normVol(cfg.ambientVol ?? cfg.ambientVolume);
    }
    if (cfg.uiVol !== undefined || cfg.uiVolume !== undefined) {
      this.volumes.ui = normVol(cfg.uiVol ?? cfg.uiVolume);
    }
    if (cfg.muted !== undefined) {
      this.muted = Boolean(cfg.muted);
    }
    if (cfg.bgmEnabled !== undefined) {
      this.bgmEnabled = Boolean(cfg.bgmEnabled);
    }
    if (cfg.bgmMode !== undefined) {
      this.bgmMode = String(cfg.bgmMode || 'auto');
    }
    if (cfg.muteInBackground !== undefined) {
      this.muteInBackground = Boolean(cfg.muteInBackground);
    }
    if (cfg.uiClickStyle) {
      this.uiClickStyle = cfg.uiClickStyle;
    }
    if (cfg.soundProfile || cfg.audioProfile) {
      this.profile = cfg.soundProfile || cfg.audioProfile;
    } else if (profile) {
      this.profile = profile;
    }

    this._updateTargetBgmTrack();
    this._syncBgmVolumeImmediate();

    if (!this.initialized || !this.ctx) return;
    this._syncWebAudioGains();
    const now = this.ctx.currentTime;

    if (this.profile === 'bass' || this.profile === 'cinematic') {
      this.nodes.bassFilter.gain.setTargetAtTime(5.5, now, 0.1);
      this.nodes.trebleFilter.gain.setTargetAtTime(2.0, now, 0.1);
    } else if (this.profile === 'night') {
      this.nodes.bassFilter.gain.setTargetAtTime(-4.5, now, 0.1);
      this.nodes.trebleFilter.gain.setTargetAtTime(-2.0, now, 0.1);
    } else if (this.profile === 'crisp' || this.profile === 'clear') {
      this.nodes.bassFilter.gain.setTargetAtTime(-1.5, now, 0.1);
      this.nodes.trebleFilter.gain.setTargetAtTime(4.8, now, 0.1);
    } else {
      this.nodes.bassFilter.gain.setTargetAtTime(0, now, 0.1);
      this.nodes.trebleFilter.gain.setTargetAtTime(0, now, 0.1);
    }
  }

  _createNoiseBuffer(seconds = 2.5) {
    const rate = this.ctx.sampleRate;
    const buf = this.ctx.createBuffer(1, Math.floor(rate * seconds), rate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < data.length; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    return buf;
  }

  _initAmbientLoops() {
    this._noiseBuf = this._createNoiseBuffer(3.0);

    const makeLoop = (type, freq, q = 1.0) => {
      const src = this.ctx.createBufferSource();
      src.buffer = this._noiseBuf;
      src.loop = true;
      const filter = this.ctx.createBiquadFilter();
      filter.type = type;
      filter.frequency.value = freq;
      filter.Q.value = q;
      const gain = this.ctx.createGain();
      gain.gain.value = 0.0001;
      src.connect(filter);
      filter.connect(gain);
      gain.connect(this.nodes.ambient);
      src.start();
      return { src, filter, gain };
    };

    // 1. Silberstrom Flussplätschern
    this.riverLoop = makeLoop('bandpass', 620, 1.4);
    // 2. Bakra Meeresrauschen
    this.seaLoop = makeLoop('lowpass', 340, 0.8);
    // 3. Höhenwind & Regen
    this.windLoop = makeLoop('bandpass', 420, 2.2);
  }

  updateSpatialAmbient({
    playerX = 0,
    playerZ = 0,
    riverZ = 0,
    coastZ = 1068,
    wind = 0.3,
    rain = 0,
    timeSec = 0,
    mapId = 'morgenwacht',
    inDungeon = false,
  }) {
    // Aktualisiere den BGM-Status (inkl. automatischem Wechsel zwischen Map 1 kingdom_one und Map 2 kingdom_two!)
    this.updateWorldBgmState({ mapId, playerX, playerZ, riverZ, inDungeon });

    if (!this.initialized || !this.ctx || !this.riverLoop) return;
    const now = this.ctx.currentTime;

    const distRiver = Math.abs(playerZ - riverZ);
    const riverGain = Math.max(0, 1 - distRiver / 95) * 0.16;

    const distSea = Math.abs(coastZ - playerZ);
    const seaWave = 0.65 + 0.35 * Math.sin(timeSec * 0.85);
    const seaGain = Math.max(0, 1 - distSea / 160) * 0.22 * seaWave;

    const windGain = Math.min(0.20, wind * 0.07 + rain * 0.13);

    this.riverLoop.gain.gain.setTargetAtTime(riverGain, now, 0.25);
    this.seaLoop.gain.gain.setTargetAtTime(seaGain, now, 0.35);
    this.seaLoop.filter.frequency.setTargetAtTime(260 + seaWave * 180, now, 0.35);
    this.windLoop.gain.gain.setTargetAtTime(windGain, now, 0.25);
  }

  // --- UI Kristallklick ---
  playUiClick(pitch = 1.0) {
    this.resume();
    if (!this.ctx || this.muted) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    const isModern = this.uiClickStyle === 'modern';
    osc.type = isModern ? 'sine' : 'triangle';
    const baseF = isModern ? 1320 : 940;
    osc.frequency.setValueAtTime(baseF * pitch, now);
    osc.frequency.exponentialRampToValueAtTime(baseF * 1.48 * pitch, now + 0.045);
    gain.gain.setValueAtTime(0.13, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.055);
    osc.connect(gain);
    gain.connect(this.nodes.ui);
    osc.start(now);
    osc.stop(now + 0.06);
  }

  // --- Nachrichten-Hinweis (zweitöniges Glöckchen, gedrosselt) ---
  playNotify() {
    this.resume();
    if (!this.ctx || this.muted || !this.nodes?.ui) return;
    const nowMs = performance.now();
    if (nowMs - (this._lastNotifyAt || 0) < 1500) return; // kein Spam bei Nachrichten-Salven
    this._lastNotifyAt = nowMs;
    const now = this.ctx.currentTime;
    [
      [880, 0],
      [1318.5, 0.11],
    ].forEach(([freq, offset]) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now + offset);
      gain.gain.setValueAtTime(0.0001, now + offset);
      gain.gain.exponentialRampToValueAtTime(0.09, now + offset + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.001, now + offset + 0.32);
      osc.connect(gain);
      gain.connect(this.nodes.ui);
      osc.start(now + offset);
      osc.stop(now + offset + 0.34);
    });
  }

  // --- Level-Up-Fanfare (aufsteigendes Dur-Arpeggio + Glanz) ---
  playLevelUp() {
    this.resume();
    if (!this.ctx || this.muted || !this.nodes?.ui) return;
    const now = this.ctx.currentTime;
    const notes = [523.25, 659.25, 783.99, 1046.5]; // C5 E5 G5 C6
    notes.forEach((freq, i) => {
      const t = now + i * 0.09;
      const last = i === notes.length - 1;
      ['triangle', 'sine'].forEach((type, layer) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(freq * (layer ? 2 : 1), t);
        const peak = (layer ? 0.035 : 0.11) * (last ? 1.2 : 1);
        const len = last ? 0.9 : 0.22;
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(peak, t + 0.015);
        gain.gain.exponentialRampToValueAtTime(0.001, t + len);
        osc.connect(gain);
        gain.connect(this.nodes.ui);
        osc.start(t);
        osc.stop(t + len + 0.02);
      });
    });
  }

  // --- Schwerthieb, Waffen-Klang & Reit-Schlag ---
  playWeaponSwing(isCrit = false, weaponSub = 'one_hand', isFinisher = false, isMounted = false) {
    this.resume();
    if (!this.ctx || this.muted) return;
    const now = this.ctx.currentTime;

    // 1. Luft-Swoosh (Waffen- & Reit-spezifisch)
    const noise = this.ctx.createBufferSource();
    noise.buffer = this._noiseBuf;
    const filter = this.ctx.createBiquadFilter();
    filter.type = 'bandpass';
    const baseFreq =
      weaponSub === 'two_hand'
        ? 320
        : weaponSub === 'dagger'
        ? 980
        : weaponSub === 'bow'
        ? 1240
        : weaponSub === 'staff'
        ? 460
        : isMounted
        ? 440
        : 580;
    const dur = weaponSub === 'two_hand' || isFinisher ? 0.21 : weaponSub === 'dagger' ? 0.11 : 0.16;
    filter.frequency.setValueAtTime(baseFreq, now);
    filter.frequency.exponentialRampToValueAtTime(baseFreq * (isMounted ? 1.85 : 2.15), now + dur * 0.85);
    filter.Q.value = weaponSub === 'two_hand' ? 1.4 : 1.9;

    const nGain = this.ctx.createGain();
    nGain.gain.setValueAtTime(isFinisher ? 0.34 : 0.26, now);
    nGain.gain.exponentialRampToValueAtTime(0.001, now + dur);
    noise.connect(filter);
    filter.connect(nGain);
    nGain.connect(this.nodes.sfx);
    noise.start(now);
    noise.stop(now + dur + 0.01);

    // Bei Dolch-Doppelschlag: Zweiter blitzschneller Schnitt nach 65ms
    if (weaponSub === 'dagger' && !isMounted) {
      const n2 = this.ctx.createBufferSource();
      n2.buffer = this._noiseBuf;
      const f2 = this.ctx.createBiquadFilter();
      f2.type = 'bandpass';
      f2.frequency.setValueAtTime(1120, now + 0.065);
      f2.frequency.exponentialRampToValueAtTime(2250, now + 0.15);
      const g2 = this.ctx.createGain();
      g2.gain.setValueAtTime(0.20, now + 0.065);
      g2.gain.exponentialRampToValueAtTime(0.001, now + 0.16);
      n2.connect(f2);
      f2.connect(g2);
      g2.connect(this.nodes.sfx);
      n2.start(now + 0.065);
      n2.stop(now + 0.17);
    }

    // 2. Metallischer Klingen-Klang / Krit- & Finisher-Wucht
    if (isCrit || isFinisher || weaponSub === 'two_hand') {
      const osc = this.ctx.createOscillator();
      const cGain = this.ctx.createGain();
      osc.type = isCrit ? 'sawtooth' : 'triangle';
      const startF = isCrit ? 540 : isFinisher ? 420 : 290;
      osc.frequency.setValueAtTime(startF, now);
      osc.frequency.exponentialRampToValueAtTime(85, now + 0.25);
      cGain.gain.setValueAtTime(isCrit ? 0.34 : 0.22, now);
      cGain.gain.exponentialRampToValueAtTime(0.001, now + 0.27);
      osc.connect(cGain);
      cGain.connect(this.nodes.sfx);
      osc.start(now);
      osc.stop(now + 0.28);
    }
  }

  // --- Wuchtiges Treffer-Feedback (Heavy Hit / Stagger / Finisher Impact) ---
  playHeavyImpact(isCrit = false, isFinisher = false, isPierce = false) {
    this.resume();
    if (!this.ctx || this.muted) return;
    const now = this.ctx.currentTime;

    // 1. Physischer Sub-Bass-Wumms (Körper-Treffer & Wanken)
    const sub = this.ctx.createOscillator();
    const subGain = this.ctx.createGain();
    sub.type = 'sine';
    sub.frequency.setValueAtTime(isFinisher || isCrit ? 135 : 108, now);
    sub.frequency.exponentialRampToValueAtTime(38, now + 0.19);
    subGain.gain.setValueAtTime(isCrit || isFinisher ? 0.38 : 0.24, now);
    subGain.gain.exponentialRampToValueAtTime(0.001, now + 0.21);
    sub.connect(subGain);
    subGain.connect(this.nodes.sfx);
    sub.start(now);
    sub.stop(now + 0.22);

    // 2. Knackiger Rüstungs-/Knochen-Crunch-Transient
    const crunch = this.ctx.createBufferSource();
    crunch.buffer = this._noiseBuf;
    const flt = this.ctx.createBiquadFilter();
    flt.type = 'bandpass';
    flt.frequency.setValueAtTime(isPierce ? 1680 : 940, now);
    flt.frequency.exponentialRampToValueAtTime(280, now + 0.12);
    flt.Q.value = 1.6;
    const cg = this.ctx.createGain();
    cg.gain.setValueAtTime(isCrit ? 0.28 : 0.18, now);
    cg.gain.exponentialRampToValueAtTime(0.001, now + 0.13);
    crunch.connect(flt);
    flt.connect(cg);
    cg.connect(this.nodes.sfx);
    crunch.start(now);
    crunch.stop(now + 0.14);
  }

  // --- Militärpferd Reit-Fertigkeiten (Stampfen, Ansturm, Wellenangriff) ---
  playHorseSkillSound(skillId = 'horse_stomp') {
    this.resume();
    if (!this.ctx || this.muted) return;
    const now = this.ctx.currentTime;

    const osc = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    osc.type = 'triangle';
    if (skillId === 'horse_stomp') {
      osc.frequency.setValueAtTime(160, now);
      osc.frequency.exponentialRampToValueAtTime(36, now + 0.38);
      g.gain.setValueAtTime(0.42, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.42);
    } else if (skillId === 'horse_charge') {
      osc.frequency.setValueAtTime(220, now);
      osc.frequency.exponentialRampToValueAtTime(480, now + 0.18);
      osc.frequency.exponentialRampToValueAtTime(90, now + 0.36);
      g.gain.setValueAtTime(0.35, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.38);
    } else {
      osc.frequency.setValueAtTime(640, now);
      osc.frequency.exponentialRampToValueAtTime(180, now + 0.32);
      g.gain.setValueAtTime(0.32, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
    }
    osc.connect(g);
    g.connect(this.nodes.sfx);
    osc.start(now);
    osc.stop(now + 0.44);
  }

  // --- Schritt- & Hufgetrappel (Stein, Gras, Wasser, Schnee) ---
  playFootstep(surface = 'grass', isMounted = false) {
    this.resume();
    if (!this.ctx || this.muted) return;
    const now = this.ctx.currentTime;
    this._stepToggle = 1 - this._stepToggle;
    const pitchVar = (this._stepToggle ? 1.04 : 0.96) * (0.95 + Math.random() * 0.1);

    if (isMounted) {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'triangle';
      const hoofFreq = surface === 'stone' ? 340 : surface === 'water' ? 210 : 250;
      osc.frequency.setValueAtTime(hoofFreq * pitchVar, now);
      osc.frequency.exponentialRampToValueAtTime(75, now + 0.065);
      gain.gain.setValueAtTime(surface === 'stone' ? 0.22 : 0.16, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.075);
      osc.connect(gain);
      gain.connect(this.nodes.sfx);
      osc.start(now);
      osc.stop(now + 0.08);
    }

    const src = this.ctx.createBufferSource();
    src.buffer = this._noiseBuf;
    const flt = this.ctx.createBiquadFilter();
    flt.type = surface === 'snow' ? 'bandpass' : surface === 'water' ? 'lowpass' : 'highpass';
    flt.frequency.value = (surface === 'snow' ? 1450 : surface === 'water' ? 680 : 950) * pitchVar;
    const g = this.ctx.createGain();
    const dur = surface === 'snow' ? 0.11 : surface === 'water' ? 0.14 : 0.07;
    g.gain.setValueAtTime(surface === 'water' ? 0.18 : 0.09, now);
    g.gain.exponentialRampToValueAtTime(0.001, now + dur);
    src.connect(flt);
    flt.connect(g);
    g.connect(this.nodes.sfx);
    src.start(now);
    src.stop(now + dur + 0.01);
  }

  // --- Spitzhacken-Schlag beim Bergbau: Metallisches Klirren mit physikalischem Schlucht- & Wald-Nachhall ---
  playMiningPickaxeHit(distance = 0, canyonEcho = 1.0) {
    this.resume();
    if (!this.ctx || this.muted) return;
    const now = this.ctx.currentTime;
    const distAtten = Math.max(0.15, Math.min(1.0, 1.0 - distance / 95.0));
    const pitchJitter = 0.96 + Math.random() * 0.08;

    // 1. Direkter Gesteins-Wucht-Impuls (Sub-Thud + Gesteins-Splitter)
    const rockOsc = this.ctx.createOscillator();
    const rockGain = this.ctx.createGain();
    rockOsc.type = 'triangle';
    rockOsc.frequency.setValueAtTime(145 * pitchJitter, now);
    rockOsc.frequency.exponentialRampToValueAtTime(46, now + 0.16);
    rockGain.gain.setValueAtTime(0.28 * distAtten, now);
    rockGain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
    rockOsc.connect(rockGain);
    rockGain.connect(this.nodes.sfx);
    rockOsc.start(now);
    rockOsc.stop(now + 0.19);

    const shardNoise = this.ctx.createBufferSource();
    shardNoise.buffer = this._noiseBuf;
    const shardFlt = this.ctx.createBiquadFilter();
    shardFlt.type = 'bandpass';
    shardFlt.frequency.setValueAtTime(2450 * pitchJitter, now);
    shardFlt.frequency.exponentialRampToValueAtTime(680, now + 0.14);
    const shardG = this.ctx.createGain();
    shardG.gain.setValueAtTime(0.20 * distAtten, now);
    shardG.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
    shardNoise.connect(shardFlt);
    shardFlt.connect(shardG);
    shardG.connect(this.nodes.sfx);
    shardNoise.start(now);
    shardNoise.stop(now + 0.16);

    // 2. Metallisches Klirren der Spitzhacke + physikalisch gedämpftes 3-Stufen-Echo durch Schluchten & Wälder
    const harmonics = [1440, 2210, 3260, 4520];
    const echoTaps = [
      { delay: 0.0, gain: 0.14 * distAtten, cutoff: 6500, pan: 0.0, decay: 0.26 },
      { delay: 0.165, gain: 0.062 * canyonEcho * distAtten, cutoff: 2400, pan: -0.52, decay: 0.32 },
      { delay: 0.365, gain: 0.034 * canyonEcho * distAtten, cutoff: 1450, pan: 0.58, decay: 0.38 },
      { delay: 0.62, gain: 0.017 * canyonEcho * distAtten, cutoff: 880, pan: -0.25, decay: 0.45 },
    ];

    for (const tap of echoTaps) {
      if (tap.gain < 0.002) continue;
      const tStart = now + tap.delay;
      const lpFilter = this.ctx.createBiquadFilter();
      lpFilter.type = 'lowpass';
      lpFilter.frequency.setValueAtTime(tap.cutoff, tStart);

      let outNode = lpFilter;
      if (typeof this.ctx.createStereoPanner === 'function' && tap.pan !== 0) {
        const panner = this.ctx.createStereoPanner();
        panner.pan.setValueAtTime(tap.pan, tStart);
        lpFilter.connect(panner);
        outNode = panner;
      }
      outNode.connect(this.nodes.sfx);

      for (let i = 0; i < harmonics.length; i++) {
        const f = harmonics[i] * pitchJitter;
        const osc = this.ctx.createOscillator();
        const g = this.ctx.createGain();
        osc.type = i % 2 === 0 ? 'sine' : 'triangle';
        osc.frequency.setValueAtTime(f, tStart);
        osc.frequency.exponentialRampToValueAtTime(f * 0.76, tStart + tap.decay);
        const hWeight = i === 0 ? 1.0 : i === 1 ? 0.85 : i === 2 ? 0.6 : 0.35;
        g.gain.setValueAtTime(tap.gain * hWeight, tStart);
        g.gain.exponentialRampToValueAtTime(0.0008, tStart + tap.decay);
        osc.connect(g);
        g.connect(lpFilter);
        osc.start(tStart);
        osc.stop(tStart + tap.decay + 0.02);
      }
    }
  }

  // --- Dumpfes Krachen der Axt beim Holzfällen mit atmosphärischem Wald-Nachhall ---
  playWoodchopAxeHit(distance = 0, forestEcho = 1.0) {
    this.resume();
    if (!this.ctx || this.muted) return;
    const now = this.ctx.currentTime;
    const distAtten = Math.max(0.15, Math.min(1.0, 1.0 - distance / 95.0));
    const pitchJitter = 0.94 + Math.random() * 0.1;

    // 1. Dumpfes, schweres Krachen der Axt im Stamm + Holzfaser-Knacken + Wald-Echo
    const echoTaps = [
      { delay: 0.0, gain: 0.34 * distAtten, cutoff: 2600, pan: 0.0, dur: 0.2 },
      { delay: 0.145, gain: 0.13 * forestEcho * distAtten, cutoff: 1280, pan: 0.48, dur: 0.24 },
      { delay: 0.32, gain: 0.068 * forestEcho * distAtten, cutoff: 760, pan: -0.5, dur: 0.29 },
      { delay: 0.54, gain: 0.032 * forestEcho * distAtten, cutoff: 460, pan: 0.22, dur: 0.35 },
    ];

    for (const tap of echoTaps) {
      if (tap.gain < 0.002) continue;
      const tStart = now + tap.delay;
      const lp = this.ctx.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.setValueAtTime(tap.cutoff, tStart);

      let outNode = lp;
      if (typeof this.ctx.createStereoPanner === 'function' && tap.pan !== 0) {
        const panner = this.ctx.createStereoPanner();
        panner.pan.setValueAtTime(tap.pan, tStart);
        lp.connect(panner);
        outNode = panner;
      }
      outNode.connect(this.nodes.sfx);

      // Tiefer hölzerner Stamm-Schlag
      const thud = this.ctx.createOscillator();
      const thudG = this.ctx.createGain();
      thud.type = 'triangle';
      thud.frequency.setValueAtTime(188 * pitchJitter, tStart);
      thud.frequency.exponentialRampToValueAtTime(58, tStart + tap.dur);
      thudG.gain.setValueAtTime(tap.gain, tStart);
      thudG.gain.exponentialRampToValueAtTime(0.0008, tStart + tap.dur);
      thud.connect(thudG);
      thudG.connect(lp);
      thud.start(tStart);
      thud.stop(tStart + tap.dur + 0.02);

      // Trockenes Holz-Krachen (Resonanzkörper des Baumstamms)
      const crack = this.ctx.createBufferSource();
      crack.buffer = this._noiseBuf;
      const bp = this.ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.setValueAtTime(640 * pitchJitter, tStart);
      bp.frequency.exponentialRampToValueAtTime(290, tStart + tap.dur * 0.85);
      bp.Q.value = 2.1;
      const crackG = this.ctx.createGain();
      crackG.gain.setValueAtTime(tap.gain * 0.72, tStart);
      crackG.gain.exponentialRampToValueAtTime(0.0008, tStart + tap.dur * 0.9);
      crack.connect(bp);
      bp.connect(crackG);
      crackG.connect(lp);
      crack.start(tStart);
      crack.stop(tStart + tap.dur);
    }
  }

  // --- Angel-Auswurf & Wasser-Platsch ---
  playFishingSplash(isBite = false) {
    this.resume();
    if (!this.ctx || this.muted) return;
    const now = this.ctx.currentTime;
    const src = this.ctx.createBufferSource();
    src.buffer = this._noiseBuf;
    const flt = this.ctx.createBiquadFilter();
    flt.type = 'bandpass';
    flt.frequency.setValueAtTime(isBite ? 860 : 540, now);
    flt.frequency.exponentialRampToValueAtTime(280, now + 0.28);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(isBite ? 0.26 : 0.18, now);
    g.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
    src.connect(flt);
    flt.connect(g);
    g.connect(this.nodes.sfx);
    src.start(now);
    src.stop(now + 0.32);
  }

  // --- Gewitterdonner passend zum Blitz ---
  playThunder() {
    this.resume();
    if (!this.ctx || this.muted) return;
    const now = this.ctx.currentTime;
    const src = this.ctx.createBufferSource();
    src.buffer = this._noiseBuf;
    const flt = this.ctx.createBiquadFilter();
    flt.type = 'lowpass';
    flt.frequency.setValueAtTime(240, now);
    flt.frequency.exponentialRampToValueAtTime(55, now + 2.4);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.42, now);
    g.gain.exponentialRampToValueAtTime(0.001, now + 2.6);
    src.connect(flt);
    flt.connect(g);
    g.connect(this.nodes.ambient);
    src.start(now);
    src.stop(now + 2.7);
  }
}

export const audioSystem = new AudioSystem();
if (typeof window !== 'undefined') {
  window.aeryndorAudio = audioSystem;
}
