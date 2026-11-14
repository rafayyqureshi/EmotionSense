# EmotionSense

**Python · Flask · Hugging Face integration · CSV processing · Automated tests**

A text-emotion analysis prototype with a browser interface and JSON API. Every result identifies whether it came from a remote classifier, local keyword rules, or an experimental mixed pipeline.

## Engineering features

- Deterministic, whole-word fallback rules: identical input produces identical local scores.
- Explicit inference provenance in API responses and the interface.
- Validated JSON and CSV input, bounded provider requests, and structured client errors.
- In-memory CSV processing with a visible five-comment limit and no duplicate probe request.
- Escaped comment and error text in the browser.
- 30 Python contract/unit tests and three JavaScript escaping tests; provider calls are mocked.

## Run locally

Tested in a clean Python 3.12 environment. Node.js 18 or newer is needed only for the JavaScript tests.

~~~bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
~~~

Open http://127.0.0.1:5000/. No token is required for the local rules demo. Without a configured token, the application sends no provider requests.

For remote inference, copy .env.example to .env and set HUGGINGFACE_API_KEY. The classifier URL defaults to the Hugging Face inference router. Access, model availability and any provider charges depend on your account. .env is ignored by Git.

HUGGINGFACE_GENERATION_URL is optional. It must return a text-generation response with a generated_text field. A configured endpoint must be trusted: it receives the submitted text and the bearer token. Generated text is scored with keyword rules, not a second emotion classifier.

## How to interpret results

| API pipeline | Result source | Interpretation |
| --- | --- | --- |
| bert | Remote classifier when available; local rules otherwise | Remote labels are mapped to six display categories and normalized. |
| gpt | Keyword rules on generated text, or local fallback | This is not a GPT emotion-classification probability. The identifier is retained for compatibility. |
| ensemble | 60% classifier path + 40% generation path | An experimental weighted combination; component sources and fallback use are disclosed. |

Every response contains provenance.method, label, used_fallback, is_model_prediction, score_label, note and components. The interface displays the source for single results and batch rows.

All displayed values are **relative scores, not calibrated confidence**. The legacy confidence field remains for API compatibility and contains the highest relative score. If local rules find no known word, the fallback assigns the neutral category. These simple rules do not understand negation, sarcasm, context or multilingual nuance. The model-label mapping groups disgust with angry and love with happy; it is a display convention, not a validated taxonomy.

## API

| Method | Route | Input |
| --- | --- | --- |
| GET | / | Browser interface |
| POST | /api/analyze | JSON object with comment and optional model_type |
| POST | /api/batch | Multipart file upload and optional model_type |

Example request:

~~~json
{
  "comment": "I am excited to start this project.",
  "model_type": "bert"
}
~~~

An example fallback response includes:

~~~json
{
  "primary_emotion": "happy",
  "provenance": {
    "method": "local_keywords",
    "label": "Local keyword fallback",
    "used_fallback": true,
    "is_model_prediction": false
  }
}
~~~

The example is abbreviated; full responses also include scores, the submitted comment, timing and provenance details.

A UTF-8 CSV must contain a comment column:

~~~csv
comment
"I am excited to start this project."
"The delivery was delayed."
~~~

### Limits and errors

- A comment must be a nonblank string of at most 5,000 characters.
- Request bodies are limited to 16 MiB. Oversized requests return JSON with HTTP 413.
- Invalid JSON, unsupported pipeline names, unreadable CSVs or missing columns return HTTP 400.
- Blank CSV cells are skipped. Overlong rows are reported in errors.
- Only the first five valid comments are analyzed. Responses include processed_count, total_rows, row_limit, truncated and a warning when truncated.
- Each provider request uses a 3.05-second connection timeout and a 15-second read timeout, with no automatic retries. Provider failures produce an explicitly labeled fallback.

## Verification

~~~bash
python -m unittest discover -s tests -v
node --test tests/text-utils.test.cjs
node --check static/js/main.js
gunicorn --check-config app:app
~~~

Tests cover score validation, deterministic fallback, provider provenance and failures, invalid requests, CSV edge cases, upload limits and HTML escaping. GitHub Actions runs the Python and JavaScript tests on pushes and pull requests using Python 3.12.

The checks validate application behavior with mocked provider responses. Live inference availability, model accuracy and production load have not been benchmarked.

## Code map

| Path | Responsibility |
| --- | --- |
| app.py | Flask routes, request validation and provider orchestration |
| emotion_core.py | Score normalization, keyword rules and result provenance |
| templates/index.html | Browser interface and pipeline explanations |
| static/js/main.js | Form submissions and result rendering |
| static/js/text-utils.js | HTML text escaping |
| tests/ | Python API/core tests and JavaScript escaping tests |
| .github/workflows/tests.yml | Automated checks |
| .env.example | Optional local provider configuration |

## Scope

This is a development prototype. It has no authentication, public-service rate limiting, persistent job queue or model-quality evaluation suite. Submitted text and uploads are not written to files by the application; configured remote providers receive the text being analyzed. Browser styling loads from public CDNs. Existing sample files remain in the repository.

[Software engineering portfolio](https://github.com/rafayyqureshi/rafay-portfolio)

