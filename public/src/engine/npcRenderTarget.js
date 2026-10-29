// ============================================================================
// AERYNDOR: LEGACY OF THE MONOLITHS – 3D-NPC-Bühne (Schmied & Runenweberin)
// ============================================================================
//  - 'blacksmith': Schmiede-Esse, Amboss, +Plus-Glühen & animierter 3D-Schmied
//  - 'runeweaver': Runenaltar, Ritualkreis, Reliktwaffe & 3D-Runenweberin
// ============================================================================

import * as THREE from '../../vendor/three.module.js';

export class NpcRenderTargetStage {
  constructor(mode = 'blacksmith') {
    this.mode = mode; // 'blacksmith' | 'runeweaver'
    this.disposed = false;
    this.clock = new THREE.Clock();
    this.actors = [];
    this.particles = null;
    this.actionBurst = 0;
    this.actionResult = null;
    this.isDragging = false;
    this.prevX = 0;
    this.currentSignature = '';
    this.container = null;
    this.weaponBaseY = 1.25;
    this.fireCore = null;
    this.fireLight = null;
    this._rafRunning = false;
    this._abort = new AbortController(); // bündelt alle DOM-Listener für dispose()

    this.initRendererAndScene();
  }

  initRendererAndScene() {
    const width = 324;
    const height = 128;

    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x070b14, 0.045);

