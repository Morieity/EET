import React, { useState, useEffect } from 'react';
import { List, Button, Tag, Empty, Spin, Popconfirm, Typography } from 'antd';
import { DeleteOutlined, ReloadOutlined, FileTextOutlined } from '@ant-design/icons';
import DocumentUploadPanel from './DocumentUploadPanel';
import { getFiles, deleteFile, openUploadsFolder } from '../../services/fileApi';

const { Text } = Typography;

const STATUS_CONFIG = {
  pending:  { color: 'processing', text: '向量化中' },
  embedded: { color: 'success',    text: '已入库' },
  failed:   { color: 'error',      text: '失败' },
};

export default function FileListPanel() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deletingName, setDeletingName] = useState(null);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const data = await getFiles();
      setFiles(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchFiles(); }, []);

  const handleDelete = async (fileName) => {
    setDeletingName(fileName);
    try {
      await deleteFile(fileName);
      setFiles(prev => prev.filter(f => f.file_name !== fileName));
    } catch (e) {
      console.error(e);
    } finally {
      setDeletingName(null);
    }
  };

  return (
    <div style={{ padding: '12px 16px' }}>
      {/* 上传区域 */}
      <DocumentUploadPanel onUploadSuccess={fetchFiles} />

      {/* 文件列表 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <FileTextOutlined style={{ fontSize: 14, color: '#3498db' }} />
          <Text strong style={{ fontSize: 13 }}>已上传文件</Text>
        </div>
        <Button type="text" size="small" icon={<ReloadOutlined />} onClick={fetchFiles} loading={loading && files.length === 0} />
      </div>

      <Spin spinning={loading && files.length === 0}>
        {!loading && files.length === 0 ? (
          <Empty description="暂无文件" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 16 }} />
        ) : (
          <List
            size="small"
            dataSource={files}
            renderItem={(file) => {
              const sc = STATUS_CONFIG[file.status] || {};
              return (
                <List.Item
                  style={{ padding: '6px 0' }}
                  actions={[
                    <Popconfirm
                      key="del"
                      title="确认删除该文件及其向量数据？"
                      onConfirm={() => handleDelete(file.file_name)}
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{ danger: true }}
                    >
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        loading={deletingName === file.file_name}
                      />
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Text
                        style={{ fontSize: 12, color: '#1890ff', cursor: 'pointer' }}
                        ellipsis={{ tooltip: file.file_name }}
                        onClick={() => openUploadsFolder().catch(() => {})}
                        title="打开文件所在文件夹"
                      >
                        {file.file_name}
                      </Text>
                    }
                    description={
                      <Tag color={sc.color} style={{ fontSize: 10, marginTop: 2 }}>
                        {sc.text || file.status}
                      </Tag>
                    }
                  />
                </List.Item>
              );
            }}
          />
        )}
      </Spin>
    </div>
  );
}
