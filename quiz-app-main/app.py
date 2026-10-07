"""Simple Quiz application - DevOps demo project (Flask)."""
import json
import os
from functools import wraps
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__)
# Set SECRET_KEY as an environment variable in real deployments
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")


def load_json(filename):
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def load_users():
    """Returns {username: password_hash}."""
    return load_json("users.json")


def load_subjects():
    return load_json("questions.json")["subjects"]


def get_subject(subject_id):
    for subject in load_subjects():
        if subject["id"] == subject_id:
            return subject
    abort(404)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_globals():
    # APP_VERSION is set by the Jenkins build (build number), "dev" locally
    return {"app_version": os.getenv("APP_VERSION", "dev"), "current_user": session.get("user")}


@app.route("/")
def home():
    return redirect(url_for("subjects" if "user" in session else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_hash = load_users().get(username)
        if password_hash and check_password_hash(password_hash, password):
            session.clear()
            session["user"] = username
            return redirect(url_for("subjects"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/subjects")
@login_required
def subjects():
    return render_template("subjects.html", subjects=load_subjects())


@app.route("/quiz/<subject_id>")
@login_required
def quiz(subject_id):
    return render_template("quiz.html", subject=get_subject(subject_id))


@app.route("/quiz/<subject_id>/submit", methods=["POST"])
@login_required
def submit(subject_id):
    subject = get_subject(subject_id)
    questions = subject["questions"]
    score = 0
    review = []
    for q in questions:
        chosen = request.form.get(f"q{q['id']}")
        is_correct = chosen == q["answer"]
        score += is_correct
        review.append(
            {
                "question": q["question"],
                "chosen": chosen or "Not answered",
                "answer": q["answer"],
                "correct": is_correct,
            }
        )
    total = len(questions)
    percent = round(score * 100 / total) if total else 0
    return render_template(
        "result.html", subject=subject, score=score, total=total, percent=percent, review=review
    )


@app.route("/health")
def health():
    """Used by Jenkins and Docker HEALTHCHECK to verify the app is running."""
    return jsonify(status="ok", version=os.getenv("APP_VERSION", "dev"))


@app.route("/api/subjects")
def api_subjects():
    """Subjects and questions as JSON, without the answers."""
    return jsonify(
        [
            {
                "id": s["id"],
                "name": s["name"],
                "questions": [{k: v for k, v in q.items() if k != "answer"} for q in s["questions"]],
            }
            for s in load_subjects()
        ]
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
