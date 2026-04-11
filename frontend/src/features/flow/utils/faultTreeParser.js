import { normalizeFaultTree } from './faultTreeConverter';

/**
 * 从 LLM 文本回复中提取故障树 JSON 并转为标准格式。
 * 返回 { tree, cleanedContent } 或 null。
 */
export const extractFaultTreeFromText = (content) => {
  if (!content) return null;

  // 1. 尝试 ```json ... ``` 代码块
  const codeBlockRegex = /```(?:json)?\s*\n?([\s\S]*?)```/g;
  let match;
  while ((match = codeBlockRegex.exec(content)) !== null) {
    try {
      const parsed = JSON.parse(match[1]);
      const tree = normalizeFaultTree(parsed);
      if (tree) {
        const cleanedContent = content.replace(match[0], '').trim();
        return { tree, cleanedContent };
      }
    } catch { /* not valid JSON, skip */ }
  }

  // 2. 尝试裸 JSON（从第一个 { 到最后一个 }）
  const firstBrace = content.indexOf('{');
  if (firstBrace >= 0) {
    const lastBrace = content.lastIndexOf('}');
    if (lastBrace > firstBrace) {
      const jsonStr = content.substring(firstBrace, lastBrace + 1);
      try {
        const parsed = JSON.parse(jsonStr);
        const tree = normalizeFaultTree(parsed);
        if (tree) {
          const cleanedContent = (content.substring(0, firstBrace) + content.substring(lastBrace + 1)).trim();
          return { tree, cleanedContent };
        }
      } catch { /* not valid JSON, skip */ }
    }
  }

  return null;
};
