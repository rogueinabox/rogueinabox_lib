# Copyright (C) 2017 Andrea Asperti, Carlo De Pieri, Gianmaria Pedrini, Francesco Sovrano
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
from abc import ABC, abstractmethod


# ABSTRACT CLASSES

class StateGenerator(ABC):
    def __init__(self, channels_first=False):
        self.channels_first = channels_first
        self._set_shape(channels_first)
        self.reset()

    def reset(self):
        self.need_reset = False

    @abstractmethod
    def _set_shape(self, channels_first):
        """The implementing class MUST set the state _shape (should be a tuple)."""
        self._shape = (0, 0, 0)

    def get_shape(self):
        """Returns state shape"""
        return self._shape

    def compute_state(self, info):
        """Returns the state representation computed from the given frame info

        :param RogueFrameInfo info:
            parsed screen information
        :return:
            state representation as a dict:
            {'state': np.ndarray, 'frame_info': RogueFrameInfo}
        """
        if self.is_frame_sufficient(info):
            state = self.build_state(info)
        else:
            state = self.empty_state()
        return {'state': state, 'frame_info': info}

    def is_frame_sufficient(self, info):
        """Return whether the frame info is sufficient to compute a state or if a default one should be provided"""
        return info.has_statusbar()

    @abstractmethod
    def build_state(self, info):
        """Returns the numpy state representation computed from the given frame info

        :param RogueFrameInfo info:
            parsed screen information
        :return:
            state representation as a numpy ndarray
        :rtype: np.ndarray
        """
        pass

    def extract_channel(self, state, channel):
        """Returns a view of the channel in the state, wrt the 'channels_first' option provided in init.
        Assigning elements to the view will also alter the state.

        :param np.ndarray state:
            state from which a channel should be extracted
        :param int channel:
            index of the channel to be extracted
        :return:
            channel view
        """
        if self.channels_first:
            return state[channel, :, :]
        else:
            return state[:, :, channel]

    def set_channel(self, state, channel, positions, value):
        """Assigns 'value' to each position in 'positions' of the channel in the given state

        :param np.ndarray state:
            state to which assign values
        :param int channel:
            state channel to be used
        :param list[tuple[int,int]] positions:
            coordinates that should be assinged in the channel of the state
        :param float value:
            value to be assigned
        :return:
            reference to state, however the assignments are made "in place"
        """
        channel_view = self.extract_channel(state, channel)
        for pos in positions:
            if pos:
                i, j = pos
                channel_view[i, j] = value
        return state

    def empty_state(self):
        """Returns an all-zero ndarray of the correct shape"""
        return np.zeros(self._shape, dtype=np.uint8)
