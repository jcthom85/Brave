import os
import sys
import types
from types import SimpleNamespace

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

chargen_stub = types.ModuleType("world.chargen")
chargen_stub.get_next_chargen_step = lambda *args, **kwargs: None
chargen_stub.has_chargen_progress = lambda *args, **kwargs: False
sys.modules.setdefault("world.chargen", chargen_stub)

from world.browser_views import build_combat_view, build_room_view


class DummyExit:
    def __init__(self, key, destination_key, *, direction=None, label=None):
        self.key = key
        self.destination = SimpleNamespace(key=destination_key)
        self.db = SimpleNamespace(
            brave_direction=direction or key,
            brave_exit_label=label,
        )


class DummyEntity:
    def __init__(self, key, kind, *, entity_id=None):
        self.key = key
        self.location = None
        self.db = SimpleNamespace(
            brave_entity_kind=kind,
            brave_entity_id=entity_id,
        )


class DummyRoom:
    def __init__(self, *, key="Lantern Rest", safe=True, description=None, room_id="lantern_rest"):
        self.key = key
        self.db = SimpleNamespace(
            brave_world="Brave",
            brave_zone="Brambleford",
            brave_safe=safe,
            brave_room_id=room_id,
            brave_activities=[],
            desc=description or "Warm light, steady conversation, and a clean path to the street.",
        )
        self.ndb = SimpleNamespace(brave_encounter=None)
        self.contents = []
        self.exits = [
            DummyExit("north", "Town Green"),
            DummyExit("east", "Kitchen"),
            DummyExit("up", "Guest Loft"),
        ]


class DummyCharacter:
    def __init__(
        self,
        char_id,
        key,
        room,
        class_key,
        resources,
        derived,
        abilities,
        *,
        inventory=None,
        race="human",
    ):
        self.id = char_id
        self.key = key
        self.location = room
        self.db = SimpleNamespace(
            brave_class=class_key,
            brave_race=race,
            brave_level=3,
            brave_primary_stats={
                "strength": 5,
                "agility": 4,
                "intellect": 3,
                "spirit": 3,
                "vitality": 5,
            },
            brave_derived_stats=dict(derived),
            brave_resources=dict(resources),
            brave_inventory=list(inventory or []),
            brave_silver=18,
            brave_party_id=None,
            brave_party_leader_id=None,
            brave_party_invites=[],
            brave_follow_target_id=None,
            brave_tutorial={},
            brave_welcome_shown=True,
        )
        self.ndb = SimpleNamespace()
        self._abilities = list(abilities)

    def ensure_brave_character(self):
        return None

    def get_unlocked_abilities(self):
        return list(self._abilities)

    def get_active_encounter(self):
        return None

    def get_active_companion(self):
        return {}


class DummyVisibleCharacter:
    def __init__(self, char_id, key, room):
        self.id = char_id
        self.key = key
        self.location = room
        self.db = SimpleNamespace(
            brave_party_id=None,
        )


class DummyEncounter:
    def __init__(self, room, participants, enemies, *, pending=None, states=None, atb_states=None, title="Mire Teeth"):
        self.obj = room
        self.db = SimpleNamespace(round=2, encounter_title=title, pending_actions=dict(pending or {}))
        self._participants = list(participants)
        self._enemies = list(enemies)
        self._states = dict(states or {})
        self._atb_states = dict(atb_states or {})

    def get_active_enemies(self):
        return list(self._enemies)

    def get_active_participants(self):
        return list(self._participants)

    def _describe_pending_action(self, character):
        return "basic attack"

    def _get_participant_state(self, character):
        actor_id = character["id"] if isinstance(character, dict) else character.id
        return self._states.get(
            actor_id,
            {
                "guard": 0,
                "bleed_turns": 0,
                "poison_turns": 0,
                "curse_turns": 0,
                "snare_turns": 0,
                "feint_turns": 0,
            },
        )

    def _get_actor_atb_state(self, character=None, enemy=None, companion=None):
        if companion is not None:
            return self._atb_states.get(f"c:{companion['id']}", {"phase": "charging", "gauge": 0, "ready_gauge": 100})
        if isinstance(character, dict):
            return self._atb_states.get(f"c:{character['id']}", {"phase": "charging", "gauge": 0, "ready_gauge": 100})
        if character is not None:
            return self._atb_states.get(f"p:{character.id}", {"phase": "charging", "gauge": 0, "ready_gauge": 100})
        if enemy is not None:
            return self._atb_states.get(f"e:{enemy['id']}", {"phase": "charging", "gauge": 0, "ready_gauge": 100})
        return {"phase": "charging", "gauge": 0, "ready_gauge": 100}


