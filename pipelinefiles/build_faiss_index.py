from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    import faiss
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    faiss = None
    _FAISS_IMPORT_ERROR = exc
else:  # pragma: no cover - trivial branch
    _FAISS_IMPORT_ERROR = None

try:
    import numpy as np
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    np = None
    _NUMPY_IMPORT_ERROR = exc
else:  # pragma: no cover - trivial branch
    _NUMPY_IMPORT_ERROR = None


def build_faiss_index(
    embedding_file: Path,
    index_file: Path,
    metadata_file: Path,
    *,
    metric: str,
) -> tuple[Any, list[dict]]:
    if faiss is None or np is None:
        raise ModuleNotFoundError("faiss and numpy are required to build the index") from (
            _FAISS_IMPORT_ERROR or _NUMPY_IMPORT_ERROR
        )
    embedding_file = embedding_file.resolve()
    index_file = index_file.resolve()
    metadata_file = metadata_file.resolve()

    embeddings: list[Any] = []
    metadata: list[dict] = []

    with embedding_file.open("r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            vector = np.array(item["embedding"], dtype=np.float32)
            embeddings.append(vector)
            metadata.append(
                {
                    "source_file": item["source_file"],
                    "chunk_id": item["chunk_id"],
                    "doi": item["doi"],
                    "title": item["title"],
                    "text": item["text"],
                    "token_count": item.get("token_count"),
                }
            )

    if not embeddings:
        raise ValueError(f"No embeddings found in {embedding_file}")

    matrix = np.stack(embeddings)
    if metric == "cosine":
        faiss.normalize_L2(matrix)
        index = faiss.IndexFlatIP(matrix.shape[1])
    else:  # L2
        index = faiss.IndexFlatL2(matrix.shape[1])

    index.add(matrix)

    index_file.parent.mkdir(parents=True, exist_ok=True)
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_file))
    with metadata_file.open("wb") as f_out:
        pickle.dump(metadata, f_out)

    print(f"✅ FAISS index built and saved to {index_file}")
    print(f"📎 Metadata saved to {metadata_file}")
    return index, metadata


def parse_args(args: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a FAISS index from embedded chunks.")
    parser.add_argument(
        "--embedding-file",
        type=Path,
        default=Path("embedded_chunks_atleast500.jsonl"),
        help="JSONL file containing embeddings (default: embedded_chunks_atleast500.jsonl).",
    )
    parser.add_argument(
        "--index-file",
        type=Path,
        default=Path("faiss_index.idx"),
        help="Output FAISS index path (default: faiss_index.idx).",
    )
    parser.add_argument(
        "--metadata-file",
        type=Path,
        default=Path("faiss_metadata.pkl"),
        help="Pickle file to store metadata records (default: faiss_metadata.pkl).",
    )
    parser.add_argument(
        "--metric",
        choices=["l2", "cosine"],
        default="l2",
        help="Similarity metric to use for the index (default: l2).",
    )
    return parser.parse_args(args)


def main(cli_args: Optional[Iterable[str]] = None) -> None:
    args = parse_args(cli_args)
    build_faiss_index(
        embedding_file=args.embedding_file,
        index_file=args.index_file,
        metadata_file=args.metadata_file,
        metric=args.metric,
    )


if __name__ == "__main__":
    main()
