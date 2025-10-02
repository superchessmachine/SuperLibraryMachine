import os
import json
import pandas as pd
import tiktoken
from concurrent.futures import ProcessPoolExecutor, as_completed
from unstructured.partition.text import partition_text
from unstructured.documents.elements import NarrativeText

# --- Config ---
TXT_DIR = "txt"
METADATA_FILE = "metadata.csv"
OUTPUT_FILE = "chunksatleast500.jsonl"
MIN_TOKENS = 500
OVERLAP = 1
ENCODING_NAME = "cl100k_base"
MAX_WORKERS = 88  # adjust based on CPU cores

# --- Load metadata ---
metadata_df = pd.read_csv(METADATA_FILE)
doi_map = dict(zip(metadata_df["filename"], metadata_df["doi"]))
title_map = dict(zip(metadata_df["filename"], metadata_df.get("title", ["unknown"] * len(metadata_df))))

# --- Paragraph chunking ---
def group_paragraphs_by_min_tokens(paragraphs, min_tokens=500, overlap=1, tokenizer_name="cl100k_base"):
    enc = tiktoken.get_encoding(tokenizer_name)
    chunks = []
    i = 0
    while i < len(paragraphs):
        chunk = []
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
        i += max(1, j - i - overlap)
    return chunks

# --- File processing ---
def process_file(filename):
    filepath = os.path.join(TXT_DIR, filename)
    try:
        elements = partition_text(filename=filepath)
        paragraphs = [el.text.strip() for el in elements if isinstance(el, NarrativeText) and el.text.strip()]
        chunks = group_paragraphs_by_min_tokens(paragraphs, min_tokens=MIN_TOKENS, overlap=OVERLAP)

        doi = doi_map.get(filename, "not found")
        title = title_map.get(filename, "unknown")

        results = []
        for idx, (chunk, token_count) in enumerate(chunks):
            results.append({
                "source_file": filename,
                "chunk_id": idx,
                "doi": doi,
                "title": title,
                "text": chunk,
                "token_count": token_count
            })
        return results
    except Exception as e:
        print(f"❌ Error in {filename}: {e}")
        return []

# --- Main ---
def main():
    filenames = [f for f in os.listdir(TXT_DIR) if f.endswith(".txt")]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor, open(OUTPUT_FILE, "w", encoding="utf-8") as out_file:
        futures = {executor.submit(process_file, filename): filename for filename in filenames}
        for future in as_completed(futures):
            filename = futures[future]
            try:
                results = future.result()
                for record in results:
                    out_file.write(json.dumps(record) + "\n")
                print(f"✅ {filename} processed with {len(results)} chunks")
            except Exception as e:
                print(f"❌ Failed to process {filename}: {e}")
    print(f"\n✅ All files processed. Output saved to `{OUTPUT_FILE}`")

if __name__ == "__main__":
    main()
