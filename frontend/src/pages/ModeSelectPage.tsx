import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { CouncilMode } from '../types/council'

function ModeSelectPage() {
  const navigate = useNavigate()
  const [mode] = useState<CouncilMode>('council')
  const [securityLevel, setSecurityLevel] = useState<'public' | 'mock'>('mock')
  const [mission, setMission] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleStart = async () => {
    if (!mission.trim()) return

    setIsLoading(true)

    try {
      // セッション作成
      const response = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ security_level: securityLevel })
      })
      const { session_id } = await response.json()

      // 会議ページへ遷移（missionとmodeをstateで渡す）
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
        {/* ヘッダー */}
        <h1 className="font-serif text-4xl text-genshu-400 text-center mb-8">
          作戦立案
        </h1>

        {/* 任務入力 */}
        <div className="mb-8">
          <label className="block text-slate-400 text-sm mb-3">議題</label>
          <textarea
            value={mission}
            onChange={(e) => setMission(e.target.value)}
            placeholder="議題を入力してください..."
            rows={5}
            className="w-full p-4 bg-slate-800 border border-slate-700 rounded-lg
                       text-slate-200 placeholder-slate-500
                       focus:outline-none focus:border-genshu-500 focus:ring-1 focus:ring-genshu-500
                       resize-none transition-colors"
          />
        </div>

        {/* モード・セキュリティ設定 */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div>
            <label className="block text-slate-400 text-sm mb-3">会議モード</label>
            <div className="flex bg-slate-800 p-1 rounded-lg border border-slate-700">
              <button
                className={`flex-1 py-2 text-sm rounded ${mode === 'council' ? 'bg-genshu-500 text-slate-900 shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
              >
                通常会議
              </button>
              <button
                disabled
                className="flex-1 py-2 text-sm text-slate-600 cursor-not-allowed"
              >
                ドライラン
              </button>
            </div>
          </div>
          <div>
            <label className="block text-slate-400 text-sm mb-3">セキュリティ</label>
            <div className="flex bg-slate-800 p-1 rounded-lg border border-slate-700">
              <button
                onClick={() => setSecurityLevel('mock')}
                className={`flex-1 py-2 text-sm rounded transition-all ${securityLevel === 'mock' ? 'bg-amber-500/20 text-amber-500 border border-amber-500/50' : 'text-slate-400 hover:text-slate-200'}`}
              >
                MOCK
              </button>
              <button
                onClick={() => setSecurityLevel('public')}
                className={`flex-1 py-2 text-sm rounded transition-all ${securityLevel === 'public' ? 'bg-blue-500/20 text-blue-500 border border-blue-500/50' : 'text-slate-400 hover:text-slate-200'}`}
              >
                PUBLIC
              </button>
            </div>
          </div>
        </div>

        {/* 開始ボタン */}
        <button
          onClick={handleStart}
          disabled={!mission.trim() || isLoading}
          className="w-full py-4 bg-genshu-500 text-slate-900 font-medium text-lg rounded-lg
                     hover:bg-genshu-400 disabled:bg-slate-700 disabled:text-slate-500
                     shadow-lg shadow-genshu-500/20
                     transition-all active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-genshu-500 focus:ring-offset-2 focus:ring-offset-slate-900"
        >
          {isLoading ? '準備中...' : '会議開始'}
        </button>

        {/* 戻るリンク */}
        <button
          onClick={() => navigate('/')}
          className="w-full mt-4 py-2 text-slate-500 hover:text-slate-400 transition-colors text-sm"
        >
          戻る
        </button>
      </div>
    </div>
  )
}

export default ModeSelectPage
