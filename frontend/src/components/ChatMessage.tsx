import type { ChatMessage as ChatMessageType } from '../types/council'
import ProposalCard from './ProposalCard'
import OfficialDocument from './OfficialDocument'
import PreMortemPanel from './PreMortemPanel'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface ChatMessageProps {
  message: ChatMessageType
}

function ChatMessage({ message }: ChatMessageProps) {
  let { from, type, content, fullText } = message

  // 裁定通達の場合、contentが文字列であればJSONとしてパースを試みる
  if (type === 'decree' && typeof content === 'string') {
    try {
      const parsed = JSON.parse(content)
      if (typeof parsed === 'object' && parsed !== null) {
        content = parsed
      }
    } catch (e) {
      // パース失敗時はそのまま
    }
  }

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
      bgColor: 'bg-shoki-900/50',
      borderColor: 'border-shoki-700',
      iconBg: 'bg-shoki-800',
    },
    genshu: {
      icon: '👑',
      label: '国家元首',
      bgColor: 'bg-amber-900/40',
      borderColor: 'border-amber-500',
      iconBg: 'bg-amber-600',
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
      <div className="text-slate-300 max-w-none">
        {type === 'decree' ? (
          <OfficialDocument
            markdown={typeof content === 'object' && content !== null && 'markdown_content' in content ? (content as any).markdown_content : (typeof content === 'string' ? content : JSON.stringify(content))}
            timestamp={(message as any).timestamp}
          />
        ) : type === 'error' ? (
          <div className="text-red-400 bg-red-900/20 p-3 rounded">
            {typeof content === 'string' ? content : JSON.stringify(content)}
          </div>
        ) : type === 'loading' ? (
          <div className="flex items-center gap-3 text-slate-300 p-4">
            <span>{typeof content === 'string' ? content : ''}</span>
            <div className={`animate-spin h-5 w-5 border-2 border-current border-t-transparent rounded-full ${from === 'kaigun' ? 'text-blue-400' : from === 'rikugun' ? 'text-green-400' : 'text-slate-400'}`} />
          </div>
        ) : type === 'pre_mortem' ? (
          <div className="w-full">
            <PreMortemPanel data={content as any} />
          </div>
        ) : typeof content === 'object' && content !== null && ('title' in content || 'summary' in content || 'key_points' in content) ? (
          <div className="p-4">
            <ProposalCard proposal={content as any} fullText={fullText} />
          </div>
        ) : (
          <div className="prose prose-invert max-w-none p-4">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatMessage
