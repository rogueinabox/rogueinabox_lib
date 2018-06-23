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


class SingleLayer_StateGenerator(StateGenerator):
    """Generates a state composed of a single layer containing (with different values):
        - the rogue
        - the stairs
        - the walls
        - the doors and corridors
    """

    def _set_shape(self, data_format):
        self._shape = (1, 22, 80) if data_format == "channels_first" else (22, 80, 1)

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("%"), 4)  # stairs
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("|"), 8)  # walls
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("-"), 8)  # walls
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("+"), 16)  # doors
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("#"), 16)  # tunnel
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("@"), 2)  # rogue (player)
        return state


class DoubleLayer_StateGenerator(StateGenerator):
    """Generates a state composed of 2 layers containing:
        - layer 1:
            - the stairs
            - the walls
            - the doors and corridors
        - layer 2:
            - the rogue
    """

    def _set_shape(self, data_format):
        self._shape = (2, 22, 80) if data_format == "channels_first" else (22, 80, 2)

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()

        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("%"), 4)  # stairs
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("|"), 2)  # walls
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("-"), 2)  # walls
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("+"), 1)  # doors
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("#"), 1)  # tunnel

        self.set_channel(state, 1, current_frame.get_list_of_positions_by_tile("@"), 1)  # rogue (player)

        return state


class TripleLayer_StateGenerator(StateGenerator):
    """Generates a state composed of 3 layers containing:
        - layer 1:
            - corridors
            - rogue if he's on a corridor
        - layer 2:
            - stairs
            - rogue if he's on the stairs
        - layer 3:
            - floor tiles
            - doors
            - rogue if he's not on corridors or stairs
        The numerical values used are the same except for the rogue.
    """

    def _set_shape(self, data_format):
        self._shape = (3, 22, 80) if data_format == "channels_first" else (22, 80, 3)

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()
        # layer 1
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("#"), 1)  # tunnel
        # layer 2
        self.set_channel(state, 1, current_frame.get_list_of_positions_by_tile("%"), 1)  # stairs
        # layer 3
        self.set_channel(state, 2, current_frame.get_list_of_positions_by_tile("."), 1)  # floor
        self.set_channel(state, 2, current_frame.get_list_of_positions_by_tile("+"), 1)  # doors

        pixel = current_frame.get_tile_below_player()
        if pixel == '#':  # tunnel
            self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("@"), 2)
        elif pixel == "%":  # stairs
            self.set_channel(state, 1, current_frame.get_list_of_positions_by_tile("@"), 2)
        else:  # floor
            self.set_channel(state, 2, current_frame.get_list_of_positions_by_tile("@"), 2)
        return state


class TripleLayer_1_StateGenerator(TripleLayer_StateGenerator):
    """Generates a state composed of 3 identical layers containing (with different values):
        - stairs
        - walls
        - doors and corridors
        The rogue is placed on layer 1 if he's on a corridor, layer 2 if he's on the stairs and layer 3 otherwise
    """

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()

        # TODO: why is it useful to have identical channels?
        n_channels = self._shape[0] if self.data_format == "channels_first" else self._shape[-1]
        for c in range(n_channels):
            self.set_channel(state, c, current_frame.get_list_of_positions_by_tile("%"), 4)  # stairs
            self.set_channel(state, c, current_frame.get_list_of_positions_by_tile("|"), 8)  # walls
            self.set_channel(state, c, current_frame.get_list_of_positions_by_tile("-"), 8)  # walls
            self.set_channel(state, c, current_frame.get_list_of_positions_by_tile("+"), 16)  # doors
            self.set_channel(state, c, current_frame.get_list_of_positions_by_tile("#"), 16)  # tunnel

        pixel = current_frame.get_tile_below_player()
        # set the rogue (player) position for last otherwise it may be overwritten by other positions!
        if pixel == '#':  # tunnel
            self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("@"), 2)
        elif pixel == "%":  # stairs
            self.set_channel(state, 1, current_frame.get_list_of_positions_by_tile("@"), 2)
        else:  # floor
            self.set_channel(state, 2, current_frame.get_list_of_positions_by_tile("@"), 2)
        return state


class TripleLayer_2_StateGenerator(TripleLayer_StateGenerator):
    """Generates a state composed of 3 layers containing:
        - layer 1:
            - corridors
            - doors
            - rogue if he's on a corridor
        - layer 2:
            - stairs
            - rogue if he's on the stairs
        - layer 3:
            - walls
            - stairs
            - rogue if he's not on corridors or stairs
        The numerical values used are the same except for the rogue and the stairs on layer 3.
    """

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()

        # layer 1
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("#"), 1)  # tunnel
        self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("+"), 1)  # doors
        # layer 2
        self.set_channel(state, 1, current_frame.get_list_of_positions_by_tile("%"), 1)  # stairs
        # layer 3
        self.set_channel(state, 2, current_frame.get_list_of_positions_by_tile("-"), 1)  # walls
        self.set_channel(state, 2, current_frame.get_list_of_positions_by_tile("|"), 1)  # walls
        self.set_channel(state, 2, current_frame.get_list_of_positions_by_tile("%"), 2)  # stairs

        pixel = current_frame.get_tile_below_player()
        if pixel == '#':  # tunnel
            self.set_channel(state, 0, current_frame.get_list_of_positions_by_tile("@"), 8)
        elif pixel == "%":  # stairs
            self.set_channel(state, 1, current_frame.get_list_of_positions_by_tile("@"), 8)
        else:  # floor
            self.set_channel(state, 2, current_frame.get_list_of_positions_by_tile("@"), 8)
        return state


class M_P_D_S_StateGenerator(StateGenerator):
    """Generates a state composed of 4 layers containing:
        - layer 1:
            - walkable tiles
        - layer 2:
            - rogue
        - layer 3:
            - doors
        - layer 4:
            - stairs
        The numerical values used are the same.
    """

    def _set_shape(self, data_format):
        self._shape = (4, 22, 80) if data_format == "channels_first" else (22, 80, 4)

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()
        # layer 0: the map
        self.set_channel(state, 0, current_frame.get_list_of_walkable_positions(), 1)
        # layer 1: the player position
        self.set_channel(state, 1, current_frame.get_list_of_positions_by_tile("@"), 1)
        # layer 2: the doors positions
        self.set_channel(state, 2, current_frame.get_list_of_positions_by_tile("+"), 1)
        # layer 3: the stairs positions
        self.set_channel(state, 3, current_frame.get_list_of_positions_by_tile("%"), 1)
        return state
