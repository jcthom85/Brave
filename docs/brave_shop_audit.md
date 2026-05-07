# Brave Shop Audit

## Current State

Brambleford Outfitters is the first configured shop service. Shops now live under `commerce.shops` in `world/content/packs/core/systems.json`.

The current shop loop supports buying, selling, and shift bonuses:

- `shop` opens the Outfitters trade board.
- `buy <item>` buys one infinite-stock shop item.
- `buy <item> = <quantity>` buys several.
- `sell <item>` sells one valued inventory item.
- `sell <item> = all` sells the available stack.
- `shift` grants a temporary merchant bonus for the next few sales.

The UI mirrors the command flow. `build_shop_view` shows player silver, buyable stock, sellable inventory, quest-reserved inventory, and a `Work Shift` action when no merchant bonus is active.

## What Works

- Sale prices come from item `value`.
- Items with no value are not sellable.
- Active `collect_item` quest requirements reserve the needed quantity so players cannot sell required quest progress by accident.
- Shift outcomes are shop-configured in `systems.json`.
- Human race hooks can add one extra favorable sale through `get_shift_sales_bonus`.
- The room service action is exposed through the navigation/activity system when the player is in Brambleford Outfitters.
- Creator API supports `shop` mutations, `shop` previews, and `shops` references.
- Systems Builder includes a Shop preset for room, keeper, sell rules, and infinite stock.

## Limits

- Stock is infinite in V1.
- There are no stock limits, restock rules, faction discounts, or dynamic pricing.
- Shift bonuses improve sales only; they do not discount buying.

## Recommendation

Keep shop infrastructure simple while Act 1 content is still forming. Use infinite stock for early vendors and only add depletion/restock rules once a real design need appears.

The next useful shop work is content-driven:

- Create one additional shop when Act 1 needs it.
- Give that shop a clear content role, such as chapel supplies, fishing/tackle, or road salvage.
- Add shop stock through the Creator API and review it in Systems Builder.

Future implementation slices:

1. Add quest-gated stock for a second vendor.
2. Add richer per-shop copy and keeper dialogue.
3. Consider limited or restocking stock only if content design calls for scarcity.

## Regression Coverage

`regression_tests/test_commerce.py` covers the current commerce contract:

- Outfitters room detection.
- Sale pricing from item values.
- Active quest item reservation.
- Shift bonus sale expiry.
- Infinite-stock buying.
- Browser shop view surfacing buy and sell actions.
