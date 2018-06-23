# Copyright (C) 2017
#
# This file is part of Rogueinabox.
#
# Rogueinabox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Rogueinabox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from .base import RewardGenerator


class StairSeeker_RewardGenerator(RewardGenerator):
    """Generate a reward for the last action:
        +10 for descending the stairs
        +1 for discovering new doors
        -0.01 for standing still
    """

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 10
        elif new_info.get_tile_count("+") > old_info.get_tile_count("+"):  # doors
            return 1
        elif self.player_standing_still(old_info, new_info):  # standing reward
            return -0.01
        return 0


class StairSeeker_13_RewardGenerator(RewardGenerator):
    """Generate a reward for the last action:
        +10000 for descending the stairs
        +1 for discovering new doors
        +1 for each new corridor tile discovered
    """

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 10000
        elif new_info.get_tile_count("+") > old_info.get_tile_count("+"):  # doors
            return 1
        elif new_info.get_tile_count("#") > old_info.get_tile_count("#"):  # passages
            return 1
        return 0


class StairSeeker_15_RewardGenerator(RewardGenerator):
    """Generate a reward for the last action:
        +10000 for descending the stairs
        +100 for discovering new doors
    """

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 10000
        elif new_info.get_tile_count("+") > old_info.get_tile_count("+"):  # doors
            return 100
        return 0


class ImprovedStairSeeker_RewardGenerator(StairSeeker_RewardGenerator):
    """Generate a reward for the last action:
        +10 for descending the stairs
        +1 for discovering new doors
        +1 for making the first step into a new corridor
        -0.01 for standing still
    """

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.get_tile_below_player() == '+':
            if new_info.get_tile_count("#") > old_info.get_tile_count("#"):  # has started to explore
                return 1
        return super().get_value(frame_history)


class ImprovedStairSeeker2_RewardGenerator(ImprovedStairSeeker_RewardGenerator):
    """Generate a reward for the last action:
        +100 for descending the stairs
        +1 for discovering new doors
        +1 for making the first step into a new corridor
        -0.01 for standing still
    """

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 100
        return super().get_value(frame_history)
