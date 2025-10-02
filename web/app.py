from flask import Flask, request, render_template
from rag_server import DB_BASE_PATH, run_rag, list_databases

app = Flask(__name__)

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
