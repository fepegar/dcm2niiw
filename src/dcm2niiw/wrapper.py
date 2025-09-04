from __future__ import annotations

from itertools import chain
from pathlib import Path
from subprocess import CompletedProcess
from subprocess import run

import typer
from loguru import logger

from .defaults import DEFAULT_COMPRESS
from .defaults import DEFAULT_COMPRESSION
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
    compression_level: int = DEFAULT_COMPRESSION,
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
    if compress:
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
        out_folder.mkdir(parents=True, exist_ok=True)
        command_lines.append(f"  -o {out_folder} \\")
    command_lines.append(f"  {in_folder} \\")
    if args:
        command_lines.append("  " + " \\\n  ".join(args))

    _dcm2niix_with_logging(*command_lines)


def _bool_to_yn(value: bool) -> str:
    """Convert a boolean to 'y' or 'n'."""
    return "y" if value else "n"


def _dcm2niix_with_logging(*lines: str) -> None:
    from dcm2niix import bin as dcm2niix_path

    logger.debug("The following command will be run:")
    lines_str = "\n".join(lines).strip(" \\")
    logger.debug(f"\n{dcm2niix_path} \\\n  {lines_str}")
    args = chain.from_iterable([line.strip("  \\").split() for line in lines])
    output = dcm2niix(*args)
    if output.returncode != 0:
        logger.error(f"dcm2niix failed with error code {output.returncode}")
        logger.error(output.stderr)

    for line in output.stdout.splitlines():
        if line.startswith("Warning: "):
            line = line.strip("Warning: ")
            log = logger.warning
        elif line.startswith("Conversion required"):
            log = logger.success
        elif line.startswith("Chris Rorden"):
            log = logger.debug
        else:
            log = logger.info
        log(line)


def dcm2niix(*args: str) -> CompletedProcess:
    from dcm2niix import bin as dcm2niix_path

    args_list = [arg.strip("\\\n") for arg in args]
    args_list = [arg for arg in args_list if arg]  # remove empty strings

    return run(
        [dcm2niix_path] + args_list,
        capture_output=True,
        text=True,
    )
