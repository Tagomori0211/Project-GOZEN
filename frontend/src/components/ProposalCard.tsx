import { useState } from 'react'
import type { Proposal } from '../types/council'

interface ProposalCardProps {
  proposal: Proposal
  fullText?: string
}

function ProposalCard({ proposal, fullText }: ProposalCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="space-y-3">
      {/* タイトルとサマリー */}
      <div>
        <h3 className="font-medium text-lg text-slate-200 mb-1">{proposal.title}</h3>
        <p className="text-slate-400">{proposal.summary}</p>
      </div>

      {/* 主要ポイント */}
      {proposal.key_points && proposal.key_points.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-slate-400 mb-2">主要ポイント</h4>
          <ul className="space-y-1">
            {proposal.key_points.map((point, index) => (
              <li key={index} className="flex items-start gap-2 text-slate-300">
                <span className="text-genshu-500 mt-1">•</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 全文展開 */}
      {fullText && (
        <div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-genshu-400 hover:text-genshu-300 flex items-center gap-1"
          >
            <span>{isExpanded ? '▼' : '▶'}</span>
            <span>{isExpanded ? '詳細を閉じる' : '詳細を表示'}</span>
          </button>

          {isExpanded && (
            <div className="mt-3 p-4 bg-slate-800/50 rounded-lg border border-slate-700 overflow-auto max-h-96">
              <pre className="text-sm text-slate-300 whitespace-pre-wrap font-sans">
                {fullText}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ProposalCard
