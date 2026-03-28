import React, { useState, useRef } from 'react';
import { Panel } from '@xyflow/react';

export default function DocumentUploadPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const uploadFile = async (file) => {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      setUploadResult({ error: '请选择 PDF 格式文件' });
      return;
    }

    setIsUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (response.ok) {
        setUploadResult({ success: true, ...data });
      } else {
        setUploadResult({ error: data.message || `上传失败 (${response.status})` });
      }
    } catch (error) {
      setUploadResult({ error: `网络错误: ${error.message}` });
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) uploadFile(file);
    e.target.value = null;
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  if (!isOpen) {
    return (
      <Panel position="bottom-right" style={{ marginBottom: '10px', marginRight: '10px' }}>
        <button
          onClick={() => setIsOpen(true)}
          style={{
            width: '50px',
            height: '50px',
            borderRadius: '50%',
            background: '#3498db',
            color: 'white',
            border: 'none',
            boxShadow: '0 4px 8px rgba(0,0,0,0.2)',
            cursor: 'pointer',
            fontSize: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          title="上传知识库文档"
        >
          📄
        </button>
      </Panel>
    );
  }

  return (
    <Panel position="bottom-right" style={{ marginBottom: '10px', marginRight: '10px' }}>
      <div style={{
        width: '320px',
        background: 'white',
        borderRadius: '12px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
        border: '1px solid #eee',
        overflow: 'hidden',
      }}>
        {/* 标题栏 */}
        <div style={{
          background: '#3498db',
          color: 'white',
          padding: '10px 15px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontWeight: 'bold',
          fontSize: '14px',
        }}>
          <span>📄 知识库文档上传</span>
          <button
            onClick={() => setIsOpen(false)}
            style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', fontSize: '18px' }}
          >
            ▼
          </button>
        </div>

        <div style={{ padding: '15px' }}>
          {/* 拖拽上传区域 */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${dragOver ? '#3498db' : '#ccc'}`,
              borderRadius: '8px',
              padding: '20px',
              textAlign: 'center',
              cursor: 'pointer',
              background: dragOver ? '#eaf4fd' : '#fafafa',
              transition: 'all 0.2s',
            }}
          >
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>
              {isUploading ? '⏳' : '📁'}
            </div>
            <div style={{ fontSize: '13px', color: '#666' }}>
              {isUploading ? '正在上传处理中...' : '点击或拖拽 PDF 文件到此处'}
            </div>
            <div style={{ fontSize: '11px', color: '#999', marginTop: '4px' }}>
              支持设备手册、故障报告等 PDF 文档
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />

          {/* 上传结果 */}
          {uploadResult && (
            <div style={{
              marginTop: '12px',
              padding: '10px',
              borderRadius: '6px',
              fontSize: '13px',
              background: uploadResult.error ? '#fdecea' : '#e8f5e9',
              color: uploadResult.error ? '#c62828' : '#2e7d32',
              border: `1px solid ${uploadResult.error ? '#ef9a9a' : '#a5d6a7'}`,
            }}>
              {uploadResult.error ? (
                <div>❌ {uploadResult.error}</div>
              ) : (
                <div>
                  <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>✅ 上传成功</div>
                  <div>📄 文件: {uploadResult.filename}</div>
                  <div>📊 总切片: {uploadResult.total_chunks}</div>
                  <div>✅ 入库: {uploadResult.persisted_chunks}</div>
                  <div>🔄 去重跳过: {uploadResult.deduplicated_chunks}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}
