#!/bin/bash

# organize.sh — Moves all .pdf files to pdf/ and .txt files to txt/

echo "📁 Creating directories..."
mkdir -p pdf
mkdir -p txt

echo "📦 Moving PDF files..."
mv *.pdf pdf/ 2>/dev/null

echo "📦 Moving TXT files..."
mv *.txt txt/ 2>/dev/null

echo "✅ Done organizing files."
