# 📜 Aeryndor: Das offizielle Master-Handbuch & Bot-Gedächtnis (Ultimate Edition)

Dieses umfassende Master-Handbuch dient als unveränderliche und verbindliche Single Source of Truth (SSOT) für das gesamte MMORPG Aeryndor. Es regelt exakt alle mathematischen Werte, Drop-Verteilungen, das vollständige Aufwertungssystem von +0 bis +9, die Charakterklassen, die epische Lore sowie die strikten Verhaltens- und Leistungsrichtlinien aller Test- und Spiel-Bots.

---

# 🤖 Teil I: Bot-Gedächtnis & Master-Konfiguration (Aeryndor)

Diese Direktiven gelten absolut verbindlich für alle 12 Test- und Spiel-Bots. Code-Änderungen an diesen Parametern sind strengstens untersagt, um die Konsistenz und Stabilität der Spielsimulation zu gewährleisten.

## ⏱️ 1. Leveldauer & XP-Fortschritt (Zielzeiten)

* **Level 1 – 20:** Exakt 40 bis 60 Minuten (Fokus auf initiale Tutorial-Quests, grundlegende Ausrüstung und effizientes Farmen auf Map 1).
* **Level 21 – 30:** Exakt 40 bis 60 Minuten (Übergang zu den Eid-Kämpfern und planmäßiger Vorstoß in die Anfangszone von Map 2).
* **Level 31 – 35:** Exakt 40 bis 60 Minuten (Intensives Farmen, Questen und Monolithen-Eroberungen im restlichen Map-2-Gebiet).
* **Level 35 – 38:** Exakt 60 Minuten (Vorbereitung auf High-End-Inhalte, Dungeons und fortgeschrittene Gruppenaktivitäten).
* **Ab Level 38:** Kaum noch EXP in den jetzigen Gebieten (Map 1 & Map 2).

---

## 🗺️ 2. Map-, Mob- & Level-Struktur sowie Intelligenter Gebietswechsel

* **MAP 1 (Start- und Trainingsgebiet):**
  * *Hunde, Keiler, Wölfe, etc.:* Level 1 – 8 (Gezielter Drop: *Wolfskralle*).
  * *Bären, Tiger:* Level 9 – 15 (Gezielter Drop: *Bärengalle* / *Tigerfell*).
  * *Eid-Kämpfer:* Level 16 – 22 (Gezielter Drop: *Schmuckgegenstand*).

* **MAP 2 (Erweitertes Kampfgebiet):**
  * *Anfangsgebiet:* Level 23 – 29.
  * *Restliches Gebiet:* Level 30 – 38.
  * *Map-2-Uppitem-Verteilung auf Mobs:* Exklusive Drops von *Stück Edelstein*, *Schwarze Uniform*, *Shuriken* und *Degenklingen*, fein verteilt auf die jeweiligen Monster-Typen.

* **Automatisierter & intelligenter Gebietswechsel:** Bots wechseln das Level- und Farmgebiet exakt beim Erreichen der jeweiligen Level-Schwellen (z. B. sofortiger Map-Wechsel nach Map 2 bei Erreichen von Level 23) sowie bei Abschluss der zugehörigen Questreihen, um jeglichen Leerlauf und XP-Verlust zu verhindern.

---

## 🎁 3. Drop-, Upp- & Seltenheitsregeln (Item-Ökonomie)

* **Ausrüstungs-Grades & Klassentrennung beim Drop:**
  * *Einzelne Waffen & Rüstungen pro Klasse:* In allen 10 Equipment-Stufen sind Waffen (7 klassenspezifische Waffentypen) und Körperrüstungen (4 klassenspezifische Rüstungen: *Plattenpanzer*, *Schattenanzug*, *Runenharnisch*, *Seelengewand*) **strikt einzeln pro Klasse getrennt** und droppen mit exakt gleicher Klassen-Gewichtung!
  * *Monster:* Droppen klassenspezifische Waffen & Rüstungen sowie universellen Schmuck im Bereich von **+0 bis +4** (strikt basierend auf rassen- und mobspezifischen Drop-Pools; jede Monster-Rasse besitzt exakt dieselbe prozentuale Fundchance, aber nicht alles von einem Monster droppen lassen).
  * *Monolithen:* Droppen klassenspezifische Waffen/Rüstungen & Schmuck von **+0 bis +4** (Instabile und höhere Rissmonolithen droppen sogar von **+0 bis +6**).
  * *Bosse:* Droppen hochwertige klassenspezifische Ausrüstung im Bereich von **+4 bis +6**, Bonus-Switcher & -Hinzufügen & weitere seltene Items.

