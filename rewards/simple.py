
from roguelib_module.rewards import RewardGenerator


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
                # todo: also check if same level between frames?
                if amulet[0] == new_info.get_player_pos():
                    self.amulet_taken = True
                    return self.reward_value
                return 0
            except:
                # amulet not visible
                return 0

        if new_info.is_victory_frame():
            self.goal_achieved = True
            return self.reward_value

        return 0
