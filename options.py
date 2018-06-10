import random


class RogueOptions:
    """Rogue command line parameters object for the custom rogue build"""

    def __init__(self, use_monsters=True, enable_secrets=True, seed=None, fixed_seed=False, amulet_level=26,
                 hungertime=1300, max_traps=0):
        """
        :param bool use_monsters:
            whether to enable monsters
        :param bool enable_secrets:
            whether to enable hidden tiles
        :param int seed:
            sets the random seed of the game
        :param bool fixed_seed:
            whether to keep the same seed every time the arguments are generated (i.e. the game is reset)
        :param int amulet_level:
            sets the level where the amulet of Yendor will be
        :param int hungertime:
            sets the number of steps after which the rouge becomes faint
        :param int max_traps:
            sets the maximum number of traps
        """
        self.use_monsters = use_monsters
        self.enable_secrets = enable_secrets
        self.seed = seed
        self.fixed_seed = fixed_seed
        self.amulet_level = amulet_level
        self.hungertime = hungertime
        self.max_traps = max_traps

        self._rng = random.Random()
        self._seed = None  # current seed for the next args generation

        if not fixed_seed:
            self.set_seed(seed)

    def set_seed(self, seed):
        self._rng.seed(seed)
        self._seed = seed if seed is not None else self._rng.getrandbits(32)

    def generate_args(self):
        args= ['--disable-monsters' if not self.use_monsters else '',
               '--disable-secrets' if not self.enable_secrets else '',
               ('--seed=%s' % self._seed) if self._seed is not None else '',
               ('--amulet-level=%s' % self.amulet_level),
               ('--hungertime=%s' % self.hungertime),
               ('--max-traps=%s' % self.max_traps)]
        if not self.fixed_seed:
            self._seed = self._rng.getrandbits(32)
        return args


class RogueBoxOptions:
    """RogueBox options class"""

    def __init__(self, game_exe_path=None, rogue_options=RogueOptions(),
                 max_step_count=500, episodes_for_evaluation=200, evaluator=None,
                 state_generator="Dummy_StateGenerator", reward_generator="Dummy_RewardGenerator",
                 transform_descent_action=False,
                 refresh_after_commands=True, start_game=False, move_rogue=False,
                 busy_wait_seconds=0.0005, max_busy_wait_seconds=5):
        """
        :param str game_exe_path:
            rogue executable path.
            If None, will use the default executable in the rogue git submodule
        :param RogueOptions rogue_options:
            custom rogue build parameters
            N.B. this is used only if parameter "game_exe_path" is None
        :param int max_step_count:
            maximum number of steps before declaring the game lost.
            N.B. this is used only if parameter "evaluator" is None
        :param int episodes_for_evaluation:
            number of latest episode to consider when computing statistics.
            N.B. this is used only if parameter "evaluator" is None
        :param RogueEvaluator evaluator:
            agent evaluator.
            If None, the default evaluator will be used.
        :param str | states.StateGenerator state_generator:
            default state generator.
            If string, a generator with a corresponding name will be looked for in the states module, otherwise it will
            be use as a state generator itself.
            This will be used to produce state representations when sending commands, unless another state generator
            is provided at that time. See RogueBox.send_command()
        :param str | rewards.RewardGenerator reward_generator:
            default reward generator.
            If string, a generator with a corresponding name will be looked for in rewards module, otherwise it will
            be use as a reward generator itself.
            This will be used to produce rewards when sending commands, unless another reward generator is provided
            at that time. See RogueBox.send_command()
        :param bool transform_descent_action:
            whether to turn descent actions '>' into ascent action '<' from the moment the amulet level is reached
        :param bool refresh_after_commands:
            whether to send screen refresh command to rogue after each command.
            This is useful because sometimes the game does not print every tile correctly, however it introduces
            a small delay for each RogueBox.send_command() call
        :param bool start_game:
            whether to immediately start the game process.
            If false, call the RogueBox instance .reset() method to start the game
        :param bool move_rogue:
            whether to perform a legal move as soon as the game is started.
            This is useful to know the tile below the player.
        :param float busy_wait_seconds:
            amount of sleep seconds for each busy wait iteration
        :param float max_busy_wait_seconds:
            maximum amount of seconds that will be waited for before assuming the game has entered an endless loop
        """
        self.game_exe_path = game_exe_path
        self.rogue_options = rogue_options
        self.max_step_count = max_step_count
        self.episodes_for_evaluation = episodes_for_evaluation
        self.evaluator = evaluator
        self.state_generator = state_generator
        self.reward_generator = reward_generator
        self.transform_descent_action = transform_descent_action
        self.refresh_after_commands = refresh_after_commands
        self.start_game = start_game
        self.move_rogue = move_rogue
        self.busy_wait_seconds = busy_wait_seconds
        self.max_busy_wait_seconds = max_busy_wait_seconds


class AgentOptions:
    """Rogue agent options class"""

    def __init__(self, roguebox_options=RogueBoxOptions(), gui=True, userinterface="curses", gui_timer_ms=50,
                 log_filepath="logfile.log", log_depth=0):
        """
        :param RogueBoxOptions roguebox_options:
             RogueBox options object, see its documentation
        :param bool gui:
            whether to display the game played by the agent in a window
        :param str userinterface:
            ui to be used, values supported: "tk", "curses"
        :param int gui_timer_ms:
           time interval in milliseconds between each action
        :param str log_filepath:
             log file path
        :param int log_depth:
            maximum log depth, see Logger
        """
        self.roguebox_options = roguebox_options
        self.gui = gui
        self.userinterface = userinterface
        self.gui_timer_ms = gui_timer_ms
        self.log_filepath = log_filepath
        self.log_depth = log_depth
