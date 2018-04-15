from math import floor
from abc import abstractmethod
from .base import StateGenerator


class CroppedView_Base_StateGenerator(StateGenerator):
    """Base class for generators that create states of fixed radius centered on a coordinate.
    Everything outside the radius is cropped out.
    """

    def _subinit(self):
        self._area =  self._shape[1:] if self.data_format == "channels_first" else self._shape[:-1]

    def _get_relative_coordinates(self, tile_position, center_position, area):
        """Return the position that 'tile_position' would have in an area of size 'area' if 'center_position'
        was the center if the area"""
        i, j = tile_position
        x, y = center_position
        norm_i = i - x + floor(area[0] / 2)
        norm_j = j - y + floor(area[1] / 2)
        return norm_i, norm_j

    def set_channel_relative(self, center, state, channel, positions, value):
        """Assigns 'value' to each position in 'positions' of the channel in the given state, however the coordinates
        are adjusted so that 'center' is in the central position of the state

        :param tuple[int,int] center:
            center around which translate the positions
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
        centered_positions = map(lambda pos: self._get_relative_coordinates(pos, center, self._area),
                                 positions)
        centered_positions = filter(lambda pos: all(c >= 0 and c < a for c, a in zip(pos, self._area)),
                                    centered_positions)
        return self.set_channel(state, channel, centered_positions, value)


class CroppedViewOnRogue_Base_StateGenerator(CroppedView_Base_StateGenerator):
    """Base class for generators that create states of fixed radius centered on the rogue.
    Everything outside the radius is cropped out.
    """

    def is_frame_history_sufficient(self, frame_history):
        current_frame = frame_history[-1]
        self.player_position = current_frame.get_player_pos()
        return (self.player_position is not None and super().is_frame_history_sufficient(frame_history))


class CroppedView_TripleLayer_11x11_StateGenerator(CroppedViewOnRogue_Base_StateGenerator):
    """Generates a 11x11 state composed of 3 layers cropped and centered around the rouge containing:
        - layer 1:
            - corridors
            - doors
        - layer 2:
            - stairs
        - layer 3:
            - walls
            - stairs
        The numerical values used are the same except for the the stairs on layer 3.
        The rogue is not directly shown in the state.
    """

    def _set_shape(self, data_format):
        self._shape = (3, 11, 11) if data_format == "channels_first" else (11, 11, 3)

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()

        # layer 1
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("#"), 1)  # tunnel
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("+"), 1)  # doors
        # layer 2
        self.set_channel_relative(self.player_position, state, 1, current_frame.get_list_of_positions_by_tile("%"), 1)  # stairs
        # layer 3
        self.set_channel_relative(self.player_position, state, 2, current_frame.get_list_of_positions_by_tile("-"), 1)  # walls
        self.set_channel_relative(self.player_position, state, 2, current_frame.get_list_of_positions_by_tile("|"), 1)  # walls
        self.set_channel_relative(self.player_position, state, 2, current_frame.get_list_of_positions_by_tile("%"), 2)  # stairs

        return state


class CroppedView_TripleLayer_17x17_StateGenerator(CroppedView_TripleLayer_11x11_StateGenerator):
    """Generates a 17x17 state composed of 3 layers cropped and centered around the rouge containing:
        - layer 1:
            - corridors
            - doors
        - layer 2:
            - stairs
        - layer 3:
            - walls
            - stairs
        The numerical values used are the same except for the the stairs on layer 3.
        The rogue is not directly shown in the state.
    """

    def _set_shape(self, data_format):
        self._shape = (3, 17, 17) if data_format == "channels_first" else (17, 17, 3)


class CroppedView_SingleLayer_17x17_StateGenerator(CroppedViewOnRogue_Base_StateGenerator):
    """Generates a 17x17 state composed of a single layer cropped and centered around the rouge containing:
        - stairs
        - walls
        - doors and corridors
        The numerical values used are different and the rogue is not directly shown in the state.
    """

    def _set_shape(self, data_format):
        self._shape = (1, 17, 17) if data_format == "channels_first" else (17, 17, 1)

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()

        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("%"), 4)  # stairs
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("|"), 8)  # walls
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("-"), 8)  # walls
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("+"), 16)  # doors
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("#"), 16)  # tunnel

        return state


class CroppedView_SingleLayer_17x17_2_StateGenerator(CroppedView_SingleLayer_17x17_StateGenerator):
    """Generates a 17x17 state composed of a single layer cropped and centered around the rouge containing:
        - stairs
        - walls
        - doors and corridors
        The numerical values used are the same except for the walls and the rogue is not directly shown in the state.
    """

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()

        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("%"), 1)  # stairs
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("|"), 8)  # walls
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("-"), 8)  # walls
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("+"), 1)  # doors
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("#"), 1)  # tunnel

        return state


class CroppedView_SingleLayer_17x17_3_StateGenerator(CroppedView_SingleLayer_17x17_StateGenerator):
    """Generates a 17x17 state composed of a single layer cropped and centered around the rouge containing:
        - stairs
        - walls
        - doors and corridors
        The numerical values used are different and the rogue is not directly shown in the state.
    """

    def build_state(self, current_frame, frame_history):
        state = self.empty_state()

        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("%"), 1)  # stairs
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("|"), 8)  # walls
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("-"), 8)  # walls
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("+"), 16)  # doors
        self.set_channel_relative(self.player_position, state, 0, current_frame.get_list_of_positions_by_tile("#"), 16)  # tunnel

        return state