* **Erweckungssteine für Monolithen:**
  * *Stufe-2-Steine (Instabil):* Besitzen eine stark reduzierte Drop-Chance (droppen ab und zu), um den Fluss der Beschwörungen zu balancieren.
  * *Stufe-3-Steine (Erweckt):* Extrem selten und exklusiv für High-End-Inhalte vorgesehen.
  * *Erweckungsmechanik:* Rissmonolithen können durch spezifische Items in drei Phasen transformiert werden (*Schlafend* ➔ *Instabil* ➔ *Erweckt*). Erweckte Monolithen bieten deutlich bessere Drop-Raten, sind jedoch extrem schwer zu bezwingen, da sie einen gebietsgebundenen **Worldboss** beschwören. Dieser besitzt immense TP- und Schadenswerte und erfordert zwingend eine koordinierte Gruppe.

* **Rissmonolithen-Spezialdrops:**
  * Geiststeine +0 bis +4 (zum Sockeln in Waffen und Rüstungen, z. B. *Monster+4*).
  * 1x Fertigkeitsbuch (M1 bis G1 für aktive Skills) – *immer garantiert*.
  * Segensschriftrollen – *selten* (unter Level 60 nur ab Monolithen ab Level 60, Bossen & Dungeons; im High-Level ab 60 deutlich verbesserte Drop-Chancen).

* **Boss-Spezialdrops:** Aktive und passive Skill-Bücher, Seelensteine, Segensschriftrollen sowie 1–5x Bonus hinzufügen / Switcher.
* **Seltene Items (Segensschriftrollen, Bonus hinzufügen / ändern):** Droppen **niemals** von normalen Monstern oder Standard-Monolithen unter Level 60. Ausnahmen bilden Monolithen ab Level 60, Bosse / Weltbosse und Dungeons (Low-Level 1–59 hat extrem seltene Drops, High-Level 60–99 bietet deutlich bessere Chancen).
* **Passive Skill-Fertigkeiten:** Droppen ausschließlich ab *Instabilen Rissmonolithen / Instabilen Risskernen*, von Bossen und in Dungeons.
* **Gold:** Gold darf nicht im Überfluss droppen – exakt so balanciert, dass es für Tränke und Equipment-Aufwertungen passt, ohne überflüssige Inflation im Inventar.
* **Low-Level-Spezialdrops:** Im Low-Level nicht zu viele Spezial-Items droppen.
* **Equipment-Häufigkeit:** Level-1- bis Level-20-Equipment droppt relativ oft von Monstern; Level-30-Equipment mit DSS- & FKS-Werten droppt seltener. Level-80- (Blaustahl) und Level-90-Equipment (Ätherium) sind **nur craftbar** und droppen niemals.

---

## ⚖️ 4. Fairness-Prinzip & Wirtschaft (Kein Pay-to-Win)

* **Kein unlauterer Push:** Es existieren keinerlei Boosts, käufliche Vorteile, Mikrotransaktionen oder Kredite, die normale Spieler nicht auf absolut exakt demselben Weg durch reines Gameplay erreichen können.
* **Intelligenter Handel & Shopsystem:** Bots verwalten ihr Inventar eigenständig, kalkulieren Gewichtsgrenzen/Slots, verkaufen überschüssiges Equipment oder Low-Level-Materialien über das standardmäßige Shopsystem gegen Gold/Yang und erwerben gezielt Verbrauchsgegenstände nach.
* **Event-Einberechnung & Teilnahme:** Das System erkennt aktiv serverweite Events (z. B. temporäre Erhöhungen von Drop- und XP-Raten oder spezielle Truhen-Events), passt die Farming- sowie Level-Routinen der Bots dynamisch an und nimmt aktiv an Events teil, wenn es sich für den Bot lohnt.
* **Intelligente Auskunft an normale Spieler:** Bots antworten normalen Spielern bei Chat- und Flüsternachrichten kontextbezogen und hilfreich.

---

## 📜 5. Quest-System (Integration & Pflichten)

* **Living Quest System V2:** Bots nutzen das System vollumfänglich. Quests von Level 1 bis 99 sind organisch und ausgewogen aufgeteilt (am Anfang weder zu viele textlastige Hürden noch zu wenig Fortschritt, sondern ein konstanter Fluss).
* **Pflichten-Zyklus:** Das Annehmen bei NPCs (anhand von `?` / `!` Indikatoren), das systematische Erfüllen von Jagd- und Sammelzielen in den jeweiligen Zonen sowie die zielgerichtete Rückkehr zur Abgabe (`turn_in`) sind fester Bestandteil der automatisierten Testzyklen.

