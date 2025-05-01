from __future__ import annotations

import enum
import shutil
import tempfile
from pathlib import Path
from subprocess import run

import typer
from loguru import logger
from typing_extensions import Annotated


app = typer.Typer()


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


_DEFAULT_COMPRESSION = 6
_DEFAULT_COMPRESS = False
_DEFAULT_DEPTH = 5
_DEFAULT_FORMAT = Format.nifti
_DEFAULT_FILENAME_FORMAT = "%f_%p_%t_%s"
_DEFAULT_VERBOSE_LEVEL = 0
_MAX_COMMENT_LENGTH = 24
_MAX_VERBOSE_LEVEL = 2


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
            help="Gunzip compression level (1=fastest..9=smallest, default 6)",
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
        ),
    ] = _DEFAULT_DEPTH,
    export_format: Annotated[
        Format,
        typer.Option(
            "--export-format",
            "-e",
            case_sensitive=False,
            help="Output file format",
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
        ),
    ] = _DEFAULT_FILENAME_FORMAT,
    ignore: Annotated[
        bool,
        typer.Option(
            "--ignore/--no-ignore",
            "-i",
            help="Ignore derived, localizer and 2D images",
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
        ),
    ] = None,
    out_file: Annotated[
        Path | None,
        typer.Option(
            dir_okay=False,
            file_okay=True,
            help="Output file path (sets depth to 0 and ignores out_folder)",
        ),
    ] = None,
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
        ),
    ] = _DEFAULT_VERBOSE_LEVEL,
    context: typer.Context = typer.Option(
        None,
        help="[Extra arguments to be added to the command]",
    ),
) -> None:
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
) -> None:
    if "-h" in args:
        _call_dcm2niix("-h")
        return
    verbosity = min(verbosity, _MAX_VERBOSE_LEVEL)
    if out_path is not None:
        depth = 0
        out_folder = Path(tempfile.mkdtemp())
    args_for_cli: list[str | Path | int | Format] = [
        "-a",
        _bool_to_yn(adjacent),
        "-d",
        str(depth),
        "-e",
        format_to_string[export_format],
        "-f",
        filename_format,
        "-i",
        _bool_to_yn(ignore),
        "-v",
        verbosity,
        "-z",
        _bool_to_yn(compress),
    ]
    if compress:
        args_for_cli.append(f"-{compression_level}")
    if comment is not None:
        length = len(comment)
        if length > _MAX_COMMENT_LENGTH:
            msg = (
                f"Comment length ({length}) exceeds maximum of "
                f"{_MAX_COMMENT_LENGTH} characters"
            )
            raise ValueError(msg)
        args_for_cli.extend(["-c", comment])
    if out_folder is not None:
        args_for_cli.extend(["-o", out_folder])
    args_for_cli.append(in_folder)
    args_for_cli += list(args)

    args_for_cli_str = [str(arg) for arg in args_for_cli]
    _call_dcm2niix(*args_for_cli_str)

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


def _call_dcm2niix(*args: str) -> None:
    from dcm2niix import bin as dcm2niix_path

    logger.debug("The following command will be run:")
    logger.debug(f"{Path(dcm2niix_path).name} {' '.join(args)}")
    output = run(
        [dcm2niix_path] + list(args),
        capture_output=True,
        text=True,
        check=True,
    )
    if output.returncode != 0:
        logger.error(f"dcm2niix failed with error code {output.returncode}")
        logger.error(output.stderr)
        raise RuntimeError(f"dcm2niix failed: {output.stderr}")
    for line in output.stdout.splitlines():
        if line.startswith("Warning: "):
            log = logger.warning
        else:
            log = logger.info
        log(line)
    logger.success("dcm2niix completed successfully")
