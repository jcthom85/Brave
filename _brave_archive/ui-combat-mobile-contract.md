# Brave UI Contract

This note is the local contract for the current exploration and combat UI.

## Mobile exploration

- Mobile utility panels must preserve the selected panel across room refresh, look refresh, activity updates, nearby updates, and ordinary command output.
- Activity and Nearby should update in place instead of collapsing back to the NSEW dock.
- Avoid redundant mobile menu copy such as repeating "Menu" explanations inside the menu body.

## Combat layout

- Mobile combat must show 4 player cards at once.
- Mobile combat must show 4 standard enemy cards at once.
- Boss enemies are 2x standard enemy width on desktop and mobile.
- Elite enemies stay standard width and use heavier visual treatment instead of a wider card.
- The player card is more prominent than its ranger companion card.
- Player and companion cards should share the same rendered height.
- Combat cards should keep stable dimensions during combat and should not resize after actions resolve.

## Battle feed

- Battle Feed persists for the full battle.
- Battle Feed should not clear during combat refresh.
- Battle Feed should not jump position between initial combat render and early action updates.

## Change discipline

- Prefer narrow fixes over broad visual redesigns.
- When changing combat or mobile exploration UI, run the Playwright harness and inspect screenshots before extending the design.
- Do not broad-redesign these surfaces without updating the screenshot harness expectations and this contract.
