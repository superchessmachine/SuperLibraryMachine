from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

try:
    import tiktoken
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    tiktoken = None
    _TIKTOKEN_IMPORT_ERROR = exc
else:  # pragma: no cover - trivial branch
    _TIKTOKEN_IMPORT_ERROR = None

try:
    from unstructured.documents.elements import NarrativeText
    from unstructured.partition.text import partition_text
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    NarrativeText = None
    partition_text = None
    _UNSTRUCTURED_TEXT_IMPORT_ERROR = exc
else:  # pragma: no cover - trivial branch
    _UNSTRUCTURED_TEXT_IMPORT_ERROR = None


def group_paragraphs_by_min_tokens(
    paragraphs: list[str],
    *,
    min_tokens: int,
    overlap: int,
    tokenizer_name: str,
) -> list[tuple[str, int]]:
    if tiktoken is None:  # pragma: no cover - runtime guard
        raise ModuleNotFoundError("tiktoken is required for chunking") from _TIKTOKEN_IMPORT_ERROR
    enc = tiktoken.get_encoding(tokenizer_name)
    chunks: list[tuple[str, int]] = []
    i = 0
    while i < len(paragraphs):
        chunk: list[str] = []
        token_count = 0
        j = i
        while j < len(paragraphs):
            para = paragraphs[j]
            para_tokens = len(enc.encode(para))
            token_count += para_tokens
            chunk.append(para)
            j += 1
            if token_count >= min_tokens:
                break
        if chunk:
            chunk_text = " ".join(chunk)
            actual_tokens = len(enc.encode(chunk_text))
            chunks.append((chunk_text, actual_tokens))
        step = max(1, j - i - overlap)
        i += step
    return chunks


def _process_file(
    filename: str,
    txt_dir: Path,
    doi_map: dict[str, str],
    title_map: dict[str, str],
    min_tokens: int,
    overlap: int,
    tokenizer_name: str,
) -> list[dict[str, object]]:
    if partition_text is None or NarrativeText is None:  # pragma: no cover - runtime guard
        raise ModuleNotFoundError("unstructured partition_text is required for chunking") from _UNSTRUCTURED_TEXT_IMPORT_ERROR
    filepath = txt_dir / filename
    elements = partition_text(filename=str(filepath))
    paragraphs = [
        el.text.strip()
        for el in elements
        if isinstance(el, NarrativeText) and el.text and el.text.strip()
    ]
    chunks = group_paragraphs_by_min_tokens(
        paragraphs,
        min_tokens=min_tokens,
        overlap=overlap,
        tokenizer_name=tokenizer_name,
    )

    doi = doi_map.get(filename, "not found")
    title = title_map.get(filename, "unknown")

    return [
        {
            "source_file": filename,
            "chunk_id": idx,
            "doi": doi,
            "title": title,
            "text": chunk,
            "token_count": token_count,
        }
        for idx, (chunk, token_count) in enumerate(chunks)
    ]


def chunk_texts(
    txt_dir: Path,
    metadata_file: Path,
    output_file: Path,
    *,
    min_tokens: int,
    overlap: int,
    tokenizer_name: str,
    max_workers: Optional[int],
) -> None:
    if partition_text is None or NarrativeText is None:
        raise ModuleNotFoundError("unstructured partition_text is required for chunking") from _UNSTRUCTURED_TEXT_IMPORT_ERROR
    if tiktoken is None:
        raise ModuleNotFoundError("tiktoken is required for chunking") from _TIKTOKEN_IMPORT_ERROR
    txt_dir = txt_dir.resolve()
    metadata_file = metadata_file.resolve()
    output_file = output_file.resolve()

    metadata_df = pd.read_csv(metadata_file)
    doi_map = dict(zip(metadata_df["filename"], metadata_df["doi"]))
    title_map = dict(
        zip(
            metadata_df["filename"],
            metadata_df.get("title", ["unknown"] * len(metadata_df)),
        )
    )

    filenames = sorted([f.name for f in txt_dir.glob("*.txt") if f.is_file()])
    if not filenames:
        print("⚠️  No TXT files found to chunk.")
        return

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=max_workers) as executor, output_file.open(
        "w", encoding="utf-8"
    ) as out_file:
        futures = {
            executor.submit(
                _process_file,
                filename,
                txt_dir,
                doi_map,
                title_map,
                min_tokens,
                overlap,
                tokenizer_name,
            ): filename
            for filename in filenames
        }

        for future in as_completed(futures):
            filename = futures[future]
            try:
                results = future.result()
                for record in results:
                    out_file.write(json.dumps(record) + "\n")
                print(f"✅ {filename} processed with {len(results)} chunks")
            except Exception as exc:  # pragma: no cover - logging only
                print(f"❌ Failed to process {filename}: {exc}")

    print(f"\n✅ All files processed. Output saved to `{output_file}`")


def _positive_int(value: str) -> Optional[int]:
    if value.lower() == "auto":
        return None
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer or 'auto'.")
    return ivalue


def parse_args(args: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chunk TXT files into token-based segments.")
    parser.add_argument("txt_dir", type=Path, help="Directory containing TXT files to chunk.")
    parser.add_argument(
        "--metadata-file",
        type=Path,
        default=Path("metadata.csv"),
        help="CSV file with at least 'filename' and 'doi' columns (default: metadata.csv).",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("chunksatleast500.jsonl"),
        help="Destination JSONL for chunk output (default: chunksatleast500.jsonl).",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=500,
        help="Minimum tokens per chunk (default: 500).",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=1,
        help="Paragraph overlap when sliding chunks (default: 1).",
    )
    parser.add_argument(
        "--tokenizer",
        default="cl100k_base",
        help="tiktoken tokenizer name (default: cl100k_base).",
    )
    parser.add_argument(
        "--max-workers",
        type=_positive_int,
        default=None,
        help="Parallel workers for chunking (default: auto).",
    )
    return parser.parse_args(args)


def main(cli_args: Optional[Iterable[str]] = None) -> None:
    args = parse_args(cli_args)
    chunk_texts(
        txt_dir=args.txt_dir,
        metadata_file=args.metadata_file,
        output_file=args.output_file,
        min_tokens=args.min_tokens,
        overlap=args.overlap,
        tokenizer_name=args.tokenizer,
        max_workers=args.max_workers,
    )


if __name__ == "__main__":
    main()
