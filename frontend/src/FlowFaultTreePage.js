import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { Button, Result, Spin } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import FaultTreeWorkspace from './FaultTreeWorkspace';

export default function FlowFaultTreePage() {
  const navigate = useNavigate();
  const { conversationId, treeId } = useParams();
  const [tree, setTree] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actualConversationId, setActualConversationId] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const loadTree = async () => {
      if (!treeId) {
        setTree(null);
        setLoading(false);
        setError('missing-tree');
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const resp = await fetch(`/api/fault-trees/${encodeURIComponent(treeId)}`);
        if (!resp.ok) {
          if (cancelled) return;
          setTree(null);
          setError('not-found');
          setLoading(false);
          return;
        }

        const nextTree = await resp.json();
        if (cancelled) return;

        if (nextTree.conversation_id && nextTree.conversation_id !== conversationId) {
          setTree(null);
          setActualConversationId(nextTree.conversation_id);
          setError('conversation-mismatch');
          setLoading(false);
          return;
        }

        setActualConversationId(nextTree.conversation_id || null);
        setTree(nextTree);
        setLoading(false);
      } catch (fetchError) {
        if (cancelled) return;
        console.error('加载故障树失败', fetchError);
        setTree(null);
        setError('load-failed');
        setLoading(false);
      }
    };

    loadTree();

    return () => {
      cancelled = true;
    };
  }, [conversationId, treeId]);

  const backPath = useMemo(() => {
    if (conversationId) {
      return `/flow/${conversationId}`;
    }
    return '/flow';
  }, [conversationId]);

  const handleBack = useCallback(() => {
    navigate(backPath);
  }, [backPath, navigate]);

  if (loading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" tip="正在加载故障树..." />
      </div>
    );
  }

  if (error === 'conversation-mismatch') {
    return (
      <Result
        status="warning"
        title="故障树与当前会话不匹配"
        subTitle="当前 URL 中的会话 ID 与该故障树的关联会话不一致，已阻止直接加载。"
        extra={[
          actualConversationId ? (
            <Button
              key="jump"
              type="primary"
              onClick={() => navigate(`/flow/${actualConversationId}/${treeId}`, { replace: true })}
            >
              前往关联会话
            </Button>
          ) : null,
          <Button key="back" onClick={handleBack}>返回聊天页</Button>,
        ].filter(Boolean)}
      />
    );
  }

  if (error) {
    return (
      <Result
        status="404"
        title="故障树加载失败"
        subTitle="未找到指定故障树，或当前页面无法恢复该故障树。"
        extra={<Button type="primary" onClick={handleBack}>返回聊天页</Button>}
      />
    );
  }

  return <FaultTreeWorkspace tree={tree} onBack={handleBack} />;
}