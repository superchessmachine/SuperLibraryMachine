# SuperLibraryMachine
An easy to use pipeline for setting up retrieval augmented generation of scientific text.

## Web Interface

The repository now bundles a simple Flask web app that can answer questions over any
processed RAG database (i.e. a folder containing `faiss_index.idx` and
`faiss_metadata.pkl`). A sample database, `Paper_DB_Sample`, is provided under
`exampleDBs/` and is used by default.

1. Create and activate a virtual environment (recommended).
2. Install dependencies: `pip install --upgrade pip && pip install -r requirements-mac.txt` (tested on macOS
   13+/Apple Silicon and Intel).
3. Export your OpenAI API key: `export OPENAI_API_KEY=sk-...`.
4. (Optional) Point the app at a different database root:
   `export RAG_DB_ROOT=/path/to/your/databases`.
5. Start the server from the project root: `python web/app.py`.
6. Visit `http://localhost:7860`—the interface is open locally once the server starts.

If no databases are detected at startup, the UI will display guidance on where to place
them.

> ℹ️  On Apple Silicon Macs, if `sentence-transformers` does not pull in a compatible
> PyTorch wheel automatically, install it manually with
> `pip install torch --index-url https://download.pytorch.org/whl/cpu` before rerunning
> `pip install -r requirements-mac.txt`.

> ℹ️  `faiss-cpu` wheels ship per-architecture. If pip still complains that no matching
> distribution is found, upgrade pip inside the environment (`pip install --upgrade pip`)
> and retry.
