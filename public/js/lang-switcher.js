(function () {
  'use strict';

  var STORAGE_KEY = 'aeryndor_hp_lang';
  var originalNodes = [];
  var originalPlaceholders = [];
  var originalTitles = [];
  var initialized = false;

  // Exakte & Teil-Übersetzungen (Deutsch -> Englisch) für alle 5 Seiten
  var EXACT_MAP = {
    'Start': 'Home',
    '🏆 Rangliste': '🏆 Leaderboard',
    '⚡ Download': '⚡ Download',
    '⚙️ Systeme': '⚙️ Systems',
    '📜 Lore': '📜 Lore',
    'Browser': 'Browser',
    'Browser-Beta': 'Browser',
    'Userpanel': 'Userpanel',
    'Account': 'Account',
    'Startseite & Userpanel': 'Home & Userpanel',
    'Ruhmeshalle (Rangliste)': 'Hall of Fame (Leaderboard)',
    'PC-Client Download': 'PC Client Download',
    'Spielsysteme & Galerie': 'Game Systems & Gallery',
    'Komplette Lore & Klassen': 'Complete Lore & Classes',
    'Zum Userpanel': 'Open Userpanel',
    'Browser-Beta starten': 'Launch Browser Beta',
    'AERYNDOR LIVE TELEMETRIE': 'AERYNDOR LIVE TELEMETRY',
    'Aeryndor ist Online': 'Aeryndor is Online',
    'Alle Welten-Knotenpunkte, das Auktionshaus und die Instanz-Server laufen stabil im Echtzeit-Synchronisationsmodus.':
      'All world nodes, the auction house, and instance servers are running stably in real-time synchronization mode.',
    'Status': 'Status',
    'Online': 'Online',
    'Helden / Welt': 'Heroes / World',
    'Server-Latenz': 'Server Latency',
    'Lade Paket herunter…': 'Downloading package…',
    'Status prüfen': 'Check Status',
    'DEINE LEGENDE BEGINNT': 'YOUR LEGEND BEGINS',
    'AERYNDOR USERPANEL': 'AERYNDOR USERPANEL',
    'Account-Verwaltung, Helden & Schatzkammer': 'Account Management, Heroes & Treasury',
    'Einloggen': 'Sign In',
    'Registrieren (+250 Coins)': 'Register (+250 Coins)',
    'Melde dich mit deinem Account an, um deine Charaktere und Drachenmünzen zu verwalten.':
      'Sign in with your account to manage your characters and Dragon Coins.',
    'Account-Name': 'Account Name',
    'Passwort': 'Password',
    'Bitte gib einen gültigen Account-Namen ein (mind. 3 Zeichen).':
      'Please enter a valid account name (min. 3 characters).',
    'Bitte gib dein Passwort ein (mind. 4 Zeichen).':
      'Please enter your password (min. 4 characters).',
    'Im Userpanel anmelden': 'Sign in to Userpanel',
    '+250 DRACHENMÜNZEN STARTBONUS': '+250 DRAGON COINS STARTER BONUS',
    'Gültig für den PC-Client & die Browser-Beta': 'Valid for both the PC Client & Browser Beta',
    'Wunsch-Accountname (3–24 Zeichen)': 'Desired Account Name (3–24 chars)',
    '3–24 Zeichen (nur Buchstaben, Zahlen, _ oder - erlaubt).':
      '3–24 characters (only letters, numbers, _ or - allowed).',
    'Passwort (mind. 4 Zeichen)': 'Password (min. 4 chars)',
    'Passwort muss mindestens 4 Zeichen lang sein.': 'Password must be at least 4 characters long.',
    'Passwort bestätigen': 'Confirm Password',
    'Die beiden Passwörter stimmen nicht überein.': 'The two passwords do not match.',
    'Kostenlos registrieren (+250 Coins)': 'Register for free (+250 Coins)',
    'Account verifiziert • Bereit für PC-Client & Browser': 'Account verified • Ready for PC Client & Browser',
    'Drachenmünzen': 'Dragon Coins',
    'Im Browser spielen': 'Play in Browser',
    'Aktualisieren': 'Refresh',
    'Ausloggen': 'Log Out',
    'Deine Helden auf Aeryndor': 'Your Heroes on Aeryndor',
    'AERYNDOR TREASURY': 'AERYNDOR TREASURY',
    'Drachenmünzen & Paket-Einlösung': 'Dragon Coins & Package Redemption',
    'Lade Drachenmünzen auf oder löse sie direkt für einen deiner Charaktere gegen Yang-Goldschätze oder Seelensplitter ein.':
      'Top up Dragon Coins or redeem them directly for one of your characters in exchange for Yang gold treasures or Soul Shards.',
    '🪙 Drachenmünzen aufladen (Sofort-Gutschrift)': '🪙 Top Up Dragon Coins (Instant Credit)',
    'Wähle ein Paket, um dein Account-Guthaben sofort aufzuladen:':
      'Choose a package to top up your account balance immediately:',
    '500 + 50 Bonus-Coins': '500 + 50 Bonus Coins',
    '1.500 + 250 Bonus-Coins': '1,500 + 250 Bonus Coins',
    '3.500 + 750 Bonus-Coins': '3,500 + 750 Bonus Coins',
    '4,99 € (Sofort-Test)': '€4.99 (Instant Test)',
    '9,99 € (Sofort-Test)': '€9.99 (Instant Test)',
    '19,99 € (Sofort-Test)': '€19.99 (Instant Test)',
    '🎁 Ingame-Pakete direkt an Charakter senden': '🎁 Send In-Game Packages Directly to Character',
    'Wähle den Ziel-Charakter aus, der das Paket sofort im Spiel erhalten soll:':
      'Select the target character who should receive the package immediately in-game:',
    'Ziel-Charakter:': 'Target Character:',
    '-- Bitte erst Charakter im Spiel erstellen --': '-- Please create a character in-game first --',
    '💰 500.000 Yang Schatztruhe': '💰 500,000 Yang Treasure Chest',
    'Wird sofort dem Goldbeutel deines ausgewählten Helden gutgeschrieben.':
      'Credited immediately to the gold pouch of your selected hero.',
    '🔮 50x Reine Seelensplitter': '🔮 50x Pure Soul Shards',
    'Edle Seelensplitter für das Schmieden und Veredeln deiner Ausrüstung.':
      'Precious Soul Shards for forging and upgrading your equipment.',
    '👑 2.000.000 Yang Goldbarren': '👑 2,000,000 Yang Gold Bullion',
    'Kaiserlicher Goldschatz direkt auf deinen ausgewählten Charakter.':
      'Imperial gold treasure sent directly to your selected character.',
    'Einlösen': 'Redeem',
    '© 2026 AERYNDOR: Legacy of the Monoliths – Das Vermächtnis der Monolithen.':
      '© 2026 AERYNDOR: Legacy of the Monoliths – Official MMORPG.',

    // Rangliste (/rangliste)
    'Ruhmeshalle': 'Hall of Fame',
    'LIVE SERVER-DATENBANK': 'LIVE SERVER DATABASE',
    'Ruhmeshalle von Aeryndor': 'Hall of Fame of Aeryndor',
    'Alle Helden aus Kaeryu und Seiryu werden live aus der Aeryndor-Datenbank synchronisiert.':
      'All heroes from Kaeryu and Seiryu are synchronized live from the Aeryndor database.',
    '🔄 Jetzt aktualisieren': '🔄 Refresh Now',
    '🏰 Zur Startseite': '🏰 Back to Home',
    'RANGLISTE & RUHMESHALLE': 'LEADERBOARD & HALL OF FAME',
    'Die stärksten Klingenwächter, Schattenjäger, Runenmagier und Seelenweber aus Kaeryu und Seiryu – live sortiert nach Erfahrungsstufe, errungenem Ruhm und Goldschatz.':
      'The strongest Blade Wardens, Shadow Hunters, Rune Mages, and Soul Weavers from Kaeryu and Seiryu – sorted live by level, renown, and gold treasure.',
    'Registrierte Accounts': 'Registered Accounts',
    'Erstellte Helden': 'Created Heroes',
    'Höchstes Level': 'Highest Level',
    'Helden Online': 'Heroes Online',
    'Aktive Rissmonolithen': 'Active Rift Monoliths',
    '🏆 Top Helden-Chronik': '🏆 Top Heroes Chronicle',
    'Filtere nach Klasse oder suche gezielt nach einem Helden oder einer Stadt (Kaeryu / Seiryu)':
      'Filter by class or search specifically for a hero or city (Kaeryu / Seiryu)',
    'Rangliste aktualisieren': 'Refresh Leaderboard',
    'Alle Klassen': 'All Classes',
    '⚔️ Klingenwächter': '⚔️ Blade Warden',
    '🗡️ Schattenjäger': '🗡️ Shadow Hunter',
    '🔮 Runenmagier': '🔮 Rune Mage',
    '✨ Seelenweber': '✨ Soul Weaver',
    'Rang': 'Rank',
    'Held': 'Hero',
    'Stadt': 'City',
    'Klasse': 'Class',
    'Stufe': 'Level',
    'Rangpunkte': 'Rank Points',
    'Ruhm': 'Rank Points',
    'Goldschatz': 'Gold Treasure',
    'Lade Helden-Chronik vom Server…': 'Loading hero chronicle from server…',

    // Download (/download)
    'Aeryndor Engine': 'Aeryndor Engine',
    'THREE.JS & STANDALONE ENGINE': 'THREE.JS & STANDALONE ENGINE',
    'Download & Echtzeit-Stream': 'Download & Real-Time Stream',
    'Starte unten den Download des PC-Client Komplettpakets (.ZIP) oder des Smart-Launchers (.EXE). Der Live-Fortschritt wird direkt hier gestreamt.':
      'Start the download of the PC Client Complete Package (.ZIP) or Smart Launcher (.EXE) below. Live progress is streamed right here.',
    '🌐 Direkt im Browser testen': '🌐 Play in Browser Now',
    'DOWNLOAD & 3D-ENGINE': 'DOWNLOAD & 3D ENGINE',
    'Wähle deine Spiel-Edition': 'Choose Your Game Edition',
    'Komplettpaket (.ZIP) herunterladen': 'Download Complete Package (.ZIP)',
    'Inkl. Native Client, Smart-Launcher & Engine.pak Vault': 'Incl. Native Client, Smart Launcher & Engine.pak Vault',
    'Nur Smart-Launcher (.EXE) laden': 'Download Smart Launcher (.EXE) Only',
    'Kompakter Auto-Updater & Paket-Downloader': 'Compact Auto-Updater & Package Downloader',
    '🔒 SHA-256 Signiert & Verifiziert': '🔒 SHA-256 Signed & Verified',
    '📦 Engine.pak Vault v2.4': '📦 Engine.pak Vault v2.4',
    '⚡ Unlimitierte 144+ FPS': '⚡ Unlimited 144+ FPS',
    '🖥️ Systemanforderungen (Windows & WebGL2)': '🖥️ System Requirements (Windows & WebGL2)',
    'Betriebssystem': 'Operating System',
    'Windows 10 / Windows 11 (64-Bit)': 'Windows 10 / Windows 11 (64-Bit)',
    '3D-Grafik-API': '3D Graphics API',
    'Three.js WebGL 2.0 / DirectX 12 Backend': 'Three.js WebGL 2.0 / DirectX 12 Backend',
    'Prozessor (CPU)': 'Processor (CPU)',
    'Intel Core i5 / AMD Ryzen 5 oder höher': 'Intel Core i5 / AMD Ryzen 5 or higher',
    'Grafikkarte (GPU)': 'Graphics Card (GPU)',
    'NVIDIA GTX 1060 / AMD RX 580 (mind. 4 GB VRAM)': 'NVIDIA GTX 1060 / AMD RX 580 (min. 4 GB VRAM)',
    'Arbeitsspeicher': 'Memory (RAM)',
    '8 GB RAM (16 GB für Ultra-Schatten & Partikel)': '8 GB RAM (16 GB for Ultra Shadows & Particles)',
    'Netzwerk': 'Network',
    'Breitband-Verbindung (Echtzeit-WebSocket)': 'Broadband Connection (Real-Time WebSocket)',
    'Account & +250 Coins sichern': 'Create Account & Claim +250 Coins',
    'Client entpacken oder Launcher starten': 'Unpack Client or Launch Updater',
    'Einloggen & Rissmonolithen jagen': 'Sign In & Hunt Rift Monoliths',
    'UNTER DER HAUBE VON AERYNDOR': 'UNDER THE HOOD OF AERYNDOR',
    'Die Three.js 3D-Engine & Client-Architektur': 'The Three.js 3D Engine & Client Architecture',
    '1. Three.js 3D-Rendering, PBR-Shading & Custom GLSL-Shader': '1. Three.js 3D Rendering, PBR Shading & Custom GLSL Shaders',
    '2. Skinned-Mesh Charakter-Pipeline & Echtzeit-Ausrüstung': '2. Skinned-Mesh Character Pipeline & Real-Time Gear',
    '3. Native Windows-Runtime & Verschlüsselter Asset-Vault': '3. Native Windows Runtime & Encrypted Asset Vault',
    '4. Autoritativer Echtzeit-Server & Cross-Play-Synchronisation': '4. Authoritative Real-Time Server & Cross-Play Sync',

    // Systeme (/systeme)
    'Aeryndor Systeme': 'Aeryndor Systems',
    'AERYNDOR ENGINE & GAMEPLAY': 'AERYNDOR ENGINE & GAMEPLAY',
    'Spielsysteme & Feature-Vorstellung': 'Game Systems & Feature Showcase',
    'Entdecke alle Kernmechaniken von Aeryndor: Rissmonolithen, Action-Kampf, Schmiede, Begleiter, HUD und das erweiterbare Bilder-Archiv.':
      'Discover all core mechanics of Aeryndor: Rift Monoliths, action combat, forging, companions, HUD, and screenshot gallery.',
    '📜 Zur Lore-Chronik': '📜 Explore Lore Chronicle',
    'SPIELSYSTEME & FEATURES': 'GAME SYSTEMS & FEATURES',
    '✨ Alle Systeme (8)': '✨ All Systems (8)',
    '⚔️ Kampf & Rissmonolithen': '⚔️ Combat & Rift Monoliths',
    '⚒️ Schmiede, Items & Skills': '⚒️ Forge, Items & Skills',
    '🐾 Pets, Mounts & Welt': '🐾 Pets, Mounts & World',
    '🖥️ Interface & Technik': '🖥️ Interface & Tech',
    '🔍 Bild vergrößern': '🔍 Enlarge Image',
    '⚔️ Kern-System': '⚔️ Core System',
    '1. Das Rissmonolithen-Netzwerk & 5 Seltenheiten': '1. The Rift Monolith Network & 5 Rarities',
    '🖥️ Interface & HUD': '🖥️ Interface & HUD',
    '2. Maßgeschneidertes Fantasy-HUD & Echtzeit-Telemetrie': '2. Custom Fantasy HUD & Real-Time Telemetry',
    '⚒️ Charakter-Entwicklung': '⚒️ Character Progression',
    '3. Fertigkeiten, Runenmagie & Meisterschaften': '3. Skills, Rune Magic & Masteries',
    '⚒️ Schmiede & Beute': '⚒️ Forge & Loot',
    '4. Schmiedekunst (+0 bis +9) & Reine Seelensplitter': '4. Blacksmithing (+0 to +9) & Pure Soul Shards',
    '🐾 Pets & Mounts': '🐾 Pets & Mounts',
    '5. Reittier-Kampf (Mounts) & Treue Begleiter (Pets)': '5. Mounted Combat & Loyal Companions (Pets)',
    '⚔️ Bosse & Beute-Info': '⚔️ Bosses & Drop Info',
    '6. Weltbosse, Ziel-Telemetrie & Drop-Vorschau': '6. World Bosses, Target Telemetry & Drop Preview',
    '⚔️ 4 Klassen • 8 Pfade': '⚔️ 4 Classes • 8 Paths',
    '7. Treffer-Feedback, Trefferzonen & 8 Heldenmodelle': '7. Hit Feedback, Hitboxes & 8 Hero Models',
    '🌍 Open World & Cloud': '🌍 Open World & Cloud',
    '8. Zusammenhängende Open World & Nahtloser Account': '8. Seamless Open World & Unified Account',

    // Lore (/lore)
    'Die Geschichte': 'The Story',
    'Aeryndor Chronik': 'Aeryndor Chronicle',
    'DAS VERMÄCHTNIS DER MONOLITHEN': 'LEGACY OF THE MONOLITHS',
    'Die Archive von Seiryu & Kaeryu': 'The Archives of Seiryu & Kaeryu',
    'Du liest die vollständige Hintergrundgeschichte von Aeryndor (Kapitel I bis VIII • Level 1 bis 90).':
      'You are reading the complete background story of Aeryndor (Chapters I to VIII • Level 1 to 90).',
    '⚙️ Zu den Spielsystemen': '⚙️ View Game Systems',
    'LORE, WELT & KLASSEN': 'LORE, WORLD & CLASSES',
    'Das Erwachen uralter Rissmonolithen, das Zerbrechen der Grenzen zwischen den Dimensionen und das vergessene Vermächtnis einer untergegangenen Zivilisation – die gesamte Hintergrundgeschichte der offenen Welt von Aeryndor.':
      'The awakening of ancient Rift Monoliths, the shattering of boundaries between dimensions, and the forgotten legacy of a lost civilization – the complete lore of the open world of Aeryndor.',
    '1. Bedeutung des Namens': '1. Meaning of the Name',
    '2–4. Die Ersten Hüter & Der Erste Bruch': '2–4. The First Guardians & The First Fracture',
    '5. Das Erwachen': '5. The Awakening',
    '6–8. Städte, Weol & See Sohan': '6–8. Cities, Weol & Lake Sohan',
    '9–10. 18 Rissmonolithen & 5 Seltenheiten': '9–10. 18 Rift Monoliths & 5 Rarities',
    '11. Die 4 Klassen': '11. The 4 Classes',
    '12. Story Lv. 1–90 (Kapitel I–VIII)': '12. Story Lv. 1–90 (Chapters I–VIII)',
    '13–17. Botschaft & Zukunft': '13–17. Message & Future',
    '♂️ Männliche Helden': '♂️ Male Heroes',
    '♀️ Weibliche Heldinnen': '♀️ Female Heroines',
    '🛡️ Start Ausrüstung': '🛡️ Starter Armor',
    '⚔️ Charaktere': '⚔️ Base Characters',
    'Klingenwächter': 'Blade Warden',
    'Schattenjäger': 'Shadow Hunter',
    'Runenkrieger / Runenmagier': 'Rune Warrior / Rune Mage',
    'Seelenweber': 'Soul Weaver',
    'Angriff': 'Attack',
    'Abwehr': 'Defense',
    'Magie': 'Magic',
    'Tempo': 'Speed',
    'Support': 'Support'
  };

  // Längere Absatz-Übersetzungen über Teilstring-Erkennung
  var SUBSTRING_MAP = [
    [
      'In der Welt von Aeryndor erwachen uralte Rissmonolithen einer vergessenen Zivilisation',
      'In the world of Aeryndor, ancient Rift Monoliths of a forgotten civilization awaken and tear open dangerous rifts between dimensions. Choose your allegiance between Kaeryu and Seiryu, master one of four classes, and face the 18 Rift Monoliths all the way to the Origin Rift.'
    ],
    [
      'Lade den nativen Windows PC-Client mit verschlüsseltem Asset-Vault für unlimitierte 144+ FPS herunter',
      'Download the native Windows PC Client with encrypted Asset Vault for unlimited 144+ FPS, or jump right in via our highly optimized Three.js WebGL2 3D Engine directly in your browser.'
    ],
    [
      'Hier findest du alle zentralen Systeme von',
      'Explore all core game systems of Aeryndor: Legacy of the Monoliths explained in detail and illustrated with screenshots. Click any image to view it in full screen.'
    ],
    [
      'Das Ingame-Interface von Aeryndor kombiniert edle gold-metallische Ornamentik',
      'The in-game interface of Aeryndor combines noble gold-metallic ornamentation with crystal-clear clarity. The high-resolution minimap displays active Rift Monoliths, NPCs, and party members in real time, while status orbs, buff timers, and customizable skill slots give you full control in combat.'
    ],
    [
      'Überall in der offenen Welt von Aeryndor schlagen',
      'Across the open world of Aeryndor, 18 distinct Rift Monoliths (Level 5 to 90) strike the earth. When attacked, they summon waves of dimensional creatures. Every monolith can appear in one of five rarities: Normal (White), Unstable (Teal), Corrupted (Purple), Ancient (Orange), and Legendary (Gold). Four Unstable Rift Monoliths are guaranteed to be active at all times (15-min respawn cycle).'
    ]
  ];

  function injectCornerLanguageSwitcher() {
    if (document.getElementById('corner-lang-switcher')) return;

    var style = document.createElement('style');
    style.textContent =
      '.corner-lang-switcher {' +
      '  position: fixed;' +
      '  top: 14px;' +
      '  left: 16px;' +
      '  z-index: 1200;' +
      '  display: inline-flex;' +
      '  align-items: center;' +
      '  gap: 6px;' +
      '  padding: 5px 8px;' +
      '  border-radius: 999px;' +
      '  background: rgba(8, 12, 22, 0.30);' +
      '  backdrop-filter: blur(12px) saturate(160%);' +
      '  -webkit-backdrop-filter: blur(12px) saturate(160%);' +
      '  border: 1px solid rgba(216, 178, 92, 0.44);' +
      '  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.22);' +
      '  pointer-events: auto;' +
      '}' +
      '.lang-flag-btn {' +
      '  display: inline-flex;' +
      '  align-items: center;' +
      '  justify-content: center;' +
      '  gap: 5px;' +
      '  padding: 4px 8px;' +
      '  border-radius: 999px;' +
      '  border: 1px solid transparent;' +
      '  background: transparent;' +
      '  color: #cbd5e1;' +
      '  font-size: 0.72rem;' +
      '  font-weight: 800;' +
      '  letter-spacing: 0.04em;' +
      '  cursor: pointer;' +
      '  transition: all 0.2s ease;' +
      '  opacity: 0.68;' +
      '}' +
      '.lang-flag-btn:hover {' +
      '  opacity: 1;' +
      '  background: rgba(255, 255, 255, 0.06);' +
      '}' +
      '.lang-flag-btn.active {' +
      '  opacity: 1;' +
      '  color: #090c14;' +
      '  background: linear-gradient(135deg, #f5df9e 0%, #d8b25c 100%);' +
      '  border-color: rgba(255, 244, 210, 0.75);' +
      '  box-shadow: 0 3px 10px rgba(216, 178, 92, 0.35);' +
      '}' +
      '.lang-flag-svg {' +
      '  width: 18px;' +
      '  height: 13px;' +
      '  border-radius: 3px;' +
      '  object-fit: cover;' +
      '  box-shadow: 0 1px 3px rgba(0,0,0,0.45);' +
      '  display: block;' +
      '}' +
      '@media (max-width: 1420px) {' +
      '  .corner-lang-switcher { top: auto; bottom: 16px; left: 16px; }' +
      '}' +
      '.corner-bgm-toggle {' +
      '  position: fixed;' +
      '  top: 14px;' +
      '  right: 16px;' +
      '  z-index: 1200;' +
      '  width: 38px;' +
      '  height: 38px;' +
      '  border-radius: 999px;' +
      '  display: inline-flex;' +
      '  align-items: center;' +
      '  justify-content: center;' +
      '  background: rgba(8, 12, 22, 0.32);' +
      '  backdrop-filter: blur(12px) saturate(160%);' +
      '  -webkit-backdrop-filter: blur(12px) saturate(160%);' +
      '  border: 1px solid rgba(216, 178, 92, 0.44);' +
      '  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.22);' +
      '  color: #f5df9e;' +
      '  cursor: pointer;' +
      '  opacity: 0.76;' +
      '  transition: all 0.2s ease;' +
      '  pointer-events: auto;' +
      '}' +
      '.corner-bgm-toggle:hover {' +
      '  opacity: 1;' +
      '  transform: translateY(-1px);' +
      '  background: rgba(15, 23, 42, 0.55);' +
      '  border-color: rgba(245, 223, 158, 0.78);' +
      '  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.48), 0 0 14px rgba(216, 178, 92, 0.32);' +
      '}' +
      '.corner-bgm-toggle.is-muted {' +
      '  color: #94a3b8;' +
      '  border-color: rgba(148, 163, 184, 0.38);' +
      '}' +
      '@media (max-width: 1420px) {' +
      '  .corner-bgm-toggle { top: 14px; right: 12px; width: 34px; height: 34px; }' +
      '}';
    document.head.appendChild(style);

    var box = document.createElement('div');
    box.className = 'corner-lang-switcher';
    box.id = 'corner-lang-switcher';
    box.setAttribute('aria-label', 'Sprache wählen / Select language');

    box.innerHTML =
      '<button type="button" class="lang-flag-btn active" id="btn-lang-de" onclick="window.setSiteLanguage(\'de\')" title="Deutsch">' +
        '<svg class="lang-flag-svg" viewBox="0 0 5 3" aria-hidden="true">' +
          '<rect width="5" height="1" y="0" fill="#000"/>' +
          '<rect width="5" height="1" y="1" fill="#D00"/>' +
          '<rect width="5" height="1" y="2" fill="#FFCE00"/>' +
        '</svg>' +
        '<span>DE</span>' +
      '</button>' +
      '<button type="button" class="lang-flag-btn" id="btn-lang-en" onclick="window.setSiteLanguage(\'en\')" title="English">' +
        '<svg class="lang-flag-svg" viewBox="0 0 60 30" aria-hidden="true">' +
          '<clipPath id="uk-clip"><path d="M0,0 v30 h60 v-30 z"/></clipPath>' +
          '<path d="M0,0 v30 h60 v-30 z" fill="#012169"/>' +
          '<path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6" clip-path="url(#uk-clip)"/>' +
          '<path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" stroke-width="4" clip-path="url(#uk-clip)"/>' +
          '<path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/>' +
          '<path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/>' +
        '</svg>' +
        '<span>EN</span>' +
      '</button>';

    document.body.appendChild(box);
    injectHomepageBgmToggle();
  }

  var hpBgmAudio = null;
  var hpBgmMuted = false;

  function renderBgmToggleIcon(btn, muted) {
    if (!btn) return;
    btn.classList.toggle('is-muted', Boolean(muted));
    btn.setAttribute('title', muted ? 'Hintergrundmusik stummgeschaltet (Klicken zum Einschalten)' : 'Hintergrundmusik aktiv (Klicken zum Stummschalten)');
    btn.setAttribute('aria-label', muted ? 'Musik einschalten' : 'Musik stummschalten');
    if (muted) {
      btn.innerHTML =
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
          '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>' +
          '<line x1="23" y1="9" x2="17" y2="15"></line>' +
          '<line x1="17" y1="9" x2="23" y2="15"></line>' +
        '</svg>';
    } else {
      btn.innerHTML =
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
          '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>' +
          '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>' +
          '<path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>' +
        '</svg>';
    }
  }

  function injectHomepageBgmToggle() {
    if (document.getElementById('corner-bgm-mute-btn')) return;
    try {
      hpBgmMuted = localStorage.getItem('aeryndor_hp_bgm_muted') === '1';
    } catch (_e) {
      hpBgmMuted = false;
    }

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'corner-bgm-mute-btn';
    btn.className = 'corner-bgm-toggle';
    renderBgmToggleIcon(btn, hpBgmMuted);
    document.body.appendChild(btn);

    try {
      hpBgmAudio = new Audio('/assets/bgm/login.mp3');
      hpBgmAudio.loop = true;
      hpBgmAudio.preload = 'auto';
      hpBgmAudio.volume = 0.36;
      hpBgmAudio.muted = hpBgmMuted;
    } catch (_err) {
      return;
    }

    function tryPlayHpBgm() {
      if (!hpBgmAudio || hpBgmMuted) return;
      var p = hpBgmAudio.play();
      if (p && typeof p.catch === 'function') {
        p.catch(function () {});
      }
    }

    btn.addEventListener('click', function (ev) {
      ev.stopPropagation();
      hpBgmMuted = !hpBgmMuted;
      try {
        localStorage.setItem('aeryndor_hp_bgm_muted', hpBgmMuted ? '1' : '0');
      } catch (_e) {}
      renderBgmToggleIcon(btn, hpBgmMuted);
      if (!hpBgmAudio) return;
      hpBgmAudio.muted = hpBgmMuted;
      if (hpBgmMuted) {
        try { hpBgmAudio.pause(); } catch (_p) {}
      } else {
        tryPlayHpBgm();
      }
    });

    if (!hpBgmMuted) {
      tryPlayHpBgm();
    }

    var unlockEvents = ['pointerdown', 'keydown', 'touchstart', 'click'];
    function onFirstInteract() {
      if (!hpBgmMuted && hpBgmAudio && hpBgmAudio.paused) {
        tryPlayHpBgm();
      }
      if (hpBgmAudio && !hpBgmAudio.paused) {
        unlockEvents.forEach(function (evName) {
          window.removeEventListener(evName, onFirstInteract, true);
        });
      }
    }
    unlockEvents.forEach(function (evName) {
      window.addEventListener(evName, onFirstInteract, true);
    });
  }

  function snapshotDOM() {
    if (initialized) return;
    initialized = true;

    // 1. Alle relevanten Elemente für Ganzsatz-/Exakt-Übersetzung erfassen
    var selectors = 'a, button, h1, h2, h3, h4, p, span, label, th, td, option, .di-exp-body, .di-exp-kicker, .di-exp-main, .lbl, .t1, .t2, .btn-main, .btn-sub, .k, .v, .clean-auth-hint';
    document.querySelectorAll(selectors).forEach(function (el) {
      // Nur Blatt-Elemente oder Absätze ohne komplexe Kind-Inputs
      if (el.querySelector('input, select, textarea, button, svg, img')) return;
      var txt = (el.textContent || '').replace(/\s+/g, ' ').trim();
      if (!txt) return;
      originalNodes.push({ el: el, deText: txt, deHtml: el.innerHTML });
    });

    // 2. Placeholders erfassen
    document.querySelectorAll('input[placeholder]').forEach(function (inp) {
      var ph = inp.getAttribute('placeholder');
      if (ph && ph.trim().length > 1) {
        originalPlaceholders.push({ el: inp, de: ph });
      }
    });

    // 3. Title-Attribute
    document.querySelectorAll('[title]').forEach(function (el) {
      var t = el.getAttribute('title');
      if (t) originalTitles.push({ el: el, de: t });
    });
  }

  window.setSiteLanguage = function (lang) {
    var target = lang === 'en' ? 'en' : 'de';
    snapshotDOM();

    document.documentElement.setAttribute('lang', target);
    var btnDe = document.getElementById('btn-lang-de');
    var btnEn = document.getElementById('btn-lang-en');
    if (btnDe) btnDe.classList.toggle('active', target === 'de');
    if (btnEn) btnEn.classList.toggle('active', target === 'en');

    try { localStorage.setItem(STORAGE_KEY, target); } catch (_e) {}

    originalNodes.forEach(function (item) {
      if (target === 'de') {
        item.el.innerHTML = item.deHtml;
        return;
      }
      var de = item.deText;
      if (EXACT_MAP[de]) {
        item.el.textContent = EXACT_MAP[de];
        return;
      }
      for (var i = 0; i < SUBSTRING_MAP.length; i++) {
        if (de.indexOf(SUBSTRING_MAP[i][0]) !== -1) {
          item.el.textContent = SUBSTRING_MAP[i][1];
          return;
        }
      }
    });

    originalPlaceholders.forEach(function (item) {
      if (target === 'de') {
        item.el.setAttribute('placeholder', item.de);
      } else if (item.de.indexOf('Held oder Stadt suchen') !== -1) {
        item.el.setAttribute('placeholder', 'Search hero or city…');
      }
    });
  };

  function bootLanguageSwitcher() {
    injectCornerLanguageSwitcher();
    snapshotDOM();
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved === 'en') window.setSiteLanguage('en');
    } catch (_e) {}

    // Spotlight-Maus-Effekt & Gold-Funken-Partikel-Animation (#ember-canvas) auf allen Seiten aktivieren
    document.querySelectorAll('.spotlight-card').forEach(function (card) {
      if (card.getAttribute('data-spotlight-bound')) return;
      card.setAttribute('data-spotlight-bound', '1');
      card.addEventListener('mousemove', function (ev) {
        var rect = card.getBoundingClientRect();
        card.style.setProperty('--mouse-x', (ev.clientX - rect.left) + 'px');
        card.style.setProperty('--mouse-y', (ev.clientY - rect.top) + 'px');
      });
    });

    var canvas = document.getElementById('ember-canvas');
    if (canvas && canvas.getContext && !canvas.getAttribute('data-ember-running')) {
      canvas.setAttribute('data-ember-running', '1');
      var ctx = canvas.getContext('2d');
      var w = (canvas.width = window.innerWidth);
      var h = (canvas.height = window.innerHeight);
      window.addEventListener('resize', function () {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
      }, { passive: true });
      var embers = Array.from({ length: 52 }, function () {
        return {
          x: Math.random() * w,
          y: Math.random() * h,
          r: Math.random() * 2.1 + 0.8,
          vx: (Math.random() - 0.5) * 0.28,
          vy: -Math.random() * 0.52 - 0.16,
          a: Math.random() * 0.55 + 0.25,
          phase: Math.random() * Math.PI * 2,
          pulseSpeed: 0.002 + Math.random() * 0.0025,
          swayAmp: 0.18 + Math.random() * 0.28
        };
      });
      (function drawEmbers(now) {
        var t = now || performance.now();
        ctx.clearRect(0, 0, w, h);
        for (var i = 0; i < embers.length; i++) {
          var p = embers[i];
          p.x += p.vx + Math.sin(t * 0.0012 + p.phase) * p.swayAmp;
          p.y += p.vy;
          if (p.y < -12) { p.y = h + 12; p.x = Math.random() * w; }
          if (p.x < -12) p.x = w + 12;
          if (p.x > w + 12) p.x = -12;
          var pulse = 0.65 + 0.35 * Math.sin(t * p.pulseSpeed + p.phase);
          var alpha = Math.min(0.95, p.a * pulse);
          var grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 3.4);
          grad.addColorStop(0, 'rgba(255, 248, 220, ' + alpha + ')');
          grad.addColorStop(0.38, 'rgba(245, 208, 115, ' + (alpha * 0.65) + ')');
          grad.addColorStop(1, 'rgba(216, 162, 58, 0)');
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.r * 3.4, 0, Math.PI * 2);
          ctx.fillStyle = grad;
          ctx.fill();
        }
        requestAnimationFrame(drawEmbers);
      })();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootLanguageSwitcher);
  } else {
    bootLanguageSwitcher();
  }
})();
