"""
Example Python Backend for Financial Chatbot Integration

This is a template showing how to integrate your existing Python functions.
Replace 'your_module' with your actual module name and adjust function calls as needed.

Installation:
    pip install flask flask-cors pandas
    # OR
    pip install fastapi uvicorn python-multipart pandas

Run:
    python backend_example.py
"""

# ============================================================================
# OPTION 1: Using Flask
# ============================================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
# Import your existing functions here:
# from your_module import convert_to_dataframe, analyze_spending

app = Flask(__name__)
CORS(app)  # Allow React frontend to make requests

# In-memory storage (use database in production)
processed_files = {}

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Endpoint that calls your convert_to_dataframe() function
    
    Frontend sends: FormData with file
    Backend calls: convert_to_dataframe(file)
    Backend returns: {file_id, filename, rows, columns}
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # ============================================================
        # CALL YOUR EXISTING FUNCTION HERE
        # ============================================================
        # df = convert_to_dataframe(file)
        # 
        # If your function signature is different, adjust accordingly:
        # - convert_to_dataframe(file_path) → save file first
        # - convert_to_dataframe(file_bytes, filename) → read file bytes
        # ============================================================
        
        # Example placeholder (replace with your actual function call):
        # df = convert_to_dataframe(file)
        
        # For demonstration, creating a dummy DataFrame:
        df = pd.DataFrame({'amount': [100, 200], 'category': ['food', 'transport']})
        
        # Store the dataframe (convert to dict for JSON)
        file_id = str(hash(file.filename + str(pd.Timestamp.now())))
        processed_files[file_id] = {
            'data': df.to_dict('records'),  # Convert DataFrame to list of dicts
            'columns': list(df.columns),
            'filename': file.filename
        }
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': file.filename,
            'rows': len(df),
            'columns': list(df.columns),
            'message': 'File processed successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Endpoint that calls your analyze_spending() function
    
    Frontend sends: {question: "...", file_ids: [...]}
    Backend calls: analyze_spending(dataframe, question)
    Backend returns: {response: "..."}
    """
    data = request.json
    question = data.get('question')
    file_ids = data.get('file_ids', [])
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    if not file_ids:
        return jsonify({'error': 'No files selected'}), 400
    
    try:
        # Combine data from all selected files
        all_data = []
        for file_id in file_ids:
            if file_id in processed_files:
                all_data.extend(processed_files[file_id]['data'])
        
        if not all_data:
            return jsonify({'error': 'No data found for selected files'}), 404
        
        # Convert back to DataFrame
        df = pd.DataFrame(all_data)
        
        # ============================================================
        # CALL YOUR EXISTING FUNCTION HERE
        # ============================================================
        # analysis_result = analyze_spending(df, question)
        # 
        # If your function signature is different, adjust accordingly:
        # - analyze_spending(df) → might need to extract question differently
        # - analyze_spending(df, question, user_id) → add user context
        # ============================================================
        
        # Example placeholder (replace with your actual function call):
        # analysis_result = analyze_spending(df, question)
        
        # For demonstration, creating a dummy response:
        analysis_result = f"Based on your {len(df)} transactions, I found that your question '{question}' relates to your spending patterns. This is a placeholder response - replace with your actual analyze_spending() function output."
        
        return jsonify({
            'success': True,
            'response': analysis_result,
            'message': 'Analysis complete'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Backend is running'}), 200

if __name__ == '__main__':
    print("Starting Flask server on http://localhost:5000")
    print("Make sure your React frontend is running on http://localhost:5173")
    app.run(port=5000, debug=True)


# ============================================================================
# OPTION 2: Using FastAPI (Alternative - uncomment to use)
# ============================================================================

"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
# from your_module import convert_to_dataframe, analyze_spending

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

processed_files = {}

class AnalyzeRequest(BaseModel):
    question: str
    file_ids: list[str]

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        # df = convert_to_dataframe(contents, file.filename)
        df = pd.DataFrame({'amount': [100, 200], 'category': ['food', 'transport']})
        
        file_id = str(hash(file.filename + str(pd.Timestamp.now())))
        processed_files[file_id] = {
            'data': df.to_dict('records'),
            'columns': list(df.columns),
            'filename': file.filename
        }
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "rows": len(df),
            "columns": list(df.columns),
            "message": "File processed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        all_data = []
        for file_id in request.file_ids:
            if file_id in processed_files:
                all_data.extend(processed_files[file_id]['data'])
        
        if not all_data:
            raise HTTPException(status_code=404, detail="No data found")
        
        df = pd.DataFrame(all_data)
        # analysis_result = analyze_spending(df, request.question)
        analysis_result = f"Analysis for: {request.question}"
        
        return {
            "success": True,
            "response": analysis_result,
            "message": "Analysis complete"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
"""

