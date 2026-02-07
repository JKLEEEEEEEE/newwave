/**
 * SupplyChainXRay - 3D 공급망 그래프 X-Ray 화면
 * Neo4j 기반 기업 간 리스크 전이를 시각적으로 보여주는 WOW 화면
 *
 * 구성:
 *   1. 3D Force Graph (중앙, 전체)
 *   2. 좌측 사이드 패널 (딜 요약 + 관련기업)
 *   3. 우측 하단 인포 패널 (스키마 정보)
 *   4. 상단 뱃지 (Neo4j 표시)
 */

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import { motion } from 'framer-motion';
// Step 1: THREE + SpriteText imports
import * as THREE from 'three';
import SpriteText from 'three-spritetext';

// 타입
import type { GraphNode3D, GraphLink3D, CompanyV2, RiskCategoryV2 } from '../types-v2';

// 디자인 토큰
import { GRADIENTS } from '../design-tokens';

// API
import { riskApiV2 } from '../api-v2';

// 유틸
import { getNode3DColor, getNode3DSize } from '../utils-v2';

// Context
import { useRiskV2 } from '../context/RiskV2Context';

// 공유 컴포넌트
import GlassCard from '../shared/GlassCard';
import ScoreGauge from '../shared/ScoreGauge';
import RiskBadge from '../shared/RiskBadge';
import ErrorState from '../shared/ErrorState';

// ============================================
// 타입 확장 (ForceGraph3D 내부 노드용)
// ============================================
interface FGNode extends GraphNode3D {
  x?: number;
  y?: number;
  z?: number;
}

interface FGLink {
  source: string | FGNode;
  target: string | FGNode;
  relationship: GraphLink3D['relationship'];
  dependency: number;
  label: string;
  riskTransfer: number;
}

// ============================================
// Step 2: NODE_LEGEND 교체 (Deal 제거, 프리미엄 색상)
// ============================================
const NODE_LEGEND = [
  { type: 'mainCompany', label: 'Main Company', color: '#E2A855', tier: 'Tier 1', shape: 'circle-md' },
  { type: 'relatedCompany', label: 'Related Company', color: '#9B8AE8', tier: 'Tier 1-2', shape: 'circle-sm' },
  { type: 'riskCategory', label: 'Risk Category', color: '#4ECDC4', tier: 'Tier 2', shape: 'diamond' },
  { type: 'riskEntity', label: 'Risk Entity', color: '#8296AA', tier: 'Tier 3', shape: 'dot' },
];

// Step 2: 헬퍼 함수 - 노드 타입별 색상
function getNodeTypeColor(nodeType: string): string {
  switch (nodeType) {
    case 'mainCompany': return '#E2A855';
    case 'relatedCompany': return '#9B8AE8';
    case 'riskCategory': return '#4ECDC4';
    case 'riskEntity': return '#8296AA';
    default: return '#8296AA';
  }
}

// Step 2: 헬퍼 함수 - 링크 타입별 색상
function getLinkTypeColor(relationship: string): string {
  switch (relationship) {
    case 'TARGET': return '#A8B8CC';
    case 'HAS_CATEGORY': return '#3BB5A8';
    case 'HAS_ENTITY': return '#7E72C0';
    case 'HAS_RELATED': return '#C9963A';
    default: return '#A8B8CC';
  }
}

// ============================================
// 링크 cascade step 매핑
// ============================================
function getLinkCascadeStep(relationship: string): number {
  switch (relationship) {
    case 'TARGET': return 0;
    case 'HAS_CATEGORY': return 1;
    case 'HAS_ENTITY': return 2;
    case 'HAS_RELATED': return 3;
    default: return 4;
  }
}

// ============================================
// 사이드 패널 너비 상수
// ============================================
const SIDE_PANEL_WIDTH = 280;

// ============================================
// Step 7: 캐스케이드 모드 타입
// ============================================
type CascadeMode = 'idle' | 'manual' | 'auto';

