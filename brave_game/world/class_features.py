"""Player-facing class feature definitions for Brave."""

CLASS_FEATURES = {
    "warrior": (
        {
            "name": "Martial Mastery",
            "icon": "construction",
            "summary": "Warriors can equip any weapon or armor they find, making them the broadest martial gear users in the game.",
        },
        {
            "name": "Line Control",
            "icon": "shield",
            "summary": "They hold the front, pull enemy pressure toward themselves, and make dangerous turns safer for everyone else.",
        },
    ),
    "cleric": (
        {
            "name": "Temple Rites",
            "icon": "church",
            "summary": "Clerics draw special blessings at chapels and temples, turning sacred spaces into stronger recovery hubs.",
        },
        {
            "name": "Holy Recovery",
            "icon": "favorite",
            "summary": "They remain the best direct healer and cleanser in the roster, strongest when the party is close to collapse.",
        },
    ),
    "ranger": (
        {
            "name": "Companion Bond",
            "icon": "travel_explore",
            "summary": "Rangers hunt with a bonded companion that reinforces marks, chase pressure, and target control.",
        },
        {
            "name": "Quarry Focus",
            "icon": "visibility",
            "summary": "They are built around choosing one prey, holding the angle, and bringing it down methodically.",
        },
    ),
    "mage": (
        {
            "name": "Spellbook Study",
            "icon": "menu_book",
            "summary": "Mages can expand their arcane kit through discovered spellbooks as well as normal leveling.",
        },
        {
            "name": "Elemental Burst",
            "icon": "auto_awesome",
            "summary": "They are the purest offensive spellcaster, converting brief openings into decisive magical damage.",
        },
    ),
    "rogue": (
        {
            "name": "Illicit Access",
            "icon": "key",
            "summary": "Rogues can work clean one-time theft angles on authored marks, opening up silver, contraband, and illicit side access other classes miss.",
        },
        {
            "name": "Opportunist",
            "icon": "swords",
            "summary": "They thrive on brief openings, compromised targets, and sudden positional payoff rather than steady pressure.",
        },
    ),
    "paladin": (
        {
            "name": "Sacred Oaths",
            "icon": "military_tech",
            "summary": "Paladins swear authored sacred oaths that change how the Dawn Bell and later holy relics answer their vigil.",
        },
        {
            "name": "Temple Vigil",
            "icon": "church",
            "summary": "At chapels and temples they can take a harder protective rite than other classes, preparing to guard the party.",
        },
    ),
    "druid": (
        {
            "name": "Primal Forms",
            "icon": "forest",
            "summary": "Druids shape the field with living magic, then exploit it through limited beast forms such as wolf and bear.",
        },
        {
            "name": "Grove Trials",
            "icon": "eco",
            "summary": "New forms are meant to come from sacred groves, primal trials, and deeper contact with the wild world.",
        },
    ),
}


def get_class_features(class_key):
    """Return authored feature entries for one class."""

    return tuple(CLASS_FEATURES.get(class_key, ()))
