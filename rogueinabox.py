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

import sys
import time
import os
import fcntl
import pty
import signal
import shlex
import pyte
import re
import numpy as np
import itertools
import scipy
import copy

from parser import RogueParser
from evaluator import RogueEvaluator
import states
import rewards

class Terminal:
    def __init__(self, columns, lines):
        self.screen = pyte.DiffScreen(columns, lines)
        self.stream = pyte.ByteStream()
        self.stream.attach(self.screen)

    def feed(self, data):
        self.stream.feed(data)

    def read(self):
        return self.screen.display

def open_terminal(command="bash", columns=80, lines=24):
    p_pid, master_fd = pty.fork()
    if p_pid == 0:  # Child.
        path, *args = shlex.split(command)
        args = [path] + args
        env = dict(TERM="linux", LC_ALL="en_GB.UTF-8",
                   COLUMNS=str(columns), LINES=str(lines))
        try:
            os.execvpe(path, args, env)
        except FileNotFoundError:
            print("Could not find the executable in %s. Press any key to exit." % path)
            exit()

    # set non blocking read
    flag = fcntl.fcntl(master_fd, fcntl.F_GETFD)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)
    # File-like object for I/O with the child process aka command.
    p_out = os.fdopen(master_fd, "w+b", 0)
    return Terminal(columns, lines), p_pid, p_out



