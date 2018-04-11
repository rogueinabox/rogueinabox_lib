
class RogueLoopError(RuntimeError):
    """Exception raised when rogue enters an endless loop"""
    pass


class RogueLoopWarning(RuntimeWarning):
    """Warning given when rogue enters an endless loop"""
    pass
