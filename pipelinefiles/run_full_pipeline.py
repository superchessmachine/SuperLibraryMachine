from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

try:  # pragma: no cover - import resolution depends on packaging context
    from .extract_doi import extract_dois
    from .upgraded_convertingtotxt import convert_pdfs
    from .chunker_updated import chunk_texts
    from .embed_chunks_multigpu import embed_chunks
    from .build_faiss_index import build_faiss_index
except ImportError:  # pragma: no cover - fallback for direct script execution
    from extract_doi import extract_dois
    from upgraded_convertingtotxt import convert_pdfs
    from chunker_updated import chunk_texts
    from embed_chunks_multigpu import embed_chunks
    from build_faiss_index import build_faiss_index


@dataclass(frozen=True)
class PipelinePaths:
    papers_dir: Path
    pdf_dir: Path
    txt_dir: Path
    metadata_file: Path
    chunks_file: Path
    embeddings_file: Path
    shard_dir: Path
    faiss_index: Path
    faiss_metadata: Path


def cleanup_mac_metadata(target_dir: Path, recursive: bool = True) -> int:
    patterns = ["._*", ".DS_Store"]
    removed = 0
    iterator = target_dir.rglob if recursive else target_dir.glob

    for pattern in patterns:
        for path in iterator(pattern):
            if path.is_file():
                path.unlink(missing_ok=True)
                removed += 1
    return removed


def organize_library(pdf_paths: list[Path], pdf_dir: Path) -> None:
    pdf_dir.mkdir(parents=True, exist_ok=True)
    for pdf_path in pdf_paths:
        if pdf_path.parent == pdf_dir:
            continue
        destination = pdf_dir / pdf_path.name
        if destination.exists():
            destination.unlink()
        pdf_path.rename(destination)


def resolve_paths(args: argparse.Namespace) -> PipelinePaths:
    papers_dir = args.papers_dir.resolve()

    pdf_dir = (args.pdf_dir or papers_dir / "pdf").resolve()
    txt_dir = (args.txt_dir or papers_dir / "txt").resolve()
    metadata_file = (args.metadata_file or papers_dir / "metadata.csv").resolve()
    chunks_file = (args.chunk_output or papers_dir / "chunksatleast500.jsonl").resolve()
    embeddings_file = (args.embedding_output or papers_dir / "embedded_chunks_atleast500.jsonl").resolve()
    shard_dir = (args.embedding_shard_dir or papers_dir / "output_shards").resolve()
    faiss_index = (args.faiss_index or papers_dir / "faiss_index.idx").resolve()
    faiss_metadata = (args.faiss_metadata or papers_dir / "faiss_metadata.pkl").resolve()

    txt_dir.mkdir(parents=True, exist_ok=True)
    shard_dir.mkdir(parents=True, exist_ok=True)

    return PipelinePaths(
        papers_dir=papers_dir,
        pdf_dir=pdf_dir,
        txt_dir=txt_dir,
        metadata_file=metadata_file,
        chunks_file=chunks_file,
        embeddings_file=embeddings_file,
        shard_dir=shard_dir,
        faiss_index=faiss_index,
        faiss_metadata=faiss_metadata,
    )


def run_pipeline(args: argparse.Namespace) -> None:
    paths = resolve_paths(args)

    print(f"🏁 Starting pipeline in {paths.papers_dir}")

    if not args.skip_cleanup:
        removed = cleanup_mac_metadata(paths.papers_dir, recursive=not args.cleanup_shallow)
        print(f"🧹 Removed {removed} macOS metadata files")

    processed_pdfs = convert_pdfs(
        input_dir=paths.papers_dir,
        output_dir=paths.txt_dir,
        recursive=args.recursive,
        max_workers=args.conversion_workers,
        overwrite=not args.conversion_no_overwrite,
    )

    if not args.skip_organize:
        organize_library(processed_pdfs, paths.pdf_dir)
        print(f"📦 Organized PDFs into {paths.pdf_dir}")

    extract_dois(
        txt_dir=paths.txt_dir,
        output_file=paths.metadata_file,
        encoding=args.metadata_encoding,
        include_rel_path=args.metadata_include_rel_path,
    )

    chunk_texts(
        txt_dir=paths.txt_dir,
        metadata_file=paths.metadata_file,
        output_file=paths.chunks_file,
        min_tokens=args.min_tokens,
        overlap=args.chunk_overlap,
        tokenizer_name=args.tokenizer,
        max_workers=args.chunk_workers,
    )

    embed_chunks(
        input_file=paths.chunks_file,
        output_dir=paths.shard_dir,
        final_output=paths.embeddings_file,
        model_name=args.embedding_model,
        batch_size=args.embedding_batch_size,
        num_workers=args.embedding_workers,
        device=args.embedding_device,
        normalize_embeddings=args.normalize_embeddings,
    )

    build_faiss_index(
        embedding_file=paths.embeddings_file,
        index_file=paths.faiss_index,
        metadata_file=paths.faiss_metadata,
        metric=args.faiss_metric,
    )

    print("✅ Pipeline complete!")


