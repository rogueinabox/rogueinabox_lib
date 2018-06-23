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


class Normalised_RewardGenerator(RewardGenerator):
    """Generate a reward for the last action, mapped from [-500,500] to [-1,1]:
        +250 for descending the stairs
        +10 for each new door discovered
        -1 for standing still
    """

    def normalize_value(self, reward):
        return self.remap(reward, 500, 1)  # from [-500,500] to [-1,1]

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 250
        elif new_info.get_tile_count("+") > old_info.get_tile_count("+"):  # doors
            return 10
        elif self.player_standing_still(old_info, new_info):  # standing reward
            return -1
        return 0


class Normalised_2_RewardGenerator(RewardGenerator):
    """Generate a reward for the last action, mapped from [-500,500] to [-1,1]:
        +250 for descending the stairs
        +10 for each new door discovered
        +1 for each new corridor tile discovered
        -1 for standing still
    """

    def normalize_value(self, reward):
        return self.remap(reward, 500, 1)  # from [-500,500] to [-1,1]

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 250
        elif new_info.get_tile_count("+") > old_info.get_tile_count("+"):  # doors
            return 10
        elif new_info.get_tile_count("#") > old_info.get_tile_count("#"):  # passages
            return 1
        elif self.player_standing_still(old_info, new_info):  # standing reward
            return -1
        return 0


class Normalised_3_RewardGenerator(RewardGenerator):
    """Generate a reward for the last action, mapped from [-500,500] to [-1,1]:
        +250 for descending the stairs
        +10 for each new door discovered
        +5 for each new corridor tile discovered
        -5 for standing still
    """

    def normalize_value(self, reward):
        return self.remap(reward, 2500, 1)  # from [-2500,2500] to [-1,1]

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 250
        elif new_info.get_tile_count("+") > old_info.get_tile_count("+"):  # doors
            return 10
        elif new_info.get_tile_count("#") > old_info.get_tile_count("#"):  # passages
            return 5
        elif self.player_standing_still(old_info, new_info):  # standing reward
            return -5
