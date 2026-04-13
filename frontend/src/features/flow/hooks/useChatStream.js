import { useState, useCallback } from 'react';
import { flushSync } from 'react-dom';
import { sendChatMessage } from '../services/chatApi';

export default function useChatStream({
  setMessages, setConversationState, abortControllerRef,
  onConversationCreated, routeConversationId, navigate,
}) {
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = useCallback(async (question, conversationId) => {
    setIsStreaming(true);
    setMessages((prev) => [...prev, { role: 'assistant', content: '', streaming: true, streamingStep: '正在连接...' }]);

    abortControllerRef.current = new AbortController();

    try {
      const response = await sendChatMessage(question, conversationId, abortControllerRef.current.signal);
      if (!response.ok) {
        throw new Error(`请求失败，状态码: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentSources = null;
      let eventType = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            let payload;
            try { payload = JSON.parse(line.slice(6)); } catch { continue; }

            if (eventType === 'conversation') {
              setConversationState(payload.conversation_id);
              onConversationCreated?.();
              if (routeConversationId !== payload.conversation_id) {
                navigate(`/flow/${payload.conversation_id}`, { replace: true });
              }
              setMessages((prev) => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.streamingStep = '正在检索相关文档...';
                updated[updated.length - 1] = last;
                return updated;
              });
            } else if (eventType === 'sources') {
              currentSources = payload.sources;
              setMessages((prev) => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.streamingStep = payload.sources?.length
                  ? `已找到 ${payload.sources.length} 条相关文档，正在生成回复...`
                  : '正在生成回复...';
                updated[updated.length - 1] = last;
                return updated;
              });
            } else if (eventType === 'token') {
              flushSync(() => {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = { ...updated[updated.length - 1] };
                  last.content = (last.content || '') + payload.content;
                  last.streamingStep = null;
                  updated[updated.length - 1] = last;
                  return updated;
                });
              });
            } else if (eventType === 'fault_tree') {
              const tree = payload.fault_tree;
              setMessages((prev) => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                last.faultTree = tree;
                last.faultTreeId = tree?.id || last.faultTreeId || null;
                updated[updated.length - 1] = last;
                return updated;
              });
            } else if (eventType === 'done') {
              const snapSources = currentSources;
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content || payload.answer || '',
                  sources: snapSources,
                  faultTreeId: payload.fault_tree_id || last.faultTreeId || null,
                  streaming: false,
                };
                return updated;
              });
            } else if (eventType === 'error') {
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: `错误：${payload.message}`,
                  streaming: false,
                };
                return updated;
              });
            }
            eventType = null;
          }
        }
      }
      // 流读取完毕，确保 streaming 标志关闭
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last.role === 'assistant' && last.streaming) {
          updated[updated.length - 1] = { ...last, sources: last.sources ?? currentSources, streaming: false };
        }
        return updated;
      });
    } catch (error) {
      if (error.name !== 'AbortError') {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === 'assistant') {
            updated[updated.length - 1] = { ...last, content: `请求出错：${error.message}`, streaming: false };
          } else {
            updated.push({ role: 'assistant', content: `请求出错：${error.message}` });
          }
          return updated;
        });
      }
    } finally {
      setIsStreaming(false);
    }
  }, [setMessages, setConversationState, abortControllerRef, onConversationCreated, routeConversationId, navigate]);

  const resetStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsStreaming(false);
  }, [abortControllerRef]);

  return { sendMessage, isStreaming, resetStreaming };
}
