import type { ChatMessage as ChatMessageType } from '../types/council'
import ProposalCard from './ProposalCard'
import Decree from './Decree'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface ChatMessageProps {
  message: ChatMessageType
}

function ChatMessage({ message }: ChatMessageProps) {
  const { from, type, content, fullText } = message

  // アイコンとカラー設定
  const config = {
    kaigun: {
      icon: '⚓',
      label: '海軍参謀',
      bgColor: 'bg-kaigun-900/50',
      borderColor: 'border-kaigun-700',
      iconBg: 'bg-kaigun-800',
    },
    rikugun: {
      icon: '🎖️',
      label: '陸軍参謀',
      bgColor: 'bg-rikugun-900/50',
      borderColor: 'border-rikugun-700',
      iconBg: 'bg-rikugun-800',
    },
    shoki: {
      icon: '📜',
      label: '書記',
      bgColor: 'bg-genshu-900/50',
      borderColor: 'border-genshu-700',
      iconBg: 'bg-genshu-800',
    },
    genshu: {
      icon: '👑',
      label: '国家元首',
      bgColor: 'bg-genshu-900/50',
      borderColor: 'border-genshu-600',
      iconBg: 'bg-genshu-700',
    },
    system: {
      icon: '⚙️',
      label: 'システム',
      bgColor: 'bg-slate-800/50',
      borderColor: 'border-slate-700',
      iconBg: 'bg-slate-700',
    },
  }

  const { icon, label, bgColor, borderColor, iconBg } = (config as any)[from] || config.system

  // タイプラベル
  const typeLabels: Record<string, string> = {
    proposal: '提案',
    objection: '異議',
    merged: '統合案',
    validation: '妥当性検証',
    decision: '裁定',
    info: '情報',
    error: 'エラー',
    decree: '裁定通達',
  }

  return (
    <div className={`animate-slide-up p-4 rounded-lg border ${bgColor} ${borderColor} mb-4`}>
      {/* ヘッダー */}
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 ${iconBg} rounded-full flex items-center justify-center text-xl`}>
          {icon}
        </div>
        <div>
          <div className="font-medium text-slate-200">{label}</div>
          <div className="text-xs text-slate-500">{typeLabels[type] || type}</div>
        </div>
      </div>

      {/* コンテンツ */}
      <div className="text-slate-300 prose prose-invert max-w-none">
        {type === 'decree' && typeof content === 'object' && 'decree_text' in content ? (
          <Decree data={content as any} />
        ) : type === 'error' ? (
          <div className="text-red-400 bg-red-900/20 p-3 rounded">
            {typeof content === 'string' ? content : JSON.stringify(content)}
          </div>
        ) : typeof content === 'object' && ('title' in content || 'summary' in content || 'key_points' in content) ? (
          <ProposalCard proposal={content as any} fullText={fullText} />
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
          </ReactMarkdown>
        )}
      </div>
    </div>
  )
}

export default ChatMessage