---

## 🧭 6. Bewegungs-KI: Kollisionen, Ziel-Fokus & Boss-Ausweichen

* **Kollisions-Umlaufung:** Erkannte Hindernisse, Bäume, Zäune und Gebäude-Collider führen niemals zu permanentem Festlaufen. Bots erkennen Kollisionen in Echtzeit und umgehen diese flüssig.
* **Strikter Ziel-Fokus (Kein Flattern):** Ein einmal anvisiertes Ziel (Monster, Monolith oder Boss) wird konsequent bekämpft, bis es vollständig besiegt ist. Ein nervöses oder sprunghaftes Hin- und Herschalten zwischen verschiedenen Zielen im Sekundentakt ist streng untersagt.
* **Boss-Skill-Ausweichen:** Bots analysieren telegrafierte Flächenangriffe und Spezialattacken von Bossen über eine intelligente AI-Hitbox-Erkennung und weichen diesen aktiv per Ausweichrolle aus, noch bevor der Schaden appliziert wird.
* **Intelligentes Benutzen von Items:** Bots setzen Verbrauchs- und Spezialgegenstände kontext- und kampfabhängig ein:
  * *Violette Tränke* (Angriffs- und Bewegungsgeschwindigkeit)
  * *Grüne Tränke* (Bewegungsgeschwindigkeit)
  * *Rote Tränke* (bei TP-Abfall)
  * *Blaue Tränke* (bei MP-Mangel)
  * *Tapferkeitsumhänge* zum effizienten Pullen von Monstermassen
  * Automatisiertes Öffnen von *Truhen* im sicheren Zustand
* **Dynamische Laufrichtungen & flüssige Bewegungen.**
* **Animations- & Skill-Optimierung:** Bots überwachen, testen und optimieren die Animationen, Fertigkeiten & Skills für die neuen Charaktermodelle & Skills.
* **Intelligentes Nachkaufen von Tränken & Verbessern von Items.**

---

## 🧠 7. Klassen-, Begleiter-, Pferde- & Pet-Skill-System

* **Klassenspezifische Skill- & Status-Verteilung:** Bots verteilen ihre Statuspunkte (`STR`, `DEX`, `INT`, `VIT`) und aktiven Skill-Punkte strikt nach optimierten Klassen-Builds:
  1. **Klingenwächter** (Ehemals Krieger) | Physischer Nahkampf | Einhand- und Zweihandschwerter
     * *Stärken:* Hoher Nahkampfschaden, exzellente Widerstandskraft, verheerende Flächenangriffe.
     * *Primäre Attribute:* 1. Stärke (`STR`), 2. Vitalität (`VIT`). Fokus-Skills: *Aura des Schwertes*, *Kampfrausch* | *Starker Körper* & *Durchschlag*.
  2. **Schattenjäger** (Ehemals Ninja) | Schneller Nah- und Fernkampf | Einhandschwert, Dolche (1 Slot), Bogen
     * *Stärken:* Enorme Beweglichkeit, absolute Präzision, hohe Chance auf kritische Treffer.
     * *Primäre Attribute:* 1. Beweglichkeit (`DEX`), 2. Vitalität (`VIT`).
  3. **Runenkrieger** (Ehemals Sura) | Magischer Nahkampf | Einhandschwert
     * *Stärken:* Tödliche Schwertkunst kombiniert mit verbotener Runenmagie und magischem Schutz.
     * *Primäre Attribute:* 1. Intelligenz (`INT`), 2. Stärke (`STR`), 3. Vitalität (`VIT`). Fokus-Skills: *Verzauberte Klinge*, *Furcht*, *Verzauberte Rüstung*.
  4. **Seelenweber** (Ehemals Schamane) | Magie und Unterstützung | Stab
     * *Stärken:* Mächtige Elementarmagie, rettende Heilung und gruppenverstärkende Zauber.
     * *Primäre Attribute:* 1. Intelligenz (`INT`), 2. Vitalität (`VIT`). Fokus-Skills: *Hilfe des Drachen*, *Segen*.

* **Intelligente Pet-Skill-Verteilung:** Begleiter (Pets, Stufe 1–120, 4 Statusattribute, 8 wählbare 3D-Pet-Skins, 24 Pet-Skills) werden nach einem präzisen Schema gelevelt, wobei defensive (HP-Regeneration, Widerstände) oder offensive (Krit-Chance, Monster-Schaden) Passiv-Skills passend zur jeweiligen Spielweise priorisiert werden.

