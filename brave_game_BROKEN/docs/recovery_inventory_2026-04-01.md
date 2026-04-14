# Brave Recovery Inventory (2026-04-01)

## Recovered Baseline

- Preserved modified tree: `/home/jcthom85/Brave-local-20260401-132510`
- Fresh GitHub checkout: `/home/jcthom85/Brave`
- Fresh checkout is now running on the preserved database and venv.
- Webclient responds successfully at `http://127.0.0.1:4001/webclient/`

## Delta Summary

The preserved local tree is on the same git commit as the clean checkout (`ff208cd`) with uncommitted feature work layered on top. The main areas of change are:

- Browser UX overhaul: chargen form input, onboarding modal/objectives sheet, richer dialogue views, mobile/menu changes, combat log layout changes, room micromap, and broad CSS expansion.
- Combat system expansion: many new class abilities, passive-trait support, healing-power support, bleed/poison/stealth states, and seeded browser combat log lines.
- Room/tutorial flow changes: merged room vicinity list, first-run welcome pages, tutorial guidance sheet, revised tutorial copy.
- Account/profile changes: auto-puppet on web login, split active abilities vs passive traits in the sheet/account views.
- NPC conversation UX: dedicated “choose an NPC” talk list plus dialogue actions that jump into shop/forge flows.
- Test coverage additions: chargen/talk/ability progression coverage added locally, room-view regression test updated.
- Web settings changes: permissive `ALLOWED_HOSTS`, cache middleware override intended to reduce stale asset issues.

## Itemized Feature Inventory

### Commands and navigation

- `more` / `menu` / `widgets` command added for a browser-native utilities menu.
- `talk` with no target changed from plain text to a dedicated browser list of nearby NPCs.
- Character command set updated to register the new `more` command.

### Character/account behavior

- Web logins now auto-puppet the last character, or the only character when there is exactly one.
- Character sheet split progression into:
  - Combat Actions
  - Passive Traits
  - Progression Notes for unknown/unclassified entries
- Passive ability bonuses now feed derived stats automatically.
- New helper methods distinguish unlocked combat abilities from unlocked passive traits.
- One-time welcome text on login was removed in favor of browser guidance/onboarding.
- Auto-aggro hook after movement was removed from character movement.

### Ability progression and combat systems

- Ability data moved/expanded into `world/data/character_options.py`.
- Full progression library added for all slice classes, including many previously missing abilities.
- Passive trait library added with stat bonuses such as HP, mana, armor, threat, dodge, healing power, and crit-related bonuses.
- Combat targeting now supports `target = none` abilities.
- Passive abilities are explicitly rejected as queueable combat actions.
- Healing power introduced as a derived stat.
- Encounter state now tracks:
  - stealth turns
  - bleed turns/damage
  - poison turns/damage
- Combat snapshot/browser chips now surface hidden, bleeding, and poisoned states.
- Browser combat scenes seed the combat log with an opener and optional first action line.

New or expanded combat abilities implemented locally:

- Warrior: `shieldbash`, `battlecry`, `intercept`, `tauntingblow`, `brace`, `laststand`
- Ranger: `aimedshot`, `snaretrap`, `volley`, `evasiveroll`, `barbedarrow`, `rainofarrows`
- Cleric: `blessing`, `renewinglight`, `sanctuary`, `cleanse`, `radiantburst`, `guardianlight`
- Additional class progression entries were also added to the shared ability library for mage, rogue, paladin, and druid.

### Browser views and panels

- Chargen copy was rewritten to a more narrative tone.
- Chargen “Choose Name” step now renders a real inline browser form instead of relying on the standard command prompt.
- Room view changed from separate “Threats Here” and “Visible Here” sections to a single “The Vicinity” section with danger-toned threat rows.
- Tutorial guidance now appears as structured browser guidance entries.
- First-time tutorial characters can receive multi-page welcome/onboarding screens.
- A browser-native `More Options` view was added.
- Account view draft/resume entry was compacted and can place actions in the row header.
- Talk view now renders as a focused dialogue scene with actions and optional system shortcuts.
- Talk panel adds context-sensitive actions for shop/forge NPCs.
- New browser talk-list view lets players choose nearby NPCs from a dedicated list.
- Room view can render a small inline micromap inside the main scene.

### Webclient JS/CSS/template changes

- Template replaced `mobile-utility-sheet` with `brave-objectives-sheet`.
- Asset URLs were cache-busted with a timestamp query parameter.
- CSS gained large new sections for:
  - onboarding/objectives modal
  - chargen form styling
  - dialogue/dialogue-list styling
  - compact account rows
  - combat sticky/log sizing and layout
  - mobile adjustments for the new modal/view states
- `default_out.js` gained:
  - inline form rendering/submission
  - onboarding/objectives rendering
  - micromap mirroring
  - richer entry variants/tones/head actions
  - sticky combat log seeding
  - explicit body `data-brave-view` state updates
  - stricter mobile dock gating for true gameplay views
- `default_in.js` also changed locally (input handling updates), but the largest browser-risk surface is `default_out.js`.

### Tutorial and narrative text

- Tutorial step titles/summaries were rewritten.
- Tamsin, Nella, Peep, Brask, and Harl tutorial dialogue was rewritten to a sharper tone.

### Tests added or updated locally

- Updated: `test_room_view.py`
- Added: `test_ability_progression.py`
- Added: `test_chargen_view.py`
- Added: `test_talk_view.py`

## Likely Regression Concentration

The strongest risk cluster for the “game isn’t displaying” failure is the local browser client layer:

- `brave_game/web/static/webclient/js/plugins/default_out.js`
- `brave_game/web/templates/webclient/webclient.html`
- `brave_game/web/static/webclient/css/brave_webclient.css`

Concrete stale-reference hazards found during review:

- `currentMobileUtilityTab` is still referenced after its backing state was removed.
- `toggleMobileUtilityTab(...)` is still called from keyboard handling even though that function was removed.
- `#mobile-utility-sheet` is still referenced in swipe gating after the template stopped rendering it.

Those are not the full root-cause proof yet, but they are real regressions in the modified client code and should be cleaned up first if we continue fixing forward from the local tree.
