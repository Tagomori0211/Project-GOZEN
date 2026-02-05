import { useEffect, useState, useRef, useCallback } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'
import ChatMessage from '../components/ChatMessage'
import DecisionPanel from '../components/DecisionPanel'
import StatusTree from '../components/StatusTree'
import type {
  ChatMessage as ChatMessageType,
  DecisionOption,
  SessionPhase,
  CouncilMode,
  WSServerMessage,
} from '../types/council'

function CouncilPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const { mission, mode } = (location.state as { mission: string; mode: CouncilMode }) || {}

  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [phase, setPhase] = useState<SessionPhase>('idle')
  const [decisionOptions, setDecisionOptions] = useState<DecisionOption[]>([])
  const [isAwaitingDecision, setIsAwaitingDecision] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [result, setResult] = useState<{ approved: boolean; adopted: string | null } | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const hasStarted = useRef(false)

  // 自動スクロール
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // メッセージ追加ヘルパー
  const addMessage = useCallback((msg: Omit<ChatMessageType, 'id' | 'timestamp'>) => {
    setMessages(prev => [
      ...prev,
      {
        ...msg,
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date(),
      },
    ])
  }, [])

  // WebSocketメッセージハンドラ
  const handleMessage = useCallback((message: WSServerMessage) => {
    switch (message.type) {
      case 'PHASE':
        setPhase(message.phase)
        if (message.status === 'in_progress') {
          const phaseLabels: Record<string, string> = {
            proposal: '海軍参謀が提案を作成しています...',
            objection: '陸軍参謀が異議を検討しています...',
            merged: '書記が統合案を起草しています...',
            execution: '実行部隊が展開しています...',
          }
          if (phaseLabels[message.phase]) {
            addMessage({
              from: 'system',
              type: 'info',
              content: phaseLabels[message.phase],
            })
          }
        }
        break

      case 'PROPOSAL':
        addMessage({
          from: 'kaigun',
          type: 'proposal',
          content: message.content,
          fullText: message.fullText,
        })
        break

      case 'OBJECTION':
        addMessage({
          from: 'rikugun',
          type: 'objection',
          content: message.content,
          fullText: message.fullText,
        })
        break

      case 'MERGED':
        addMessage({
          from: 'shoki',
          type: 'merged',
          content: message.content,
          fullText: message.fullText,
        })
        break

      case 'AWAITING_DECISION':
        setDecisionOptions(message.options)
        setIsAwaitingDecision(true)
        addMessage({
          from: 'system',
          type: 'info',
          content: '国家元首による裁定をお待ちしています。',
        })
        break

      case 'COMPLETE':
        setIsComplete(true)
        setIsAwaitingDecision(false)
        setResult(message.result)

        const resultLabels: Record<string, string> = {
          kaigun: '海軍案が採択されました。',
          rikugun: '陸軍案が採択されました。',
          integrated: '統合案が採択されました。',
        }
        const resultMessage = message.result.approved
          ? resultLabels[message.result.adopted || ''] || '裁定が完了しました。'
          : '案は却下されました。'

        addMessage({
          from: 'genshu',
          type: 'decision',
          content: resultMessage,
        })
        break

      case 'ERROR':
        setPhase('error')
        addMessage({
          from: 'system',
          type: 'error',
          content: message.message,
        })
        break
    }
  }, [addMessage])

  const { isConnected, send, connect } = useWebSocket(sessionId, {
    onMessage: handleMessage,
    onOpen: () => {
      if (!hasStarted.current && mission) {
        hasStarted.current = true
        // 会議開始メッセージ追加
        addMessage({
          from: 'genshu',
          type: 'info',
          content: `任務: ${mission}`,
        })
        // 会議開始を送信
        send({ type: 'START', mission, mode: mode || 'council' })
      }
    },
    onClose: () => {
      if (!isComplete) {
        addMessage({
          from: 'system',
          type: 'error',
          content: '接続が切断されました。',
        })
      }
    },
  })

  // 接続開始
  useEffect(() => {
    if (!mission) {
      navigate('/')
      return
    }
    connect()
  }, [connect, mission, navigate])

  // 裁定送信
  const handleDecision = (choice: number) => {
    send({ type: 'DECISION', choice })
    setIsAwaitingDecision(false)

    const choiceLabels: Record<number, string> = {
      1: '海軍案を採択',
      2: '陸軍案を採択',
      3: '統合案を作成',
      4: '却下',
    }

    addMessage({
      from: 'genshu',
      type: 'decision',
      content: `裁定: ${choiceLabels[choice] || '不明'}`,
    })
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-900">
      {/* ヘッダー */}
      <header className="bg-slate-800 border-b border-slate-700 px-4 py-3">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="font-serif text-xl text-genshu-400">御前会議</h1>
            <span className="text-slate-500 text-sm">
              Session: {sessionId}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-slate-500 text-sm">
              {isConnected ? '接続中' : '切断'}
            </span>
          </div>
        </div>
      </header>

      {/* メインコンテンツ */}
      <div className="flex-1 flex max-w-6xl mx-auto w-full">
        {/* チャットエリア */}
        <main className="flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        </main>

        {/* サイドバー */}
        <aside className="w-64 border-l border-slate-700 p-4 hidden md:block">
          <StatusTree phase={phase} mode={mode || 'council'} />

          {/* 結果サマリー */}
          {isComplete && result && (
            <div className="mt-4 p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
              <h3 className="text-sm font-medium text-slate-400 mb-2">結果</h3>
              <div className={`text-lg font-medium ${result.approved ? 'text-green-400' : 'text-red-400'}`}>
                {result.approved ? '承認' : '却下'}
              </div>
              {result.adopted && (
                <div className="text-sm text-slate-400 mt-1">
                  採択: {result.adopted === 'kaigun' ? '海軍案' :
                         result.adopted === 'rikugun' ? '陸軍案' :
                         result.adopted === 'integrated' ? '統合案' : result.adopted}
                </div>
              )}

              <button
                onClick={() => navigate('/')}
                className="mt-4 w-full py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm rounded transition-colors"
              >
                新しい会議を始める
              </button>
            </div>
          )}
        </aside>
      </div>

      {/* 裁定パネル */}
      {isAwaitingDecision && (
        <DecisionPanel
          options={decisionOptions}
          onDecide={handleDecision}
        />
      )}
    </div>
  )
}

export default CouncilPage
