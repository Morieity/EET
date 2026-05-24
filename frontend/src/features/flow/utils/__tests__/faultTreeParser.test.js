/**
 * Unit tests for extractFaultTreeFromText.
 */
import { extractFaultTreeFromText } from '../faultTreeParser';

describe('extractFaultTreeFromText', () => {
  test('returns null for empty input', () => {
    expect(extractFaultTreeFromText('')).toBeNull();
    expect(extractFaultTreeFromText(null)).toBeNull();
  });

  test('extracts fault tree from a ```json fenced code block and strips it from text', () => {
    const json = JSON.stringify({
      name: '示例',
      nodes: [{ id: 'n1', label: '顶事件', node_type: 'event' }],
      edges: [],
    });
    const content = `分析完成：\n\`\`\`json\n${json}\n\`\`\`\n请确认。`;

    const result = extractFaultTreeFromText(content);

    expect(result).not.toBeNull();
    expect(result.tree.name).toBe('示例');
    expect(result.tree.nodes).toHaveLength(1);
    expect(result.cleanedContent).toContain('分析完成');
    expect(result.cleanedContent).toContain('请确认');
    expect(result.cleanedContent).not.toContain('```');
  });

  test('extracts bare JSON object embedded in surrounding prose', () => {
    const json = JSON.stringify({
      nodes: [{ id: 'n1', label: 'X' }],
      edges: [],
    });
    const content = `这里是分析结果： ${json} 完毕。`;

    const result = extractFaultTreeFromText(content);

    expect(result).not.toBeNull();
    expect(result.tree.nodes[0].id).toBe('n1');
    expect(result.cleanedContent).toBe('这里是分析结果：  完毕。');
  });

  test('returns null when no parseable / convertible JSON is present', () => {
    expect(extractFaultTreeFromText('纯文本，无 JSON。')).toBeNull();
    expect(extractFaultTreeFromText('```json\n{ not valid json }\n```')).toBeNull();
  });
});
