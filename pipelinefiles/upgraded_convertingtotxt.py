from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
from pathlib import Path
from typing import Iterable, Optional

from tqdm import tqdm

try:
    from unstructured.partition.pdf import partition_pdf
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    partition_pdf = None
    _PDF_IMPORT_ERROR = exc
else:  # pragma: no cover - trivial branch
    _PDF_IMPORT_ERROR = None


def _process_pdf(pdf_path: Path, output_dir: Path, overwrite: bool = True) -> Path:
    """Convert a single PDF into a TXT file using unstructured's partitioner."""
    if partition_pdf is None:  # pragma: no cover - runtime guard
        raise ModuleNotFoundError("unstructured.partition.pdf is required for PDF conversion") from _PDF_IMPORT_ERROR
    txt_path = output_dir / f"{pdf_path.stem}.txt"

    if txt_path.exists() and not overwrite:
        return pdf_path

    elements = partition_pdf(filename=str(pdf_path))

    output_dir.mkdir(parents=True, exist_ok=True)
    with txt_path.open("w", encoding="utf-8") as f:
        for el in elements:
            if el.text:
                f.write(el.text.strip() + "\n")

    return pdf_path


def convert_pdfs(
    input_dir: Path,
    output_dir: Optional[Path] = None,
    recursive: bool = False,
    max_workers: Optional[int] = None,
    overwrite: bool = True,
) -> list[Path]:
    """Convert all PDFs in *input_dir* to TXT files in *output_dir*.

    Parameters
    ----------
    input_dir:
        Directory containing PDFs.
    output_dir:
        Destination directory for TXT files. Defaults to *input_dir*.
    recursive:
        Whether to search for PDFs recursively.
    max_workers:
        Number of worker processes for parallel conversion. Defaults to `os.cpu_count()`.
    overwrite:
        If False, skip PDFs that already have a matching TXT file.

    Returns
    -------
    list[Path]
        The list of processed PDF paths.
    """

    input_dir = input_dir.resolve()
    output_dir = (output_dir or input_dir).resolve()

    pattern = "**/*.pdf" if recursive else "*.pdf"
    pdf_files = sorted(input_dir.glob(pattern))

    if not pdf_files:
        print("⚠️  No PDF files found. Skipping conversion.")
        return []

    print(f"🧾 Found {len(pdf_files)} PDFs to process in {input_dir}.")

    process_func = partial(_process_pdf, output_dir=output_dir, overwrite=overwrite)

    processed: list[Path] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_func, pdf): pdf for pdf in pdf_files}
        with tqdm(total=len(pdf_files), desc="📄 Processing PDFs", unit="file") as pbar:
            for future in as_completed(futures):
                pdf_path = futures[future]
                future.result()
                processed.append(pdf_path)
                pbar.update(1)

    print("✅ PDF to TXT conversion complete.")
    return processed


def _positive_int(value: str) -> Optional[int]:
    if value.lower() == "auto":
        return None
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer or 'auto'.")
    return ivalue


def parse_args(args: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert PDFs to TXT files in bulk.")
    parser.add_argument("input_dir", type=Path, help="Directory containing source PDF files.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Destination directory for generated TXT files. Defaults to the input directory.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search for PDFs inside the input directory.",
    )
    parser.add_argument(
        "--max-workers",
        type=_positive_int,
        default=None,
        help="Number of parallel workers (default: auto).",
    )
    parser.add_argument(
        "--no-overwrite",
        dest="overwrite",
        action="store_false",
        help="Skip conversion if the TXT file already exists.",
    )

    parser.set_defaults(overwrite=True)
    return parser.parse_args(args)


def main(cli_args: Optional[Iterable[str]] = None) -> list[Path]:
    args = parse_args(cli_args)
    return convert_pdfs(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        recursive=args.recursive,
        max_workers=args.max_workers,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