* **Pferde- & Reittier-System (`[P]`):**
  * **Stufen 1 bis 50 mit Pferdemedaillen (`pferdemedaille`):** Steigende Kosten von 1 bis 5–8 Medaillen vor Stufe 50.
  * **WICHTIGE SPERRE FÜR PFERDEMEDAILLEN & BOTS:** Pferdemedaillen droppen **ausschließlich von Affen** (werden später hinzugefügt). Solange es keine Affen-Dungeons/-Mobs gibt, droppen nirgendwo Pferdemedaillen und **kein Bot darf sein Mount-/Pferde-Level steigern**!
  * **Die 3 Pferde-Ränge:**
    * *Level 1–34 — Pferd (Lv. 1 Pferd):* Einfacher Kampf vom Pferderücken (360°-Reitschlag ohne Wegstoßen) mit kleinem Basis-Bonus.
    * *Level 35–49 — Kampfpferd (Lv. 35 Kampfpferd):* Deutlich höherer Grundschaden & STR-Bonus im Sattel sowie mehr als doppelt so starke Skalierung der Sattel-Statuspunkte.
    * *Level 50 — Militärgaul (Lv. 50 Militärgaul):* Höchster Grundschaden & STR-Bonus im Sattel, maximale Skalierung der Sattel-Statuspunkte und Freischaltung der **3 Pferde-Fertigkeiten** (*Kampf vom Pferderücken / Pferde-Stampfen*, *Pferde-Angriff / Ansturm*, *Wellenangriff*), frei auf die Slots 1–9 der Taskbar ziehbar.
  * **Sattel-Statuspunkte (+2 pro Pferde-Level):** *Kampfkraft im Sattel* (Schaden & STR) und *Vitalität im Sattel* (Max. TP & DEF).
  * **Mount-Skins:** Überdecken immer das Standard-Pferd und aktivieren ihre Reit-Boni.

---

## 📈 8. Fertigkeiten-Progression (Stufe 0 bis L1)

* **0 bis 20 FK-Punkte:** Steigerung über Fertigkeitspunkte von 0 bis 20 (automatischer Meister-Sprung ab Erreichen von 20 Punkten auf **M1**).
* **M1 bis M10 (und M10 auf G1):** Fertigkeitsbücher (FB). Jede einzelne Fertigkeit besitzt ein eigenes, spezifisches Fertigkeitsbuch.
* **G1 bis G10 & P1 bis P10:** Seelensteine (`ReadSoulStone` & `UseInventoryItem`). Normale Seelensteine steigern sowohl G1 bis G10 (Übergang auf P1) als auch P1 bis P10.
* **P10 bis L1 (Maximalstufe):** 1x Legendärer Seelenstein. Sobald eine Fertigkeit P10 erreicht hat, wird sie mit genau 1x Legendärem Seelenstein direkt auf **L1** (die absolute Maximalstufe) gehoben.
* **6. & 7. Fertigkeit:** Werden klassenunabhängig mit demselben universellen Freischalt-Item freigeschaltet (schaltet zuerst den 6. Skill frei, und wenn dieser bereits aktiv ist, den 7. Skill). Nach dem Freischalten starten sie auf Stufe 0 und durchlaufen exakt dieselbe Progression (`0–20 FK-Punkte ➔ M1–M10 FB ➔ G1–G10 Seelensteine ➔ P1–P10 Seelensteine ➔ P10–L1 Legendärer Seelenstein`).

---

## 💎 9. Das Stufen-, Ausrüstungs- & Bonussystem (Weiß ➔ Grün ➔ Gold)

### Bonus-Stufen & Wirkungsweise
* **1–5 zufällige Boni (Weiß):** Ein frisch erbeuteter Gegenstand besitzt zufällig zwischen 1 und 5 Standard-Boni.
* **1–5 Boni hinzufügen / switchen (Grün):** Über den Runenaltar / die Runenweberin können fehlende Standard-Plätze bis zu einem Maximum von 5 Boni hinzugefügt und bestehende ungeschützte Boni mit Bonuswandlern geswitcht werden.
* **2 legendäre Boni hinzufügen / switchen (Gold):** Sobald die ersten 5 Standard-Boni aktiv sind, lassen sich bis zu **2 mächtige legendäre Endgame-Boni (6. & 7. Bonus)** freischalten und separat mit Seelensteinen switchen.
* **Spezifische Wirkungsweise („Stark gegen Monster“):** Der Bonus *„Stark gegen Monster“* erhöht den verursachten Schaden **ausschließlich** bei normalen Monstern und greift **weder** bei Bossen noch bei Rissmonolithen!

