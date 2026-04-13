import { useRef, useCallback, useEffect } from 'react';
import { getConversation } from '../services/conversationApi';
import { getFaultTree } from '../services/faultTreeApi';
import { DEFAULT_WELCOME_MESSAGE, DEFAULT_NEW_SESSION_MESSAGE, createAssistantMessage } from '../utils/constants';

export default function useConversationLoader({
  routeConversationId, initialConversationId,
  setMessages, setConversationState, conversationIdRef,
  resetStreaming, navigate, injectedTree, onInjected,
}) {
  const loadRequestRef = useRef(0);

  const loadConversation = useCallback(async (convId, requestId) => {
    try {
      const conv = await getConversation(convId);
      if (requestId !== loadRequestRef.current) return;

      const roundTreeIds = [...new Set(
        (conv.rounds || [])
          .map((round) => round.fault_tree_id)
          .filter(Boolean)
      )];
      const roundTrees = new Map();

      if (roundTreeIds.length > 0) {
        const treeEntries = await Promise.all(roundTreeIds.map(async (treeId) => {
          try {
            const tree = await getFaultTree(treeId);
            return [treeId, tree];
          } catch (error) {
            console.error('加载轮次关联故障树失败', error);
            return null;
          }
        }));

        if (requestId !== loadRequestRef.current) return;

        treeEntries.filter(Boolean).forEach(([treeId, tree]) => {
          roundTrees.set(treeId, tree);
        });
      }

      const msgs = [];
      for (const round of (conv.rounds || [])) {
        msgs.push({ role: 'user', content: round.question });
        const sources = Array.isArray(round.sources) ? round.sources : [];
        msgs.push({
          role: 'assistant',
          content: round.answer,
          sources,
          faultTree: round.fault_tree_id ? roundTrees.get(round.fault_tree_id) || undefined : undefined,
          faultTreeId: round.fault_tree_id || null,
        });
      }
      setConversationState(convId);
      setMessages(msgs.length > 0 ? msgs : createAssistantMessage(DEFAULT_WELCOME_MESSAGE));
    } catch (e) {
      if (requestId !== loadRequestRef.current) return;
      console.error('加载历史对话失败', e);
      setConversationState(null);
      setMessages(createAssistantMessage(e.message?.includes('404') ? '未找到该历史对话，请开始新的诊断会话。' : '加载历史对话失败，请稍后重试。'));
    }
  }, [setConversationState, setMessages]);

  // 路由驱动会话恢复
  useEffect(() => {
    const nextConversationId = routeConversationId ?? initialConversationId ?? null;

    if (nextConversationId && nextConversationId === conversationIdRef.current) {
      return;
    }

    resetStreaming();
    loadRequestRef.current += 1;

    if (nextConversationId) {
      setMessages(createAssistantMessage('正在加载历史对话...'));
      loadConversation(nextConversationId, loadRequestRef.current);
      return;
    }

    setConversationState(null);
    setMessages(createAssistantMessage(DEFAULT_WELCOME_MESSAGE));
  }, [routeConversationId, initialConversationId, loadConversation, setConversationState, setMessages, conversationIdRef, resetStreaming]);

  // 外部注入故障树时追加 system 消息
  useEffect(() => {
    if (injectedTree) {
      setMessages((prev) => [...prev, { role: 'system', content: '已从故障树库加载', faultTree: injectedTree }]);
      onInjected?.();
    }
  }, [injectedTree]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleNewSession = useCallback(() => {
    resetStreaming();
    loadRequestRef.current += 1;
    setConversationState(null);
    setMessages(createAssistantMessage(DEFAULT_NEW_SESSION_MESSAGE));
    if (routeConversationId) {
      navigate('/flow');
    }
  }, [resetStreaming, setConversationState, setMessages, routeConversationId, navigate]);

  return { loadRequestRef, handleNewSession };
}
