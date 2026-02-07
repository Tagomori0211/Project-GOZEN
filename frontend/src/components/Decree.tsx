import React from 'react';
import { DecreeData } from '../types/council';

interface DecreeProps {
  data: DecreeData;
}

const Decree: React.FC<DecreeProps> = ({ data }) => {
  const { decree_text, criteria, signatories, timestamp, adopted_type } = data;

  const formatDate = (dateStr: string) => {
    try {
      // "2024年XX月XX日" 形式ならそのまま、ISO形式ならパース
      if (dateStr.includes('年')) return dateStr;
      const d = new Date(dateStr);
      return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
    } catch {
      return dateStr;
    }
  };

  // ハンココンポーネント
  const Hanko = ({ label, active, color = 'red' }: { label: string; active: boolean; color?: string }) => (
    <div className="flex flex-col items-center">
      <div className="text-xs mb-1 font-serif text-black">{label}</div>
      <div className={`
        w-16 h-16 border-2 rounded-full flex items-center justify-center relative
        ${active ? `border-${color}-600` : 'border-gray-300'}
      `}>
        {active && (
          <div className={`
            w-14 h-14 border border-${color}-600 rounded-full flex flex-col items-center justify-center
            text-${color}-600 transform -rotate-12 select-none
          `}>
             <span className="text-[10px] leading-tight">Project</span>
             <span className="text-sm font-bold leading-tight">GOZEN</span>
             <span className="text-[10px] leading-tight">Approved</span>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto my-6 p-8 bg-white text-black font-serif shadow-xl relative overflow-hidden">
      {/* 背景透かし */}
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 opacity-5 pointer-events-none">
        <svg width="400" height="400" viewBox="0 0 100 100">
           <circle cx="50" cy="50" r="40" stroke="black" strokeWidth="2" fill="none" />
           <path d="M50 10 L50 90 M10 50 L90 50" stroke="black" strokeWidth="1" />
        </svg>
      </div>

      {/* ヘッダー */}
      <div className="text-center mb-12 border-b-2 border-black pb-4">
        <h2 className="text-3xl font-bold tracking-widest mb-2">裁定通達書</h2>
        <div className="text-sm text-right mt-2">{formatDate(timestamp)}</div>
        <div className="text-sm text-right">Project GOZEN 統合司令部</div>
      </div>

      {/* 決裁印欄（右上） */}
      <div className="absolute top-6 right-6 flex gap-2 bg-white/80 p-1">
        <Hanko label="海軍参謀" active={signatories.kaigun} color="blue" />
        <Hanko label="陸軍参謀" active={signatories.rikugun} color="green" />
        <Hanko label="国家元首" active={signatories.shogun} color="red" />
      </div>

      {/* 本文 */}
      <div className="mb-8 leading-loose text-lg text-justify px-4 mt-16">
        <p className="mb-4 whitespace-pre-wrap">{decree_text}</p>
      </div>

      {/* 決定事項詳細（判断基準） */}
      {criteria && criteria.length > 0 && (
        <div className="mb-8 border border-black p-4">
          <h3 className="font-bold border-b border-black inline-block mb-3 px-2">
            【判断基準・特記事項】
          </h3>
          <ul className="list-decimal list-inside space-y-2 ml-2">
            {criteria.map((item, idx) => (
              <li key={idx} className="pl-2 -indent-2">{item}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 採択案種別 */}
      <div className="text-center mt-12 mb-8">
        <div className="inline-block border-2 border-black px-8 py-2 text-xl font-bold">
          採択：{adopted_type === 'kaigun' ? '海軍案' : adopted_type === 'rikugun' ? '陸軍案' : '統合案'}
        </div>
      </div>

      <div className="text-right text-sm mt-8">
        以上
      </div>
    </div>
  );
};

export default Decree;
