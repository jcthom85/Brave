# Brave Evennia Game Dir

This directory contains the Evennia game scaffold for `Brave`.

Project-level design docs live in [`/mnt/c/Brave/docs`](/mnt/c/Brave/docs). The
most relevant setup and architecture references are:

- [`docs/evennia_setup.md`](/mnt/c/Brave/docs/evennia_setup.md)
- [`docs/evennia_architecture.md`](/mnt/c/Brave/docs/evennia_architecture.md)
- [`docs/implementation_plan.md`](/mnt/c/Brave/docs/implementation_plan.md)

## Current Status

- Evennia scaffold created
- Database initialized with `evennia migrate`
- Server name set to `Brave`
- Default networking left open for local LAN play

## Local Run

From the project root:

```bash
cd /mnt/c/Brave
./run_evennia.sh start
```

On first start, Evennia will prompt for a superuser account.

Connect locally with:

- Web client: `http://localhost:4001/webclient`
- Telnet client: `localhost:4000`

Connect from other devices on the same network with the host machine's LAN IP:

- Web client: `http://<host-lan-ip>:4001/webclient`
- Telnet client: `<host-lan-ip>:4000`

## Initial Build Direction

Keep the Evennia scaffold mostly intact until the first vertical slice is working.
Add Brave-specific logic through:

- Typeclasses for player and world entities
- Data-driven content definitions
- Commands layered on top of Evennia defaults
- Encounter scripts for combat and quest progression
