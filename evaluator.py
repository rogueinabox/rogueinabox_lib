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

import collections


class RogueEvaluator:
    """Implements the evaluation of an agent by keeping track of how many time it
    accomplishes its goal, the return received, the number of steps it takes and the number of
    tiles seen.

    N.B.: this is meant for the first level only
    """

    def __init__(self, max_step_count=500, episodes_for_evaluation=200):
        """
        :param int max_step_count:
            maximum number of steps per episode
        :param int episodes_for_evaluation:
            number of latest episode to consider when computing statistics
            (use 0, None or any "falsy" value to consider them all)
        """
        self.max_step_count = max_step_count
        self.episodes_for_evaluation = episodes_for_evaluation or None
        self.episodes = collections.deque(maxlen=self.episodes_for_evaluation)  # type: deque[Episode]
        self.current_episode = None  # type: Episode

    def reset(self):
        self.episodes.clear()
        self.current_episode = None  # type: Episode

    def on_run_begin(self):
        """Records the beginning of a run"""
        self.current_episode = Episode()

    def on_step(self, frame_history, action, reward, step):
        """Records a step taken by the agent during the run and returns whether the run should stop

        :param list[frame_info.RogueFrameInfo] frame_history:
            list of parsed frames until now
        :param str action:
            action performed
        :param float reward:
            reward obtained
        :param int step:
            rougueinabox step number

        :rtype: bool
        :return:
            True if the run should stop
        """
        self.current_episode.steps += 1
        self.current_episode.total_reward += reward
        return self.current_episode.steps >= self.max_step_count

    def on_run_end(self, frame_history, won, is_rogue_dead):
        """Records the end of a run

        :param list[frame_info.RogueFrameInfo] frame_history:
            list of parsed frames
        :param bool won:
            whether the game was won, according to a reward generator
        :param bool is_rogue_dead:
            whether the rogue died
        """
        # we use the penultimate frame if we can because the last one may be the tombstone or a new level
        frame = frame_history[-2] if len(frame_history) > 1 else frame_history[0]
        self.current_episode.final_tiles_count = frame.get_known_tiles_count()
        self.current_episode.won = won
        self._add_episode(self.current_episode)

    def _add_episode(self, episode):
        """Adds the given episode to the collection, keeping a maximum of self.episodes_for_evaluation.
        When the number of collected episodes exceeds this amounts, the oldest episodes are removed (FIFO policy)

        :param Episode episode:
            episode to add to the collection
        """
        self.episodes.append(episode)

    def statistics(self):
        """
        :return:
            dict of statistics:
            {
             "win_perc": float,        # % of victories, as determined by the reward generator
             "reward_avg": float,      # cumulative reward average
             "tiles_avg": float,       # average number of tiles seen
             "all_steps_avg": float,   # average number of steps taken in all episodes
             "win_steps_avg": float    # average number of steps taken in won episodes
            }
        """
        result = {}
        result["win_perc"] = 0
        result["reward_avg"] = 0
        result["tiles_avg"] = 0
        result["all_steps_avg"] = 0
        result["win_steps_avg"] = 0

        evaluated_episodes = self.episodes
        # accumulate stats for each episode
        for e in evaluated_episodes:
            result["reward_avg"] += e.total_reward
            result["tiles_avg"] += e.final_tiles_count
            result["all_steps_avg"] += e.steps
            if e.won:
                result["win_perc"] += 1
                result["win_steps_avg"] += e.steps

        # average stats across all episodes
        n_episodes = len(evaluated_episodes)
        if n_episodes > 0:
            result["win_steps_avg"] /= max(result["win_perc"], 1)
            result["win_perc"] /= n_episodes
            result["all_steps_avg"] /= n_episodes
            result["reward_avg"] /= n_episodes
            result["tiles_avg"] /= n_episodes

        return result


class Episode:
    """Game episode representation"""
    def __init__(self):
        self.won = False
        self.steps = 0
        self.final_tiles_count = 0
        self.total_reward = 0


