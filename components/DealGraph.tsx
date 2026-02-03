
import React, { useState, useMemo } from 'react';
import { DealNode, DealEdge, HurdleStatus, AIInsight } from '../types';

const NODES: DealNode[] = [
  { 
    id: 'n1', 
    name: 'Affinity Equity Partners', 
    type: 'Sponsor', 
    status: HurdleStatus.FAIL, 
    position: { x: 50, y: 15 }, 
    details: [
      { label: '리스크 핵심', value: '대표이사 횡령 및 배임' },
      { label: '자산 상태', value: '검찰 동결 명령' }
    ],
    insights: [{
      title: "스폰서 대주주 적격성 상실",
      content: "대표이사 횡령 보도로 인해 자금 조달 및 엑시트 경로가 전면 차단되었습니다. 이는 금융약정서 제 15조(스폰서 의무 위반)에 해당합니다.",
      impactScore: 95,
      relatedCovenant: "제15조 2항 (Default Event)",
      actionRequired: "EOD 즉시 선고 및 질권 실행 검토"
    }]
  },
  { 
    id: 'n2', 
    name: 'SEEK Limited', 
    type: 'Investor', 
    status: HurdleStatus.WARNING, 
    position: { x: 82, y: 15 }, 
    details: [
      { label: '지분율', value: '10%' },
      { label: '리스크 노출', value: '전략적 협업 중단 우려' }
    ] 
  },
  { 
    id: 'n3', 
    name: 'Career Opportunities Ltd.', 
    type: 'HoldCo', 
    status: HurdleStatus.FAIL, 
    position: { x: 50, y: 50 }, 
    details: [
      { label: '차입금', value: '7,200억' },
      { label: '상환 능력', value: '이자 지급 불능 위험' }
    ],
    insights: [{
      title: "SPC 현금흐름 차단 가능성",
      content: "상위 스폰서의 자산 동결로 인해 배당 수입 및 유상증자 지원이 불가능해졌습니다. 차기 이자 상환일(D-15) 불능 확률 88%입니다.",
      impactScore: 88,
      relatedCovenant: "제 8조 (Cash Flow Waterfall)",
      actionRequired: "인출제한계좌(Reserve Account) 동결"
    }]
  },
  { 
    id: 'n4', 
    name: 'JobKorea (OpCo)', 
    type: 'OpCo', 
    status: HurdleStatus.WARNING, 
    position: { x: 50, y: 85 }, 
    details: [
      { label: '경영진 상태', value: '정상 가동 중' },
      { label: 'MAU 추이', value: '사람인 대비 -3% 하락' }
    ] 
  },
  { 
    id: 'n5', 
    name: 'JobKorea Partners', 
    type: 'Partner', 
    status: HurdleStatus.PASS, 
    position: { x: 20, y: 85 }, 
    details: [
      { label: '영업 대행', value: '정상 가동' }
    ] 
  },
];

const EDGES: DealEdge[] = [
  { from: 'n1', to: 'n3', label: '100% Risk Contagion', isRiskPath: true },
  { from: 'n2', to: 'n3', label: 'Joint Venture' },
  { from: 'n3', to: 'n4', label: 'Debt Service Link', isRiskPath: true },
  { from: 'n4', to: 'n5', label: 'Service Control' },
];

