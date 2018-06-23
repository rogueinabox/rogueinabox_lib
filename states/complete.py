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

from .base import StateGenerator


class FullMap_StateGenerator(StateGenerator):
    """Generates a 22x80 state comprising the entire map composed of 'channels' layers, inserting the position
    of tiles in configurable layers and values, e.g. the stairs in layer 'stairs_channel' with value 'stairs_value'.
    Also, if 'forget_hidden_floors' is True the generator hides floor tiles that are not currently visible but were
    so in a previous frame (e.g. when moving in dark rooms).

    By default, two channels are built:
        first channel:
            - walls (value: 1)
            - doors and corridors (value: 10)
        second channel:
            - rogue, covers the stairs if they are present (value: 1)
            - stairs (value: 10)
            - amulet (value: 100)
    """

    channels = 2

    walls_channel     = 0
    walls_value       = 1

    doors_channel     = 0
    doors_value       = 10

    corridors_channel = 0
    corridors_value   = 10

    floor_channel     = 0
    floor_value       = 0
    forget_hidden_floors = True

    stairs_channel    = 1
    stairs_value      = 10

    amulet_channel    = 1
    amulet_value      = 100

    rogue_channel     = 1
    rogue_value       = 1

    def _set_shape(self, data_format):
        self._shape = (22, 80, self.channels) if data_format == 'channels_last' else (self.channels, 22, 80)

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()

        # stairs
        self.set_channel(state, self.stairs_channel,
                         current_frame.get_list_of_positions_by_tile("%"), self.stairs_value)

        # amulet
        self.set_channel(state, self.amulet_channel,
                         current_frame.get_list_of_positions_by_tile(","), self.amulet_value)

        # rogue (covers the stairs if they are present)
        self.set_channel(state, self.rogue_channel,
                         current_frame.get_list_of_positions_by_tile("@"), self.rogue_value)

        # walls
        self.set_channel(state, self.walls_channel,
                         current_frame.get_list_of_positions_by_tile("|"), self.walls_value)
        self.set_channel(state, self.walls_channel,
                         current_frame.get_list_of_positions_by_tile("-"), self.walls_value)

        # doors and corridors
        self.set_channel(state, self.doors_channel,
                         current_frame.get_list_of_positions_by_tile("+"), self.doors_value)
        self.set_channel(state, self.corridors_channel,
                         current_frame.get_list_of_positions_by_tile("#"), self.corridors_value)

        if self.floor_value != 0:
            floors = current_frame.get_list_of_positions_by_tile(".")
            if self.forget_hidden_floors:
                floors = self.filter_out_hidden(floors, current_frame)
            self.set_channel(state, self.floor_channel, floors, self.floor_value)

        return state


class FullMap_5L_forget_StateGenerator(FullMap_StateGenerator):
    """Generates a 22x80 state comprising the entire map composed of 5 channels:
        channel 0:
            - walls
        channel 1:
            - doors and corridors
        channel 2:
            - floor
        channel 3:
            - stairs
            - amulet (value: 10)
        channel 4:
            - rogue
        All unspecified values are 1.
    """

    channels = 5

    walls_channel     = 0
    walls_value       = 1

    doors_channel     = 1
    doors_value       = 1

    corridors_channel = 1
    corridors_value   = 1

    floor_channel     = 2
    floor_value       = 1

    stairs_channel    = 3
    stairs_value      = 1

    amulet_channel    = 3
    amulet_value      = 10

    rogue_channel     = 4
    rogue_value       = 1


class FullMap_5L_remember_StateGenerator(FullMap_5L_forget_StateGenerator):
    """See FullMap_5L_forget_StateGenerator. This version retains explored dark room tiles."""

    forget_hidden_floors = False


class FullMap_6L_forget_StateGenerator(FullMap_5L_forget_StateGenerator):
    """Generates a 22x80 state comprising the entire map composed of 5 channels:
            channel 0:
                - walls
            channel 1:
                - doors and corridors
            channel 2:
                - floor
            channel 3:
                - stairs
            channel 4:
                - rogue
            channel 5:
                - amulet
            All values are 1.
        """

    channels = 6

    amulet_channel = 5
    amulet_value   = 1
