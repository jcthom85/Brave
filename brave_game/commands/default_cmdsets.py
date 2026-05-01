"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds

from .account import (
    CmdBraveCreate,
    CmdBraveDelete,
    CmdBraveLogout,
    CmdBraveOOCLook,
    CmdBravePlay,
    CmdBraveTheme,
    CmdBraveUnconnectedConnect,
    CmdBraveUnconnectedCreate,
    CmdBraveUnconnectedLook,
)
from .brave import CmdFinishPlaySilent
from .brave_arcade import CmdArcade, CmdArcadeSubmit
from .brave_combat import CmdBossGate, CmdCombatPreview, CmdEnemies, CmdFight, CmdFlee, CmdTarget, CmdUse
from .brave_creator import CmdContent
from .brave_explore import CmdCook, CmdEat, CmdEmote, CmdFish, CmdItem, CmdMap, CmdReel, CmdRest, CmdTravel
from .brave_party import CmdParty
from .brave_profile import CmdBuild, CmdClass, CmdCompanion, CmdGear, CmdMastery, CmdOath, CmdPack, CmdQuests, CmdRace, CmdSheet
from .brave_town import (
    CmdBravePopup,
    CmdForge,
    CmdPortals,
    CmdPray,
    CmdRead,
    CmdSell,
    CmdShift,
    CmdShop,
    CmdSteal,
    CmdTalk,
    CmdTinker,
)


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CmdBuild())
        self.add(CmdRace())
        self.add(CmdClass())
        self.add(CmdSheet())
        self.add(CmdMastery())
        self.add(CmdGear())
        self.add(CmdPack())
        self.add(CmdCompanion())
        self.add(CmdOath())
        self.add(CmdShop())
        self.add(CmdSell())
        self.add(CmdShift())
        self.add(CmdForge())
        self.add(CmdTinker())
        self.add(CmdMap())
        self.add(CmdFish())
        self.add(CmdReel())
        self.add(CmdCook())
        self.add(CmdEat())
        self.add(CmdEmote())
        self.add(CmdItem())
        self.add(CmdPortals())
        self.add(CmdParty())
        self.add(CmdQuests())
        self.add(CmdPray())
        self.add(CmdTravel())
        self.add(CmdFight())
        self.add(CmdBossGate())
        self.add(CmdEnemies())
        self.add(CmdTarget())
        self.add(CmdUse())
        self.add(CmdFlee())
        self.add(CmdCombatPreview())
        self.add(CmdRest())
        self.add(CmdArcade())
        self.add(CmdArcadeSubmit())
        self.add(CmdTalk())
        self.add(CmdBravePopup())
        self.add(CmdSteal())
        self.add(CmdRead())
        self.add(CmdContent())
        self.add(CmdFinishPlaySilent())


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CmdBraveOOCLook())
        self.add(CmdBravePlay())
        self.add(CmdBraveLogout())
        self.add(CmdBraveCreate())
        self.add(CmdBraveDelete())
        self.add(CmdBraveTheme())
        self.add(CmdFinishPlaySilent())


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.remove("look")
        self.add(CmdBraveUnconnectedConnect())
        self.add(CmdBraveUnconnectedCreate())
        self.add(CmdBraveUnconnectedLook())


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
