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

def parse_budget_input(expenses, wants, savings):
    """
    Parse budget input that can be either fractions (0.7, 0.2, 0.1) or percentages (70, 20, 10).
    Returns normalized fractions (values between 0 and 1 that sum to 1).
    """
    try:
        expenses = float(expenses)
        wants = float(wants)
        savings = float(savings)
        
        # Check if values are percentages (sum > 1) or fractions (sum <= 1)
        total = expenses + wants + savings
        
        if total > 1.5:  # Likely percentages (e.g., 70 + 20 + 10 = 100)
            # Convert percentages to fractions
            expenses = expenses / 100
            wants = wants / 100
            savings = savings / 100
            total = expenses + wants + savings
        
        # Normalize to ensure they sum to 1
        if abs(total - 1.0) > 0.01:
            expenses = expenses / total
            wants = wants / total
            savings = savings / total
        
        return expenses, wants, savings
    except (ValueError, TypeError):
        # Return defaults if parsing fails
        return 0.70, 0.20, 0.10

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Backend is running'})

@app.route('/api/set-budget', methods=['POST'])
def set_budget():
    """
    Set budget goals before file upload.
    Accepts expenses, wants, savings as either fractions (0.7, 0.2, 0.1) or percentages (70, 20, 10).
    If not provided, defaults to 70%, 20%, 10%.
    """
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        expenses = data.get('expenses')
        wants = data.get('wants')
        savings = data.get('savings')
        
        # Initialize session if it doesn't exist
        if session_id not in chatbot_sessions:
            chatbot_sessions[session_id] = {
                'dataframes': [],
                'chatbot': None,
                'budget': None
            }
        
        # If budget values are provided, parse and store them
        if expenses is not None and wants is not None and savings is not None:
            expenses, wants, savings = parse_budget_input(expenses, wants, savings)
            chatbot_sessions[session_id]['budget'] = {
                'expenses': expenses,
                'wants': wants,
                'savings': savings
            }
            return jsonify({
                'success': True,
                'message': f'Budget set to: Expenses {expenses*100:.1f}%, Wants {wants*100:.1f}%, Savings {savings*100:.1f}%',
                'budget': {
                    'expenses': expenses,
                    'wants': wants,
                    'savings': savings
                }
            })
        else:
            # Use defaults if not provided
            default_expenses, default_wants, default_savings = 0.70, 0.20, 0.10
            chatbot_sessions[session_id]['budget'] = {
                'expenses': default_expenses,
                'wants': default_wants,
                'savings': default_savings
            }
            return jsonify({
                'success': True,
                'message': 'Using default budget: Expenses 70%, Wants 20%, Savings 10%',
                'budget': {
                    'expenses': default_expenses,
                    'wants': default_wants,
                    'savings': default_savings
                }
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
                    'chatbot': None,
                    'budget': None
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
            chat_session = chatbot_sessions[session_id]['chatbot']
            
            # Set budget goals - use stored budget or defaults (70, 20, 10)
            if chatbot_sessions[session_id]['budget']:
                budget = chatbot_sessions[session_id]['budget']
                chatbot_sessions[session_id]['chatbot'].set_budget_goals(
                    expenses=budget['expenses'],
                    wants=budget['wants'],
                    savings=budget['savings']
                )
            else:
                # Use default budget if not set
                chatbot_sessions[session_id]['chatbot'].set_budget_goals(expenses=0.70, wants=0.20, savings=0.10)


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
    Handle chat queries using financial_chatbot.py with context from uploaded file
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
        
        # Get context from uploaded file data
        try:
            # Get spending analysis
            spending_analysis = chatbot.analyze_current_spending()
            
            # Get budget summary
            summary = chatbot.get_summary()
            
            # Get transaction statistics
            transactions_df = chatbot.transactions_df
            transaction_stats = {
                'total_transactions': len(transactions_df),
                'date_range': {
                    'start': transactions_df['transaction_date'].min().strftime('%Y-%m-%d') if 'transaction_date' in transactions_df.columns else None,
                    'end': transactions_df['transaction_date'].max().strftime('%Y-%m-%d') if 'transaction_date' in transactions_df.columns else None
                },
                'income_from_transactions': chatbot.income,
                'total_amount': float(transactions_df['transaction_amount'].sum()) if 'transaction_amount' in transactions_df.columns else 0
            }
            
            # Get category breakdown
            category_breakdown = spending_analysis.get('category_breakdown', {})
            
            # Build context message
            context = f"""Current Financial Context from Uploaded File:

            Transaction Statistics:
            - Total Transactions: {transaction_stats['total_transactions']}
            - Date Range: {transaction_stats['date_range']['start']} to {transaction_stats['date_range']['end']}
            - Income from Transactions: ${transaction_stats['income_from_transactions']:,.2f}
            - Total Transaction Amount: ${transaction_stats['total_amount']:,.2f}

            Current Spending:
            - Expenses: ${spending_analysis['spending'].get('expenses', 0):,.2f}
            - Wants: ${spending_analysis['spending'].get('wants', 0):,.2f}
            - Savings: ${spending_analysis['spending'].get('savings', 0):,.2f}
            - Total Spent: ${spending_analysis['total_spent']:,.2f}

            Budget Summary:
            - Budget Income: ${summary['total_income']:,.2f}
            - Expenses Budget: ${summary['budget_allocations']['expenses']:,.2f} (Spent: ${summary['current_spending']['expenses']:,.2f}, Remaining: ${summary['remaining_budget']['expenses']:,.2f})
            - Wants Budget: ${summary['budget_allocations']['wants']:,.2f} (Spent: ${summary['current_spending']['wants']:,.2f}, Remaining: ${summary['remaining_budget']['wants']:,.2f})
            - Savings Goal: ${summary['budget_allocations']['savings']:,.2f} (Saved: ${summary['current_spending']['savings']:,.2f}, {'Exceeded by' if summary['remaining_budget']['savings'] > 0 else 'Remaining'}: ${abs(summary['remaining_budget']['savings']):,.2f})

            Top Spending Categories:
            {json.dumps(dict(sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)[:10]), indent=2) if category_breakdown else 'No categories yet'}

User Question: {message}

Please answer the user's question using the above context from their uploaded financial data."""
            
            # Use the chatbot's chat method with enhanced context
            response = chatbot.chat(context)
            
        except Exception as context_error:
            # If context gathering fails, still try to chat without context
            print(f"Warning: Could not gather context: {str(context_error)}")
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
