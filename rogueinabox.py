# Copyright (C) 2017 Andrea Asperti, Carlo De Pieri, Gianmaria Pedrini, Francesco Sovrano
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

import time
import os
import fcntl
import pty
import signal
import shlex
import pyte
import shutil

from .parser import RogueParser
from .evaluator import RogueEvaluator
from . import states
from . import rewards


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
    """Start a rogue game and expose interface to communicate with it.

    Usage example:

        rb = RogueBox(state_generator="SingleLayer_StateGenerator", reward_generator="StairSeeker_RewardGenerator")

        # get actions list
        actions = rb.get_actions()
        # get initial state
        state = rb.get_current_state()

        terminal = False
        while not terminal:
            act = compute_action(state, actions)
            reward, state, won, lost = rb.send_command(act)
            terminal = won or lost

    """

    @staticmethod
    def get_actions():
        """return the list of actions"""
        # h, j, k, l: ortogonal moves
        # y, u, b, n: diagonal moves
        # >: go downstairs
        # return ['h', 'j', 'k', 'l', '>', 'y', 'u', 'b', 'n']
        return ['h', 'j', 'k', 'l', '>']

    @staticmethod
    def default_game_exe_path(use_monsters=True):
        exe_name = 'rogue_monsters' if use_monsters else 'rogue_without_monsters'
        this_file_dir = os.path.dirname(os.path.realpath(__file__))
        rogue_path = os.path.join(this_file_dir, 'rogue', exe_name)
        return rogue_path

    def __init__(self, game_exe_path=None, use_monsters=True, max_step_count=500, evaluator=None,
                 state_generator="Dummy_StateGenerator", reward_generator="Dummy_RewardGenerator",
                 refresh_after_commands=True, start_game=False, move_rogue=False):
        """
        :param str game_exe_path:
            rogue executable path.
            If None, will use the default executable in the rogue git submodule, either "./rogue/rogue_monsters"
            or "./rogue/rogue_without_monsters", depending on the "use_monsters" parameter.
        :param bool use_monsters:
            whether to enable monsters in the game.
            N.B. this is used only if parameter "game_exe_path" is None
        :param int max_step_count:
            maximum number of steps before declaring the game lost.
            N.B. this is used only if parameter "evaluator" is None
        :param RogueEvaluator evaluator:
            agent evaluator.
            If None, the default evaluator will be used.
        :param str | states.StateGenerator state_generator:
            default state generator.
            If string, a generator with a corresponding name will be looked for in the states module, otherwise it will
            be use as a state generator itself.
            This will be used to produce state representations when sending commands, unless another state generator
            is provided at that time. See .send_command()
        :param str | rewards.RewardGenerator reward_generator:
            default reward generator.
            If string, a generator with a corresponding name will be looked for in rewards module, otherwise it will
            be use as a reward generator itself.
            This will be used to produce rewards when sending commands, unless another reward generator is provided
            at that time. See .send_command()
        :param bool refresh_after_commands:
            whether to send screen refresh command to rogue after each command.
            This is useful because sometimes the game does not print every tile correctly, however it introduces
            a small delay for each .send_command() call
        :param bool start_game:
            whether to immediately start the game process.
            If false, call .reset() to start the game
        :param bool move_rogue:
            whether to perform a legal move as soon as the game is started.
            This is useful to know the tile below the player.
        """
        self.rogue_path = game_exe_path or self.default_game_exe_path(use_monsters=use_monsters)
        if not shutil.which(self.rogue_path):
            raise ValueError('game_exe_path "%s" is not executable' % self.rogue_path)

        self.parser = RogueParser()

        self.evaluator = evaluator if evaluator is not None else RogueEvaluator(max_step_count=max_step_count)

        if reward_generator is None:
            raise ValueError('reward generator cannot be None, use "Dummy_RewardGenerator" instead')
        if isinstance(reward_generator, str):
            if not hasattr(rewards, reward_generator):
                raise ValueError('no reward generator named "%s" was found' % reward_generator)
            self.reward_generator = getattr(rewards, reward_generator)()
        else:
            self.reward_generator = reward_generator

        if state_generator is None:
            raise ValueError('state generator cannot be None, use "Dummy_StateGenerator" instead')
        if isinstance(state_generator, str):
            if not hasattr(states, state_generator):
                raise ValueError('no state generator named "%s" was found' % state_generator)
            self.state_generator = getattr(states, state_generator)()
        else:
            self.state_generator = state_generator

        self.refresh_after_commands = refresh_after_commands
        self.refresh_command = '\x12'.encode()

        self.move_rogue = move_rogue

        self.has_cmd_count = False

        if start_game:
            self._start()

    def _start(self):
        """Start the game.
        If move_rogue was set to True in init, perform a legal move to see the tile below the player and the resulting
        state will be returned.

        :return:
            if move_rogue was set to True in init:
                (reward, state, won, lost)
            else:
                None
        """
        # reset internal variables
        self.step_count = 0
        self.state = None
        self.reward = None

        self.evaluator.on_run_begin()
        self.parser.reset()
        self.reward_generator.reset()
        self.state_generator.reset()

        # start game process
        self.terminal, self.pid, self.pipe = open_terminal(command=self.rogue_path)

        if not self.is_running():
            print("Could not find the executable in %s." % self.rogue_path)
            exit()

        # wait until the rogue spawns
        self.screen = self.get_empty_screen()
        self._update_screen()
        while not "Exp:" in self.screen[-1]:
            self._update_screen()

        if not self.has_cmd_count:
            # if self.has_cmd_count was True then we found the cmd count previously so it will be still there
            # otherwise it may be the first time the game is started so we will check
            self.has_cmd_count = "Cmd" in self.screen[-1]

        self.frame_history = [self.parser.parse_screen(self.screen)]

        if self.move_rogue:
            # we move the rogue to be able to see the tile below it
            action = self.get_legal_actions()[0]
            return self.send_command(action)
        else:
            self.state = self.state_generator.compute_state(self.frame_history)

    def reset(self):
        """Kill and restart the rogue process.
        If move_rogue was set to True in init, an initial legal action is performed and the resulting state returned.

        :return:
            if move_rogue was set to True in init:
                (reward, state, won, lost)
            else:
                None
        """
        self.stop()
        return self._start()

    def stop(self):
        """kill the rogue process"""
        if self.is_running():
            self.pipe.close()
            os.kill(self.pid, signal.SIGTERM)
            # wait the process so it doesnt became a zombie
            os.waitpid(self.pid, 0)

    def get_current_state(self):
        """return the current state representation of the game.
        This is the same state returned by the last .send_command() call, or the initial state.
        """
        return self.state

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
        """current player position"""
        return self.frame_history[-1].get_list_of_positions_by_tile("@")[0]

    @property
    def stairs_pos(self):
        """current stairs position or None if they are not visibile"""
        stairs = self.frame_history[-1].get_list_of_positions_by_tile("%")
        if stairs:
            return stairs[0]
        else:
            return None

    def get_legal_actions(self):
        """return the list of legal actions in the current screen"""
        actions = []
        row = self.player_pos[0]
        column = self.player_pos[1]
        if self.screen[row - 1][column] not in '-| ':
            actions += ['k']
        if self.screen[row + 1][column] not in '-| ':
            actions += ['j']
        if self.screen[row][column - 1] not in '-| ':
            actions += ['h']
        if self.screen[row][column + 1] not in '-| ':
            actions += ['l']
        if self.player_pos == self.stairs_pos:
            actions += ['>']
        return actions

    def game_over(self, screen=None):
        """check if we are at the game over screen (tombstone)"""
        if not screen:
            screen = self.screen
        # TODO: this returns True also for inventory screens
        return not ('Hp:' in screen[-1])

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

    def currently_in_corridor(self):
        """return whether the rogue is in a corridor"""
        info = self.frame_history[-1]
        return info.get_tile_below_player() == "#"

    def currently_in_door(self):
        """return whether the rogue is on a door"""
        info = self.frame_history[-1]
        return info.get_tile_below_player() == '+'

    def _dismiss_message(self):
        """dismiss a rogue status message (N.B. does not refresh the screen)"""
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

    def _dismiss_all_messages(self):
        """dismiss all status messages and refresh the screen"""
        while self._need_to_dismiss():
            self._dismiss_message()
            self._update_screen()

    def quit_the_game(self):
        """Send the keystroke needed to quit the game."""
        self.pipe.write('Q'.encode())
        self.pipe.write('y'.encode())
        self.pipe.write('\n'.encode())

    def get_last_frame(self):
        return self.frame_history[-1]

    def _cmd_busy_wait(self):
        """perform busy wait on the rogue custom build with command count"""
        cmd_increment = 1 if not self.refresh_after_commands else 2
        old_cmd_count = self.frame_history[-1].statusbar["command_count"]
        expected_cmd_count = old_cmd_count + cmd_increment
        new_cmd_count = old_cmd_count
        # busy wait until the cmd count is increased
        # the command count may increase more than expected, e.g. when a monster is next to the rogue and he moves
        # parallel to it the count is increased by 2
        while new_cmd_count < expected_cmd_count:
            self._update_screen()
            if self.refresh_after_commands and self._need_to_dismiss():
                # if the refresh command is sent when a dismissable "...--More--" message is on screen, then
                # the cmd count will not increase
                expected_cmd_count -= 1
            self._dismiss_all_messages()
            if self.game_over():
                break
            try:
                # very rarely, the screen does not completely refresh
                # in particular the status bar may not be totally drawn
                # in principle this means we could get a lower cmd count (if some but not all the digits were drawn)
                bak_cmd_count = new_cmd_count
                new_cmd_count = self.parser.get_cmd_count(self.screen)
                if new_cmd_count < bak_cmd_count:
                    new_cmd_count = bak_cmd_count
            except RuntimeError:
                # screen was not fully refreshed and did not contain yet the cmd count
                continue

    def send_command(self, command, state_generator=None, reward_generator=None):
        """send a command to rogue and return (reward, state, won, lost).
        If passed generators are None, the ones supplied during init are used.

        :param str command:
            command to send, one in  .get_actions()
        :param states.StateGenerator state_generator:
            state builder, if None the one supplied during init will be used
        :param rewards.RewardGenerator reward_generator:
            reward generator, if None the one supplied during init will be used
        :return:
            (reward, state, won, lost)
        """

        old_screen = self.screen
        self.pipe.write(command.encode())
        # rogue may not properly print all tiles after elaborating a command
        # so, based on the init options, we send a refresh command
        if self.refresh_after_commands:
            self.pipe.write(self.refresh_command)

        # wait until rogue elaborates the command
        if self.has_cmd_count:
            # this is a custom build of rogue that prints a cmd count in the status bar that is updated as soon as a
            # command is elaborated, so we can perform busy waiting
            self._cmd_busy_wait()
        else:
            # this build of rogue does not provide an easy and fast way to determine if the command elaboration is
            # done, so we must wait a fixed amount of time
            time.sleep(0.01)
            self._update_screen()
            self._dismiss_all_messages()

        self.step_count += 1

        new_screen = self.screen
        self.frame_history.append(self.parser.parse_screen(new_screen))

        state_generator = state_generator or self.state_generator
        reward_generator = reward_generator or self.reward_generator
        self.reward = reward_generator.compute_reward(self.frame_history)
        self.state = state_generator.compute_state(self.frame_history)

        is_rogue_dead = self.game_over(new_screen)
        won = (reward_generator and reward_generator.goal_achieved)
        stop = self.evaluator.on_step(self.frame_history, command, self.reward, self.step_count)
        lost = (stop or is_rogue_dead) and not won

        is_run_over = stop or is_rogue_dead or won
        if is_run_over:
            self.evaluator.on_run_end(won)

        return self.reward, self.state, won, lost
