import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { List, Button, Empty, Spin, Dropdown, Modal, Typography } from 'antd';
import { MoreOutlined, ReloadOutlined, MessageOutlined, InfoCircleOutlined, DeleteOutlined } from '@ant-design/icons';
import { getConversations, deleteConversation } from '../../services/conversationApi';

const { Text } = Typography;

export default function ConversationHistoryPanel({ onSelectConversation, refreshTrigger }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { conversationId: activeConvId } = useParams();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const data = await getConversations();
      setConversations(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchConversations(); }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  // 当外部触发刷新时重新拉取
  useEffect(() => {
    if (refreshTrigger > 0) fetchConversations();
  }, [refreshTrigger]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleDelete = async (id) => {
    setDeletingId(id);
    try {
      await deleteConversation(id);
      setConversations(prev => prev.filter(c => c.id !== id));
    } catch (e) {
      console.error(e);
    } finally {
      setDeletingId(null);
    }
  };

  const handleSelect = (id) => {
    if (onSelectConversation) {
      onSelectConversation(id);
      return;
    }
    navigate(`/flow/${id}`);
  };

  return (
    <div style={{ padding: '12px 16px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <MessageOutlined style={{ fontSize: 14, color: 'var(--fc-accent)' }} />
          <Text strong style={{ fontSize: 13 }}>历史对话</Text>
        </div>
        <Button type="text" size="small" icon={<ReloadOutlined />} onClick={fetchConversations} loading={loading} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        <Spin spinning={loading && conversations.length === 0}>
          {!loading && conversations.length === 0 ? (
            <Empty description="暂无历史对话" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              size="small"
              dataSource={conversations}
              renderItem={(conv) => {
                const menuItems = [
                  {
                    key: 'info',
                    icon: <InfoCircleOutlined />,
                    label: '信息',
                    onClick: ({ domEvent }) => {
                      domEvent.stopPropagation();
                      Modal.info({
                        title: conv.name,
                        content: (
                          <div>
                            <p>对话轮次：{conv.round_count ?? conv.rounds?.length ?? 0} 轮</p>
                            <p>创建日期：{new Date(conv.created_at).toLocaleDateString()}</p>
                          </div>
                        ),
                      });
                    },
                  },
                  { type: 'divider' },
                  {
                    key: 'delete',
                    icon: <DeleteOutlined />,
                    label: '删除对话',
                    danger: true,
                    onClick: ({ domEvent }) => {
                      domEvent.stopPropagation();
                      Modal.confirm({
                        title: '确认删除该对话及其关联故障树？',
                        okText: '删除',
                        cancelText: '取消',
                        okButtonProps: { danger: true },
                        onOk: () => handleDelete(conv.id),
                      });
                    },
                  },
                ];
                return (
                  <List.Item
                    className={activeConvId === conv.id ? 'fc-list-item--active' : ''}
                    onClick={() => handleSelect(conv.id)}
                    style={{ padding: '8px 12px', cursor: 'pointer' }}
                    actions={[
                      <Dropdown key="more" menu={{ items: menuItems }} trigger={['click']}
                        placement="bottomRight">
                        <Button type="text" size="small" icon={<MoreOutlined />}
                          onClick={(e) => e.stopPropagation()}
                          loading={deletingId === conv.id}
                          style={{ color: 'var(--fc-sidebar-text-muted)' }} />
                      </Dropdown>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Text style={{ fontSize: 13 }} ellipsis={{ tooltip: conv.name }}>
                          {conv.name}
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
