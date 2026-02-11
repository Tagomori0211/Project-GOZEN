import { Routes, Route } from 'react-router-dom'
import SessionStartPage from './pages/SessionStartPage'
import CouncilPage from './pages/CouncilPage'

function App() {
  return (
    <div className="min-h-screen bg-slate-900">
      <Routes>
        <Route path="/" element={<SessionStartPage />} />
        <Route path="/council/:sessionId" element={<CouncilPage />} />
      </Routes>
    </div>
  )
}

export default App
