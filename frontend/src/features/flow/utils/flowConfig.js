import TextUpdaterNode from '../components/tree/TextUpdaterNode';
import GateNode from '../components/tree/GateNode';

// 简单生成全局自增ID
let id = 5;
export const getId = () => `n${id++}`;

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
