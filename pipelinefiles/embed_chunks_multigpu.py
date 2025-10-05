from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
from pathlib import Path
from typing import Iterable, Optional

try:
    import numpy as np
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    np = None
    _NUMPY_IMPORT_ERROR = exc
else:  # pragma: no cover - trivial branch
    _NUMPY_IMPORT_ERROR = None

try:
    from sentence_transformers import SentenceTransformer
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    SentenceTransformer = None
    _SENTENCE_TRANSFORMERS_IMPORT_ERROR = exc
else:  # pragma: no cover - trivial branch
    _SENTENCE_TRANSFORMERS_IMPORT_ERROR = None

from tqdm import tqdm


def _load_entries(input_file: Path) -> list[dict]:
    with input_file.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _chunkify(lst: list, chunks: int) -> list[list]:
    if chunks <= 0:
        raise ValueError("chunks must be a positive integer")
    return [lst[i::chunks] for i in range(chunks)]


def _embed_worker(
    worker_rank: int,
    entries_subset: list[dict],
    shard_path: Path,
    model_name: str,
    batch_size: int,
    device_type: str,
    normalize: bool,
) -> None:
    if SentenceTransformer is None or np is None:  # pragma: no cover - runtime guard
        raise ModuleNotFoundError("sentence-transformers and numpy are required for embedding")
    if device_type == "gpu":
        os.environ["CUDA_VISIBLE_DEVICES"] = str(worker_rank)
        device = "cuda"
    else:
        device = "cpu"

    model = SentenceTransformer(model_name, device=device)

    shard_path.parent.mkdir(parents=True, exist_ok=True)
    with shard_path.open("w", encoding="utf-8") as f_out:
        for start in tqdm(
            range(0, len(entries_subset), batch_size),
            desc=f"worker {worker_rank}",
            position=worker_rank,
        ):
            batch = entries_subset[start : start + batch_size]
            texts = [entry["text"] for entry in batch]
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                device=device,
                convert_to_numpy=True,
                normalize_embeddings=normalize,
                show_progress_bar=False,
            )
            if not isinstance(embeddings, np.ndarray):
                embeddings = np.asarray(embeddings)
            for entry, emb in zip(batch, embeddings):
                entry["embedding"] = emb.astype(float).tolist()
                f_out.write(json.dumps(entry) + "\n")


def embed_chunks(
    input_file: Path,
    output_dir: Path,
    final_output: Path,
    *,
    model_name: str,
    batch_size: int,
    num_workers: int,
    device: str,
    normalize_embeddings: bool,
) -> None:
    if SentenceTransformer is None or np is None:
        raise ModuleNotFoundError("sentence-transformers and numpy are required for embedding") from (
            _SENTENCE_TRANSFORMERS_IMPORT_ERROR or _NUMPY_IMPORT_ERROR
        )
    input_file = input_file.resolve()
    output_dir = output_dir.resolve()
    final_output = final_output.resolve()

    entries = _load_entries(input_file)
    if not entries:
        print("⚠️  No entries found to embed.")
        final_output.write_text("", encoding="utf-8")
        return

    if device == "gpu":
        try:
            import torch

            available = torch.cuda.device_count()
        except Exception:  # pragma: no cover - optional dependency
            available = 0
        if available == 0:
            print("⚠️  No GPUs detected; falling back to CPU.")
            device = "cpu"
        else:
            num_workers = min(num_workers, available, len(entries))
    if device == "cpu":
        num_workers = 1 if num_workers is None else max(1, min(num_workers, len(entries)))

    if num_workers <= 0:
        num_workers = 1

    shards = _chunkify(entries, num_workers)

    mp.set_start_method("spawn", force=True)
    processes: list[mp.Process] = []
    for rank, shard in enumerate(shards):
        shard_path = output_dir / f"shard_{rank}.jsonl"
        process = mp.Process(
            target=_embed_worker,
            args=(rank, shard, shard_path, model_name, batch_size, device, normalize_embeddings),
        )
        process.start()
        processes.append(process)

    for process in processes:
        process.join()

    with final_output.open("w", encoding="utf-8") as f_out:
        for rank in range(len(shards)):
            shard_file = output_dir / f"shard_{rank}.jsonl"
            if shard_file.exists():
                with shard_file.open("r", encoding="utf-8") as f_in:
                    for line in f_in:
                        f_out.write(line)

    print(f"\n✅ Embeddings written to `{final_output}`.")


def parse_args(args: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed chunked text with SentenceTransformers.")
    parser.add_argument(
        "--input-file",
        type=Path,
        default=Path("chunksatleast500.jsonl"),
        help="JSONL file containing chunks to embed (default: chunksatleast500.jsonl).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output_shards"),
        help="Temporary directory for shard outputs (default: output_shards).",
    )
    parser.add_argument(
        "--final-output",
        type=Path,
        default=Path("embedded_chunks_atleast500.jsonl"),
        help="Final JSONL file containing embedded chunks (default: embedded_chunks_atleast500.jsonl).",
    )
    parser.add_argument(
        "--model-name",
        default="all-MiniLM-L6-v2",
        help="SentenceTransformer model name (default: all-MiniLM-L6-v2).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2048,
        help="Batch size for embedding (default: 2048).",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=4,
        help="Number of parallel worker processes (default: 4).",
    )
    parser.add_argument(
        "--device",
        choices=["gpu", "cpu"],
        default="gpu",
        help="Device type to target (default: gpu).",
    )
    parser.add_argument(
        "--normalize-embeddings",
        action="store_true",
        help="L2-normalize embeddings during encoding (useful for cosine similarity).",
    )
    return parser.parse_args(args)


def main(cli_args: Optional[Iterable[str]] = None) -> None:
    args = parse_args(cli_args)
    embed_chunks(
        input_file=args.input_file,
        output_dir=args.output_dir,
        final_output=args.final_output,
        model_name=args.model_name,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        device=args.device,
        normalize_embeddings=args.normalize_embeddings,
    )


if __name__ == "__main__":
    main()
