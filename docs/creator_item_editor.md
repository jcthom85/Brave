# Creator Item Editor

Brave now has a browser-based item authoring surface at `/creator/items/`.

## Current Scope

The editor currently supports:
- browsing authored item templates
- loading live item previews through the content registry
- editing common item fields such as kind, slot, stackable state, summary, and value
- editing bonuses, restore effects, meal bonuses, and use metadata as JSON blocks
- staging new item drafts directly in the browser
- syncing the structured form into the raw item payload used by the mutation path
- dry-run diff and write through the creator API

## Notes

This page gives creators direct control over the item domain that feeds quests, loot, shops, cooking, and forging. The next expansion should add friendlier stat editors, usage presets, and reference views for where each item is consumed across the game.
