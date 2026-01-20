from __future__ import annotations

from itertools import chain
from pathlib import Path
from subprocess import PIPE
from subprocess import Popen

import loguru
import typer
from dcm2niix import bin as dcm2niix_path
from loguru import logger
from rich import print

from .defaults import DEFAULT_COMPRESS
from .defaults import DEFAULT_COMPRESSION_LEVEL
from .defaults import DEFAULT_DEPTH
from .defaults import DEFAULT_FILENAME_FORMAT
from .defaults import DEFAULT_FORMAT
from .defaults import DEFAULT_VERBOSE_LEVEL
from .defaults import DEFAULT_WRITE_BEHAVIOR
from .defaults import MAX_COMMENT_LENGTH
from .defaults import MAX_VERBOSE_LEVEL
from .enums import Format
from .enums import WriteBehavior
from .enums import format_to_string
from .enums import write_behavior_to_int


def dcm2nii(
    in_folder: Path,
    out_folder: Path,
    *args: str,
    compress: bool = DEFAULT_COMPRESS,
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
    adjacent: bool = False,
    comment: str | None = None,
    depth: int = DEFAULT_DEPTH,
    export_format: Format = DEFAULT_FORMAT,
    filename_format: str = DEFAULT_FILENAME_FORMAT,
    ignore: bool = False,
    verbosity: int = DEFAULT_VERBOSE_LEVEL,
    write_behavior: WriteBehavior = DEFAULT_WRITE_BEHAVIOR,
    is_cli: bool = False,
) -> None:
    verbosity = min(verbosity, MAX_VERBOSE_LEVEL)
    command_lines = [
        f"  -a {_bool_to_yn(adjacent)} \\",
        f"  -d {depth} \\",
        f"  -e {format_to_string[export_format]} \\",
        f"  -f {filename_format} \\",
        f"  -i {_bool_to_yn(ignore)} \\",
        f"  -v {verbosity} \\",
        f"  -z {_bool_to_yn(compress)} \\",
        f"  -w {write_behavior_to_int[write_behavior]} \\",
    ]
    if compress and compression_level != DEFAULT_COMPRESSION_LEVEL:
        command_lines.append(f"  -{compression_level} \\")
    if comment is not None:
        length = len(comment)
        if length > MAX_COMMENT_LENGTH:
            msg = (
                f"Comment length ({length}) exceeds maximum of "
                f"{MAX_COMMENT_LENGTH} characters"
            )
            if is_cli:
                logger.error(msg)
                raise typer.Exit(1)
            else:
                raise ValueError(msg)
        command_lines.append(f'  -c "{comment}" \\')
    if out_folder is not None:
        out_folder = out_folder.resolve()
        out_folder.mkdir(parents=True, exist_ok=True)
        command_lines.append(f"  -o {out_folder} \\")
    if args:
        command_lines.append("  " + " \\\n  ".join(args))
    # The input must be at the end of the command
    command_lines.append(f"  {in_folder.resolve()} \\")

    _dcm2niix_with_logging(*command_lines)


def _bool_to_yn(value: bool) -> str:
    """Convert a boolean to 'y' or 'n'."""
    return "y" if value else "n"


def _dcm2niix_with_logging(*lines: str) -> None:
    loggerw = logger.bind(executable="dcm2niiw")
    loggerx = logger.bind(executable="dcm2niix")

    loggerw.debug("The following command will be run:")
    lines_str = "\n".join(lines).strip(" \\")
    loggerw.debug(f"{dcm2niix_path} \\\n  {lines_str}")
    args = chain.from_iterable([line.strip("  \\").split() for line in lines])

    dcm2niix(*args, logger=loggerx)


def dcm2niix(*args: str, logger: loguru.Logger | None = None) -> None:
    args_list = [arg.strip("\\\n") for arg in args]
    args_list = [arg for arg in args_list if arg]  # remove empty strings

    cmd = [dcm2niix_path] + args_list
    with Popen(cmd, stdout=PIPE, stderr=PIPE, text=True, bufsize=1) as p:
        assert p.stdout is not None
        assert p.stderr is not None

        for line in p.stdout:
            line = line.rstrip("\n")
            if logger is None:
                print(line)
                continue
            elif line.startswith("Warning: "):
                line = line.strip("Warning: ")
                log = logger.warning
            elif line.startswith("Conversion required"):
                log = logger.success
            elif line.startswith("Chris Rorden"):
                log = logger.debug
            else:
                log = logger.info
            log(line)
