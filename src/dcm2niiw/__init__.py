from importlib.metadata import version

from .wrapper import dcm2niiw

__all__ = [
    "dcm2niiw",
]

assert __package__ is not None
__version__ = version(__package__)
