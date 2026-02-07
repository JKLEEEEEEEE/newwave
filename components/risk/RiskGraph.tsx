/**
 * Step 3. 리스크 모니터링 시스템 - Neo4j 공급망 그래프
 * Graph-First 핵심 컴포넌트
 * v2.0 - 인터렉티브 기능 추가 (줌/팬/드래그)
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { SupplyChainGraph, GraphNode, GraphEdge } from './types';
import { EMOJI_MAP, ZOOM_CONFIG, NODE_SIZE, STATUS_THRESHOLDS } from './constants';
import { getNodeColor, getEdgeColor, getScoreTextClass, screenToCanvas, clamp } from './utils';
import ZoomControls from './ZoomControls';

interface RiskGraphProps {
  data: SupplyChainGraph;
  companyName: string;
}

// 확장 타입 정의
interface ExtendedGraphNode extends GraphNode {
  label?: string;
}

interface ExtendedGraphEdge extends GraphEdge {
  from?: string;
  to?: string;
  riskTransfer?: number;
}

interface ExtendedSupplyChainGraph {
  nodes: ExtendedGraphNode[];
  edges: ExtendedGraphEdge[];
  centerNode?: GraphNode;
  totalPropagatedRisk?: number;
}

// 그래프 상태 인터페이스
interface GraphState {
  scale: number;
  offsetX: number;
  offsetY: number;
  isPanning: boolean;
  isNodeDragging: boolean;
  dragStartX: number;
  dragStartY: number;
  dragNodeId: string | null;
}

const RiskGraph: React.FC<RiskGraphProps> = ({ data, companyName }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 기본 상태
  const [hoveredNode, setHoveredNode] = useState<ExtendedGraphNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<ExtendedGraphNode | null>(null);
  const [nodePositions, setNodePositions] = useState<Map<string, { x: number; y: number }>>(new Map());

  // 인터렉티브 상태
  const [graphState, setGraphState] = useState<GraphState>({
    scale: ZOOM_CONFIG.default,
    offsetX: 0,
    offsetY: 0,
    isPanning: false,
    isNodeDragging: false,
    dragStartX: 0,
    dragStartY: 0,
    dragNodeId: null,
  });

  // 데이터 변환
  const safeData: ExtendedSupplyChainGraph = React.useMemo(() => {
    if (!data) {
      return { nodes: [], edges: [] };
    }

    if (data.nodes && Array.isArray(data.nodes)) {
      return {
        nodes: data.nodes.map(n => ({
          ...n,
          label: n.name || n.label || n.id,
        })),
        edges: data.edges?.map(e => ({
          ...e,
          from: e.source || e.from,
          to: e.target || e.to,
          riskTransfer: e.dependency || e.riskTransfer || 0.3,
        })) || [],
      };
    }

    const nodes: ExtendedGraphNode[] = [];
    const edges: ExtendedGraphEdge[] = [];

    if (data.centerNode) {
      nodes.push({
        ...data.centerNode,
        label: data.centerNode.name || data.centerNode.id,
        type: 'company',
      });
    }

    if (data.suppliers) {
      data.suppliers.forEach((s, idx) => {
        if (s && s.id) {
          nodes.push({
            ...s,
            label: s.name || s.id,
            type: 'supplier',
          });
          if (data.centerNode) {
            edges.push({
              id: `e_s_${idx}`,
              source: s.id,
              target: data.centerNode.id,
              from: s.id,
              to: data.centerNode.id,
              relationship: 'SUPPLIES_TO',
              riskTransfer: (s.riskScore || 50) * 0.01 * (s.tier === 1 ? 0.7 : 0.5),
            });
          }
        }
      });
    }

    if (data.customers) {
      data.customers.forEach((c, idx) => {
        if (c && c.id) {
          nodes.push({
            ...c,
            label: c.name || c.id,
            type: 'customer',
          });
          if (data.centerNode) {
            edges.push({
              id: `e_c_${idx}`,
              source: data.centerNode.id,
              target: c.id,
              from: data.centerNode.id,
              to: c.id,
              relationship: 'SUPPLIES_TO',
              riskTransfer: 0.3,
            });
          }
        }
      });
    }

    if (data.edges) {
      data.edges.forEach(e => {
        if (!edges.find(ex => ex.id === e.id)) {
          edges.push({
            ...e,
            from: e.source || e.from,
            to: e.target || e.to,
            riskTransfer: e.dependency || e.riskTransfer || 0.3,
          });
        }
      });
    }

    return { nodes, edges };
  }, [data]);

  // 노드 타입 스타일
  const getNodeTypeStyle = (type: string) => {
    return {
      emoji: EMOJI_MAP.nodeType[type as keyof typeof EMOJI_MAP.nodeType] || '📦',
      border: EMOJI_MAP.nodeTypeBorder[type as keyof typeof EMOJI_MAP.nodeTypeBorder] || '#64748b',
    };
  };

  const getNodeLabel = (node: ExtendedGraphNode) => {
    return node.label || node.name || node.id;
  };

  const getEdgeTransfer = (edge: ExtendedGraphEdge) => {
    return edge.riskTransfer || edge.dependency || 0.3;
  };

  // 노드 찾기
  const findNodeAtPosition = useCallback((canvasX: number, canvasY: number): ExtendedGraphNode | null => {
    for (const node of safeData.nodes) {
      const pos = nodePositions.get(node.id);
      if (!pos) continue;

      const isCenter = node.type === 'company';
      const radius = isCenter ? NODE_SIZE.center : NODE_SIZE.normal;
      const dist = Math.sqrt((canvasX - pos.x) ** 2 + (canvasY - pos.y) ** 2);

      if (dist <= radius + 5) {
        return node;
      }
    }
    return null;
  }, [safeData.nodes, nodePositions]);

  // 레이아웃 계산
  const calculateLayout = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || safeData.nodes.length === 0) return;

    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;

    const positions = new Map<string, { x: number; y: number }>();

    const centerNode = safeData.nodes.find(n => getNodeLabel(n) === companyName || n.type === 'company') || safeData.nodes[0];
    positions.set(centerNode.id, { x: centerX, y: centerY });

    const otherNodes = safeData.nodes.filter(n => n.id !== centerNode.id);
    const angleStep = (2 * Math.PI) / Math.max(otherNodes.length, 1);
    const radius = Math.min(width, height) * 0.35;

    otherNodes.forEach((node, idx) => {
      const angle = idx * angleStep - Math.PI / 2;
      positions.set(node.id, {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      });
    });

    setNodePositions(positions);
  }, [safeData, companyName]);

  // 캔버스 렌더링
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { scale, offsetX, offsetY } = graphState;

    // 변환 리셋 및 클리어
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 변환 적용 (줌 + 패닝)
    ctx.setTransform(scale, 0, 0, scale, offsetX, offsetY);

    // 엣지 렌더링
    safeData.edges.forEach(edge => {
      const fromId = edge.from || edge.source;
      const toId = edge.to || edge.target;
      const fromPos = nodePositions.get(fromId);
      const toPos = nodePositions.get(toId);
      if (!fromPos || !toPos) return;

      const transfer = getEdgeTransfer(edge);

      ctx.beginPath();
      ctx.moveTo(fromPos.x, fromPos.y);
      ctx.lineTo(toPos.x, toPos.y);
      ctx.strokeStyle = getEdgeColor(transfer);
      ctx.lineWidth = Math.max(1, transfer * 4) / scale;
      ctx.stroke();

      // 화살표
      const angle = Math.atan2(toPos.y - fromPos.y, toPos.x - fromPos.x);
      const arrowLen = 10 / scale;
      const arrowX = toPos.x - (30 / scale) * Math.cos(angle);
      const arrowY = toPos.y - (30 / scale) * Math.sin(angle);

      ctx.beginPath();
      ctx.moveTo(arrowX, arrowY);
      ctx.lineTo(
        arrowX - arrowLen * Math.cos(angle - Math.PI / 6),
        arrowY - arrowLen * Math.sin(angle - Math.PI / 6)
      );
      ctx.moveTo(arrowX, arrowY);
      ctx.lineTo(
        arrowX - arrowLen * Math.cos(angle + Math.PI / 6),
        arrowY - arrowLen * Math.sin(angle + Math.PI / 6)
      );
      ctx.stroke();
    });

    // 노드 렌더링
    safeData.nodes.forEach(node => {
      const pos = nodePositions.get(node.id);
      if (!pos) return;

      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const nodeLabel = getNodeLabel(node);
      const isCenter = nodeLabel === companyName || node.type === 'company';
      const baseRadius = isCenter ? NODE_SIZE.center : NODE_SIZE.normal;
      const nodeRadius = baseRadius + (isHovered ? NODE_SIZE.hoverIncrease : 0);
      const style = getNodeTypeStyle(node.type);

      // 노드 원
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, nodeRadius, 0, 2 * Math.PI);
      ctx.fillStyle = getNodeColor(node.riskScore);
      ctx.fill();
      ctx.strokeStyle = isSelected ? '#3B82F6' : isHovered ? '#fff' : style.border;
      ctx.lineWidth = (isSelected ? 4 : isHovered ? 3 : 2) / scale;
      ctx.stroke();

      // 리스크 점수
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${(isCenter ? 14 : 12)}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.riskScore.toString(), pos.x, pos.y);

      // 레이블
      ctx.fillStyle = '#e2e8f0';
      ctx.font = `${11}px sans-serif`;
      ctx.fillText(nodeLabel, pos.x, pos.y + nodeRadius + 12);
    });

  }, [safeData, nodePositions, hoveredNode, selectedNode, companyName, graphState]);

  // 휠 줌 핸들러
  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault();

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    setGraphState(prev => {
      const delta = -e.deltaY * ZOOM_CONFIG.wheelSensitivity;
      const newScale = clamp(prev.scale * (1 + delta), ZOOM_CONFIG.min, ZOOM_CONFIG.max);

      // 마우스 위치 중심으로 확대
      const scaleRatio = newScale / prev.scale;
      const newOffsetX = mouseX - (mouseX - prev.offsetX) * scaleRatio;
      const newOffsetY = mouseY - (mouseY - prev.offsetY) * scaleRatio;

      return {
        ...prev,
        scale: newScale,
        offsetX: newOffsetX,
        offsetY: newOffsetY,
      };
    });
  }, []);

  // 마우스 다운 핸들러
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const canvasPos = screenToCanvas(mouseX, mouseY, graphState.scale, graphState.offsetX, graphState.offsetY);
    const clickedNode = findNodeAtPosition(canvasPos.x, canvasPos.y);

    if (clickedNode) {
      // 노드 드래그 시작
      setGraphState(prev => ({
        ...prev,
        isNodeDragging: true,
        dragNodeId: clickedNode.id,
        dragStartX: canvasPos.x,
        dragStartY: canvasPos.y,
      }));
    } else {
      // 화면 패닝 시작
      setGraphState(prev => ({
        ...prev,
        isPanning: true,
        dragStartX: e.clientX - prev.offsetX,
        dragStartY: e.clientY - prev.offsetY,
      }));
    }
  }, [graphState.scale, graphState.offsetX, graphState.offsetY, findNodeAtPosition]);

  // 마우스 이동 핸들러
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (graphState.isPanning) {
      // 화면 패닝
      setGraphState(prev => ({
        ...prev,
        offsetX: e.clientX - prev.dragStartX,
        offsetY: e.clientY - prev.dragStartY,
      }));
    } else if (graphState.isNodeDragging && graphState.dragNodeId) {
      // 노드 드래그
      const canvasPos = screenToCanvas(mouseX, mouseY, graphState.scale, graphState.offsetX, graphState.offsetY);
      setNodePositions(prev => {
        const newPositions = new Map(prev);
        newPositions.set(graphState.dragNodeId!, { x: canvasPos.x, y: canvasPos.y });
        return newPositions;
      });
    } else {
      // 호버 검사
      const canvasPos = screenToCanvas(mouseX, mouseY, graphState.scale, graphState.offsetX, graphState.offsetY);
      const hovered = findNodeAtPosition(canvasPos.x, canvasPos.y);
      setHoveredNode(hovered);
      canvas.style.cursor = hovered ? 'pointer' : graphState.isPanning ? 'grabbing' : 'grab';
    }
  }, [graphState, findNodeAtPosition]);

  // 마우스 업 핸들러
  const handleMouseUp = useCallback(() => {
    setGraphState(prev => ({
      ...prev,
      isPanning: false,
      isNodeDragging: false,
      dragNodeId: null,
    }));
  }, []);

  // 클릭 핸들러
  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (graphState.isPanning || graphState.isNodeDragging) return;

    if (hoveredNode) {
      setSelectedNode(hoveredNode === selectedNode ? null : hoveredNode);
    }
  }, [hoveredNode, selectedNode, graphState.isPanning, graphState.isNodeDragging]);

  // 키보드 핸들러
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    const PAN_STEP = 50;

    switch (e.key) {
      case 'ArrowUp':
        setGraphState(prev => ({ ...prev, offsetY: prev.offsetY + PAN_STEP }));
        break;
      case 'ArrowDown':
        setGraphState(prev => ({ ...prev, offsetY: prev.offsetY - PAN_STEP }));
        break;
      case 'ArrowLeft':
        setGraphState(prev => ({ ...prev, offsetX: prev.offsetX + PAN_STEP }));
        break;
      case 'ArrowRight':
        setGraphState(prev => ({ ...prev, offsetX: prev.offsetX - PAN_STEP }));
        break;
      case '+':
      case '=':
        setGraphState(prev => ({
          ...prev,
          scale: clamp(prev.scale + ZOOM_CONFIG.step, ZOOM_CONFIG.min, ZOOM_CONFIG.max),
        }));
        break;
      case '-':
        setGraphState(prev => ({
          ...prev,
          scale: clamp(prev.scale - ZOOM_CONFIG.step, ZOOM_CONFIG.min, ZOOM_CONFIG.max),
        }));
        break;
      case '0':
        setGraphState(prev => ({
          ...prev,
          scale: ZOOM_CONFIG.default,
          offsetX: 0,
          offsetY: 0,
        }));
        break;
      case 'Escape':
        setSelectedNode(null);
        break;
    }
  }, []);

  // 줌 컨트롤 핸들러
  const handleZoomIn = useCallback(() => {
    setGraphState(prev => ({
      ...prev,
      scale: clamp(prev.scale + ZOOM_CONFIG.step, ZOOM_CONFIG.min, ZOOM_CONFIG.max),
    }));
  }, []);

  const handleZoomOut = useCallback(() => {
    setGraphState(prev => ({
      ...prev,
      scale: clamp(prev.scale - ZOOM_CONFIG.step, ZOOM_CONFIG.min, ZOOM_CONFIG.max),
    }));
  }, []);

  const handleZoomReset = useCallback(() => {
    setGraphState(prev => ({
      ...prev,
      scale: ZOOM_CONFIG.default,
      offsetX: 0,
      offsetY: 0,
    }));
  }, []);

  // 이벤트 리스너 등록
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.addEventListener('wheel', handleWheel, { passive: false });
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      canvas.removeEventListener('wheel', handleWheel);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleWheel, handleKeyDown, handleMouseUp]);

  // 레이아웃 계산
  useEffect(() => {
    calculateLayout();
  }, [calculateLayout]);

  // 렌더링
  useEffect(() => {
    render();
  }, [render]);

  // 리사이즈 대응
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const container = canvas.parentElement;
      if (!container) return;

      canvas.width = container.clientWidth;
      canvas.height = 400;
      calculateLayout();
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [calculateLayout]);

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700" ref={containerRef}>
      {/* 헤더 */}
      <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
        <h2 className="font-semibold flex items-center gap-2">
          <span>{EMOJI_MAP.category.SUPPLY}</span>
          <span>SUPPLY CHAIN GRAPH</span>
          <span className="text-xs text-cyan-400 ml-2">Neo4j Powered</span>
        </h2>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span>노드: {safeData.nodes.length}</span>
          <span>·</span>
          <span>관계: {safeData.edges.length}</span>
        </div>
      </div>

      {/* 범례 */}
      <div className="px-4 py-2 border-b border-slate-700 flex flex-wrap gap-4 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-slate-400">노드 타입:</span>
          <span className="flex items-center gap-1">{EMOJI_MAP.nodeType.company} 대상</span>
          <span className="flex items-center gap-1">{EMOJI_MAP.nodeType.supplier} 공급사</span>
          <span className="flex items-center gap-1">{EMOJI_MAP.nodeType.customer} 고객사</span>
          <span className="flex items-center gap-1">{EMOJI_MAP.nodeType.subsidiary} 자회사</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-400">리스크:</span>
          <span className="flex items-center gap-1">
            <span>{EMOJI_MAP.status.PASS}</span>
            &lt;{STATUS_THRESHOLDS.WARNING.min}
          </span>
          <span className="flex items-center gap-1">
            <span>{EMOJI_MAP.status.WARNING}</span>
            {STATUS_THRESHOLDS.WARNING.min}-{STATUS_THRESHOLDS.WARNING.max}
          </span>
          <span className="flex items-center gap-1">
            <span>{EMOJI_MAP.status.FAIL}</span>
            &gt;{STATUS_THRESHOLDS.WARNING.max}
          </span>
        </div>
      </div>

      {/* 캔버스 */}
      <div className="relative">
        <canvas
          ref={canvasRef}
          className="w-full"
          style={{ cursor: graphState.isPanning ? 'grabbing' : 'grab' }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onClick={handleClick}
        />

        {/* 줌 컨트롤 */}
        <ZoomControls
          scale={graphState.scale}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onReset={handleZoomReset}
        />

        {/* 호버 툴팁 */}
        {hoveredNode && !graphState.isPanning && !graphState.isNodeDragging && (
          <div className="absolute top-4 left-4 bg-slate-900/95 border border-slate-600 rounded-lg p-3 max-w-xs">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">{getNodeTypeStyle(hoveredNode.type || 'company').emoji}</span>
              <span className="font-medium">{getNodeLabel(hoveredNode)}</span>
            </div>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">리스크 점수</span>
                <span className={`font-bold ${getScoreTextClass(hoveredNode.riskScore)}`}>
                  {hoveredNode.riskScore}점
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">타입</span>
                <span>{hoveredNode.type}</span>
              </div>
              {(hoveredNode.sector || hoveredNode.metadata?.industry) && (
                <div className="flex justify-between">
                  <span className="text-slate-400">산업</span>
                  <span>{hoveredNode.sector || hoveredNode.metadata?.industry}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 선택된 노드 상세 */}
      {selectedNode && (
        <div className="px-4 py-3 border-t border-slate-700 bg-slate-700/50">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium flex items-center gap-2">
              <span>{getNodeTypeStyle(selectedNode.type || 'company').emoji}</span>
              {getNodeLabel(selectedNode)}
            </span>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-slate-400 hover:text-white"
              aria-label="닫기"
            >
              ✕
            </button>
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-slate-400 text-xs">리스크 점수</span>
              <div className={`text-lg font-bold ${getScoreTextClass(selectedNode.riskScore)}`}>
                {selectedNode.riskScore}점
              </div>
            </div>
            <div>
              <span className="text-slate-400 text-xs">연결 관계</span>
              <div className="text-lg font-bold text-cyan-400">
                {safeData.edges.filter(e =>
                  (e.from || e.source) === selectedNode.id || (e.to || e.target) === selectedNode.id
                ).length}개
              </div>
            </div>
            <div>
              <span className="text-slate-400 text-xs">전이 영향</span>
              <div className="text-lg font-bold text-orange-400">
                {Math.round(
                  safeData.edges
                    .filter(e => (e.from || e.source) === selectedNode.id)
                    .reduce((sum, e) => sum + getEdgeTransfer(e), 0) * 100
                )}%
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RiskGraph;
