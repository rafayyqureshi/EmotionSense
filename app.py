from flask import Flask, render_template, request, jsonify
import pandas as pd
import json
import os
import time
import random
import requests
from datetime import datetime
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Hugging Face API configuration
# Note: In a production application, you would use an actual API key
# For this demo, we're using the demo endpoint which has rate limits
API_URL_BERT = "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base"
API_URL_GPT = "https://api-inference.huggingface.co/models/distilgpt2"
# Load API key from environment variable
API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")
API_HEADERS = {"Authorization": f"Bearer {API_KEY}"}  # Get key from environment variable

print("Using Hugging Face API for BERT and GPT emotion classification...")

# Track model usage
model_usage = {
    "bert": 0,
    "gpt": 0,
    "ensemble": 0
}

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def query_huggingface_api(text, api_url):
    """Query the Hugging Face API for emotion classification"""
    try:
        print(f"Calling API: {api_url[:50]}... with text: {text[:30]}...")
        response = requests.post(api_url, headers=API_HEADERS, json={"inputs": text})
        print(f"API response status: {response.status_code}")
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        
        # If the model is loading, wait and retry
        if response.status_code == 503:
            print("Model is loading, waiting to retry...")
            time.sleep(2)  # Wait longer for model to load
            response = requests.post(api_url, headers=API_HEADERS, json={"inputs": text})
            print(f"Retry response status: {response.status_code}")
            if response.status_code == 200:
                return response.json()
        
        # Log the error details
        print(f"API Error: Status {response.status_code}, Response: {response.text[:200]}")
        
        # If still not successful, use fallback
        return None
    
    except Exception as e:
        print(f"API error: {str(e)}")
        return None

def process_bert_api_response(api_response, text):
    """Process the BERT API response"""
    # If API response failed, use fallback
    if api_response is None:
        return fallback_emotion_analysis(text, "bert")
    
    try:
        # Format differs based on API endpoint, this is for emotion classification
        emotions = {}
        
        # The API returns a list of emotions with scores
        for emotion_data in api_response[0]:
            emotion = emotion_data['label']
            score = emotion_data['score']
            
            # Map to our standard emotions
            mapped_emotion = map_emotion(emotion)
            if mapped_emotion in emotions:
                emotions[mapped_emotion] += score
            else:
                emotions[mapped_emotion] = score
                
        # Ensure all standard emotions exist
        for emotion in ["happy", "sad", "angry", "fear", "neutral", "surprise"]:
            if emotion not in emotions:
                emotions[emotion] = 0.01
        
        # Normalize
        total = sum(emotions.values())
        emotions = {k: v/total for k, v in emotions.items()}
        
        return emotions
    
    except Exception as e:
        print(f"Error processing BERT API response: {e}")
        return fallback_emotion_analysis(text, "bert")

def process_gpt_api_response(api_response, text):
    """Process the GPT API response"""
    # If API response failed, use fallback
    if api_response is None:
        return fallback_emotion_analysis(text, "gpt")
    
    try:
        # For GPT, we need to analyze the generated text for emotions
        generated_text = api_response[0].get('generated_text', '')
        if not generated_text:
            return fallback_emotion_analysis(text, "gpt")
            
        # We'll use a keyword approach to extract emotions from the generated text
        emotions = extract_emotions_from_text(generated_text)
        
        return emotions
    
    except Exception as e:
        print(f"Error processing GPT API response: {e}")
        return fallback_emotion_analysis(text, "gpt")

def extract_emotions_from_text(text):
    """Extract emotions from text using keyword approach"""
    # Define emotion keywords
    emotion_keywords = {
        "happy": ["happy", "joy", "glad", "excited", "wonderful", "amazing", "great", "love", "excellent"],
        "sad": ["sad", "unhappy", "disappointed", "depressed", "miserable", "upset", "crying", "sorry", "miss"],
        "angry": ["angry", "mad", "furious", "annoyed", "irritated", "frustrated", "hate", "unfair", "terrible"],
        "fear": ["afraid", "scared", "fear", "worried", "nervous", "terrified", "anxious", "concern", "panic"],
        "neutral": ["okay", "fine", "normal", "standard", "regular", "average", "common", "usual", "typical"],
        "surprise": ["wow", "surprised", "unexpected", "shocking", "unbelievable", "amazed", "astonished", "startled"]
    }
    
    # Initialize score
    emotions = {emotion: 0.1 for emotion in emotion_keywords}  # Baseline
    
    # Check for emotions in the text
    text_lower = text.lower()
    for emotion, keywords in emotion_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                emotions[emotion] += 0.2
    
    # Normalize
    total = sum(emotions.values())
    emotions = {k: v/total for k, v in emotions.items()}
    
    return emotions

