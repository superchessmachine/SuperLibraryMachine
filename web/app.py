import json
import os
import re
import shutil
import sys
import threading
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path

from flask import Flask, jsonify, render_template, request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
PIPELINE_ROOT = PROJECT_ROOT / "pipelinefiles"
if PIPELINE_ROOT.exists() and str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipelinefiles.run_full_pipeline import parse_args as parse_pipeline_args, run_pipeline

try:  # pragma: no cover - package-relative import for bundled app
    from .rag_server import DB_BASE_PATH, list_databases, reset_openai_client, run_rag
except ImportError:  # pragma: no cover - fallback for running as a script
    from rag_server import DB_BASE_PATH, list_databases, reset_openai_client, run_rag

app = Flask(__name__)

VALID_DB_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
BUILD_LOCK = threading.Lock()
CONFIG_PATH_ENV = os.getenv("SLM_CONFIG_PATH")
CONFIG_PATH = Path(CONFIG_PATH_ENV).expanduser() if CONFIG_PATH_ENV else None


def _normalize_path(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _persist_api_key_to_config(api_key: str | None) -> bool:
    if CONFIG_PATH is None:
        return False
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text())
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}
        if api_key:
            data["openai_api_key"] = api_key
        else:
            data.pop("openai_api_key", None)
        CONFIG_PATH.write_text(json.dumps(data, indent=2))
        return True
    except Exception as exc:  # pragma: no cover - persistence is best-effort
        print(f"Warning: unable to persist API key: {exc}")
        return False


@app.get("/api/databases")
def api_databases():
    return jsonify({"databases": list_databases(), "db_root": str(DB_BASE_PATH)})


@app.post("/settings/api-key")
def update_api_key():
    payload = request.get_json(silent=True) or {}
    api_key_raw = payload.get("apiKey")
    api_key = api_key_raw.strip() if isinstance(api_key_raw, str) else None

    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        reset_openai_client()
        persisted = _persist_api_key_to_config(api_key)
        message = "API key saved for this session."
        if persisted:
            message = "API key saved."
        return jsonify({"ok": True, "message": message, "persisted": persisted})

    os.environ.pop("OPENAI_API_KEY", None)
    reset_openai_client()
    persisted = _persist_api_key_to_config(None)
    message = "API key cleared."
    if persisted:
        message = "API key cleared and removed from storage."
    return jsonify({"ok": True, "message": message, "persisted": persisted})


