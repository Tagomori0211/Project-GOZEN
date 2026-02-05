import type { SessionPhase } from '../types/council'

interface StatusTreeProps {
  phase: SessionPhase
  mode: 'council' | 'execute'
}

interface PhaseStatus {
  key: SessionPhase
  label: string
  icon: string
}

function StatusTree({ phase, mode }: StatusTreeProps) {
  const phases: PhaseStatus[] = [
    { key: 'proposal', label: '海軍提案', icon: '⚓' },
    { key: 'objection', label: '陸軍異議', icon: '🎖️' },
    { key: 'decision', label: '裁定', icon: '👑' },
    ...(mode === 'execute' ? [{ key: 'execution' as SessionPhase, label: '実行', icon: '⚔️' }] : []),
    { key: 'completed', label: '完了', icon: '✓' },
  ]

  const getPhaseState = (phaseKey: SessionPhase): 'pending' | 'active' | 'completed' => {
    const phaseOrder = phases.map(p => p.key)
    const currentIndex = phaseOrder.indexOf(phase)
    const targetIndex = phaseOrder.indexOf(phaseKey)

    if (phase === 'error') return 'pending'
    if (phase === 'merged') {
      // merged は decision と同時進行扱い
      if (phaseKey === 'decision' || phaseKey === 'merged') return 'active'
    }

    if (targetIndex < currentIndex) return 'completed'
    if (targetIndex === currentIndex) return 'active'
    return 'pending'
  }

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
      <h3 className="text-sm font-medium text-slate-400 mb-4">進行状況</h3>

      <div className="space-y-3">
        {phases.map((p, index) => {
          const state = getPhaseState(p.key)

          return (
            <div key={p.key} className="flex items-center gap-3">
              {/* 接続線 */}
              {index > 0 && (
                <div className="absolute -mt-6 ml-4 w-px h-3 bg-slate-600" />
              )}

              {/* ステータスアイコン */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm
                  ${state === 'completed' ? 'bg-green-800 text-green-200' :
                    state === 'active' ? 'bg-genshu-600 text-genshu-100 animate-pulse' :
                    'bg-slate-700 text-slate-500'
                  }`}
              >
                {state === 'completed' ? '✓' : p.icon}
              </div>

              {/* ラベル */}
              <span
                className={`text-sm
                  ${state === 'completed' ? 'text-slate-400' :
                    state === 'active' ? 'text-slate-200 font-medium' :
                    'text-slate-500'
                  }`}
              >
                {p.label}
              </span>

              {/* ローディングインジケーター */}
              {state === 'active' && (
                <span className="text-xs text-genshu-400">処理中...</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default StatusTree
