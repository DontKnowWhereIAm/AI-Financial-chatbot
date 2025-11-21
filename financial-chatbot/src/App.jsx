// src/App.jsx
import React, { useState } from 'react';
import Login from './components/Login';
import FinancialChatbot from './components/FinancialChatbot';

function App() {
  const [user, setUser] = useState(null);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    setUser(null);
  };

  return (
    <>
      {!user ? (
        <Login onLogin={handleLogin} />
      ) : (
        <FinancialChatbot user={user} onLogout={handleLogout} />
      )}
    </>
  );
}

export default App;
