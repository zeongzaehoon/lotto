import { createContext, useContext } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import FloatingLogPanel from './components/FloatingLogPanel';
import Dashboard from './pages/Dashboard';
import History from './pages/History';
import Statistics from './pages/Statistics';
import Prediction from './pages/Prediction';
import Training from './pages/Training';
import Collection from './pages/Collection';
import { useLogStream, type UseLogStreamReturn } from './hooks/useLogStream';

const LogStreamContext = createContext<UseLogStreamReturn | null>(null);
export const useGlobalLogStream = () => useContext(LogStreamContext)!;

function App() {
  const logStream = useLogStream();

  return (
    <LogStreamContext.Provider value={logStream}>
      <div style={{ paddingBottom: logStream.logs.length > 0 || logStream.isConnected ? 50 : 0 }}>
        <Navbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/history" element={<History />} />
          <Route path="/statistics" element={<Statistics />} />
          <Route path="/prediction" element={<Prediction />} />
          <Route path="/training" element={<Training />} />
          <Route path="/collection" element={<Collection />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
      <FloatingLogPanel stream={logStream} />
    </LogStreamContext.Provider>
  );
}

export default App;
