import React, { useState, useEffect, useCallback } from 'react';

interface CriteriaRow {
  id: number;
  module: string;
  category: string;
  item: string;
  score_1: string;
  score_2: string;
  score_3: string;
  score_4: string;
  score_5: string;
  source: string;
}

const EMPTY_ROW: Omit<CriteriaRow, 'id'> = {
  module: '', category: '', item: '',
  score_1: '', score_2: '', score_3: '', score_4: '', score_5: '',
  source: '',
};

const API_BASE = 'http://localhost:3001';

const ScreeningCriteriaManager: React.FC = () => {
  const [rows, setRows] = useState<CriteriaRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editData, setEditData] = useState<Omit<CriteriaRow, 'id'>>(EMPTY_ROW);
  const [addingNew, setAddingNew] = useState(false);
  const [newData, setNewData] = useState<Omit<CriteriaRow, 'id'>>(EMPTY_ROW);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/screening-criteria`);
      const data = await res.json();
      setRows(data);
    } catch (e) {
      console.error('Failed to fetch criteria:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleEdit = (row: CriteriaRow) => {
    setEditingId(row.id);
    setEditData({ module: row.module, category: row.category, item: row.item, score_1: row.score_1, score_2: row.score_2, score_3: row.score_3, score_4: row.score_4, score_5: row.score_5, source: row.source });
  };

  const handleSave = async () => {
    if (!editingId) return;
    try {
      await fetch(`${API_BASE}/api/screening-criteria/${editingId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editData),
      });
      setEditingId(null);
      fetchData();
    } catch (e) { console.error('Save failed:', e); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('이 항목을 삭제하시겠습니까?')) return;
    try {
      await fetch(`${API_BASE}/api/screening-criteria/${id}`, { method: 'DELETE' });
      fetchData();
    } catch (e) { console.error('Delete failed:', e); }
  };

  const handleAdd = async () => {
    if (!newData.module || !newData.category || !newData.item) return;
    try {
      await fetch(`${API_BASE}/api/screening-criteria`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newData),
      });
      setAddingNew(false);
      setNewData(EMPTY_ROW);
      fetchData();
    } catch (e) { console.error('Add failed:', e); }
  };

  // Group rows by module
  const grouped = rows.reduce<Record<string, CriteriaRow[]>>((acc, row) => {
    if (!acc[row.module]) acc[row.module] = [];
    acc[row.module].push(row);
    return acc;
  }, {});

  const modules = Object.keys(grouped);

  const renderCell = (row: CriteriaRow, field: keyof Omit<CriteriaRow, 'id'>, width: string) => {
    if (editingId === row.id) {
      return (
        <input
          className="w-full px-1.5 py-1 text-[11px] border border-blue-400 bg-blue-50 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
          value={(editData as any)[field]}
          onChange={(e) => setEditData(prev => ({ ...prev, [field]: e.target.value }))}
        />
      );
    }
    return <span className="text-[11px] text-slate-700">{(row as any)[field]}</span>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-100">
        <div className="text-sm text-slate-500">평가 기준표 로딩 중...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-100 font-sans">
      <div className="flex-1 px-6 pt-6 pb-2 overflow-y-auto custom-scrollbar">
        <div className="w-full max-w-[1200px] mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-black text-slate-900">평가 기준표 관리</h2>
              <p className="text-[11px] text-slate-500 mt-0.5">Screening Criteria Management — {rows.length}개 항목</p>
            </div>
            <button
              onClick={() => { setAddingNew(true); setNewData({ ...EMPTY_ROW, module: modules[0] || '' }); }}
              className="px-4 py-2 bg-[#003366] text-white text-xs font-bold rounded-lg hover:bg-[#004488] transition-colors shadow-sm"
            >
              + 항목 추가
            </button>
          </div>

          {/* Add New Row Form */}
          {addingNew && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 shadow-sm">
              <div className="text-xs font-bold text-blue-800 mb-3">새 항목 추가</div>
              <div className="grid grid-cols-3 gap-2 mb-2">
                <input placeholder="모듈 (예: 1. 상환능력)" className="px-2 py-1.5 text-[11px] border border-blue-300 rounded bg-white" value={newData.module} onChange={e => setNewData(p => ({ ...p, module: e.target.value }))} />
                <input placeholder="카테고리" className="px-2 py-1.5 text-[11px] border border-blue-300 rounded bg-white" value={newData.category} onChange={e => setNewData(p => ({ ...p, category: e.target.value }))} />
                <input placeholder="항목명" className="px-2 py-1.5 text-[11px] border border-blue-300 rounded bg-white" value={newData.item} onChange={e => setNewData(p => ({ ...p, item: e.target.value }))} />
              </div>
              <div className="grid grid-cols-5 gap-2 mb-2">
                <input placeholder="1점 기준" className="px-2 py-1.5 text-[11px] border border-blue-300 rounded bg-white" value={newData.score_1} onChange={e => setNewData(p => ({ ...p, score_1: e.target.value }))} />
                <input placeholder="2점 기준" className="px-2 py-1.5 text-[11px] border border-blue-300 rounded bg-white" value={newData.score_2} onChange={e => setNewData(p => ({ ...p, score_2: e.target.value }))} />
                <input placeholder="3점 기준" className="px-2 py-1.5 text-[11px] border border-blue-300 rounded bg-white" value={newData.score_3} onChange={e => setNewData(p => ({ ...p, score_3: e.target.value }))} />
                <input placeholder="4점 기준" className="px-2 py-1.5 text-[11px] border border-blue-300 rounded bg-white" value={newData.score_4} onChange={e => setNewData(p => ({ ...p, score_4: e.target.value }))} />
                <input placeholder="5점 기준" className="px-2 py-1.5 text-[11px] border border-blue-300 rounded bg-white" value={newData.score_5} onChange={e => setNewData(p => ({ ...p, score_5: e.target.value }))} />
              </div>
              <div className="flex items-center gap-2">
                <input placeholder="출처" className="px-2 py-1.5 text-[11px] border border-blue-300 rounded bg-white w-32" value={newData.source} onChange={e => setNewData(p => ({ ...p, source: e.target.value }))} />
                <button onClick={handleAdd} className="px-3 py-1.5 bg-[#003366] text-white text-[11px] font-bold rounded hover:bg-[#004488]">저장</button>
                <button onClick={() => setAddingNew(false)} className="px-3 py-1.5 bg-slate-200 text-slate-600 text-[11px] font-bold rounded hover:bg-slate-300">취소</button>
              </div>
            </div>
          )}

          {/* Module Groups */}
          {modules.map((mod) => (
            <div key={mod} className="mb-4">
              <div className="bg-[#003366] text-white px-4 py-2.5 rounded-t-lg font-bold text-xs tracking-wide">
                {mod}
              </div>
              <div className="bg-white border border-slate-200 border-t-0 rounded-b-lg shadow-sm overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="px-3 py-2 text-[10px] font-bold text-slate-500 text-left w-[100px]">카테고리</th>
                      <th className="px-3 py-2 text-[10px] font-bold text-slate-500 text-left w-[160px]">항목</th>
                      <th className="px-2 py-2 text-[10px] font-bold text-slate-500 text-center w-[100px]">1점</th>
                      <th className="px-2 py-2 text-[10px] font-bold text-slate-500 text-center w-[100px]">2점</th>
                      <th className="px-2 py-2 text-[10px] font-bold text-slate-500 text-center w-[100px]">3점</th>
                      <th className="px-2 py-2 text-[10px] font-bold text-slate-500 text-center w-[100px]">4점</th>
                      <th className="px-2 py-2 text-[10px] font-bold text-slate-500 text-center w-[100px]">5점</th>
                      <th className="px-2 py-2 text-[10px] font-bold text-slate-500 text-center w-[60px]">출처</th>
                      <th className="px-2 py-2 text-[10px] font-bold text-slate-500 text-center w-[80px]">관리</th>
                    </tr>
                  </thead>
                  <tbody>
                    {grouped[mod].map((row) => (
                      <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                        <td className="px-3 py-2">{renderCell(row, 'category', '100px')}</td>
                        <td className="px-3 py-2">{renderCell(row, 'item', '160px')}</td>
                        <td className="px-2 py-2 text-center">{renderCell(row, 'score_1', '100px')}</td>
                        <td className="px-2 py-2 text-center">{renderCell(row, 'score_2', '100px')}</td>
                        <td className="px-2 py-2 text-center">{renderCell(row, 'score_3', '100px')}</td>
                        <td className="px-2 py-2 text-center">{renderCell(row, 'score_4', '100px')}</td>
                        <td className="px-2 py-2 text-center">{renderCell(row, 'score_5', '100px')}</td>
                        <td className="px-2 py-2 text-center">{renderCell(row, 'source', '60px')}</td>
                        <td className="px-2 py-2 text-center">
                          {editingId === row.id ? (
                            <div className="flex gap-1 justify-center">
                              <button onClick={handleSave} className="text-[10px] px-2 py-0.5 bg-emerald-500 text-white rounded hover:bg-emerald-600">저장</button>
                              <button onClick={() => setEditingId(null)} className="text-[10px] px-2 py-0.5 bg-slate-300 text-slate-600 rounded hover:bg-slate-400">취소</button>
                            </div>
                          ) : (
                            <div className="flex gap-1 justify-center">
                              <button onClick={() => handleEdit(row)} className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded hover:bg-slate-200">수정</button>
                              <button onClick={() => handleDelete(row.id)} className="text-[10px] px-2 py-0.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded">삭제</button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}

          {/* Footer */}
          <div className="text-center py-4">
            <span className="inline-block px-4 py-1 bg-slate-50 rounded text-[9px] text-slate-400 font-bold tracking-[0.2em] uppercase">
              JB Financial Group &bull; Screening Criteria &bull; Internal Use Only
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScreeningCriteriaManager;
