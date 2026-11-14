"""Emotion-analysis prototype with bounded requests and explicit result provenance."""
from datetime import datetime, timezone
import os
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
import pandas as pd
import requests
from werkzeug.exceptions import RequestEntityTooLarge

from emotion_core import classifier_analysis, combine_results, keyword_analysis

load_dotenv(Path(__file__).with_name(".env"))
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")
API_URL_BERT = os.environ.get(
    "HUGGINGFACE_CLASSIFIER_URL",
    "https://router.huggingface.co/hf-inference/models/"
    "j-hartmann/emotion-english-distilroberta-base",
)
# A text-generation endpoint is opt-in. Generated text is analyzed with rules.
API_URL_GPT = os.environ.get("HUGGINGFACE_GENERATION_URL", "")
API_TIMEOUT = (3.05, 15)
MAX_COMMENT_LENGTH = 5000
BATCH_LIMIT = 5
MODELS = {"bert", "gpt", "ensemble"}


def query_huggingface_api(text, api_url):
    """Make one bounded request only when both credentials and an endpoint exist."""
    if not API_KEY or not api_url:
        return None
    try:
        response = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={"inputs": text},
            timeout=API_TIMEOUT,
        )
        if response.status_code != 200:
            app.logger.info("Remote inference unavailable (HTTP %s)", response.status_code)
            return None
        return response.json()
    except (requests.RequestException, ValueError):
        app.logger.info("Remote inference unavailable; using labeled fallback")
        return None


def classifier_result(text):
    payload = query_huggingface_api(text, API_URL_BERT)
    try:
        return classifier_analysis(payload)
    except (ValueError, TypeError, OverflowError):
        return keyword_analysis(text)


def generation_result(text):
    payload = query_huggingface_api(text, API_URL_GPT)
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        generated = payload[0].get("generated_text")
        if isinstance(generated, str) and generated.strip():
            return keyword_analysis(generated, generated=True)
    return keyword_analysis(text)


def analyze_text(text, model_type="bert"):
    if model_type not in MODELS:
        raise ValueError("Choose bert, gpt or ensemble")
    started = perf_counter()
    if model_type == "bert":
        inference = classifier_result(text)
    elif model_type == "gpt":
        inference = generation_result(text)
    else:
        inference = combine_results(classifier_result(text), generation_result(text))
    primary = max(inference.scores, key=inference.scores.get)
    return {
        "comment": text,
        "emotions": inference.scores,
        "primary_emotion": primary,
        # Retained for API compatibility. The UI labels this as a relative score.
        "confidence": inference.scores[primary],
        "model": model_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processing_time_ms": round((perf_counter() - started) * 1000, 2),
        "provenance": inference.provenance(),
    }


def validate_comment(comment):
    if not isinstance(comment, str) or not comment.strip():
        raise ValueError("Comment text is required and must be a string")
    comment = comment.strip()
    if len(comment) > MAX_COMMENT_LENGTH:
        raise ValueError(f"Comment must be {MAX_COMMENT_LENGTH} characters or fewer")
    return comment


def validate_model(value):
    if not isinstance(value, str) or value.lower() not in MODELS:
        raise ValueError("Choose bert, gpt or ensemble")
    return value.lower()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze_comment():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Send a JSON object containing a comment"), 400
    try:
        comment = validate_comment(data.get("comment"))
        model = validate_model(data.get("model_type", "bert"))
    except ValueError as error:
        return jsonify(error=str(error)), 400
    return jsonify(analyze_text(comment, model))


@app.route("/api/batch", methods=["POST"])
def batch_process():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify(error="Select a CSV file"), 400
    if Path(uploaded.filename).suffix.lower() != ".csv":
        return jsonify(error="File type not allowed; use CSV"), 400
    try:
        model = validate_model(request.form.get("model_type", "bert"))
        # Process the stream in memory. No uploaded file is persisted.
        frame = pd.read_csv(uploaded.stream, dtype=str, keep_default_na=False)
    except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError):
        return jsonify(error="Provide a readable UTF-8 CSV and a supported model"), 400
    if "comment" not in frame.columns:
        return jsonify(error="CSV file must contain a column named comment"), 400
    comments, errors = [], []
    for index, value in enumerate(frame["comment"], start=1):
        if not value.strip():
            continue
        try:
            comments.append(validate_comment(value))
        except ValueError as error:
            errors.append({"row": index, "error": str(error)})
    results, counts = [], {}
    for comment in comments[:BATCH_LIMIT]:
        result = analyze_text(comment, model)
        results.append({"comment": comment, "analysis": result})
        emotion = result["primary_emotion"]
        counts[emotion] = counts.get(emotion, 0) + 1
    response = {
        "message": f"Processed {len(results)} comments successfully",
        "results": results,
        "emotion_counts": counts,
        "processed_count": len(results),
        "total_rows": len(frame),
        "row_limit": BATCH_LIMIT,
        "truncated": len(comments) > BATCH_LIMIT,
    }
    if errors:
        response["errors"] = errors
    if response["truncated"]:
        response["warning"] = f"Only the first {BATCH_LIMIT} valid comments were processed."
    return jsonify(response)


@app.errorhandler(RequestEntityTooLarge)
def upload_too_large(_error):
    return jsonify(error="Upload exceeds the 16 MiB limit"), 413


if __name__ == "__main__":
    app.run(debug=False)
