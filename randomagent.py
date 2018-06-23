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
