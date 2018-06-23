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

try:
    from .baseagent import BaseAgent
    from .options import AgentOptions, RogueBoxOptions
except SystemError:
    # the user is executing this script directly
    # we must append roguelib parent directory to sys.path so the module can be correctly loaded
    import os
    import sys
    import importlib
    dir_path = os.path.dirname(os.path.abspath(__file__))
    parent_path = os.path.abspath(os.path.join(dir_path, os.pardir))
    sys.path.append(parent_path)
    dir_name = os.path.basename(os.path.normpath(dir_path))
    BaseAgent = importlib.import_module("%s.baseagent" % dir_name).BaseAgent
    options_module = importlib.import_module("%s.options" % dir_name)
    AgentOptions = options_module.AgentOptions
    RogueBoxOptions = options_module.RogueBoxOptions
import random


class RandomAgent(BaseAgent):
    """Implements an agent that performs random actions"""

    def act(self):
        actions = self.rb.get_actions()
        action = random.choice(actions)
        _, _, won, lost = self.rb.send_command(action)
        return won or lost


if __name__ == '__main__':
    agent = RandomAgent(AgentOptions(
        gui=True,
        userinterface='curses',
        gui_timer_ms=100,
        roguebox_options=RogueBoxOptions(
            state_generator='SingleLayer_StateGenerator',
            reward_generator='StairSeeker_13_RewardGenerator',
            max_step_count=500)
    ))
    agent.run()
