# Copyright (C) 2017 Andrea Asperti, Carlo De Pieri, Gianmaria Pedrini
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

from abc import ABC, abstractmethod
from rogueinabox.utils import SaveManager, MultiSaveManager
import datetime
import numpy as np
import json

class LoweringMeanSentence(Exception):
    """The mean is lower, this is bad!"""


class TookTooLongSentence(Exception):
    """The rogue seems stuck!"""


class Judge(ABC):
    def __init__(self, agent):
        self.agent = agent
        self.rb = agent.rb
        self.scores = []
        self.means = []
        self.default_score = 0
        self.mean = 0
        self.highest_mean = 0
        self._reset_score()
        self.last_name = ""
        self.death_sentence = self.agent.configs["death_sentence"]
        self.mean_sample = self.agent.configs["mean_sample"]
        self.mean_stride = self.agent.configs["mean_stride"]
        self.save_score = self.agent.configs["save_score"]
        self.save_mean = self.agent.configs["save_mean"]
        self.FSM = SaveManager(self.agent.configs, self)

    @abstractmethod
    def hook_before_action(self):
        """This should be called before the agent act."""
        pass

    @abstractmethod
    def hook_after_action(self):
        """This should be called after the agent act."""
        pass

    @abstractmethod
    def hook_game_over(self):
        """This should be called on game over."""
        pass

    def _register_score(self):
        self.scores.append(self.score)
        if len(self.scores) > self.mean_sample:
            self.scores.pop(0)

    def _reset_score(self):
        self.score = self.default_score

    def _register_mean(self):
        if len(self.scores) >= self.mean_sample:
            self.mean = float(sum(self.scores)) / float(self.mean_sample)
            self.means.append(self.mean)

    def get_agent(self):
        """Return the current agent. Sometimes this must be determined every step, hence the function."""
        return self.agent


class BaseJudge(Judge):

    def __init__(self, agent, mean_sample=100, train=False):
        super().__init__(agent)
        self.train = train
        self.mean_sample = mean_sample
        self.moves = 0
        self.run_counter = 0
        self.test_stats = {
                    "success" : 0, #percentuale di successi
                    "tiles" : [],  #tiles scoperte in media
                    "moves" : []   #numero medio di mosse per scendere
        }


    def hook_after_action(self):
        if self.train:
            return

        self.moves += 1
        lvl = self.rb.get_stat("dungeon_level")
        if self.rb.get_stat("status") in ["Hungry", "Weak", "Faint"] or self.rb.game_over() or self.moves >= 500:
            # a random agent usually terminates in < 400 moves
            self.test_stats["tiles"].append(self.rb.count_passables())
            print("terminated run number {}".format(self.run_counter))
            self.moves = 0
            self.run_counter += 1
            self.rb.reset()
        elif lvl and int(lvl) > 1:
            self.test_stats["success"] += 1
            self.test_stats["tiles"].append(self.rb.count_passables())
            self.test_stats["moves"].append(self.moves)
            self.moves = 0
            print("terminated run number {}".format(self.run_counter))
            self.run_counter += 1
            self.rb.reset()

        if self.run_counter >= self.mean_sample:
            self.rb.quit_the_game()
            self.test_stats["success"] /= self.run_counter
            if not self.test_stats["tiles"]:
                self.test_stats["tiles"] = [0]
            if not self.test_stats["moves"]:
                self.test_stats["moves"] = [0]
            self.test_stats["tiles"] = np.mean(self.test_stats["tiles"])
            self.test_stats["moves"] = np.mean(self.test_stats["moves"])
            now = datetime.datetime.now()
            with open("test_result_{}-{}-{}.json".format(now.hour, now.minute, now.second), "w") as f:
                json.dump(self.test_stats, f, indent=4)
            exit()

    def hook_before_action(self):
        pass

    def hook_game_over(self):
        pass

