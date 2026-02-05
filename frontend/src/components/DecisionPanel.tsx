import type { DecisionOption } from '../types/council'

interface DecisionPanelProps {
  options: DecisionOption[]
  onDecide: (choice: number) => void
  disabled?: boolean
  mode?: 'decision' | 'merge_decision'
  loopCount?: number
}

function DecisionPanel({ options, onDecide, disabled, mode = 'decision', loopCount }: DecisionPanelProps) {
  // 通常の裁定モード
  const getButtonStyle = (value: number) => {
    if (mode === 'merge_decision') {
      // 折衷案の採用/却下
      switch (value) {
        case 1: // 採用
          return 'border-green-600 hover:bg-green-900/50 hover:border-green-500'
        case 2: // 却下
          return 'border-red-600 hover:bg-red-900/50 hover:border-red-500'
        default:
          return 'border-slate-600 hover:bg-slate-800/50 hover:border-slate-500'
      }
    }

    // 通常の裁定
    switch (value) {
      case 1: // 海軍案
        return 'border-kaigun-600 hover:bg-kaigun-900/50 hover:border-kaigun-500'
      case 2: // 陸軍案
        return 'border-rikugun-600 hover:bg-rikugun-900/50 hover:border-rikugun-500'
      case 3: // 統合案
        return 'border-genshu-600 hover:bg-genshu-900/50 hover:border-genshu-500'
      case 4: // 却下
        return 'border-red-800 hover:bg-red-900/50 hover:border-red-600'
      default:
        return 'border-slate-600 hover:bg-slate-800/50 hover:border-slate-500'
    }
  }

  const getIcon = (value: number) => {
    if (mode === 'merge_decision') {
      switch (value) {
        case 1: return '✓'
        case 2: return '↻'
        default: return '•'
      }
    }

    switch (value) {
      case 1: return '⚓'
      case 2: return '🎖️'
      case 3: return '🤝'
      case 4: return '✕'
      default: return '•'
    }
  }

  const title = mode === 'merge_decision'
    ? '折衷案の裁定'
    : '国家元首による裁定'

  const gridCols = mode === 'merge_decision'
    ? 'grid-cols-2'
    : 'grid-cols-2 md:grid-cols-4'

  return (
    <div className="bg-slate-800/80 backdrop-blur border-t border-slate-700 p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">👑</span>
          <span className="text-slate-400 text-sm">{title}</span>
          {loopCount && loopCount > 1 && (
            <span className="text-xs text-genshu-400 ml-2">
              (会議ループ {loopCount}回目)
            </span>
          )}
        </div>

        <div className={`grid ${gridCols} gap-3`}>
          {options.map((option) => (
            <button
              key={option.value}
              onClick={() => onDecide(option.value)}
              disabled={disabled}
              className={`p-3 border-2 rounded-lg transition-all text-left
                ${getButtonStyle(option.value)}
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                bg-slate-900/50`}
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">{getIcon(option.value)}</span>
                <span className="text-slate-200 text-sm font-medium">{option.label}</span>
              </div>
            </button>
          ))}
        </div>

        {mode === 'merge_decision' && (
          <div className="mt-3 text-xs text-slate-500">
            ※ 却下を選択すると、海軍参謀による妥当性検証が行われ、会議が継続します
          </div>
        )}
      </div>
    </div>
  )
}

export default DecisionPanel
