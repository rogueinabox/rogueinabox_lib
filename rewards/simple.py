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


class StairsOnly_RewardGenerator(RewardGenerator):

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 10
        return 0


class StairsOnly_NthLevel_RewardGenerator(RewardGenerator):
    """Generates a reward of 10 whenever a higher level is reached.
    If 'objective_level' is reached, declares the game won.
    """

    objective_level = 10

    def reset(self):
        super().reset()
        self.last_level = 1

    def get_value(self, frame_history):
        last_frame = frame_history[-1]
        if last_frame.statusbar["dungeon_level"] > self.last_level:
            self.last_level = last_frame.statusbar["dungeon_level"]
            if self.last_level >= self.objective_level:
                self.goal_achieved = True
            return 10
        return 0


class AmuletVictory_RewardGenerator(RewardGenerator):
    """Generates a positive reward when the amulet is taken and when the game is won.
    By default, the generated rewards have value 10.
    """

    reward_value = 10

    def reset(self):
        super().reset()
        self.amulet_taken = False

    def is_frame_history_sufficient(self, frame_history):
        if len(frame_history) >= 2:
            old_info = frame_history[-2]
            return old_info.has_statusbar()
        return False

    def get_value(self, frame_history):

        old_info = frame_history[-2]
        new_info = frame_history[-1]

        if not self.amulet_taken:
            amulet = old_info.get_list_of_positions_by_tile(',')
            try:
                if old_info.statusbar["dungeon_level"] == new_info.statusbar["dungeon_level"]:
                    if amulet[0] == new_info.get_player_pos():
                        self.amulet_taken = True
                        return self.reward_value
                    return 0
            except (IndexError, KeyError):
                # amulet not visible
                return 0

        if new_info.is_victory_frame():
            self.goal_achieved = True
            return self.reward_value

        return 0
