import re
import numpy as np
import itertools
import copy

from .frame_info import RogueFrameInfo


class RogueParser:
    """Stateful rogue screen parser.
    Provides a convenient way of accessing rogue screen information.

    N.B. instances of RogueParser are stateful, they store an internal representation that is updated on each
    .parse_screen() call for performance reasons.
    If you need to parse non-consecutive screens, call .reset() after each one.
    """

    # regexp used to parse the status bar
    parse_statusbar_re = re.compile(r"""
                    Level:\s*(?P<dungeon_level>\d*)\s*
                    Gold:\s*(?P<gold>\d*)\s*
                    Hp:\s*(?P<current_hp>\d*)\((?P<max_hp>\d*)\)\s*
                    Str:\s*(?P<current_strength>\d*)\((?P<max_strength>\d*)\)\s*
                    Arm:\s*(?P<armor>\d*)\s*
                    Exp:\s*(?P<exp_level>\d*)/(?P<tot_exp>\d*)\s*
                    (?P<status>(Hungry|Weak|Faint)?)\s*
                    (Cmd:\s*(?P<command_count>\d*))?""", re.VERBOSE)

    # regexp used to extract the command count in custom rogue builds
    cmd_count_re = re.compile(r"Cmd:\s*(?P<command_count>\d*)", re.VERBOSE)

    # tile type -> set of tiles of that type
    tiles_types_dict = {
        "environment": set(tile for tile in '#+.%-|'),
        "items":       set(tile for tile in '^*!?$:)],=/'),
        "monsters":    set(tile for tile in 'KEBSHIROZLCQANYFTWPXUMVGJD'),
        "agents":      set(tile for tile in '@'),
    }

    def __init__(self):
        self.last_info = None

    def reset(self):
        """reset internal state, call this before parsing a non-consecutive screen"""
        self.pixel = self._build_pixel_dict()
        self.environment_map = self.empty_environment_map()  # reset the environment state
        self.environment_dict = self._build_type_dict("environment")
        self.last_info = None

    def _build_pixel_dict(self):
        result = {}
        for key in self.tiles_types_dict:
            result[key] = self._build_type_dict(key)
        return result

    def _build_type_dict(self, key):
        result = {}
        for pixel in self.tiles_types_dict[key]:
            result[pixel] = []
        return result

    @staticmethod
    def empty_environment_map():
        env = []
        for x in range(22):
            row = []
            for y in range(80):
                row.append(" ")
            env.append(row)
        return env

    def build_statusbar(self, screen):
        bar = {}
        # parse status bar, status bar is the last line
        statusbar = screen[-1]
        parsed_statusbar = self.parse_statusbar_re.match(statusbar)
        if (parsed_statusbar != None):  # parsed_statusbar of an empty screen is None
            statusbar_infos = parsed_statusbar.groupdict()
            for info in statusbar_infos:
                try:
                    bar[info] = int(statusbar_infos[info])
                except:
                    bar[info] = statusbar_infos[info]
            bar["is_empty"] = False
        else:
            bar["is_empty"] = True
        return bar

    def parse_screen(self, screen):
        """return a RogueFrameInfo built from the given screen.
        N.B. this is a stateful operation as an internal state is stored and updated between subsequent calls.
        If you need to parse an unrelated screen, call .reset() first.

        :param list[str] screen:
            rogue screen
        :rtype: RogueFrameInfo
        """
        # get statusbar
        new_statusbar = self.build_statusbar(screen)

        # get old level
        old_level = 1
        if self.last_info and not self.last_info.statusbar["is_empty"]:
            old_level = self.last_info.statusbar["dungeon_level"]

        if new_statusbar["is_empty"]:
            # this is a tombstone (death) screen or any other screen without a status bar
            new_statusbar["dungeon_level"] = old_level
            self.last_info = RogueFrameInfo(pixel={}, map=[[]], statusbar=new_statusbar, screen=screen)
            return self.last_info

        # get new level
        new_level = new_statusbar["dungeon_level"]

        # check whether the environment has changed -> the environment cannot change unless the player has reached a new level
        if new_level != old_level:
            self.environment_map = self.empty_environment_map()  # reset the environment state
            self.environment_dict = self._build_type_dict("environment")

        # optimal info initialisation
        self.pixel = {}
        self.pixel["agents"] = self._build_type_dict("agents")
        self.pixel["monsters"] = self._build_type_dict("monsters")
        self.pixel["items"] = self._build_type_dict("items")

        # populate the info dictionary
        for x, j in itertools.product(range(1, 23), range(80)):
            pixel = screen[x][j]
            i = x - 1  # The internal map has a different size and it is 22x80, on the other hand the screen is 24x80. The first and the last screen line contains useless metadata
            if pixel in self.tiles_types_dict["environment"]:  # immobile environment
                # once initialised, there is no need to re-initialise it again because the environment is immobile
                if str(self.environment_map[i][j]) == ' ':
                    self.environment_map[i][j] = pixel
                    self.environment_dict[pixel].append((i, j))
            elif pixel in self.tiles_types_dict["items"]:  # items
                self.pixel["items"][pixel].append((i, j))
            elif pixel in self.tiles_types_dict["agents"]:  # agents
                self.pixel["agents"][pixel].append((i, j))
            elif pixel in self.tiles_types_dict["monsters"]:  # monsters
                self.pixel["monsters"][pixel].append((i, j))

        # copies must be returned in order to be able to keep a history and compare different frames
        self.pixel["environment"] = copy.deepcopy(self.environment_dict)
        self.last_info = RogueFrameInfo(pixel=self.pixel, map=copy.deepcopy(self.environment_map), statusbar=new_statusbar, screen=screen)
        return self.last_info

    def get_cmd_count(self, screen):
        """Return cmd count of the screen for custom rogue build

        :rtype: int
        :raises RuntimeError:
            if the screen is not fully refrehsed and the last line is not complete and in particular does not
            contain the Cmd count yet
        """
        try:
            return int(self.cmd_count_re.search(screen[-1]).group("command_count"))
        except (AttributeError, ValueError):
            raise RuntimeError('screen not fully refreshed')
