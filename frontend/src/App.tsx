import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { Toaster } from 'sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import Navbar from './components/Navbar'

const Landing = lazy(() => import('./pages/Landing'))
const Login = lazy(() => import('./pages/Login'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const HistoryResults = lazy(() => import('./pages/HistoryResults'))
const NotFound = lazy(() => import('./pages/NotFound'))
const Profile = lazy(() => import('./pages/Profile'))

function RouteFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center" aria-busy="true" aria-label="Loading page">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-300 border-t-brand" />
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <TooltipProvider>
        <Navbar />
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Navigate to="/login" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/results/:id" element={<HistoryResults />} />
            <Route path="/agent" element={<Navigate to="/" replace />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
        <Toaster position="bottom-left" />
      </TooltipProvider>
    </AuthProvider>
  )
}
