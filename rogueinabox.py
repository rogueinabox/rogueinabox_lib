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

import time
import os
import fcntl
import pty
import signal
import shlex
import datetime
import pyte
import re
import numpy as np
import itertools
import scipy
import json

#from rogueinabox import states


TEST_RUN = 500
MONSTERS = ["QWERTYUIOPASDFGHJKLZXCVBNM"]
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


class StateManager:

    def __init__(self):
        self._room = []
        self._corridor = []
        self._door = []
        self._rogue = None
        self._stairs = None


    def reset(self, screen=None):
        self._room = []
        self._corridor = []
        self._door = []
        self._rogue = None
        self._stairs = []
        if screen:
            self.update(screen)



    def update(self, screen):
        for i, j in itertools.product(range(1, 23), range(80)):
            tile = screen[i][j]
            # i and j are screen coordinates
            # x and y are state coordinates; states have 2 less rows (one from top and one from bottom of the screen)
            x = i-1
            y = j

            if tile in '.:?!*+])=/%' and not (x,y) in self._room:
                self._room.append((x,y))

            #if tile in MONSTERS:
            #    adj = [(i+1,j), (i-1,j), (i,j-1), (i,j+1)]
            

            if tile == '#' and not (x,y) in self._corridor:
                self._corridor.append((x,y))

            if tile == '+' and not (x,y) in self._door:
                self._door.append((x,y))

            if tile == '@':
                self._rogue = (x,y)

            if tile == '%':
                self._stairs = (x,y) 


    def set_layer(self, layer, positions, state, value=255):
        for pos in positions:
            if pos:
                i, j = pos
                state[layer][i][j] = value

    @property
    def rogue(self):
        return self._rogue

    @property
    def room(self):
        return self._room

    @property
    def corridor(self):
        return self._corridor

    @property
    def door(self):
        return self._door

    @property
    def stairs(self):
        return self._stairs



