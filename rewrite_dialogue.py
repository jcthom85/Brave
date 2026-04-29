import re
import json

with open('brave_game/world/data/entity_dialogue.py', 'r') as f:
    content = f.read()

# Fix static read responses first (no quotes, just cleanups)
content = content.replace('Use |wpray|n', 'Pray')
content = content.replace('|wpray|n', 'pray')
content = content.replace('ASK WITH |wforge|n, NOT WITH STORIES.', 'ASK AT THE FORGE, NOT WITH STORIES.')

def clean_text(text):
    text = text.replace('Check `sheet` and `gear`', 'Check your equipment')
    text = text.replace('Use `party invite <name>` if you need to gather the family', 'Gather the family if you need to')
    text = text.replace('Bring a `party`', 'Bring your party')
    text = text.replace('use `map`', 'check your map')
    text = text.replace('clear them with `fight`', 'clear them out')
    text = text.replace('Check `quests`', 'Check your objectives')
    text = text.replace('check `quests`', 'check your objectives')
    text = text.replace('and `rest`', 'and rest')
    text = text.replace('and `eat`', 'and eat')
    text = text.replace('`cook`', 'cook')
    text = text.replace('empty your `pack`', 'empty your pack')
    text = text.replace('in your `pack`', 'in your pack')
    text = text.replace('use `enemies` before you commit to `fight`', 'size up your enemies before you fight')
    text = text.replace('use `enemies` before you commit', 'check your enemies before you commit')
    text = text.replace('Use `portals` to review the lineup', 'Review the lineup')
    text = text.replace('go `east`', 'step through')
    text = text.replace('`sheet` will show', 'Your sheet will show')
    text = text.replace('`down` to the cellar', 'down to the cellar')
    text = text.replace('|wpray|n', 'pray')
    text = text.replace('|wfight|n', 'fight')
    return text

def replacer(m):
    text = clean_text(m.group(1))
    # m.group(0) is _rule(\n "Original text"
    # we replace "Original text" with python representation of '"Clean text"'
    python_literal = json.dumps(f'"{text}"')
    return m.group(0).replace(f'"{m.group(1)}"', python_literal)

content = re.sub(r'_rule\(\s*"([^"]+)"', replacer, content)

with open('brave_game/world/data/entity_dialogue.py', 'w') as f:
    f.write(content)
