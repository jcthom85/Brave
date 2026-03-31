import os
import unittest

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.data.entity_dialogue import STATIC_READ_RESPONSES, TALK_RULES
from world.data.starting_world import WORLD_OBJECTS
from world.interactions import DYNAMIC_READ_HANDLERS, DYNAMIC_TALK_HANDLERS


def _is_tutorial_object(world_object):
    return str(world_object.get("location", "")).startswith("tutorial_")


class InteractionCoverageTests(unittest.TestCase):
    def test_non_tutorial_npcs_have_response_paths(self):
        covered = set(TALK_RULES) | set(DYNAMIC_TALK_HANDLERS)
        missing = [
            obj["id"]
            for obj in WORLD_OBJECTS
            if obj.get("kind") == "npc" and not _is_tutorial_object(obj) and obj["id"] not in covered
        ]
        self.assertEqual([], missing)

    def test_non_tutorial_readables_have_response_paths(self):
        covered = set(STATIC_READ_RESPONSES) | set(DYNAMIC_READ_HANDLERS)
        missing = [
            obj["id"]
            for obj in WORLD_OBJECTS
            if obj.get("kind") == "readable" and not _is_tutorial_object(obj) and obj["id"] not in covered
        ]
        self.assertEqual([], missing)
