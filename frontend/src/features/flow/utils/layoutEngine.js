import dagre from '@dagrejs/dagre';

const defaultNodeWidth = 150;
const defaultNodeHeight = 50;

/**
 * 获取树形排版布局
 * @param {Array} nodes - 节点数组
 * @param {Array} edges - 边（连线）数组
 * @param {String} direction - 排版方向，TB: top-to-bottom，LR: left-to-right
 * @returns {Object} 包含处理好坐标的 { nodes, edges } 的对象
 */
export const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  dagreGraph.setGraph({
    rankdir: direction,
    align: 'UL',
    nodesep: 100,
    ranksep: 120,
    edgesep: 50,
  });

  nodes.forEach((node) => {
    const width = node.measured?.width ?? defaultNodeWidth;
    const height = node.measured?.height ?? defaultNodeHeight;
    dagreGraph.setNode(node.id, { width, height });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const isHorizontal = direction === 'LR' || direction === 'RL';

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const newNode = { ...node };

    const width = node.measured?.width ?? defaultNodeWidth;
    const height = node.measured?.height ?? defaultNodeHeight;

    newNode.position = {
      x: nodeWithPosition.x - width / 2,
      y: nodeWithPosition.y - height / 2,
    };

    // 用 dagre 的 rank 方向坐标标识同一层
    newNode._rankKey = Math.round(isHorizontal ? nodeWithPosition.x : nodeWithPosition.y);

    return newNode;
  });

  // 同一层节点左对齐：统一左边缘 x 为该层最小值
  const rankGroups = {};
  newNodes.forEach((node) => {
    if (!rankGroups[node._rankKey]) rankGroups[node._rankKey] = [];
    rankGroups[node._rankKey].push(node);
  });
  Object.values(rankGroups).forEach((group) => {
    const minX = Math.min(...group.map((n) => n.position.x));
    group.forEach((node) => { node.position.x = minX; });
  });
  newNodes.forEach((node) => { delete node._rankKey; });

  return { nodes: newNodes, edges };
};
