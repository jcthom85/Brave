# Evennia Setup

## Current Baseline

`Brave` is now scaffolded as an Evennia project in [`brave_game`](/mnt/c/Brave/brave_game).

Pinned framework version:

- `evennia==6.0.0`

Project root dependencies are tracked in [`requirements.txt`](/mnt/c/Brave/requirements.txt).

## Recommended Environment

For this workspace, use a Python `3.12` virtual environment.

Important practical note:

- If you are developing under WSL with the project stored on `/mnt/c/...`, keep the virtualenv on the Linux filesystem when possible and point the project at it.
- Creating large Python environments directly on the mounted Windows filesystem can be slow or unreliable.

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
cd /mnt/c/Brave
./run_evennia.sh migrate
```

This creates the default SQLite database at `brave_game/server/evennia.db3`.

Practical note:

- If no superuser exists yet, prefer creating it during the first interactive `evennia start`.
- Rerunning `evennia migrate` from a non-interactive shell before that can repeatedly print the superuser prompt.

## Start The Server

```bash
cd /mnt/c/Brave
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
cd /mnt/c/Brave
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

- [`docs/`](/mnt/c/Brave/docs): design and build docs
- [`brave_game/server/`](/mnt/c/Brave/brave_game/server): Evennia server config, logs, and lifecycle hooks
- [`brave_game/typeclasses/`](/mnt/c/Brave/brave_game/typeclasses): core game entities
- [`brave_game/commands/`](/mnt/c/Brave/brave_game/commands): command and cmdset extensions
- [`brave_game/world/`](/mnt/c/Brave/brave_game/world): content definitions, help entries, prototypes, batch commands
- [`brave_game/web/`](/mnt/c/Brave/brave_game/web): web routes and client customization

## Next Technical Step

Do not start with broad customization of Evennia's web client or replacement of default commands. The next useful step is to expand the current vertical slice with stronger party play, broader enemy variety, and a first named boss encounter.