def _player_specs():
    return [
        ("Dad", "warrior", {"hp": 24, "mana": 0, "stamina": 13}, {"max_hp": 28, "max_mana": 0, "max_stamina": 16}, ["Strike"]),
        ("Peep", "mage", {"hp": 17, "mana": 16, "stamina": 8}, {"max_hp": 20, "max_mana": 20, "max_stamina": 10}, ["Bolt"]),
        ("Mara", "rogue", {"hp": 19, "mana": 4, "stamina": 12}, {"max_hp": 22, "max_mana": 6, "max_stamina": 14}, ["Slash"]),
        ("Rook", "paladin", {"hp": 26, "mana": 10, "stamina": 10}, {"max_hp": 30, "max_mana": 12, "max_stamina": 13}, ["Smite"]),
    ]


def _enemy_spec(template_key, enemy_id, *, key, hp, max_hp, rank=None):
    data = {
        "id": enemy_id,
        "template_key": template_key,
        "key": key,
        "hp": hp,
        "max_hp": max_hp,
    }
    if rank is not None:
        data["rank"] = rank
    return data


def build_room_fixture(*, version=1):
    room = DummyRoom(
        key="Lantern Rest" if version == 1 else "Lantern Rest After Look",
        description=(
            "Warm light, steady conversation, and a clean path to the street."
            if version == 1
            else "Fresh footsteps cross the floor and the street door swings once before settling."
        ),
    )
    viewer = DummyCharacter(
        77,
        "Dad",
        room,
        "warrior",
        {"hp": 37, "mana": 6, "stamina": 15},
        {"max_hp": 42, "max_mana": 8, "max_stamina": 18, "attack_power": 9, "armor": 4, "accuracy": 8, "dodge": 3},
        ["Strike"],
        inventory=[
            {"template": "innkeepers_fishpie", "quantity": 2},
            {"template": "lantern_carp", "quantity": 3},
        ],
    )
    ally = DummyVisibleCharacter(21, "Peep", room)
    extra_nearby = [DummyVisibleCharacter(22, "Rook", room)] if version != 1 else []
    entities = [
        DummyEntity("Kitchen Hearth", "readable", entity_id="kitchen_hearth"),
        DummyEntity("Mistress Elira Thorne", "npc", entity_id="mistress_elira_thorne"),
    ]
    view = build_room_view(
        room,
        viewer,
        visible_entities=entities,
        visible_chars=[ally] + extra_nearby,
        visible_threats=[
            {
                "display_name": "Road Wolves" if version == 1 else "Road Wolves Closing In",
                "composition": "2 Road Wolves",
                "count": 2,
                "detail": "2 Road Wolves" if version == 1 else "2 Road Wolves + 1 Scout",
                "badge": "2" if version == 1 else "3",
                "marker_icon": "warning",
                "command": "fight road_wolves_a",
                "tooltip": "Hostile threat nearby.",
            }
        ],
    )
    panels = dict(view.get("mobile_panels", {}))
    panels.setdefault("room", {})
    panels.setdefault("character", {})
    panels.setdefault("pack", {})
    panels.setdefault("quests", {})
    panels.setdefault("party", {})
    panels["room"] = {
        **panels["room"],
        "description": room.db.desc,
        "status_label": "Safe" if room.db.brave_safe else "Danger",
        "route_count": 3,
        "routes": [
            {"text": "Town Green", "detail": "North", "command": "north"},
            {"text": "Kitchen", "detail": "East", "command": "east"},
            {"text": "Guest Loft", "detail": "Up", "command": "up"},
        ],
        "vicinity": [
            {"text": "Peep", "detail": "Ally"},
            {"text": "Kitchen Hearth", "detail": "Readable"},
            {"text": "Mistress Elira Thorne", "detail": "Trainer"},
        ] + ([{"text": "Road Wolves", "detail": "Hostiles"}] if version == 1 else [{"text": "Road Wolves Closing In", "detail": "3 Hostiles"}]),
    }
    panels["character"] = {
        **panels["character"],
        "name": "Dad",
        "identity": "Human Warrior",
        "summary": "Frontline anchor ready to move.",
        "resources": [
            {"label": "HP", "value": "37 / 42"},
            {"label": "STA", "value": "15 / 18"},
            {"label": "MP", "value": "6 / 8"},
        ],
        "stats": [
            {"label": "Attack", "value": "9"},
            {"label": "Armor", "value": "4"},
            {"label": "Accuracy", "value": "8"},
            {"label": "Dodge", "value": "3"},
        ],
        "feature": {"name": "Shield Discipline", "summary": "Steady frontline pressure."},
    }
    panels["quests"] = {
        **panels["quests"],
        "active_count": 1,
        "completed_count": 0,
        "tracked": {
            "title": "First Watch",
            "meta": "Brambleford",
            "line": "Speak with the watch captain.",
            "objectives": [
                {"text": "Find Captain Nera", "completed": version != 1},
                {"text": "Report the road threat", "completed": False},
            ],
        },
        "active": [{"text": "First Watch", "detail": "Town"}],
    }
    panels["party"] = {
        **panels["party"],
        "in_party": True,
        "member_count": 2,
        "leader_name": "Dad",
        "members": [
            {"name": "Dad", "meta": "Leader", "resource": "HP 37/42"},
            {"name": "Peep", "meta": "Ally", "resource": "HP 30/30"},
        ],
        "invites": [],
    }
    panels["pack"] = {
        **panels["pack"],
        "silver": 18,
        "item_types": 2,
        "consumables": 2,
        "sections": [
            {"label": "Consumables", "count": 2, "items": [{"label": "Innkeeper's Fish Pie", "quantity": 2, "meta": "HP+18"}]},
            {"label": "Ingredients", "count": 3, "items": [{"label": "Lantern Carp", "quantity": 3}]},
        ],
    }
    view["mobile_panels"] = panels
    view["mobile_pack"] = panels["pack"]
    return view


