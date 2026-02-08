
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { HurdleStatus } from '../types';

interface GraphNode {
  id: string;
  name: string;
  type: 'MACRO' | 'SECTOR' | 'ASSET';
  x: number;
  y: number;
  status: HurdleStatus;
  score?: number;
}

interface GraphEdge {
  from: string;
  to: string;
}

// 고정 자산 데이터 (7개)
const ASSETS = [
  { id: 'case1', name: '골든락 마이닝', sector: 's0', score: 137, x: 10, y: 80 },
  { id: 'case2', name: '오비탈 에어로스페이스', sector: 's1', score: 114, x: 23, y: 80 },
  { id: 'case3', name: '넥스트 로보틱스', sector: 's1', score: 116, x: 36, y: 80 },
  { id: 'case4', name: '사이버다인 시스템즈', sector: 's3', score: 115, x: 50, y: 80 },
  { id: 'case5', name: '아르젠텀 리소스', sector: 's0', score: 145, x: 63, y: 80 },
  { id: 'case6', name: '세미콘 퓨처테크', sector: 's2', score: 133, x: 76, y: 80 },
  { id: 'case7', name: '퀀텀 칩 솔루션', sector: 's2', score: 124, x: 90, y: 80 },
];

const MACROS = [
  { id: 'm1', name: '고금리', x: 25, y: 15 },
  { id: 'm2', name: '공급망', x: 50, y: 15 },
  { id: 'm3', name: '환율', x: 75, y: 15 },
];

const SECTORS = [
  { id: 's0', name: '광업/제련', x: 20, y: 45 },
  { id: 's1', name: '우주/로봇', x: 40, y: 45 },
  { id: 's2', name: '반도체/소재', x: 60, y: 45 },
  { id: 's3', name: '기타/렌탈', x: 80, y: 45 },
];

const EDGES: GraphEdge[] = [
  { from: 'm2', to: 's0' }, { from: 'm2', to: 's2' },
  { from: 'm1', to: 's1' }, { from: 'm3', to: 's2' },
  ...ASSETS.map(a => ({ from: a.sector, to: a.id }))
];

const NEWS_POOL = [
  { id: 'n1', source: 'FT', headline: "물류 병목 현상 심화", content: "홍해 사태 장기화로 원자재 수급 리스크가 반도체 및 광업 섹터로 전이되고 있습니다.", rootId: 'm2' },
  { id: 'n2', source: 'Reuters', headline: "미 연준 금리 유지 시사", content: "긴축 기조 유지로 인해 자본 집약적 산업인 우주항공 분야의 이자 부담이 가중됩니다.", rootId: 'm1' },
  { id: 'n3', source: 'Nikkei', headline: "반도체 소재 수출 규제", content: "동아시아 무역 갈등으로 소재 및 부품 공급망의 불확실성이 극도로 높아졌습니다.", rootId: 'm3' },
  { id: 'n4', source: 'Bloomberg', headline: "원자재가 변동성 확대", content: "구리 및 주요 광물 가격의 급변으로 제련 업종의 수익성 방어선이 위협받고 있습니다.", rootId: 'm2' },
  { id: 'n5', source: 'WSJ', headline: "글로벌 채권 금리 급등", content: "국채 수익률 상승에 따라 하이일드 채권 시장의 자금 경색이 우려됩니다.", rootId: 'm1' },
];

