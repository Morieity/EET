import React, { useState, useRef } from 'react';
import { Upload, Typography, Alert, Tag } from 'antd';
import { InboxOutlined, FileTextOutlined, CheckCircleOutlined, SyncOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { uploadFile } from '../../services/fileApi';

const { Dragger } = Upload;
const { Text } = Typography;

const ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt', '.md'];

export default function DocumentUploadPanel({ onUploadSuccess }) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [fileStatus, setFileStatus] = useState(null); // 'pending' | 'embedded' | 'failed'
  const sseRef = useRef(null);

  const watchStatus = (fileName) => {
    if (sseRef.current) sseRef.current.close();
    const sse = new EventSource(`/api/files/${encodeURIComponent(fileName)}/status`);
    sseRef.current = sse;
    sse.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        const status = data.status;
        setFileStatus(status);
        if (status === 'embedded' || status === 'failed') {
          sse.close();
        }
      } catch {}
    };
    sse.onerror = () => sse.close();
  };

  const customUpload = async ({ file, onSuccess, onError }) => {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setUploadResult({ error: `不支持的文件类型，请选择：${ALLOWED_EXTENSIONS.join(', ')}` });
      onError(new Error('Invalid format'));
      return;
    }

    setIsUploading(true);
    setUploadResult(null);
    setFileStatus(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await uploadFile(formData);
      setUploadResult({ success: true, file_name: data.file_name, file_id: data.id });
      setFileStatus(data.status);
      onSuccess(data);
      watchStatus(data.file_name);
      if (onUploadSuccess) onUploadSuccess();
    } catch (error) {
      setUploadResult({ error: error.message });
      onError(error);
    } finally {
      setIsUploading(false);
    }
  };

  const statusInfo = {
    pending:  { icon: <SyncOutlined spin />,        color: 'processing', text: '向量化中...' },
    embedded: { icon: <CheckCircleOutlined />,       color: 'success',    text: '已入知识库' },
    failed:   { icon: <CloseCircleOutlined />,       color: 'error',      text: '处理失败' },
  };

  return (
    <div style={{ padding: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <FileTextOutlined style={{ fontSize: 16, color: '#3498db' }} />
        <Text strong style={{ fontSize: 14 }}>知识库文档</Text>
      </div>

      <Dragger
        customRequest={customUpload}
        accept={ALLOWED_EXTENSIONS.join(',')}
        showUploadList={false}
        disabled={isUploading}
        style={{
          background: '#fafbfc',
          borderColor: '#d9d9d9',
          borderRadius: 8,
        }}
      >
        <p style={{ fontSize: 28, marginBottom: 8, color: '#3498db' }}>
          <InboxOutlined />
        </p>
        <p style={{ fontSize: 13, color: '#666', margin: 0 }}>
          {isUploading ? '正在上传...' : '点击或拖拽文件上传'}
        </p>
        <p style={{ fontSize: 11, color: '#bbb', margin: '4px 0 0' }}>
          支持 PDF、Word、TXT、Markdown
        </p>
      </Dragger>

      {uploadResult && uploadResult.error && (
        <Alert
          type="error"
          message={uploadResult.error}
          showIcon
          closable
          onClose={() => setUploadResult(null)}
          style={{ marginTop: 12, borderRadius: 6, fontSize: 12 }}
        />
      )}

      {uploadResult && uploadResult.success && (
        <div style={{
          marginTop: 12,
          padding: '12px',
          background: '#f6ffed',
          borderRadius: 8,
          border: '1px solid #b7eb8f',
        }}>
          <Text strong style={{ fontSize: 12, color: '#52c41a', display: 'block', marginBottom: 8 }}>
            <CheckCircleOutlined /> 上传成功 — {uploadResult.file_name}
          </Text>
          {fileStatus && statusInfo[fileStatus] && (
            <Tag
              icon={statusInfo[fileStatus].icon}
              color={statusInfo[fileStatus].color}
              style={{ fontSize: 12 }}
            >
              {statusInfo[fileStatus].text}
            </Tag>
          )}
        </div>
      )}
    </div>
  );
}
