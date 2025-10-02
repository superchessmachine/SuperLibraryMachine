import json
import faiss
import numpy as np
import pickle

EMBED_FILE = "embedded_chunks_atleast500.jsonl"
INDEX_FILE = "faiss_index.idx"
METADATA_FILE = "faiss_metadata.pkl"

embeddings = []
metadata = []

# Step 1: Load embeddings and metadata
with open(EMBED_FILE, "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        vector = np.array(item["embedding"], dtype=np.float32)
        embeddings.append(vector)

        metadata.append({
            "source_file": item["source_file"],
            "chunk_id": item["chunk_id"],
            "doi": item["doi"],
            "title": item["title"],
            "text": item["text"],
            "token_count": item.get("token_count", None)
        })

embeddings = np.stack(embeddings)

# Step 2: Build FAISS index
index = faiss.IndexFlatL2(embeddings.shape[1])  # Use L2 distance
index.add(embeddings)

# Step 3: Save index and metadata
faiss.write_index(index, INDEX_FILE)
with open(METADATA_FILE, "wb") as f:
    pickle.dump(metadata, f)

print(f"✅ FAISS index built and saved to {INDEX_FILE}")
print(f"📎 Metadata saved to {METADATA_FILE}")
