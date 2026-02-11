import React from 'react'
import { PreMortemData, PreMortemAnalysis, DecisionOption } from '../types/council'

interface PreMortemPanelProps {
    data: PreMortemData
    options?: DecisionOption[]
    onDecide?: (choice: number) => void
}

const AnalysisColumn: React.FC<{ title: string; analysis: PreMortemAnalysis; color: string }> = ({ title, analysis, color }) => (
    <div className={`flex-1 p-4 rounded-lg bg-${color}-900/20 border border-${color}-700/50`}>
        <h3 className={`text-xl font-bold mb-4 text-${color}-400 border-b border-${color}-700 pb-2 flex items-center gap-2`}>
            {title === '海軍' ? '⚓' : '🎖️'} {title}の分析
        </h3>

        <div className="mb-6">
            <h4 className="text-sm font-bold text-slate-400 mb-2">💀 失敗シナリオ</h4>
            <div className="space-y-3">
                {analysis.failure_scenarios.map((scenario, i) => (
                    <div key={i} className="bg-black/30 p-3 rounded border border-slate-700/50">
                        <div className="flex justify-between items-start mb-1">
                            <span className={`text-xs px-2 py-0.5 rounded font-bold ${scenario.impact === '致命的' ? 'bg-red-900 text-red-200' :
                                    scenario.impact === '重大' ? 'bg-orange-900 text-orange-200' :
                                        'bg-yellow-900/50 text-yellow-200'
                                }`}>
                                {scenario.impact}
                            </span>
                            <span className="text-xs text-slate-500">確率: {scenario.probability}</span>
                        </div>
                        <p className="text-slate-300 text-sm">{scenario.cause}</p>
                    </div>
                ))}
            </div>
        </div>

        <div className="mb-6">
            <h4 className="text-sm font-bold text-slate-400 mb-2">👁️ 盲点</h4>
            <ul className="list-disc list-inside text-sm text-slate-300 space-y-1">
                {analysis.blind_spots.map((spot, i) => (
                    <li key={i}>{spot}</li>
                ))}
            </ul>
        </div>

        <div>
            <h4 className="text-sm font-bold text-slate-400 mb-2">🛡️ 緩和策</h4>
            <ul className="list-disc list-inside text-sm text-slate-300 space-y-1">
                {analysis.mitigation.map((m, i) => (
                    <li key={i}>{m}</li>
                ))}
            </ul>
        </div>
    </div>
)

const PreMortemPanel: React.FC<PreMortemPanelProps> = ({ data, options, onDecide }) => {
    return (
        <div className="max-w-5xl mx-auto my-8 animate-fade-in">
            <div className="bg-slate-900/90 border-2 border-slate-700/50 rounded-xl overflow-hidden shadow-2xl">
                {/* Header */}
                <div className="bg-slate-800/80 p-6 border-b border-slate-700 flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-red-400 flex items-center gap-3">
                            <span className="text-3xl">💀</span> Pre-Mortem (事前検死) 分析
                        </h2>
                        <p className="text-slate-400 mt-1">
                            採択予定案（<span className="font-bold text-white">{data.adopted_by}案</span>）が6ヶ月後に失敗したと仮定した場合のシミュレーション
                        </p>
                    </div>
                    <div className="text-right text-xs text-slate-500">
                        <div>Session ID: {data.session_id}</div>
                        <div>Timestamp: {new Date(data.timestamp).toLocaleString()}</div>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 flex flex-col md:flex-row gap-6">
                    <AnalysisColumn title="海軍" analysis={data.kaigun_analysis} color="blue" />
                    <AnalysisColumn title="陸軍" analysis={data.rikugun_analysis} color="green" />
                </div>

                {/* Action Area (Optional) */}
                {options && onDecide && (
                    <div className="bg-slate-800/50 p-6 border-t border-slate-700 flex justify-center gap-4">
                        {options.map((option) => (
                            <button
                                key={option.value}
                                onClick={() => onDecide(option.value)}
                                className={`px-8 py-3 rounded-lg font-bold transition-all duration-300 transform hover:scale-105 ${option.value === 1
                                        ? 'bg-red-900/80 hover:bg-red-800 text-red-100 border border-red-500/50 shadow-lg shadow-red-900/20'
                                        : 'bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-500/50'
                                    }`}
                            >
                                <div className="flex items-center gap-2">
                                    <span>{option.value === 1 ? '⚠️' : '🔄'}</span>
                                    <span>{option.label}</span>
                                </div>
                                <div className="text-xs font-normal opacity-70 mt-1">
                                    {option.value === 1 ? 'リスクを受容して公文書を発行' : '提案フェーズに戻り再検討'}
                                </div>
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}

export default PreMortemPanel
