from . import check
from . import events
from . import util
from . import state
from . import var
import sys


def linux(func):
    if sys.platform == "linux":
        return func()