class SimpleExplorationJudge(Judge):
    """An exploration based Judge: its scoring is based on the number of tiles discovered by the rogue.
        Training behaviour: calculates the average score every 'self.mean_stride' of the last 'self.mean_sample'. Always
    save on the side the best weights by these standards. Can interrupt the training if the average score lowers. Finally
    save all relevant data into 'config["saves_dir"]' if needed.
        Play behaviour: after 'self.mean_sample' calculate the mean, save all relevant data and terminate the run."""

    def hook_before_action(self):
        self.old_screen = self.rb.get_screen()
        self.old_level = self.rb._get_stat_from_screen("dungeon_level", self.old_screen)

    def hook_after_action(self):
        self.screen = self.rb.get_screen()
        self.level = self.rb._get_stat_from_screen("dungeon_level", self.screen)
        if self.level is None:
            # this will happen at game_over
            self.level = self.old_level
        elif self.level > self.old_level:
            self.score += self.rb._count_passables_in_screen(self.old_screen)

    def hook_game_over(self):
        from logger import Log
        self.score += self.rb._count_passables_in_screen(self.old_screen)
        self._register_score()
        self._register_mean()
        mode = self.agent.configs["mode"]
        if mode == "learn":
            # Training behaviour
            if len(self.means) == 1 or (len(self.means) > 0 and len(self.means) % self.mean_stride == 0):
                # will trigger when the first mean is recorded and then every self.mean_stride games
                if self.mean > self.highest_mean:
                    self.highest_mean = self.mean
                    self.FSM.update_tmp_weights()
                else:
                    # there were no improvement
                    if self.agent.configs["stop_training"] or self.FSM.manual_stop_required():
                        if self.agent.configs["save_learning"]:
                            self.FSM.save_training()
                        logs = [Log("end_learn",
                                    "Ending this run, we haven't learned anything. Saving training result...".format(
                                        self.mean_sample), 0)]
                        self.get_agent().l.log(logs)
                        if self.death_sentence:
                            raise LoweringMeanSentence("Last average score was higher than the current, this is bad!")
                        exit(0)
        elif mode == "play":
            # play behaviour
            #TODO remove judges from roguelib
            if False and (len(self.scores) >= self.mean_sample or self.FSM.manual_stop_required()):
                logs = [Log("end_play",
                            "Ending this run, we reached the game {}. Saving report...".format(self.mean_sample), 0)]
                self.get_agent().l.log(logs)
                self.FSM.save_playing()
                exit(0)
        self._reset_score()


class ImpatientTrait:
    """A Judge that wants to interrupt the agent if it has not explored new tiles in a while must inherit from both this
    class and its parent Judge like this:
    class NewImpatientJudge(ImpatientTrait, OldJudge): ...
    BEWARE that ImpatientTrait must come BEFORE OldJudge because of how the __mro__ works in python."""

    def __init__(self, *args, **kwargs):
        super(ImpatientTrait, self).__init__(*args, **kwargs)
        self.old_screen = self.rb.get_screen()
        self.patience_moves = 0
        self.old_passable = 0
        self.patience = self.agent.configs["patience"]
        self.impatient = self.agent.configs["impatient"]
        self.agent.configs["impatient"] = True

    def hook_before_action(self):
        super().hook_before_action()
        self.old_screen = self.rb.get_screen()
        self.old_level = self.rb._get_stat_from_screen("dungeon_level", self.old_screen)


    def hook_after_action(self):
        super().hook_after_action()
        self.screen = self.rb.get_screen()
        self.level = self.rb._get_stat_from_screen("dungeon_level", self.screen)
        if self.impatient:
            passable = self.rb._count_passables_in_screen(self.old_screen)
            if self.level is not None:
                if self.level == self.old_level and self.old_passable == passable:
                    self.patience_moves += 1
                    if self.patience_moves >= self.patience:
                        raise TookTooLongSentence(
                            "In {} moves the rogue hasn't discovered nothing new...".format(self.patience))
                else:
                    # Either the rogue gained points or went down a level
                    self.old_passable = passable
                    self.patience_moves = 0
            else:
                # The rogue died
                self.old_passable = self.rb._count_passables_in_screen(self.screen)
                self.patience_moves = 0


class ImpatientSimpleExplorationJudge(ImpatientTrait, BaseJudge):
    """A simple exploration judge that interrupts the agent if it goes in a loop."""


class MultiImpatientSimpleExplorationJudge(ImpatientTrait, BaseJudge):
    """A simple exploration judge that interrupts the agent if it goes in a loop."""

    def __init__ (self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.FSM
        self.FSM = MultiSaveManager(self.agent.configs, self)

    def get_agent(self):
        """Be sure to call the right, current agent."""
        return self.agent.SM.current.situational_agent