const DealGraph: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<DealNode | null>(null);

  const riskLevel = useMemo(() => {
    return NODES.some(n => n.status === HurdleStatus.FAIL) ? 'CRITICAL' : 'NORMAL';
  }, []);

  return (
    <div className={`bg-slate-950 rounded-3xl border ${riskLevel === 'CRITICAL' ? 'border-rose-900/50' : 'border-slate-800'} overflow-hidden h-[650px] relative flex shadow-2xl transition-all duration-1000`}>
      
      {/* Risk Alert Background Effect */}
      {riskLevel === 'CRITICAL' && (
        <div className="absolute inset-0 bg-rose-950/10 animate-pulse pointer-events-none z-0"></div>
      )}

      {/* Floating Status Card */}
      <div className="absolute top-8 left-8 z-10 space-y-6 max-w-[280px]">
        <div className="bg-slate-900/80 backdrop-blur-md border border-slate-700/50 p-6 rounded-2xl shadow-xl">
           <span className="text-[10px] font-black text-rose-500 uppercase tracking-widest flex items-center gap-2">
             <div className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></div>
             Active Risk Contagion Detect
           </span>
           <h4 className="text-white font-black text-lg mt-2">어피니티 크레딧 위기</h4>
           <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
             스폰서의 형사 리스크가 하위 SPC로 전이되었습니다. 대주단은 즉시 EOD(기한이익상실) 여부를 판단해야 합니다.
           </p>
        </div>

        <div className="space-y-2">
           <LegendItem color="bg-rose-500" label="Risk Origin (Crisis)" pulse />
           <LegendItem color="bg-rose-400" label="Contagion Nodes (HoldCo/OpCo)" />
           <LegendItem color="bg-blue-500" label="Normal Entities" />
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="flex-1 relative cursor-grab active:cursor-grabbing z-10">
        <svg className="w-full h-full p-20" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="1.5" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          
          {/* Risk Propagation Paths */}
          {EDGES.map((edge, i) => {
            const fromNode = NODES.find(n => n.id === edge.from)!;
            const toNode = NODES.find(n => n.id === edge.to)!;
            return (
              <g key={i}>
                <line 
                  x1={fromNode.position.x} y1={fromNode.position.y} 
                  x2={toNode.position.x} y2={toNode.position.y} 
                  stroke={edge.isRiskPath ? "#f43f5e" : "#334155"} 
                  strokeWidth={edge.isRiskPath ? "0.8" : "0.4"}
                  strokeDasharray={edge.isRiskPath ? "2, 2" : "none"}
                  className={edge.isRiskPath ? "animate-[dash_1.5s_linear_infinite]" : ""}
                />
                {edge.isRiskPath && (
                   <circle r="1" fill="#f43f5e" filter="url(#glow)">
                     <animateMotion 
                       dur="2s" repeatCount="indefinite" 
                       path={`M ${fromNode.position.x} ${fromNode.position.y} L ${toNode.position.x} ${toNode.position.y}`} 
                     />
                   </circle>
                )}
                <text 
                  x={(fromNode.position.x + toNode.position.x) / 2} 
                  y={(fromNode.position.y + toNode.position.y) / 2 - 3} 
                  textAnchor="middle" 
                  className={`text-[2.2px] font-black uppercase tracking-tighter ${edge.isRiskPath ? 'fill-rose-400' : 'fill-slate-500'}`}
                >
                  {edge.label}
                </text>
              </g>
            );
          })}

          {/* Nodes */}
          {NODES.map(node => (
            <g 
              key={node.id} 
              onClick={() => setSelectedNode(node)}
              className="cursor-pointer group"
            >
              {node.status === HurdleStatus.FAIL && (
                <circle cx={node.position.x} cy={node.position.y} r="7" fill="rgba(244, 63, 94, 0.15)" className="animate-ping" />
              )}
              <circle 
                cx={node.position.x} cy={node.position.y} r="5" 
                fill="#0f172a" 
                stroke={node.status === HurdleStatus.FAIL ? "#f43f5e" : node.status === HurdleStatus.WARNING ? "#f59e0b" : "#3b82f6"} 
                strokeWidth={selectedNode?.id === node.id ? "1.5" : "1"}
                className="transition-all duration-300"
              />
              <text 
                x={node.position.x} y={node.position.y + 10} 
                textAnchor="middle" 
                className={`text-[2.8px] font-black tracking-tight transition-all ${selectedNode?.id === node.id ? 'fill-white scale-110' : 'fill-slate-300 group-hover:fill-white'}`}
              >
                {node.name}
              </text>
              <text 
                x={node.position.x} y={node.position.y + 0.8} 
                textAnchor="middle" 
                className={`text-[1.8px] font-bold fill-slate-400 pointer-events-none`}
              >
                {node.type.toUpperCase()}
              </text>
            </g>
          ))}
        </svg>
      </div>

      {/* AI Insight & Crisis Control Panel */}
      <div className={`w-[420px] h-full border-l border-slate-800 bg-slate-900/90 backdrop-blur-3xl p-8 transition-all duration-500 absolute right-0 top-0 z-20 shadow-[-20px_0_40px_rgba(0,0,0,0.4)] ${selectedNode ? 'translate-x-0' : 'translate-x-full'}`}>
        {selectedNode && (
          <div className="flex flex-col h-full space-y-8 animate-in slide-in-from-right duration-300">
            <div className="flex justify-between items-start">
               <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-xl font-black ${selectedNode.status === HurdleStatus.FAIL ? 'bg-rose-500/20 text-rose-500' : 'bg-blue-500/20 text-blue-500'}`}>
                    {selectedNode.type.charAt(0)}
                  </div>
                  <div>
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{selectedNode.type} Profile</span>
                    <h3 className="text-white font-black text-xl leading-tight">{selectedNode.name}</h3>
                  </div>
               </div>
               <button onClick={() => setSelectedNode(null)} className="p-2 text-slate-500 hover:text-white transition-colors bg-slate-800 rounded-lg">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
               </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {selectedNode.details.map((d, i) => (
                <div key={i} className="bg-slate-800/40 p-4 rounded-xl border border-slate-700/50">
                   <p className="text-[9px] font-black text-slate-500 uppercase mb-1">{d.label}</p>
                   <p className="text-sm font-black text-slate-100">{d.value}</p>
                </div>
              ))}
            </div>

            {selectedNode.insights && (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                   <span className="text-amber-500">✨</span>
                   <h4 className="text-[11px] font-black text-amber-500 uppercase tracking-[0.2em]">AI Crisis Reasoning</h4>
                </div>
                {selectedNode.insights.map((insight, idx) => (
                  <div key={idx} className="bg-gradient-to-br from-amber-500/10 to-rose-500/10 border border-amber-500/30 rounded-2xl p-6 relative overflow-hidden group">
                    <div className="absolute -top-4 -right-4 text-4xl opacity-5 group-hover:scale-110 transition-transform">🤖</div>
                    <h5 className="text-amber-400 font-black text-sm mb-2">{insight.title}</h5>
                    <p className="text-xs text-slate-300 leading-relaxed font-medium mb-4">{insight.content}</p>
                    
                    <div className="flex flex-col gap-2 border-t border-amber-500/20 pt-4">
                       <div className="flex justify-between text-[10px] font-bold">
                          <span className="text-slate-500 uppercase">Impact Score</span>
                          <span className="text-rose-500">{insight.impactScore}%</span>
                       </div>
                       <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                          <div className="h-full bg-rose-500" style={{ width: `${insight.impactScore}%` }}></div>
                       </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-auto pt-8 border-t border-slate-800 flex flex-col gap-3">
              <button className="w-full py-4 bg-rose-600 hover:bg-rose-500 text-white rounded-2xl text-xs font-black transition-all shadow-[0_0_20px_rgba(225,29,72,0.3)] active:scale-[0.98]">
                EOD(기한이익상실) 통지서 발송 시뮬레이션
              </button>
              <button className="w-full py-4 bg-slate-800 hover:bg-slate-700 text-white rounded-2xl text-xs font-black transition-all">
                DART 실시간 지분 관계도 분석
              </button>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes dash { to { stroke-dashoffset: -4; } }
      `}</style>
    </div>
  );
};

const LegendItem: React.FC<{ color: string; label: string; pulse?: boolean }> = ({ color, label, pulse }) => (
  <div className="flex items-center gap-3 bg-slate-900/50 px-3 py-2 rounded-lg border border-slate-800">
    <div className={`w-2 h-2 rounded-full ${color} ${pulse ? 'animate-pulse shadow-[0_0_8px_rgba(244,63,94,0.8)]' : ''}`}></div>
    <span className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">{label}</span>
  </div>
);

export default DealGraph;
