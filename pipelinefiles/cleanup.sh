#!/bin/bash

# cleanup.sh — Delete all macOS ._ files recursively

echo "🔍 Searching for Mac metadata files (._*)..."
count=$(find . -type f -name "._*" | wc -l)

if [ "$count" -eq 0 ]; then
    echo "✅ No ._ files found."
else
    echo "🗑️  Deleting $count ._ files..."
    find . -type f -name "._*" -delete
    echo "✅ Cleanup complete."
fi