// ============================================
// 메인 컴포넌트
// ============================================
export default function SupplyChainXRay() {
  const { state, selectDeal, selectCompany, selectCategory, setActiveView, currentDeal, currentCompany, currentCategories, currentRelatedCompanies } = useRiskV2();
  const { selectedDealId, deals, dealDetail } = state;

  // --- ForceGraph3D ref ---
  const fgRef = useRef<any>(null);

  // --- 윈도우 크기 추적 ---
  const [dimensions, setDimensions] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    height: typeof window !== 'undefined' ? window.innerHeight : 800,
  });

  useEffect(() => {
    const handleResize = () => {
      setDimensions({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // --- 그래프 데이터 (API) ---
  const [graphData, setGraphData] = useState<{ nodes: GraphNode3D[]; links: GraphLink3D[] }>({ nodes: [], links: [] });
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedDealId) {
      setGraphData({ nodes: [], links: [] });
      setGraphError(null);
      return;
    }

    let cancelled = false;
    setGraphLoading(true);
    setGraphError(null);
    riskApiV2.fetchCompanyGraph(selectedDealId).then(res => {
      if (!cancelled) {
        if (res.success && res.data) {
          setGraphData(res.data);
          setGraphError(null);
        } else {
          setGraphData({ nodes: [], links: [] });
          setGraphError(res.error || 'API 서버에 연결할 수 없습니다.');
        }
        setGraphLoading(false);
      }
    });

    return () => { cancelled = true; };
  }, [selectedDealId]);

  // --- 선택된 딜/기업 정보 (from context) ---
  const selectedDeal = currentDeal;
  const mainCompany = currentCompany;
  const relatedCompanies = currentRelatedCompanies;

  // ============================================
  // Step 5: filteredGraphData (U5: Deal 숨김)
  // ============================================
  const filteredGraphData = useMemo(() => {
    const nodes = graphData.nodes.filter(n => n.nodeType !== 'deal');
    const nodeIds = new Set(nodes.map(n => n.id));
    const links = graphData.links.filter(l => {
      const sId = typeof l.source === 'string' ? l.source : (l.source as string);
      const tId = typeof l.target === 'string' ? l.target : (l.target as string);
      return nodeIds.has(sId) && nodeIds.has(tId);
    });
    return { nodes, links };
  }, [graphData]);

  // ============================================
  // Step 6: activeFlowCount (particleCount 대체)
  // ============================================
  const activeFlowCount = useMemo(() => filteredGraphData.links.filter(l => l.riskTransfer > 0).length, [filteredGraphData]);

  // --- 선택된 노드 (NodeDetailPanel) ---
  const [selectedNode, setSelectedNode] = useState<GraphNode3D | null>(null);
  const [showAllConnections, setShowAllConnections] = useState(false);
  const detailPanelRef = useRef<HTMLDivElement>(null);

  // --- Legend 패널 ---
  const [selectedLegendType, setSelectedLegendType] = useState<string | null>(null);
  const [legendSearch, setLegendSearch] = useState('');
  const [legendSortDesc, setLegendSortDesc] = useState(true);
  const legendPanelRef = useRef<HTMLDivElement>(null);

  // --- 관련기업 하이라이트 ---
  const [highlightedCompanyId, setHighlightedCompanyId] = useState<string | null>(null);

  // --- 선택된 링크 ---
  const [selectedLink, setSelectedLink] = useState<GraphLink3D | null>(null);

  // ============================================
  // Step 7: 캐스케이드 시뮬레이션 상태 + 로직
  // ============================================
  const [cascadeMode, setCascadeMode] = useState<CascadeMode>('idle');
  const [cascadeStep, setCascadeStep] = useState(-1);
  const cascadeIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cascadeActive = cascadeMode !== 'idle';

  const stopCascade = useCallback(() => {
    setCascadeMode('idle');
    setCascadeStep(-1);
    if (cascadeIntervalRef.current) {
      clearInterval(cascadeIntervalRef.current);
      cascadeIntervalRef.current = null;
    }
  }, []);

  const startAutoPlay = useCallback(() => {
    stopCascade();
    setCascadeMode('auto');
    setCascadeStep(0);
    cascadeIntervalRef.current = setInterval(() => {
      setCascadeStep(prev => {
        if (prev >= 3) {
          // 한 바퀴 완료 후 정지
          if (cascadeIntervalRef.current) {
            clearInterval(cascadeIntervalRef.current);
            cascadeIntervalRef.current = null;
          }
          setCascadeMode('idle');
          return -1;
        }
        return prev + 1;
      });
    }, 2000);
  }, [stopCascade]);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (cascadeIntervalRef.current) {
        clearInterval(cascadeIntervalRef.current);
      }
    };
  }, []);


  // Legend 패널 열릴 때 자동 스크롤
  useEffect(() => {
    if (selectedLegendType && legendPanelRef.current) {
      setTimeout(() => {
        legendPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 50);
    }
  }, [selectedLegendType]);

  // ============================================
  // Step 8: 캐스케이드 노드 시각 효과 (useEffect로 scene traverse)
  // ============================================
  useEffect(() => {
    if (!fgRef.current) return;
    const scene = fgRef.current.scene?.();
    if (!scene) return;

    scene.traverse((obj: any) => {
      if (!obj.userData?.nodeType) return;
      const nodeTier = obj.userData.nodeTier as number;
      const nodeColor = obj.userData.nodeColor as string;

      if (cascadeActive && cascadeStep >= 0) {
        const isCurrent = nodeTier === cascadeStep;
        const isActive = nodeTier <= cascadeStep;

        obj.children?.forEach((child: any) => {
          if (!child.material) return;

          if (child.userData?.role === 'mainSphere' || child.userData?.role === 'halo') {
            if (isCurrent) {
              if (child.material.emissive) child.material.emissive.set('#fef08a');
              if (child.material.emissiveIntensity !== undefined) child.material.emissiveIntensity = 0.6;
              child.material.opacity = 1.0;
              obj.scale.setScalar(1.3);
            } else if (isActive) {
              if (child.material.emissive) child.material.emissive.set('#000000');
              if (child.material.emissiveIntensity !== undefined) child.material.emissiveIntensity = 0;
              child.material.opacity = 0.9;
              obj.scale.setScalar(1.0);
            } else {
              if (child.material.emissive) child.material.emissive.set('#0a0f1e');
              if (child.material.emissiveIntensity !== undefined) child.material.emissiveIntensity = 0;
              child.material.opacity = 0.15;
              obj.scale.setScalar(0.8);
            }
          }

          if (child.userData?.role === 'pulseRing') {
            child.visible = isCurrent;
          }
        });
      } else {
        // Reset to default state
        obj.scale.setScalar(1.0);
        obj.children?.forEach((child: any) => {
          if (!child.material) return;
          if (child.userData?.role === 'mainSphere' || child.userData?.role === 'halo') {
            if (child.material.emissive) child.material.emissive.set('#000000');
            if (child.material.emissiveIntensity !== undefined) child.material.emissiveIntensity = 0;
            child.material.opacity = child.userData?.role === 'halo' ? 0.15 : 0.9;
          }
          if (child.userData?.role === 'pulseRing') {
            child.visible = false;
          }
        });
      }
    });
  }, [cascadeActive, cascadeStep]);

  // --- 패널 바깥 클릭 시 닫기 ---
  useEffect(() => {
    if (!selectedNode) return;
    const handleOutsideClick = (e: MouseEvent) => {
      if (detailPanelRef.current && !detailPanelRef.current.contains(e.target as Node)) {
        setSelectedNode(null);
        setShowAllConnections(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [selectedNode]);

  // --- 노드 클릭 핸들러 (U1: 자동 네비게이션 제거, NodeDetailPanel만 토글) ---
  const handleNodeClick = useCallback((node: FGNode) => {
    setSelectedNode(prev => prev?.id === node.id ? null : node);
    setShowAllConnections(false);
  }, []);

  // --- 노드 라벨 콜백 (U2: 리치 HTML 툴팁) ---
  const nodeLabelFn = useCallback((node: FGNode) => {
    const typeLabel = node.nodeType === 'mainCompany' ? '투자대상'
      : node.nodeType === 'relatedCompany' ? '관련기업'
      : node.nodeType === 'riskCategory' ? '리스크 카테고리'
      : node.nodeType === 'riskEntity' ? '리스크 엔티티'
      : 'Deal';
    const levelColor = node.riskLevel === 'FAIL' ? '#ef4444'
      : node.riskLevel === 'WARNING' ? '#eab308'
      : '#22c55e';
    return `<div style="background:rgba(15,23,42,0.95);padding:8px 12px;border-radius:8px;border:1px solid rgba(255,255,255,0.1);min-width:160px">
      <div style="font-weight:700;color:#fff;font-size:13px;margin-bottom:4px">${node.name}</div>
      <div style="font-size:11px;color:#94a3b8;margin-bottom:6px">${typeLabel} · Tier ${node.tier}</div>
      <div style="display:flex;align-items:center;gap:6px">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${levelColor}"></span>
        <span style="font-size:12px;color:#e2e8f0;font-weight:600">${node.riskScore}점</span>
        <span style="font-size:10px;color:#64748b;text-transform:uppercase">${node.riskLevel}</span>
      </div>
    </div>`;
  }, []);

  // --- 링크 라벨 콜백 ---
  const linkLabelFn = useCallback((link: FGLink) => {
    const rawLink = link as unknown as GraphLink3D;
    return `${rawLink.label} (전이: ${rawLink.riskTransfer})`;
  }, []);

  // --- 링크 클릭 핸들러 ---
  const handleLinkClick = useCallback((link: FGLink) => {
    const rawLink = link as unknown as GraphLink3D;
    setSelectedLink(prev => prev?.source === rawLink.source && prev?.target === rawLink.target ? null : rawLink);
  }, []);

  // ============================================
  // Step 9: nodeThreeObjectFn (U1+U2+U3+U4 통합)
  // ============================================
  const nodeThreeObjectFn = useCallback((node: FGNode) => {
    const group = new THREE.Group();
    const color = getNodeTypeColor(node.nodeType);
    const size = getNode3DSize(node.nodeType, node.riskScore) * 0.35;

    // 노드 tier 매핑: mainCompany=0, relatedCompany=1, riskCategory=2, riskEntity=3
    let nodeTier = 3;
    if (node.nodeType === 'mainCompany') nodeTier = 0;
    else if (node.nodeType === 'relatedCompany') nodeTier = 1;
    else if (node.nodeType === 'riskCategory') nodeTier = 2;
    else if (node.nodeType === 'riskEntity') nodeTier = 3;

    // userData for cascade effect (Step 8)
    group.userData = { nodeType: node.nodeType, nodeTier, nodeColor: color, nodeId: node.id };

    // 메인 구체
    const sphereGeo = new THREE.SphereGeometry(size, 32, 32);
    const sphereMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(color),
      emissive: new THREE.Color('#000000'),
      emissiveIntensity: 0,
      roughness: 0.3,
      metalness: 0.6,
      transparent: true,
      opacity: 0.9,
    });
    const sphere = new THREE.Mesh(sphereGeo, sphereMat);
    sphere.userData = { role: 'mainSphere' };
    group.add(sphere);

    // 헤일로 (반투명 구체)
    const haloGeo = new THREE.SphereGeometry(size * 1.4, 32, 32);
    const haloMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(color),
      transparent: true,
      opacity: 0.15,
      roughness: 1,
      metalness: 0,
      depthWrite: false,
    });
    const halo = new THREE.Mesh(haloGeo, haloMat);
    halo.userData = { role: 'halo' };
    group.add(halo);

    // 펄스링 (company 노드만)
    if (node.nodeType === 'mainCompany' || node.nodeType === 'relatedCompany') {
      const ringGeo = new THREE.RingGeometry(size * 1.6, size * 1.8, 64);
      const ringMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity: 0.3,
        side: THREE.DoubleSide,
        depthWrite: false,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.userData = { role: 'pulseRing' };
      ring.visible = false; // hidden by default, shown during cascade
      group.add(ring);
    }

    // SpriteText 라벨 (U3: depthTest=false)
    const label = new SpriteText(node.name, size * 0.6, '#e2e8f0');
    (label as any).material.depthTest = false;
    (label as any).position.set(0, size + 2.5, 0);
    label.fontWeight = '600';
    label.backgroundColor = 'rgba(15, 23, 42, 0.7)';
    label.padding = 2;
    label.borderRadius = 3;
    group.add(label);

    return group;
  }, []);

  // --- 링크 콜백 (cascade 연동) ---
  const linkColorFn = useCallback((link: FGLink) => {
    const rel = (link as any).relationship || 'TARGET';
    if (cascadeActive && cascadeStep >= 0) {
      const linkStep = getLinkCascadeStep(rel);
      if (linkStep > cascadeStep) return 'rgba(100,116,139,0.08)'; // 비활성: 거의 안보임
    }
    return getLinkTypeColor(rel);
  }, [cascadeActive, cascadeStep]);

  const linkWidthFn = useCallback((link: FGLink) => {
    if (cascadeActive && cascadeStep >= 0) {
      const rel = (link as any).relationship || 'TARGET';
      const linkStep = getLinkCascadeStep(rel);
      if (linkStep > cascadeStep) return 0.2;
      if (linkStep === cascadeStep) return 2;
    }
    return 1;
  }, [cascadeActive, cascadeStep]);

  const linkParticlesFn = useCallback((link: FGLink) => {
    if (cascadeActive && cascadeStep >= 0) {
      const rel = (link as any).relationship || 'TARGET';
      const linkStep = getLinkCascadeStep(rel);
      if (linkStep > cascadeStep) return 0; // 비활성 엣지는 파티클 없음
    }
    const rawLink = link as unknown as GraphLink3D;
    return rawLink.riskTransfer > 0 ? 3 : 1;
  }, [cascadeActive, cascadeStep]);

  const linkParticleColorFn = useCallback((link: FGLink) => {
    const rawLink = link as unknown as GraphLink3D;
    return rawLink.riskTransfer > 20 ? '#ef4444' : rawLink.riskTransfer > 0 ? '#f59e0b' : '#6366f1';
  }, []);

  return (
    <div className="relative w-full h-full overflow-hidden" style={{ background: 'rgba(10, 15, 30, 1)' }}>
      {/* ============================================ */}
      {/* 1. 3D 그래프 (전체 배경) */}
      {/* ============================================ */}
      <div className="absolute inset-0">
        {/* U7: 로딩 스피너 */}
        {graphLoading && selectedDealId && (
          <div className="absolute inset-0 flex items-center justify-center z-[5]">
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-2 border-purple-500/30 border-t-purple-400 rounded-full animate-spin" />
              <p className="text-slate-400 text-sm">그래프 데이터 로딩 중...</p>
            </div>
          </div>
        )}
        {/* Step 13: ForceGraph3D props 교체 */}
        {selectedDealId && filteredGraphData.nodes.length > 0 && !graphLoading ? (
          <ForceGraph3D
            ref={fgRef}
            graphData={filteredGraphData}
            width={dimensions.width - SIDE_PANEL_WIDTH}
            height={dimensions.height - 64}
            backgroundColor="rgba(10, 15, 30, 1)"
            nodeThreeObject={nodeThreeObjectFn as (node: object) => any}
            nodeLabel={nodeLabelFn as (node: object) => string}
            linkColor={linkColorFn as (link: object) => string}
            linkWidth={linkWidthFn as (link: object) => number}
            linkOpacity={0.5}
            linkDirectionalParticles={linkParticlesFn as (link: object) => number}
            linkDirectionalParticleSpeed={0.005}
            linkDirectionalParticleWidth={2.5}
            linkDirectionalParticleColor={linkParticleColorFn as (link: object) => string}
            linkLabel={linkLabelFn as (link: object) => string}
            onNodeClick={handleNodeClick as (node: object) => void}
            onLinkClick={handleLinkClick as (link: object) => void}
            enableNodeDrag={true}
            enableNavigationControls={true}
            showNavInfo={false}
          />
        ) : graphError && selectedDealId ? (
          <div className="flex items-center justify-center h-full">
            <ErrorState
              message="그래프 데이터를 불러올 수 없습니다"
              detail={graphError}
              onRetry={() => {
                if (selectedDealId) {
                  setGraphLoading(true);
                  setGraphError(null);
                  riskApiV2.fetchCompanyGraph(selectedDealId).then(res => {
                    if (res.success && res.data) {
                      setGraphData(res.data);
                      setGraphError(null);
                    } else {
                      setGraphData({ nodes: [], links: [] });
                      setGraphError(res.error || 'API 서버에 연결할 수 없습니다.');
                    }
                    setGraphLoading(false);
                  });
                }
              }}
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center"
            >
              <div className="text-6xl mb-4 opacity-30">&#128269;</div>
              <p className="text-slate-500 text-lg">
                좌측 패널에서 딜을 선택하세요
              </p>
              <p className="text-slate-600 text-sm mt-2">
                3D 그래프로 리스크 전이를 시각화합니다
              </p>
            </motion.div>
          </div>
        )}
      </div>

      {/* ============================================ */}
      {/* Step 14: 상단 뱃지 (activeFlowCount) */}
      {/* ============================================ */}
      <motion.div
        className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <GlassCard className="px-4 py-2">
          <div className="flex items-center gap-3">
            <span className="text-purple-400 text-xs font-medium">Real-time Risk Propagation</span>
            {activeFlowCount > 0 && (
              <>
                <span className="text-slate-500 text-xs">|</span>
                <span className="text-red-400 text-xs">
                  &#9679; {activeFlowCount} active flows
                </span>
              </>
            )}
          </div>
        </GlassCard>
      </motion.div>

      {/* ============================================ */}
      {/* 2. 좌측 사이드 패널 */}
      {/* ============================================ */}
      <motion.div
        className="absolute left-4 top-4 z-10"
        style={{ width: `${SIDE_PANEL_WIDTH}px` }}
        initial={{ opacity: 0, x: -30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
      >
        <GlassCard className="p-4 max-h-[calc(100vh-120px)] overflow-y-auto">
          {/* 타이틀 */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-white font-bold text-base">Supply Chain X-Ray</h2>
          </div>

          {/* 딜 선택 드롭다운 */}
          <div className="mb-4">
            <label className="text-xs text-slate-500 block mb-1">Select Deal</label>
            <select
              className="w-full bg-slate-800/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-purple-500"
              value={selectedDealId ?? ''}
              onChange={(e) => {
                if (e.target.value) selectDeal(e.target.value);
              }}
            >
              <option value="" className="bg-slate-900">
                -- 딜을 선택하세요 --
              </option>
              {deals.map(deal => (
                <option key={deal.id} value={deal.id} className="bg-slate-900">
                  {deal.name}
                </option>
              ))}
            </select>
          </div>

          {/* 선택된 딜 메인 기업 요약 */}
          {mainCompany && (
            <div className="mb-4 p-3 rounded-xl bg-slate-800/40 border border-white/5">
              <div className="flex items-center gap-3 mb-2">
                <ScoreGauge
                  score={mainCompany.totalRiskScore}
                  size={56}
                  directScore={mainCompany.directScore}
                  propagatedScore={mainCompany.propagatedScore}
                />
                <div>
                  <p className="text-white text-sm font-semibold">{mainCompany.name}</p>
                  <p className="text-slate-400 text-xs">{mainCompany.sector} / {mainCompany.market}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <RiskBadge level={mainCompany.riskLevel} size="sm" animated />
                <span className="text-xs text-slate-500">
                  D:{mainCompany.directScore} + P:{mainCompany.propagatedScore} = {mainCompany.totalRiskScore}
                </span>
              </div>
            </div>
          )}

          {/* ============================================ */}
          {/* Step 15: 캐스케이드 시뮬레이션 UI */}
          {/* ============================================ */}
          {filteredGraphData.nodes.length > 0 && (
            <div className="mb-4">
              <h3 className="text-xs text-slate-500 font-semibold mb-2 uppercase tracking-wider">
                Risk Cascade
              </h3>
              <div className="p-3 rounded-xl bg-slate-800/40 border border-white/5 space-y-3">
                {/* Auto play / stop button */}
                <button
                  onClick={() => {
                    if (cascadeMode === 'auto') {
                      stopCascade();
                    } else {
                      startAutoPlay();
                    }
                  }}
                  className={`w-full py-2 rounded-lg text-xs font-medium transition-colors border ${
                    cascadeMode === 'auto'
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/30 hover:bg-amber-500/30'
                      : 'bg-purple-500/20 text-purple-300 border-purple-500/20 hover:bg-purple-500/30'
                  }`}
                >
                  {cascadeMode === 'auto' ? '\u25FC 정지' : '\u26A1 리스크 전파 시뮬레이션'}
                </button>

                {/* 4 step buttons */}
                <div className="grid grid-cols-2 gap-1.5">
                  {[
                    { step: 0, label: 'Main Company' },
                    { step: 1, label: 'Supply Chain' },
                    { step: 2, label: 'Risk Categories' },
                    { step: 3, label: 'Risk Entities' },
                  ].map(({ step, label }) => (
                    <button
                      key={step}
                      onClick={() => {
                        if (cascadeIntervalRef.current) {
                          clearInterval(cascadeIntervalRef.current);
                          cascadeIntervalRef.current = null;
                        }
                        setCascadeMode('manual');
                        setCascadeStep(step);
                      }}
                      className={`py-1.5 px-2 rounded text-[10px] font-medium transition-all border ${
                        cascadeActive && cascadeStep === step
                          ? 'bg-yellow-400/20 text-yellow-300 border-yellow-400/40'
                          : cascadeActive && cascadeStep > step
                            ? 'bg-slate-700/40 text-slate-300 border-white/10'
                            : 'bg-slate-800/30 text-slate-500 border-white/5 hover:border-white/15 hover:text-slate-400'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                {/* Progress bar (5 dots) */}
                <div className="flex items-center justify-center gap-2">
                  {[0, 1, 2, 3].map(i => (
                    <div
                      key={i}
                      className={`w-2 h-2 rounded-full transition-all duration-300 ${
                        cascadeActive && cascadeStep >= i
                          ? cascadeStep === i
                            ? 'bg-yellow-400 scale-125 shadow-lg shadow-yellow-400/50'
                            : 'bg-purple-400'
                          : 'bg-slate-700'
                      }`}
                    />
                  ))}
                </div>

                {/* Reset button when cascade is active */}
                {cascadeActive && (
                  <button
                    onClick={stopCascade}
                    className="w-full py-1.5 rounded text-[10px] text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-colors"
                  >
                    {'\u2715'} 초기화
                  </button>
                )}
              </div>
            </div>
          )}

          {/* 관련기업 리스트 */}
          {relatedCompanies.length > 0 && (
            <div className="mb-4">
              <h3 className="text-xs text-slate-500 font-semibold mb-2 uppercase tracking-wider">
                Related Companies
              </h3>
              <div className="flex flex-col gap-2">
                {relatedCompanies.map((rc) => (
                  <div
                    key={rc.id}
                    className={`flex items-center justify-between p-2 rounded-lg bg-slate-800/30 border transition-colors cursor-pointer ${
                      highlightedCompanyId === rc.id
                        ? 'border-purple-500/50 bg-purple-500/10'
                        : 'border-white/5 hover:border-purple-500/30'
                    }`}
                    onClick={() => {
                      selectCompany(rc.id);
                      setHighlightedCompanyId(prev => prev === rc.id ? null : rc.id);
                    }}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === 'Enter') { selectCompany(rc.id); setHighlightedCompanyId(prev => prev === rc.id ? null : rc.id); } }}
                  >
                    <div>
                      <p className="text-white text-xs font-medium">{rc.name}</p>
                      <p className="text-slate-500 text-[10px]">
                        {rc.relationToMain?.relation ?? '-'} / Tier {rc.relationToMain?.tier ?? '-'}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-slate-400">{rc.totalRiskScore}pts</span>
                      <RiskBadge level={rc.riskLevel} size="sm" showLabel={false} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 노드 유형별 범례 (클릭 가능) */}
          <div>
            <h3 className="text-xs text-slate-500 font-semibold mb-2 uppercase tracking-wider">
              Node Legend
            </h3>
            <div className="flex flex-col gap-1.5">
              {NODE_LEGEND.map((item) => {
                const count = filteredGraphData.nodes.filter(n => n.nodeType === item.type).length;
                const isSelected = selectedLegendType === item.type;
                return (
                  <div
                    key={item.type}
                    className={`flex items-center gap-2 px-2 py-1 rounded-lg cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-white/10 border border-white/20'
                        : 'hover:bg-white/5 border border-transparent'
                    }`}
                    onClick={() => {
                      setSelectedLegendType(prev => prev === item.type ? null : item.type);
                      setLegendSearch('');
                    }}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === 'Enter') { setSelectedLegendType(prev => prev === item.type ? null : item.type); setLegendSearch(''); } }}
                  >
                    {item.shape === 'circle-md' && <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />}
                    {item.shape === 'circle-sm' && <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />}
                    {item.shape === 'diamond' && <span className="w-2.5 h-2.5 rotate-45" style={{ backgroundColor: item.color }} />}
                    {item.shape === 'dot' && <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />}
                    <span className="text-[10px] text-slate-400 flex-1">{item.label}</span>
                    <span className="text-[10px] text-slate-500 bg-slate-800/60 px-1.5 rounded">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Legend 노드 목록 패널 */}
          {selectedLegendType && (() => {
            const legendItem = NODE_LEGEND.find(l => l.type === selectedLegendType);
            const allOfType = filteredGraphData.nodes.filter(n => n.nodeType === selectedLegendType);
            const searched = legendSearch
              ? allOfType.filter(n => n.name.toLowerCase().includes(legendSearch.toLowerCase()))
              : allOfType;
            const sorted = [...searched].sort((a, b) =>
              legendSortDesc ? b.riskScore - a.riskScore : a.riskScore - b.riskScore
            );
            return (
              <div ref={legendPanelRef} className="mt-3 p-3 rounded-xl bg-slate-800/50 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: legendItem?.color }} />
                    <span className="text-xs text-white font-semibold">{legendItem?.label}</span>
                    <span className="text-[10px] text-slate-500">{sorted.length}개</span>
                  </div>
                  <button
                    onClick={() => setSelectedLegendType(null)}
                    className="p-0.5 rounded hover:bg-white/10 transition-colors"
                    aria-label="닫기"
                  >
                    <span className="text-slate-500 text-xs">{'\u2715'}</span>
                  </button>
                </div>

                {/* 검색 + 정렬 */}
                <div className="flex gap-1.5 mb-2">
                  <input
                    type="text"
                    value={legendSearch}
                    onChange={(e) => setLegendSearch(e.target.value)}
                    placeholder="검색..."
                    className="flex-1 bg-slate-900/60 border border-white/10 rounded px-2 py-1 text-[10px] text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/40"
                  />
                  <button
                    onClick={() => setLegendSortDesc(prev => !prev)}
                    className="px-2 py-1 rounded text-[10px] text-slate-400 bg-slate-900/60 border border-white/10 hover:border-white/20 transition-colors"
                    title="점수 정렬"
                  >
                    {legendSortDesc ? '\u2193 점수' : '\u2191 점수'}
                  </button>
                </div>

                {/* 노드 리스트 */}
                <div className="flex flex-col gap-1 max-h-[280px] overflow-y-auto">
                  {sorted.map(node => (
                    <div
                      key={node.id}
                      className={`flex items-center justify-between p-1.5 rounded-lg cursor-pointer transition-colors ${
                        selectedNode?.id === node.id
                          ? 'bg-purple-500/20 border border-purple-500/30'
                          : 'hover:bg-white/5 border border-transparent'
                      }`}
                      onClick={() => {
                        setSelectedNode(node);
                        setShowAllConnections(false);
                        // 카메라 포커스
                        if (fgRef.current) {
                          const fg = fgRef.current;
                          const graphNode = filteredGraphData.nodes.find(n => n.id === node.id) as any;
                          if (graphNode?.x !== undefined) {
                            fg.cameraPosition(
                              { x: graphNode.x + 80, y: graphNode.y + 40, z: graphNode.z + 80 },
                              { x: graphNode.x, y: graphNode.y, z: graphNode.z },
                              1000
                            );
                          }
                        }
                      }}
                      role="button"
                      tabIndex={0}
                    >
                      <span className="text-[10px] text-slate-300 truncate flex-1">{node.name}</span>
                      <div className="flex items-center gap-1.5 ml-2 shrink-0">
                        <span className="text-[10px] text-slate-400">{node.riskScore}점</span>
                        <RiskBadge level={node.riskLevel} size="sm" showLabel={false} />
                      </div>
                    </div>
                  ))}
                  {sorted.length === 0 && (
                    <p className="text-[10px] text-slate-600 text-center py-2">검색 결과 없음</p>
                  )}
                </div>
              </div>
            );
          })()}
        </GlassCard>
      </motion.div>

      {/* ============================================ */}
      {/* 2.5 Node Detail Panel (right side) */}
      {/* ============================================ */}
      {selectedNode && (
        <motion.div
          ref={detailPanelRef}
          className="absolute right-4 top-4 z-20"
          style={{ width: '320px' }}
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 30 }}
          transition={{ duration: 0.3 }}
        >
          <GlassCard className="p-4 max-h-[60vh] overflow-y-auto">
            {/* Close button */}
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-white font-bold text-sm">{selectedNode.name}</h3>
              <button
                onClick={() => { setSelectedNode(null); setShowAllConnections(false); }}
                className="p-1 rounded-lg hover:bg-white/10 transition-colors"
                aria-label="패널 닫기"
              >
                <span className="text-slate-400 text-sm">&#10005;</span>
              </button>
            </div>

            {/* Node type badge */}
            <div className="flex items-center gap-2 mb-3">
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
                {selectedNode.nodeType === 'mainCompany' ? 'Main Company'
                 : selectedNode.nodeType === 'relatedCompany' ? 'Related Company'
                 : selectedNode.nodeType === 'riskCategory' ? 'Risk Category'
                 : selectedNode.nodeType === 'riskEntity' ? 'Risk Entity'
                 : 'Deal'}
              </span>
              <span className="text-xs text-slate-500">Tier {selectedNode.tier}</span>
            </div>

            {/* Risk score */}
            <div className="mb-3 p-3 rounded-xl bg-slate-800/40 border border-white/5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Risk Score</span>
                <div className="flex items-center gap-2">
                  <span className="text-white font-bold">{selectedNode.riskScore}</span>
                  <RiskBadge level={selectedNode.riskLevel} size="sm" />
                </div>
              </div>
            </div>

            {/* Selection reason / Why this node */}
            <div className="mb-3">
              <h4 className="text-xs text-slate-500 font-semibold mb-2 uppercase tracking-wider">
                Why This Node
              </h4>
              <div className="text-xs text-slate-300 space-y-1.5">
                {/* Show selectionReason from API if available */}
                {selectedNode.metadata?.selectionReason && (
                  <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20 mb-2">
                    <p className="text-purple-200">{String(selectedNode.metadata.selectionReason)}</p>
                  </div>
                )}
                {selectedNode.nodeType === 'mainCompany' && (
                  <>
                    <p>투자 대상 기업으로, 딜의 직접적인 리스크 평가 대상입니다.</p>
                    {selectedNode.metadata?.sector && (
                      <p>섹터: <span className="text-white">{String(selectedNode.metadata.sector)}</span></p>
                    )}
                  </>
                )}
                {selectedNode.nodeType === 'relatedCompany' && (
                  <>
                    <p>공급망/계열사 관계로 리스크가 전이될 수 있는 기업입니다.</p>
                    {selectedNode.metadata?.relation && (
                      <p>관계: <span className="text-white">{String(selectedNode.metadata.relation)}</span></p>
                    )}
                  </>
                )}
                {selectedNode.nodeType === 'riskCategory' && (
                  <>
                    <p>리스크 카테고리로, 하위 엔티티/이벤트의 집계 결과입니다.</p>
                    {selectedNode.metadata?.weight && (
                      <p>가중치: <span className="text-white">{String(Number(selectedNode.metadata.weight) * 100)}%</span></p>
                    )}
                    {selectedNode.metadata?.weightedScore && (
                      <p>가중점수: <span className="text-white">{String(selectedNode.metadata.weightedScore)}</span></p>
                    )}
                  </>
                )}
                {selectedNode.nodeType === 'deal' && (
                  <p>투자검토 건으로, 하위 기업들의 리스크를 종합합니다.</p>
                )}
              </div>
            </div>

            {/* Step 17: Connected edges info - use filteredGraphData */}
            <div className="mb-3">
              <h4 className="text-xs text-slate-500 font-semibold mb-2 uppercase tracking-wider">
                Connections
              </h4>
              {(() => {
                const allConnections = filteredGraphData.links
                  .filter(l => l.source === selectedNode.id || l.target === selectedNode.id);
                const visibleConnections = showAllConnections ? allConnections : allConnections.slice(0, 5);
                const hasMore = allConnections.length > 5;
                return (
                  <>
                    <div className="space-y-1.5">
                      {visibleConnections.map((link, idx) => {
                        const isSource = link.source === selectedNode.id;
                        const otherNodeId = isSource ? link.target : link.source;
                        const otherNode = filteredGraphData.nodes.find(n => n.id === otherNodeId);
                        return (
                          <div key={idx} className="flex items-center gap-2 text-xs p-1.5 rounded bg-slate-800/30">
                            <span className="text-slate-500">{isSource ? '\u2192' : '\u2190'}</span>
                            <span className="text-slate-300 flex-1 truncate">{otherNode?.name ?? otherNodeId}</span>
                            <span className="text-purple-400 text-[10px]">{link.relationship}</span>
                            {link.riskTransfer > 0 && (
                              <span className="text-red-400 text-[10px]">+{link.riskTransfer}</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    {hasMore && (
                      <button
                        onClick={() => setShowAllConnections(prev => !prev)}
                        className="mt-1.5 w-full py-1 rounded text-[10px] text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-colors"
                      >
                        {showAllConnections
                          ? `접기 (${allConnections.length}개)`
                          : `+ ${allConnections.length - 5}개 더 보기`}
                      </button>
                    )}
                  </>
                );
              })()}
            </div>

            {/* Recent events for this node */}
            {selectedNode.nodeType !== 'deal' && state.recentEvents.length > 0 && (
              <div className="mb-3">
                <h4 className="text-xs text-slate-500 font-semibold mb-2 uppercase tracking-wider">
                  Recent Events
                </h4>
                <div className="space-y-1.5">
                  {state.recentEvents
                    .filter(e =>
                      e.title.includes(selectedNode.name) ||
                      e.entityId === selectedNode.id ||
                      e.summary?.includes(selectedNode.name)
                    )
                    .slice(0, 3)
                    .map((event) => (
                      <div key={event.id} className="p-2 rounded-lg bg-slate-800/30 border border-white/5">
                        <p className="text-xs text-white font-medium truncate">{event.title}</p>
                        <div className="flex items-center justify-between mt-1">
                          <span className="text-[10px] text-slate-500">{event.type}</span>
                          <span className={`text-[10px] font-medium ${event.score > 30 ? 'text-red-400' : event.score > 10 ? 'text-yellow-400' : 'text-slate-400'}`}>
                            {event.score > 0 ? '+' : ''}{event.score}점
                          </span>
                        </div>
                      </div>
                    ))
                  }
                  {state.recentEvents.filter(e =>
                    e.title.includes(selectedNode.name) ||
                    e.entityId === selectedNode.id ||
                    e.summary?.includes(selectedNode.name)
                  ).length === 0 && (
                    <p className="text-[10px] text-slate-600">관련 이벤트가 없습니다</p>
                  )}
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-2 mt-4">
              {(selectedNode.nodeType === 'mainCompany' || selectedNode.nodeType === 'relatedCompany') && (
                <button
                  onClick={() => { selectCompany(selectedNode.id); setActiveView('deepdive'); }}
                  className="flex-1 py-2 rounded-lg text-xs font-medium bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 transition-colors border border-purple-500/20"
                >
                  Deep Dive &#8594;
                </button>
              )}
              {selectedNode.nodeType === 'riskCategory' && selectedNode.categoryCode && (
                <button
                  onClick={() => { selectCategory(selectedNode.categoryCode!); setActiveView('deepdive'); }}
                  className="flex-1 py-2 rounded-lg text-xs font-medium bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 transition-colors border border-purple-500/20"
                >
                  카테고리 분석 &#8594;
                </button>
              )}
            </div>
          </GlassCard>
        </motion.div>
      )}

      {/* Link Detail Info */}
      {selectedLink && !selectedNode && (
        <motion.div
          className="absolute right-4 top-4 z-20"
          style={{ width: '280px' }}
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <GlassCard className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-white font-bold text-sm">Relationship Detail</h3>
              <button
                onClick={() => setSelectedLink(null)}
                className="p-1 rounded-lg hover:bg-white/10 transition-colors"
              >
                <span className="text-slate-400 text-sm">&#10005;</span>
              </button>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">관계 유형</span>
                <span className="text-purple-400 font-medium">{selectedLink.relationship}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">라벨</span>
                <span className="text-white">{selectedLink.label}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">의존도</span>
                <span className="text-white">{(selectedLink.dependency * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">리스크 전이</span>
                <span className={selectedLink.riskTransfer > 0 ? 'text-red-400 font-medium' : 'text-slate-400'}>
                  {selectedLink.riskTransfer > 0 ? '+' : ''}{selectedLink.riskTransfer}
                </span>
              </div>
            </div>
          </GlassCard>
        </motion.div>
      )}

      {/* ============================================ */}
      {/* Step 16: 우측 하단 인포 패널 (filteredGraphData 카운트) */}
      {/* ============================================ */}
      <motion.div
        className="absolute right-4 bottom-4 z-10"
        style={{ width: '300px' }}
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.5 }}
      >
        <GlassCard className="p-4">
          {/* 스키마 버전 */}
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-slate-400 font-semibold">Graph DB Schema</span>
            <span
              className="text-[10px] px-2 py-0.5 rounded-full font-semibold"
              style={{
                background: GRADIENTS.purple,
                color: 'white',
              }}
            >
              V5 (5-Node)
            </span>
          </div>

          {/* 노드/엣지 카운트 - Step 16: filteredGraphData */}
          <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-slate-800/40">
            <div className="flex-1 text-center">
              <p className="text-lg font-bold text-purple-400">{filteredGraphData.nodes.length}</p>
              <p className="text-[10px] text-slate-500">Nodes</p>
            </div>
            <div className="w-px h-8 bg-white/10" />
            <div className="flex-1 text-center">
              <p className="text-lg font-bold text-cyan-400">{filteredGraphData.links.length}</p>
              <p className="text-[10px] text-slate-500">Edges</p>
            </div>
          </div>

          {/* 안내 텍스트 */}
          <p className="text-[11px] text-slate-500 mb-2">
            &#128073; 노드를 클릭하면 상세 패널이 열립니다
          </p>

          {/* 전이 공식 */}
          <div className="p-2 rounded-lg bg-slate-800/40 border border-white/5">
            <p className="text-[10px] text-slate-600 mb-1">Risk Propagation Formula:</p>
            <p className="text-[11px] text-slate-400 font-mono">
              전이 점수 = 관련기업 직접점수 x 0.3
            </p>
          </div>
        </GlassCard>
      </motion.div>
    </div>
  );
}
