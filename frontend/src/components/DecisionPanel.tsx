import type { DecisionOption } from '../types/council'

interface DecisionPanelProps {
  options: DecisionOption[]
  onDecide: (choice: number) => void
  disabled?: boolean
}

function DecisionPanel({ options, onDecide, disabled }: DecisionPanelProps) {
  // 選択肢ごとのスタイル
  const getButtonStyle = (value: number) => {
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
    switch (value) {
      case 1: return '⚓'
      case 2: return '🎖️'
      case 3: return '🤝'
      case 4: return '✕'
      default: return '•'
    }
  }

  return (
    <div className="bg-slate-800/80 backdrop-blur border-t border-slate-700 p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">👑</span>
          <span className="text-slate-400 text-sm">国家元首による裁定</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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
      </div>
    </div>
  )
}

export default DecisionPanel
