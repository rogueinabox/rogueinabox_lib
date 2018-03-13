# -*- coding: utf-8 -*-


class RogueEvaluator:
    """Implements the evaluation of an agent"""

    def __init__(self, max_step_count=500):
        self.max_step_count = max_step_count
        self.episodes = []  # type: list[Episode]
        self.reset()

    def reset(self):
        self.episodes = []

    def on_run_begin(self):
        """Records the beginning of a run"""
        self.episodes.append(Episode())

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
        episode = self.episodes[-1]
        episode.steps += 1
        episode.total_reward += reward
        episode.frame_history = frame_history
        return episode.steps >= self.max_step_count

    def on_run_end(self, won):
        """Records the end of a run

        :param won:
            whether the game was won, according to a reward generator
        """
        self.episodes[-1].won = won

    def statistics(self, episode_slice=slice(None)):
        """
        :param slice episode_slice:
            slice of episode to consider, default to all episodes
        :return:
            dict of statistics:
            {
             "win_perc": float,    # % of victories, as determined by the reward generator
             "reward_avg": float,  # reward average of the episode
             "tiles_avg": float,   # average number of tiles seen
             "steps_avg": float    # average number of steps taken
            }
        """
        result = {}
        result["win_perc"] = 0
        result["reward_avg"] = 0
        result["tiles_avg"] = 0
        result["steps_avg"] = 0

        evaluated_episodes = self.episodes[episode_slice]
        # accumulate stats for each episode
        for e in evaluated_episodes:
            result["reward_avg"] += e.total_reward
            # we use the penultimate frame because the last one may be the tombstone or a new level
            result["tiles_avg"] += e.frame_history[-2].get_known_tiles_count()
            result["steps_avg"] += e.steps
            if e.won:
                result["win_perc"] += 1

        # average stats across all episodes
        n_episodes = len(evaluated_episodes)
        result["win_perc"] /= n_episodes
        result["steps_avg"] /= n_episodes
        # TODO: this is the total episode reward average, should the average be by step instead?
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
