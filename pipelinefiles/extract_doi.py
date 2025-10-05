from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Iterable, Optional


DOI_REGEX = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)


def extract_doi_from_text(text: str) -> str:
    match = DOI_REGEX.search(text)
    return match.group(0) if match else "not found"


def extract_dois(
    txt_dir: Path,
    output_file: Path,
    encoding: str = "utf-8",
    include_rel_path: bool = False,
) -> list[dict[str, str]]:
    txt_dir = txt_dir.resolve()
    output_file = output_file.resolve()
    rows: list[dict[str, str]] = []

    if not txt_dir.exists():
        raise FileNotFoundError(f"TXT directory not found: {txt_dir}")

    txt_files = sorted(p for p in txt_dir.glob("*.txt") if p.is_file())
    if not txt_files:
        print("⚠️  No TXT files found; metadata CSV will be empty.")

    for path in txt_files:
        with path.open("r", encoding=encoding) as f:
            text = f.read()

        doi = extract_doi_from_text(text)
        rows.append(
            {
                "filename": path.name,
                "doi": doi,
                **({"relative_path": str(path.relative_to(txt_dir))} if include_rel_path else {}),
            }
        )
        print(f"✅ {path.name} → DOI: {doi}")

    fieldnames = ["filename", "doi"] + (["relative_path"] if include_rel_path else [])
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding=encoding) as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n📝 Metadata saved to {output_file}")
    return rows


def parse_args(args: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract DOIs from TXT files into a CSV metadata table.")
    parser.add_argument("txt_dir", type=Path, help="Directory containing *.txt files.")
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("metadata.csv"),
        help="Destination CSV file for metadata (default: metadata.csv).",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Text encoding for input and output files (default: utf-8).",
    )
    parser.add_argument(
        "--include-relative-path",
        action="store_true",
        help="Include the relative path of each TXT file in the metadata output.",
    )
    return parser.parse_args(args)


def main(cli_args: Optional[Iterable[str]] = None) -> list[dict[str, str]]:
    args = parse_args(cli_args)
    return extract_dois(
        txt_dir=args.txt_dir,
        output_file=args.output_file,
        encoding=args.encoding,
        include_rel_path=args.include_relative_path,
    )


if __name__ == "__main__":
    main()
