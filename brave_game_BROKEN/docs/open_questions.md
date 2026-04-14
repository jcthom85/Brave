# Open Questions

These are the main design and production decisions that still need final answers. Until they are resolved, use the default recommendation in the middle column.

| Topic | Default Recommendation | Why It Matters |
| --- | --- | --- |
| Player interface | Text-first commands with a small set of shortcut verbs or menu actions | Strongly affects usability and log clarity |
| Local multiplayer model | Single shared process with multiple player slots | Determines session flow, save model, and input handling |
| Persistence | Character and party progression saved locally between sessions | Changes quest state, inventory, and testing needs |
| Death penalty | Defeat returns party to town with modest cost, not harsh item loss | Sets overall tone and frustration level |
| Encounter scaling | Tune for 3 to 4 players first, then scale down for solo and duo | Prevents the core fantasy from collapsing into solo balance first |
| Inventory limits | Keep inventory simple and generous in phase 1 | Avoids adding friction before the main loop is proven |
| Economy | Minimal vendor model with loot selling and basic purchases | Avoids economy creep |
| Respecs | Allow limited or town-based respec if class tuning changes late | Protects players from being punished by balancing changes |
| Content format | Store classes, abilities, enemies, items, and quests as external data | Improves iteration speed and future tooling |
| Combat timing | Short fixed simulation tick rather than freeform text spam | Keeps multiplayer combat readable |
| Join and drop flow | Allow party setup before starting a run; mid-run join is optional | Simplifies local session management |
| Narrative delivery | Quest text plus short NPC dialogue, not long lore dumps | Keeps pacing tight in a systems-first build |

## Recommended Near-Term Decisions

Resolve these before heavy implementation begins:

1. Input model and presentation style
2. Save and session structure
3. Content data format
4. Solo and duo scaling rules
5. Death and recovery loop

## Working Assumption

Until a final decision is made, optimize for the simplest choice that keeps the game readable, replayable, and shippable.
