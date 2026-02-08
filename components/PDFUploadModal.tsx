
import React, { useState, useCallback } from 'react';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onUploadSuccess: (runId: number) => void;
}

const PDFUploadModal: React.FC<Props> = ({ isOpen, onClose, onUploadSuccess }) => {
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setIsDragging(true);
        } else if (e.type === 'dragleave') {
            setIsDragging(false);
        }
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    }, []);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0]);
        }
    };

    const handleFile = async (file: File) => {
        if (file.type !== 'application/pdf') {
            setError('PDF 파일만 업로드 가능합니다.');
            return;
        }
        setError(null);
        setIsUploading(true);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:3001/api/im/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const data = await response.json();
            onUploadSuccess(data.runId);
            onClose();
        } catch (err: any) {
            setError(err.message || '업로드 중 오류가 발생했습니다.');
        } finally {
            setIsUploading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
            <div
                className="bg-white rounded-3xl p-8 w-[500px] shadow-2xl relative overflow-hidden text-center"
                onClick={(e) => e.stopPropagation()}
            >
                <button className="absolute top-4 right-4 text-slate-400 hover:text-slate-600" onClick={onClose}>
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>

                <h3 className="text-2xl font-black text-[#003366] mb-2">IM 보고서 분석</h3>
                <p className="text-sm text-slate-500 mb-8 font-bold">PDF 파일을 업로드하여 AI 정밀 심사를 시작하세요.</p>

                <div
                    className={`border-2 border-dashed rounded-2xl p-12 transition-all ${isDragging ? 'border-[#003366] bg-blue-50' : 'border-slate-300 hover:border-[#003366] hover:bg-slate-50'}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                >
                    {isUploading ? (
                        <div className="flex flex-col items-center gap-4">
                            <div className="w-12 h-12 border-4 border-[#003366]/20 border-t-[#003366] rounded-full animate-spin"></div>
                            <p className="text-sm font-bold text-[#003366] animate-pulse">분석 중...</p>
                        </div>
                    ) : (
                        <>
                            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4 text-3xl">📄</div>
                            <p className="text-slate-600 font-bold mb-2">Drag & Drop PDF here</p>
                            <p className="text-xs text-slate-400 mb-6">최대 20MB</p>
                            <label className="inline-block cursor-pointer px-6 py-3 bg-[#003366] text-white rounded-xl font-bold text-sm hover:bg-[#002244] transition-colors shadow-lg shadow-blue-900/20">
                                파일 찾기
                                <input type="file" className="hidden" accept=".pdf" onChange={handleFileSelect} />
                            </label>
                        </>
                    )}
                </div>

                {error && (
                    <div className="mt-6 p-4 bg-rose-50 text-rose-600 rounded-xl text-sm font-bold border border-rose-100 flex items-center gap-2 justify-center">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        {error}
                    </div>
                )}
            </div>
        </div>
    );
};

export default PDFUploadModal;