class RogueBox:
    """Start a rogue game and expose interface to communicate with it"""
    #init methods
    moves = 0
    run_counter = 0
    test_stats = {
                "success" : 0, #percentuale di successi
                "tiles" : [],  #tiles scoperte in media
                "moves" : []   #numero medio di mosse per scendere
    }


    def __init__(self, configs):
        """start rogue and get initial screen"""
        self.configs = configs
        self.rogue_path = self.configs["rogue"]
        self.memory_size = self.configs["memory_size"]
        self.terminal, self.pid, self.pipe = open_terminal(command=self.rogue_path)
        # our internal screen is list of lines, each line is a string
        # can be indexed as a 24x80 matrix
        self.screen = []
        self.stairs_pos = None
        #self.player_pos = None
        self.past_positions = []
        self.test = configs["test"]
        self.state = StateManager()
        time.sleep(0.5)
        if not self.is_running():
            print("Could not find the executable in %s." % self.rogue_path)
            exit()
        self._update_screen()
        self.state.update(self.screen)
        #try:
            #self._update_player_pos()
        #except:
            #pass
        self.parse_statusbar_re = self._compile_statusbar_re()
        #self.reward_generator = getattr(rewards, self.configs["reward_generator"])(self)

    @staticmethod
    def _compile_statusbar_re():
        parse_statusbar_re = re.compile(r"""
                Level:\s*(?P<dungeon_level>\d*)\s*
                Gold:\s*(?P<gold>\d*)\s*
                Hp:\s*(?P<current_hp>\d*)\((?P<max_hp>\d*)\)\s*
                Str:\s*(?P<current_strength>\d*)\((?P<max_strength>\d*)\)\s*
                Arm:\s*(?P<armor>\d*)\s*
                Exp:\s*(?P<exp_level>\d*)/(?P<tot_exp>\d*)\s*
                (?P<status>(Hungry|Weak|Faint)?)\s*""", re.VERBOSE)
        return parse_statusbar_re

    def _update_screen(self):
        """update the virtual screen and the class variable"""
        update = self.pipe.read(65536)
        if update:
            self.terminal.feed(update)
            self.screen = self.terminal.read()

    @property
    def player_pos(self):
        return self.state.rogue

    # get info methods

    def get_actions(self):
        """return the list of actions"""
        actions = ['h', 'j', 'k', 'l', '>']
        #actions = ['h', 'j', 'k', 'l']
        return actions

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

    def print_screen(self):
        """print the current screen"""
        print(*self.screen, sep='\n')

    def get_screen(self):
        """return the screen as a list of strings.
        can be treated like a 24x80 matrix of characters (screen[17][42])"""
        return self.screen

    def get_stat(self, stat):
        """Get the chosen 'stat' from the current screen as a string. Available stats:
        dungeon_level, gold, current_hp, max_hp, 
        current_strength, max_strength, armor, exp_level, tot_exp """
        return self._get_stat_from_screen(stat, self.screen)

    def _get_stat_from_screen(self, stat, screen):
        """Get the chosen 'stat' from the given 'screen' as a string. Available stats:
        dungeon_level, gold, current_hp, max_hp, 
        current_strength, max_strength, armor, exp_level, tot_exp """
        parsed_status_bar = self.parse_statusbar_re.match(screen[-1])
        answer = None
        if parsed_status_bar:
            answer = parsed_status_bar.groupdict()[stat]
        return answer

    def get_screen_string(self):
        """return the screen as a single string with \n at EOL"""
        out = ""
        for line in self.screen:
            out += line
            out += '\n'
        return out

    def game_over(self):
        """check if we are at the game over screen (tombstone)"""
        # look for tombstone
        for line in self.screen:
            if '_______)' in line or 'You quit' in line:
                return True
        return False

    def is_map_view(self, screen):
        """return True if the current screen is the dungeon map, False otherwise"""
        statusbar = screen[-1]
        parsed_statusbar = self.parse_statusbar_re.match(statusbar)
        if parsed_statusbar:
            # if there is a status bar
            return True
        else:
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

    def currently_in_corridor(self):
        return self.state.rogue in self.state.corridor #or self.state.rogue in self.state.door

    def currently_in_door(self):
        return self.state.rogue in self.state.door
    
    def in_corridor(self, screen, ppos):
        if not ppos:
            return False

        res = False

        #the player is in a corridor if one or more adjacent tiles are corridor
        # and there are no '.'
        # standing on a door != being in a corridor
        for i in range(ppos[0]-1, ppos[0]+2):
            for j in range(ppos[1]-1,ppos[1]+2):
                try:
                    if screen[i][j] == '.':
                        return False
                    if screen[i][j] == '#':
                        res = True
                except IndexError:
                    continue

        return res

    def in_corridor_door(self, screen, ppos):
        if not ppos:
            return False

        real = (ppos[0], ppos[1])
        for i, row in enumerate(screen):
            for j, col in enumerate(screen[i]):
                if screen[i][j] == '@':
                    real = (i,j)

        if real != ppos:
            print("stop here")
            pass

        #the player is in a corridor if one or more adjacent tiles are corridor
        # standing on a door == being in a corridor
        for i in range(ppos[0]-1, ppos[0]+2):
            for j in range(ppos[1]-1,ppos[1]+2):
                try:
                    if screen[i][j] == '#':
                        return True
                except IndexError:
                    continue

        return False


    # interact with rogue methods
        
    def send_command(self, command, stride=1):
        """send a command to rogue"""
        old_screen = self.screen[:]
        lvl = self.get_stat("dungeon_level")
        if stride > 1 and stride < 10 and command in self.get_actions():
            self.pipe.write(str(stride).encode())
        self.pipe.write(command.encode())
        if command in self.get_actions():
            self.pipe.write('\x12'.encode())
        time.sleep(0.01)
        self._update_screen()
        if self._need_to_dismiss():
            # will dismiss all upcoming messages,
            # because dismiss_message() calls send_command() again
            self._dismiss_message()
        new_screen = self.screen[:]

        terminal = self.game_over()
        if terminal:
            self.state.reset()
        elif self.get_stat("dungeon_level") > lvl:
            self.state.reset(new_screen)
        else:
            self.state.update(new_screen)

        self._update_stairs_pos(old_screen, new_screen)
        #self._update_player_pos()
        self._update_past_positions(old_screen, new_screen)

        #if self.reward_generator.objective_achieved or self.state_generator.need_reset:
            #terminal = True

        if self.test and command in self.get_actions():
            self.moves += 1
            lvl = self.get_stat("dungeon_level")
            if self.get_stat("status") in ["Hungry", "Weak", "Faint"] or self.game_over() or self.moves >= 500:
                # a random agent usually terminates in < 400 moves
                self.test_stats["tiles"].append(self.count_passables())
                print("terminated run number {}".format(self.run_counter))
                self.moves = 0
                self.run_counter += 1
                self.reset()
                terminal = True
            elif lvl and int(lvl) > 1:
                self.test_stats["success"] += 1
                self.test_stats["tiles"].append(self.count_passables())
                self.test_stats["moves"].append(self.moves)
                self.moves = 0
                terminal = True
                print("terminated run number {}".format(self.run_counter))
                self.run_counter += 1
                self.reset()
                terminal = True

            if self.run_counter >= TEST_RUN:
                self.quit_the_game()
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

        return (old_screen, new_screen), terminal


    def _dismiss_message(self):
        """dismiss a rogue status message.
        call it once, because it will call itself again until
        all messages are dismissed (through send_command())"""
        messagebar = self.screen[0]
        if "ore--" in messagebar:
            # press space
            self.send_command(' ')
        elif "all it" in messagebar:
            # press esc
            self.send_command('\e')

    def _need_to_dismiss(self):
        """check if there are status messages that need to be dismissed"""
        messagebar = self.screen[0]
        if "all it" in messagebar or "ore--" in messagebar:
            return True
        else:
            return False

    def _update_stairs_pos(self, old_screen, new_screen):
        old_statusbar = old_screen[-1]
        new_statusbar = new_screen[-1]
        parsed_old_statusbar = self.parse_statusbar_re.match(old_statusbar)
        parsed_new_statusbar = self.parse_statusbar_re.match(new_statusbar)
        if parsed_old_statusbar and parsed_new_statusbar:
            old_statusbar_infos = parsed_old_statusbar.groupdict()
            new_statusbar_infos = parsed_new_statusbar.groupdict()
            if new_statusbar_infos["dungeon_level"] > old_statusbar_infos["dungeon_level"]:
                #changed floor, reset stairsposition to unknown
                self.stairs_pos = None
            # search the screen for visible stairs
            for i, j in itertools.product(range(1, 23), range(80)):
                pixel = new_screen[i][j]
                if pixel == "%":
                    self.stairs_pos = (i, j)

    #def _update_player_pos(self):
        #found = False
        #for i, j in itertools.product(range(1, 23), range(80)):
            #pixel = self.screen[i][j]
            #if pixel == "@":
                #found = True
                #self.player_pos = (i, j)
        #if not found:
            #self.player_pos = None


    def _update_past_positions(self, old_screen, new_screen):
        old_statusbar = old_screen[-1]
        new_statusbar = new_screen[-1]
        parsed_old_statusbar = self.parse_statusbar_re.match(old_statusbar)
        parsed_new_statusbar = self.parse_statusbar_re.match(new_statusbar)
        if parsed_old_statusbar and parsed_new_statusbar:
            old_statusbar_infos = parsed_old_statusbar.groupdict()
            new_statusbar_infos = parsed_new_statusbar.groupdict()
            if int(new_statusbar_infos["dungeon_level"]) > int(old_statusbar_infos["dungeon_level"]):
                self.past_positions = []
            elif self.memory_size > 0 and len(self.past_positions) > self.memory_size:
                self.past_positions.pop(0)
        self.past_positions.append(self.player_pos)


    def count_passables(self):
        """Count the passable tiles in the current screen and returns it as an int."""
        return self._count_passables_in_screen(self.screen)


    def _count_passables_in_screen(self, screen):
        """Count the passable tiles in a given 'screen' (24*80 matrix) and returns it as an int."""
        passables = 0
        impassable_pixels =  '|- '
        for line in screen:
            for pixel in line:
                if pixel not in impassable_pixels:
                    passables += 1
        return passables


    def reset(self):
        """kill and restart the rogue process"""
        if self.is_running():
            os.kill(self.pid, signal.SIGTERM)
            # wait the process so it doesnt became a zombie
            os.waitpid(self.pid, 0)
        try:
            self.pipe.close()
        except:
            pass
        try:
            self.__init__(self.configs)
        except:
            self.reset()


    def quit_the_game(self):
        """Send the keystroke needed to quit the game."""
        self.send_command('Q')
        self.send_command('y')
        self.send_command('\n')
