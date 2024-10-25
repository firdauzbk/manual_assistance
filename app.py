from flask import Flask, request, render_template, jsonify, session
from werkzeug.utils import secure_filename
import os
from manual_assistant import ManualAssistant
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configure upload folder
UPLOAD_FOLDER = Path('uploads')
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Store ManualAssistant instances for each session
assistants = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
            
        if file and allowed_file(file.filename):
            # Create unique session ID if not exists
            if 'session_id' not in session:
                session['session_id'] = os.urandom(16).hex()
            
            logger.info(f"Processing file upload for session {session['session_id']}")
            
            # Save file with secure filename
            filename = secure_filename(file.filename)
            filepath = app.config['UPLOAD_FOLDER'] / filename
            file.save(filepath)
            
            # Initialize ManualAssistant for this session
            assistant = ManualAssistant()
            assistant.load_manual(str(filepath))
            assistants[session['session_id']] = assistant
            
            logger.info("File processed successfully")
            return jsonify({'message': 'Manual uploaded successfully!'})
            
        logger.error("Invalid file type")
        return jsonify({'error': 'Invalid file type'}), 400
        
    except Exception as e:
        logger.error(f"Error in upload_file: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No data received'}), 400
            
        question = data.get('question')
        if not question:
            logger.error("No question in request")
            return jsonify({'error': 'No question provided'}), 400
            
        logger.info(f"Processing question: {question}")
        
        if 'session_id' not in session:
            logger.error("No session ID found")
            return jsonify({'error': 'No manual loaded - session expired'}), 400
            
        assistant = assistants.get(session['session_id'])
        if not assistant:
            logger.error(f"No assistant found for session {session['session_id']}")
            return jsonify({'error': 'No manual loaded - please reload the page'}), 400
            
        answer = assistant.answer_question(question)
        logger.info(f"Answer generated: {answer}")
        
        return jsonify({'answer': answer})
        
    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}", exc_info=True)
        return jsonify({'error': f"Error processing question: {str(e)}"}), 500

# Add a route to check session status
@app.route('/check_session', methods=['GET'])
def check_session():
    if 'session_id' in session and session['session_id'] in assistants:
        return jsonify({'status': 'active'})
    return jsonify({'status': 'inactive'})

if __name__ == '__main__':
    app.run(debug=True)