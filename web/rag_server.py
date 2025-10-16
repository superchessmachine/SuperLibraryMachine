import os
import json
import re
import time
from datetime import datetime
from pathlib import Path

import faiss
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
from openai import OpenAI

# guard against numpy 2.x until faiss exposes wheels that support it
_NUMPY_VERSION_PARTS = []
for raw_part in np.__version__.split(".")[:2]:
    match = re.match(r"(\d+)", raw_part)
    _NUMPY_VERSION_PARTS.append(int(match.group(1)) if match else 0)
while len(_NUMPY_VERSION_PARTS) < 2:
    _NUMPY_VERSION_PARTS.append(0)
if tuple(_NUMPY_VERSION_PARTS) >= (2, 0):
    raise RuntimeError(
        "SuperLibraryMachine currently requires numpy<2.0 because faiss-cpu depends on the private numpy._ARRAY_API symbol. "
        "Install with 'pip install \"numpy<2.0\"' before launching the app."
    )

# ----------------------------
# Configuration
# ----------------------------

REWRITE_MODEL = "gpt-4.1-nano-2025-04-14"
ANSWER_MODEL = "o3-2025-04-16"
EMBED_MODEL = "all-MiniLM-L6-v2"
TOP_K = 15

DEFAULT_DB_ROOT = (Path(__file__).resolve().parent.parent / "exampleDBs").resolve()
DB_BASE_PATH = Path(os.getenv("RAG_DB_ROOT", DEFAULT_DB_ROOT)).resolve()

_client = None
model = SentenceTransformer(EMBED_MODEL)

# ----------------------------
# Helper Functions
# ----------------------------

def reset_openai_client():
    """Clear the cached OpenAI client so new credentials take effect."""
    global _client
    _client = None


def _get_openai_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
        _client = OpenAI(api_key=api_key)
    return _client


def list_databases():
    if not DB_BASE_PATH.exists():
        return []
    return sorted(
        entry.name
        for entry in DB_BASE_PATH.iterdir()
        if entry.is_dir() and (entry / "faiss_index.idx").exists()
    )


def load_db(db_name):
    db_path = (DB_BASE_PATH / db_name).resolve()
    if DB_BASE_PATH not in db_path.parents and db_path != DB_BASE_PATH:
        raise ValueError(f"Invalid database name: {db_name}")
    index_path = db_path / "faiss_index.idx"
    metadata_path = db_path / "faiss_metadata.pkl"

    if not index_path.exists():
        raise FileNotFoundError(f"Database '{db_name}' does not contain faiss_index.idx")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Database '{db_name}' does not contain faiss_metadata.pkl")

    index = faiss.read_index(str(index_path))
    with open(metadata_path, "rb") as f:
        metadata = pickle.load(f)
    return index, metadata

def call_openai_chat(prompt, model, retries=3):
    for _ in range(retries):
        try:
            client = _get_openai_client()
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Retrying due to: {e}")
            time.sleep(2)
    return None

# ----------------------------
# RAG Pipeline
# ----------------------------

def run_rag(user_input, db_name):
    index, metadata = load_db(db_name)

    # Step 1: Rewrite
    rewrite_prompt = (
        "You are assisting with analytical research across any subject area. "
        "Given an initial query, produce a more precise and detailed version that highlights the key entities, relationships, "
        "methods, metrics, or timeframes that would lead to the most relevant evidence in a knowledge base. "
        "Keep the tone neutral, avoid assumptions, and do not answer the question—only rewrite it.\n\n"
        f"User query:\n{user_input}"
    )
    refined_prompt = call_openai_chat(rewrite_prompt, model=REWRITE_MODEL) or user_input

    # Step 2: Vector search
    query_vec = model.encode([refined_prompt])
    D, I = index.search(np.array(query_vec, dtype=np.float32), k=TOP_K)

    retrieved_chunks = []
    chunk_lookup = {}
    for rank, (idx, dist) in enumerate(zip(I[0], D[0])):
        if idx < 0: continue
        chunk = metadata[idx]
        citation = str(rank + 1)
        chunk_lookup[citation] = chunk
        retrieved_chunks.append(f"[{citation}] {chunk['text']}")

    # Step 3: Answer prompt
    context_block = "\n\n".join(retrieved_chunks)
    answer_prompt = (
        "You are an analytical assistant who must respond using only the supplied context.\n"
        "Deliver concise, well-structured reasoning and highlight implications or comparisons when helpful. "
        "Use bracketed citations like [1], [2, 5] to support your answer, and only cite chunks provided.\n\n"
        f"Context:\n{context_block}\n\n"
        f"User question: {refined_prompt}"
    )
    reply = call_openai_chat(answer_prompt, model=ANSWER_MODEL)

    if reply is None:
        return "❌ Error generating answer. Try again.", {}

    # Step 4: Extract citations safely
    cited = re.findall(r"\[(\d+(?:,\s*\d+)*)\]", reply)
    cited_numbers = set()
    for group in cited:
        for num in group.split(","):
            cited_numbers.add(num.strip())

    citation_dict = {}
    for num in cited_numbers:
        chunk = chunk_lookup.get(num)
        citation_dict[num] = chunk.get("doi", "N/A") if chunk else "N/A"

    # Step 5: Logging
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "input_query": user_input,
        "rewritten_query": refined_prompt,
        "retrieved_chunks": retrieved_chunks,
        "final_answer": reply,
        "citations": citation_dict
    }

    log_dir = Path(os.getenv("SLM_LOG_DIR", "logs")).expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    with (log_dir / f"log_{ts}.jsonl").open("w", encoding="utf-8") as f:
        f.write(json.dumps(log_data) + "\n")

    return reply, citation_dict
