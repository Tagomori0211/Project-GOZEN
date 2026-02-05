import { useNavigate } from 'react-router-dom'

function LandingPage() {
  const navigate = useNavigate()

  const handleStart = () => {
    navigate('/start')
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-slate-900 relative overflow-hidden">
      {/* 背景装飾 */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-genshu-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-kaigun-500/5 rounded-full blur-3xl" />
      </div>

      {/* メインコンテンツ */}
      <div className="relative z-10 text-center animate-fade-in">
        {/* タイトル */}
        <h1 className="font-serif text-7xl md:text-8xl lg:text-9xl text-genshu-400 mb-4 tracking-wider">
          御前会議
        </h1>

        {/* サブタイトル */}
        <p className="text-slate-400 text-lg md:text-xl mb-2">
          Project GOZEN
        </p>
        <p className="text-slate-500 text-sm md:text-base mb-12">
          海軍参謀 vs 陸軍参謀 - マルチエージェント意思決定システム
        </p>

        {/* 開廷ボタン */}
        <button
          onClick={handleStart}
          className="group relative px-12 py-4 border-2 border-genshu-500 text-genshu-400 font-serif text-2xl tracking-widest
                     hover:bg-genshu-500/10 hover:border-genshu-400 hover:text-genshu-300
                     transition-all duration-300 ease-out
                     focus:outline-none focus:ring-2 focus:ring-genshu-500 focus:ring-offset-2 focus:ring-offset-slate-900"
        >
          <span className="relative z-10">開 廷</span>

          {/* ホバー時の装飾線 */}
          <span className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-genshu-500 opacity-0 group-hover:opacity-100 transition-opacity" />
          <span className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-genshu-500 opacity-0 group-hover:opacity-100 transition-opacity" />
          <span className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-genshu-500 opacity-0 group-hover:opacity-100 transition-opacity" />
          <span className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-genshu-500 opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>

        {/* フッター情報 */}
        <div className="mt-16 text-slate-600 text-xs">
          <p>「陸軍として海軍の提案に反対である」</p>
        </div>
      </div>

      {/* 下部の装飾 */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-genshu-500/30 to-transparent" />
    </div>
  )
}

export default LandingPage