class RogueBox:
    @staticmethod
    def get_actions():
        """return the list of actions"""
        # h, j, k, l: ortogonal moves
        # y, u, b, n: diagonal moves
        # >: go downstairs
        # return ['h', 'j', 'k', 'l', '>', 'y', 'u', 'b', 'n']
        return ['h', 'j', 'k', 'l', '>']
    
    """Start a rogue game and expose interface to communicate with it"""
    def __init__(self,game_exe_path,  max_step_count, state_generator=None, reward_generator=None):
        self.rogue_path = game_exe_path
        self.parser = RogueParser()
        self.evaluator = RogueEvaluator()
        self.max_step_count=max_step_count
        if self.max_step_count <= 0:
            self.max_step_count = 1
        if reward_generator:
            self.reward_generator = getattr(rewards, reward_generator)()
        if state_generator:
            self.state_generator = getattr(states, state_generator)()

        self._start()


    def _start(self):
        self.terminal, self.pid, self.pipe = open_terminal(command=self.rogue_path)
        # our internal screen is list of lines, each line is a string
        # can be indexed as a 24x80 matrix
        self.screen = []
        self.frame_info = []
        self.parser.reset()
        self.step_count =0
        self.episode_reward = 0

        if not self.is_running():
            print("Could not find the executable in %s." % self.rogue_path)
            exit()

        time.sleep(.5)
        
        # wait until the rogue spawns
        self.screen = self.get_empty_screen()
        while not ('Hp:' in self.screen[-1]):
            self._update_screen()

        self._update_screen()
        self.frame_info.append( self.parser.parse_screen( self.screen ) )
        self.parse_statusbar_re = self._compile_statusbar_re()


    @staticmethod
    def _compile_statusbar_re():
        parse_statusbar_re = re.compile(r"""
                Level:\s*(?P<dungeon_level>\d*)\s*
                Gold:\s*(?P<gold>\d*)\s*
                Hp:\s*(?P<current_hp>\d*)\((?P<max_hp>\d*)\)\s*
                Str:\s*(?P<current_strength>\d*)\((?P<max_strength>\d*)\)\s*
                Arm:\s*(?P<armor>\d*)\s*
                Exp:\s*(?P<exp_level>\d*)/(?P<tot_exp>\d*)\s*
                (?P<status>(Hungry|Weak|Faint)?)\s*
                (Cmd:\s*(?P<command_count>\d*))?""", re.VERBOSE)
        return parse_statusbar_re

    def reset(self):
        """kill and restart the rogue process"""
        self.stop()
        return self._start()
            
    def stop(self):
        """kill and restart the rogue process"""
        if self.is_running():
            self.pipe.close()
            os.kill(self.pid, signal.SIGTERM)
            # wait the process so it doesnt became a zombie
            os.waitpid(self.pid, 0)

    def _update_screen(self):
        """update the virtual screen and the class variable"""
        update = self.pipe.read(65536)
        if update:
            self.terminal.feed(update)
            self.screen = self.terminal.read()
            
    def get_empty_screen(self):
        screen = list()
        for row in range(24):
            value = ""
            for col in range(80):
                value += " "
            screen.append(value)
        return screen

    def print_screen(self):
        """print the current screen"""
        print(*self.screen, sep='\n')

    def get_screen(self):
        """return the screen as a list of strings.
        can be treated like a 24x80 matrix of characters (screen[17][42])"""
        return self.screen

    def get_screen_string(self):
        """return the screen as a single string with \n at EOL"""
        out = ""
        for line in self.screen:
            out += line
            out += '\n'
        return out

    @property
    def player_pos(self):
        return self.frame_info[-1].get_list_of_positions_by_tile("@")[0]

    # get info methods
    def get_legal_actions(self):
        actions = []
        row = self.player_pos[0]
        column = self.player_pos[1]
        if self.screen[row-1][column] not in '-| ':
            actions += ['k']
        if self.screen[row+1][column] not in '-| ':
            actions += ['j']
        if self.screen[row][column-1] not in '-| ':
            actions += ['h']
        if self.screen[row][column+1] not in '-| ':
            actions += ['l']
        if self.player_pos == self.stairs_pos:
            actions += ['>']
        return actions


    def game_over(self, screen=None):
        """check if we are at the game over screen (tombstone)"""
        if not screen:
            screen = self.screen
        # look for tombstone
        for line in screen:
            if '_______)' in line or 'You quit' in line:
                return True
        return False


    def is_running(self):
        """check if the rogue process exited"""
        try:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
        except OSError:
            return False
        if pid == 0:
            return True
        else:
            return False

    def compute_state(self, new_info):
        """return a numpy array representation of the current state using the function specified during init"""
        if self.state_generator:
            return self.state_generator.compute_state(new_info)
        else:
            return Non

    def compute_reward(self, old_info, new_info):
        """return the reward for a state transition using the function specified during init"""
        if self.reward_generator:
            return self.reward_generator.compute_reward(old_info, new_info)
        else:
            return 0

    def currently_in_corridor(self):
        info = self.frame_info[-1]
        return info.get_list_of_positions_by_tile("@")[0] in info.get_list_of_positions_by_tile("#")

    def currently_in_door(self):
        info = self.frame_info[-1]
        return info.get_list_of_positions_by_tile("@")[0] in info.get_list_of_positions_by_tile("+")
    
    def _dismiss_message(self):
        """dismiss a rogue status message.
        call it once, because it will call itself again until
        all messages are dismissed """
        messagebar = self.screen[0]
        if "ore--" in messagebar:
            # press space
            self.pipe.write(' '.encode())
        elif "all it" in messagebar:
            # press esc
            self.pipe.write('\e'.encode())

    def _need_to_dismiss(self):
        """check if there are status messages that need to be dismissed"""
        messagebar = self.screen[0]
        if "all it" in messagebar or "ore--" in messagebar:
            return True
        else:
            return False

    def quit_the_game(self):
        """Send the keystroke needed to quit the game."""
        self.pipe.write('Q'.encode())
        self.pipe.write('y'.encode())
        self.pipe.write('\n'.encode())


    def get_last_frame(self):
        return self.frame_info[-1]


    # interact with rogue methods
    def send_command(self, command, state_generator=None, reward_generator=None):
        if not state_generator:
            state_generator = self.state_generator
        if not reward_generator:
            reward_generator = self.reward_generator

        """send a command to rogue"""
        old_screen = self.screen[:]
        self.pipe.write(command.encode())
        if command in self.get_actions():
            self.pipe.write('\x12'.encode())

        if "Cmd" in old_screen[-1]:
            new_screen = old_screen
            while old_screen[-1] == new_screen[-1]: # after a command execution, the new screen is always different from the old one
                self._update_screen()
        else:
            time.sleep(0.01)
            self._update_screen()

        while self._need_to_dismiss(): # will dismiss all upcoming messages
            self._dismiss_message()
            self._update_screen()
        new_screen = self.screen
        lose = self.game_over(new_screen)

        if not lose:
            if not self.frame_info:
                self.frame_info.append( self.parser.parse_screen( old_screen ) )
            self.frame_info.append( self.parser.parse_screen( new_screen ) )

            self.reward = reward_generator.compute_reward(self.frame_info[-2], self.frame_info[-1])
            self.state = state_generator.compute_state(self.frame_info[-1])
            
            self.step_count += 1
            self.episode_reward += self.reward
            lose = self.step_count > self.max_step_count or state_generator.need_reset
        
        win = reward_generator.goal_achieved
        if win or lose:
            self.evaluator.add( info = self.frame_info[-1], reward = self.episode_reward, has_won = win, step = self.step_count )

        if win or lose:
            print("waht")
        return self.reward, self.state, win or lose
