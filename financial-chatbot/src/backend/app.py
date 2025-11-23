from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pandas as pd
from werkzeug.utils import secure_filename
import json
from datetime import datetime

# Import our existing modules
from pdfconverter import load_transactions_from_file
from financial_chatbot import FinancialChatbot

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'csv', 'xls', 'xlsx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Store chatbot instances per session (in production, use Redis or similar)
chatbot_sessions = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Backend is running'})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Handle file upload and convert to dataframe using pdfconverter.py
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        session_id = request.form.get('session_id', 'default')

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload PDF, Excel, or CSV files.'}), 400

        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Use pdfconverter to load and standardize transactions
        try:
            df = load_transactions_from_file(filepath, keep_extra=True)

            # Store dataframe for this session
            if session_id not in chatbot_sessions:
                chatbot_sessions[session_id] = {
                    'dataframes': [],
                    'chatbot': None
                }

            chatbot_sessions[session_id]['dataframes'].append({
                'filename': filename,
                'df': df,
                'uploaded_at': datetime.now().isoformat()
            })

            # Initialize or update chatbot with combined dataframe
            all_dfs = [item['df'] for item in chatbot_sessions[session_id]['dataframes']]
            combined_df = pd.concat(all_dfs, ignore_index=True) if len(all_dfs) > 1 else all_dfs[0]

            # Get API key from environment or request
            api_key = os.getenv('GROQ_API_KEY', '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')

            # Initialize chatbot with the dataframe
            chatbot_sessions[session_id]['chatbot'] = FinancialChatbot(api_key, combined_df)

            # Get basic statistics
            stats = {
                'total_transactions': len(df),
                'date_range': {
                    'start': df['transaction_date'].min().strftime('%Y-%m-%d') if 'transaction_date' in df.columns else None,
                    'end': df['transaction_date'].max().strftime('%Y-%m-%d') if 'transaction_date' in df.columns else None
                },
                'total_amount': float(df['transaction_amount'].sum()) if 'transaction_amount' in df.columns else 0
            }

            return jsonify({
                'success': True,
                'filename': filename,
                'stats': stats,
                'message': f'Successfully processed {filename}. Found {len(df)} transactions.'
            })

        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle chat queries using financial_chatbot.py
    """
    try:
        data = request.json
        message = data.get('message', '')
        session_id = data.get('session_id', 'default')

        if not message:
            return jsonify({'error': 'No message provided'}), 400

        # Check if session exists
        if session_id not in chatbot_sessions or not chatbot_sessions[session_id]['chatbot']:
            return jsonify({'error': 'No data uploaded yet. Please upload a file first.'}), 400

        chatbot = chatbot_sessions[session_id]['chatbot']

        # Use the chatbot's chat method
        response = chatbot.chat(message)

        return jsonify({
            'success': True,
            'response': response,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/set-income', methods=['POST'])
def set_income():
    """
    Set monthly income for budget calculations
    """
    try:
        data = request.json
        income = data.get('income')
        session_id = data.get('session_id', 'default')

        if not income:
            return jsonify({'error': 'No income value provided'}), 400

        if session_id not in chatbot_sessions or not chatbot_sessions[session_id]['chatbot']:
            return jsonify({'error': 'No data uploaded yet. Please upload a file first.'}), 400

        chatbot = chatbot_sessions[session_id]['chatbot']
        chatbot.set_income(float(income))

        return jsonify({
            'success': True,
            'message': f'Income set to ${float(income):,.2f}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-transaction', methods=['POST'])
def add_transaction():
    """
    Add a new transaction
    """
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        amount = data.get('amount')
        description = data.get('description')
        category = data.get('category')
        category_type = data.get('category_type')

        if not amount or not description:
            return jsonify({'error': 'Amount and description are required'}), 400

        if session_id not in chatbot_sessions or not chatbot_sessions[session_id]['chatbot']:
            return jsonify({'error': 'No data uploaded yet. Please upload a file first.'}), 400

        chatbot = chatbot_sessions[session_id]['chatbot']
        response = chatbot.add_transaction(
            amount=float(amount),
            description=description,
            category=category,
            category_type=category_type
        )

        return jsonify({
            'success': True,
            'response': response
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/summary', methods=['GET'])
def get_summary():
    """
    Get budget summary
    """
    try:
        session_id = request.args.get('session_id', 'default')

        if session_id not in chatbot_sessions or not chatbot_sessions[session_id]['chatbot']:
            return jsonify({'error': 'No data uploaded yet. Please upload a file first.'}), 400

        chatbot = chatbot_sessions[session_id]['chatbot']
        summary = chatbot.get_summary()

        return jsonify({
            'success': True,
            'summary': summary
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/initial-analysis', methods=['GET'])
def initial_analysis():
    """
    Get initial budget analysis
    """
    try:
        session_id = request.args.get('session_id', 'default')

        if session_id not in chatbot_sessions or not chatbot_sessions[session_id]['chatbot']:
            return jsonify({'error': 'No data uploaded yet. Please upload a file first.'}), 400

        chatbot = chatbot_sessions[session_id]['chatbot']
        analysis = chatbot.get_initial_analysis()

        return jsonify({
            'success': True,
            'analysis': analysis
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