    this.camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 80);
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    // Kein Shadow-Mapping: kein Mesh der Bühne wirft/empfängt Schatten -> ersparter Shadow-Pass pro Frame
    this.renderer.shadowMap.enabled = false;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.18;

    this.bindInteraction();
    this.animate();
  }

  mountTo(container, options = {}) {
    if (!container || this.disposed) return;
    this.container = container;

    const width = Math.max(240, container.clientWidth || 324);
    const height = Math.max(110, container.clientHeight || 128);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);

    if (this.renderer.domElement.parentElement !== container) {
      container.innerHTML = '';
      container.appendChild(this.renderer.domElement);
    }

    const weaponType = this.resolveWeaponType(options.templateId, options.slot);
    const plusLevel = Math.max(0, Number(options.plus) || 0);
    const sig = `${this.mode}|${weaponType}|${plusLevel}`;

    if (sig !== this.currentSignature) {
      this.currentSignature = sig;
      this.rebuildStage(weaponType, plusLevel);
    }
    this.clock.getDelta();
    if (!this._rafRunning) {
      this._rafRunning = true;
      requestAnimationFrame(() => this.animate());
    }
  }

  _disposeHierarchy(obj) {
    if (!obj) return;
    obj.traverse((child) => {
      if (child.geometry && !child.geometry.userData?.isShared) {
        child.geometry.dispose();
      }
      if (child.material) {
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        for (const m of mats) {
          if (!m || m.userData?.isShared) continue;
          for (const k of ['map', 'alphaMap', 'emissiveMap', 'normalMap', 'roughnessMap', 'metalnessMap']) {
            if (m[k] && !m[k].userData?.isCached) {
              m[k].dispose();
            }
          }
          m.dispose();
        }
      }
    });
  }

  resolveWeaponType(templateId = '', slot = 'weapon') {
    const id = String(templateId || '').toLowerCase();
    if (id.includes('red_iron') || id.includes('rek') || id.includes('rsb') || id.includes('partisan') || id.includes('halberd')) {
      return 'rsb';
    }
    if (id.includes('fullmoon') || id.includes('vms') || id.includes('msk') || id.includes('moon')) {
      return 'msk';
    }
    if (id.includes('poison') || id.includes('gift') || id.includes('seuchen')) {
      return 'seuchenzahn';
    }
    if (id.includes('star') || id.includes('sternen') || id.includes('runic') || id.includes('solar')) {
      return 'sternenreisser';
    }
    if (id.includes('bow') || id.includes('bogen') || id.includes('horn')) {
      return 'bow';
    }
    if (id.includes('bell') || id.includes('glocke') || id.includes('fan') || id.includes('fächer')) {
      return 'bell';
    }
    if (id.includes('staff') || id.includes('stab')) {
      return 'staff';
    }
    if (slot === 'armor' || slot === 'shield' || slot === 'helmet') {
      return 'sternenreisser';
    }
    return 'msk';
  }

  rebuildStage(weaponType = 'msk', plusLevel = 0) {
    while (this.scene.children.length > 0) {
      const child = this.scene.children[0];
      this.scene.remove(child);
      this._disposeHierarchy(child);
    }
    this.actors = [];
    this.anvilWeapon = null;
    this.arcaneRing = null;
    this.mainActor = null;
    this.fireCore = null;
    this.fireLight = null;

    // Ambient & Directional Lights (wie in Projekt 2 scene3d.js)
    const hemi = new THREE.HemisphereLight(0x7dd3fc, 0x1e1b4b, 0.88);
    this.scene.add(hemi);

    const dirLight = new THREE.DirectionalLight(0xfffbeb, 1.45);
    dirLight.position.set(6, 12, 8);
    this.scene.add(dirLight);

    this.setupFloatingParticles();

    if (this.mode === 'blacksmith') {
      this.buildBlacksmithForge(weaponType, plusLevel);
    } else {
      this.buildRuneweaverSanctum(weaponType, plusLevel);
    }
  }

  setupFloatingParticles() {
    const count = 65;
    const geo = new THREE.BufferGeometry();
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 14;
      pos[i * 3 + 1] = Math.random() * 5 + 0.2;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 12;
    }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const mat = new THREE.PointsMaterial({
      color: this.mode === 'blacksmith' ? 0x38bdf8 : 0xc084fc,
      size: 0.11,
      transparent: true,
      opacity: 0.78,
    });
    this.particles = new THREE.Points(geo, mat);
    this.scene.add(this.particles);
  }

  createAnimatedHumanoid(cfg = {}) {
    const root = new THREE.Group();
    const {
      armorColor = 0x334155,
      accentColor = 0xf59e0b,
      skinColor = 0xf1c27d,
      capeColor = null,
      helmetType = 'smith',
      weaponType = 'hammer',
      plusLevel = 0,
      scale = 1.0,
      animStyle = 'smith_hammer',
    } = cfg;

    root.scale.setScalar(scale);

    const armorMat = new THREE.MeshStandardMaterial({ color: armorColor, metalness: 0.65, roughness: 0.35 });
    const accentMat = new THREE.MeshStandardMaterial({
      color: accentColor,
      metalness: 0.8,
      roughness: 0.2,
      emissive: accentColor,
      emissiveIntensity: 0.14,
    });
    const skinMat = new THREE.MeshStandardMaterial({ color: skinColor, roughness: 0.6 });
    const darkMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.7 });

    // Pedestal base
    const baseDisk = new THREE.Mesh(
      new THREE.CylinderGeometry(0.85, 0.98, 0.16, 24),
      new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.5, roughness: 0.4 })
    );
    baseDisk.position.y = 0.08;
    root.add(baseDisk);

    const baseRing = new THREE.Mesh(
      new THREE.TorusGeometry(0.9, 0.035, 12, 36),
      new THREE.MeshStandardMaterial({ color: accentColor, emissive: accentColor, emissiveIntensity: 0.65 })
    );
    baseRing.rotation.x = Math.PI / 2;
    baseRing.position.y = 0.16;
    root.add(baseRing);

    const bodyGroup = new THREE.Group();
    bodyGroup.position.y = 0.16;
    root.add(bodyGroup);

    // Legs
    const leftLeg = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.72, 0.26), darkMat);
    leftLeg.position.set(-0.17, 0.36, 0);
    bodyGroup.add(leftLeg);

    const rightLeg = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.72, 0.26), darkMat);
    rightLeg.position.set(0.17, 0.36, 0);
    bodyGroup.add(rightLeg);

    const bootGeo = new THREE.BoxGeometry(0.27, 0.22, 0.34);
    const lBoot = new THREE.Mesh(bootGeo, accentMat);
    lBoot.position.set(0, -0.26, 0.04);
    leftLeg.add(lBoot);
    const rBoot = new THREE.Mesh(bootGeo, accentMat);
    rBoot.position.set(0, -0.26, 0.04);
    rightLeg.add(rBoot);

    // Torso
    const torso = new THREE.Group();
    torso.position.y = 1.08;
    bodyGroup.add(torso);

    const chest = new THREE.Mesh(new THREE.BoxGeometry(0.68, 0.82, 0.42), armorMat);
    torso.add(chest);

    const chestGem = new THREE.Mesh(
      new THREE.OctahedronGeometry(0.13, 0),
      new THREE.MeshStandardMaterial({ color: 0x38bdf8, emissive: 0x38bdf8, emissiveIntensity: 0.9 })
    );
    chestGem.position.set(0, 0.08, 0.22);
    torso.add(chestGem);

    const belt = new THREE.Mesh(new THREE.BoxGeometry(0.71, 0.12, 0.45), accentMat);
    belt.position.set(0, -0.34, 0);
    torso.add(belt);

    // Shoulders
    const pauldronGeo = new THREE.SphereGeometry(0.23, 12, 12);
    const lShoulder = new THREE.Mesh(pauldronGeo, accentMat);
    lShoulder.position.set(-0.46, 0.28, 0);
    lShoulder.scale.set(1, 0.8, 1);
    torso.add(lShoulder);

    const rShoulder = new THREE.Mesh(pauldronGeo, accentMat);
    rShoulder.position.set(0.46, 0.28, 0);
    rShoulder.scale.set(1, 0.8, 1);
    torso.add(rShoulder);

    let capeMesh = null;
    if (capeColor) {
      const capeGeo = new THREE.PlaneGeometry(0.76, 1.35, 4, 8);
      const capeMat = new THREE.MeshStandardMaterial({
        color: capeColor,
        side: THREE.DoubleSide,
        roughness: 0.6,
      });
      capeMesh = new THREE.Mesh(capeGeo, capeMat);
      capeMesh.position.set(0, -0.28, -0.25);
      capeMesh.rotation.x = 0.18;
      torso.add(capeMesh);
    }

    // Head
    const headGroup = new THREE.Group();
    headGroup.position.set(0, 0.66, 0);
    torso.add(headGroup);

    const headMesh = new THREE.Mesh(new THREE.SphereGeometry(0.25, 16, 16), skinMat);
    headGroup.add(headMesh);

    const eyeMat = new THREE.MeshBasicMaterial({ color: helmetType === 'hood' ? 0x38bdf8 : 0x1e293b });
    const lEye = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 8), eyeMat);
    lEye.position.set(-0.08, 0.03, 0.22);
    headGroup.add(lEye);
    const rEye = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 8), eyeMat);
    rEye.position.set(0.08, 0.03, 0.22);
    headGroup.add(rEye);

    if (helmetType === 'hood') {
      const hood = new THREE.Mesh(new THREE.ConeGeometry(0.34, 0.52, 12), armorMat);
      hood.position.set(0, 0.14, -0.02);
      headGroup.add(hood);
    } else if (helmetType === 'smith') {
      const beard = new THREE.Mesh(
        new THREE.BoxGeometry(0.3, 0.26, 0.22),
        new THREE.MeshStandardMaterial({ color: 0x451a03 })
      );
      beard.position.set(0, -0.14, 0.14);
      headGroup.add(beard);
    }

    // Arms
    const rightArmPivot = new THREE.Group();
    rightArmPivot.position.set(-0.48, 0.22, 0);
    torso.add(rightArmPivot);

    const rightArm = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.64, 0.2), armorMat);
    rightArm.position.set(0, -0.26, 0);
    rightArmPivot.add(rightArm);

    const leftArmPivot = new THREE.Group();
    leftArmPivot.position.set(0.48, 0.22, 0);
    torso.add(leftArmPivot);

    const leftArm = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.64, 0.2), armorMat);
    leftArm.position.set(0, -0.26, 0);
    leftArmPivot.add(leftArm);

    if (weaponType) {
      const weaponMesh = this.build3DWeaponMesh(weaponType, plusLevel);
      weaponMesh.position.set(0, -0.55, 0.18);
      rightArmPivot.add(weaponMesh);
    }

    const actor = {
      root,
      bodyGroup,
      torso,
      headGroup,
      rightArmPivot,
      leftArmPivot,
      leftLeg,
      rightLeg,
      capeMesh,
      animStyle,
      phase: Math.random() * Math.PI * 2,
    };
    this.actors.push(actor);
    return actor;
  }

  build3DWeaponMesh(weaponType, plusLevel = 0) {
    const group = new THREE.Group();
    const glowIntensity = plusLevel >= 9 ? 0.95 : plusLevel >= 7 ? 0.55 : 0.2;

    if (weaponType === 'hammer') {
      const handle = new THREE.Mesh(
        new THREE.CylinderGeometry(0.04, 0.04, 0.75, 8),
        new THREE.MeshStandardMaterial({ color: 0x78350f })
      );
      handle.rotation.x = Math.PI / 2;
      const head = new THREE.Mesh(
        new THREE.BoxGeometry(0.28, 0.24, 0.48),
        new THREE.MeshStandardMaterial({
          color: 0x94a3b8,
          metalness: 0.85,
          roughness: 0.25,
          emissive: 0xf97316,
          emissiveIntensity: 0.35,
        })
      );
      head.position.set(0, 0, 0.36);
      group.add(handle, head);
      return group;
    }

    if (weaponType === 'staff') {
      const shaft = new THREE.Mesh(
        new THREE.CylinderGeometry(0.035, 0.035, 1.65, 8),
        new THREE.MeshStandardMaterial({ color: 0x4c1d95, metalness: 0.6 })
      );
      const orb = new THREE.Mesh(
        new THREE.OctahedronGeometry(0.18, 0),
        new THREE.MeshStandardMaterial({ color: 0xa855f7, emissive: 0xc084fc, emissiveIntensity: 0.9 })
      );
      orb.position.y = 0.88;
      group.add(shaft, orb);
      group.rotation.x = 0.35;
      return group;
    }

    if (weaponType === 'bow') {
      const arc = new THREE.Mesh(
        new THREE.TorusGeometry(0.55, 0.04, 8, 20, Math.PI),
        new THREE.MeshStandardMaterial({
          color: 0xf59e0b,
          metalness: 0.8,
          roughness: 0.2,
          emissive: 0x10b981,
          emissiveIntensity: glowIntensity,
        })
      );
      arc.rotation.z = -Math.PI / 2;
      group.add(arc);
      return group;
    }

    if (weaponType === 'bell') {
      const bell = new THREE.Mesh(
        new THREE.ConeGeometry(0.22, 0.38, 14),
        new THREE.MeshStandardMaterial({
          color: 0xfde047,
          metalness: 0.85,
          roughness: 0.2,
          emissive: 0x38bdf8,
          emissiveIntensity: 0.45,
        })
      );
      bell.position.z = 0.25;
      group.add(bell);
      return group;
    }

    let bladeColor = 0xbae6fd;
    let emissiveColor = 0x38bdf8;
    let bladeLen = 1.28;
    let bladeWidth = 0.15;

    if (weaponType === 'rsb') {
      bladeColor = 0xef4444;
      emissiveColor = 0xdc2626;
      bladeLen = 1.52;
      bladeWidth = 0.23;
    } else if (weaponType === 'seuchenzahn') {
      bladeColor = 0x10b981;
      emissiveColor = 0x10b981;
      bladeLen = 1.35;
    } else if (weaponType === 'sternenreisser') {
      bladeColor = 0xfef08a;
      emissiveColor = 0x38bdf8;
      bladeLen = 1.48;
      bladeWidth = 0.2;
    }

    const hilt = new THREE.Mesh(
      new THREE.CylinderGeometry(0.035, 0.035, 0.3, 8),
      new THREE.MeshStandardMaterial({ color: 0x78350f })
    );
    hilt.rotation.x = Math.PI / 2;

    const guard = new THREE.Mesh(
      new THREE.BoxGeometry(0.36, 0.08, 0.09),
      new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.85 })
    );
    guard.position.z = 0.15;

    const blade = new THREE.Mesh(
      new THREE.BoxGeometry(bladeWidth, 0.04, bladeLen),
      new THREE.MeshStandardMaterial({
        color: bladeColor,
        metalness: 0.85,
        roughness: 0.18,
        emissive: emissiveColor,
        emissiveIntensity: Math.max(0.28, glowIntensity),
      })
    );
    blade.position.z = 0.15 + bladeLen / 2;

    group.add(hilt, guard, blade);
    return group;
  }

  buildBlacksmithForge(weaponType = 'msk', plusLevel = 0) {
    this.camera.position.set(0, 2.15, 4.95);
    this.camera.lookAt(0, 1.18, 0);

    // Glühender Schmiedeofen links (wie in Projekt 2 Bild)
    const furnace = new THREE.Mesh(
      new THREE.BoxGeometry(1.6, 2.2, 1.4),
      new THREE.MeshStandardMaterial({ color: 0x27272a, roughness: 0.8 })
    );
    furnace.position.set(-1.7, 1.1, -0.8);
    this.scene.add(furnace);

    const fireCore = new THREE.Mesh(
      new THREE.SphereGeometry(0.55, 16, 16),
      new THREE.MeshBasicMaterial({ color: 0xf97316 })
    );
    fireCore.position.set(-1.7, 0.8, -0.1);
    this.scene.add(fireCore);

    const fireLight = new THREE.PointLight(0xf97316, 5, 9);
    fireLight.position.set(-1.2, 1.5, 0.5);
    this.scene.add(fireLight);
    this.fireCore = fireCore;
    this.fireLight = fireLight;

    // 3D-Amboss vorne mittig
    const anvilGroup = new THREE.Group();
    const anvilBase = new THREE.Mesh(
      new THREE.BoxGeometry(0.9, 0.55, 0.6),
      new THREE.MeshStandardMaterial({ color: 0x3f3f46, metalness: 0.8, roughness: 0.3 })
    );
    anvilBase.position.y = 0.28;
    const anvilTop = new THREE.Mesh(
      new THREE.BoxGeometry(1.25, 0.32, 0.52),
      new THREE.MeshStandardMaterial({ color: 0x71717a, metalness: 0.9, roughness: 0.2 })
    );
    anvilTop.position.y = 0.68;
    anvilGroup.add(anvilBase, anvilTop);
    anvilGroup.position.set(0, 0, 0.85);
    this.scene.add(anvilGroup);

    // Schwebende Waffe über dem Amboss
    this.anvilWeapon = this.build3DWeaponMesh(weaponType, plusLevel);
    this.weaponBaseY = 1.25;
    this.anvilWeapon.position.set(-0.5, this.weaponBaseY, 0.85);
    this.anvilWeapon.rotation.y = Math.PI / 2;
    this.scene.add(this.anvilWeapon);

    // 3D-Schmied-NPC hinter dem Amboss
    const smith = this.createAnimatedHumanoid({
      armorColor: 0x451a03,
      accentColor: 0xf97316,
      helmetType: 'smith',
      weaponType: 'hammer',
      scale: 1.15,
      animStyle: 'smith_hammer',
    });
    smith.root.position.set(0, 0, -0.2);
    this.mainActor = smith;
    this.scene.add(smith.root);
  }

  buildRuneweaverSanctum(weaponType = 'sternenreisser', plusLevel = 0) {
    this.camera.position.set(0, 2.25, 5.05);
    this.camera.lookAt(0, 1.25, 0);

    const runeLight = new THREE.PointLight(0xa855f7, 5, 10);
    runeLight.position.set(0, 2.0, 1.0);
    this.scene.add(runeLight);

    // Rotierender arkaner Seelen-/Runenkreis am Boden
    this.arcaneRing = new THREE.Mesh(
      new THREE.RingGeometry(1.38, 1.56, 6),
      new THREE.MeshBasicMaterial({ color: 0xc084fc, side: THREE.DoubleSide })
    );
    this.arcaneRing.rotation.x = -Math.PI / 2;
    this.arcaneRing.position.set(0, 0.05, 0.8);
    this.scene.add(this.arcaneRing);

    // Schwebende Reliktwaffe im Ritualkreis
    this.anvilWeapon = this.build3DWeaponMesh(weaponType, plusLevel);
    // Basis-Höhe muss gesetzt werden, sonst springt die Waffe im ersten Frame von 1.35 auf 1.25 (animate nutzt weaponBaseY)
    this.weaponBaseY = 1.35;
    this.anvilWeapon.position.set(0, this.weaponBaseY, 1.1);
    this.anvilWeapon.rotation.x = -Math.PI / 2;
    this.scene.add(this.anvilWeapon);

    // 3D-Seelenverbesserin / Runenweberin NPC
    const weaver = this.createAnimatedHumanoid({
      armorColor: 0x3b0764,
      accentColor: 0x38bdf8,
      capeColor: 0x4c1d95,
      helmetType: 'hood',
      weaponType: 'staff',
      scale: 1.12,
      animStyle: 'float_mystic',
    });
    weaver.root.position.set(0, 0.2, -0.45);
    this.mainActor = weaver;
    this.scene.add(weaver.root);
  }

  triggerActionAnimation(resultType = 'success') {
    this.actionBurst = 1.4;
    this.actionResult = resultType;
  }

  bindInteraction() {
    const dom = this.renderer.domElement;
    const opts = { signal: this._abort.signal };
    dom.addEventListener('pointerdown', (e) => {
      this.isDragging = true;
      this.prevX = e.clientX;
      // Pointer-Capture: Drehen funktioniert auch, wenn der Zeiger das kleine Canvas verlässt
      dom.setPointerCapture?.(e.pointerId);
    }, opts);
    const stopDrag = () => {
      this.isDragging = false;
    };
    window.addEventListener('pointerup', stopDrag, opts);
    window.addEventListener('pointercancel', stopDrag, opts);
    dom.addEventListener('pointermove', (e) => {
      if (this.isDragging && this.mainActor) {
        const dx = e.clientX - this.prevX;
        this.prevX = e.clientX;
        this.mainActor.root.rotation.y += dx * 0.014;
      }
    }, opts);
  }

  animate() {
    if (this.disposed) {
      this._rafRunning = false;
      return;
    }
    // Render-Loop komplett pausieren, wenn das Viewport-Element nicht sichtbar im DOM eingehängt ist (wird durch mountTo automatisch geweckt)
    if (!this.container || !this.container.isConnected) {
      this._rafRunning = false;
      return;
    }
    const winEl = this.container.closest('.ornate-window, .window-frame');
    if (winEl && winEl.classList.contains('hidden')) {
      this._rafRunning = false;
      return;
    }
    this._rafRunning = true;
    requestAnimationFrame(() => this.animate());

    const dt = Math.min(0.1, this.clock.getDelta());
    const elapsed = this.clock.getElapsedTime();

    if (this.actionBurst > 0) {
      this.actionBurst = Math.max(0, this.actionBurst - dt * 1.6);
    }

    if (this.fireCore && this.fireLight) {
      const flicker = 1.0 + Math.sin(elapsed * 18.0) * 0.18 + Math.cos(elapsed * 27.0) * 0.12;
      this.fireLight.intensity = 5.0 * flicker;
      this.fireCore.scale.setScalar(0.95 + Math.sin(elapsed * 14.0) * 0.08);
    }
    if (this.arcaneRing) {
      this.arcaneRing.rotation.z = elapsed * 0.85;
    }

    if (this.anvilWeapon) {
      this.anvilWeapon.position.y = (this.weaponBaseY || 1.25) + Math.sin(elapsed * 3) * 0.08;
      if (this.mode === 'runeweaver') {
        this.anvilWeapon.rotation.z = elapsed * 1.4 + this.actionBurst * 8;
      }
    }

    if (this.particles) {
      this.particles.rotation.y = elapsed * 0.08;
    }

    for (const ac of this.actors) {
      const t = elapsed * 2.6 + ac.phase;
      ac.torso.position.y = 1.08 + Math.sin(t) * 0.035;
      ac.headGroup.rotation.y = Math.sin(t * 0.5) * 0.12;

      if (ac.capeMesh) {
        ac.capeMesh.rotation.x = 0.2 + Math.sin(t * 1.5) * 0.08;
      }

      if (ac.animStyle === 'smith_hammer') {
        const speed = this.actionBurst > 0 ? 15 : 4.2;
        const swing = Math.sin(elapsed * speed);
        ac.rightArmPivot.rotation.x = -0.9 + swing * 0.85;
        ac.torso.rotation.x = swing > 0.5 ? 0.18 : 0;
      } else if (ac.animStyle === 'float_mystic') {
        ac.bodyGroup.position.y = 0.36 + Math.sin(t) * 0.13;
        ac.rightArmPivot.rotation.x = -0.6 + Math.sin(t * 1.3) * 0.25 + (this.actionBurst > 0 ? Math.sin(elapsed * 14) * 0.45 : 0);
        ac.leftArmPivot.rotation.x = -0.5 + Math.cos(t * 1.3) * 0.25;
      }
    }

    this.renderer.render(this.scene, this.camera);
  }

  /** Gibt Szene, GPU-Ressourcen, Listener & WebGL-Kontext frei. Danach ist die Instanz nicht mehr nutzbar. */
  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this._rafRunning = false;
    this._abort.abort();
    while (this.scene.children.length > 0) {
      const child = this.scene.children[0];
      this.scene.remove(child);
      this._disposeHierarchy(child);
    }
    this.actors = [];
    this.mainActor = null;
    this.anvilWeapon = null;
    this.arcaneRing = null;
    this.fireCore = null;
    this.fireLight = null;
    this.particles = null;
    this.renderer.domElement.remove();
    this.renderer.dispose();
    this.renderer.forceContextLoss?.();
    this.container = null;
  }
}
