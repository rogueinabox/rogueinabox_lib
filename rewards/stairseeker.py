from .base import RewardGenerator


class StairSeeker_RewardGenerator(RewardGenerator):
    """Generate a reward for the last action:
        +10 for descending the stairs
        +1 for each new door discovered
        -0.01 for standing still
    """

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 10
        elif new_info.get_tile_count("+") > old_info.get_tile_count("+"):  # doors
            return 1
        elif self.player_standing_still(old_info, new_info):  # standing reward
            return -0.01
        return 0


class StairSeeker_13_RewardGenerator(RewardGenerator):
    """Generate a reward for the last action:
        +10000 for descending the stairs
        +1 for each new door discovered
        +1 for each new corridor tile discovered
    """

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 10000
        elif new_info.get_tile_count("+") > old_info.get_tile_count("+"):  # doors
            return 1
        elif new_info.get_tile_count("#") > old_info.get_tile_count("#"):  # passages
            return 1
        return 0


class StairSeeker_15_RewardGenerator(RewardGenerator):
    """Generate a reward for the last action:
        +10000 for descending the stairs
        +100 for each new door discovered
    """

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 10000
        elif new_info.get_tile_count("+") > old_info.get_tile_count("+"):  # doors
            return 100
        return 0


class ImprovedStairSeeker_RewardGenerator(StairSeeker_RewardGenerator):
    """Generate a reward for the last action:
        +10 for descending the stairs
        +1 for each new door discovered
        +1 for making the first step into a new corridor
        -0.01 for standing still
    """

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if old_info.get_tile_below_player() == '+':
            if new_info.get_tile_count("#") > old_info.get_tile_count("#"):  # has started to explore
                return 1
        return super().get_value(frame_history)


class ImprovedStairSeeker2_RewardGenerator(ImprovedStairSeeker_RewardGenerator):
    """Generate a reward for the last action:
        +100 for descending the stairs
        +1 for each new door discovered
        +1 for making the first step into a new corridor
        -0.01 for standing still
    """

    def get_value(self, frame_history):
        old_info = frame_history[-2]
        new_info = frame_history[-1]
        if new_info.statusbar["dungeon_level"] > old_info.statusbar["dungeon_level"]:
            self.goal_achieved = True
            return 100
        return super().get_value(frame_history)
