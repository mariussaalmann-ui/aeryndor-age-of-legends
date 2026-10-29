// ============================================================================
// AERYNDOR: LEGACY OF THE MONOLITHS – Item-, Waffen- & Skill-Icon-Renderer
// ============================================================================

const SVG_ICONS = {
  // WEAPONS
  weapon_broadsword: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bs_blade" x1="12" y1="52" x2="54" y2="10" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#94a3b8"/>
          <stop offset="50%" stop-color="#e2e8f0"/>
          <stop offset="100%" stop-color="#cbd5e1"/>
        </linearGradient>
      </defs>
      <path d="M46 10L54 8L52 16L25 43L19 37L46 10Z" fill="url(#bs_blade)" stroke="#334155" stroke-width="2"/>
      <path d="M49 11L22 38" stroke="#f8fafc" stroke-width="1.5" stroke-linecap="round"/>
      <path d="M14 34L28 48L25 51L11 37L14 34Z" fill="#d97706" stroke="#78350f" stroke-width="1.5"/>
      <path d="M18 44L11 51L13 53L20 46" fill="#78350f" stroke="#451a03" stroke-width="2"/>
      <circle cx="10" cy="54" r="3.5" fill="#f59e0b" stroke="#78350f" stroke-width="1.5"/>
    </svg>`,

  weapon_silversword: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="ss_blade" x1="14" y1="50" x2="55" y2="9" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#bae6fd"/>
          <stop offset="50%" stop-color="#f8fafc"/>
          <stop offset="100%" stop-color="#38bdf8"/>
        </linearGradient>
      </defs>
      <path d="M47 9L56 7L54 16L25 45L18 38L47 9Z" fill="url(#ss_blade)" stroke="#0284c7" stroke-width="2"/>
      <path d="M13 33L30 50L26 53L10 37L13 33Z" fill="#eab308" stroke="#854d0e" stroke-width="1.5"/>
      <circle cx="21" cy="42" r="2.5" fill="#38bdf8"/>
      <path d="M17 45L10 52L13 55L20 48" fill="#1e3a8a" stroke="#172554" stroke-width="2"/>
      <circle cx="9.5" cy="54.5" r="3.5" fill="#facc15" stroke="#854d0e" stroke-width="1.5"/>
    </svg>`,

  // Mondsplitterklinge (MSK - Vollmondschwert / VMS Design!)
  weapon_msk: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="msk_grad" x1="10" y1="54" x2="56" y2="8" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#38bdf8"/>
          <stop offset="45%" stop-color="#f1f5f9"/>
          <stop offset="80%" stop-color="#e0f2fe"/>
          <stop offset="100%" stop-color="#7dd3fc"/>
        </linearGradient>
        <filter id="msk_glow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#38bdf8" flood-opacity="0.85"/>
        </filter>
      </defs>
      <path filter="url(#msk_glow)" d="M54 8C42 10 28 21 19 36L26 43C34 33 41 28 38 23C43 21 48 18 54 8Z" fill="url(#msk_grad)" stroke="#0ea5e9" stroke-width="1.8"/>
      <circle cx="28" cy="34" r="4" fill="#1e1b4b" stroke="#38bdf8" stroke-width="1.5"/>
      <circle cx="28" cy="34" r="1.8" fill="#60a5fa"/>
      <path d="M14 33C19 36 26 43 29 48L25 51C21 46 16 41 11 37L14 33Z" fill="#f59e0b" stroke="#92400e" stroke-width="1.5"/>
      <path d="M18 44L10 52L13 55L21 47" fill="#312e81" stroke="#1e1b4b" stroke-width="2"/>
      <circle cx="9.5" cy="54.5" r="4" fill="#38bdf8" stroke="#f59e0b" stroke-width="1.5"/>
    </svg>`,

  // Rotstahlbrecher (RSB - Roteisenklinge / REK Design!)
  weapon_rsb: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="rsb_grad" x1="12" y1="52" x2="56" y2="8" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#7f1d1d"/>
          <stop offset="45%" stop-color="#ef4444"/>
          <stop offset="75%" stop-color="#fca5a5"/>
          <stop offset="100%" stop-color="#dc2626"/>
        </linearGradient>
        <filter id="rsb_glow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#ef4444" flood-opacity="0.8"/>
        </filter>
      </defs>
      <path filter="url(#rsb_glow)" d="M56 7L41 12L44 17L32 23L35 28L18 38L26 46L52 24L49 19L56 7Z" fill="url(#rsb_grad)" stroke="#991b1b" stroke-width="1.8"/>
      <path d="M14 34L30 50L26 53L11 38L14 34Z" fill="#d97706" stroke="#78350f" stroke-width="1.6"/>
      <path d="M19 45L8 56L11 59L22 48" fill="#450a0a" stroke="#991b1b" stroke-width="2.5"/>
      <circle cx="22" cy="42" r="2.8" fill="#fef08a"/>
    </svg>`,

  weapon_hornbow: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M16 10C38 12 50 26 50 48" stroke="#f59e0b" stroke-width="4.5" stroke-linecap="round"/>
      <path d="M16 10C34 14 46 28 50 48" stroke="#fef3c7" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="16" y1="11" x2="49" y2="48" stroke="#94a3b8" stroke-width="1.5"/>
      <line x1="18" y1="46" x2="47" y2="17" stroke="#10b981" stroke-width="2.5"/>
      <polygon points="51,13 43,16 48,21" fill="#34d399"/>
    </svg>`,

  weapon_bell: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="14" r="5" stroke="#f59e0b" stroke-width="2.5" fill="#1e1b4b"/>
      <path d="M20 42C20 26 24 20 32 20C40 20 44 26 44 42L49 48H15L20 42Z" fill="#f59e0b" stroke="#b45309" stroke-width="2"/>
      <circle cx="32" cy="34" r="5" fill="#38bdf8"/>
      <circle cx="32" cy="51" r="4.5" fill="#fde047" stroke="#92400e" stroke-width="1.5"/>
    </svg>`,

  // Seuchenzahn (SZ - Gift/Dämonenklinge)
  weapon_seuchenzahn: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="sz_grad" x1="12" y1="52" x2="55" y2="9" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#065f46"/>
          <stop offset="50%" stop-color="#10b981"/>
          <stop offset="100%" stop-color="#a7f3d0"/>
        </linearGradient>
        <filter id="sz_glow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="0" stdDeviation="3.5" flood-color="#10b981" flood-opacity="0.9"/>
        </filter>
      </defs>
      <path filter="url(#sz_glow)" d="M55 8L40 14L44 19L31 26L35 31L19 39L25 45L54 19L55 8Z" fill="url(#sz_grad)" stroke="#047857" stroke-width="1.8"/>
      <path d="M12 34L29 51L25 54L9 38L12 34Z" fill="#a855f7" stroke="#581c87" stroke-width="1.5"/>
      <circle cx="21" cy="43" r="3" fill="#34d399"/>
      <path d="M17 45L9 53L12 56L20 48" fill="#1e1b4b" stroke="#065f46" stroke-width="2"/>
    </svg>`,

  // Sternenreißer (Legendäre Endwaffe)
  weapon_sternenreisser: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="sr_grad" x1="10" y1="54" x2="56" y2="8" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#6366f1"/>
          <stop offset="45%" stop-color="#38bdf8"/>
          <stop offset="80%" stop-color="#f8fafc"/>
          <stop offset="100%" stop-color="#facc15"/>
        </linearGradient>
        <filter id="sr_glow" x="-25%" y="-25%" width="150%" height="150%">
          <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#38bdf8" flood-opacity="1"/>
        </filter>
      </defs>
      <path filter="url(#sr_glow)" d="M56 7L44 11L46 16L20 37L27 44L48 18L53 19L56 7Z" fill="url(#sr_grad)" stroke="#bae6fd" stroke-width="1.6"/>
      <polygon points="34,30 39,25 36,34 29,36" fill="#fde047"/>
      <path d="M11 32L32 53L27 56L8 37L11 32Z" fill="#f59e0b" stroke="#b45309" stroke-width="1.6"/>
      <circle cx="22" cy="42" r="4" fill="#38bdf8" stroke="#fef08a" stroke-width="1.5"/>
      <path d="M17 46L8 55L11 58L20 49" fill="#312e81" stroke="#f59e0b" stroke-width="2"/>
    </svg>`,

  // ARMORS
  armor_leather: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 12L10 20L15 30L20 26V52H44V26L49 30L54 20L44 12L37 17H27L20 12Z" fill="#92400e" stroke="#451a03" stroke-width="2"/>
      <path d="M26 17V52M38 17V52" stroke="#b45309" stroke-width="1.5"/>
      <rect x="20" y="38" width="24" height="5" fill="#d97706"/>
    </svg>`,

  armor_tiger: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M19 11L8 20L14 31L20 26V53H44V26L50 31L56 20L45 11L37 17H27L19 11Z" fill="#991b1b" stroke="#f59e0b" stroke-width="2"/>
      <path d="M24 24L32 32L40 24" stroke="#fbbf24" stroke-width="2"/>
      <circle cx="32" cy="30" r="4" fill="#f59e0b"/>
      <rect x="20" y="40" width="24" height="5" fill="#fbbf24"/>
    </svg>`,

  armor_dragon: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 10L7 19L13 31L20 26V53H44V26L51 31L57 19L46 10L37 16H27L18 10Z" fill="#b45309" stroke="#fde047" stroke-width="2"/>
      <polygon points="32,20 39,30 32,40 25,30" fill="#ef4444" stroke="#fef08a" stroke-width="1.5"/>
      <rect x="20" y="42" width="24" height="5" fill="#fde047"/>
    </svg>`,

  armor_blacksteel: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="bsa_glow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#38bdf8" flood-opacity="0.8"/>
        </filter>
      </defs>
      <path filter="url(#bsa_glow)" d="M17 10L6 18L13 31L20 26V54H44V26L51 31L58 18L47 10L37 16H27L17 10Z" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>
      <polygon points="32,19 40,30 32,41 24,30" fill="#0ea5e9" stroke="#bae6fd" stroke-width="1.5"/>
      <path d="M20 43H44" stroke="#38bdf8" stroke-width="3"/>
    </svg>`,

  // HELMETS
  helmet_iron: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M16 36C16 20 23 14 32 14C41 14 48 20 48 36V48H38V36H26V48H16V36Z" fill="#64748b" stroke="#cbd5e1" stroke-width="2"/>
      <line x1="32" y1="14" x2="32" y2="38" stroke="#e2e8f0" stroke-width="3"/>
    </svg>`,

  helmet_ghost: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M15 34C15 18 22 12 32 12C42 12 49 18 49 34L45 50H19L15 34Z" fill="#334155" stroke="#a855f7" stroke-width="2"/>
      <polygon points="22,30 29,33 23,36" fill="#38bdf8"/>
      <polygon points="42,30 35,33 41,36" fill="#38bdf8"/>
    </svg>`,

  helmet_horned: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 14C10 26 16 30 20 30" stroke="#f59e0b" stroke-width="4" stroke-linecap="round"/>
      <path d="M56 14C54 26 48 30 44 30" stroke="#f59e0b" stroke-width="4" stroke-linecap="round"/>
      <path d="M17 34C17 20 23 14 32 14C41 14 47 20 47 34L44 50H20L17 34Z" fill="#1e1b4b" stroke="#38bdf8" stroke-width="2"/>
      <circle cx="32" cy="25" r="4" fill="#38bdf8"/>
    </svg>`,

  // SHIELDS
  shield_battle: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="21" fill="#78350f" stroke="#94a3b8" stroke-width="4"/>
      <circle cx="32" cy="32" r="7" fill="#cbd5e1" stroke="#475569" stroke-width="2"/>
    </svg>`,

  shield_pentagon: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="32,10 53,25 45,52 19,52 11,25" fill="#1e3a8a" stroke="#eab308" stroke-width="3"/>
      <polygon points="32,20 43,28 39,43 25,43 21,28" fill="#3b82f6" stroke="#fef08a" stroke-width="1.5"/>
    </svg>`,

  shield_falcon: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 14H50V32C50 45 32 54 32 54C32 54 14 45 14 32V14Z" fill="#312e81" stroke="#f59e0b" stroke-width="3"/>
      <path d="M20 26L32 20L44 26L32 42L20 26Z" fill="#38bdf8" stroke="#fde047" stroke-width="1.5"/>
    </svg>`,

  // SHOES
  shoes_leather: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 16H34V36L48 42V50H16V16Z" fill="#78350f" stroke="#d97706" stroke-width="2"/>
      <rect x="16" y="46" width="32" height="5" fill="#451a03"/>
    </svg>`,

  shoes_phoenix: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 14H34V35L50 41V50H16V14Z" fill="#dc2626" stroke="#fbbf24" stroke-width="2"/>
      <path d="M18 24L28 20L24 30" fill="#fde047"/>
    </svg>`,

  shoes_qilin: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 14H35V35L51 41V50H16V14Z" fill="#0284c7" stroke="#38bdf8" stroke-width="2"/>
      <circle cx="27" cy="26" r="4" fill="#fde047"/>
    </svg>`,

  // ACCESSORIES
  bracelet_silver: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="32" cy="34" rx="18" ry="13" stroke="#cbd5e1" stroke-width="5"/>
      <circle cx="32" cy="21" r="4.5" fill="#38bdf8" stroke="#f8fafc" stroke-width="1.5"/>
    </svg>`,

  bracelet_skytear: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="32" cy="34" rx="18" ry="13" stroke="#f59e0b" stroke-width="5"/>
      <polygon points="32,14 38,22 32,28 26,22" fill="#38bdf8" stroke="#fef08a" stroke-width="1.5"/>
    </svg>`,

  necklace_ebony: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 14C18 32 46 32 46 14" stroke="#d97706" stroke-width="3" fill="none"/>
      <polygon points="32,28 39,40 32,50 25,40" fill="#78350f" stroke="#f59e0b" stroke-width="2"/>
    </svg>`,

  necklace_skytear: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M16 14C16 34 48 34 48 14" stroke="#facc15" stroke-width="3" fill="none"/>
      <polygon points="32,27 40,40 32,52 24,40" fill="#0ea5e9" stroke="#fef08a" stroke-width="2"/>
    </svg>`,

  earrings_ebony: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="22" cy="20" r="5" stroke="#f59e0b" stroke-width="2.5"/>
      <polygon points="22,26 27,42 22,49 17,42" fill="#92400e" stroke="#f59e0b" stroke-width="1.8"/>
      <circle cx="42" cy="20" r="5" stroke="#f59e0b" stroke-width="2.5"/>
      <polygon points="42,26 47,42 42,49 37,42" fill="#92400e" stroke="#f59e0b" stroke-width="1.8"/>
    </svg>`,

  earrings_skytear: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="22" cy="19" r="5" stroke="#fde047" stroke-width="2.5"/>
      <polygon points="22,25 28,41 22,50 16,41" fill="#38bdf8" stroke="#fde047" stroke-width="1.8"/>
      <circle cx="42" cy="19" r="5" stroke="#fde047" stroke-width="2.5"/>
      <polygon points="42,25 48,41 42,50 36,41" fill="#38bdf8" stroke="#fde047" stroke-width="1.8"/>
    </svg>`,

  // CONSUMABLES & MATERIALS
  item_switcher: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="20" fill="#4c1d95" stroke="#f59e0b" stroke-width="3"/>
      <circle cx="32" cy="32" r="13" fill="#a855f7"/>
      <path d="M24 28C26 22 36 22 39 27M40 36C38 42 28 42 25 37" stroke="#fef08a" stroke-width="3" stroke-linecap="round"/>
      <circle cx="32" cy="32" r="4" fill="#fef08a"/>
    </svg>`,

  item_adder: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="20" fill="#0c4a6e" stroke="#38bdf8" stroke-width="3"/>
      <path d="M32 20V44M20 32H44" stroke="#7dd3fc" stroke-width="4" stroke-linecap="round"/>
    </svg>`,

  item_blessing_marble: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="marble_grad" cx="35%" cy="30%" r="65%">
          <stop offset="0%" stop-color="#fef08a"/>
          <stop offset="45%" stop-color="#10b981"/>
          <stop offset="100%" stop-color="#064e3b"/>
        </radialGradient>
      </defs>
      <circle cx="32" cy="32" r="21" fill="url(#marble_grad)" stroke="#fbbf24" stroke-width="3"/>
      <circle cx="32" cy="32" r="14" stroke="#a7f3d0" stroke-width="1.5" stroke-dasharray="4 3"/>
      <polygon points="32,16 36,27 47,27 38,34 41,45 32,38 23,45 26,34 17,27 28,27" fill="#fef08a" stroke="#047857" stroke-width="1.2"/>
    </svg>`,

  item_blessing_67: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="b67_grad" x1="10" y1="10" x2="54" y2="54" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#f43f5e"/>
          <stop offset="50%" stop-color="#a855f7"/>
          <stop offset="100%" stop-color="#f59e0b"/>
        </linearGradient>
      </defs>
      <polygon points="32,6 54,19 54,45 32,58 10,45 10,19" fill="url(#b67_grad)" stroke="#fde047" stroke-width="3"/>
      <polygon points="32,13 46,22 46,42 32,51 18,42 18,22" fill="#1e1b4b" stroke="#f472b6" stroke-width="1.5"/>
      <polygon points="32,17 36,28 47,32 36,36 32,47 28,36 17,32 28,28" fill="#fde047"/>
      <circle cx="32" cy="32" r="4.5" fill="#fff"/>
    </svg>`,

  item_seal: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="32,8 52,20 52,44 32,56 12,44 12,20" fill="#312e81" stroke="#f59e0b" stroke-width="3"/>
      <rect x="24" y="29" width="16" height="13" rx="2" fill="#f59e0b"/>
      <path d="M27 29V24C27 20 37 20 37 24V29" stroke="#fde047" stroke-width="3"/>
    </svg>`,

  item_scroll: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="16" y="12" width="32" height="40" rx="4" fill="#fef3c7" stroke="#d97706" stroke-width="2.5"/>
      <rect x="12" y="10" width="40" height="6" rx="3" fill="#b45309"/>
      <rect x="12" y="48" width="40" height="6" rx="3" fill="#b45309"/>
      <path d="M24 25H40M24 32H40M24 39H34" stroke="#92400e" stroke-width="2.5" stroke-linecap="round"/>
    </svg>`,

  item_ritualstone: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="32,8 50,24 44,52 20,52 14,24" fill="#0ea5e9" stroke="#fef08a" stroke-width="2.5"/>
      <polygon points="32,16 42,27 38,44 26,44 22,27" fill="#bae6fd"/>
    </svg>`,

  item_skillbook: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 14H46C49 14 50 16 50 19V50H18C15 50 14 48 14 45V14Z" fill="#991b1b" stroke="#f59e0b" stroke-width="2.5"/>
      <path d="M20 14V50" stroke="#f59e0b" stroke-width="2"/>
      <polygon points="34,24 38,32 34,40 30,32" fill="#fde047"/>
    </svg>`,

  item_soulstone: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="soul_grad" x1="12" y1="12" x2="52" y2="52" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#f43f5e"/>
          <stop offset="50%" stop-color="#a855f7"/>
          <stop offset="100%" stop-color="#38bdf8"/>
        </linearGradient>
      </defs>
      <polygon points="32,8 50,26 42,54 22,54 14,26" fill="url(#soul_grad)" stroke="#fef08a" stroke-width="2"/>
      <circle cx="32" cy="30" r="6" fill="#fff" fill-opacity="0.5"/>
    </svg>`,

  item_essence: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="20" fill="#0284c7" stroke="#bae6fd" stroke-width="2.5"/>
      <polygon points="32,12 38,26 52,32 38,38 32,52 26,38 12,32 26,26" fill="#e0f2fe"/>
    </svg>`,

  mat_claw: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 48C20 30 28 18 44 12C38 26 34 38 34 48" fill="#cbd5e1" stroke="#475569" stroke-width="2"/>
      <path d="M28 52C30 36 38 24 52 18C46 32 42 42 42 52" fill="#93c5fd" stroke="#1d4ed8" stroke-width="2"/>
    </svg>`,

  mat_resin: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M32 10C32 10 50 28 50 41C50 50 42 56 32 56C22 56 14 50 14 41C14 28 32 10 32 10Z" fill="#dc2626" stroke="#fca5a5" stroke-width="2"/>
      <circle cx="26" cy="38" r="4" fill="#fca5a5"/>
    </svg>`,

  mat_ore: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="14,44 22,18 42,14 52,36 40,52 20,52" fill="#52525b" stroke="#a1a1aa" stroke-width="2"/>
      <polygon points="26,26 36,22 38,32 28,36" fill="#ef4444"/>
      <polygon points="34,38 44,36 42,46 32,46" fill="#f97316"/>
    </svg>`,

  mat_frost: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="32,8 44,24 38,54 26,54 20,24" fill="#38bdf8" stroke="#e0f2fe" stroke-width="2"/>
      <line x1="32" y1="10" x2="32" y2="52" stroke="#fff" stroke-width="2"/>
    </svg>`,

  mat_shard: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="32,6 48,22 42,56 22,56 16,22" fill="#7e22ce" stroke="#d8b4fe" stroke-width="2.5"/>
      <path d="M24 24L38 36M36 20L26 44" stroke="#38bdf8" stroke-width="2.5"/>
    </svg>`,

  mat_core: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="18" fill="#1e1b4b" stroke="#38bdf8" stroke-width="3"/>
      <circle cx="32" cy="32" r="10" fill="#38bdf8"/>
      <circle cx="32" cy="32" r="4" fill="#fff"/>
    </svg>`,

  // CHESTS
  chest_green: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="22" width="44" height="30" rx="4" fill="#15803d" stroke="#f59e0b" stroke-width="3"/>
      <path d="M10 32H54" stroke="#f59e0b" stroke-width="3"/>
      <rect x="28" y="28" width="8" height="10" rx="2" fill="#fde047" stroke="#92400e" stroke-width="1.5"/>
    </svg>`,

  chest_red: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="22" width="44" height="30" rx="4" fill="#991b1b" stroke="#f59e0b" stroke-width="3"/>
      <path d="M10 32H54" stroke="#f59e0b" stroke-width="3"/>
      <rect x="28" y="28" width="8" height="10" rx="2" fill="#fde047" stroke="#92400e" stroke-width="1.5"/>
    </svg>`,

  chest_iron: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="22" width="44" height="30" rx="4" fill="#3f3f46" stroke="#38bdf8" stroke-width="3"/>
      <path d="M10 32H54" stroke="#38bdf8" stroke-width="3"/>
      <rect x="28" y="28" width="8" height="10" rx="2" fill="#38bdf8" stroke="#e0f2fe" stroke-width="1.5"/>
    </svg>`,

  chest_frost: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="22" width="44" height="30" rx="4" fill="#0369a1" stroke="#bae6fd" stroke-width="3"/>
      <path d="M10 32H54" stroke="#bae6fd" stroke-width="3"/>
      <rect x="28" y="28" width="8" height="10" rx="2" fill="#e0f2fe" stroke="#0284c7" stroke-width="1.5"/>
    </svg>`,

  chest_fallen: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="22" width="44" height="30" rx="4" fill="#581c87" stroke="#f59e0b" stroke-width="3"/>
      <path d="M10 32H54" stroke="#f59e0b" stroke-width="3"/>
      <rect x="28" y="28" width="8" height="10" rx="2" fill="#a855f7" stroke="#fde047" stroke-width="1.5"/>
    </svg>`,

  chest_legend: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="22" width="44" height="30" rx="4" fill="#1e1b4b" stroke="#fde047" stroke-width="3"/>
      <path d="M10 32H54" stroke="#fde047" stroke-width="3"/>
      <polygon points="32,24 38,33 32,42 26,33" fill="#38bdf8" stroke="#fde047" stroke-width="1.5"/>
    </svg>`,

  // SKILLS
  skill_whirlwind: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="22" stroke="#ef4444" stroke-width="4" stroke-dasharray="18 8"/>
      <path d="M20 44L44 20M26 20H44V38" stroke="#fca5a5" stroke-width="3.5" stroke-linecap="round"/>
    </svg>`,
  skill_rage: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M32 10C42 22 48 30 44 44C40 52 24 52 20 44C16 30 22 22 32 10Z" fill="#ef4444" stroke="#fde047" stroke-width="2.5"/>
      <circle cx="32" cy="36" r="7" fill="#fde047"/>
    </svg>`,
  skill_ironwill: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M16 14H48V32C48 45 32 54 32 54C32 54 16 45 16 32V14Z" fill="#475569" stroke="#f59e0b" stroke-width="3"/>
      <path d="M32 20V44M22 30H42" stroke="#fde047" stroke-width="3.5"/>
    </svg>`,
  skill_thunder: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="36,8 18,34 31,34 26,56 46,28 33,28" fill="#fde047" stroke="#f97316" stroke-width="2"/>
    </svg>`,
  skill_shadowstrike: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 50L50 14M32 14H50V32" stroke="#10b981" stroke-width="4" stroke-linecap="round"/>
      <circle cx="32" cy="32" r="10" stroke="#6ee7b7" stroke-width="2"/>
    </svg>`,
  skill_poison: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="34" r="16" fill="#10b981" stroke="#065f46" stroke-width="3"/>
      <circle cx="26" cy="31" r="3" fill="#064e3b"/>
      <circle cx="38" cy="31" r="3" fill="#064e3b"/>
    </svg>`,
  skill_arrowhail: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 12V48M32 16V52M44 12V48" stroke="#34d399" stroke-width="3.5" stroke-linecap="round"/>
      <polygon points="20,52 15,43 25,43" fill="#10b981"/>
      <polygon points="32,56 27,47 37,47" fill="#10b981"/>
      <polygon points="44,52 39,43 49,43" fill="#10b981"/>
    </svg>`,
  skill_miststep: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 24H46M18 34H50M12 44H42" stroke="#6ee7b7" stroke-width="4" stroke-linecap="round"/>
    </svg>`,
  skill_runeblade: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M16 48L48 16" stroke="#c084fc" stroke-width="6" stroke-linecap="round"/>
      <circle cx="32" cy="32" r="16" stroke="#38bdf8" stroke-width="2.5" stroke-dasharray="6 4"/>
    </svg>`,
  skill_aethershield: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="32,10 52,22 52,42 32,54 12,42 12,22" fill="#4c1d95" stroke="#38bdf8" stroke-width="3"/>
      <circle cx="32" cy="32" r="8" fill="#38bdf8"/>
    </svg>`,
  skill_soulburn: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M32 10C44 22 48 34 42 48C36 54 28 54 22 48C16 34 20 22 32 10Z" fill="#8b5cf6" stroke="#38bdf8" stroke-width="2.5"/>
    </svg>`,
  skill_shadowstorm: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="18" fill="#3b0764" stroke="#c084fc" stroke-width="3"/>
      <circle cx="32" cy="32" r="8" fill="#38bdf8"/>
    </svg>`,
  skill_blessing: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="32,10 38,25 54,25 41,35 46,50 32,40 18,50 23,35 10,25 26,25" fill="#fde047" stroke="#f59e0b" stroke-width="2"/>
    </svg>`,
  skill_heal: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="26" y="14" width="12" height="36" rx="3" fill="#22c55e"/>
      <rect x="14" y="26" width="36" height="12" rx="3" fill="#22c55e"/>
    </svg>`,
  skill_lightning: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="35,8 17,34 30,34 25,56 47,27 34,27" fill="#38bdf8" stroke="#e0f2fe" stroke-width="2"/>
    </svg>`,
  skill_dragon: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 44C18 22 32 14 48 16C42 26 44 36 50 44C38 40 26 42 14 44Z" fill="#f59e0b" stroke="#fde047" stroke-width="2.5"/>
      <circle cx="38" cy="24" r="3" fill="#fff"/>
    </svg>`,
  costume_desert: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 14L32 18L44 14L50 26L44 32V52H20V32L14 26L20 14Z" fill="#d97706" stroke="#fde047" stroke-width="2"/>
      <path d="M26 18L32 34L38 18" stroke="#fef3c7" stroke-width="2"/>
      <rect x="20" y="36" width="24" height="5" fill="#991b1b" stroke="#fbbf24" stroke-width="1.2"/>
    </svg>`,
  costume_azrael: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 12L32 18L46 12L54 24L45 32V54H19V32L10 24L18 12Z" fill="#311042" stroke="#c084fc" stroke-width="2.2"/>
      <polygon points="32,22 38,32 32,42 26,32" fill="#ef4444" stroke="#fca5a5" stroke-width="1.5"/>
    </svg>`,
  costume_hair_samurai: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="16" r="7" fill="#1e293b" stroke="#fbbf24" stroke-width="2"/>
      <path d="M16 38C16 24 48 24 48 38C44 32 20 32 16 38Z" fill="#0f172a" stroke="#38bdf8" stroke-width="2"/>
      <line x1="18" y1="16" x2="46" y2="16" stroke="#ef4444" stroke-width="2.5"/>
    </svg>`,
  costume_hair_phoenix: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="14,38 22,18 32,28 42,18 50,38" fill="#f59e0b" stroke="#fef08a" stroke-width="2"/>
      <circle cx="32" cy="30" r="4" fill="#ef4444"/>
    </svg>`,
  costume_weapon_dragon: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M50 10L22 38L26 42L54 14L50 10Z" fill="#ef4444" stroke="#fde047" stroke-width="2"/>
      <path d="M14 34L30 50L26 54L10 38L14 34Z" fill="#f59e0b" stroke="#78350f" stroke-width="1.8"/>
    </svg>`,
  costume_sash_royal: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 24C22 14 42 14 52 24L44 48C36 38 28 38 20 48L12 24Z" fill="#7e22ce" stroke="#fde047" stroke-width="2.2"/>
      <circle cx="32" cy="26" r="5" fill="#38bdf8" stroke="#fef08a" stroke-width="1.5"/>
    </svg>`,
  costume_aura_radiant: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="20" stroke="#fde047" stroke-width="2.5" stroke-dasharray="6 4"/>
      <circle cx="32" cy="32" r="12" fill="#38bdf8" fill-opacity="0.35" stroke="#38bdf8" stroke-width="2"/>
      <polygon points="32,16 36,28 48,32 36,36 32,48 28,36 16,32 28,28" fill="#fef08a"/>
    </svg>`,
  costume_shadow_lord: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 14L26 20L32 12L38 20L50 14L56 26L46 34V54H18V34L8 26L14 14Z" fill="#1e1b4b" stroke="#a855f7" stroke-width="2.2"/>
      <polygon points="32,20 39,32 32,44 25,32" fill="#9333ea" stroke="#e9d5ff" stroke-width="1.5"/>
      <polygon points="14,14 20,6 24,18" fill="#c084fc"/>
      <polygon points="50,14 44,6 40,18" fill="#c084fc"/>
    </svg>`,
  costume_starlight_robe: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 12L32 18L46 12L54 24L45 32L48 54H16L19 32L10 24L18 12Z" fill="#0c4a6e" stroke="#38bdf8" stroke-width="2.2"/>
      <circle cx="32" cy="30" r="6" fill="#fde047" stroke="#fef08a" stroke-width="1.5"/>
    </svg>`,
  costume_shadow_crown: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="12,42 18,20 27,32 32,12 37,32 46,20 52,42" fill="#7e22ce" stroke="#e9d5ff" stroke-width="2"/>
      <polygon points="32,22 36,32 32,40 28,32" fill="#f0abfc"/>
    </svg>`,
  costume_void_blade: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M54 8L38 16L20 38L26 44L48 26L54 8Z" fill="#9333ea" stroke="#f0abfc" stroke-width="2"/>
      <path d="M14 34L30 50L26 54L10 38L14 34Z" fill="#3b0764" stroke="#c084fc" stroke-width="1.8"/>
      <circle cx="23" cy="41" r="3.5" fill="#e879f9"/>
    </svg>`,
  costume_frost_bow: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M16 10C40 12 52 26 50 50" stroke="#38bdf8" stroke-width="4" stroke-linecap="round"/>
      <line x1="16" y1="11" x2="49" y2="49" stroke="#e0f2fe" stroke-width="1.5"/>
      <line x1="18" y1="46" x2="48" y2="16" stroke="#7dd3fc" stroke-width="2.5"/>
    </svg>`,
  mount_crystal_wolf: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 48L18 32L12 24L20 20L24 12L30 20L44 22L52 16L50 30L54 48H46L44 38H24L22 48H14Z" fill="#e0f2fe" stroke="#38bdf8" stroke-width="2"/>
      <path d="M28 22H40L38 30H30L28 22Z" fill="#92400e" stroke="#fbbf24" stroke-width="1.5"/>
      <circle cx="20" cy="22" r="2" fill="#0284c7"/>
    </svg>`,
  mount_shadow_lion: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="22" cy="26" r="12" fill="#581c87" stroke="#c084fc" stroke-width="2"/>
      <path d="M16 48L20 34H44L48 48H40L38 40H26L24 48H16Z" fill="#1e1b4b" stroke="#a855f7" stroke-width="2"/>
      <circle cx="20" cy="24" r="2" fill="#fde047"/>
    </svg>`,
  mount_war_boar: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="32" cy="34" rx="18" ry="12" fill="#451a03" stroke="#f59e0b" stroke-width="2"/>
      <path d="M12 34L6 26L14 30Z" fill="#fef08a"/>
      <rect x="26" y="22" width="12" height="8" rx="2" fill="#b45309" stroke="#fde047" stroke-width="1.5"/>
    </svg>`,
  pet_fire_phoenix: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M32 12L40 26L56 18L46 36L52 50L32 42L12 50L18 36L8 18L24 26L32 12Z" fill="#ef4444" stroke="#fde047" stroke-width="2"/>
      <circle cx="32" cy="28" r="5" fill="#fef08a"/>
    </svg>`,
  pet_mini_azrael: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="24" r="10" fill="#1e1b4b" stroke="#ef4444" stroke-width="2"/>
      <path d="M20 14L25 22M44 14L39 22" stroke="#fca5a5" stroke-width="3" stroke-linecap="round"/>
      <rect x="22" y="34" width="20" height="16" rx="4" fill="#311042" stroke="#c084fc" stroke-width="2"/>
    </svg>`,
  pet_twilight_fox: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="16,14 26,24 20,34" fill="#a855f7" stroke="#f0abfc" stroke-width="1.8"/>
      <polygon points="48,14 38,24 44,34" fill="#a855f7" stroke="#f0abfc" stroke-width="1.8"/>
      <polygon points="20,24 44,24 32,46" fill="#581c87" stroke="#e9d5ff" stroke-width="2"/>
      <circle cx="27" cy="30" r="2" fill="#38bdf8"/>
      <circle cx="37" cy="30" r="2" fill="#38bdf8"/>
    </svg>`,
  perm_exp_ring: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="36" r="16" stroke="#fbbf24" stroke-width="5" fill="none"/>
      <circle cx="32" cy="36" r="12" stroke="#fef08a" stroke-width="1.5" fill="none"/>
      <polygon points="32,8 40,18 32,26 24,18" fill="#38bdf8" stroke="#e0f2fe" stroke-width="2"/>
    </svg>`,
  perm_thief_gloves: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 28L22 14L28 16L32 12L38 15L44 18L46 34L40 50H22L18 28Z" fill="#7f1d1d" stroke="#f87171" stroke-width="2.2"/>
      <path d="M20 42H42V50H20V42Z" fill="#fbbf24" stroke="#fef08a" stroke-width="1.5"/>
      <circle cx="32" cy="30" r="4" fill="#c084fc"/>
    </svg>`,
  perm_luck_medal: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M22 10H42L38 24H26L22 10Z" fill="#1d4ed8" stroke="#93c5fd" stroke-width="1.8"/>
      <circle cx="32" cy="38" r="16" fill="#f59e0b" stroke="#fef08a" stroke-width="2.5"/>
      <polygon points="32,26 35,34 44,35 37,40 39,48 32,43 25,48 27,40 20,35 29,34" fill="#fef9c3"/>
    </svg>`,
  bundle_adventurer: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="24" width="44" height="28" rx="4" fill="#78350f" stroke="#fbbf24" stroke-width="2.5"/>
      <path d="M10 26C10 16 54 16 54 26Z" fill="#b45309" stroke="#fde047" stroke-width="2"/>
      <circle cx="32" cy="28" r="5" fill="#a855f7" stroke="#f3e8ff" stroke-width="1.5"/>
    </svg>`,
  bundle_trinity: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="20" r="10" fill="#38bdf8" stroke="#fef08a" stroke-width="2"/>
      <circle cx="20" cy="42" r="10" fill="#ef4444" stroke="#fef08a" stroke-width="2"/>
      <circle cx="44" cy="42" r="10" fill="#f59e0b" stroke="#fef08a" stroke-width="2"/>
    </svg>`,

  // --- RACE-SPECIFIC METIN2 WEAPONS ---
  weapon_glaive: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <line x1="10" y1="54" x2="46" y2="18" stroke="#78350f" stroke-width="4" stroke-linecap="round"/>
      <path d="M40 24L56 8C58 16 54 26 44 30L40 24Z" fill="#cbd5e1" stroke="#475569" stroke-width="2"/>
      <circle cx="42" cy="22" r="2.5" fill="#f59e0b"/>
    </svg>`,
  weapon_groll: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M56 6L38 14L42 19L18 40L24 46L52 20L56 6Z" fill="#dc2626" stroke="#fef08a" stroke-width="1.8"/>
      <path d="M13 35L29 51L25 54L10 39L13 35Z" fill="#f59e0b" stroke="#78350f" stroke-width="1.6"/>
      <path d="M18 46L8 56L11 59L21 49" fill="#450a0a" stroke="#dc2626" stroke-width="2.2"/>
    </svg>`,
  weapon_sunblade: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M56 6L40 12L20 38L26 44L52 24L56 6Z" fill="#fbbf24" stroke="#fef08a" stroke-width="2"/>
      <circle cx="29" cy="35" r="5" fill="#ef4444" stroke="#fde047" stroke-width="1.5"/>
      <path d="M12 34L30 52L26 55L9 38L12 34Z" fill="#d97706" stroke="#78350f" stroke-width="1.6"/>
      <path d="M17 47L8 56L11 59L20 50" fill="#7c2d12" stroke="#fbbf24" stroke-width="2"/>
    </svg>`,
  weapon_dagger_amija: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M46 12L26 32L31 37L51 17L46 12Z" fill="#cbd5e1" stroke="#475569" stroke-width="1.8"/>
      <path d="M23 29L34 40L31 43L20 32L23 29Z" fill="#d97706"/>
      <path d="M36 24L16 44L21 49L41 29L36 24Z" fill="#94a3b8" stroke="#334155" stroke-width="1.8"/>
    </svg>`,
  weapon_sbd: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M52 10C40 14 28 24 22 36L28 42C40 36 50 24 52 10Z" fill="#1e293b" stroke="#10b981" stroke-width="2"/>
      <path d="M44 18C36 22 30 28 26 36" stroke="#34d399" stroke-width="2" stroke-linecap="round"/>
      <path d="M17 33L31 47L27 50L14 37L17 33Z" fill="#f59e0b" stroke="#78350f" stroke-width="1.5"/>
      <path d="M19 44L11 52L14 55L22 47" fill="#064e3b" stroke="#10b981" stroke-width="2"/>
    </svg>`,
  weapon_chakram: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="18" stroke="#a855f7" stroke-width="5" fill="none"/>
      <circle cx="32" cy="32" r="14" stroke="#e9d5ff" stroke-width="1.5" fill="none"/>
      <polygon points="32,8 37,16 27,16" fill="#c084fc"/>
      <polygon points="32,56 37,48 27,48" fill="#c084fc"/>
      <polygon points="8,32 16,37 16,27" fill="#c084fc"/>
      <polygon points="56,32 48,37 48,27" fill="#c084fc"/>
      <circle cx="32" cy="32" r="5" fill="#1e1b4b" stroke="#fde047" stroke-width="2"/>
    </svg>`,
  weapon_crowbow: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 10C40 12 52 26 52 50" stroke="#312e81" stroke-width="5" stroke-linecap="round"/>
      <path d="M14 10C38 14 48 28 52 50" stroke="#a855f7" stroke-width="2" stroke-linecap="round"/>
      <line x1="14" y1="11" x2="51" y2="49" stroke="#cbd5e1" stroke-width="1.5"/>
      <line x1="18" y1="46" x2="48" y2="16" stroke="#38bdf8" stroke-width="2.5"/>
      <polygon points="52,12 44,15 49,20" fill="#7dd3fc"/>
    </svg>`,
  weapon_soulless_dagger: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M54 8L24 34L30 40L54 8Z" fill="#38bdf8" stroke="#e0f2fe" stroke-width="1.8"/>
      <path d="M46 20L18 44L24 50L46 20Z" fill="#a855f7" stroke="#f3e8ff" stroke-width="1.8"/>
      <circle cx="27" cy="37" r="3.5" fill="#fde047"/>
    </svg>`,
  weapon_gzk: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M54 8L38 16L42 20L28 28L32 32L18 40L24 46L52 18L54 8Z" fill="#9333ea" stroke="#e9d5ff" stroke-width="1.8"/>
      <path d="M13 35L29 51L25 54L10 39L13 35Z" fill="#ef4444" stroke="#7f1d1d" stroke-width="1.5"/>
      <circle cx="21" cy="43" r="3" fill="#fde047"/>
    </svg>`,
  weapon_lionsword: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M54 8L20 38L26 44L56 14L54 8Z" fill="#f59e0b" stroke="#fef08a" stroke-width="1.8"/>
      <circle cx="23" cy="41" r="5" fill="#b45309" stroke="#fde047" stroke-width="2"/>
      <path d="M18 44L10 52L13 55L21 47" fill="#78350f" stroke="#f59e0b" stroke-width="2"/>
    </svg>`,
  weapon_holysword: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M55 7L20 38L26 44L57 13L55 7Z" fill="#38bdf8" stroke="#fef08a" stroke-width="2"/>
      <polygon points="14,32 32,50 27,53 11,37" fill="#fde047" stroke="#b45309" stroke-width="1.5"/>
      <circle cx="23" cy="41" r="4" fill="#a855f7" stroke="#ffffff" stroke-width="1.5"/>
    </svg>`,
  weapon_copper_bell: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="14" r="4.5" stroke="#d97706" stroke-width="2.5" fill="#451a03"/>
      <path d="M21 42C21 27 25 20 32 20C39 20 43 27 43 42L48 48H16L21 42Z" fill="#d97706" stroke="#78350f" stroke-width="2"/>
      <circle cx="32" cy="50" r="4" fill="#fbbf24"/>
    </svg>`,
  weapon_fan_hwf: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M10 26C18 10 46 10 54 26L32 48L10 26Z" fill="#ea580c" stroke="#fed7aa" stroke-width="2"/>
      <line x1="32" y1="48" x2="20" y2="18" stroke="#fde047" stroke-width="1.5"/>
      <line x1="32" y1="48" x2="32" y2="14" stroke="#fde047" stroke-width="1.5"/>
      <line x1="32" y1="48" x2="44" y2="18" stroke="#fde047" stroke-width="1.5"/>
      <circle cx="32" cy="50" r="3.5" fill="#fde047"/>
    </svg>`,
  weapon_orchid_bell: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="13" r="5" stroke="#e879f9" stroke-width="2.5" fill="#4a044e"/>
      <path d="M19 42C19 25 24 19 32 19C40 19 45 25 45 42L50 48H14L19 42Z" fill="#c084fc" stroke="#f5d0fe" stroke-width="2"/>
      <circle cx="32" cy="33" r="5" fill="#fde047"/>
      <circle cx="32" cy="51" r="4.5" fill="#f472b6" stroke="#ffffff" stroke-width="1.5"/>
    </svg>`,
  weapon_demon_fan: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 24C18 8 46 8 56 24L32 50L8 24Z" fill="#7e22ce" stroke="#f5d0fe" stroke-width="2"/>
      <circle cx="32" cy="26" r="6" fill="#ef4444" stroke="#fde047" stroke-width="1.5"/>
      <line x1="32" y1="50" x2="18" y2="18" stroke="#c084fc" stroke-width="1.5"/>
      <line x1="32" y1="50" x2="46" y2="18" stroke="#c084fc" stroke-width="1.5"/>
    </svg>`,

  // --- RACE-SPECIFIC ARMORS ---
  armor_ninja_azure: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 12L11 20L16 29L21 25V52H43V25L48 29L53 20L44 12L36 17H28L20 12Z" fill="#0284c7" stroke="#7dd3fc" stroke-width="2"/>
      <path d="M24 20L40 38M40 20L24 38" stroke="#bae6fd" stroke-width="1.5"/>
      <rect x="21" y="39" width="22" height="4" fill="#f59e0b"/>
    </svg>`,
  armor_ninja_antlion: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 12L10 20L15 30L21 25V52H43V25L49 30L54 20L44 12L36 17H28L20 12Z" fill="#b45309" stroke="#fde047" stroke-width="2"/>
      <polygon points="32,21 38,30 32,37 26,30" fill="#10b981"/>
      <rect x="21" y="40" width="22" height="4" fill="#fde047"/>
    </svg>`,
  armor_ninja_killerwind: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M19 11L9 19L15 30L21 25V53H43V25L49 30L55 19L45 11L36 16H28L19 11Z" fill="#7e22ce" stroke="#e9d5ff" stroke-width="2"/>
      <polygon points="32,20 39,29 32,38 25,29" fill="#f43f5e" stroke="#fde047" stroke-width="1.5"/>
      <rect x="21" y="41" width="22" height="4" fill="#fde047"/>
    </svg>`,
  armor_ninja_blackwind: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 10L8 18L14 30L20 25V54H44V25L50 30L56 18L46 10L36 16H28L18 10Z" fill="#0f172a" stroke="#10b981" stroke-width="2.2"/>
      <polygon points="32,19 40,29 32,39 24,29" fill="#10b981" stroke="#a7f3d0" stroke-width="1.5"/>
      <rect x="20" y="42" width="24" height="4" fill="#34d399"/>
    </svg>`,
  armor_sura_requiem: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M19 12L10 20L15 30L20 26V52H44V26L49 30L54 20L45 12L37 17H27L19 12Z" fill="#3b0764" stroke="#c084fc" stroke-width="2"/>
      <circle cx="32" cy="29" r="5" fill="#9333ea"/>
    </svg>`,
  armor_sura_misfortune: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M19 11L9 20L14 31L20 26V53H44V26L50 31L55 20L45 11L37 17H27L19 11Z" fill="#7f1d1d" stroke="#f87171" stroke-width="2"/>
      <polygon points="32,20 39,29 32,38 25,29" fill="#a855f7" stroke="#fde047" stroke-width="1.5"/>
    </svg>`,
  armor_sura_ghost: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 10L7 19L13 31L20 26V53H44V26L51 31L57 19L46 10L37 16H27L18 10Z" fill="#4c1d95" stroke="#c084fc" stroke-width="2"/>
      <polygon points="32,19 40,29 32,39 24,29" fill="#38bdf8" stroke="#f3e8ff" stroke-width="1.5"/>
    </svg>`,
  armor_sura_magic: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M17 10L6 18L13 31L20 26V54H44V26L51 31L58 18L47 10L37 16H27L17 10Z" fill="#1e1b4b" stroke="#a855f7" stroke-width="2.2"/>
      <polygon points="32,19 40,30 32,41 24,30" fill="#ec4899" stroke="#fde047" stroke-width="1.5"/>
      <path d="M20 43H44" stroke="#c084fc" stroke-width="3"/>
    </svg>`,
  armor_shaman_crimson: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M21 12L10 22L16 32L22 27L19 54H45L42 27L48 32L54 22L43 12L36 17H28L21 12Z" fill="#be123c" stroke="#fda4af" stroke-width="2"/>
      <path d="M28 17L32 54L36 17" stroke="#fde047" stroke-width="1.5"/>
    </svg>`,
  armor_shaman_love: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M21 12L10 22L16 32L22 27L18 54H46L42 27L48 32L54 22L43 12L36 17H28L21 12Z" fill="#db2777" stroke="#fbcfe8" stroke-width="2"/>
      <circle cx="32" cy="28" r="5" fill="#fde047"/>
    </svg>`,
  armor_shaman_orangecat: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 11L9 21L15 32L22 27L18 54H46L42 27L49 32L55 21L44 11L36 16H28L20 11Z" fill="#ea580c" stroke="#fde047" stroke-width="2"/>
      <polygon points="32,20 39,29 32,38 25,29" fill="#fef08a" stroke="#b45309" stroke-width="1.5"/>
    </svg>`,
  armor_shaman_black: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M19 10L8 20L15 32L22 27L17 55H47L42 27L49 32L56 20L45 10L36 16H28L19 10Z" fill="#1e1b4b" stroke="#f59e0b" stroke-width="2.2"/>
      <polygon points="32,19 39,29 32,40 25,29" fill="#f59e0b" stroke="#fef08a" stroke-width="1.5"/>
    </svg>`,

  // --- RACE-SPECIFIC HELMETS ---
  helmet_ninja_leather: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M16 38C16 20 24 12 32 12C40 12 48 20 48 38L43 50H21L16 38Z" fill="#78350f" stroke="#d97706" stroke-width="2"/>
      <path d="M23 30H41V37H23V30Z" fill="#0f172a"/>
    </svg>`,
  helmet_ninja_chain: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M16 38C16 20 24 12 32 12C40 12 48 20 48 38L44 50H20L16 38Z" fill="#475569" stroke="#38bdf8" stroke-width="2"/>
      <path d="M22 29H42V36H22V29Z" fill="#0f172a"/>
    </svg>`,
  helmet_ninja_orc: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M15 38C15 18 23 11 32 11C41 11 49 18 49 38L44 51H20L15 38Z" fill="#065f46" stroke="#34d399" stroke-width="2"/>
      <polygon points="22,28 30,32 22,35" fill="#fde047"/>
      <polygon points="42,28 34,32 42,35" fill="#fde047"/>
    </svg>`,
  helmet_sura_bloody: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M17 36C17 20 23 14 32 14C41 14 47 20 47 36V48H38V36H26V48H17V36Z" fill="#7f1d1d" stroke="#f87171" stroke-width="2"/>
    </svg>`,
  helmet_sura_castle: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M16 36C16 19 23 13 32 13C41 13 48 19 48 36L45 50H19L16 36Z" fill="#4c1d95" stroke="#c084fc" stroke-width="2"/>
      <circle cx="32" cy="24" r="4" fill="#ef4444"/>
    </svg>`,
  helmet_sura_horned: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 12C10 25 16 29 21 29" stroke="#ef4444" stroke-width="4" stroke-linecap="round"/>
      <path d="M56 12C54 25 48 29 43 29" stroke="#ef4444" stroke-width="4" stroke-linecap="round"/>
      <path d="M17 35C17 20 23 14 32 14C41 14 47 20 47 35L44 50H20L17 35Z" fill="#3b0764" stroke="#e879f9" stroke-width="2"/>
    </svg>`,
  helmet_shaman_monk: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 38L32 14L56 38H8Z" fill="#b45309" stroke="#fde047" stroke-width="2"/>
      <circle cx="32" cy="26" r="4" fill="#38bdf8"/>
    </svg>`,
  helmet_shaman_sunlight: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M6 38L32 12L58 38H6Z" fill="#d97706" stroke="#fef08a" stroke-width="2"/>
      <circle cx="32" cy="25" r="5" fill="#ef4444" stroke="#fde047" stroke-width="1.5"/>
    </svg>`,
  helmet_shaman_cardinal: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M10 38L32 10L54 38H10Z" fill="#9333ea" stroke="#fde047" stroke-width="2.2"/>
      <polygon points="32,16 37,26 32,33 27,26" fill="#38bdf8" stroke="#ffffff" stroke-width="1.2"/>
    </svg>`,

  // --- SHIELDS, SHOES & JEWELRY ---
  shield_black_round: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="22" fill="#0f172a" stroke="#94a3b8" stroke-width="4"/>
      <circle cx="32" cy="32" r="8" fill="#ef4444" stroke="#fde047" stroke-width="2"/>
    </svg>`,
  shield_tiger: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 14H50V32C50 45 32 54 32 54C32 54 14 45 14 32V14Z" fill="#78350f" stroke="#fbbf24" stroke-width="3"/>
      <polygon points="32,20 42,30 32,42 22,30" fill="#10b981" stroke="#fde047" stroke-width="1.5"/>
    </svg>`,
  shield_lion_edge: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 14H50V32C50 45 32 54 32 54C32 54 14 45 14 32V14Z" fill="#4c1d95" stroke="#fde047" stroke-width="3"/>
      <circle cx="32" cy="30" r="8" fill="#f59e0b" stroke="#fef08a" stroke-width="1.5"/>
    </svg>`,
  shield_dragon_scale: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 14H50V32C50 45 32 54 32 54C32 54 14 45 14 32V14Z" fill="#065f46" stroke="#fde047" stroke-width="3"/>
      <polygon points="32,18 43,30 32,44 21,30" fill="#f59e0b" stroke="#fef08a" stroke-width="1.5"/>
    </svg>`,
  shield_titan: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 12H52V32C52 47 32 56 32 56C32 56 12 47 12 32V12Z" fill="#1e1b4b" stroke="#fde047" stroke-width="3.5"/>
      <polygon points="32,17 44,30 32,45 20,30" fill="#ef4444" stroke="#fef08a" stroke-width="2"/>
    </svg>`,
  shoes_ecstasy: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 14H34V35L50 41V50H16V14Z" fill="#7e22ce" stroke="#f5d0fe" stroke-width="2"/>
      <circle cx="26" cy="26" r="4" fill="#38bdf8"/>
    </svg>`,
  bracelet_whitegold: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="32" cy="34" rx="18" ry="13" stroke="#f8fafc" stroke-width="5"/>
      <circle cx="32" cy="21" r="5" fill="#fde047" stroke="#f59e0b" stroke-width="1.5"/>
    </svg>`,
  bracelet_soulcrystal: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="32" cy="34" rx="18" ry="13" stroke="#a855f7" stroke-width="5"/>
      <polygon points="32,12 39,21 32,29 25,21" fill="#38bdf8" stroke="#fde047" stroke-width="1.5"/>
    </svg>`,
  necklace_amethyst: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 14C18 32 46 32 46 14" stroke="#cbd5e1" stroke-width="3" fill="none"/>
      <polygon points="32,28 39,40 32,50 25,40" fill="#9333ea" stroke="#e9d5ff" stroke-width="2"/>
    </svg>`,
  necklace_soulcrystal: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 14C18 32 46 32 46 14" stroke="#fde047" stroke-width="3" fill="none"/>
      <polygon points="32,27 40,40 32,52 24,40" fill="#38bdf8" stroke="#f43f5e" stroke-width="2"/>
    </svg>`,
  earrings_copper: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="22" cy="32" r="8" stroke="#d97706" stroke-width="3"/>
      <circle cx="42" cy="32" r="8" stroke="#d97706" stroke-width="3"/>
    </svg>`,
  earrings_emerald: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="22,20 29,32 22,44 15,32" fill="#10b981" stroke="#fde047" stroke-width="2"/>
      <polygon points="42,20 49,32 42,44 35,32" fill="#10b981" stroke="#fde047" stroke-width="2"/>
    </svg>`,
  item_zen_bohne: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="zenGlow" cx="35%" cy="30%" r="65%">
          <stop offset="0%" stop-color="#86efac"/>
          <stop offset="55%" stop-color="#10b981"/>
          <stop offset="100%" stop-color="#065f46"/>
        </radialGradient>
      </defs>
      <circle cx="32" cy="34" r="22" fill="#10b981" fill-opacity="0.16"/>
      <path d="M22 16 C12 20, 12 44, 24 50 C34 55, 48 48, 50 34 C52 22, 42 14, 34 18 C29 20, 28 28, 22 16 Z" fill="url(#zenGlow)" stroke="#a7f3d0" stroke-width="2.2"/>
      <path d="M24 23 C20 29, 21 39, 29 43" stroke="#ecfdf5" stroke-width="2.2" stroke-linecap="round" opacity="0.85"/>
      <circle cx="38" cy="24" r="2.2" fill="#fef08a"/>
      <circle cx="18" cy="20" r="1.6" fill="#a7f3d0"/>
      <circle cx="48" cy="44" r="1.8" fill="#6ee7b7"/>
    </svg>`,
  item_frucht_des_lebens: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="fruitGlow" cx="38%" cy="32%" r="65%">
          <stop offset="0%" stop-color="#fef08a"/>
          <stop offset="45%" stop-color="#f43f5e"/>
          <stop offset="100%" stop-color="#881337"/>
        </radialGradient>
      </defs>
      <circle cx="32" cy="36" r="23" fill="#f59e0b" fill-opacity="0.2"/>
      <path d="M32 18 C32 11, 36 9, 41 9" stroke="#a16207" stroke-width="3" stroke-linecap="round"/>
      <path d="M33 14 C40 10, 48 13, 45 20 C40 22, 35 19, 33 14 Z" fill="#22c55e" stroke="#bbf7d0" stroke-width="1.5"/>
      <path d="M31 15 C24 10, 17 13, 20 19 C24 21, 29 19, 31 15 Z" fill="#16a34a" stroke="#86efac" stroke-width="1.5"/>
      <path d="M32 20 C20 18, 13 27, 15 39 C17 49, 25 54, 32 52 C39 54, 47 49, 49 39 C51 27, 44 18, 32 20 Z" fill="url(#fruitGlow)" stroke="#fde047" stroke-width="2.2"/>
      <path d="M22 27 C19 33, 20 41, 25 46" stroke="#fef9c3" stroke-width="2.2" stroke-linecap="round" opacity="0.85"/>
      <polygon points="32,27 34,32 39,34 34,36 32,41 30,36 25,34 30,32" fill="#fef08a" opacity="0.9"/>
    </svg>`,
  icon_thief_gloves: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="tg_leather" x1="12" y1="10" x2="52" y2="56" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#dc2626"/>
          <stop offset="55%" stop-color="#991b1b"/>
          <stop offset="100%" stop-color="#450a0a"/>
        </linearGradient>
      </defs>
      <path d="M20 34V18C20 15.5 22 14 24 14C26 14 27.5 15.5 27.5 18V26H29V15C29 12.5 31 11 33 11C35 11 36.5 12.5 36.5 15V26H38V17C38 14.5 40 13 42 13C44 13 45.5 14.5 45.5 17V34L50 28C51.8 26.2 54.5 27 54.5 29.5C54.5 31 53.5 33 52 35L44 45V53H20V34Z" fill="url(#tg_leather)" stroke="#fbbf24" stroke-width="2.2"/>
      <rect x="17" y="45" width="30" height="8" rx="2" fill="#78350f" stroke="#fde047" stroke-width="2"/>
      <circle cx="32" cy="36" r="4.5" fill="#fde047" stroke="#92400e" stroke-width="1.5"/>
    </svg>`,
  icon_luck_medal: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="lm_gold" cx="35%" cy="30%" r="65%">
          <stop offset="0%" stop-color="#fef08a"/>
          <stop offset="55%" stop-color="#eab308"/>
          <stop offset="100%" stop-color="#854d0e"/>
        </radialGradient>
      </defs>
      <path d="M24 8L32 20L40 8" stroke="#dc2626" stroke-width="4" stroke-linecap="round"/>
      <circle cx="32" cy="36" r="20" fill="url(#lm_gold)" stroke="#fef9c3" stroke-width="2.2"/>
      <circle cx="32" cy="36" r="15.5" fill="#422006" fill-opacity="0.35" stroke="#ca8a04" stroke-width="1.4"/>
      <path d="M32 23C34.5 20 38.5 22 37 26C35.5 29 32 33 32 33C32 33 28.5 29 27 26C25.5 22 29.5 20 32 23Z" fill="#22c55e" stroke="#bbf7d0" stroke-width="1.2"/>
      <path d="M32 49C34.5 52 38.5 50 37 46C35.5 43 32 39 32 39C32 39 28.5 43 27 46C25.5 50 29.5 52 32 49Z" fill="#16a34a" stroke="#bbf7d0" stroke-width="1.2"/>
      <path d="M19 36C16 33.5 18 29.5 22 31C25 32.5 29 36 29 36C29 36 25 39.5 22 41C18 42.5 16 38.5 19 36Z" fill="#22c55e" stroke="#bbf7d0" stroke-width="1.2"/>
      <path d="M45 36C48 33.5 46 29.5 42 31C39 32.5 35 36 35 36C35 36 39 39.5 42 41C46 42.5 48 38.5 45 36Z" fill="#16a34a" stroke="#bbf7d0" stroke-width="1.2"/>
      <circle cx="32" cy="36" r="2.8" fill="#fef08a"/>
    </svg>`,
  icon_wind_shoes: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="ws_boot" x1="14" y1="14" x2="52" y2="52" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#38bdf8"/>
          <stop offset="55%" stop-color="#0284c7"/>
          <stop offset="100%" stop-color="#1e3a8a"/>
        </linearGradient>
      </defs>
      <path d="M18 16H34V35L50 41V50H16V16Z" fill="url(#ws_boot)" stroke="#fef08a" stroke-width="2.2"/>
      <path d="M12 22C6 18 8 11 16 13C19 14 23 19 18 25L12 22Z" fill="#f8fafc" stroke="#bae6fd" stroke-width="1.5"/>
      <path d="M9 28C4 25 6 20 13 21C16 22 18 26 14 30L9 28Z" fill="#e0f2fe" stroke="#7dd3fc" stroke-width="1.4"/>
      <rect x="15" y="46" width="36" height="5" rx="1.5" fill="#f59e0b" stroke="#78350f" stroke-width="1.5"/>
    </svg>`,
  icon_gloves_leather: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 34V18C20 15.5 22 14 24 14C26 14 27.5 15.5 27.5 18V26H29V15C29 12.5 31 11 33 11C35 11 36.5 12.5 36.5 15V26H38V17C38 14.5 40 13 42 13C44 13 45.5 14.5 45.5 17V34L50 28C51.8 26.2 54.5 27 54.5 29.5C54.5 31 53.5 33 52 35L44 45V53H20V34Z" fill="#92400e" stroke="#d97706" stroke-width="2.2"/>
      <rect x="17" y="45" width="30" height="8" rx="2" fill="#451a03" stroke="#b45309" stroke-width="2"/>
      <path d="M23 34H42" stroke="#fbbf24" stroke-width="1.8" stroke-linecap="round"/>
    </svg>`,
  icon_gloves_iron: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 34V18C20 15.5 22 14 24 14C26 14 27.5 15.5 27.5 18V26H29V15C29 12.5 31 11 33 11C35 11 36.5 12.5 36.5 15V26H38V17C38 14.5 40 13 42 13C44 13 45.5 14.5 45.5 17V34L50 28C51.8 26.2 54.5 27 54.5 29.5C54.5 31 53.5 33 52 35L44 45V53H20V34Z" fill="#64748b" stroke="#e2e8f0" stroke-width="2.2"/>
      <rect x="17" y="45" width="30" height="8" rx="2" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
      <circle cx="32" cy="36" r="4" fill="#38bdf8" stroke="#f8fafc" stroke-width="1.5"/>
    </svg>`,
  icon_gloves_ebony: `
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 34V18C20 15.5 22 14 24 14C26 14 27.5 15.5 27.5 18V26H29V15C29 12.5 31 11 33 11C35 11 36.5 12.5 36.5 15V26H38V17C38 14.5 40 13 42 13C44 13 45.5 14.5 45.5 17V34L50 28C51.8 26.2 54.5 27 54.5 29.5C54.5 31 53.5 33 52 35L44 45V53H20V34Z" fill="#312e81" stroke="#f59e0b" stroke-width="2.2"/>
      <rect x="17" y="45" width="30" height="8" rx="2" fill="#1e1b4b" stroke="#fde047" stroke-width="2"/>
      <polygon points="32,29 37,36 32,42 27,36" fill="#a855f7" stroke="#fef08a" stroke-width="1.5"/>
    </svg>`
};

const DIRECT_SVG_KEYS = new Set([
  'icon_thief_gloves',
  'icon_luck_medal',
  'icon_wind_shoes',
  'icon_gloves_leather',
  'icon_gloves_iron',
  'icon_gloves_ebony',
]);

const NEW_ITEM_PATHS = {
  // Currency
  daya: './assets/icons/currency/daya.png',
  gold: './assets/icons/currency/gold.png',
  curr_gold: './assets/icons/currency/gold.png',
  currency_gold: './assets/icons/currency/gold.png',

  // Potions
  potion_hp: './assets/icons/items/potion/roter_trank.png',
  potion_hp_small: './assets/icons/items/potion/roter_trank.png',
  potion_hp_medium: './assets/icons/items/potion/roter_trank.png',
  potion_hp_large: './assets/icons/items/potion/roter_auto_pott.png',
  roter_trank: './assets/icons/items/potion/roter_trank.png',
  roter_auto_pott: './assets/icons/items/potion/roter_auto_pott.png',
  potion_mp: './assets/icons/items/potion/blauer_trank.png',
  potion_mp_small: './assets/icons/items/potion/blauer_trank.png',
  potion_mp_medium: './assets/icons/items/potion/blauer_trank.png',
  potion_mp_large: './assets/icons/items/potion/blauer_auto_pott.png',
  blauer_trank: './assets/icons/items/potion/blauer_trank.png',
  blauer_auto_pott: './assets/icons/items/potion/blauer_auto_pott.png',
  potion_blue: './assets/icons/items/potion/potion_blue.png',
  potion_green: './assets/icons/items/potion/potion_green.png',
  potion_atk_speed: './assets/icons/items/potion/potion_green.png',
  potion_purple: './assets/icons/items/potion/potion_purple.png',
  potion_speed: './assets/icons/items/potion/potion_purple.png',
  potion_gold: './assets/icons/items/potion/potion_gold.png',

  // Mounts & Pets
  mount_seal: './assets/icons/items/mount/mount_seal.png',
  mount_seal_horse: './assets/icons/items/mount/mount_seal.png',
  mount_war_boar: './assets/icons/items/mount/mount_seal.png',
  mount_crystal_wolf: './assets/icons/items/mount/mount_seal.png',
  mount_shadow_lion: './assets/icons/items/mount/mount_seal.png',
  pet_seal: './assets/icons/items/pet/pet_seal.png',
  pet_seal_paw: './assets/icons/items/pet/pet_seal.png',
  pet_fire_phoenix: './assets/icons/items/pet/pet_seal.png',
  pet_mini_azrael: './assets/icons/items/pet/pet_seal.png',
  pet_twilight_fox: './assets/icons/items/pet/pet_seal.png',

  // Equipment 1 (Wood / Starter & Classic Equipment)
  wood_sword: './assets/icons/items/equipment/1/wood_sword.png',
  rusty_sword: './assets/icons/items/equipment/1/wood_sword.png',
  weapon_broadsword: './assets/icons/items/equipment/1/wood_sword.png',
  silver_blade: './assets/icons/items/equipment/1/wood_sword.png',
  weapon_silversword: './assets/icons/items/equipment/1/wood_sword.png',
  msk: './assets/icons/items/equipment/1/wood_sword.png',
  weapon_msk: './assets/icons/items/equipment/1/wood_sword.png',
  seuchenzahn: './assets/icons/items/equipment/1/wood_sword.png',
  sternenreisser: './assets/icons/items/equipment/1/wood_sword.png',
  wood_axe: './assets/icons/items/equipment/1/wood_axe.png',
  rsb: './assets/icons/items/equipment/1/wood_axe.png',
  weapon_rsb: './assets/icons/items/equipment/1/wood_axe.png',
  sword_rsb: './assets/icons/items/equipment/1/wood_axe.png',
  glaive_iron: './assets/icons/items/equipment/1/wood_axe.png',
  weapon_glaive: './assets/icons/items/equipment/1/wood_axe.png',
  sword_grudge: './assets/icons/items/equipment/1/wood_axe.png',
  weapon_groll: './assets/icons/items/equipment/1/wood_axe.png',
  wood_hammer: './assets/icons/items/equipment/1/wood_hammer.png',
  wood_bow: './assets/icons/items/equipment/1/wood_bow.png',
  shadow_bow: './assets/icons/items/equipment/1/wood_bow.png',
  weapon_hornbow: './assets/icons/items/equipment/1/wood_bow.png',
  weapon_crowbow: './assets/icons/items/equipment/1/wood_bow.png',
  wood_quiver: './assets/icons/items/equipment/1/wood_quiver.png',
  wood_staff: './assets/icons/items/equipment/1/wood_staff.png',
  wood_wand: './assets/icons/items/equipment/1/wood_wand.png',
  amber_bell: './assets/icons/items/equipment/1/wood_wand.png',
  weapon_bell: './assets/icons/items/equipment/1/wood_wand.png',
  weapon_copper_bell: './assets/icons/items/equipment/1/wood_wand.png',
  weapon_orchid_bell: './assets/icons/items/equipment/1/wood_wand.png',
  wood_spellbook: './assets/icons/items/equipment/1/wood_spellbook.png',
  weapon_fan_hwf: './assets/icons/items/equipment/1/wood_spellbook.png',
  weapon_demon_fan: './assets/icons/items/equipment/1/wood_spellbook.png',

  wood_armor_warrior: './assets/icons/items/equipment/1/wood_armor_warrior.png',
  wood_armor_ninja: './assets/icons/items/equipment/1/wood_armor_ninja.png',
  wood_armor_sura: './assets/icons/items/equipment/1/wood_armor_sura.png',
  wood_armor_shaman: './assets/icons/items/equipment/1/wood_armor_shaman.png',
  leather_armor: './assets/icons/items/equipment/1/wood_armor_warrior.png',
  armor_leather: './assets/icons/items/equipment/1/wood_armor_warrior.png',
  tiger_plate: './assets/icons/items/equipment/1/wood_armor_warrior.png',
  armor_tiger: './assets/icons/items/equipment/1/wood_armor_warrior.png',
  dragon_scale_armor: './assets/icons/items/equipment/1/wood_armor_warrior.png',
  armor_dragon: './assets/icons/items/equipment/1/wood_armor_warrior.png',
  black_steel_armor: './assets/icons/items/equipment/1/wood_armor_warrior.png',
  armor_blacksteel: './assets/icons/items/equipment/1/wood_armor_warrior.png',
  armor_ninja_azure: './assets/icons/items/equipment/1/wood_armor_ninja.png',
  armor_ninja_antlion: './assets/icons/items/equipment/1/wood_armor_ninja.png',
  armor_ninja_killerwind: './assets/icons/items/equipment/1/wood_armor_ninja.png',
  armor_ninja_blackwind: './assets/icons/items/equipment/1/wood_armor_ninja.png',
  armor_sura_requiem: './assets/icons/items/equipment/1/wood_armor_sura.png',
  armor_sura_misfortune: './assets/icons/items/equipment/1/wood_armor_sura.png',
  armor_sura_ghost: './assets/icons/items/equipment/1/wood_armor_sura.png',
  armor_sura_magic: './assets/icons/items/equipment/1/wood_armor_sura.png',
  armor_shaman_crimson: './assets/icons/items/equipment/1/wood_armor_shaman.png',
  armor_shaman_love: './assets/icons/items/equipment/1/wood_armor_shaman.png',
  armor_shaman_orangecat: './assets/icons/items/equipment/1/wood_armor_shaman.png',
  armor_shaman_black: './assets/icons/items/equipment/1/wood_armor_shaman.png',

  wood_helm: './assets/icons/items/equipment/1/wood_helm.png',
  wood_helm2: './assets/icons/items/equipment/1/wood_helm2.png',
  iron_helm: './assets/icons/items/equipment/1/wood_helm.png',
  helmet_iron: './assets/icons/items/equipment/1/wood_helm.png',
  ghost_mask_helm: './assets/icons/items/equipment/1/wood_helm2.png',
  helmet_ghost: './assets/icons/items/equipment/1/wood_helm2.png',
  horned_aether_helm: './assets/icons/items/equipment/1/wood_helm2.png',
  helmet_horned: './assets/icons/items/equipment/1/wood_helm2.png',

  wood_shield: './assets/icons/items/equipment/1/wood_shield.png',
  battle_shield: './assets/icons/items/equipment/1/wood_shield.png',
  shield_battle: './assets/icons/items/equipment/1/wood_shield.png',
  pentagon_shield: './assets/icons/items/equipment/1/wood_shield.png',
  shield_pentagon: './assets/icons/items/equipment/1/wood_shield.png',
  falcon_aether_shield: './assets/icons/items/equipment/1/wood_shield.png',
  shield_falcon: './assets/icons/items/equipment/1/wood_shield.png',
  shield_black_round: './assets/icons/items/equipment/1/wood_shield.png',
  shield_tiger: './assets/icons/items/equipment/1/wood_shield.png',
  shield_lion_edge: './assets/icons/items/equipment/1/wood_shield.png',
  shield_dragon_scale: './assets/icons/items/equipment/1/wood_shield.png',
  shield_titan: './assets/icons/items/equipment/1/wood_shield.png',

  wood_boots: './assets/icons/items/equipment/1/wood_boots.png',
  wood_greaves: './assets/icons/items/equipment/1/wood_greaves.png',
  leather_boots: './assets/icons/items/equipment/1/wood_boots.png',
  shoes_leather: './assets/icons/items/equipment/1/wood_boots.png',
  phoenix_shoes: './assets/icons/items/equipment/1/wood_greaves.png',
  shoes_phoenix: './assets/icons/items/equipment/1/wood_greaves.png',
  qilin_aether_boots: './assets/icons/items/equipment/1/wood_greaves.png',
  shoes_qilin: './assets/icons/items/equipment/1/wood_greaves.png',
  shoes_ecstasy: './assets/icons/items/equipment/1/wood_boots.png',

  wood_bracelet: './assets/icons/items/equipment/1/wood_bracelet.png',
  wood_bracelet2: './assets/icons/items/equipment/1/wood_bracelet2.png',
  wood_bracers: './assets/icons/items/equipment/1/wood_bracers.png',
  silver_bracelet: './assets/icons/items/equipment/1/wood_bracelet.png',
  bracelet_silver: './assets/icons/items/equipment/1/wood_bracelet.png',
  sky_tear_bracelet: './assets/icons/items/equipment/1/wood_bracelet2.png',
  bracelet_skytear: './assets/icons/items/equipment/1/wood_bracelet2.png',
  bracelet_whitegold: './assets/icons/items/equipment/1/wood_bracelet.png',
  bracelet_soulcrystal: './assets/icons/items/equipment/1/wood_bracelet2.png',

  wood_necklace: './assets/icons/items/equipment/1/wood_necklace.png',
  ebony_necklace: './assets/icons/items/equipment/1/wood_necklace.png',
  necklace_ebony: './assets/icons/items/equipment/1/wood_necklace.png',
  sky_tear_necklace: './assets/icons/items/equipment/1/wood_necklace.png',
  necklace_skytear: './assets/icons/items/equipment/1/wood_necklace.png',
  necklace_amethyst: './assets/icons/items/equipment/1/wood_necklace.png',
  necklace_soulcrystal: './assets/icons/items/equipment/1/wood_necklace.png',

  wood_earrings: './assets/icons/items/equipment/1/wood_earrings.png',
  ebony_earrings: './assets/icons/items/equipment/1/wood_earrings.png',
  earrings_ebony: './assets/icons/items/equipment/1/wood_earrings.png',
  sky_tear_earrings: './assets/icons/items/equipment/1/wood_earrings.png',
  earrings_skytear: './assets/icons/items/equipment/1/wood_earrings.png',
  earrings_copper: './assets/icons/items/equipment/1/wood_earrings.png',
  earrings_emerald: './assets/icons/items/equipment/1/wood_earrings.png',

  wood_gloves: './assets/icons/items/equipment/1/wood_gloves.png',
  wood_ring: './assets/icons/items/equipment/1/wood_ring.png',

  // Bonus & Upgrade Items
  bonuswandler: './assets/icons/items/bonus/bonuswandler.png',
  bonuswandler2: './assets/icons/items/bonus/bonuswandler2.png',
  item_switcher: './assets/icons/items/bonus/bonuswandler.png',
  item_bonus_changer: './assets/icons/items/bonus/bonuswandler.png',
  bonus_adder: './assets/icons/items/bonus/bonus_adder.png',
  item_adder: './assets/icons/items/bonus/bonus_adder.png',
  item_bonus_adder: './assets/icons/items/bonus/bonus_adder.png',
  aether_seal: './assets/icons/items/bonus/aether_seal.png',
  aether_seal2: './assets/icons/items/bonus/aether_seal2.png',
  item_seal: './assets/icons/items/bonus/aether_seal.png',
  item_aether_seal: './assets/icons/items/bonus/aether_seal.png',
  blessing_scroll: './assets/icons/items/upgrade/blessing_scroll.png',
  scroll_blessing: './assets/icons/items/upgrade/blessing_scroll.png',
  item_scroll: './assets/icons/items/upgrade/blessing_scroll.png',
  magic_metal: './assets/icons/items/upgrade/magic_metal.png',
  ritual_stone: './assets/icons/items/upgrade/magic_metal.png',
  item_ritualstone: './assets/icons/items/upgrade/magic_metal.png',
  soul_orb_rainbow: './assets/icons/items/ranking_points/zen_bean_rainbow.png',
  item_blessing_orb: './assets/icons/items/ranking_points/zen_bean_rainbow.png',

  // Skill Books & Soulstones
  skill_book: './assets/icons/items/skill/skill_book.png',
  skill_book2: './assets/icons/items/skill/skill_book2.png',
  book_skill: './assets/icons/items/skill/skill_book.png',
  item_skill_book: './assets/icons/items/skill/skill_book.png',
  item_skillbook: './assets/icons/items/skill/skill_book.png',
  concentrated_reading: './assets/icons/items/skill/concentrated_reading.png',
  exorcism_scroll: './assets/icons/items/skill/exorcism_scroll.png',
  item_skill_unlock_scroll: './assets/icons/items/skill/exorcism_scroll.png',
  soulstone: './assets/icons/items/skill/soulstone.png',
  soulstone_2: './assets/icons/items/skill/soulstone_2.png',
  soulstone_3: './assets/icons/items/skill/soulstone_3.png',
  soul_fragment: './assets/icons/items/skill/soulstone.png',
  item_soul_fragment: './assets/icons/items/skill/soulstone.png',
  mat_soul_stone: './assets/icons/items/skill/soulstone.png',
  item_soulstone: './assets/icons/items/skill/soulstone.png',
  mat_legendary_soul_stone: './assets/icons/items/skill/soulstone_3.png',

  // Itemshop & Special Rings
  bravery_cape_red: './assets/icons/items/itemshop/bravery_cape_red.png',
  bravery_cape_black: './assets/icons/items/itemshop/bravery_cape_black.png',
  bravery_cape_white: './assets/icons/items/itemshop/bravery_cape_white.png',
  cape_bravery: './assets/icons/items/itemshop/bravery_cape_red.png',
  lollipop: './assets/icons/items/itemshop/lollipop.png',
  lolly: './assets/icons/items/itemshop/lollipop.png',
  ring_of_experience: './assets/icons/items/itemshop/ring_of_experience.png',
  exp_ring: './assets/icons/items/itemshop/ring_of_experience.png',
  perm_exp_ring: './assets/icons/items/itemshop/ring_of_experience.png',
  ring_moon: './assets/icons/items/itemshop/ring_moon.png',
  hmr: './assets/icons/items/itemshop/ring_moon.png',
  ring_amethyst: './assets/icons/items/itemshop/ring_amethyst.png',
  ring_dragon: './assets/icons/items/itemshop/ring_dragon.png',
  ring_emerald: './assets/icons/items/itemshop/ring_emerald.png',
  ring_emerald_luxury: './assets/icons/items/itemshop/ring_emerald_luxury.png',
  ring_ruby: './assets/icons/items/itemshop/ring_ruby.png',
  ring_sapphire: './assets/icons/items/itemshop/ring_sapphire.png',

  // Chests
  mondlicht_truhe: './assets/icons/items/chest/mondlicht_truhe.png',
  mondlicht_schatztruhe: './assets/icons/items/chest/mondlicht_truhe.png',
  chest_moonlight: './assets/icons/items/chest/mondlicht_truhe.png',
  gold_chest: './assets/icons/items/chest/mondlicht_truhe.png',
  boss_chest: './assets/icons/items/chest/boss_chest.png',
  boss_chest2: './assets/icons/items/chest/boss_chest2.png',
  chest_oberork: './assets/icons/items/chest/boss_chest.png',
  chest_bloodleaf: './assets/icons/items/chest/boss_chest.png',
  chest_red: './assets/icons/items/chest/boss_chest.png',
  chest_fallen: './assets/icons/items/chest/boss_chest2.png',
  chest_monolith_legend: './assets/icons/items/chest/boss_chest2.png',
  chest_legend: './assets/icons/items/chest/boss_chest2.png',
  dungeon_chest: './assets/icons/items/chest/dungeon_chest.png',
  dungeon_chest2: './assets/icons/items/chest/dungeon_chest2.png',
  chest_borderlands: './assets/icons/items/chest/dungeon_chest.png',
  chest_green: './assets/icons/items/chest/dungeon_chest.png',
  chest_ironlord: './assets/icons/items/chest/dungeon_chest2.png',
  chest_iron: './assets/icons/items/chest/dungeon_chest2.png',
  chest_frostcolossus: './assets/icons/items/chest/dungeon_chest2.png',
  chest_frost: './assets/icons/items/chest/dungeon_chest2.png',

  // Ores
  ebony_ore: './assets/icons/items/ore/ebony_ore.png',
  ore_coal: './assets/icons/items/ore/ore_coal.png',
  ore_gold: './assets/icons/items/ore/ore_gold.png',
  ore_silver: './assets/icons/items/ore/ore_silver.png',
  cursed_iron_ore: './assets/icons/items/ore/ebony_ore.png',
  mat_cursed_iron: './assets/icons/items/ore/ebony_ore.png',
  mat_ore: './assets/icons/items/ore/ebony_ore.png',

  // Ranking Points / Zen Beans & Pouches
  zen_bean: './assets/icons/items/ranking_points/zen_bean.png',
  item_zen_bohne: './assets/icons/items/ranking_points/zen_bean.png',
  zen_bean_dark: './assets/icons/items/ranking_points/zen_bean_dark.png',
  zen_bean_gold: './assets/icons/items/ranking_points/zen_bean_gold.png',
  zen_bean_rainbow: './assets/icons/items/ranking_points/zen_bean_rainbow.png',
  item_frucht_des_lebens: './assets/icons/items/ranking_points/zen_bean_rainbow.png',
  zen_bean_silver: './assets/icons/items/ranking_points/zen_bean_silver.png',
  yang_pouch: './assets/icons/items/shop/yang_pouch.png',

  // Uppitems & Materials
  bear_claw: './assets/icons/items/uppitems/bear_claw.png',
  wolf_claw: './assets/icons/items/uppitems/bear_claw.png',
  mat_wolf_claw: './assets/icons/items/uppitems/bear_claw.png',
  mat_claw: './assets/icons/items/uppitems/bear_claw.png',
  fur_tiger: './assets/icons/items/uppitems/fur_tiger.png',
  fur_wolf: './assets/icons/items/uppitems/fur_wolf.png',
  monolith_core: './assets/icons/items/uppitems/monolith_core.png',
  origin_core_fragment: './assets/icons/items/uppitems/monolith_core.png',
  mat_awakened_rift_core: './assets/icons/items/uppitems/monolith_core.png',
  mat_core: './assets/icons/items/uppitems/monolith_core.png',
  aether_essence: './assets/icons/items/uppitems/monolith_core.png',
  item_essence: './assets/icons/items/uppitems/monolith_core.png',
  monolith_shards: './assets/icons/items/uppitems/monolith_shards.png',
  monolith_shard: './assets/icons/items/uppitems/monolith_shards.png',
  mat_monolith_shard: './assets/icons/items/uppitems/monolith_shards.png',
  mat_shard: './assets/icons/items/uppitems/monolith_shards.png',
  muschel: './assets/icons/items/uppitems/muschel.png',
  nahgarn_rot: './assets/icons/items/uppitems/nahgarn_rot.png',
  bloodleaf_resin: './assets/icons/items/uppitems/nahgarn_rot.png',
  mat_bloodleaf_resin: './assets/icons/items/uppitems/nahgarn_rot.png',
  mat_resin: './assets/icons/items/uppitems/nahgarn_rot.png',
  nahgarn_violett: './assets/icons/items/uppitems/nahgarn_violett.png',
  orc_band: './assets/icons/items/uppitems/orc_band.png',
  Orcish_War_Totem: './assets/icons/items/uppitems/Orcish_War_Totem.png',
  Ancestors_Amulet_of_the_Wilderness: './assets/icons/items/uppitems/Ancestors_Amulet_of_the_Wilderness.png',
  Runic_Seal_of_the_Ancestors: './assets/icons/items/uppitems/Runic_Seal_of_the_Ancestors.png',
  pearl_white: './assets/icons/items/uppitems/pearl_white.png',
  mat_white_pearl: './assets/icons/items/uppitems/pearl_white.png',
  pearl_blue: './assets/icons/items/uppitems/pearl_blue.png',
  mat_blue_pearl: './assets/icons/items/uppitems/pearl_blue.png',
  frost_crystal: './assets/icons/items/uppitems/pearl_blue.png',
  mat_frost: './assets/icons/items/uppitems/pearl_blue.png',
  pearl_red: './assets/icons/items/uppitems/pearl_red.png',
  mat_red_pearl: './assets/icons/items/uppitems/pearl_red.png',
  pearl_purple: './assets/icons/items/uppitems/pearl_purple.png',
  schmiedehammer: './assets/icons/items/uppitems/schmiedehammer.png',
  schmuck: './assets/icons/items/uppitems/schmuck.png',
  seelenstein: './assets/icons/items/uppitems/seelenstein.png',
  seelenstein_blue: './assets/icons/items/uppitems/seelenstein_blue.png',
  seelenstein_green: './assets/icons/items/uppitems/seelenstein_green.png',
  seelenstein_purple: './assets/icons/items/uppitems/seelenstein_purple.png',
  stoff_schwarz: './assets/icons/items/uppitems/stoff_schwarz.png',
  stoff_weiss: './assets/icons/items/uppitems/stoff_weiss.png',
  stueck_edelstein: './assets/icons/items/uppitems/stueck_edelstein.png',
  tooth_boar: './assets/icons/items/uppitems/tooth_boar.png',
  tooth_orc: './assets/icons/items/uppitems/tooth_orc.png',
  orc_tooth: './assets/icons/items/uppitems/tooth_orc.png',
  bow_crow: './assets/icons/items/equipment/1/wood_bow.png',
  costume_shadow_lord: './assets/icons/items/equipment/1/wood_armor_warrior.png',
  icon_gloves_leather: './assets/icons/items/equipment/1/wood_gloves.png',
  icon_gloves_iron: './assets/icons/items/equipment/1/wood_gloves.png',
  icon_gloves_ebony: './assets/icons/items/equipment/1/wood_gloves.png',
  ore_ebony: './assets/icons/items/ore/ebony_ore.png',
  verfluchtes_eisenerz: './assets/icons/items/ore/ebony_ore.png',
  quest_missing_ore: './assets/icons/items/ore/ebony_ore.png',
  ore_aether_crystal: './assets/icons/items/skill/soulstone.png',
  soul_stone: './assets/icons/items/skill/soulstone.png',
  chest_skill_books: './assets/icons/items/skill/skill_book2.png',
  fertigkeitsbuch: './assets/icons/items/skill/skill_book.png',
  sample_guardian_tablet: './assets/icons/items/skill/skill_book2.png',
  herb_silverleaf: './assets/icons/items/uppitems/seelenstein_green.png',
  herb_glowing_mushroom: './assets/icons/items/uppitems/seelenstein_blue.png',
  sample_forest_plant: './assets/icons/items/uppitems/seelenstein_green.png',
  mat_herb: './assets/icons/items/uppitems/seelenstein_green.png',
  sample_wolf_blood: './assets/icons/items/uppitems/bear_claw.png',
  wolfskralle: './assets/icons/items/uppitems/bear_claw.png',
};

function normalizeLegacyAssetPath(p) {
  const m = String(p || '').match(/^\.?\/assets\/icons\/items\/([^/]+)\.(png|webp|jpg|svg)$/i);
  if (m && NEW_ITEM_PATHS[m[1]]) {
    return NEW_ITEM_PATHS[m[1]];
  }
  return p;
}

function resolveAssetPath(itemOrTemplate) {
  if (!itemOrTemplate) return './assets/icons/system/platzhalter.png';

  if (typeof itemOrTemplate === 'string') {
    const k = itemOrTemplate.trim();
    if (k.startsWith('./') || k.startsWith('/') || k.startsWith('http')) return normalizeLegacyAssetPath(k);
    if (NEW_ITEM_PATHS[k]) return NEW_ITEM_PATHS[k];
    if (k.startsWith('fb_passive_')) return './assets/icons/items/skill/skill_book2.png';
    if (k.startsWith('fb_')) return './assets/icons/items/skill/skill_book.png';
    if (k.startsWith('pet_skill_')) return `./assets/icons/skills/Pet/${k}.png`;
    if (k.startsWith('skill_')) return './assets/icons/skills/krieger.png';
    return `./assets/icons/items/equipment/1/${k}.png`;
  }

  if (itemOrTemplate.customIcon) {
    const ci = String(itemOrTemplate.customIcon);
    if (NEW_ITEM_PATHS[ci]) return NEW_ITEM_PATHS[ci];
    return normalizeLegacyAssetPath(ci);
  }

  // Monster / Rissmonolith / Boss
  if (itemOrTemplate.kind || itemOrTemplate.modelType) {
    if (itemOrTemplate.kind === 'metin' || itemOrTemplate.modelType === 'metin') {
      return './assets/client_ui/Dynamic island/monolith_red.png';
    }
    if (itemOrTemplate.isBoss) {
      return './assets/client_ui/Dynamic island/race_boss.png';
    }
    return './assets/client_ui/Dynamic island/race_animals.png';
  }

  const candidates = [
    itemOrTemplate.icon,
    itemOrTemplate.templateId,
    itemOrTemplate.id,
  ].filter(Boolean);

  for (const c of candidates) {
    const key = String(c).trim();
    if (key.startsWith('./') || key.startsWith('/')) return normalizeLegacyAssetPath(key);
    if (NEW_ITEM_PATHS[key]) return NEW_ITEM_PATHS[key];
    if (key.startsWith('fb_passive_')) return './assets/icons/items/skill/skill_book2.png';
    if (key.startsWith('fb_')) return './assets/icons/items/skill/skill_book.png';
    if (key.startsWith('pet_skill_')) return `./assets/icons/skills/Pet/${key}.png`;
  }

  // Fallback by slot / weaponSubType / name
  const slot = String(itemOrTemplate.slot || '').toLowerCase();
  const sub = String(itemOrTemplate.weaponSubType || '').toLowerCase();
  const itype = String(itemOrTemplate.type || '').toLowerCase();
  const name = String(itemOrTemplate.name || '').toLowerCase();
  const cat = Number(itemOrTemplate.category ?? -1);

  if (itype === 'mount_seal' || slot.includes('mount') || name.includes('pferd') || name.includes('reittier') || name.includes('streitross') || name.includes('eber') || name.includes('rappe') || name.includes('schimmel')) {
    return './assets/icons/items/mount/mount_seal.png';
  }
  if (itype === 'pet_seal' || slot.includes('pet') || name.includes('begleiter') || name.includes('drache') || name.includes('phönix')) {
    return './assets/icons/items/pet/pet_seal.png';
  }
  if (name.includes('heiltrank') || name.includes('roter trank')) {
    return './assets/icons/items/potion/roter_trank.png';
  }
  if (name.includes('manatrank') || name.includes('blauer trank')) {
    return './assets/icons/items/potion/blauer_trank.png';
  }
  if (name.includes('fertigkeitsbuch') || name.includes('buch')) {
    return './assets/icons/items/skill/skill_book.png';
  }
  if (name.includes('seelenstein')) {
    return './assets/icons/items/skill/soulstone.png';
  }
  if (name.includes('truhe') || name.includes('kiste') || itype === 'chest') {
    return './assets/icons/items/chest/mondlicht_truhe.png';
  }
  if (slot === 'weapon') {
    if (sub === 'bow' || name.includes('bogen')) return './assets/icons/items/equipment/1/wood_bow.png';
    if (sub === 'two_hand' || name.includes('zweihand') || name.includes('glefe') || name.includes('axt') || name.includes('brecher')) return './assets/icons/items/equipment/1/wood_axe.png';
    if (sub === 'bell' || name.includes('glocke') || name.includes('stab')) return './assets/icons/items/equipment/1/wood_wand.png';
    if (sub === 'fan' || name.includes('fächer')) return './assets/icons/items/equipment/1/wood_spellbook.png';
    return './assets/icons/items/equipment/1/wood_sword.png';
  }
  if (slot === 'armor' || slot === 'costume' || slot === 'costume_armor') {
    if (name.includes('ninja') || name.includes('schatten') || name.includes('assassine')) return './assets/icons/items/equipment/1/wood_armor_ninja.png';
    if (name.includes('sura') || name.includes('runen')) return './assets/icons/items/equipment/1/wood_armor_sura.png';
    if (name.includes('schaman') || name.includes('seelen')) return './assets/icons/items/equipment/1/wood_armor_shaman.png';
    return './assets/icons/items/equipment/1/wood_armor_warrior.png';
  }
  if (slot === 'helmet' || slot === 'costume_hair' || name.includes('helm') || name.includes('kapuze') || name.includes('hut')) {
    return './assets/icons/items/equipment/1/wood_helm.png';
  }
  if (slot === 'shield' || slot === 'belt' || name.includes('schild') || name.includes('gürtel')) {
    return './assets/icons/items/equipment/1/wood_shield.png';
  }
  if (slot === 'shoes' || name.includes('schuh') || name.includes('stiefel')) {
    return './assets/icons/items/equipment/1/wood_boots.png';
  }
  if (slot === 'bracelet' || name.includes('armband')) {
    return './assets/icons/items/equipment/1/wood_bracelet.png';
  }
  if (slot === 'necklace' || name.includes('kette') || name.includes('halskette')) {
    return './assets/icons/items/equipment/1/wood_necklace.png';
  }
  if (slot === 'earrings' || name.includes('ohrring')) {
    return './assets/icons/items/equipment/1/wood_earrings.png';
  }
  if (slot === 'gloves' || name.includes('handschuh')) {
    return './assets/icons/items/equipment/1/wood_gloves.png';
  }
  if (slot.includes('ring') || name.includes('ring')) {
    return './assets/icons/items/equipment/1/wood_ring.png';
  }
  if (cat === 1) {
    return './assets/icons/items/uppitems/monolith_shards.png';
  }
  if (cat === 2) {
    return './assets/icons/items/skill/skill_book.png';
  }

  return './assets/icons/system/platzhalter.png';
}

export function getItemSlotSize(itemOrTemplate) {
  if (!itemOrTemplate || typeof itemOrTemplate !== 'object') return 1;
  const id = String(itemOrTemplate.templateId || itemOrTemplate.id || '');
  const sub = String(itemOrTemplate.weaponSubType || '');
  const slot = String(itemOrTemplate.slot || '');
  const icon = String(itemOrTemplate.icon || '');
  if (sub === 'dagger' || id === 'dagger_shadow' || id === 'dagger_viper' || id === 'dagger_soulless') {
    return 1;
  }
  if (
    sub === 'two_hand' ||
    sub === 'staff' ||
    sub === 'bell' ||
    sub === 'fan' ||
    slot === 'costume_weapon' ||
    id === 'sword_rsb' ||
    id === 'glaive_iron' ||
    id === 'sword_grudge' ||
    id === 'bell_amber' ||
    id === 'staff_jade' ||
    id === 'staff_dragon' ||
    icon === 'rsb' ||
    icon === 'glaive_iron' ||
    icon === 'sword_grudge' ||
    icon === 'wood_staff'
  ) {
    return 3;
  }
  if (sub === 'one_hand' || sub === 'bow' || slot === 'armor' || slot === 'costume' || slot === 'costume_armor' || slot === 'weapon') {
    return 2;
  }
  if (typeof itemOrTemplate.slotSize === 'number' && itemOrTemplate.slotSize >= 1) {
    return itemOrTemplate.slotSize;
  }
  return 1;
}

export function getItemTypeLabel(itemOrTemplate) {
  if (!itemOrTemplate || typeof itemOrTemplate !== 'object') return 'Gegenstand (1 Slot)';
  const sz = getItemSlotSize(itemOrTemplate);
  const sub = String(itemOrTemplate.weaponSubType || '');
  const slot = String(itemOrTemplate.slot || '');
  const itype = String(itemOrTemplate.type || '');
  if (itype === 'mount_seal') return 'Mount-Siegel (Bleibt im Inventar — Rechtsklick AN/AUS)';
  if (itype === 'pet_seal') return 'Pet-Siegel (Bleibt im Inventar — Rechtsklick AN/AUS)';
  if (slot === 'costume_weapon') return 'Waffen-Kostüm (3 Slots — Kostüm-Seite)';
  if (slot === 'costume_armor' || slot === 'costume') return 'Rüstungs-Kostüm (2 Slots — Kostüm-Seite)';
  if (slot === 'costume_hair') return 'Frisuren-Kostüm (1 Slot — Kostüm-Seite)';
  if (slot === 'costume_pet_skin') return 'Skin-Pet (1 Slot — Kostüm-Seite)';
  if (slot === 'costume_mount_skin') return 'Skin-Mount (1 Slot — Kostüm-Seite)';
  if (['exp_ring', 'thief_gloves', 'luck_medal', 'wind_shoes', 'lolly', 'hmr'].includes(slot)) {
    return 'Spezial-Gegenstand (1 Slot — Spezial-Seite)';
  }
  if (sub === 'two_hand') return 'Zweihandwaffe • Nur Klingenwächter (3 Slots)';
  if (sub === 'staff' || sub === 'bell' || sub === 'fan') return 'Stab • Nur Seelenweber (3 Slots)';
  if (sub === 'one_hand') return 'Einhandwaffe • Schwert (2 Slots)';
  if (sub === 'bow') return 'Bogen • Nur Schattenjäger (2 Slots)';
  if (sub === 'dagger') return 'Dolche • Nur Schattenjäger (1 Slot)';
  if (sz === 3) return 'Zweihandwaffe / Stab (3 Slots)';
  if (slot === 'armor') return 'Rüstung (2 Slots)';
  if (slot === 'helmet') return 'Helm (1 Slot)';
  if (slot === 'shield') return 'Schild (1 Slot)';
  if (slot === 'shoes') return 'Schuhe (1 Slot)';
  if (slot === 'bracelet') return 'Armband (1 Slot)';
  if (slot === 'necklace') return 'Kette (1 Slot)';
  if (slot === 'earrings') return 'Ohrringe (1 Slot)';
  if (slot === 'gloves') return 'Handschuhe (1 Slot)';
  if (slot === 'weapon') return sz === 2 ? 'Einhandwaffe (2 Slots)' : 'Waffe (1 Slot)';
  return `Gegenstand (${sz} ${sz === 1 ? 'Slot' : 'Slots'})`;
}

export function renderIconHTML(itemOrTemplate, size = 44, heightOverride = null) {
  if (!itemOrTemplate) return '';
  const h = heightOverride || size;

  const rawKey = typeof itemOrTemplate === 'string'
    ? itemOrTemplate
    : (itemOrTemplate.icon || itemOrTemplate.id || itemOrTemplate.templateId);

  if (typeof rawKey === 'string' && DIRECT_SVG_KEYS.has(rawKey) && !NEW_ITEM_PATHS[rawKey] && SVG_ICONS[rawKey]) {
    return `<div class="game-icon-svg" style="width:${size}px;height:${h}px;display:flex;align-items:center;justify-content:center;">${SVG_ICONS[rawKey]}</div>`;
  }

  const slot = typeof itemOrTemplate === 'object' ? (itemOrTemplate.slot || '') : '';
  const sub = typeof itemOrTemplate === 'object' ? (itemOrTemplate.weaponSub || '') : '';
  let fallbackSvgKey = null;
  if (rawKey && SVG_ICONS[rawKey]) fallbackSvgKey = rawKey;
  else if (slot === 'weapon' && sub === 'two_hand') fallbackSvgKey = 'weapon_rsb';
  else if (slot === 'weapon') fallbackSvgKey = 'weapon_msk';
  else if (slot === 'armor') fallbackSvgKey = 'armor_dragon';
  else if (slot === 'shield') fallbackSvgKey = 'shield_falcon';
  else if (slot === 'helmet') fallbackSvgKey = 'helmet_horned';

  const assetPath = resolveAssetPath(itemOrTemplate);
  const slotSize = typeof itemOrTemplate === 'object' ? getItemSlotSize(itemOrTemplate) : 1;
  const altTxt = typeof itemOrTemplate === 'object' ? (itemOrTemplate.name || '') : String(itemOrTemplate || '');

  if (fallbackSvgKey && SVG_ICONS[fallbackSvgKey]) {
    const encodedSvg = encodeURIComponent(SVG_ICONS[fallbackSvgKey]);
    return `<div class="game-icon-wrap slot-span-${slotSize}" style="width:${size}px;height:${h}px;"><img src="${assetPath}" alt="${altTxt.replace(/"/g, '&quot;')}" class="game-icon-img" onerror="if(this.dataset.fb!=='1'){this.dataset.fb='1';this.parentElement.innerHTML=decodeURIComponent('${encodedSvg}');}" /></div>`;
  }

  return `<div class="game-icon-wrap slot-span-${slotSize}" style="width:${size}px;height:${h}px;"><img src="${assetPath}" alt="${altTxt.replace(/"/g, '&quot;')}" class="game-icon-img" onerror="if(this.dataset.fb!=='1'){this.dataset.fb='1';this.src='./assets/icons/system/platzhalter.png';}" /></div>`;
}
