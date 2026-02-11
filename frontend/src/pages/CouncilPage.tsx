import { useEffect, useState, useRef, useCallback } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'
import ChatMessage from '../components/ChatMessage'
import DecisionPanel from '../components/DecisionPanel'
import PreMortemPanel from '../components/PreMortemPanel'
import StatusTree from '../components/StatusTree'
import ApprovedStamp from '../components/ApprovedStamp'
import type {
  ChatMessage as ChatMessageType,
  DecisionOption,
  SessionPhase,
  CouncilMode,
  WSServerMessage,
  PreMortemData,
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
  const [isAwaitingMergeDecision, setIsAwaitingMergeDecision] = useState(false)
  const [mergeDecisionOptions, setMergeDecisionOptions] = useState<DecisionOption[]>([])
  const [showApprovedStamp, setShowApprovedStamp] = useState(false)
  const [stampText, setStampText] = useState("承認")
  const [isComplete, setIsComplete] = useState(false)
  const [result, setResult] = useState<{ approved: boolean; adopted: string | null; loop_count?: number } | null>(null)
  const [loopCount, setLoopCount] = useState(1)

  // Pre-Mortem State
  const [isAwaitingPreMortemDecision, setIsAwaitingPreMortemDecision] = useState(false)
  const [preMortemOptions, setPreMortemOptions] = useState<DecisionOption[]>([])
  const [currentPreMortemData, setCurrentPreMortemData] = useState<PreMortemData | null>(null)

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
        // 判定待ち状態の時はフェーズ更新を無視する（上書き防止）
        setPhase(prev => {
          if (isAwaitingMergeDecision && message.phase === 'merged' && message.status === 'completed') {
            return prev
          }
          return message.phase
        })

        if (message.status === 'in_progress') {
          const phaseLabels: Record<string, string> = {
            merged: '書記が統合案を起草しています...',
            validation: '海軍参謀が妥当性を検証しています...',
            execution: '実行部隊が展開しています...',
          }

          if (message.phase === 'proposal') {
            setMessages(prev => [...prev, {
              id: `loading-${Date.now()}`,
              from: 'kaigun',
              type: 'loading',
              content: '提案を作成しています...',
              timestamp: new Date()
            }])
          } else if (message.phase === 'objection') {
            setMessages(prev => [...prev, {
              id: `loading-${Date.now()}`,
              from: 'rikugun',
              type: 'loading',
              content: '異議を検討しています...',
              timestamp: new Date()
            }])
          } else if (message.phase === 'final_notification') {
            setMessages(prev => [...prev, {
              id: `loading-${Date.now()}`,
              from: 'shoki',
              type: 'loading',
              content: '公文書を発行しています...',
              timestamp: new Date()
            }])
          } else if (phaseLabels[message.phase]) {
            addMessage({
              from: 'system',
              type: 'info',
              content: phaseLabels[message.phase],
            })
          }
        }
        break

      case 'PROPOSAL':
        setMessages(prev => {
          // Loadingメッセージがあれば削除
          const last = prev[prev.length - 1];
          let newMsgs = [...prev];
          if (last && last.type === 'loading' && last.from === 'kaigun') {
            newMsgs.pop();
          }
          return [...newMsgs, {
            from: 'kaigun',
            type: 'proposal',
            content: message.content,
            fullText: message.fullText,
            id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            timestamp: new Date(),
          }]
        })
        break

      case 'OBJECTION':
        setMessages(prev => {
          // Loadingメッセージがあれば削除
          const last = prev[prev.length - 1];
          let newMsgs = [...prev];
          if (last && last.type === 'loading' && last.from === 'rikugun') {
            newMsgs.pop();
          }
          return [...newMsgs, {
            from: 'rikugun',
            type: 'objection',
            content: message.content,
            fullText: message.fullText,
            id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            timestamp: new Date(),
          }]
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

      case 'VALIDATION':
        addMessage({
          from: 'kaigun',
          type: 'validation',
          content: message.content,
          fullText: message.fullText,
        })
        break

      case 'PRE_MORTEM':
        setCurrentPreMortemData(message.content)
        setMessages(prev => [...prev, {
          from: 'shoki',
          type: 'pre_mortem',
          content: message.content,
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
        }])
        break

      case 'AWAITING_DECISION':
        setDecisionOptions(message.options)
        setIsAwaitingDecision(true)
        setIsAwaitingMergeDecision(false)
        setIsAwaitingPreMortemDecision(false)
        if (message.loopCount) {
          setLoopCount(message.loopCount)
        }
        addMessage({
          from: 'system',
          type: 'info',
          content: loopCount > 1
            ? `会議ループ ${loopCount}回目: 国家元首による裁定をお待ちしています。`
            : '国家元首による裁定をお待ちしています。',
        })
        break

      case 'AWAITING_MERGE_DECISION':
        {
          setMergeDecisionOptions(message.options)
          setIsAwaitingMergeDecision(true)
          setIsAwaitingDecision(false)
          setIsAwaitingPreMortemDecision(false)
          // 明示的にフェーズを更新してパネル表示を確実にトリガーする
          setPhase('merge_decision')

          addMessage({
            from: 'system',
            type: 'info',
            content: '折衷案の採用/却下を選択してください。',
          })
        }
        break

      case 'AWAITING_PREMORTEM_DECISION':
        setPreMortemOptions(message.options)
        setIsAwaitingPreMortemDecision(true)
        setIsAwaitingDecision(false)
        setIsAwaitingMergeDecision(false)
        addMessage({
          from: 'system',
          type: 'info',
          content: 'リスクを受容するか、再審議に戻るかを選択してください。',
        })
        break

      case 'APPROVED_STAMP':
        setShowApprovedStamp(true)
        setIsAwaitingMergeDecision(false)
        setIsAwaitingPreMortemDecision(false)
        break

      case 'INFO':
        if (message.from === 'shoki') {
          setMessages(prev => {
            const last = prev[prev.length - 1];
            let newMsgs = [...prev];
            if (last && last.type === 'loading' && last.from === 'shoki') {
              newMsgs.pop();
            }
            return [...newMsgs, {
              id: `loading-${Date.now()}`,
              from: 'shoki',
              type: 'loading',
              content: message.content,
              timestamp: new Date()
            }]
          })
        } else {
          addMessage({
            from: 'system',
            type: 'info',
            content: message.content,
          })
        }
        break

      case 'SHOKI_SUMMARY':
        setMessages(prev => {
          const last = prev[prev.length - 1];
          let newMsgs = [...prev];
          if (last && last.type === 'loading' && last.from === 'shoki') {
            newMsgs.pop();
          }
          return [...newMsgs, {
            from: 'shoki',
            type: 'decree',
            content: message.content,
            id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            timestamp: new Date(),
          }]
        })
        break

      case 'COMPLETE':
        setIsComplete(true)
        setIsAwaitingDecision(false)
        setIsAwaitingMergeDecision(false)
        setIsAwaitingPreMortemDecision(false)
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
          from: 'system',
          type: 'info',
          content: resultMessage,
        })

        if (message.result.approved) {
          // 承認スタンプ表示
          const stampLabels: Record<string, string> = {
            kaigun: '海軍案',
            rikugun: '陸軍案',
            integrated: '統合案',
          }
          setStampText(stampLabels[message.result.adopted || ''] || '承認')
          setShowApprovedStamp(true)
        }
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
  }, [addMessage, loopCount])

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

  // 折衷案の採用/却下送信
  const handleMergeDecision = (choice: number) => {
    send({ type: 'MERGE_DECISION', choice })
    setIsAwaitingMergeDecision(false)

    const choiceLabels: Record<number, string> = {
      1: '折衷案を採用',
      2: '折衷案を却下（妥当性検証へ）',
    }

    addMessage({
      from: 'genshu',
      type: 'decision',
      content: `裁定: ${choiceLabels[choice] || '不明'}`,
    })
  }

  // Pre-Mortem 決定送信
  const handlePreMortemDecision = (choice: number) => {
    send({ type: 'PREMORTEM_DECISION', choice })
    setIsAwaitingPreMortemDecision(false)

    const choiceLabels: Record<number, string> = {
      1: 'リスクを受容して採択',
      2: '再審議に戻る',
    }

    addMessage({
      from: 'genshu',
      type: 'decision',
      content: `決断: ${choiceLabels[choice] || '不明'}`,
    })
  }

  // 承認スタンプを閉じる
  const handleCloseStamp = () => {
    setShowApprovedStamp(false)
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
            {loopCount > 1 && (
              <span className="text-xs text-genshu-400 bg-genshu-900/30 px-2 py-1 rounded">
                ループ {loopCount}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={async () => {
                if (confirm('サーバーを終了しますか？\n終了後はポート9000が解放されます。')) {
                  try {
                    await fetch('/api/shutdown', { method: 'POST' })
                    alert('サーバーを終了しました。タブを閉じてください。')
                    window.close()
                  } catch (e) {
                    alert('終了エラー: ' + e)
                  }
                }
              }}
              className="px-3 py-1 text-xs bg-red-900/50 hover:bg-red-800 text-red-200 rounded border border-red-700 transition-colors mr-2"
            >
              終了
            </button>
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
              {result.loop_count && result.loop_count > 1 && (
                <div className="text-xs text-slate-500 mt-1">
                  会議ループ: {result.loop_count}回
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
          mode="decision"
          loopCount={loopCount}
        />
      )}

      {/* 折衷案採用/却下パネル */}
      {isAwaitingMergeDecision && (
        <DecisionPanel
          options={mergeDecisionOptions}
          onDecide={handleMergeDecision}
          mode="merge_decision"
        />
      )}

      {/* Pre-Mortem 決定パネル (Overlay) */}
      {isAwaitingPreMortemDecision && currentPreMortemData && (
        <div className="fixed inset-0 z-50 bg-slate-900/90 backdrop-blur-sm overflow-y-auto">
          <div className="min-h-screen flex items-center justify-center p-4">
            <PreMortemPanel
              data={currentPreMortemData}
              options={preMortemOptions}
              onDecide={handlePreMortemDecision}
            />
          </div>
        </div>
      )}

      {/* 承認スタンプ */}
      {showApprovedStamp && (
        <ApprovedStamp onClose={handleCloseStamp} text={stampText} />
      )}
    </div>
  )
}

export default CouncilPage