### Seltenheits-Rahmen der Ausrüstung
* ⚪ **Gewöhnlich** (Grau/Weiß) – Niedrige Boni-Anzahl oder Basiswerte (oft).
* 🔵 **Gut** (Blau) – Solide Zusatzwerte (ab und zu).
* 🟣 **Episch** (Lila) – Hohe Attributswerte (selten).
* 🟡 **Legendär** (Gold) – Perfekt optimierte Boni (sehr selten).
* 💠 **Instabil** (Leuchteffekt) – Alle Boni auf absolutem Maximalwert (äußerst selten)!

### Basis-Werte der 10 Equipment-Stufen (+0 bis +9 • 19 Teile pro Stufe: Waffen & Rüstungen einzeln je Klasse!)
Nur dieses Equipment darf droppen (`+0` bis `+6`, gemäß Drop-Grades; Stufe 9 & 10 nur craftbar!):

#### 🗡️ Klassenspezifische Waffen (7 einzelne Waffen pro Stufe — jede Waffe strikt für EINE Klasse!)
* **Klingenwächter (Krieger):** `{Präfix}-Kriegsschwert` (Einhand, 2 Slots) & `{Präfix}-Zweihänder` (Zweihand, 3 Slots)
* **Schattenjäger (Ninja):** `{Präfix}-Schattenklinge` (Einhand, 2 Slots), `{Präfix}-Dolche` (Dolche, 1 Slot) & `{Präfix}-Bogen` (Bogen, 3 Slots)
* **Runenmagier (Sura):** `{Präfix}-Runenschwert` (Einhand, 2 Slots — AW + Magischer AW)
* **Seelenweber (Schamane):** `{Präfix}-Seelenstab` (Stab, 3 Slots — AW + Magischer AW)
* **Stufe 1 (Lv. 1, Holz):** `+10 AW (+0)` ➔ `+38 AW (+9)` | `+3% Angriffsgeschwindigkeit`
* **Stufe 2 (Lv. 10, Kupfer):** `+18 AW (+0)` ➔ `+56 AW (+9)` | `+4% Angriffsgeschwindigkeit`
* **Stufe 3 (Lv. 20, Eisen):** `+28 AW (+0)` ➔ `+82 AW (+9)` | `+5% Angriffsgeschwindigkeit`
* **Stufe 4 (Lv. 30, Ebenholz):** `+40 AW (+0)` ➔ `+115 AW (+9)` | `+6% Angriffsgeschwindigkeit` *(mit festem DSS & FKS!)*
* **Stufe 5 (Lv. 40, Silber):** `+55 AW (+0)` ➔ `+155 AW (+9)` | `+7% Angriffsgeschwindigkeit`
* **Stufe 6 (Lv. 50, Gold):** `+75 AW (+0)` ➔ `+205 AW (+9)` | `+8% Angriffsgeschwindigkeit`
* **Stufe 7 (Lv. 60, Drachengold):** `+100 AW (+0)` ➔ `+265 AW (+9)` | `+9% Angriffsgeschwindigkeit`
* **Stufe 8 (Lv. 70, Schwarzstahl):** `+135 AW (+0)` ➔ `+345 AW (+9)` | `+10% Angriffsgeschwindigkeit`
* **Stufe 9 (Lv. 80, Blaustahl – Nur Craftbar):** `+180 AW (+0)` ➔ `+445 AW (+9)` | `+11% Angriffsgeschwindigkeit`
* **Stufe 10 (Lv. 90, Ätherium – Nur Craftbar):** `+240 AW (+0)` ➔ `+560 AW (+9)` | `+12% Angriffsgeschwindigkeit`

