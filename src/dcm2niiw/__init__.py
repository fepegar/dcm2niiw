from __future__ import annotations

import enum
import shutil
import sys
import tempfile
from itertools import chain
from pathlib import Path
from subprocess import CompletedProcess, run

import typer
from loguru import logger
from rich import print
from typing_extensions import Annotated


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


_DEFAULT_COMPRESSION = 6
_DEFAULT_COMPRESS = True  # originally False
_DEFAULT_DEPTH = 5
_DEFAULT_FORMAT = Format.nifti
_DEFAULT_FILENAME_FORMAT = "%f_%p_%t_%s"
_DEFAULT_VERBOSE_LEVEL = 0
_DEFAULT_WRITE_BEHAVIOR = WriteBehavior.overwrite  # originally add suffix
_MAX_COMMENT_LENGTH = 24
_MAX_VERBOSE_LEVEL = 2


def help_callback(value: bool) -> None:
    if value:
        print(_dcm2niix("-h").stdout)
        raise typer.Exit()


app = typer.Typer()


@app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
def main(
    in_folder: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=True,
            file_okay=False,
        ),
    ],
    compress: Annotated[
        bool,
        typer.Option(),
    ] = _DEFAULT_COMPRESS,
    compression_level: Annotated[
        int,
        typer.Option(
            min=1,
            max=9,
            help="Gunzip compression level (1=fastest..9=smallest)",
        ),
    ] = _DEFAULT_COMPRESSION,
    adjacent: Annotated[
        bool,
        typer.Option(
            "--adjacent/--no-adjacent",
            "-a",
            help=(
                "Assume adjacent DICOMs (images from same series always in same folder)"
                " for faster conversion"
            ),
        ),
    ] = False,
    comment: Annotated[
        str | None,
        typer.Option(
            "--comment",
            "-c",
            help=(
                "Comment to store in NIfTI aux_file (up to 24 characters e.g. '-c VIP',"
                " empty to anonymize e.g. 0020,4000 e.g. '-c \"\"')"
            ),
        ),
    ] = None,
    depth: Annotated[
        int,
        typer.Option(
            "--depth",
            "-d",
            min=0,
            max=9,
            help="Directory search depth (convert DICOMs in sub-folders of in_folder?)",
            rich_help_panel="Inputs",
        ),
    ] = _DEFAULT_DEPTH,
    export_format: Annotated[
        Format,
        typer.Option(
            "--export-format",
            "-e",
            case_sensitive=False,
            help="Output file format",
            rich_help_panel="Outputs",
        ),
    ] = _DEFAULT_FORMAT,
    filename_format: Annotated[
        str,
        typer.Option(
            "--filename-format",
            "-f",
            help=(
                "Filename format (%a=antenna (coil) name, %b=basename, %c=comments,"
                " %d=description, %e=echo number, %f=folder name, %g=accession number,"
                " %i=ID of patient, %j=seriesInstanceUID, %k=studyInstanceUID,"
                " %m=manufacturer, %n=name of patient, %o=mediaObjectInstanceUID,"
                " %p=protocol, %r=instance number, %s=series number, %t=time,"
                " %u=acquisition number, %v=vendor, %x=study ID; %z=sequence name)"
            ),
            rich_help_panel="Outputs",
        ),
    ] = _DEFAULT_FILENAME_FORMAT,
    ignore: Annotated[
        bool,
        typer.Option(
            "--ignore/--no-ignore",
            "-i",
            help="Ignore derived, localizer and 2D images",
            rich_help_panel="Outputs",
        ),
    ] = False,
    out_folder: Annotated[
        Path | None,
        typer.Option(
            "--out-folder",
            "-o",
            dir_okay=True,
            file_okay=False,
            help="Output directory (omit to save to input folder)",
            rich_help_panel="Outputs",
        ),
    ] = None,
    out_file: Annotated[
        Path | None,
        typer.Option(
            dir_okay=False,
            file_okay=True,
            help="Output file path (sets depth to 0 and ignores out_folder)",
            rich_help_panel="Outputs",
        ),
    ] = None,
    write_behavior: Annotated[
        WriteBehavior,
        typer.Option(
            "--write-behavior",
            "-w",
            case_sensitive=False,
            help="Behavior when output file already exists.",
            rich_help_panel="Outputs",
        ),
    ] = _DEFAULT_WRITE_BEHAVIOR,
    print_help: Annotated[
        bool,
        typer.Option(
            "--print-help",
            "-h",
            is_eager=True,
            callback=help_callback,
            help="Print dcm2niix help message and exit.",
        ),
    ] = False,
    log_level: Annotated[
        LogLevel,
        typer.Option(
            "--log",
            case_sensitive=False,
            help="Set the log level",
            rich_help_panel="Logging",
        ),
    ] = LogLevel.DEBUG,
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help=("Verbosity level. Use up to three times to increase verbosity."),
            rich_help_panel="Logging",
        ),
    ] = _DEFAULT_VERBOSE_LEVEL,
    context: typer.Context = typer.Option(
        None,
        help="[Extra arguments to be added to the command]",
    ),
) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level.value,
        colorize=True,
    )
    dcm2niix(
        in_folder,
        *context.args,
        compress=compress,
        compression_level=compression_level,
        adjacent=adjacent,
        comment=comment,
        depth=depth,
        export_format=export_format,
        filename_format=filename_format,
        ignore=ignore,
        out_folder=out_folder,
        verbosity=verbose,
        out_path=out_file,
        write_behavior=write_behavior,
    )


