import os
import re
import csv

TXT_DIR = "txt"  # directory with your .txt files
OUTPUT_FILE = "metadata.csv"

# Regular expression for DOI (crossref standard)
doi_regex = re.compile(r'\b10\.\d{4,9}/[^\s"<>]+', re.IGNORECASE)

def extract_doi_from_text(text):
    match = doi_regex.search(text)
    return match.group(0) if match else "not found"

def main():
    results = []

    for filename in os.listdir(TXT_DIR):
        if filename.endswith(".txt"):
            path = os.path.join(TXT_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

            doi = extract_doi_from_text(text)
            results.append((filename, doi))
            print(f"✅ {filename} → DOI: {doi}")

    # Write CSV output
    with open(OUTPUT_FILE, "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["filename", "doi"])
        writer.writerows(results)

    print(f"\n📝 Metadata saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
