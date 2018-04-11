# -*- coding: utf-8 -*-

import collections


class RogueEvaluator:
    """Implements the evaluation of an agent"""

    def __init__(self, max_step_count=500, episodes_for_evaluation=200):
        """
        :param int max_step_count:
            maximum number of steps per episode
        :param int episodes_for_evaluation:
            number of latest episode to consider when computing statistics
            (use 0, None or any "falsy" value to consider them all)
        """
        self.max_step_count = max_step_count
        self.episodes_for_evaluation = episodes_for_evaluation or float('inf')
        self.episodes = collections.deque()  # type: deque[Episode]
        self.current_episode = None  # type: Episode

    def reset(self):
        self.episodes = collections.deque()
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
        episode = self.current_episode
        episode.steps += 1
        episode.total_reward += reward
        episode.frame_history = frame_history
        return episode.steps >= self.max_step_count

    def on_run_end(self, won, is_rogue_dead):
        """Records the end of a run

        :param bool won:
            whether the game was won, according to a reward generator
        :param bool is_rogue_dead:
            whether the rogue died
        """
        self.current_episode.won = won
        self._add_episode(self.current_episode)

    def _add_episode(self, episode):
        """Adds the given episode to the collection, keeping a maximum of self.episodes_for_evaluation.
        When the number of collected episodes exceeds this amounts, the oldest episodes are removed (FIFO policy)

        :param Episode episode:
            episode to add to the collection
        """
        self.episodes.append(episode)
        if len(self.episodes) > self.episodes_for_evaluation:
            self.episodes.popleft()

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
            result["tiles_avg"] += e.get_known_tiles_count()
            result["all_steps_avg"] += e.steps
            if e.won:
                result["win_perc"] += 1
                result["win_steps_avg"] += e.steps

        # average stats across all episodes
        n_episodes = len(evaluated_episodes)
        if n_episodes > 0:
            result["win_perc"] /= n_episodes
            result["all_steps_avg"] /= n_episodes
            result["win_steps_avg"] /= n_episodes
            result["reward_avg"] /= n_episodes
            result["tiles_avg"] /= n_episodes

        return result


class Episode:
    """Game episode representation"""
    def __init__(self):
        self.won = False
        self.steps = 0
        self.frame_history = None
        self.total_reward = 0

    def get_known_tiles_count(self):
        """Returns the number of tiles seen in the episode"""
        # we use the penultimate frame if we can because the last one may be the tombstone or a new level
        frame = self.frame_history[-2] if len(self.frame_history) > 1 else self.frame_history[0]
        return frame.get_known_tiles_count()
