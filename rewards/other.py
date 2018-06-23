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

import numpy as np
from .base import RewardGenerator


class E_D_W_RewardGenerator(RewardGenerator):
    """Generate a reward for the last action:
        +100 for descending the stairs
        +5 for exploring the map
        -0.1 living reward
    """

    def set_default_reward(self):
        self.default_reward = -1

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 100
        elif new_info.get_known_tiles_count() > old_info.get_known_tiles_count():
            return 5
        else:
            return -0.1


class E_D_Ps_W_RewardGenerator(E_D_W_RewardGenerator):
    """Generate a reward for the last action:
        +100 for descending the stairs
        +5 for exploring the map
        -1 for standing still
        -0.1 living reward
    """

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if self.player_standing_still(old_info, new_info):
            return -1
        return super().get_value(frame_history)


class Clipped_RewardGenerator(RewardGenerator):
    """Generate a reward for the last action:
        +1 for descending the stairs
        +1 for each new door discovered
        +1 for each new corridor tile discovered
        -0.05 for standing still
    """

    def normalize_value(self, reward):
        return np.clip(reward, -1, 1)

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 10000
        elif new_info.get_tile_count("+") > old_info.get_tile_count("+"):  # doors
            return 100
        elif new_info.get_tile_count("#") > old_info.get_tile_count("#"):  # passages
            return 1
        elif self.player_standing_still(old_info, new_info):  # standing reward
            return -0.05
        return 0
