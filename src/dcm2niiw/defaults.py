from .enums import Format
from .enums import WriteBehavior

DEFAULT_COMPRESSION_LEVEL = 6
DEFAULT_COMPRESS = True  # originally False
DEFAULT_DEPTH = 5
DEFAULT_FORMAT = Format.nifti
DEFAULT_FILENAME_FORMAT = "%j"
DEFAULT_VERBOSE_LEVEL = 0
DEFAULT_WRITE_BEHAVIOR = WriteBehavior.overwrite  # originally add suffix
MAX_COMMENT_LENGTH = 24
MAX_VERBOSE_LEVEL = 2
