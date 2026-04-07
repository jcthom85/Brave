"""
File-based help entries. These complements command-based help and help entries
added in the database using the `sethelp` command in-game.

Control where Evennia reads these entries with `settings.FILE_HELP_ENTRY_MODULES`,
which is a list of python-paths to modules to read.

A module like this should hold a global `HELP_ENTRY_DICTS` list, containing
dicts that each represent a help entry. If no `HELP_ENTRY_DICTS` variable is
given, all top-level variables that are dicts in the module are read as help
entries.

Each dict is on the form
::

    {'key': <str>,
     'text': <str>}``     # the actual help text. Can contain # subtopic sections
     'category': <str>,   # optional, otherwise settings.DEFAULT_HELP_CATEGORY
     'aliases': <list>,   # optional
     'locks': <str>       # optional, 'view' controls seeing in help index, 'read'
                          #           if the entry can be read. If 'view' is unset,
                          #           'read' is used for the index. If unset, everyone
                          #           can read/view the entry.

"""

HELP_ENTRY_DICTS = [
    {
        "key": "evennia",
        "aliases": ["ev"],
        "category": "General",
        "locks": "read:perm(Developer)",
        "text": """
            Evennia is a MU-game server and framework written in Python. You can read more
            on https://www.evennia.com.

            # subtopics

            ## Installation

            You'll find installation instructions on https://www.evennia.com.

            ## Community

            There are many ways to get help and communicate with other devs!

            ### Discussions

            The Discussions forum is found at https://github.com/evennia/evennia/discussions.

            ### Discord

            There is also a discord channel for chatting - connect using the
            following link: https://discord.gg/AJJpcRUhtF

        """,
    },
    {
        "key": "brave",
        "category": "Brave",
        "text": """
            Brave is a family-scale fantasy MUD built around Brambleford, a cozy frontier town,
            Goblin Road to the east, and a growing frontier ladder that now runs all the way out to the drowned south-light beyond Blackfen.

            The live slice is still compact, but the core loop is in place. You can already:

            - Explore Brambleford, the current fantasy ladder through Drowned Weir, and the first portal world
            - Use `build`, `race`, and `class` to set your starting identity
            - Use `sheet`, `gear`, and `pack` to inspect your adventurer and loot
            - Use `fish` and `reel` at Hobbyist's Wharf for the first town activity loop
            - Use `cook` and `eat` at the Lantern Rest hearth for simple meal buffs
            - Use `shop`, `sell`, and `shift` at Brambleford Outfitters for the first town trade loop
            - Use `forge` at Ironroot Forge to turn field loot and silver into better gear
            - Use `pray` at the Chapel of the Dawn Bell for a modest one-encounter blessing
            - Use `party` to form a family group before tougher fights
            - Use `party where` to find one another and `party follow` to stay together
            - Use `quests` to track your starter objectives
            - Use `n`, `e`, `s`, `w`, `u`, and `d` for primary movement, with `map` and `minimap` for layout
            - Use `travel` as a named-route fallback when you want place names spelled out
            - Use `talk` and `read` to get guidance from Brambleford's NPCs and notice board
            - Use `fight`, `attack`, `use`, and `rest` in the first combat slice

            Warrior, Cleric, Ranger, Mage, Rogue, Paladin, and Druid are currently playable.

            # subtopics

            ## First Steps

            Use `build` to see your current options before you start leveling.
            Use `sheet` to see your current race, class, level, and unlocked abilities.
            Use `gear` to inspect your starter loadout and `pack` to review any loot.
            Use `map` in any room to see the current area layout.
            Use cardinal movement like `w`, `n`, `e`, `s`, `u`, and `d` as your normal way of getting around.
            Use `w` from the inn to reach Brambleford Outfitters when you want to turn loot into silver.
            Use `s` from Town Green to reach Hobbyist's Wharf and try `fish`.
            Use `s` again from the wharf to reach Ironroot Forge and check `forge` for gear upgrades.
            Use `pray` at the Chapel of the Dawn Bell when you want a modest one-run blessing before a harder push.
            Use `cook` in the inn to see simple fish recipes, then `eat <meal>` to carry a buff into the field.
            Use `n` to reach the Training Yard, then `e` to reach the Great Observatory and `e` again for the Nexus Gate.
            Use `party` to review members or invite allies standing in the same room.
            Use `party where` to get route hints to your family and `party follow` when you want someone to lead.
            Use `shop` to review prices, `sell` to trade pack items, and `shift` to improve your next few sales.
            Use `quests` to see what places you should visit first.
            Use `travel` with no arguments when you want a named route list from your current room.
            Use `talk` or `read` in town if you want direct guidance without leaving the fiction.

            In dangerous rooms, use `enemies` to preview likely threats and `fight` to engage them.
            During combat, use `attack <enemy>` for a basic hit or `use <ability> [= target]`
            for your class action.

            ## Current Scope

            The live slice currently includes:

            - Brambleford Town Green
            - The Lantern Rest Inn
            - Brambleford Outfitters
            - Rat and Kettle Cellar
            - Hobbyist's Wharf
            - Ironroot Forge
            - Great Observatory
            - Nexus Gate
            - Mayor's Hall
            - Chapel of the Dawn Bell
            - Training Yard
            - East Gate
            - Goblin Road Trailhead
            - Old Fence Line
            - Wolf Turn
            - Fencebreaker Camp
            - Whispering Woods Trail
            - Old Stone Path
            - Briar Glade
            - Greymaw's Hollow
            - Old Barrow Causeway
            - Marker Row
            - Barrow Circle
            - Sunken Dais
            - Watchtower Approach
            - Breach Yard
            - Archer's Ledge
            - Cracked Tower Stairs
            - Blackreed's Roost
            - Sinkmouth Cut
            - Torchgut Tunnel
            - Bone Midden
            - Sludge Run
            - Feast Hall
            - Pot-King's Court
            - Junk-Yard Landing
            - Scrapway Verge
            - Relay Trench
            - Crane Grave
            - Anchor Pit
            - Fenreach Track
            - Reedflats
            - Boglight Hollow
            - Carrion Rise
            - Miretooth's Wallow
            - Drowned Causeway
            - Lantern Weir
            - Sluice Walk
            - Sunken Lock
            - Blackwater Lamp House
        """,
    },
]