class LevelsRogueEvaluator(RogueEvaluator):
    """Evaluates an agent by keeping track of how many times it reaches each level and how many steps
    it took, both when descending and ascending.

    N.B.: this implementation supposes that when the agent starts ascending it will never descend again.
          The behavior when this is not true is undefined.
    """

    def on_run_begin(self):
        """Records the beginning of a run"""
        self.last_level = 1
        self.just_changed_level = False
        self.current_episode = LevelsEpisode()

    def on_step(self, frame_history, action, reward, step):
        """Records a step taken by the agent during the run and returns whether the run should stop

        :param list[frame_info.RogueFrameInfo] frame_history:
            list of parsed frames until now
        :param str action:
            action performed
        :param float reward:
            reward obtained
        :param int step:
            rougueinabox step number

        :rtype: bool
        :return:
            True if the run should stop
        """
        stop = super().on_step(frame_history, action, reward, step)

        self.just_changed_level = False

        last_frame = frame_history[-1]
        level = None
        if last_frame.has_statusbar():
            level = frame_history[-1].statusbar["dungeon_level"]
        elif last_frame.is_victory_frame():
            level = 0

        if level is not None and level != self.last_level:
            self.just_changed_level = True

            # count the tiles of the frame of the previous level
            self.current_episode.final_tiles_count += frame_history[-2].get_known_tiles_count()

            # add as many 'levels_steps' entries as needed, considering even the case of advancing multiple levels
            # in a single frame
            diff = level - self.last_level
            descending = (diff > 0)
            if descending:
                levels_steps = self.current_episode.levels_steps
            else:
                diff *= -1
                levels_steps = self.current_episode.ascending_levels_steps
            levels_steps.extend([self.current_episode.steps]*diff)
            self.last_level = level

        return stop

    def on_run_end(self, frame_history, won, is_rogue_dead):
        """Records the end of a run

        :param list[frame_info.RogueFrameInfo] frame_history:
            list of parsed frames
        :param bool won:
            whether the game was won, according to a reward generator
        :param bool is_rogue_dead:
            whether the rogue died
        """
        if not self.just_changed_level:
            last_frame = frame_history[-1]
            if last_frame.is_victory_frame():
                last_frame = frame_history[-2]
            self.current_episode.final_tiles_count += last_frame.get_known_tiles_count()
        self.current_episode.won = won
        self._add_episode(self.current_episode)

    def statistics(self):
        """
        :return:
            dict of statistics:
            {
             "win_perc": float,          # % of victories, as determined by the reward generator
             "reward_avg": float,        # cumulative reward average
             "tiles_avg": float,         # average number of tiles seen
             "all_steps_avg": float,     # average number of steps taken in all episodes
             "win_steps_avg": float,     # average number of steps taken in won episodes
             "lvls_avg": [float],        # average number of times each level is reached
             "lvls_steps_avg": [float],  # average number of steps taken to reach each level
             "alvls_avg": [float],       # average number of times each level is ascended, in reverse order
             "alvls_steps_avg": [float]  # average number of steps taken to ascend each level, in reverse order
            }
        """
        result = super().statistics()

        evaluated_episodes = self.episodes

        # compute stats for descending and ascending levels
        keys = [("lvls_avg", "lvls_steps_avg"), ("alvls_avg", "alvls_steps_avg")]
        ep_attrs = ['levels_steps', 'ascending_levels_steps']

        for k, ep_attr in zip(keys, ep_attrs):

            # accumulate stats for each episode
            lvls_avg = []
            lvls_steps_avg = []
            for e in evaluated_episodes:
                ep_steps = getattr(e, ep_attr)
                if len(ep_steps) > 0:
                    diff = len(ep_steps) - len(lvls_avg)
                    if diff > 0:
                        lvls_avg.extend([0]*diff)
                        lvls_steps_avg.extend([0]*diff)
                    for i, steps in enumerate(ep_steps):
                        lvls_avg[i] += 1
                        lvls_steps_avg[i] += steps

            # average stats across all episodes
            n_episodes = len(evaluated_episodes)
            for i, (reached, steps) in enumerate(zip(lvls_avg, lvls_steps_avg)):
                lvls_steps_avg[i] = steps / reached
                lvls_avg[i] = reached / n_episodes

            k_rate, k_steps = k
            if len(lvls_avg) > 0:
                result[k_rate] = lvls_avg
                result[k_steps] = lvls_steps_avg

        return result


class LevelsEpisode(Episode):
    """Game episode representation with stats per level"""
    def __init__(self):
        super().__init__()
        self.levels_steps = []
        self.ascending_levels_steps = []


class AmuletLevelsRogueEvaluator(LevelsRogueEvaluator):
    """Evaluates an agent based on how many times it finds and takes the amulet and wins the game.
    As a LevelsRogueEvaluator subclass, it will also track levels descent/ascent stats.
    """

    def on_run_begin(self):
        """Records the beginning of a run"""
        self.last_level = 1
        self.current_episode = AmuletLevelsEpisode()

    def on_step(self, frame_history, action, reward, step):
        """Records a step taken by the agent during the run and returns whether the run should stop

        :param list[frame_info.RogueFrameInfo] frame_history:
            list of parsed frames until now
        :param str action:
            action performed
        :param float reward:
            reward obtained
        :param int step:
            rougueinabox step number

        :rtype: bool
        :return:
            True if the run should stop
        """
        stop = super().on_step(frame_history, action, reward, step)

        if len(frame_history) >= 2:
            old_info = frame_history[-2]
            new_info = frame_history[-1]

            amulet = old_info.get_list_of_positions_by_tile(',')
            if len(amulet) > 0:
                self.current_episode.amulet_found = True
                try:
                    if old_info.statusbar["dungeon_level"] == new_info.statusbar["dungeon_level"]:
                        if amulet[0] == new_info.get_player_pos():
                            self.current_episode.amulet_taken = True
                except KeyError:
                    pass

        return stop

    def statistics(self):
        """
        :return:
            dict of statistics, with the same keys as LevelsRogueEvaluator, plus the following:
            {
             "am_found_avg": float,   # average number of episodes in which the amulet was found
             "am_taken_avg": float    # average number of episodes in which the amulet was taken
            }
        """
        result = super().statistics()

        amulet_found_avg = 0
        amulet_taken_avg = 0

        evaluated_episodes = self.episodes

        # accumulate stats for each episode
        for e in evaluated_episodes:
            if e.amulet_found:
                amulet_found_avg += 1
            if e.amulet_taken:
                amulet_taken_avg += 1

        # average stats across all episodes
        n_episodes = len(evaluated_episodes)
        if n_episodes > 0:
            amulet_found_avg /= n_episodes
            amulet_taken_avg /= n_episodes

        result["am_found_avg"] = amulet_found_avg
        result["am_taken_avg"] = amulet_taken_avg

        return result


class AmuletLevelsEpisode(LevelsEpisode):
    def __init__(self):
        super().__init__()
        self.amulet_found = False
        self.amulet_taken = False
