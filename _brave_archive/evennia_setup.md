# Evennia Setup

## Current Baseline

`Brave` is scaffolded as an Evennia project in [`brave_game`](../brave_game).

Pinned framework version:

- `evennia==6.0.0`

Project root dependencies are tracked in [`requirements.txt`](../requirements.txt).

## Recommended Environment

For this workspace, use a Python `3.12` virtual environment.

Important practical note:

- Keep the virtual environment inside this workspace unless you have a reason to share it elsewhere.

## Install

From the project root:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

If the mounted filesystem makes local venv creation problematic, create it elsewhere and symlink `.venv` back into the project.

## Initialize Database

The database has already been initialized once for this workspace, but the normal command is:

```bash
cd /home/jcthom85/Brave
./run_evennia.sh migrate
```

This creates the default SQLite database at `brave_game/server/evennia.db3`.

Practical note:

- If no superuser exists yet, prefer creating it during the first interactive `evennia start`.
- Rerunning `evennia migrate` from a non-interactive shell before that can repeatedly print the superuser prompt.

## Start The Server

```bash
cd /home/jcthom85/Brave
./run_evennia.sh start
```

On first start, Evennia prompts for a superuser account.

Expected first-run flow:

- Create the superuser interactively
- Let Evennia finish its own initial setup and restart once
- After that restart, Brave's world bootstrap will build the Brambleford and Goblin Road slice automatically

If you prefer creating it manually instead, use Django's management command from inside `brave_game`:

```bash
../.venv/bin/evennia createsuperuser
```

Useful related commands:

```bash
cd /home/jcthom85/Brave
./run_evennia.sh restart
./run_evennia.sh stop
./run_evennia.sh -l
```

## Local And LAN Access

Current Evennia defaults used by this project:

- Telnet port: `4000`
- Web port: `4001`
- Websocket port: `4002`
- Interfaces: `0.0.0.0`
- Allowed hosts: `*`

This means the host machine can serve the game to other devices on the same local network without extra binding changes.

Access patterns:

- Same machine browser: `http://localhost:4001/webclient`
- Same machine telnet client: `localhost:4000`
- Other device browser: `http://<host-lan-ip>:4001/webclient`
- Other device telnet client: `<host-lan-ip>:4000`

## First Slice Commands

Once logged in, the most useful current commands are:

- `build`
- `race <name>`
- `class <name>`
- `sheet`
- `gear`
- `pack`
- `party`
- `quests`
- `travel`
- `talk <name>`
- `read <thing>`
- `enemies`
- `fight`
- `attack <enemy>`
- `use <ability> [= target]`
- `rest`
- `help brave`

## Current Project Layout

- [`docs/`](../docs): design and build docs
- [`brave_game/server/`](../brave_game/server): Evennia server config, logs, and lifecycle hooks
- [`brave_game/typeclasses/`](../brave_game/typeclasses): core game entities
- [`brave_game/commands/`](../brave_game/commands): command and cmdset extensions
- [`brave_game/world/`](../brave_game/world): content, combat, quests, tutorial, and UI helpers
- [`brave_game/web/`](../brave_game/web): web routes, templates, static assets, API, and browser client customization

## Next Technical Step

The next useful technical step should support the first-hour story pass: make the existing tutorial, cellar, road, and Ruk beats more reactive and better connected before adding new areas.
