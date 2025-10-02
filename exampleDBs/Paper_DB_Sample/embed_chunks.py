import json
from sentence_transformers import SentenceTransformer

# Load model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Input/output paths
input_file = "chunksatleast500.jsonl"
output_file = "embedded_chunks_atleast500.jsonl"

# Embed and save
with open(input_file, "r", encoding="utf-8") as f_in, open(output_file, "w", encoding="utf-8") as f_out:
    for line in f_in:
        entry = json.loads(line)
        embedding = model.encode(entry["text"])
        entry["embedding"] = embedding.tolist()
        f_out.write(json.dumps(entry) + "\n")

print("✅ Embedding complete. Saved to embedded_chunks_atleast500.jsonl")
