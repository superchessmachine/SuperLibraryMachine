import os
from unstructured.partition.pdf import partition_pdf

# Get all PDFs in current directory
for filename in os.listdir("."):
    if filename.endswith(".pdf"):
        print(f"Processing {filename}...")
        elements = partition_pdf(filename=filename)

        txt_filename = filename.replace(".pdf", ".txt")
        with open(txt_filename, "w", encoding="utf-8") as f:
            for el in elements:
                if el.text:
                    f.write(el.text.strip() + "\n")

print("✅ All PDFs processed.")
