import json
import multiprocessing as mp
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import Annotated

import pydicom
import typer
from tqdm.auto import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed


def read_dicom(path: Path, **kwargs) -> pydicom.Dataset:
    try:
        return pydicom.dcmread(path, stop_before_pixels=True, **kwargs)
    except Exception as e:
        msg = f'Failed to read DICOM file "{path}"'
        raise RuntimeError(msg) from e


def header_to_dict(header: pydicom.Dataset) -> dict[str, Any]:
    return header.to_json_dict()


def get_series_id(header: pydicom.Dataset) -> str:
    return header.get("SeriesInstanceUID", "")


def _read_series_header(
    path: str, kwargs: dict[str, Any]
) -> tuple[str, pydicom.Dataset]:
    """Helper executed in a worker process."""
    header = read_dicom(Path(path), **kwargs)
    return get_series_id(header), header


def read_dicom_headers(paths: Iterable[Path], **kwargs) -> list[pydicom.Dataset]:
    headers = []
    for path in paths:
        try:
            header = read_dicom(path, **kwargs)
            headers.append(header)
        except Exception as e:
            print(f"Error reading {path}: {e}")
    return headers


def get_series_id_to_filenames(paths: list[Path], **kwargs) -> dict[str, list[Path]]:
    series_dict = {}
    for path in paths:
        header = read_dicom(path, **kwargs)
        series_id = get_series_id(header)
        if series_id not in series_dict:
            series_dict[series_id] = []
        series_dict[series_id].append(path)
    return series_dict


def get_series_id_to_headers(
    paths: list[Path],
    *,
    sort: bool = True,
    progress: bool = False,
    parallel: bool = False,
    **kwargs,
) -> dict[str, list[pydicom.Dataset]]:
    series_dict: dict[str, list[pydicom.Dataset]] = {}

    if not parallel:
        for path in tqdm(paths, disable=not progress, leave=False):
            header = read_dicom(path, **kwargs)
            series_id = get_series_id(header)
            if series_id not in series_dict:
                series_dict[series_id] = []
            series_dict[series_id].append(header)
    else:
        # Use all available CPUs except one (leave one for the main process / system)
        workers = max(1, mp.cpu_count() - 1)
        # Prepare immutable kwargs once to avoid repeated pickling cost
        shared_kwargs: dict[str, Any] = dict(kwargs)
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_read_series_header, str(path), shared_kwargs)
                for path in paths
            ]
            for fut in tqdm(
                as_completed(futures),
                total=len(futures),
                disable=not progress,
                leave=False,
            ):
                series_id, header = fut.result()  # propagate exceptions directly
                if series_id not in series_dict:
                    series_dict[series_id] = []
                series_dict[series_id].append(header)

    if sort:
        for series_id, headers in series_dict.items():
            series_dict[series_id] = sort_headers_by_instance_number(headers)

    return series_dict


def sort_headers_by_instance_number(
    headers: list[pydicom.Dataset],
) -> list[pydicom.Dataset]:
    return sorted(headers, key=lambda h: h.get("InstanceNumber", 0))


def get_series_id_to_first_header(
    paths: list[Path],
    *,
    as_dict: bool = False,
    progress: bool = False,
    parallel: bool = False,
    **kwargs,
) -> dict[str, pydicom.Dataset | dict[str, Any]]:
    series_id_to_headers = get_series_id_to_headers(
        paths,
        sort=True,
        progress=progress,
        parallel=parallel,
        **kwargs,
    )
    return {
        series_id: headers[0].to_json_dict() if as_dict else headers[0]
        for series_id, headers in series_id_to_headers.items()
        if headers
    }


def write_series_headers_json(
    dicom_dir: Path,
    output_path: Path,
    pattern: str = "*",
    progress: bool = True,
    parallel: bool = True,
    **kwargs,
):
    paths = sorted(dicom_dir.rglob(pattern))
    series_id_to_first_header_dict = get_series_id_to_first_header(
        paths,
        as_dict=True,
        progress=progress,
        parallel=parallel,
        **kwargs,
    )
    with Path(output_path).open("w") as f:
        json.dump(series_id_to_first_header_dict, f, indent=2, ensure_ascii=False)


app = typer.Typer()


@app.command()
def main(
    dicom_dir: Annotated[
        Path,
        typer.Argument(
            ...,
            exists=True,
            dir_okay=True,
            file_okay=False,
            help="Directory containing DICOM files",
        ),
    ],
    output_path: Annotated[
        Path,
        typer.Argument(
            ...,
            dir_okay=False,
            file_okay=True,
            help="Output JSON file path for series headers",
        ),
    ],
    pattern: Annotated[
        str,
        typer.Option(
            "--pattern",
            "-p",
            help="Glob pattern to match DICOM files within the directory.",
            show_default=True,
        ),
    ] = "*",
    progress: Annotated[
        bool,
        typer.Option(
            help="Show a progress bar while reading DICOM headers.",
            show_default=True,
        ),
    ] = True,
    parallel: Annotated[
        bool,
        typer.Option(
            help="Read DICOM headers in parallel using multiple processes.",
        ),
    ] = True,
):
    write_series_headers_json(
        dicom_dir,
        output_path,
        pattern=pattern,
        progress=progress,
        parallel=parallel,
    )