#### 🛡️ Klassenspezifische Körperrüstungen (4 einzelne Rüstungen pro Stufe — jede Rüstung strikt für EINE Klasse!)
* **Klingenwächter (Krieger):** `{Präfix}-Plattenpanzer` (2 Slots)
* **Schattenjäger (Ninja):** `{Präfix}-Schattenanzug` (2 Slots)
* **Runenmagier (Sura):** `{Präfix}-Runenharnisch` (2 Slots)
* **Seelenweber (Schamane):** `{Präfix}-Seelengewand` (2 Slots)
* **Stufe 1 (Lv. 1, Holz):** `+12 DEF, +300 TP (+0)` ➔ `+42 DEF, +1.200 TP (+9)`
* **Stufe 2 (Lv. 10, Kupfer):** `+22 DEF, +650 TP (+0)` ➔ `+72 DEF, +2.100 TP (+9)`
* **Stufe 3 (Lv. 20, Eisen):** `+35 DEF, +1.100 TP (+0)` ➔ `+110 DEF, +3.100 TP (+9)`
* **Stufe 4 (Lv. 30, Ebenholz):** `+50 DEF, +1.650 TP (+0)` ➔ `+155 DEF, +4.000 TP (+9)`
* **Stufe 5 (Lv. 40, Silber):** `+70 DEF, +2.300 TP (+0)` ➔ `+210 DEF, +4.000 TP (+9)`
* **Stufe 6 (Lv. 50, Gold):** `+95 DEF, +3.000 TP (+0)` ➔ `+280 DEF, +4.000 TP (+9)`
* **Stufe 7 (Lv. 60, Drachengold):** `+125 DEF, +3.600 TP (+0)` ➔ `+365 DEF, +4.000 TP (+9)`
* **Stufe 8 (Lv. 70, Schwarzstahl):** `+165 DEF, +4.000 TP (+0)` ➔ `+470 DEF, +4.000 TP (+9)`
* **Stufe 9 (Lv. 80, Blaustahl – Nur Craftbar):** `+215 DEF, +4.000 TP (+0)` ➔ `+590 DEF, +4.000 TP (+9)`
* **Stufe 10 (Lv. 90, Ätherium – Nur Craftbar):** `+280 DEF, +4.000 TP (+0)` ➔ `+730 DEF, +4.000 TP (+9)`

#### 🛡️ Schilde, Helme, Schuhe, Handschuhe, Ketten, Armbänder, Ohrringe & Gürtel (1 Slot)
* **Schilde (+0 ➔ +9):** Skaliert von `+8` bis `+120 DEF (+0)` auf `+32` bis `+340 DEF (+9)`.
* **Helme (+0 ➔ +9):** Skaliert von `+6` bis `+95 DEF (+0)` auf `+24` bis `+270 DEF (+9)`.
* **Schuhe (+0 ➔ +9):** Verteidigung skaliert von `+5` auf `+200 DEF (+9)` + feste Bewegungsgeschwindigkeit (`+5%` bis `+20%`).
* **Handschuhe (+0 ➔ +9):** Angriffswert skaliert von `+4` auf `+180 AW (+9)`.
* **Ohrringe (+0 ➔ +9):** Angriffswert skaliert von `+5` auf `+200 AW (+9)`.
* **Gürtel (1 Slot, +0 ➔ +9):** Max. TP skaliert von `+150` (Stufe 1) bis `+4.000 TP (+9)`.

### ⚡ Spezialwaffen ab Level 30: Das DSS- und FKS-System
* **Durchschnittsschaden (DSS):** Erhöht den normalen Nahkampf-Schaden (Ideal für PvM / Monolithen-Farmen).
* **Fertigkeitsschaden (FKS):** Erhöht den Skill-Schaden (Primärer PvP-Wert für Burst-Klassen).

### 🗺️ Upp-Items & Upp-Tabellen (+0 bis +9)
* **Map 1 Materialien:** 🐺 *Wolfskralle* (Wölfe Lv. 1–8), 🐻 *Bärengalle* (Bären Lv. 9–15), 🐅 *Tigerfell* (Tiger Lv. 9–15), 💍 *Schmuckgegenstand* (Eid-Kämpfer Lv. 16–22).
* **Map 2 Materialien (Lv. 23–38):** 💎 *Stück Edelstein*, 🖤 *Schwarze Uniform*, 🗡️ *Shuriken*, ⚔️ *Degenklingen*.
* **Schutz vor Zerstörung (+6 bis +9):** Segensschriftrollen (-1 Stufe statt Zerstörung) oder Magisches Metall (100% Stufenschutz).

#### Stufe 1: Holz-Equipment (Lv. 1)
* `+0 ➔ +1:` 500 G | Keine Upp-Items | 100%
* `+1 ➔ +2:` 1.000 G | Keine Upp-Items | 90%
* `+2 ➔ +3:` 2.000 G | 1x Wolfskralle | 80%
* `+3 ➔ +4:` 4.000 G | 2x Wolfskralle | 70%
* `+4 ➔ +5:` 8.000 G | 1x Bärengalle | 60%
* `+5 ➔ +6:` 15.000 G | 2x Bärengalle | 50%
* `+6 ➔ +7:` 25.000 G | 2x Tigerfell | 40%
* `+7 ➔ +8:` 40.000 G | 3x Tigerfell | 30%
* `+8 ➔ +9:` 70.000 G | 5x Schmuckgegenstand | 20%

