from __future__ import annotations

import sys
from pathlib import Path

import typer
from loguru import logger
from typing_extensions import Annotated

from .defaults import DEFAULT_COMPRESS
from .defaults import DEFAULT_COMPRESSION_LEVEL
from .defaults import DEFAULT_DEPTH
from .defaults import DEFAULT_FILENAME_FORMAT
from .defaults import DEFAULT_FORMAT
from .defaults import DEFAULT_VERBOSE_LEVEL
from .defaults import DEFAULT_WRITE_BEHAVIOR
from .enums import Format
from .enums import LogLevel
from .enums import WriteBehavior
from .wrapper import dcm2nii
from .wrapper import dcm2niix

app = typer.Typer()


def help_callback(value: bool) -> None:
    if value:
        dcm2niix("-h")
        raise typer.Exit()


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
    out_folder: Annotated[
        Path,
        typer.Argument(
            dir_okay=True,
            file_okay=False,
            help="Output directory (omit to save to input folder)",
            rich_help_panel="Outputs",
        ),
    ],
    compress: Annotated[
        bool,
        typer.Option(),
    ] = DEFAULT_COMPRESS,
    compression_level: Annotated[
        int,
        typer.Option(
            min=1,
            max=9,
            help="Gunzip compression level (1=fastest..9=smallest)",
        ),
    ] = DEFAULT_COMPRESSION_LEVEL,
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
    ] = DEFAULT_DEPTH,
    export_format: Annotated[
        Format,
        typer.Option(
            "--export-format",
            "-e",
            case_sensitive=False,
            help="Output file format",
            rich_help_panel="Outputs",
        ),
    ] = DEFAULT_FORMAT,
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
    ] = DEFAULT_FILENAME_FORMAT,
    ignore: Annotated[
        bool,
        typer.Option(
            "--ignore/--no-ignore",
            "-i",
            help="Ignore derived, localizer and 2D images",
            rich_help_panel="Outputs",
        ),
    ] = False,
    write_behavior: Annotated[
        WriteBehavior,
        typer.Option(
            "--write-behavior",
            "-w",
            case_sensitive=False,
            help="Behavior when output file already exists.",
            rich_help_panel="Outputs",
        ),
    ] = DEFAULT_WRITE_BEHAVIOR,
    _: Annotated[
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
    ] = DEFAULT_VERBOSE_LEVEL,
    context: typer.Context = typer.Option(
        None,
        help="[Extra arguments to be added to the command]",
    ),
) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{extra[executable]}</level> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level.value,
        colorize=True,
    )
    dcm2nii(
        in_folder,
        out_folder,
        *context.args,
        compress=compress,
        compression_level=compression_level,
        adjacent=adjacent,
        comment=comment,
        depth=depth,
        export_format=export_format,
        filename_format=filename_format,
        ignore=ignore,
        verbosity=verbose,
        write_behavior=write_behavior,
        is_cli=True,
    )


if __name__ == "__main__":
    app()
