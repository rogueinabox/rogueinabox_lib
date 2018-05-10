import os

from .ui.UIManager import UIManager, UI
from .rogueinabox import RogueBox
from .logger import Logger, Log
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
                "use_monsters": bool
                    whether to use monsters (N.B. "rogue" key should be None for this to have any effect)
                    Default: True
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
                    N.B. this is used only if key "rogue_evaluator" is None
                    Default: 500
                "episodes_for_evaluation": int
                    number of latest episode to consider when computing statistics.
                    N.B. this is used only if key "rogue_evaluator" is None
                    Default: 200
                "rogue_evaluator": evaluator
                    agent evaluator. If None, the default evaluator will be used.
                    Default: None
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
                "busy_wait_seconds": float
                    amount of sleep seconds for each busy wait iteration
                    Default: 0.0005
                "max_busy_wait_seconds: float
                    max amount of seconds that will be waited for before assuming the game has entered an endless loop
                    Default: 5
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
        configs.setdefault("use_monsters", True)
        configs.setdefault("gui", True)
        configs.setdefault("userinterface", "tk")
        configs.setdefault("gui_timer_ms", 100)
        configs.setdefault("max_step_count", 500)
        configs.setdefault("episodes_for_evaluation", 200)
        configs.setdefault("rogue_evaluator", None)
        configs.setdefault("state_generator", "Dummy_StateGenerator")
        configs.setdefault("reward_generator", "Dummy_RewardGenerator")
        configs.setdefault("refresh_after_commands", True)
        configs.setdefault("move_rogue", False)
        configs.setdefault("busy_wait_seconds", 0.0005)
        configs.setdefault("max_busy_wait_seconds", 5)
        configs.setdefault("log_filepath", "logfile.log")
        configs.setdefault("log_depth", 0)

    def _create_rogue(self, configs):
        """Returns a RogueBox instance to interact with the game

        :param dict configs:
            configuration dictionary, see __init__
        :rtype: RogueBox
        """
        rb = RogueBox(game_exe_path=configs["rogue"],
                      use_monsters=configs["use_monsters"],
                      max_step_count=configs["max_step_count"],
                      episodes_for_evaluation=configs["episodes_for_evaluation"],
                      evaluator=configs["rogue_evaluator"],
                      state_generator=configs["state_generator"],
                      reward_generator=configs["reward_generator"],
                      refresh_after_commands=configs["refresh_after_commands"],
                      start_game=True,
                      move_rogue=configs["move_rogue"],
                      busy_wait_seconds=configs["busy_wait_seconds"],
                      max_busy_wait_seconds=configs["max_busy_wait_seconds"])
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
            self.logger.log([Log('start', 'start')])
            while self.rb.is_running():
                terminal = self.act()
                if terminal:
                    self.game_over()
            self.logger.log([Log('exit', 'exit')])

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
        if self.rb.game_over() or terminal:
            self.game_over()
        # renew the callback
        self._pending_action_timer = self.ui.on_timer_end(self._timer_value, self._act_callback)


class AgentWrapper(BaseAgent):
    """
    Wraps an Agent and all of its methods.

    This is inteded to be used a superclass to add functionalities to an agent's method, without altering
    the agent itself. By default, this class does not add anything.

    N.B. wrapping agents with a custom ._act_callback() or .run() method is not supported,
    please implement .act() instead.

    Usage of a wrapper:
        class MyWrapper(AgentWrapper):
            ...

        class MyAgent(BaseAgent):
            ...

        agent = MyAgent(...)
        wrappedAgent = MyWrapper(agent)
        # use wrapperAgent
    """

    def __init__(self, wrappedAgent):
        """
        :param BaseAgent wrappedAgent:
            agent to wrap
        """
        self.wrapped = wrappedAgent
        super().__init__(wrappedAgent.configs)

    def _replace_timer_cb(self, ui=None):
        """
        Replaces the ui timer callback of the wrapped agent with the wrapper's callback

        :param ui:
            ui to use, use None for self.ui
        """
        ui = ui or self.ui
        ui.cancel_timer(self.wrapped._pending_action_timer)
        self._pending_action_timer = ui.on_timer_end(self._timer_value, self._act_callback)

    def _create_rogue(self, configs):
        return self.wrapped.rb

    def _create_ui(self, configs):
        ui = self.wrapped.ui

        if ui is not None:
            # replace key pressed callback
            ui.on_key_press(self._keypress_callback)
            # replace timer callback
            self._timer_value = configs["gui_timer_ms"]
            self._replace_timer_cb(ui)

        return ui

    def _create_logger(self, configs):
        return self.wrapped.logger

    def _keypress_callback(self, event):
        res = self.wrapped._keypress_callback(event)
        self._replace_timer_cb()
        return res

    def _act_callback(self):
        """
        Ignore wrapped ._act_callback() method, this is why agents that customized it are not supported.
        This is necessary otherwise the wrapped agent would call its own .act() method instead of the wrapper's.
        """
        super()._act_callback()

    def act(self):
        return self.wrapped.act()

    def run(self):
        """
        Ignore wrapped .run() method, this is why agents that customized it are not supported.
        This is necessary otherwise the wrapped agent would call its own .act() method instead of the wrapper's.
        """
        return super().run()

    def game_over(self):
        return self.wrapped.game_over()


class RecordingWrapper(AgentWrapper):
    """
    Agent wrapper that records the succession of frames.

    Usage:
        class CustomAgent(BaseAgent):
            ...

        recordedAgent = RecordingWrapper(CustomAgent(...))
        recordedAgent.run()

    """

    def __init__(self, wrappedAgent, record_dir='video', reset_key='rR'):
        """
        :param BaseAgent wrappedAgent:
            agent to wrap
        :param str record_dir:
            path to the directory where to record frames
        :param str reset_key:
            key used to reset the game, use this if your custom agent uses a different key than the default
        """
        super().__init__(wrappedAgent)

        os.makedirs(record_dir, exist_ok=True)

        self.record_dir = record_dir
        self.episode_index = 0
        self.step_count = 0
        self.reset_key = reset_key

        self.game_over()

    def _new_episode(self):
        """
        Registers the beginning of a new episode and records the starting screen
        """
        self.episode_index += 1
        self.step_count = 0
        self.record_screen()

    def act(self):
        """
        Acts according to the wrapped agent then records the resulting screen
        """
        res = super().act()
        self.step_count += 1
        self.record_screen()
        return res

    def _keypress_callback(self, event):
        """
        Registers the beginning of a new episode in case the game is reset

        :param event:
            key pressed event
        """
        res = super()._keypress_callback(event)
        if event.char in self.reset_key:
            self._new_episode()
        return res

    def game_over(self):
        super().game_over()
        self._new_episode()

    def record_screen(self):
        """
        Records the current rogue frame on file in the directory specified during init
        """
        screen = self.rb.get_screen()[:]
        step = str(self.step_count)
        step = '0' * (3 - len(step)) + step
        fname = os.path.join(self.record_dir, 'ep%sst%s.txt' % (self.episode_index, step))
        with open(fname, mode='w') as file:
            print(*screen, sep='\n', file=file)