#### Stufe 2: Kupfer-Equipment (Lv. 10)
* `+0 ➔ +1:` 1.500 G | Keine Upp-Items | 100%
* `+1 ➔ +2:` 3.000 G | 1x Wolfskralle | 90%
* `+2 ➔ +3:` 6.000 G | 2x Wolfskralle | 80%
* `+3 ➔ +4:` 12.000 G | 1x Bärengalle | 70%
* `+4 ➔ +5:` 22.000 G | 2x Bärengalle | 60%
* `+5 ➔ +6:` 38.000 G | 1x Tigerfell | 50%
* `+6 ➔ +7:` 60.000 G | 2x Tigerfell | 35%
* `+7 ➔ +8:` 95.000 G | 4x Schmuckgegenstand | 30%
* `+8 ➔ +9:` 150.000 G | 6x Schmuckgegenstand | 20%

#### Stufe 3: Eisen-Equipment (Lv. 20)
* `+0 ➔ +1:` 3.500 G | 1x Wolfskralle | 100%
* `+1 ➔ +2:` 7.000 G | 2x Wolfskralle | 90%
* `+2 ➔ +3:` 14.000 G | 1x Bärengalle | 80%
* `+3 ➔ +4:` 28.000 G | 2x Bärengalle | 70%
* `+4 ➔ +5:` 50.000 G | 1x Tigerfell | 60%
* `+5 ➔ +6:` 85.000 G | 2x Tigerfell | 50%
* `+6 ➔ +7:` 130.000 G | 2x Schmuckgegenstand | 40%
* `+7 ➔ +8:` 200.000 G | 4x Schmuckgegenstand | 30%
* `+8 ➔ +9:` 320.000 G | 6x Schmuckgegenstand | 20%

#### Stufe 4 bis 6: Mid-Level-Equipment (Ebenholz Lv. 30, Silber Lv. 40, Gold Lv. 50)
* `+6 ➔ +7:` 120.000 – 250.000 Gold | 2x Map-2-Material | 35%
* `+7 ➔ +8:` 200.000 – 400.000 Gold | 4x Map-2-Material | 25%
* `+8 ➔ +9:` 350.000 – 700.000 Gold | 6x Map-2-Material | 15%

#### Stufe 7 & 8: Mid/High-End-Equipment (Drachengold Lv. 60, Schwarzstahl Lv. 70)
* `+6 ➔ +7:` 600.000 Gold | 2x Map-2-Material | 35%
* `+7 ➔ +8:` 1.200.000 Gold | 4x Map-2-Material | 25%
* `+8 ➔ +9:` 2.500.000 Gold | 6x Map-2-Material | 15%

#### Stufe 9: Blaustahl-Equipment (Lv. 80 – Nur Craftbar)
* `+6 ➔ +7:` 2.500.000 Gold | 4x Map-2-Material | 30%
* `+7 ➔ +8:` 5.000.000 Gold | 7x Map-2-Material | 20%
* `+8 ➔ +9:` 9.000.000 Gold | 10x Map-2-Material | 12%

#### Stufe 10: Ätherium-Equipment (Lv. 90 – High-End / Nur Craftbar)
* `+6 ➔ +7:` 5.000.000 Gold | 5x Map-2-Material | 25%
* `+7 ➔ +8:` 10.000.000 Gold | 8x Map-2-Material | 15%
* `+8 ➔ +9:` 20.000.000 Gold | 12x Map-2-Material | 8%

---

## 💎 10. Die 18 Rissmonolithen (Level 5 bis 90)

