from .ui.UIManager import UIManager
from .rogueinabox import RogueBox
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """
    Convenience class for displaying an agent policy in action.

    Implementing classes must define the .act() method, that should perform an action in the game.
    See the abstract method for further details.

    The constructor accepts a configuration parameter, see __init__ for details.
    """

    def __init__(self, configs):
        """
        :param dict configs:
            configuration dictionary, the following keys are supported:
                "rogue": str
                    rogue game executable path
                    Default: rogueinabox's custom build executable
                "gui": bool
                    whether to display the game played by the agent in a window
                    Default: True
                "userinterface": "tk" | "curses"
                    ui to be used
                    Default: "tk"
                "gui_timer_ms": int
                    time interval in milliseconds between each action
                    Default: 100
                "max_step_count": int
                    maximum number of steps per episode
                    Default: 500
                "state_generator": states.StateGenerator
                    state generator to be used
                    Default: None
                "reward_generator": rewards.RewardGenerator
                    state generator to be used
                    Default: None
                "refresh_after_commands": bool
                    whether to issue a refresh command after each action
                    Default: True
        """
        self.configs = configs
        self.rb = self._create_rogue(configs)
        self._init_ui(configs)

    def _create_rogue(self, configs):
        """
        :param dict configs:
            configs to be used
        :rtype: RogueBox
        """
        rb = RogueBox(game_exe_path=configs.get("rogue"),
                      max_step_count=configs.get("max_step_count", 500),
                      state_generator=configs.get("state_generator"),
                      reward_generator=configs.get("reward_generator"),
                      refresh_after_commands=configs.get("refresh_after_commands", True),
                      start_game=True)
        return rb

    def _init_ui(self, configs):
        if self.configs.get("gui", True):
            self._pending_action_timer = None
            self.ui = UIManager.init(configs.get("userinterface", "tk"), self.rb)
            self.ui.on_key_press(self._keypress_callback)
            self._timer_value = configs.get("gui_timer_ms", 100)
            self._pending_action_timer = self.ui.on_timer_end(self._timer_value, self._act_callback)
        else:
            self.ui = None

    @abstractmethod
    def act(self):
        """Perform an action in the game and return whether the next state is terminal, according to any condition.

        Use the following instruction to perform an action an get the result:
            reward, state, won, lost = self.rb.send_command(<action>)

        :rtype : bool
        :return: whether next state is terminal
        """
        pass

    def run(self):
        if self.ui is not None:
            self.ui.start_ui()
        else:
            while (self.rb.is_running()):
                self.act()

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
        if not self.rb.game_over() or terminal:
            # renew the callback
            self._pending_action_timer = self.ui.on_timer_end(self._timer_value, self._act_callback)
        else:
            self.game_over()
