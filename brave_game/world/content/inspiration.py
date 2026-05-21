"""
Creative inspiration logic for Brave Creator Studio.
Provides contextual suggestions for descriptions, NPCs, and quests.
"""

from __future__ import annotations
import random
from typing import Dict, List, Optional

def generate_room_description(room_id: str, zone: str, registry) -> str:
    """Generate a room description based on zone and context."""
    
    zone_themes = {
        "brambleford": {
            "adjectives": ["moss-choked", "sturdy", "thicket-rimmed", "forgotten", "weathered"],
            "features": ["timber beams", "wild vines", "stone hearth", "creaky floors"],
            "moods": ["A sense of quiet resilience hangs in the air.", "Nature is slowly reclaiming the edges of this space.", "The scent of damp earth and old wood is thick here."]
        },
        "hollow_woods": {
            "adjectives": ["gloomy", "whispering", "twisted", "shadow-drenched", "unnatural"],
            "features": ["pale fungi", "knotted roots", "shifting mists", "distant owl calls"],
            "moods": ["The trees seem to lean in as if listening.", "Light struggles to reach the forest floor through the dense canopy.", "A cold breeze carries the faint sound of a cracking twig."]
        }
    }
    
    theme = zone_themes.get(zone.lower(), {
        "adjectives": ["plain", "functional", "stark", "unremarkable"],
        "features": ["simple stone", "wooden furniture", "faint dust", "stable walls"],
        "moods": ["It is a place of utility and quiet."]
    })
    
    adj = random.choice(theme["adjectives"])
    feat = random.choice(theme["features"])
    mood = random.choice(theme["moods"])
    
    return f"This {adj} area is defined by {feat}. {mood}"

def generate_npc_details(room_id: str, zone: str, registry) -> Dict:
    """Generate NPC details like name, role, and description."""
    
    names = ["Kaelen", "Mira", "Silas", "Elara", "Finn", "Gretel", "Bryn", "Oryn"]
    roles = ["Scavenger", "Guard", "Hermit", "Merchant", "Traveler", "Chronicler"]
    
    name = random.choice(names)
    role = random.choice(roles)
    
    desc = f"{name} is a {role.lower()} who has seen better days. They carry themselves with the weary grace of someone used to the frontier."
    
    return {
        "key": name,
        "role": role,
        "desc": desc,
        "dialogue": [
            {"id": "greeting", "text": f"Stay clear of the deep shadows, traveler. The {zone} has a way of hiding its teeth."},
            {"id": "about_self", "text": f"I've been a {role.lower()} for more years than I care to count."}
        ]
    }

def generate_quest_hook(npc_id: str, zone: str, registry) -> Dict:
    """Generate a quest hook based on an NPC."""
    
    goals = [
        "Recover a lost locket from the thicket.",
        "Deliver a warning to the next outpost.",
        "Gather three glowing fungi for a remedy.",
        "Scout the old watchtower for signs of movement."
    ]
    
    goal = random.choice(goals)
    
    return {
        "title": f"The {zone.title()} Task",
        "summary": f"Help an inhabitant of {zone} with a pressing concern: {goal}",
        "objectives": [
            {"type": "talk_to_npc", "npc_id": npc_id, "count": 1}
        ],
        "reward_note": "A handful of tokens and the gratitude of a local."
    }

def get_inspiration(kind: str, context: Dict, registry) -> Dict:
    """Main entry point for inspiration requests."""
    
    room_id = context.get("room_id", "")
    zone = context.get("zone", "The Frontier")
    
    if kind == "room_description":
        return {"desc": generate_room_description(room_id, zone, registry)}
    
    if kind == "npc":
        return generate_npc_details(room_id, zone, registry)
    
    if kind == "quest":
        npc_id = context.get("npc_id", "unknown_npc")
        return generate_quest_hook(npc_id, zone, registry)
    
    return {"error": f"Unknown inspiration kind: {kind}"}
