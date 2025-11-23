import React, { useState, useRef, useEffect } from 'react';
import { Upload, Send, DollarSign, FileText, X, TrendingUp, LogOut } from 'lucide-react';
import { uploadFile, analyzeSpending } from '../services/api';

export default function FinancialChatbot({ user, onLogout }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m your financial assistant. Upload your bank statements (PDF, Excel, or CSV) and ask me anything about your spending, budgeting, or financial insights.',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    const validTypes = [
      'application/pdf',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/csv'
    ];

    const validFiles = files.filter(file => 
      validTypes.includes(file.type) || file.name.endsWith('.csv')
    );

    if (validFiles.length === 0) {
      alert('Please upload PDF, Excel, or CSV files only.');
      return;
    }

    setIsProcessing(true);
    
    try {
      // Upload each file to the backend
      const uploadPromises = validFiles.map(file => uploadFile(file, sessionId));
      const uploadResults = await Promise.all(uploadPromises);
      
      // Store session ID from first upload if not set
      if (!sessionId && uploadResults.length > 0 && uploadResults[0].session_id) {
        setSessionId(uploadResults[0].session_id);
      }
      
      // Store file info with backend file_id
      const newFiles = uploadResults.map((result, index) => ({
        id: result.file_id,
        name: result.filename,
        size: (validFiles[index].size / 1024).toFixed(2) + ' KB',
        type: validFiles[index].type.includes('pdf') ? 'PDF' : 
              validFiles[index].type.includes('sheet') || validFiles[index].type.includes('excel') ? 'Excel' : 'CSV',
        rows: result.rows,
        columns: result.columns
      }));

      setUploadedFiles([...uploadedFiles, ...newFiles]);
      
      const totalRows = uploadResults.reduce((sum, r) => sum + r.rows, 0);
      setMessages([...messages, {
        role: 'assistant',
        content: `I've successfully processed ${validFiles.length} file(s) with ${totalRows} total transactions. I can now answer questions about your transactions, spending patterns, and help you with budgeting insights. What would you like to know?`,
        timestamp: new Date()
      }]);
    } catch (error) {
      console.error('File upload error:', error); // Debug logging
      setMessages([...messages, {
        role: 'assistant',
        content: `Error processing files: ${error.message}. Please try again.`,
        timestamp: new Date()
      }]);
    } finally {
      setIsProcessing(false);
    }

    e.target.value = '';
  };

  const removeFile = (fileId) => {
    setUploadedFiles(uploadedFiles.filter(f => f.id !== fileId));
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages([...messages, userMessage]);
    setInput('');
    setIsProcessing(true);

    try {
      // Get file IDs from uploaded files
      const fileIds = uploadedFiles.map(f => f.id);
      
      if (fileIds.length === 0) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'Please upload a financial statement first before asking questions.',
          timestamp: new Date()
        }]);
        setIsProcessing(false);
        return;
      }
      
      if (!sessionId) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'Session error. Please upload your files again.',
          timestamp: new Date()
        }]);
        setIsProcessing(false);
        return;
      }
      
      // Call backend analysis function
      const result = await analyzeSpending(input, fileIds, sessionId);
      
      const assistantMessage = {
        role: 'assistant',
        content: result.response,
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Analysis error:', error); // Debug logging
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}. Please try again.`,
        timestamp: new Date()
      }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickQuestions = [
    "What did I spend the most on?",
    "Show my monthly budget",
    "Analyze my spending trends",
    "List recurring payments"
  ];

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 backdrop-blur-sm border-b border-purple-500/20 p-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-purple-500 to-pink-500 p-2 rounded-lg">
              <DollarSign className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Financial Assistant</h1>
              <p className="text-sm text-purple-300">AI-Powered Budget Analysis</p>
            </div>
          </div>

          {/* Hi User */}
          {user && (
            <span className="text-sm text-purple-200 flex items-center">
              Hi, <span className="font-semibold ml-1">{user.name}</span>
            </span>
          )}

          {/* Logout Button */}
          {onLogout && (
            <button
              onClick={onLogout}
              className="flex items-center gap-2 text-purple-200 hover:text-purple-100 text-sm transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          )}

          {/* Upload Button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
            disabled={isProcessing}
          >
            <Upload className="w-4 h-4" />
            Upload Statements
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.csv,.xls,.xlsx"
            onChange={handleFileUpload}
            className="hidden"
          />
        </div>


      </div>

      <div className="flex-1 overflow-hidden flex max-w-6xl w-full mx-auto">
        {/* Sidebar - Uploaded Files */}
        <div className="w-64 bg-slate-800/30 backdrop-blur-sm border-r border-purple-500/20 p-4 overflow-y-auto">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Uploaded Files ({uploadedFiles.length})
          </h2>
          
          {uploadedFiles.length === 0 ? (
            <p className="text-purple-300/60 text-sm">No files uploaded yet</p>
          ) : (
            <div className="space-y-2">
              {uploadedFiles.map(file => (
                <div key={file.id} className="bg-slate-700/50 p-3 rounded-lg group">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm font-medium truncate">{file.name}</p>
                      <p className="text-purple-300/60 text-xs mt-1">{file.type} • {file.size}</p>
                    </div>
                    <button
                      onClick={() => removeFile(file.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-4 h-4 text-red-400 hover:text-red-300" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Quick Stats */}
          <div className="mt-6 space-y-3">
            <div className="bg-gradient-to-br from-purple-600/20 to-pink-600/20 p-3 rounded-lg border border-purple-500/30">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-4 h-4 text-purple-300" />
                <span className="text-purple-200 text-xs font-medium">Quick Insights</span>
              </div>
              <p className="text-white text-sm">Upload statements to see your financial overview</p>
            </div>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-2xl rounded-2xl p-4 ${
                    message.role === 'user'
                      ? 'bg-gradient-to-br from-purple-600 to-pink-600 text-white'
                      : 'bg-slate-800/50 backdrop-blur-sm text-white border border-purple-500/20'
                  }`}
                >
                  <p className="text-sm leading-relaxed">{message.content}</p>
                  <p className="text-xs mt-2 opacity-60">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
            
            {isProcessing && (
              <div className="flex justify-start">
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-4 border border-purple-500/20">
                  <div className="flex gap-2">
                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Questions */}
          {messages.length <= 2 && (
            <div className="px-6 pb-4">
              <p className="text-purple-300 text-sm mb-3">Try asking:</p>
              <div className="grid grid-cols-2 gap-2">
                {quickQuestions.map((question, index) => (
                  <button
                    key={index}
                    onClick={() => setInput(question)}
                    className="text-left text-sm bg-slate-800/50 hover:bg-slate-700/50 text-purple-200 p-3 rounded-lg transition-colors border border-purple-500/20"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input Area */}
          <div className="p-6 bg-slate-800/30 backdrop-blur-sm border-t border-purple-500/20">
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about your spending, budgets, or financial goals..."
                className="flex-1 bg-slate-700/50 text-white placeholder-purple-300/40 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500 border border-purple-500/20"
                disabled={isProcessing}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isProcessing}
                className="bg-gradient-to-br from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed text-white p-3 rounded-xl transition-all"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}