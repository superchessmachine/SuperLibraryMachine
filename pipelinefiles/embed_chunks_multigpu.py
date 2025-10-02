import os
import json
import math
import multiprocessing as mp
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# --- Config ---
INPUT_FILE = "chunksatleast500.jsonl"
OUTPUT_DIR = "output_shards"
FINAL_OUTPUT = "embedded_chunks_atleast500.jsonl"
NUM_GPUS = 4
BATCH_SIZE = 2048

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Load input ---
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    entries = [json.loads(line) for line in f]

# --- Split work across GPUs ---
def chunkify(lst, n):
    return [lst[i::n] for i in range(n)]

shards = chunkify(entries, NUM_GPUS)

# --- Worker ---
def embed_worker(gpu_id, entries_subset, shard_id):
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    model = SentenceTransformer("all-MiniLM-L6-v2")

    out_path = os.path.join(OUTPUT_DIR, f"shard_{shard_id}.jsonl")
    with open(out_path, "w", encoding="utf-8") as f_out:
        for i in tqdm(range(0, len(entries_subset), BATCH_SIZE), desc=f"GPU {gpu_id}", position=gpu_id):
            batch = entries_subset[i:i + BATCH_SIZE]
            texts = [e["text"] for e in batch]
            embeddings = model.encode(texts, device="cuda", convert_to_numpy=True)
            for entry, emb in zip(batch, embeddings):
                entry["embedding"] = emb.tolist()
                f_out.write(json.dumps(entry) + "\n")

# --- Start multiprocess embedding ---
if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    processes = []
    for i in range(NUM_GPUS):
        p = mp.Process(target=embed_worker, args=(i, shards[i], i))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    # --- Combine output shards ---
    with open(FINAL_OUTPUT, "w", encoding="utf-8") as f_out:
        for i in range(NUM_GPUS):
            shard_file = os.path.join(OUTPUT_DIR, f"shard_{i}.jsonl")
            with open(shard_file, "r", encoding="utf-8") as f_in:
                for line in f_in:
                    f_out.write(line)

    print(f"\n✅ All GPUs finished. Output written to `{FINAL_OUTPUT}`.")
