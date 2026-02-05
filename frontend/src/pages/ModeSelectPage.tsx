import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { CouncilMode } from '../types/council'

function ModeSelectPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<CouncilMode>('council')
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
      })
      const { session_id } = await response.json()

      // 会議ページへ遷移（missionとmodeをstateで渡す）
      navigate(`/council/${session_id}`, {
        state: { mission, mode },
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

        {/* モード選択 */}
        <div className="mb-8">
          <label className="block text-slate-400 text-sm mb-3">作戦形式</label>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => setMode('council')}
              className={`p-4 border-2 rounded-lg text-left transition-all
                ${mode === 'council'
                  ? 'border-genshu-500 bg-genshu-500/10'
                  : 'border-slate-700 hover:border-slate-600'
                }`}
            >
              <div className="font-medium text-slate-200 mb-1">会議モード</div>
              <div className="text-sm text-slate-400">
                海軍参謀 vs 陸軍参謀の討議のみ
              </div>
            </button>

            <button
              onClick={() => setMode('execute')}
              className={`p-4 border-2 rounded-lg text-left transition-all
                ${mode === 'execute'
                  ? 'border-genshu-500 bg-genshu-500/10'
                  : 'border-slate-700 hover:border-slate-600'
                }`}
            >
              <div className="font-medium text-slate-200 mb-1">作戦実行モード</div>
              <div className="text-sm text-slate-400">
                討議後、実行部隊を展開
              </div>
            </button>
          </div>
        </div>

        {/* 任務入力 */}
        <div className="mb-8">
          <label className="block text-slate-400 text-sm mb-3">任務</label>
          <textarea
            value={mission}
            onChange={(e) => setMission(e.target.value)}
            placeholder="任務を入力してください..."
            rows={5}
            className="w-full p-4 bg-slate-800 border border-slate-700 rounded-lg
                       text-slate-200 placeholder-slate-500
                       focus:outline-none focus:border-genshu-500 focus:ring-1 focus:ring-genshu-500
                       resize-none transition-colors"
          />
        </div>

        {/* 開始ボタン */}
        <button
          onClick={handleStart}
          disabled={!mission.trim() || isLoading}
          className="w-full py-4 bg-genshu-500 text-slate-900 font-medium text-lg rounded-lg
                     hover:bg-genshu-400 disabled:bg-slate-700 disabled:text-slate-500
                     transition-colors focus:outline-none focus:ring-2 focus:ring-genshu-500 focus:ring-offset-2 focus:ring-offset-slate-900"
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