| Level | Rissmonolith | Bedeutung innerhalb der Geschichte | Region / Status |
| --- | --- | --- | --- |
| **5** | Rissmonolith des Erwachens | Die ersten Anzeichen der zurückkehrenden Dimensionsenergie | Map 1 |
| **10** | Rissmonolith der Wildnis | Die fremde Energie beginnt, die Natur zu beeinflussen | Map 1 |
| **15** | Rissmonolith des Blutmondes | Aggressive und zerstörerische Energien treten hervor | Map 1 |
| **20** | Rissmonolith der verlorenen Seelen | Die Grenze zwischen Leben, Tod und fremden Dimensionen wird schwächer | Map 1 |
| **25** | Rissmonolith des Zwielichts | Unterschiedliche Dimensionseinflüsse beginnen sich zu überlagern | Map 2 |
| **30** | Rissmonolith der Verderbnis | Die Energie verändert Kreaturen und ihre Umgebung | Map 2 |
| **35** | Rissmonolith des Chaos | Das Monolithennetzwerk verliert zunehmend seine Stabilität | Map 2 |
| **40** | Rissmonolith des Abgrunds | Ein mächtiger Zugang zu einer gefährlichen fremden Dimension | Noch nicht vergeben |
| **45** | Rissmonolith der Verdammnis | Die zerstörerischen Kräfte der alten Katastrophe kehren zurück | Noch nicht vergeben |
| **50** | Rissmonolith der Finsternis | Schattenenergien beginnen, ganze Regionen zu beeinflussen | Noch nicht vergeben |
| **55** | Rissmonolith des Seelensturms | Mächtige Seelen- und Dimensionsenergien verbinden sich | Noch nicht vergeben |
| **60** | Rissmonolith der ewigen Nacht | Die Energie kann selbst Licht und Atmosphäre verändern | Noch nicht vergeben |
| **65** | Rissmonolith der Zerstörung | Gewaltige Kräfte bedrohen die Stabilität der Landschaft | Noch nicht vergeben |
| **70** | Rissmonolith des Dimensionsbruchs | Die Grenzen zwischen mehreren Dimensionen zerfallen | Noch nicht vergeben |
| **75** | Rissmonolith der Leere | Eine unbekannte Macht entzieht ihrer Umgebung Energie | Noch nicht vergeben |
| **80** | Rissmonolith der Urgewalten | Die ursprünglichen Natur- und Dimensionskräfte treten hervor | Noch nicht vergeben |
| **85** | Rissmonolith des Weltenendes | Die Gefahr eines neuen großen Dimensionsbruchs erreicht ihren Höhepunkt | Noch nicht vergeben |
| **90** | Rissmonolith des Ursprungsspalts | Der mögliche Ursprung des gesamten Monolithennetzwerks | Noch nicht vergeben |

---

## 📖 11. Lore & Spielwelt (Aeryndor: Legacy of the Monoliths)

1. **Die Welt & Das Vermächtnis:** Aeryndor ist eine uralte Welt auf den Überresten vergessener Zeitalter. Im Zentrum stehen die *Rissmonolithen* – monumentale Steingebilde mit Runen und dimensionsübergreifenden Energiekernen. Sie sind das Vermächtnis der *Ersten Hüter*, einer hochentwickelten Zivilisation, die einst die Dimensionsgrenzen stabilisieren wollte. Durch Machtmissbrauch kam es zum *Ersten Bruch* – einer katastrophalen Überschneidung der Welten, in der die Zivilisation zerfiel.
2. **Die Städte & Landmarken:**
   * *Kaeryu (Die Stadt der Wächter):* Im grünen Nordwesten gelegen, Zentrum für Schwertkampf und Grenzwache. Startpunkt für Abenteurer.
   * *Seiryu (Die Stadt des Wissens):* Im Nordosten, Heimat von Archiven und Runenforschern, die die Verbindung zu den Ersten Hütern untersuchen.
   * *Bakra (Die Stadt des herbstlichen Südens):* Umgeben von goldenen und roten Wäldern, ein gefährlicherer Zufluchtsort für Abenteurer im mittleren Levelbereich.
   * *Das Weol-Denkmal:* Monumentale Ruinenanlage im Norden, die als alter Kontrollpunkt des Monolithennetzwerks diente.
   * *See Sohan:* Natürliche Landmarke mit tiefen, pulsierenden Energien unter der Wasseroberfläche.

---

## 🤝 12. Eigenständiges Arbeiten, Verbesserung und Absprache mit anderen Bots

* **Autonome Optimierung & Team-Koordination:** Die 12 Test- und Spiel-Bots agieren vollkommen eigenständig, analysieren kontinuierlich ihre eigene Leistung (Kill-Geschwindigkeit, Ressourcen-Verbrauch, Tode, Animationen & Skill-Timing der neuen Charaktermodelle) und passen ihre Taktiken dynamisch an.
* **Echtzeit-Synchronisation & Gruppen-Synergien:** Gleichzeitig kommunizieren und stimmen sie sich untereinander in Echtzeit ab (Gruppenbildung, Fokus-Ziel-Zuweisung bei Bossen und Rissmonolithen, Aufteilung von Farm-Zonen und gegenseitige Unterstützung durch Buffs oder Heilung), um maximale Effizienz und realistische Spieler-Synergien zu simulieren.
