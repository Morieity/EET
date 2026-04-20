// 意图标签配置
export const INTENT_CONFIG = {
  fault_diagnosis: { label: '故障诊断', color: '#40b586' },
  off_topic: { label: '非诊断话题', color: '#e67e22' },
  suggest_fault_tree: { label: '建议生成故障树', color: '#3498db' },
  fault_tree_generated: { label: '✅ 已生成故障树', color: '#8e44ad' },
};

export const DEFAULT_WELCOME_MESSAGE = '你好！我是设备故障诊断助手青色交流电灯。请描述您遇到的设备故障现象，我会帮您逐步分析定位问题。';
export const DEFAULT_NEW_SESSION_MESSAGE = '新会话已创建。请描述您遇到的设备故障现象，我会帮您分析定位问题。';
export const PERSISTED_TREE_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function createAssistantMessage(content) {
  return [{ role: 'assistant', content }];
}

export const gateButtons = [
  { type: 'AND', label: '& 与门', tip: 'AND Gate' },
  { type: 'OR', label: '≥1 或门', tip: 'OR Gate' },
  { type: 'XOR', label: '=1 异或', tip: 'XOR Gate' },
  { type: 'INHIBIT', label: '⊘ 禁止', tip: 'INHIBIT Gate' },
  { type: 'PRIORITY_AND', label: 'P& 优先', tip: 'PRIORITY AND Gate' },
];
