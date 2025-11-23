# Setup Instructions - Financial Chatbot Integration

## Overview

Your Python backend functions (`pdfconverter.py` and `financial_chatbot.py`) have been integrated with your React frontend through a Flask API server.

## Files Created/Modified

### Backend Files:
- ✅ `financial-chatbot/src/backend/app.py` - Flask API server
- ✅ `financial-chatbot/src/backend/pdfconverter.py` - Modified to work with Flask (removed Colab dependency)
- ✅ `financial-chatbot/src/backend/requirements.txt` - Python dependencies
- ✅ `financial-chatbot/src/backend/README.md` - Backend documentation

### Frontend Files:
- ✅ `financial-chatbot/src/services/api.js` - API service for React
- ✅ `financial-chatbot/src/components/FinancialChatbot.jsx` - Updated to use API calls

## Setup Steps

### 1. Install Python Dependencies

```bash
cd financial-chatbot/src/backend
pip install -r requirements.txt
```

### 2. Set Groq API Key (Optional)

The backend uses a default API key. To use your own:

**Option A: Environment Variable**
```bash
export GROQ_API_KEY="your_api_key_here"
```

**Option B: Edit app.py**
Edit line 25 in `financial-chatbot/src/backend/app.py`:
```python
GROQ_API_KEY = os.getenv('GROQ_API_KEY', 'your_api_key_here')
```

### 3. Start the Backend Server

```bash
cd financial-chatbot/src/backend
python app.py
```

You should see:
```
============================================================
Financial Chatbot Backend API
============================================================
Groq API Key: Set
Upload folder: /tmp
Starting server on http://localhost:5000
Make sure your React frontend is running on http://localhost:5173
============================================================
```

### 4. Start the Frontend (in a new terminal)

```bash
cd financial-chatbot
npm run dev
```

### 5. Test the Integration

1. Open `http://localhost:5173` in your browser
2. Upload a PDF, Excel, or CSV file
3. Ask a question like "What did I spend the most on?"

## How It Works

### File Upload Flow:
1. User uploads file in React frontend
2. Frontend sends file to `POST /api/upload`
3. Backend saves file temporarily
4. Backend calls `load_transactions_from_file()` from `pdfconverter.py`
5. Backend stores DataFrame and returns file metadata
6. Frontend displays file in the UI

### Analysis Flow:
1. User asks a question in React frontend
2. Frontend sends question + file IDs to `POST /api/analyze`
3. Backend retrieves stored DataFrames
4. Backend initializes `FinancialChatbot` with the data
5. Backend calls `chatbot.chat(question)` from `financial_chatbot.py`
6. Backend returns AI response
7. Frontend displays response in chat

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/upload` - Upload and process files
- `POST /api/analyze` - Analyze spending and answer questions
- `POST /api/initialize` - Initialize chatbot with income/budget (optional)
- `POST /api/summary` - Get budget summary (optional)

## Troubleshooting

### Backend won't start
- Check if port 5000 is already in use
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check Python version (requires Python 3.7+)

### CORS errors
- Make sure `flask-cors` is installed
- Verify frontend is running on `http://localhost:5173`

### File upload fails
- Check file size (max 16MB)
- Verify file is PDF, CSV, or Excel format
- Check backend logs for error messages

### Analysis returns errors
- Verify Groq API key is set correctly
- Check that files were uploaded successfully
- Review backend console for detailed error messages

### Frontend can't connect
- Verify backend is running on port 5000
- Check browser console for network errors
- Verify `API_BASE_URL` in `api.js` is `http://localhost:5000/api`

## Next Steps

1. Test with your actual financial statement files
2. Customize income/budget settings using `/api/initialize` endpoint
3. Add error handling improvements as needed
4. Consider adding database storage for production use

## Notes

- Session data is stored in memory (lost on server restart)
- Files are temporarily stored and cleaned up after processing
- The chatbot automatically estimates income from deposits if not explicitly set
- All existing logic in your Python files remains unchanged