def dcm2niix(
    in_folder: Path,
    *args: str,
    compress: bool = _DEFAULT_COMPRESS,
    compression_level: int = _DEFAULT_COMPRESSION,
    adjacent: bool = False,
    comment: str | None = None,
    depth: int = _DEFAULT_DEPTH,
    export_format: Format = _DEFAULT_FORMAT,
    filename_format: str = _DEFAULT_FILENAME_FORMAT,
    ignore: bool = False,
    out_folder: Path | None = None,
    verbosity: int = _DEFAULT_VERBOSE_LEVEL,
    out_path: Path | None = None,
    write_behavior: WriteBehavior = _DEFAULT_WRITE_BEHAVIOR,
) -> None:
    if "-h" in args:
        _call_dcm2niix("-h")
        return
    verbosity = min(verbosity, _MAX_VERBOSE_LEVEL)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        depth = 0
        out_folder = Path(tempfile.mkdtemp())
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
        if length > _MAX_COMMENT_LENGTH:
            msg = (
                f"Comment length ({length}) exceeds maximum of "
                f"{_MAX_COMMENT_LENGTH} characters"
            )
            raise ValueError(msg)
        command_lines.append(f'  -c "{comment}" \\')
    if out_folder is not None:
        out_folder.mkdir(parents=True, exist_ok=True)
        command_lines.append(f"  -o {out_folder} \\")
    command_lines.append(f"  {in_folder} \\")
    if args:
        command_lines.append("  " + " \\\n  ".join(args))

    _call_dcm2niix(*command_lines)

    if out_path is not None:
        assert out_folder is not None
        out_paths = list(out_folder.iterdir())
        out_paths = [p for p in out_paths if p.suffix != ".json"]
        if len(out_paths) > 1:
            msg = (
                "More than one output file found. Output file not written. The"
                f' temporary directory "{out_folder}" will not be deleted'  # type: ignore
            )
            logger.warning(msg)
            return

        shutil.move(
            out_paths[0],
            out_path,
        )
        shutil.rmtree(out_folder)


def _bool_to_yn(value: bool) -> str:
    """Convert a boolean to 'y' or 'n'."""
    return "y" if value else "n"


def _call_dcm2niix(*lines: str) -> None:
    from dcm2niix import bin as dcm2niix_path

    logger.debug("The following command will be run:")
    lines_str = "\n".join(lines).strip(" \\")
    logger.debug(f"\n{dcm2niix_path} \\\n  {lines_str}")
    args = chain.from_iterable([line.strip("  \\").split() for line in lines])
    output = _dcm2niix(*args)
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


def _dcm2niix(*args: str) -> CompletedProcess:
    from dcm2niix import bin as dcm2niix_path

    return run(
        [dcm2niix_path] + list(args),
        capture_output=True,
        text=True,
    )
