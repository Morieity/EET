import React, { useState, useRef } from 'react';
import { Button, Upload, Typography, Space, Alert, Statistic, Row, Col } from 'antd';
import { InboxOutlined, FileTextOutlined, CheckCircleOutlined, SyncOutlined } from '@ant-design/icons';

const { Dragger } = Upload;
const { Text } = Typography;

export default function DocumentUploadPanel() {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  const customUpload = async ({ file, onSuccess, onError }) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadResult({ error: '请选择 PDF 格式文件' });
      onError(new Error('Invalid format'));
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
        onSuccess(data);
      } else {
        setUploadResult({ error: data.message || `上传失败 (${response.status})` });
        onError(new Error(data.message));
      }
    } catch (error) {
      setUploadResult({ error: `网络错误: ${error.message}` });
      onError(error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div style={{ padding: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <FileTextOutlined style={{ fontSize: 16, color: '#3498db' }} />
        <Text strong style={{ fontSize: 14 }}>知识库文档</Text>
      </div>

      <Dragger
        customRequest={customUpload}
        accept=".pdf"
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
          {isUploading ? '正在处理中...' : '点击或拖拽 PDF 文件上传'}
        </p>
        <p style={{ fontSize: 11, color: '#bbb', margin: '4px 0 0' }}>
          支持设备手册、故障报告等
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
            <CheckCircleOutlined /> 上传成功 — {uploadResult.filename}
          </Text>
          <Row gutter={8}>
            <Col span={8}>
              <Statistic title={<span style={{ fontSize: 10 }}>总切片</span>} value={uploadResult.total_chunks} valueStyle={{ fontSize: 16, color: '#1890ff' }} />
            </Col>
            <Col span={8}>
              <Statistic title={<span style={{ fontSize: 10 }}>入库</span>} value={uploadResult.persisted_chunks} valueStyle={{ fontSize: 16, color: '#52c41a' }} />
            </Col>
            <Col span={8}>
              <Statistic title={<span style={{ fontSize: 10 }}>去重</span>} value={uploadResult.deduplicated_chunks} valueStyle={{ fontSize: 16, color: '#faad14' }} />
            </Col>
          </Row>
        </div>
      )}
    </div>
  );
}
