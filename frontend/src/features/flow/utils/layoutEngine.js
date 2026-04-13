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

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const newNode = { ...node };

    const width = node.measured?.width ?? defaultNodeWidth;
    const height = node.measured?.height ?? defaultNodeHeight;

    newNode.position = {
      x: nodeWithPosition.x - width / 2,
      y: nodeWithPosition.y - height / 2,
    };

    return newNode;
  });

  return { nodes: newNodes, edges };
};
