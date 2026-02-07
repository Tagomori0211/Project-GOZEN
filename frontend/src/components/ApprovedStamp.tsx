interface ApprovedStampProps {
  onClose?: () => void;
  text?: string;
  subText?: string;
}

function ApprovedStamp({ onClose, text = "承認", subText = "APPROVED" }: ApprovedStampProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 animate-fade-in"
      onClick={onClose}
    >
      <div className="relative animate-stamp">
        {/* スタンプ本体 */}
        <div className="relative w-80 h-80 flex items-center justify-center">
          {/* 外枠 */}
          <div className="absolute inset-0 border-8 border-red-600 rounded-full opacity-90" />
          <div className="absolute inset-4 border-4 border-red-600 rounded-full opacity-70" />

          {/* 中央テキスト */}
          <div className="text-center">
            <div className="font-serif text-red-600 text-6xl font-bold tracking-widest transform -rotate-12 whitespace-nowrap px-4">
              {text}
            </div>
            <div className="text-red-600 text-lg mt-2 transform -rotate-12">
              {subText}
            </div>
          </div>

          {/* 装飾線 */}
          <div className="absolute top-1/2 left-0 w-full h-1 bg-red-600 opacity-30 transform -rotate-12" />
          <div className="absolute top-1/2 left-0 w-full h-1 bg-red-600 opacity-30 transform rotate-12" />
        </div>

        {/* 閉じるヒント */}
        <div className="text-center mt-8 text-slate-400 text-sm animate-pulse">
          クリックして続行
        </div>
      </div>

      <style>{`
        @keyframes stamp {
          0% {
            transform: scale(3) rotate(-30deg);
            opacity: 0;
          }
          50% {
            transform: scale(1.1) rotate(-5deg);
            opacity: 1;
          }
          70% {
            transform: scale(0.95) rotate(2deg);
          }
          100% {
            transform: scale(1) rotate(0deg);
            opacity: 1;
          }
        }
        .animate-stamp {
          animation: stamp 0.5s ease-out forwards;
        }
      `}</style>
    </div>
  );
}

export default ApprovedStamp;
