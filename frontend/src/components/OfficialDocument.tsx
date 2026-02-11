import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface OfficialDocumentProps {
    markdown: string;
    timestamp?: string | Date;
}

const OfficialDocument: React.FC<OfficialDocumentProps> = ({ markdown, timestamp }) => {
    const documentRef = React.useRef<HTMLDivElement>(null);

    // Generate random issue number
    const issueNumber = React.useMemo(() => {
        return Math.floor(Math.random() * 9000) + 1000;
    }, []);

    // Format Date to Japanese Era (Reiwa)
    const formattedDate = React.useMemo(() => {
        const date = timestamp ? new Date(timestamp) : new Date();
        const year = date.getFullYear();
        const month = date.getMonth() + 1;
        const day = date.getDate();

        let eraYear = year - 2018;
        let eraName = "令和";
        if (year < 2019) {
            eraName = "西暦";
            eraYear = year;
        }
        const yearStr = eraYear === 1 ? "元" : eraYear.toString();
        return `${eraName}${yearStr}年${month}月${day}日`;
    }, [timestamp]);

    const exportToHtml = () => {
        if (!documentRef.current) return;

        const content = documentRef.current.innerHTML;
        const fullHtml = `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>御前会議決定公文書_${issueNumber}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { background-color: #333; display: flex; justify-content: center; padding: 40px; font-family: 'Noto Serif JP', serif; }
        .document-container { 
            background-color: #f4f1ea; 
            color: #1a1a1a; 
            padding: 60px; 
            width: 800px; 
            border: 6px double #2d2d2d; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            position: relative;
            line-height: 2;
        }
        .hanko-area { position: absolute; top: 40px; right: 40px; display: flex; gap: 8px; }
        .hanko-box { width: 70px; height: 90px; border: 1px solid #000; display: flex; flex-direction: column; align-items: center; background: rgba(255,255,255,0.3); }
        .hanko-title { font-size: 10px; border-bottom: 1px solid #000; width: 100%; text-align: center; padding: 2px 0; }
        .hanko-seal { flex: 1; display: flex; items: center; justify-content: center; position: relative; }
        .seal-red { 
            width: 50px; height: 50px; border: 2px solid #b91c1c; rounded: 50%; color: #b91c1c; 
            display: flex; items: center; justify-content: center; font-weight: bold; font-size: 14px;
            transform: rotate(-12deg); border-radius: 50%;
        }
        .header-meta { margin-bottom: 40px; }
        .title { text-align: center; font-size: 28px; font-weight: bold; margin: 60px 0; border-bottom: 2px solid #000; display: inline-block; width: 100%; padding-bottom: 10px; }
        .content { font-size: 18px; text-align: justify; white-space: pre-wrap; }
        .footer { margin-top: 80px; text-align: right; }
    </style>
</head>
<body>
    <div class="document-container">
        ${content}
    </div>
</body>
</html>`;

        const blob = new Blob([fullHtml], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `decision_${issueNumber}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const HankoSeal = ({ label, role }: { label: string, role: string }) => (
        <div className="w-[70px] h-[90px] border border-black flex flex-col items-center bg-white/20 select-none">
            <div className="w-full text-center text-[10px] border-b border-black py-1 font-serif">
                {role}
            </div>
            <div className="flex-1 flex items-center justify-center">
                <div className="w-[50px] h-[50px] border-2 border-red-700 rounded-full flex items-center justify-center text-red-700 font-serif font-bold transform -rotate-12 opacity-90">
                    {label}
                </div>
            </div>
        </div>
    );

    return (
        <div className="flex flex-col items-center gap-6 my-8">
            <div
                ref={documentRef}
                className="max-w-4xl w-full p-16 bg-[#f4f1ea] text-[#1a1a1a] font-serif shadow-2xl relative border-double border-4 border-gray-800 leading-loose overflow-hidden"
                style={{ fontFamily: "'Noto Serif JP', serif" }}
            >
                {/* Hanko Area */}
                <div className="absolute top-10 right-10 flex gap-2 z-20">
                    <HankoSeal role="陸軍省" label="承認" />
                    <HankoSeal role="海軍省" label="承認" />
                    <HankoSeal role="国家元首" label="裁可" />
                </div>

                {/* Header */}
                <div className="header-meta mb-12 relative z-10 pt-10">
                    <div className="text-sm font-bold">
                        <div>機密第 {issueNumber} 号</div>
                        <div>{formattedDate}</div>
                    </div>
                    <div className="mt-8">
                        <h2 className="text-xl font-bold border-b-2 border-black pb-1 inline-block">
                            全軍将兵 殿
                        </h2>
                    </div>
                </div>

                {/* Title Area */}
                <div className="text-center mb-16">
                    <h1 className="text-3xl font-bold tracking-[0.5em] border-b-4 border-black inline-block pb-4 px-8">
                        御前会議決定公文書
                    </h1>
                </div>

                {/* Body Content */}
                <div className="content font-serif text-xl text-justify whitespace-pre-wrap leading-[2.5] mb-20">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {markdown}
                    </ReactMarkdown>
                </div>

                {/* Footer */}
                <div className="footer mt-32 text-right font-bold">
                    <div>Project GOZEN 統合司令部</div>
                    <div className="text-lg">書記局 奉勅印</div>
                </div>
            </div>

            {/* Export Button */}
            <button
                onClick={exportToHtml}
                className="flex items-center gap-2 px-6 py-3 bg-red-900/80 hover:bg-red-800 text-gold-200 border border-gold-500/30 rounded-full transition-all duration-300 font-serif tracking-widest shadow-lg hover:shadow-red-900/40 group"
            >
                <span className="group-hover:scale-110 transition-transform">📜</span>
                現物保存（HTML出力）
            </button>
        </div>
    );
};

export default OfficialDocument;

