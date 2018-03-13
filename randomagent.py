from .baseagent import BaseAgent
import random


class RandomAgent(BaseAgent):
    configuration_manager_style = "single"

    def act(self):
        actions = self.rb.get_actions()
        action = random.choice(actions)
        _, _, won, lost = self.rb.send_command(action)
        return won or lost


if __name__ == '__main__':
    configs = {
        'userinterface': 'tk',
        'gui': True,
        'gui_timer_ms': 100,
        'state_generator': 'SingleLayer_StateGenerator',
        'reward_generator': 'StairSeeker_13_RewardGenerator',
        'max_step_count': 500
    }

    agent = RandomAgent(configs)
    agent.run()
