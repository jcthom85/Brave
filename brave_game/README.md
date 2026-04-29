# Brave Evennia Game Directory

This directory contains the Evennia game scaffold and Brave-specific runtime code.

Project docs live in [`../docs`](../docs). The best entry points are:

- [`../docs/evennia_setup.md`](../docs/evennia_setup.md)
- [`../docs/evennia_architecture.md`](../docs/evennia_architecture.md)
- [`../docs/world_and_content.md`](../docs/world_and_content.md)
- [`../docs/first_hour_chapter_plan.md`](../docs/first_hour_chapter_plan.md)

## Current Status

- Evennia project scaffold is in place.
- Core content is data-driven through JSON packs in `world/content/packs/core/`.
- Current live build includes character creation, seven classes, Wayfarer's Yard onboarding, Brambleford, Goblin Road through Drowned Weir, Junk-Yard Planet, ATB combat, creator tooling, party play, town activities, audio hooks, and browser UI panels.

## Local Run

From the project root:

```bash
./run_evennia.sh start
```

Connect locally with:

- Web client: `http://localhost:4001/webclient`
- Telnet client: `localhost:4000`

Connect from another device on the same network with the host machine's LAN IP:

- Web client: `http://<host-lan-ip>:4001/webclient`
- Telnet client: `<host-lan-ip>:4000`

## Test Lanes

Fast non-Django checks from this directory:

```bash
../.venv/bin/python scripts/fast_check.py
```

This compiles core Python packages, runs the JSON content build, and runs
`regression_tests/fast/`. Use the full regression suite when Django/Evennia is
available:

```bash
../.venv/bin/python -m pytest
```

## Runtime Layout

- `commands/`: player, combat, exploration, creator, town, profile, party, and arcade commands.
- `server/conf/`: Evennia settings, startup hooks, web plugins, and connection screens.
- `typeclasses/`: Evennia object, room, account, character, exit, channel, and script behavior.
- `web/`: Brave webclient, API, website, templates, static assets, and audio/browser code.
- `world/`: content registry, world bootstrap, quests, combat, tutorial, UI views, activities, commerce, portals, and progression systems.
