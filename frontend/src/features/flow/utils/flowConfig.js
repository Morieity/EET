import TextUpdaterNode from '../components/tree/TextUpdaterNode';
import GateNode from '../components/tree/GateNode';

// 生成全局唯一 ID，避免与后端节点 ID（n1/n2/g1...）冲突
export const getId = () => `node-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;

export const nodeColor = (node) => {
  if (node.style && node.style.backgroundColor) {
    return node.style.backgroundColor;
  }
  switch (node.type) {
    case 'input': return '#6ede87';
    case 'output': return '#6865A5';
    case 'textUpdater': return '#40b586';
    default: return '#ff0072';
  }
};

export const nodeTypes = {
  textUpdater: TextUpdaterNode,
  gate: GateNode,
};
