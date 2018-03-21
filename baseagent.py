from .ui.UIManager import UIManager, UI
from .rogueinabox import RogueBox
from .logger import Logger
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """
    Convenience class for displaying an agent policy in action.

    Implementing classes must define the .act() method, that should perform an action in the game (see the abstract
    method for further details).

    A logger is instantiated in attribute .logger that provides a simple api for logging messages, abstracting the
    underlying media, i.e. the terminal, the ui and the log file.

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
                    Default: "Dummy_StateGenerator"
                "reward_generator": rewards.RewardGenerator
                    state generator to be used
                    Default: "Dummy_RewardGenerator"
                "refresh_after_commands": bool
                    whether to issue a refresh command after each action
                    Default: True
                "move_rogue": bool
                    whether to perform a legal move as soon as the game is started
                    Default: False
                "log_filepath": str
                    log file path
                    Default: "logfile.log"
                "log_depth": int
                    maximum log depth, see Logger
                    Default: 0
        """
        self._fill_default_configs(configs)
        self.configs = configs
        self.rb = self._create_rogue(configs)
        self.ui = self._create_ui(configs)
        self.logger = self._create_logger(configs)

    @staticmethod
    def _fill_default_configs(configs):
        """Fills the given configuration dict with the default values, according to the __init__ documentation

        :param dict configs:
            dict to fill
        """
        configs.setdefault("rogue", None)
        configs.setdefault("gui", True)
        configs.setdefault("userinterface", "tk")
        configs.setdefault("gui_timer_ms", 100)
        configs.setdefault("max_step_count", 500)
        configs.setdefault("state_generator", "Dummy_StateGenerator")
        configs.setdefault("reward_generator", "Dummy_RewardGenerator")
        configs.setdefault("refresh_after_commands", True)
        configs.setdefault("move_rogue", False)
        configs.setdefault("log_filepath", "logfile.log")
        configs.setdefault("log_depth", 0)

    def _create_rogue(self, configs):
        """Returns a RogueBox instance to interact with the game

        :param dict configs:
            configuration dictionary, see __init__
        :rtype: RogueBox
        """
        rb = RogueBox(game_exe_path=configs["rogue"],
                      max_step_count=configs["max_step_count"],
                      state_generator=configs["state_generator"],
                      reward_generator=configs["reward_generator"],
                      refresh_after_commands=configs["refresh_after_commands"],
                      start_game=True,
                      move_rogue=configs["move_rogue"])
        return rb

    def _create_ui(self, configs):
        """Returns the user interface to display the game

        :param dict configs:
            configuration dictionary, see __init__
        :rtype: UI
        """
        if configs["gui"]:
            self._pending_action_timer = None
            ui = UIManager.init(configs["userinterface"], self.rb)
            ui.on_key_press(self._keypress_callback)
            self._timer_value = configs["gui_timer_ms"]
            self._pending_action_timer = ui.on_timer_end(self._timer_value, self._act_callback)
            return ui
        return None

    def _create_logger(self, configs):
        """Returns a logger

        :param configs:
            configuration dictionary, see __init__
        :rtype: Logger
        """
        targets = ["ui" if configs["gui"] else "terminal", "file"]
        return Logger(log_depth=configs["log_depth"],
                      log_targets=targets,
                      filepath=configs["log_filepath"],
                      ui=self.ui)

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
        """Starts the interacton with the game"""
        if self.ui is not None:
            self.ui.start_ui()
        else:
            while (self.rb.is_running()):
                self.act()

    def game_over(self):
        """Called each time a terminal state is reached.
        By default restarts the game.
        """
        self.rb.reset()

    def _keypress_callback(self, event):
        """Handles the event generated by the user pressing a button.

        By default:
            - quits if buttons 'q' or 'Q' are pressed
            - restarts if buttons 'r' or 'R' are pressed

        :param event:
            object with a .char string attribute containing the pressed key
        """
        if event.char == 'q' or event.char == 'Q':
            self.rb.quit_the_game()
            exit()
        elif event.char == 'r' or event.char == 'R':
            # we need to stop the agent from acting
            # or it will try to write to a closed pipe
            self.ui.cancel_timer(self._pending_action_timer)
            self.rb.reset()
            self.ui.draw_from_rogue()
            self._pending_action_timer = self.ui.on_timer_end(self._timer_value, self._act_callback)

    def _act_callback(self):
        """Called every configs["gui_timer_ms"] millisecods.

        By default:
            - executes an action
            - redraws the screen on the ui
            - restarts the game if a terminal state is reached
        """
        terminal = self.act()
        self.ui.draw_from_rogue()
        if not self.rb.game_over() or terminal:
            # renew the callback
            self._pending_action_timer = self.ui.on_timer_end(self._timer_value, self._act_callback)
        else:
            self.game_over()
