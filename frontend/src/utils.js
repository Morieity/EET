import dagre from '@dagrejs/dagre';

// 简单生成全局自增ID
let id = 5;
export const getId = () => `n${id++}`;

export const nodeColor = (node) => {
  // 如果节点有自定义的背景颜色，优先使用自定义颜色
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

// 默认的节点尺寸（用来兜底没有被测量的节点）
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
  // 必须在函数内部新建图实例，不然连续多次点击排版会导致旧的数据残留引起报错或乱掉
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  // === 核心：调整排版的数学参数使其变成更美丽的树 ===
  dagreGraph.setGraph({ 
    rankdir: direction, // 控制树的方向（TB=从上到下）
    nodesep: 100,       // 【同级节点间距】（横向）：拉宽水平间距！如果一个父节点有很多子节点，这个参数会把它们自动撑开拉平，防止拥挤
    ranksep: 120,       // 【层级间距】（纵向）：拉宽上下层级之间的垂直距离，使得体现“树的层数”非常清晰
    edgesep: 50         // 【边间距】
  });

  // 同步添加节点到 dagre
  nodes.forEach((node) => {
    // 亮点：优先使用 React Flow 内部运行时自带的被渲染真实尺寸 (node.measured)，不再使用全部定死的 150x50。
    // 这让不同长度文本的宽节点也能得到完美的数学间距而不重叠。
    const width = node.measured?.width ?? defaultNodeWidth;
    const height = node.measured?.height ?? defaultNodeHeight;
    dagreGraph.setNode(node.id, { width, height });
  });

  // 同步添加连线到 dagre，确立层级父子关系
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // 触发 dagre 自动计算！
  dagre.layout(dagreGraph);

  // 整理重新计算完毕后的最终节点（赋予新的 x, y 坐标）
  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const newNode = { ...node };

    const width = node.measured?.width ?? defaultNodeWidth;
    const height = node.measured?.height ?? defaultNodeHeight;

    // dagre 排版的节点默认是以“中心点”为坐标，而 React flow 以“左上角”为锚点，所以需要减去宽高的一半做对齐补偿。
    newNode.position = {
      x: nodeWithPosition.x - width / 2,
      y: nodeWithPosition.y - height / 2,
    };

    return newNode;
  });

  return { nodes: newNodes, edges };
};

/**
 * 将后端故障树数据转换为 React Flow 节点和边
 * 后端格式: { nodes: [{id, type:"event"/"gate", data:{label, remark, gateType}}], edges: [{id, source, target}] }
 * React Flow 格式: nodes 包含 type:"textUpdater"/"gate"，edges 包含 type:"smoothstep"
 */
export const convertFaultTreeToFlow = (faultTree) => {
  const rawNodes = faultTree.nodes || [];
  const rawEdges = faultTree.edges || [];

  // 判断哪些节点没有入边（根节点）
  const hasIncoming = new Set(rawEdges.map(e => e.target));

  const nodes = rawNodes.map((n, index) => {
    if (n.type === 'gate') {
      return {
        id: n.id,
        type: 'gate',
        position: { x: 0, y: index * 100 },
        data: {
          gateType: n.data?.gateType || 'OR',
        },
      };
    }
    // event node → textUpdater
    const isRoot = !hasIncoming.has(n.id);
    return {
      id: n.id,
      type: 'textUpdater',
      position: { x: 0, y: index * 100 },
      data: {
        label: n.data?.label || n.id,
        remark: n.data?.remark || '',
      },
      style: {
        backgroundColor: isRoot ? '#e74c3c' : '#40b586',
        color: 'white',
      },
    };
  });

  const edges = rawEdges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: 'smoothstep',
  }));

  return { nodes, edges };
};
