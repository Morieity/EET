import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { List, Button, Empty, Spin, Popconfirm, Typography, message } from 'antd';
import { DeleteOutlined, ReloadOutlined, ApartmentOutlined, ImportOutlined } from '@ant-design/icons';

const { Text } = Typography;

export default function FaultTreeLibraryPanel({ onLoadTree }) {
  const navigate = useNavigate();
  const [trees, setTrees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [loadingId, setLoadingId] = useState(null);

  const fetchTrees = async () => {
    setLoading(true);
    try {
      const resp = await fetch('/api/fault-trees');
      if (resp.ok) setTrees(await resp.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTrees(); }, []);

  const handleLoad = async (tree) => {
    setLoadingId(tree.id);
    if (onLoadTree) {
      onLoadTree(tree);
      setLoadingId(null);
      return;
    }

    if (!tree.conversation_id) {
      message.warning('该故障树未关联对话，暂不支持通过页面路由打开');
      setLoadingId(null);
      return;
    }

    navigate(`/flow/${tree.conversation_id}/${tree.id}`);
    setLoadingId(null);
  };

  const handleDelete = async (id) => {
    setDeletingId(id);
    try {
      const resp = await fetch(`/api/fault-trees/${encodeURIComponent(id)}`, { method: 'DELETE' });
      if (resp.ok) setTrees(prev => prev.filter(t => t.id !== id));
    } catch (e) {
      console.error(e);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div style={{ padding: '12px 16px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ApartmentOutlined style={{ fontSize: 14, color: '#8e44ad' }} />
          <Text strong style={{ fontSize: 13 }}>故障树库</Text>
        </div>
        <Button type="text" size="small" icon={<ReloadOutlined />} onClick={fetchTrees} loading={loading} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        <Spin spinning={loading && trees.length === 0}>
          {!loading && trees.length === 0 ? (
            <Empty description="暂无故障树" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              size="small"
              dataSource={trees}
              renderItem={(tree) => (
                <List.Item
                  style={{ padding: '8px 0' }}
                  actions={[
                    <Button
                      key="load"
                      type="text"
                      size="small"
                      icon={<ImportOutlined />}
                      style={{ color: '#8e44ad' }}
                      title="加载到画布"
                      loading={loadingId === tree.id}
                      onClick={() => handleLoad(tree)}
                    />,
                    <Popconfirm
                      key="del"
                      title="确认删除该故障树？"
                      onConfirm={() => handleDelete(tree.id)}
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{ danger: true }}
                    >
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        loading={deletingId === tree.id}
                      />
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Text style={{ fontSize: 12 }} ellipsis={{ tooltip: tree.name }}>
                        {tree.name}
                      </Text>
                    }
                    description={
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {tree.nodes?.length || 0} 节点 · {new Date(tree.created_at).toLocaleDateString()}
                      </Text>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Spin>
      </div>
    </div>
  );
}
