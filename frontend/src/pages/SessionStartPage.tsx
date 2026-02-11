import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { CouncilMode } from '../types/council'

function SessionStartPage() {
    const navigate = useNavigate()
    // Mode selection is removed, defaulting to 'council'
    const mode: CouncilMode = 'council'
    const [securityLevel, setSecurityLevel] = useState<'public' | 'confidential' | 'mock'>('public')
    const [mission, setMission] = useState('')
    const [isLoading, setIsLoading] = useState(false)

    const handleStart = async () => {
        if (!mission.trim()) return

        setIsLoading(true)

        try {
            // Create Session
            const response = await fetch('/api/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ security_level: securityLevel })
            })
            const { session_id } = await response.json()

            // Navigate to Council Page
            navigate(`/council/${session_id}`, {
                state: { mission, mode, securityLevel },
            })
        } catch (error) {
            console.error('Failed to create session:', error)
            setIsLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-slate-900 p-4">
            <div className="w-full max-w-2xl animate-fade-in">
                {/* Header */}
                <h1 className="font-serif text-5xl text-genshu-400 text-center mb-4 tracking-widest">
                    御前会議
                </h1>
                <p className="text-slate-400 text-center mb-10 tracking-widest text-sm">
                    PROJECT GOZEN - STRATEGIC DECISION SYSTEM
                </p>

                {/* Mission Input */}
                <div className="mb-8">
                    <label className="block text-slate-400 text-xs mb-3 uppercase tracking-wider">Mission / Agenda</label>
                    <textarea
                        value={mission}
                        onChange={(e) => setMission(e.target.value)}
                        placeholder="議題を入力してください..."
                        rows={4}
                        className="w-full p-4 bg-slate-800/50 border border-slate-700/50 rounded-lg
                       text-slate-200 placeholder-slate-600
                       focus:outline-none focus:border-genshu-500/50 focus:ring-1 focus:ring-genshu-500/50
                       resize-none transition-all backdrop-blur-sm"
                    />
                </div>

                {/* Security Level */}
                <div className="mb-8 flex justify-end items-center gap-3">
                    <span className="text-[10px] text-slate-500 uppercase tracking-widest">Security Level:</span>
                    <div className="flex bg-slate-900/50 p-1 rounded-lg border border-slate-700/50 scale-90 origin-right">
                        <button
                            onClick={() => setSecurityLevel('public')}
                            className={`px-4 py-1 text-xs rounded transition-all ${securityLevel === 'public' ? 'bg-blue-500/10 text-blue-500 border border-blue-500/30' : 'text-slate-600 hover:text-slate-400'}`}
                        >
                            PUBLIC
                        </button>
                        <button
                            onClick={() => setSecurityLevel('confidential')}
                            className={`px-4 py-1 text-xs rounded transition-all ${securityLevel === 'confidential' ? 'bg-purple-500/10 text-purple-500 border border-purple-500/30' : 'text-slate-600 hover:text-slate-400'}`}
                        >
                            CONFIDENTIAL
                        </button>
                        <button
                            onClick={() => setSecurityLevel('mock')}
                            className={`px-4 py-1 text-xs rounded transition-all ${securityLevel === 'mock' ? 'bg-amber-500/10 text-amber-500 border border-amber-500/30' : 'text-slate-600 hover:text-slate-400'}`}
                        >
                            MOCK
                        </button>
                    </div>
                </div>

                {/* Start Button */}
                <button
                    onClick={handleStart}
                    disabled={!mission.trim() || isLoading}
                    className="w-full py-4 bg-gradient-to-r from-genshu-600 to-genshu-500 text-slate-900 font-bold text-lg rounded-lg
                     hover:from-genshu-500 hover:to-genshu-400 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-600
                     shadow-lg shadow-genshu-900/50 border border-genshu-400/20
                     transition-all active:scale-[0.99] focus:outline-none focus:ring-2 focus:ring-genshu-500/50"
                >
                    {isLoading ? 'SESSION INITIALIZING...' : '開廷'}
                </button>
            </div>
        </div>
    )
}

export default SessionStartPage