@app.post("/build")
def build_database():
    payload = request.get_json(silent=True) or {}
    db_name = _normalize_path(payload.get("dbName"))
    papers_dir_raw = _normalize_path(payload.get("papersDir"))
    options = payload.get("options") or {}

    if not db_name:
        return jsonify({"ok": False, "error": "Database name is required."}), 400
    if not VALID_DB_NAME.match(db_name):
        return jsonify({"ok": False, "error": "Database name may only contain letters, numbers, '.', '_', and '-'."}), 400
    if not papers_dir_raw:
        return jsonify({"ok": False, "error": "Path to the papers directory is required."}), 400

    try:
        papers_dir = Path(papers_dir_raw).expanduser().resolve(strict=True)
    except FileNotFoundError:
        return jsonify({"ok": False, "error": f"Papers directory '{papers_dir_raw}' does not exist."}), 400
    if not papers_dir.is_dir():
        return jsonify({"ok": False, "error": f"Papers directory '{papers_dir}' is not a directory."}), 400

    recursive = bool(options.get("recursive"))
    pdf_iter = papers_dir.rglob("*.pdf") if recursive else papers_dir.glob("*.pdf")
    if next(pdf_iter, None) is None:
        return jsonify({"ok": False, "error": f"No PDF files found in '{papers_dir}'."}), 400

    target_dir = (DB_BASE_PATH / db_name).resolve()
    try:
        target_dir.relative_to(DB_BASE_PATH.resolve())
    except ValueError:
        # Should not happen, but guard against path traversal.
        return jsonify({"ok": False, "error": "Invalid database path requested."}), 400

    if target_dir.exists():
        return jsonify({"ok": False, "error": f"Database '{db_name}' already exists."}), 409

    DB_BASE_PATH.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=False)
    created_dir = True

    defaults = {
        "pdfDir": str(target_dir / "pdf"),
        "txtDir": str(target_dir / "txt"),
        "metadataFile": str(target_dir / "metadata.csv"),
        "chunkOutput": str(target_dir / "chunksatleast500.jsonl"),
        "embeddingOutput": str(target_dir / "embedded_chunks_atleast500.jsonl"),
        "embeddingShardDir": str(target_dir / "output_shards"),
        "faissIndex": str(target_dir / "faiss_index.idx"),
        "faissMetadata": str(target_dir / "faiss_metadata.pkl"),
    }

    boolean_flags = {
        "recursive": "--recursive",
        "skipCleanup": "--skip-cleanup",
        "cleanupShallow": "--cleanup-shallow",
        "skipOrganize": "--skip-organize",
        "conversionNoOverwrite": "--conversion-no-overwrite",
        "metadataIncludeRelPath": "--metadata-include-rel-path",
        "normalizeEmbeddings": "--normalize-embeddings",
    }

    value_flags = {
        "pdfDir": "--pdf-dir",
        "txtDir": "--txt-dir",
        "metadataFile": "--metadata-file",
        "chunkOutput": "--chunk-output",
        "embeddingOutput": "--embedding-output",
        "embeddingShardDir": "--embedding-shard-dir",
        "faissIndex": "--faiss-index",
        "faissMetadata": "--faiss-metadata",
        "conversionWorkers": "--conversion-workers",
        "metadataEncoding": "--metadata-encoding",
        "minTokens": "--min-tokens",
        "chunkOverlap": "--chunk-overlap",
        "tokenizer": "--tokenizer",
        "chunkWorkers": "--chunk-workers",
        "embeddingModel": "--embedding-model",
        "embeddingBatchSize": "--embedding-batch-size",
        "embeddingWorkers": "--embedding-workers",
        "embeddingDevice": "--embedding-device",
        "faissMetric": "--faiss-metric",
    }

    args_list = ["--papers-dir", str(papers_dir)]
    # Default skip-organize to True unless explicitly disabled.
    skip_organize = options.get("skipOrganize")
    if skip_organize is None:
        options["skipOrganize"] = True

    for opt_key, flag in boolean_flags.items():
        if options.get(opt_key):
            args_list.append(flag)

    for opt_key, flag in value_flags.items():
        raw_value = options.get(opt_key)
        normalized = _normalize_path(raw_value) or defaults.get(opt_key)
        if normalized:
            args_list.extend([flag, normalized])

    logs_buffer = StringIO()
    build_error = None

    if not BUILD_LOCK.acquire(blocking=False):
        return jsonify({"ok": False, "error": "Another build is already in progress. Try again shortly."}), 409

    try:
        with redirect_stdout(logs_buffer), redirect_stderr(logs_buffer):
            try:
                parsed_args = parse_pipeline_args(args_list)
                run_pipeline(parsed_args)
            except BaseException as exc:  # pragma: no cover - runtime pipeline failure
                build_error = exc
    finally:
        BUILD_LOCK.release()

    logs_output = logs_buffer.getvalue()

    if build_error:
        if created_dir:
            shutil.rmtree(target_dir, ignore_errors=True)
        logs_output += f"\n❌ Pipeline failed: {build_error}\n"
        return (
            jsonify({"ok": False, "error": str(build_error), "logs": logs_output}),
            500,
        )

    return jsonify(
        {
            "ok": True,
            "logs": logs_output,
            "database": db_name,
            "databases": list_databases(),
            "db_path": str(target_dir),
        }
    )


@app.route("/", methods=["GET", "POST"])
def home():
    answer, citations = None, None
    selected_db = None
    databases = list_databases()

    if request.method == "POST":
        query = request.form["query"]
        selected_db = request.form["db"]

        if selected_db not in databases:
            answer = f"⚠️ Selected database '{selected_db}' is not available."
            citations = {}
        else:
            try:
                answer, citations = run_rag(query, selected_db)
            except Exception as exc:
                answer = f"⚠️ Unable to answer the question: {exc}"
                citations = {}

    return render_template(
        "index.html",
        answer=answer,
        citations=citations,
        databases=databases,
        selected_db=selected_db,
        db_root=str(DB_BASE_PATH),
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
