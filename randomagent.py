from ui.UIManager import UIManager
from rogueinabox import RogueBox
import random

class RandomAgent():
    configuration_manager_style = "single"

    def __init__(self, configs):
        self.rb = RogueBox(configs["rogue"])
        self.configs = configs
        self._pending_action_timer = None
        self.ui = UIManager.init(configs["userinterface"], self.rb)
        self.ui.on_key_press(self._keypress_callback)
        self._timer_value = 100
        self._pending_action_timer = self.ui.on_timer_end(self._timer_value, self._act_callback)

    def run(self):
        if self.configs["gui"]:
            self.ui.start_ui()
        else:
            while(self.rb.is_running()):
                self.act()



    def act(self):
        actions = self.rb.get_actions()
        action = random.choice(actions)
        screen_transition, terminal = self.rb.send_command(action)
        return terminal

    def _keypress_callback(self, event):
        if event.char == 'q' or event.char == 'Q':
            self.rb.quit_the_game()
            exit()
        elif event.char == 'r' or event.char == 'R':
            # we need to stop the agent from acting
            # or it will try to write to a closed pipe
            self.ui.cancel_timer(self._pending_action_timer)
            self.rb.reset()
            self._pending_action_timer = self.ui.on_timer_end(self._timer_value, self._act_callback)

    def game_over(self):
        # This must stay a separate method because of the interaction with the Judges
        # Takes care of restarting rogue and the agent
        self.rb.reset()

    def _act_callback(self):
        terminal = self.act()
        self.ui.draw_from_rogue()
        if not self.rb.game_over():
            # renew the callback
            self._pending_action_timer = self.ui.on_timer_end(self._timer_value, self._act_callback)
        else:
            self.game_over()
            #self.ui.cancel_timer(self._pending_action_timer)


if __name__ == '__main__':
    configs = { 
       'userinterface': 'tk',
       'verbose': 3,
       'gui': True,
       'rogue': 'rogue',
       'memory_size': 0,
       'test': False
    }

    agent = RandomAgent(configs)
    agent.run()
