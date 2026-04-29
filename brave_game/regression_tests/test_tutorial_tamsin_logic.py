import unittest
from types import SimpleNamespace
from world.tutorial import _talk_tamsin, begin_tutorial

class DummyCharacter:
    def __init__(self):
        self.db = SimpleNamespace(
            brave_tutorial=None,
            brave_tutorial_current_step=None,
            brave_quests={},
            brave_class="warrior",
        )
        self.ndb = SimpleNamespace()

class TamsinLogicTests(unittest.TestCase):
    def test_tamsin_reminder_logic(self):
        character = DummyCharacter()
        begin_tutorial(character)
        
        # First talk
        response1 = _talk_tamsin(character, is_action=True)
        self.assertIn("Hear that bell?", response1)
        
        # Second talk (reminder)
        response2 = _talk_tamsin(character, is_action=True)
        self.assertIn("East to the shed", response2)

if __name__ == "__main__":
    unittest.main()
