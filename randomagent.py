from .baseagent import BaseAgent
from .options import AgentOptions, RogueBoxOptions
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
        userinterface='tk',
        gui_timer_ms=100,
        roguebox_options=RogueBoxOptions(
            state_generator='SingleLayer_StateGenerator',
            reward_generator='StairSeeker_13_RewardGenerator',
            max_step_count=500)
    ))
    agent.run()
