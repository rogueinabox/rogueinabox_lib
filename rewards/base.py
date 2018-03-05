# Copyright (C) 2017 Andrea Asperti, Carlo De Pieri, Gianmaria Pedrini
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

from abc import ABC, abstractmethod


# ABSTRACT CLASS

class RewardGenerator(ABC):
    """Base class for reward generators.
    Concrete classes must compute the reward in .get_value().

    N.B. Instance attribute .goal_achieved is used by rogueinabox to determine if an episode is won
    """

    def __init__(self):
        self.set_default_reward()
        self.reset()

    def set_default_reward(self):
        """The implementing class MUST set self.default_reward.
        This is used in .compute_reward() when the frame history is not sufficient to compute a reward.
        """
        self.default_reward = 0

    def reset(self):
        self.goal_achieved = False

    def compute_reward(self, frame_history):
        """return a reward computed from the given frame history

        :param list[RogueFrameInfo] frame_history:
            list of frame information
        :return:
            reward
        """
        if self.is_frame_history_sufficient(frame_history):
            return self.normalize_value(self.get_value(frame_history))
        return self.default_reward

    def is_frame_history_sufficient(self, frame_history):
        """return whether the frame history is sufficient to compute a reward or if a default one should be provided"""
        if len(frame_history) >= 2:
            old_info = frame_history[-2]
            new_info = frame_history[-1]
            return old_info.has_statusbar() and new_info.has_statusbar()
        return False

    @abstractmethod
    def get_value(self, frame_history):
        """the implementing class should compute the reward from the given frame history and return it"""
        return 0

    def normalize_value(self, reward):
        """maps the input reward to some value.
        This is used in .compute_reward() on the value returned by .get_value().
        This is useful for subclassing a concrete class without altering its .get_value() logic.
        """
        return reward

    @staticmethod
    def clip_reward(reward):
        # clip reward to 1 or -1
        if reward > 0:
            reward = 1
        else:
            reward = -1
        return reward

    @staticmethod
    def player_standing_still(old_info, new_info):
        return old_info.get_player_pos() == new_info.get_player_pos()

    @staticmethod
    def manhattan_distance(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def remap(x, oMax, nMax):
        # range check
        oMin = -oMax
        nMin = -nMax

        # check reversed input range
        reverseInput = False
        oldMin = min(oMin, oMax)
        oldMax = max(oMin, oMax)
        if not oldMin == oMin:
            reverseInput = True

        # check reversed output range
        reverseOutput = False
        newMin = min(nMin, nMax)
        newMax = max(nMin, nMax)
        if not newMin == nMin:
            reverseOutput = True

        portion = (x - oldMin) * (newMax - newMin) / (oldMax - oldMin)
        if reverseInput:
            portion = (oldMax - x) * (newMax - newMin) / (oldMax - oldMin)

        result = portion + newMin
        if reverseOutput:
            result = newMax - portion

        return result