def _positive_int(value: str) -> Optional[int]:
    if value.lower() == "auto":
        return None
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer or 'auto'.")
    return ivalue


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the SuperLibraryMachine document ingestion pipeline end-to-end.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--papers-dir", type=Path, required=True, help="Directory containing source PDFs.")
    parser.add_argument("--recursive", action="store_true", help="Recursively search for PDFs inside --papers-dir.")

    parser.add_argument("--skip-cleanup", action="store_true", help="Skip removal of macOS metadata files.")
    parser.add_argument(
        "--cleanup-shallow",
        action="store_true",
        help="Only clean up metadata files in the top-level of --papers-dir.",
    )
    parser.add_argument("--skip-organize", action="store_true", help="Leave PDFs in place instead of moving to /pdf.")

    parser.add_argument("--pdf-dir", type=Path, help="Destination directory for original PDFs.")
    parser.add_argument("--txt-dir", type=Path, help="Destination directory for generated TXT files.")
    parser.add_argument("--metadata-file", type=Path, help="CSV metadata output path.")
    parser.add_argument("--chunk-output", type=Path, help="JSONL output path for text chunks.")
    parser.add_argument("--embedding-output", type=Path, help="JSONL output path for embedded chunks.")
    parser.add_argument("--embedding-shard-dir", type=Path, help="Directory for temporary embedding shards.")
    parser.add_argument("--faiss-index", type=Path, help="Output FAISS index path.")
    parser.add_argument("--faiss-metadata", type=Path, help="Output pickle metadata path.")

    parser.add_argument(
        "--conversion-workers",
        type=_positive_int,
        default=None,
        help="Max parallel workers for PDF→TXT conversion (auto = CPU count).",
    )
    parser.add_argument(
        "--conversion-no-overwrite",
        action="store_true",
        help="Skip PDFs that already have TXT files present.",
    )

    parser.add_argument("--metadata-encoding", default="utf-8", help="Encoding for TXT and metadata CSV files.")
    parser.add_argument(
        "--metadata-include-rel-path",
        action="store_true",
        help="Include relative TXT paths in metadata output.",
    )

    parser.add_argument("--min-tokens", type=int, default=500, help="Minimum tokens per chunk.")
    parser.add_argument("--chunk-overlap", type=int, default=1, help="Paragraph overlap between chunks.")
    parser.add_argument("--tokenizer", default="cl100k_base", help="tiktoken tokenizer name for chunking.")
    parser.add_argument(
        "--chunk-workers",
        type=_positive_int,
        default=None,
        help="Max parallel workers for chunking (auto = CPU count).",
    )

    parser.add_argument("--embedding-model", default="all-MiniLM-L6-v2", help="SentenceTransformer model to use.")
    parser.add_argument("--embedding-batch-size", type=int, default=2048, help="Batch size for embedding.")
    parser.add_argument(
        "--embedding-workers",
        type=int,
        default=4,
        help="Number of parallel embedding workers (GPU count or CPU processes).",
    )
    parser.add_argument(
        "--embedding-device",
        choices=["gpu", "cpu"],
        default="gpu",
        help="Device type to target for embeddings.",
    )
    parser.add_argument(
        "--normalize-embeddings",
        action="store_true",
        help="L2-normalize embeddings during encoding (recommended for cosine FAISS indices).",
    )

    parser.add_argument(
        "--faiss-metric",
        choices=["l2", "cosine"],
        default="l2",
        help="Similarity metric for the FAISS index.",
    )

    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    run_pipeline(args)


if __name__ == "__main__":
    main()
