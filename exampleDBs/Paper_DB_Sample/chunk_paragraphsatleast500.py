import os
import json
import pandas as pd
import tiktoken
from unstructured.partition.text import partition_text
from unstructured.documents.elements import NarrativeText

# --- Config ---
TXT_DIR = "txt"
METADATA_FILE = "metadata.csv"
OUTPUT_FILE = "chunksatleast500.jsonl"
MIN_TOKENS = 500
OVERLAP = 1
ENCODING_NAME = "cl100k_base"  # for GPT-3.5/4

# --- Load tokenizer ---
enc = tiktoken.get_encoding(ENCODING_NAME)

# --- Load metadata ---
metadata_df = pd.read_csv(METADATA_FILE)
doi_map = dict(zip(metadata_df["filename"], metadata_df["doi"]))
title_map = dict(zip(metadata_df["filename"], metadata_df.get("title", ["unknown"] * len(metadata_df))))

# --- Paragraph chunking ---
def group_paragraphs_by_min_tokens(paragraphs, min_tokens=500, overlap=1, tokenizer=None):
    chunks = []
    i = 0
    while i < len(paragraphs):
        chunk = []
        token_count = 0
        j = i

        while j < len(paragraphs):
            para = paragraphs[j]
            para_tokens = len(tokenizer.encode(para))
            token_count += para_tokens
            chunk.append(para)
            j += 1
            if token_count >= min_tokens:
                break

        if chunk:
            chunk_text = " ".join(chunk)
            actual_tokens = len(tokenizer.encode(chunk_text))
            chunks.append((chunk_text, actual_tokens))
        i += max(1, j - i - overlap)  # allow overlap

    return chunks

# --- File processing ---
def process_txt_file(filepath, tokenizer):
    elements = partition_text(filename=filepath)
    paragraphs = [el.text.strip() for el in elements if isinstance(el, NarrativeText) and el.text.strip()]
    return group_paragraphs_by_min_tokens(paragraphs, min_tokens=MIN_TOKENS, overlap=OVERLAP, tokenizer=tokenizer)

# --- Main script ---
def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_file:
        for filename in os.listdir(TXT_DIR):
            if not filename.endswith(".txt"):
                continue
            file_path = os.path.join(TXT_DIR, filename)
            print(f"📄 Processing {filename}")
            try:
                chunks = process_txt_file(file_path, tokenizer=enc)
            except Exception as e:
                print(f"❌ Error in {filename}: {e}")
                continue

            doi = doi_map.get(filename, "not found")
            title = title_map.get(filename, "unknown")

            for idx, (chunk, token_count) in enumerate(chunks):
                out_file.write(json.dumps({
                    "source_file": filename,
                    "chunk_id": idx,
                    "doi": doi,
                    "title": title,
                    "text": chunk,
                    "token_count": token_count
                }) + "\n")

    print(f"\n✅ Chunking complete. Output saved to `{OUTPUT_FILE}`")

if __name__ == "__main__":
    main()
