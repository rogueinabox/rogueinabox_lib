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
    def __init__(self, data_format="channels_last"):
        """
        :param str data_format:
            "channels_first" or "channels_last"
            represents the shape configuration, with the same meaning given by Keras, i.e.:
                a shape with height H, width W and C channels is represented as (C, H, W) with the "channel_first"
                option and (H, W, C) with "channels_last"
        """
        if data_format not in ("channels_first", "channels_last"):
            raise ValueError('data_format should be one of "channels_first" or "channels_last", got "%s" instead' %
                             data_format)
        self.data_format = data_format
        self._set_shape(data_format)
        self.reset()

    def reset(self):
        self.need_reset = False

    @abstractmethod
    def _set_shape(self, data_format):
        """The implementing class MUST set the state _shape (should be a tuple), wrt the 'data_format' option

        :param str data_format:
            "channels_first" or "channels_last"
            represents the shape configuration, with the same meaning given by Keras, i.e.:
                a shape with height H, width W and C channels is represented as (C, H, W) with the "channel_first"
                option and (H, W, C) with "channels_last"
        """
        self._shape = (0, 0, 0)

    def get_shape(self):
        """Returns state shape"""
        return self._shape

    def compute_state(self, frame_history):
        """Returns the state representation computed from the given frame history

        :param list[RogueFrameInfo] frame_history:
            list of parsed screen information
        :return:
            state representation as a numpy array
        """
        if self.is_frame_history_sufficient(frame_history):
            state = self.build_state(frame_history[-1], frame_history)
        else:
            state = self.empty_state()
        return state

    def is_frame_history_sufficient(self, frame_history):
        """Return whether the frame info is sufficient to compute a state or if a default one should be provided"""
        current_frame = frame_history[-1]
        return current_frame.has_statusbar()

    @abstractmethod
    def build_state(self, current_frame, frame_history):
        """Returns the numpy state representation computed from the given frame info

        :param RogueFrameInfo current_frame:
            parsed screen information of the current frame
        :param list[RogueFrameInfo] frame_history:
            list of parsed screen information, where current_frame == frame_history[-1]
        :return:
            state representation as a numpy ndarray
        :rtype: np.ndarray
        """
        pass

    def extract_channel(self, state, channel):
        """Returns a view of the channel in the state, wrt the 'data_format' option provided in init.
        Assigning elements to the view will also alter the state.

        :param np.ndarray state:
            state from which a channel should be extracted
        :param int channel:
            index of the channel to be extracted
        :return:
            channel view
        """
        if self.data_format == "channels_first":
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
        """Returns an all-zero ndarray of the correct shape

        :rtype: np.ndarray
        """
        return np.zeros(self._shape, dtype=np.uint8)


class Dummy_StateGenerator(StateGenerator):
    """Dummy generator that always returns None"""

    def _set_shape(self, data_format):
        self._shape = (0, 0, 0)

    def compute_state(self, frame_history):
        return None

    def build_state(self, current_frame, frame_history):
        pass