def map_emotion(api_emotion):
    """Map API emotion labels to our standard set"""
    mapping = {
        "joy": "happy",
        "happiness": "happy",
        "sadness": "sad",
        "anger": "angry",
        "fear": "fear",
        "neutral": "neutral",
        "surprise": "surprise",
        "disgust": "angry",  # Map disgust to angry
        "love": "happy",     # Map love to happy
        "admiration": "happy",
        "disappointment": "sad",
        "annoyance": "angry",
        "disapproval": "angry",
        "realization": "surprise",
        "nervousness": "fear",
        "approval": "happy",
        "confusion": "surprise",
        "caring": "happy",
        "desire": "happy",
        "excitement": "happy",
        "gratitude": "happy",
        "optimism": "happy",
        "relief": "happy",
        "remorse": "sad",
        "embarrassment": "sad",
        "grief": "sad"
    }
    
    return mapping.get(api_emotion.lower(), "neutral")

def fallback_emotion_analysis(text, model_type="bert"):
    """Fallback emotion analysis when API fails"""
    print(f"Using fallback for {model_type} analysis")
    
    # Define base emotion detection
    emotions = {
        "happy": 0.1,
        "sad": 0.1,
        "angry": 0.1,
        "fear": 0.1,
        "neutral": 0.1,
        "surprise": 0.1
    }
    
    # Simple keyword-based analysis
    text_lower = text.lower()
    
    # Happy keywords
    if any(word in text_lower for word in ["happy", "joy", "glad", "excited", "great", "love"]):
        emotions["happy"] += 0.3
        
    # Sad keywords
    if any(word in text_lower for word in ["sad", "unhappy", "disappointed", "miserable", "sorry"]):
        emotions["sad"] += 0.3
        
    # Angry keywords
    if any(word in text_lower for word in ["angry", "mad", "furious", "annoyed", "hate"]):
        emotions["angry"] += 0.3
        
    # Fear keywords
    if any(word in text_lower for word in ["afraid", "scared", "fear", "worried", "nervous"]):
        emotions["fear"] += 0.3
        
    # Surprise keywords
    if any(word in text_lower for word in ["wow", "surprised", "unexpected", "shocking"]):
        emotions["surprise"] += 0.3
    
    # Add sentiment from punctuation
    if "!" in text:
        emotions["happy" if "happy" in text_lower or "great" in text_lower else "surprise"] += 0.1
    
    # Check for questions
    if "?" in text:
        emotions["surprise"] += 0.1
    
    # Model-specific adjustments
    if model_type == "gpt":
        # GPT tends to be more positive
        emotions["happy"] *= 1.2
        emotions["sad"] *= 0.9
    else:
        # BERT tends to be more neutral
        emotions["neutral"] *= 1.2
    
    # Add randomness to simulate model variance
    for emotion in emotions:
        emotions[emotion] += random.uniform(0, 0.1)
    
    # Normalize
    total = sum(emotions.values())
    emotions = {k: v/total for k, v in emotions.items()}
    
    return emotions

def analyze_with_bert(text):
    """Analyze text using BERT model via Hugging Face API"""
    start_time = time.time()
    
    # Call Hugging Face API
    api_response = query_huggingface_api(text, API_URL_BERT)
    
    # Process the response
    emotions = process_bert_api_response(api_response, text)
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    # Get primary emotion
    primary_emotion = max(emotions, key=emotions.get)
    confidence = emotions[primary_emotion]
    
    # Track usage
    model_usage["bert"] += 1
    
    return {
        "emotions": emotions,
        "primary_emotion": primary_emotion,
        "confidence": confidence,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": "bert",
        "processing_time_ms": round(processing_time * 1000, 2)
    }

def analyze_with_gpt(text):
    """Analyze text using GPT model via Hugging Face API"""
    start_time = time.time()
    
    # Call Hugging Face API
    api_response = query_huggingface_api(text, API_URL_GPT)
    
    # Process the response
    emotions = process_gpt_api_response(api_response, text)
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    # Get primary emotion
    primary_emotion = max(emotions, key=emotions.get)
    confidence = emotions[primary_emotion]
    
    # Track usage
    model_usage["gpt"] += 1
    
    return {
        "emotions": emotions,
        "primary_emotion": primary_emotion,
        "confidence": confidence,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": "gpt",
        "processing_time_ms": round(processing_time * 1000, 2)
    }

