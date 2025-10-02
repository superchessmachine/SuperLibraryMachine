#!/usr/bin/env bash
# run_pipeline.sh — end-to-end paper-processing pipeline
# Assumes all individual scripts are in the same directory.

set -euo pipefail           # stop on first error, catch unset vars
IFS=$'\n\t'

echo "🚀 Starting pipeline $(date)"

############################
# 1. Clean up AppleDouble files
############################
echo "🧹  Cleaning up ._ files…"
bash cleanup.sh

############################
# 2. Convert PDFs → TXT
############################
echo "📄 Converting PDFs to text…"
python upgraded_convertingtotxt.py

############################
# 3. Organize PDFs and TXTs
############################
echo "📁 Sorting files into pdf/ and txt/…"
bash librarian.sh

############################
# 4. Extract DOIs to metadata.csv
############################
echo "🔎 Extracting DOIs…"
python extract_doi.py

############################
# 5. Chunk text into ≥500-token blocks
############################
echo "✂️  Chunking text…"
python chunker_updated.py

############################
# 6. Embed chunks (multi-GPU)
############################
echo "⚙️  Embedding chunks on GPUs…"
python embed_chunks_multigpu.py

############################
# 7. Build FAISS index
############################
echo "📚 Building FAISS index…"
python build_faiss_index.py

echo "✅ Pipeline completed successfully $(date)"
