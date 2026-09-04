import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Phase5Dashboard } from './pages/Phase5Dashboard';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#060911] text-slate-100 font-sans selection:bg-blue-500 selection:text-white">
        <Routes>
          <Route path="/" element={<Phase5Dashboard />} />
          <Route path="*" element={<Phase5Dashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
};

