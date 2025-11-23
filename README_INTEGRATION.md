# Backend Integration Guide

## Overview
This guide explains how to run the integrated financial chatbot with both frontend (React) and backend (Flask/Python).

## Architecture
- **Frontend**: React app running on `http://127.0.0.1:5173` (Vite dev server)
- **Backend**: Flask API running on `http://127.0.0.1:5000`
- **Files**:
  - `financial-chatbot/src/backend/app.py` - Flask API server
  - `financial-chatbot/src/backend/pdfconverter.py` - File processing logic
  - `financial-chatbot/src/backend/financial_chatbot.py` - Chatbot logic with Groq AI

## Setup Instructions

### 1. Backend Setup

```bash
# Navigate to project root
cd c:\Users\Mitsy\itcs6190\AI-Financial-chatbot

# Install Python dependencies
pip install -r requirements.txt

# Start the Flask backend
cd financial-chatbot/src/backend
python app.py
```

The backend will start on `http://127.0.0.1:5000`

### 2. Frontend Setup

```bash
# Open a new terminal
cd c:\Users\Mitsy\itcs6190\AI-Financial-chatbot\financial-chatbot

# Start the React dev server
npm run dev
```

The frontend will start on `http://127.0.0.1:5173`

### 3. Access the Application

Open your browser and navigate to: `http://127.0.0.1:5173`

## API Endpoints

### POST /api/upload
Upload financial documents (PDF, Excel, CSV)
- **Body**: FormData with `file` and `session_id`
- **Response**: File statistics and success message

### POST /api/chat
Send chat messages to the AI assistant
- **Body**: `{ "message": "your question", "session_id": "session_id" }`
- **Response**: AI-generated response

### POST /api/set-income
Set monthly income for budget calculations
- **Body**: `{ "income": 5000, "session_id": "session_id" }`
- **Response**: Confirmation message

### POST /api/add-transaction
Add a new transaction
- **Body**: `{ "amount": 50, "description": "Coffee", "session_id": "session_id" }`
- **Response**: Updated budget analysis

### GET /api/summary
Get budget summary
- **Query Params**: `session_id`
- **Response**: Complete budget breakdown

### GET /api/initial-analysis
Get initial budget analysis
- **Query Params**: `session_id`
- **Response**: AI-generated budget analysis

## Features

1. **File Upload**: Upload PDF, Excel, or CSV bank statements
2. **Transaction Parsing**: Automatically extracts and standardizes transaction data
3. **AI Chat**: Ask questions about your spending patterns, budgets, and financial insights
4. **Budget Tracking**: Set income and track spending against budget goals
5. **Session Management**: Each user session maintains its own data

## Environment Variables

You can set the Groq API key as an environment variable:

```bash
set GROQ_API_KEY=your_api_key_here
```

Or it will use the default key in the code.

## Troubleshooting

### Backend not connecting
- Make sure Flask is running on port 5000
- Check that CORS is enabled in app.py
- Verify the API_BASE_URL in FinancialChatbot.jsx matches your backend URL

### File upload issues
- Ensure the `uploads` folder is created (app.py does this automatically)
- Check file types are supported: .pdf, .csv, .xls, .xlsx
- Verify file size is reasonable (< 10MB recommended)

### Chat not working
- Make sure you've uploaded a file first
- Check browser console for errors
- Verify Groq API key is valid

## Notes

- The backend logic in `pdfconverter.py` and `financial_chatbot.py` remains unchanged
- CORS is enabled for development (adjust for production)
- Session data is stored in memory (use Redis or database for production)
- Files are temporarily saved and then deleted after processing
