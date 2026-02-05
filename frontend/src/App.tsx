import { Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import ModeSelectPage from './pages/ModeSelectPage'
import CouncilPage from './pages/CouncilPage'

function App() {
  return (
    <div className="min-h-screen bg-slate-900">
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/start" element={<ModeSelectPage />} />
        <Route path="/council/:sessionId" element={<CouncilPage />} />
      </Routes>
    </div>
  )
}

export default App