def build_room_scene_fixture(*, version=1):
    return {
        "tracked_quest": {
            "title": "First Watch",
            "objectives": ["Find Captain Nera" if version == 1 else "Report the road threat"],
        }
    }


def build_combat_fixture(
    *,
    party_size=1,
    enemies=None,
    include_companion=False,
    title="Mire Teeth",
):
    room = DummyRoom(key="Wolf Turn", safe=False, description="The brush narrows to a fighting lane.", room_id="wolf_turn")
    players = []
    atb_states = {}
    for index, spec in enumerate(_player_specs()[:party_size], start=1):
        key, class_key, resources, derived, abilities = spec
        player = DummyCharacter(index, key, room, class_key, resources, derived, abilities)
        players.append(player)
        atb_states[f"p:{player.id}"] = {
            "phase": "ready" if index == 1 else "charging",
            "gauge": 100 if index == 1 else 35 + (index * 12),
            "ready_gauge": 100,
        }

    participants = list(players)
    if include_companion and players:
        companion = {
            "kind": "companion",
            "id": "c1",
            "owner_id": players[0].id,
            "key": "Marsh Hound",
            "icon": "pets",
            "hp": 11,
            "max_hp": 14,
        }
        participants.append(companion)
        atb_states["c:c1"] = {"phase": "charging", "gauge": 58, "ready_gauge": 100}

    enemy_list = list(enemies or [
        _enemy_spec("road_wolf", "e1", key="Road Wolf", hp=11, max_hp=16),
    ])
    for offset, enemy in enumerate(enemy_list, start=1):
        atb_states[f"e:{enemy['id']}"] = {
            "phase": "charging",
            "gauge": 28 + (offset * 14),
            "ready_gauge": 100,
        }

    encounter = DummyEncounter(room, participants, enemy_list, atb_states=atb_states, title=title)
    return build_combat_view(encounter, players[0])


