import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface OfficialDocumentProps {
    markdown: string;
    timestamp?: string | Date;
}

const OfficialDocument: React.FC<OfficialDocumentProps> = ({ markdown, timestamp }) => {
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

        // Simple calculation for Reiwa (2019 onward)
        // 2019 = Reiwa 1, 2020 = Reiwa 2...
        // Year - 2018 = Reiwa Year
        let eraYear = year - 2018;
        let eraName = "令和";

        if (year < 2019) {
            // Fallback for older dates if needed (Heisei etc), but for now assume Reiwa
            eraName = "西暦";
            eraYear = year;
        }

        const yearStr = eraYear === 1 ? "元" : eraYear.toString();

        return `${eraName}${yearStr}年${month}月${day}日`;
    }, [timestamp]);

    const HankoBox = ({ title, sealed, color = "red" }: { title: string, sealed: boolean, color?: string }) => (
        <div className="flex flex-col items-center border border-black w-16">
            <div className="w-full text-center text-xs border-b border-black py-1 font-serif">
                {title}
            </div>
            <div className="w-full h-16 flex items-center justify-center relative">
                {sealed && (
                    <div className={`
                        w-12 h-12 border-2 border-${color}-700 rounded-full flex flex-col items-center justify-center
                        text-${color}-700 transform -rotate-12 opacity-80 select-none
                    `}>
                        <span className="text-[10px] font-bold">Project</span>
                        <span className="text-xs font-bold leading-none">GOZEN</span>
                        <span className="text-[10px]">承認</span>
                    </div>
                )}
            </div>
        </div>
    );

    return (
        <div className="max-w-4xl mx-auto my-8 p-16 bg-[#fdfbf7] text-black font-serif shadow-2xl relative border border-stone-200 leading-relaxed overflow-hidden">
            {/* Watermark */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-[20rem] text-stone-100 font-serif font-bold pointer-events-none select-none z-0 rotate-[-30deg] opacity-50">
                GOZEN
            </div>

            {/* Header Area */}
            <div className="flex justify-between items-start mb-12 relative z-10">
                {/* Left: Addressee (Usually comes after Date/Number in standard layout, 
                    but user requested: "Right top... titles... Left: To Genshu-dono")
                    Standard Japanese Business/Official Document:
                    1. Date (Top Right)
                    2. Addressee (Top Left)
                    3. Sender (Top Right or Bottom Right)
                    4. Title (Center)
                    
                    User Request: 
                    "Right top: 3 Hanko columns... 
                    Title: '御前会議最終決定書'
                    To: '国家元首殿'" 
                    
                    I will place Date/Number at very top right, then Hanko boxes below it.
                    Then Addressee at left.
                */}

                <div className="mt-20">
                    <h2 className="text-xl font-bold border-b border-black pb-1 inline-block">
                        国家元首殿
                    </h2>
                </div>

                <div className="flex flex-col items-end gap-4">
                    {/* Metadata */}
                    <div className="text-right text-sm space-y-1 mb-2">
                        <div>GOZEN総第 {issueNumber} 号</div>
                        <div>{formattedDate}</div>
                    </div>

                    {/* Hanko Columns */}
                    <div className="flex gap-0 border border-black bg-white">
                        <HankoBox title="海軍省" sealed={true} color="blue" />
                        <HankoBox title="陸軍省" sealed={true} color="green" />
                        <HankoBox title="国家元首" sealed={false} />
                    </div>
                </div>
            </div>

            {/* Title */}
            <div className="text-center mb-16 relative">
                <h1 className="text-3xl font-bold tracking-widest border-b-2 border-black inline-block pb-2 px-4 z-10 relative">
                    御前会議最終決定書
                </h1>

                {/* Grand Stamp "全軍通達" */}
                <div className="absolute top-[-20px] left-1/2 transform -translate-x-1/2 -rotate-12 border-4 border-red-600 rounded-lg p-2 opacity-80 pointer-events-none">
                    <div className="border-2 border-red-600 px-4 py-2 text-red-600 font-serif font-black text-4xl tracking-widest whitespace-nowrap">
                        全軍通達
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="prose prose-stone prose-lg max-w-none prose-headings:font-serif prose-p:font-serif prose-headings:text-black prose-p:text-black text-justify leading-loose">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {markdown}
                </ReactMarkdown>
            </div>

            {/* Footer */}
            <div className="mt-24 text-right">
                <div className="inline-block text-center">
                    <div className="text-sm mb-2">Project GOZEN 統合司令部</div>
                    <div className="font-bold">書記局</div>
                    {/* No sender name as requested */}
                </div>
            </div>
        </div>
    );
};

export default OfficialDocument;
