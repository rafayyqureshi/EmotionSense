# Emotion Analysis System

A web application for analyzing emotions in text comments using natural language processing.

## Features

- Single comment emotion analysis
- Batch processing of CSV files containing multiple comments
- Multiple model options: BERT, GPT, and Ensemble
- Clean, modern social media inspired interface
- Responsive design for desktop and mobile devices

## Project Structure

```
├── app.py                 # Main Flask application
├── static/
│   ├── css/               # CSS stylesheets
│   │   └── style.css
│   └── js/                # JavaScript files
│       └── main.js
├── templates/             # HTML templates
│   └── index.html
└── uploads/               # Directory for uploaded files (created at runtime)
```

## Installation

1. Clone the repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Run the Flask application:

```bash
python app.py
```

2. Open your web browser and navigate to `http://127.0.0.1:5000/`

## API Endpoints

- `GET /` - Main application page
- `POST /api/analyze` - Analyze a single comment
- `POST /api/batch` - Process a batch of comments from a CSV file

## CSV File Format

For batch processing, the CSV file should contain a column named `comment`:

```
comment
"I'm so excited about the upcoming vacation! Can't wait!"
"This is completely unacceptable! I've been waiting for hours!"
"I miss how things used to be. Nothing feels the same anymore."
"The meeting went well, we discussed the next steps..."
"I'm really worried about the deadline, we might not make it."
```

## Technologies Used

- Backend: Python, Flask
- Frontend: HTML, CSS, JavaScript
- Libraries: Bootstrap, Font Awesome
- Data Processing: pandas

## Future Improvements

- Integration with a real NLP model for emotion analysis
- User authentication system
- Historical analysis tracking
- Export functionality for analysis results
- Multi-language support 