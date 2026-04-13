import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { List, Button, Empty, Spin, Dropdown, Modal, Typography, message } from 'antd';
import { MoreOutlined, ReloadOutlined, ApartmentOutlined, InfoCircleOutlined, DeleteOutlined } from '@ant-design/icons';
import { getFaultTrees, deleteFaultTree } from '../../services/faultTreeApi';

const { Text } = Typography;

export default function FaultTreeLibraryPanel({ onLoadTree }) {
  const navigate = useNavigate();
  const [trees, setTrees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const fetchTrees = async () => {
    setLoading(true);
    try {
      const data = await getFaultTrees();
      setTrees(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTrees(); }, []);

  const handleLoad = (tree) => {
    if (onLoadTree) {
      onLoadTree(tree);
      return;
    }

    if (!tree.conversation_id) {
      message.warning('该故障树未关联对话，暂不支持通过页面路由打开');
      return;
    }

    navigate(`/flow/${tree.conversation_id}/${tree.id}`);
  };

  const handleDelete = async (id) => {
    setDeletingId(id);
    try {
      await deleteFaultTree(id);
      setTrees(prev => prev.filter(t => t.id !== id));
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
          <ApartmentOutlined style={{ fontSize: 14, color: 'var(--fc-accent)' }} />
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
              renderItem={(tree) => {
                const menuItems = [
                  {
                    key: 'info',
                    icon: <InfoCircleOutlined />,
                    label: '信息',
                    onClick: ({ domEvent }) => {
                      domEvent.stopPropagation();
                      Modal.info({
                        title: tree.name,
                        content: (
                          <div>
                            <p>节点数：{tree.nodes?.length || 0}</p>
                            <p>创建日期：{new Date(tree.created_at).toLocaleDateString()}</p>
                          </div>
                        ),
                      });
                    },
                  },
                  { type: 'divider' },
                  {
                    key: 'delete',
                    icon: <DeleteOutlined />,
                    label: '删除故障树',
                    danger: true,
                    onClick: ({ domEvent }) => {
                      domEvent.stopPropagation();
                      Modal.confirm({
                        title: '确认删除该故障树？',
                        okText: '删除',
                        cancelText: '取消',
                        okButtonProps: { danger: true },
                        onOk: () => handleDelete(tree.id),
                      });
                    },
                  },
                ];
                return (
                  <List.Item
                    onClick={() => handleLoad(tree)}
                    style={{ padding: '8px 12px', cursor: 'pointer' }}
                    actions={[
                      <Dropdown key="more" menu={{ items: menuItems }} trigger={['click']}
                        placement="bottomRight">
                        <Button type="text" size="small" icon={<MoreOutlined />}
                          onClick={(e) => e.stopPropagation()}
                          loading={deletingId === tree.id}
                          style={{ color: 'var(--fc-sidebar-text-muted)' }} />
                      </Dropdown>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Text style={{ fontSize: 13 }} ellipsis={{ tooltip: tree.name }}>
                          {tree.name}
                        </Text>
                      }
                    />
                  </List.Item>
                );
              }}
            />
          )}
        </Spin>
      </div>
    </div>
  );
}
