import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from unstructured.partition.pdf import partition_pdf

def process_pdf(filename):
    elements = partition_pdf(filename=filename)

    txt_filename = filename.replace(".pdf", ".txt")
    with open(txt_filename, "w", encoding="utf-8") as f:
        for el in elements:
            if el.text:
                f.write(el.text.strip() + "\n")
    return filename

if __name__ == "__main__":
    pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]

    print(f"🧾 Found {len(pdf_files)} PDFs to process.\n")

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(process_pdf, f): f for f in pdf_files}
        with tqdm(total=len(pdf_files), desc="📄 Processing PDFs", unit="file") as pbar:
            for future in as_completed(futures):
                future.result()
                pbar.update(1)

    print("✅ All PDFs processed.")