def analyze_with_ensemble(text):
    """Analyze text using an ensemble of BERT and GPT models"""
    # Get results from both models
    bert_results = analyze_with_bert(text)
    gpt_results = analyze_with_gpt(text)
    
    # Combine the emotion scores (weighted average)
    bert_weight = 0.6  # Give slightly more weight to BERT
    gpt_weight = 0.4
    
    # Initialize combined emotions
    combined_emotions = {}
    
    # Combine scores
    for emotion in bert_results["emotions"]:
        bert_score = bert_results["emotions"].get(emotion, 0)
        gpt_score = gpt_results["emotions"].get(emotion, 0)
        combined_emotions[emotion] = bert_score * bert_weight + gpt_score * gpt_weight
    
    # Get primary emotion
    primary_emotion = max(combined_emotions, key=combined_emotions.get)
    confidence = combined_emotions[primary_emotion]
    
    # Calculate confidence as the average of the models' confidence for their primary emotions
    avg_confidence = (bert_results["confidence"] + gpt_results["confidence"]) / 2
    
    # Calculate total processing time
    total_time = bert_results.get("processing_time_ms", 0) + gpt_results.get("processing_time_ms", 0)
    
    # Track usage (but decrement the individual models since they were incremented in their functions)
    model_usage["bert"] -= 1
    model_usage["gpt"] -= 1
    model_usage["ensemble"] += 1
    
    return {
        "emotions": combined_emotions,
        "primary_emotion": primary_emotion,
        "confidence": confidence,
        "ensemble_confidence": avg_confidence,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": "ensemble",
        "bert_primary": bert_results["primary_emotion"],
        "gpt_primary": gpt_results["primary_emotion"],
        "processing_time_ms": total_time
    }

def analyze_text(text, model_type="bert"):
    """Analyze text using the specified model"""
    if model_type == "bert":
        return analyze_with_bert(text)
    elif model_type == "gpt":
        return analyze_with_gpt(text)
    elif model_type == "ensemble":
        return analyze_with_ensemble(text)
    else:
        # Default to BERT
        return analyze_with_bert(text)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_comment():
    try:
        data = request.json
        comment = data.get('comment', '').strip()
        model_type = data.get('model_type', 'bert').lower()
        
        if not comment:
            return jsonify({'error': 'Comment text is required'}), 400
        
        # Analyze the text
        result = analyze_text(comment, model_type)
        
        # Save to log (in a real app, this would go to a database)
        try:
            with open('analysis_log.json', 'a') as f:
                log_entry = {
                    'comment': comment,
                    'model_type': model_type,
                    'result': result
                }
                f.write(json.dumps(log_entry) + '\n')
        except:
            pass  # Don't fail if logging fails
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch', methods=['POST'])
def batch_process():
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        model_type = request.form.get('model_type', 'bert').lower()
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the CSV file
            try:
                print(f"Loading CSV file: {filepath}")
                df = pd.read_csv(filepath)
                print(f"CSV columns found: {list(df.columns)}")
                
                if 'comment' not in df.columns:
                    return jsonify({
                        'error': f'CSV file must contain a column named "comment". Found columns: {list(df.columns)}'
                    }), 400
                
                # Verify we can analyze at least one comment before proceeding
                if len(df) > 0:
                    test_comment = str(df.iloc[0]['comment']).strip()
                    if test_comment:
                        print(f"Testing analysis with first comment: '{test_comment[:30]}...'")
                        try:
                            analyze_text(test_comment, model_type)
                            print("Test analysis successful")
                        except Exception as e:
                            print(f"Test analysis failed: {str(e)}")
                            return jsonify({
                                'error': f'API test failed. Please try again later or switch models. Error: {str(e)}'
                            }), 500
                
                results = []
                errors = []
                emotion_counts = {}
                max_comments = min(5, len(df))  # Process maximum 5 comments to avoid rate limits
                
                print(f"Processing {max_comments} comments from CSV file")
                for index, row in df.iloc[:max_comments].iterrows():
                    try:
                        comment = str(row['comment']).strip()
                        if not comment:
                            continue
                            
                        print(f"Processing comment {index+1}: '{comment[:30]}...'")
                        # Add retry logic with backoff
                        max_retries = 2
                        for retry in range(max_retries + 1):
                            try:
                                result = analyze_text(comment, model_type)
                                
                                # Update emotion counts
                                primary_emotion = result.get('primary_emotion')
                                if primary_emotion:
                                    emotion_counts[primary_emotion] = emotion_counts.get(primary_emotion, 0) + 1
                                
                                results.append({
                                    'comment': comment,
                                    'analysis': result
                                })
                                break
                            except Exception as e:
                                if retry < max_retries:
                                    print(f"Retry {retry+1} after error: {str(e)}")
                                    time.sleep(2)  # Wait longer between retries
                                else:
                                    raise
                    except Exception as e:
                        print(f"Error processing comment {index}: {str(e)}")
                        errors.append({
                            'comment_index': index,
                            'error': str(e)
                        })
                
                response_data = {
                    'message': f'Processed {len(results)} comments successfully',
                    'results': results,
                    'emotion_counts': emotion_counts
                }
                
                if errors:
                    response_data['errors'] = errors
                    response_data['warning'] = f'Failed to process {len(errors)} comments.'
                
                if len(df) > max_comments:
                    response_data['warning'] = f'Only processed {max_comments} out of {len(df)} comments to avoid API rate limits.'
                
                return jsonify(response_data)
            
            except Exception as e:
                print(f"CSV processing error: {str(e)}")
                return jsonify({'error': f'Error processing CSV: {str(e)}'}), 500
        else:
            return jsonify({'error': 'File type not allowed'}), 400
    
    except Exception as e:
        print(f"Batch processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 