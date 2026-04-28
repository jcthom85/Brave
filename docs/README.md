# Brave Documentation

This folder is intentionally small now. The old concept dumps, dated handoff plans, and completed migration notes were removed because they contradicted the current build more than they helped it.

The live source of truth is the content pack in `brave_game/world/content/packs/core/`. These docs should explain that content and the design direction around it, not preserve every historical idea.

## Current Sources Of Truth

- [Vision And Scope](vision_and_scope.md): Product promise, audience, and scope guardrails.
- [World And Content](world_and_content.md): Current live rooms, zones, NPC roles, quest ladder, and story arc.
- [Tutorial And Onboarding](tutorial_and_onboarding.md): Current Wayfarer's Yard onboarding flow and its remaining story job.
- [First Hour Chapter Plan](first_hour_chapter_plan.md): The opening chapter from first spawn through Ruk, including the recommended high-impact cold open.
- [First-Hour Co-op Pass](first_hour_coop_pass.md): Family-play tuning rules for tutorial, cellar, road, and first boss.
- [Brambleford Town Plan](brambleford_town_plan.md): Room-by-room town layout and reserved expansion footprint.
- [Phase-1 Capstone Plan](phase1_capstone_plan.md): Drowned Weir and The Hollow Lantern as the current fantasy chapter ending.

## Systems References

- [Core Systems](core_systems.md): Stats, races, classes, resources, progression, and resonance concepts.
- [Combat And Encounters](combat_and_encounters.md): Encounter roles, combat readability, and boss-design rules.
- [Data-Driven Content Architecture](data_driven_content_architecture.md): JSON pack structure, registry boundary, validation, and creator-tool goals.
- [Creator Command Surface](creator_command_surface.md): Command-facing creator operations.
- [Creator API](creator_api.md): Browser/API creator operations.
- [Creator Access](creator_access.md): Creator access rules.

## Feature Notes

These are working references for active subsystems. Treat them as design notes, not canonical project history.

- [Audio Systems](audio_systems.md)
- [Minigames And Activities](minigames_and_activities.md)
- [Lantern Rest Arcade Plan](lantern_rest_arcade_plan.md)
- [Menu-First, Command-Complete](menu_first_command_complete_plan.md)
- [Mobile Webclient Design](mobile_webclient_design.md)
- [Mobile Shell Refactor Plan](mobile_shell_refactor_plan.md)
- [Reactive UI And Theming Plan](reactive_ui_and_theming_plan.md)
- [Multiverse And Portals](multiverse_and_portals.md)
- [Open Questions](open_questions.md)

## Technical Setup

- [Evennia Setup](evennia_setup.md)
- [Evennia Architecture](evennia_architecture.md)

## Retired Material

Removed docs included the original phase-1 concept dump, the engine-agnostic implementation plan, the old recovery inventory, dated combat/creator handoffs, the completed data migration plan, and the completed chapel/class completion plan.

If a deleted idea still matters, reintroduce it as current design in one of the source-of-truth docs above instead of restoring the old file wholesale.
