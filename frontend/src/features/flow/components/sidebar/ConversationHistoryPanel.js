import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { List, Button, Empty, Spin, Popconfirm, Typography } from 'antd';
import { DeleteOutlined, ReloadOutlined, MessageOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { getConversations, deleteConversation } from '../../services/conversationApi';

const { Text } = Typography;

export default function ConversationHistoryPanel({ onSelectConversation, refreshTrigger }) {
  const navigate = useNavigate();
  const location = useLocation();
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
          <MessageOutlined style={{ fontSize: 14, color: '#40b586' }} />
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
              renderItem={(conv) => (
                <List.Item
                  style={{ padding: '8px 0' }}
                  actions={[
                    <Button
                      key="continue"
                      type="text"
                      size="small"
                      icon={<PlayCircleOutlined />}
                      style={{ color: '#40b586' }}
                      title="继续该对话"
                      onClick={() => handleSelect(conv.id)}
                    />,
                    <Popconfirm
                      key="del"
                      title="确认删除该对话及其关联故障树？"
                      onConfirm={() => handleDelete(conv.id)}
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{ danger: true }}
                    >
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        loading={deletingId === conv.id}
                      />
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Text style={{ fontSize: 12 }} ellipsis={{ tooltip: conv.name }}>
                        {conv.name}
                      </Text>
                    }
                    description={
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {conv.round_count ?? conv.rounds?.length ?? 0} 轮 · {new Date(conv.created_at).toLocaleDateString()}
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
