# Audio Systems: The Sound Of Brave

Audio is a first-class citizen in `Brave`. It transforms the text interface into a multisensory experience, helping the family (especially the kids) feel fully immersed in the world.

## 1. The Soundscape System (Ambient Audio)
Each zone and major room has a dedicated "Soundscape" that plays in the background.
- **Layers:** Most soundscapes are composed of 2-3 layers (e.g., a "Forest Wind" loop + occasional "Distant Wolf" or "Bird Chirp" triggers).
- **Transitions:** As the party moves from Brambleford (warm, cozy music) to the Goblin Road (tense, adventurous drumbeats), the audio cross-fades smoothly.

## 2. Reactive Event SFX (Action Audio)
The game triggers specific sound effects in response to player and enemy actions:
- **Combat:** Distinct sounds for a sword swing, a shield bash, or a "Firebolt" crackle.
- **Loot:** A satisfying "jingle" when gold is found or a "thud" for heavy equipment.
- **Portal:** A unique, warping "hum" when entering a new genre dimension.

## 3. The Musical Theme System
Each major location and portal world has a signature "Theme."
- **Home Base (Brambleford):** A warm, acoustic folk theme with mandolins and soft flutes.
- **Star Wars World:** Orchestral, cinematic swells and electronic "tech" pulses.
- **Dragonball World:** High-energy, driving percussion and synth bass.

## 4. Family Voice & Custom SFX
This is a core creative feature:
- **The Town Cryer:** The kids can record a short "Welcome to Brambleford!" message that plays when a new player joins the room.
- **Custom Enemy Sounds:** When the kids build a new monster, they can choose (or record) its "Roar" or "Attack" sound.
- **Voiceover Passages:** Important story moments can have a "Read Aloud" button that plays a recording of the narrator (or the parents) reading the text.

## 5. Technical Implementation (Evennia Webclient)
- **Protocol:** Uses the standard Evennia OOB (Out-Of-Band) messages to send audio triggers to the browser.
- **Caching:** Pre-loads sounds for the current and adjacent zones to ensure zero-latency triggers.
- **Volume Control:** Independent sliders for "Music," "Ambience," and "Effects."

## 6. Phase-1 Audio Priorities
1. **The Core Loop:** Ambient loops for Brambleford and the first three zones (Road, Woods, Barrows).
2. **Combat Essentials:** 10 basic SFX for common class abilities (Strike, Heal, Firebolt, etc.).
3. **The Portal Transition:** A high-quality "Multiverse Warp" sound for the Nexus.
4. **UI Feedback:** "Click" and "Error" sounds to guide the boys through the interface.