const MonitoringDashboard: React.FC = () => {
  const [nodes, setNodes] = useState<GraphNode[]>(() => [
    ...MACROS.map(m => ({ ...m, type: 'MACRO' as const, status: HurdleStatus.PASS })),
    ...SECTORS.map(s => ({ ...s, type: 'SECTOR' as const, status: HurdleStatus.PASS })),
    ...ASSETS.map(a => ({ ...a, type: 'ASSET' as const, status: a.score < 60 ? HurdleStatus.FAIL : HurdleStatus.PASS }))
  ]);

  const [newsFeed, setNewsFeed] = useState<any[]>([]);
  const [activeNews, setActiveNews] = useState<any | null>(null);
  const [isLive, setIsLive] = useState(true);
  const timerRefs = useRef<number[]>([]);

  // 타이머 정리 함수
  const clearTimers = useCallback(() => {
    timerRefs.current.forEach(window.clearTimeout);
    timerRefs.current = [];
  }, []);

  useEffect(() => {
    return () => clearTimers();
  }, [clearTimers]);

  // 실시간 크롤링 시뮬레이션 (뉴스 5개로 제한)
  useEffect(() => {
    const fetchNews = () => {
      if (!isLive) return;
      const raw = NEWS_POOL[Math.floor(Math.random() * NEWS_POOL.length)];
      const newsItem = {
        ...raw,
        uid: Date.now(),
        time: new Date().toLocaleTimeString('ko-KR', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
      };
      setNewsFeed(prev => [newsItem, ...prev].slice(0, 5));
    };

    fetchNews(); // 초기 실행
    const interval = setInterval(fetchNews, 8000); // 8초마다 갱신 (부하 방지)
    return () => clearInterval(interval);
  }, [isLive]);

  // 리스크 전이 시뮬레이션
  const handleNewsClick = (news: any) => {
    clearTimers();
    setIsLive(false);
    setActiveNews(news);

    // 1단계: 근원지 타격
    setNodes(prev => prev.map(n => ({
      ...n,
      status: n.id === news.rootId ? HurdleStatus.FAIL : HurdleStatus.PASS
    })));

    // 2단계: 섹터 전이 (1.5초 뒤)
    const t1 = window.setTimeout(() => {
      setNodes(prev => prev.map(n => {
        const isTargetSector = EDGES.some(e => e.from === news.rootId && e.to === n.id);
        if (isTargetSector) return { ...n, status: HurdleStatus.WARNING };
        return n;
      }));
    }, 1200);

    // 3단계: 자산 전이 (3초 뒤)
    const t2 = window.setTimeout(() => {
      setNodes(prev => prev.map(n => {
        if (n.type === 'ASSET') {
          const parentSector = EDGES.find(e => e.to === n.id)?.from;
          const isParentHit = nodes.find(sn => sn.id === parentSector)?.status !== HurdleStatus.PASS;
          if (isParentHit) return { ...n, status: HurdleStatus.FAIL };
        }
        return n;
      }));
    }, 2500);

    timerRefs.current = [t1, t2];
  };

  const reset = () => {
    clearTimers();
    setNodes([
      ...MACROS.map(m => ({ ...m, type: 'MACRO' as const, status: HurdleStatus.PASS })),
      ...SECTORS.map(s => ({ ...s, type: 'SECTOR' as const, status: HurdleStatus.PASS })),
      ...ASSETS.map(a => ({ ...a, type: 'ASSET' as const, status: a.score < 60 ? HurdleStatus.FAIL : HurdleStatus.PASS }))
    ]);
    setActiveNews(null);
    setIsLive(true);
  };

  return (
    <div className="flex h-full bg-[#020617] text-slate-400 font-['Pretendard'] overflow-hidden">
      {/* 뉴스 피드 (최대 5개) */}
      <aside className="w-80 border-r border-white/5 bg-[#030712]/95 backdrop-blur-3xl flex flex-col shrink-0">
        <div className="p-6 border-b border-white/5 bg-white/[0.02]">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-[11px] font-black text-white uppercase tracking-widest flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`}></div>
              리스크 크롤러 (TOP 5)
            </h3>
          </div>
          <p className="text-[9px] text-slate-500 font-bold uppercase tracking-tighter">실시간 데이터 스트림 모니터링 중</p>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
          {newsFeed.map(news => (
            <div
              key={news.uid}
              onClick={() => handleNewsClick(news)}
              className={`p-4 rounded-xl border transition-all cursor-pointer group ${activeNews?.uid === news.uid ? 'bg-rose-600/20 border-rose-500/50' : 'bg-white/5 border-white/5 hover:border-white/10'}`}
            >
              <div className="flex justify-between items-center mb-1">
                <span className="text-[8px] font-black text-blue-400 uppercase">{news.source}</span>
                <span className="text-[8px] font-mono opacity-40">{news.time}</span>
              </div>
              <h4 className="text-[11px] font-black leading-tight text-slate-300 group-hover:text-white">{news.headline}</h4>
            </div>
          ))}
          {newsFeed.length === 0 && <div className="py-20 text-center opacity-10 text-[10px]">데이터 연결 중...</div>}
        </div>
      </aside>

      {/* 메인 관제판 */}
      <main className="flex-1 relative flex flex-col bg-[#020617]">
        <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:40px_40px] opacity-10"></div>

        <header className="h-16 flex items-center justify-between px-10 border-b border-white/5 bg-[#020617]/90 backdrop-blur-md z-30">
          <div>
            <h2 className="text-xs font-black text-white tracking-[0.15em] uppercase">Enterprise Risk Topology (7 Core Assets)</h2>
            <p className="text-[9px] font-bold text-slate-600 mt-1 uppercase">거시 지표 - 섹터 - 개별 자산 전이 모델링</p>
          </div>
          <div className="flex gap-4">
            {activeNews && <span className="px-3 py-1 bg-rose-600/20 border border-rose-500/30 rounded-full text-[9px] font-black text-rose-500 animate-pulse">CONTAGION_ACTIVE</span>}
            <button onClick={reset} className="px-5 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-[10px] font-black text-slate-300 transition-all">초기화</button>
          </div>
        </header>

        <div className="flex-1 relative z-10">
          <svg className="w-full h-full p-10" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
            {/* 고정 경로 (Edges) */}
            {EDGES.map((edge, i) => {
              const from = [...MACROS, ...SECTORS, ...ASSETS].find(n => n.id === edge.from)!;
              const to = [...MACROS, ...SECTORS, ...ASSETS].find(n => n.id === edge.to)!;
              const sourceNode = nodes.find(n => n.id === edge.from);
              const isDanger = sourceNode?.status !== HurdleStatus.PASS;

              return (
                <g key={i}>
                  <line
                    x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                    stroke={isDanger ? "#f43f5e" : "#1e293b"}
                    strokeWidth={isDanger ? "0.6" : "0.3"}
                    strokeDasharray={isDanger ? "1, 1" : "none"}
                    className={isDanger ? "animate-[dash_1s_linear_infinite]" : ""}
                    style={{ transition: 'stroke 0.5s' }}
                  />
                </g>
              );
            })}

            {/* 노드 (Nodes) */}
            {nodes.map(node => (
              <g key={node.id} className="cursor-default">
                {node.status !== HurdleStatus.PASS && (
                  <circle cx={node.x} cy={node.y} r={node.type === 'ASSET' ? '5' : '3.5'} fill={node.status === HurdleStatus.FAIL ? 'rgba(244, 63, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)'} className="animate-pulse" />
                )}
                <rect
                  x={node.x - (node.type === 'ASSET' ? 5 : 4)} y={node.y - 2.5}
                  width={node.type === 'ASSET' ? 10 : 8} height="5" rx="1"
                  fill="#030712"
                  stroke={node.status === HurdleStatus.FAIL ? "#f43f5e" : node.status === HurdleStatus.WARNING ? "#f59e0b" : "#3b82f6"}
                  strokeWidth="0.4"
                  className="transition-all duration-500"
                />
                <text x={node.x} y={node.y + 0.5} textAnchor="middle" className="text-[1.8px] font-black fill-white pointer-events-none">{node.name}</text>
                <text x={node.x} y={node.y + 7} textAnchor="middle" className={`text-[1.1px] font-bold uppercase tracking-widest ${node.status === HurdleStatus.FAIL ? 'fill-rose-500' : 'fill-slate-600'}`}>
                  {node.type} {node.score ? `| ${node.score}PT` : ''}
                </text>
              </g>
            ))}
          </svg>
        </div>

        {/* AI 분석 요약 패널 */}
        {activeNews && (
          <div className="absolute bottom-8 left-8 right-8 z-30 animate-in slide-in-from-bottom-5 duration-500">
            <div className="bg-[#0f172a]/95 backdrop-blur-2xl border border-white/10 rounded-3xl p-6 shadow-2xl flex gap-8 items-center">
              <div className="w-12 h-12 rounded-2xl bg-blue-600 flex items-center justify-center text-white font-black text-lg">AI</div>
              <div className="flex-1">
                <h4 className="text-[10px] font-black text-blue-500 uppercase tracking-widest mb-1">Risk Propagation Analysis</h4>
                <p className="text-sm text-slate-200 font-medium leading-relaxed italic">
                  "{activeNews.content} 현재 전이 경로의 끝단에 위치한 자산들에 대한 DSCR 점검이 시급합니다."
                </p>
              </div>
              <div className="w-48 text-right">
                <p className="text-[9px] font-bold text-slate-500 uppercase mb-1">Contagion Prob.</p>
                <p className="text-xl font-black text-rose-500">84.5%</p>
              </div>
            </div>
          </div>
        )}
      </main>

      <style>{`
        @keyframes dash { to { stroke-dashoffset: -2; } }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
      `}</style>
    </div>
  );
};

export default MonitoringDashboard;
