#Copyright (C) 2017 Andrea Asperti, Carlo De Pieri, Gianmaria Pedrini
#
#This file is part of Rogueinabox.
#
#Rogueinabox is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#Rogueinabox is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from abc import ABC, abstractmethod

import pickle
import random
import numpy as np

import os
from collections import deque


class HistoryManager(ABC):
    """A class responsible for saving history and loading batch of it for training purposes."""

    def __init__(self, histsize):
        """Constructor for History"""
        self._history = None
        self.histsize = histsize

    @property
    def history(self):
        """Return the history"""
        return self._history

    def hist_len(self):
        """Return the history length"""
        return len(self._history)

    def save_history_on_file(self, filename):
        """Save the history on file"""
        print("Saving history...")
        with open(filename, "wb") as history:
            pickle.dump(self._history, history)
            print("History saved!")

    def load_history_from_file(self, filename):
        """Load the history from the filesystem"""
        if os.path.isfile(filename):
            print("History found, loading...")
            with open(filename, "rb") as history:
                self._history = pickle.load(history)
                print("History loaded!")

    @abstractmethod
    def update_history(self):
        """Method responsible for saving the new state into the history"""
        pass

    @abstractmethod
    def pick_batch(self):
        """Method responsible for picking a batch of states from the history to train"""
        pass


    def check_balance(self):
        print("history size: {}".format(len(self._history)))
        p = np.zeros(5)
        n = np.zeros(5)
        z = np.zeros(5)
        i = 0

        for (s1, a, r, s2, ter) in self._history:
            if r > 2:
                p[a] += 1
            elif r <= -0.5:
                n[a] += 1
            else:
                z[a] += 1

        print(p)
        print(n)
        print(z)


class FIFORandomPickHM(HistoryManager):
    """Simple fifo queue history implementation"""

    def __init__(self, histsize):
        super().__init__(histsize)
        self._history = deque()

    def update_history(self, old_state, new_state, action_index, reward, terminal):
        """Update the fifo history queue
        return True if an item was added, False otherwise
        """
        self._history.appendleft((old_state, action_index, reward, new_state, terminal))
        if len(self._history) > self.histsize:
            self._history.pop()
        return True

    def pick_batch(self, batch_dimension):
        return random.sample(list(self._history), batch_dimension)

class NearDoorRandomPickHM(HistoryManager):
    """A more balanced history implementation for ExitRoom"""

    def __init__(self, histsize):
        super().__init__(histsize)
        self._history = deque()

    def _distance_from_door(self, state):
        # warning: the rogue may cover the door
        rogue_pos = np.argwhere(state[1] == 255)
        if rogue_pos.shape[0] == 0: return 1000
        rx,ry = rogue_pos[0][0],rogue_pos[0][1]
        doors = np.argwhere(state[2] == 255)
        dl = []
        for dpos in doors:
            dx,dy = dpos[0],dpos[1]
            dl.append(abs(dx-rx)+abs(dy-ry))
        if dl == []: return 1000
        mind = min(dl)
        print("distance = %", mind)
        return mind

    def update_history(self, old_state, new_state, action_index, reward, terminal):
        """Update the balanced history queue
        return True if an item was added, False otherwise
        """
        item_added = False
        if (reward > 0) or (random.random() < self._distance_from_door(new_state[0])**-2.):  
            self._history.appendleft((old_state, action_index, reward, new_state, terminal))
            item_added = True
        if len(self._history) > self.histsize:
            self._history.pop()
        return item_added

    def pick_batch(self, batch_dimension):
        return random.sample(list(self._history), batch_dimension)

class StatisticBalanceRandomPickHM(HistoryManager):
    """Simple balanced history implementation"""

    def __init__(self, histsize):
        super().__init__(histsize)
        self.counter = 0
        self._history = deque()

    def update_history(self, old_state, new_state, action_index, reward, terminal):
        """Update the balanced history queue
        return True if an item was added, False otherwise
        """
        item_added = False
        self.counter += 1
        if (reward >= 0) or (self.counter % 7 == 0):
            self._history.appendleft((old_state, action_index, reward, new_state, terminal))
            item_added = True
        if len(self._history) > self.histsize:
            self._history.pop()
        return item_added

    def pick_batch(self, batch_dimension):
        return random.sample(list(self._history), batch_dimension)


class StatisticBalance2RandomPickHM(HistoryManager):
    """Simple balanced history implementation"""

    def __init__(self, histsize):
        super().__init__(histsize)
        self._history = deque()

    def update_history(self, old_state, new_state, action_index, reward, terminal):
        """Update the balanced history queue
        return True if an item was added, False otherwise
        """
        item_added = False
        if reward > 0 or (reward < 0 and random.random() < 0.2) or reward < -0.5:
            self._history.appendleft((old_state, action_index, reward, new_state, terminal))
            item_added = True
        if len(self._history) > self.histsize:
            self._history.pop()
        return item_added

    def pick_batch(self, batch_dimension):
        return random.sample(list(self._history), batch_dimension)
