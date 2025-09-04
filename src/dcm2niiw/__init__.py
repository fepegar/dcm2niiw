from importlib.metadata import version

from .wrapper import dcm2nii

__all__ = [
    "dcm2nii",
]

assert __package__ is not None
__version__ = version(__package__)
