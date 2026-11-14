# EmotionSense — Text Emotion Analysis

**Python · Flask · Model API integration · CSV processing**

A Flask prototype for exploring emotion analysis through a single-comment interface and a CSV batch workflow.

## What is implemented

- Single-comment analysis with BERT, GPT and ensemble options.
- CSV uploads containing a comment column.
- Hugging Face inference API integration.
- Browser interface and JSON endpoints.
- Local upload storage and analysis logging.

## Model behavior

The application attempts remote inference when configured. If a request fails, it falls back to keyword-based scores with random variation. Fallback output is illustrative, not a measured model prediction. No model-quality benchmark is claimed.

## Run locally

Create and activate a virtual environment, then run:

~~~bash
python -m pip install -r requirements.txt
python app.py
~~~

Open http://127.0.0.1:5000/.

For remote inference, set HUGGINGFACE_API_KEY in your local environment or a local .env file. Keep the key outside Git. Without a usable inference response, the fallback path remains available.

## API

| Method | Route | Input |
| --- | --- | --- |
| GET | / | Browser interface |
| POST | /api/analyze | JSON with comment and optional model_type |
| POST | /api/batch | Multipart file upload and optional model_type |

Example single-comment request:

~~~json
{
  "comment": "I am excited to start this project.",
  "model_type": "bert"
}
~~~

A batch CSV uses this shape:

~~~csv
comment
"I am excited to start this project."
"The delivery was delayed."
~~~

## Code map

| Path | Purpose |
| --- | --- |
| app.py | Routes, API integration, response mapping and fallback logic |
| templates/index.html | Browser interface |
| static/ | Interface styles and client behavior |
| sample_comments.csv | Small example batch |
| requirements.txt | Application dependencies |

Uploads are stored locally in uploads/. Analysis events are appended to analysis_log.json. The application is a development prototype, with no user-account or production operations layer.

[Software engineering portfolio](https://github.com/rafayyqureshi/rafay-portfolio)