def combat_scenarios():
    return {
        "solo_regular": build_combat_fixture(
            party_size=1,
            enemies=[_enemy_spec("road_wolf", "e1", key="Road Wolf", hp=11, max_hp=16)],
            title="Solo Roadside Clash",
        ),
        "party_duo": build_combat_fixture(
            party_size=2,
            enemies=[
                _enemy_spec("road_wolf", "e1", key="Road Wolf", hp=11, max_hp=16),
                _enemy_spec("road_wolf", "e2", key="Road Wolf", hp=11, max_hp=16),
            ],
            title="Two Against The Brush",
        ),
        "party_trio": build_combat_fixture(
            party_size=3,
            enemies=[
                _enemy_spec("road_wolf", "e1", key="Road Wolf", hp=11, max_hp=16),
                _enemy_spec("road_wolf", "e2", key="Road Wolf", hp=11, max_hp=16),
                _enemy_spec("grave_crow", "e3", key="Grave Crow", hp=9, max_hp=12),
            ],
            title="Three Hold The Track",
        ),
        "party_quad": build_combat_fixture(
            party_size=4,
            enemies=[
                _enemy_spec("road_wolf", "e1", key="Road Wolf", hp=11, max_hp=16),
                _enemy_spec("road_wolf", "e2", key="Road Wolf", hp=11, max_hp=16),
                _enemy_spec("grave_crow", "e3", key="Grave Crow", hp=9, max_hp=12),
                _enemy_spec("grave_crow", "e4", key="Grave Crow", hp=9, max_hp=12),
            ],
            title="Full Party Field Test",
        ),
        "ranger_companion": build_combat_fixture(
            party_size=1,
            include_companion=True,
            enemies=[_enemy_spec("road_wolf", "e1", key="Road Wolf", hp=11, max_hp=16)],
            title="Ranger With Companion",
        ),
        "elite_enemy": build_combat_fixture(
            party_size=1,
            enemies=[_enemy_spec("goblin_cutter", "e1", key="Goblin Cutter", hp=24, max_hp=30)],
            title="Elite Enemy Check",
        ),
        "boss_enemy": build_combat_fixture(
            party_size=1,
            enemies=[_enemy_spec("captain_varn_blackreed", "e1", key="Captain Varn Blackreed", hp=30, max_hp=30)],
            title="Boss Enemy Check",
        ),
        "boss_with_adds": build_combat_fixture(
            party_size=3,
            enemies=[
                _enemy_spec("captain_varn_blackreed", "e1", key="Captain Varn Blackreed", hp=30, max_hp=30),
                _enemy_spec("road_wolf", "e2", key="Road Wolf", hp=11, max_hp=16),
                _enemy_spec("road_wolf", "e3", key="Road Wolf", hp=11, max_hp=16),
            ],
            title="Boss And Adds Check",
        ),
        "mobile_card_count": build_combat_fixture(
            party_size=4,
            enemies=[
                _enemy_spec("road_wolf", "e1", key="Road Wolf", hp=11, max_hp=16),
                _enemy_spec("road_wolf", "e2", key="Road Wolf", hp=11, max_hp=16),
                _enemy_spec("road_wolf", "e3", key="Road Wolf", hp=11, max_hp=16),
                _enemy_spec("road_wolf", "e4", key="Road Wolf", hp=11, max_hp=16),
            ],
            title="Mobile Four And Four",
        ),
        "elite_vs_regular": build_combat_fixture(
            party_size=2,
            enemies=[
                _enemy_spec("road_wolf", "e1", key="Road Wolf", hp=11, max_hp=16),
                _enemy_spec("goblin_cutter", "e2", key="Goblin Cutter", hp=24, max_hp=30),
            ],
            title="Elite Versus Standard",
        ),
    }
