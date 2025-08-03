import enum


class Format(str, enum.Enum):
    nrrd = "NRRD"
    mgh = "MGH"
    json_nifti = "JSON/JNIfTI"
    bjnifti = "BJNIfTI"
    nifti = "NIfTI"


format_to_string = {
    Format.nrrd: "y",
    Format.mgh: "m",
    Format.json_nifti: "j",
    Format.bjnifti: "b",
    Format.nifti: "n",
}


class LogLevel(enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class WriteBehavior(enum.Enum):
    skip = "skip"  # skip duplicates
    overwrite = "overwrite"  # overwrite existing files
    add_suffix = "suffix"  # add suffix to avoid overwriting


write_behavior_to_int = {
    WriteBehavior.skip: 0,
    WriteBehavior.overwrite: 1,
    WriteBehavior.add_suffix: 2,
}
