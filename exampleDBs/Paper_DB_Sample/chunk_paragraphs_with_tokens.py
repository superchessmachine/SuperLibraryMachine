import os
import json
import pandas as pd
import tiktoken
from unstructured.partition.text import partition_text
from unstructured.documents.elements import NarrativeText

# --- Config ---
TXT_DIR = "txt"
METADATA_FILE = "metadata.csv"
OUTPUT_FILE = "chunks.jsonl"
PARAGRAPHS_PER_CHUNK = 2
OVERLAP = 1
ENCODING_NAME = "cl100k_base"  # GPT-3.5/4 tokenizer

# --- Load tokenizer ---
enc = tiktoken.get_encoding(ENCODING_NAME)

# --- Load metadata ---
metadata_df = pd.read_csv(METADATA_FILE)
doi_map = dict(zip(metadata_df["filename"], metadata_df["doi"]))
title_map = dict(zip(metadata_df["filename"], metadata_df.get("title", ["unknown"] * len(metadata_df))))

# --- Chunking function ---
def group_paragraphs_by_count(paragraphs, count=2, overlap=1):
    chunks = []
    i = 0
    while i < len(paragraphs):
        chunk = paragraphs[i:i+count]
        if chunk:
            chunks.append(" ".join(chunk))
        i += count - overlap
    return chunks

# --- Text processing ---
def process_txt_file(filepath):
    elements = partition_text(filename=filepath)
    paragraphs = [el.text.strip() for el in elements if isinstance(el, NarrativeText) and el.text.strip()]
    return group_paragraphs_by_count(paragraphs, count=PARAGRAPHS_PER_CHUNK, overlap=OVERLAP)

# --- Main script ---
def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_file:
        for filename in os.listdir(TXT_DIR):
            if not filename.endswith(".txt"):
                continue
            file_path = os.path.join(TXT_DIR, filename)
            print(f"📄 Processing {filename}")
            try:
                chunks = process_txt_file(file_path)
            except Exception as e:
                print(f"❌ Error in {filename}: {e}")
                continue

            doi = doi_map.get(filename, "not found")
            title = title_map.get(filename, "unknown")

            for idx, chunk in enumerate(chunks):
                token_count = len(enc.encode(chunk))
                out_file.write(json.dumps({
                    "source_file": filename,
                    "chunk_id": idx,
                    "doi": doi,
                    "title": title,
                    "text": chunk,
                    "token_count": token_count
                }) + "\n")

    print(f"\n✅ Chunking complete. All data saved to `{OUTPUT_FILE}`")

if __name__ == "__main__":
    main()
