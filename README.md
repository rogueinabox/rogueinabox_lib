Rogueinabox: a Rogue environment for AI learning
==========

  Rogueinabox is a higly modular and configurable learning environment built around the videogame Rogue,
  the father of the roguelike genre.
  
  It offers easy ways to interact with the game, especially for the reinforcement learning setting,
  providing several built-in state and reward generators and utilities for creating custom ones. 


Cloning
-------

  This library comes with its own custom Rogue build, which has its own git repo and is included as a submodule.
  In order for it to be correctly initialized and used, please clone this repo with the following command:
  ```console
  git clone --recurse-submodules https://gitlab.com/rogueinabox/roguelib_module.git
  ```

  If you cloned without any flags, please run the following command from within your local repo directory:
  ```console
  git submodule update --init --recursive
  ```
