import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { Toaster } from 'sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import Navbar from './components/Navbar'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import HistoryResults from './pages/HistoryResults'
import NotFound from './pages/NotFound'
import AgentAnalyze from './pages/AgentAnalyze'

export default function App() {
  return (
    <AuthProvider>
      <TooltipProvider>
        <Navbar />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/results/:id" element={<HistoryResults />} />
          <Route path="/agent" element={<AgentAnalyze />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
        <Toaster position="bottom-left" />
      </TooltipProvider>
    </AuthProvider>
  )
}

