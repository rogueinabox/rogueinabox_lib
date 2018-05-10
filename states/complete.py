
from .base import StateGenerator


class FullMap_StateGenerator(StateGenerator):
    """Generates a 22x80 state comprising the entire map composed of 'channels' layers, inserting the position
    of tiles in configurable layers and values, e.g. the stairs in layer 'stairs_channel' with value 'stairs_value'.

    By default, two channels are built:
        first channel:
            - walls (value: 1)
            - doors and corridors (value: 10)
        second channel:
            - rogue, covers the stairs if they are present (value: 1)
            - stairs (value: 10)
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

    stairs_channel    = 1
    stairs_value      = 10

    rogue_channel     = 1
    rogue_value       = 1

    def _set_shape(self, data_format):
        self._shape = (22, 80, self.channels) if data_format == 'channels_last' else (self.channels, 22, 80)

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()

        # stairs
        self.set_channel(state, self.stairs_channel,
                         current_frame.get_list_of_positions_by_tile("%"), self.stairs_value)

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
            self.set_channel(state, self.floor_channel,
                             current_frame.get_list_of_positions_by_tile("."), self.floor_value)

        return state


class FullMap_5L_StateGenerator(FullMap_StateGenerator):
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
        All values are 1.
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

    rogue_channel     = 4
    rogue_value       = 1
