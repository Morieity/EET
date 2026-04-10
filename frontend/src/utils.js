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
 * 将 LLM 输出的 fault_tree 格式 (top_event/gates/basic_events)
 * 转换为标准后端格式 { name, nodes, edges }。
 */
function convertLLMFormatToStandard(raw) {
  const nodes = [];
  const edges = [];
  let edgeId = 0;

  const topEvent = raw.top_event;
  const gates = raw.gates || [];
  const basicEvents = raw.basic_events || raw.events || [];
  const gateIds = new Set(gates.map((g) => g.id));

  // 顶层事件
  if (topEvent) {
    nodes.push({
      id: topEvent.id,
      node_type: 'event',
      label: topEvent.description || topEvent.label || topEvent.id,
      remark: '',
    });
    // 顶层事件连接到第一个门
    if (!gateIds.has(topEvent.id) && gates.length > 0) {
      edges.push({ id: `e-${edgeId++}`, source_id: topEvent.id, target_id: gates[0].id });
    }
  }

  // 逻辑门
  gates.forEach((g) => {
    const existing = nodes.find((n) => n.id === g.id);
    if (existing) {
      existing.node_type = 'gate';
      existing.gate_type = (g.type || g.gate_type || 'OR').toUpperCase();
    } else {
      nodes.push({
        id: g.id,
        node_type: 'gate',
        label: g.description || g.label || g.id,
        gate_type: (g.type || g.gate_type || 'OR').toUpperCase(),
        remark: '',
      });
    }
    (g.inputs || []).forEach((inputId) => {
      edges.push({ id: `e-${edgeId++}`, source_id: g.id, target_id: inputId });
    });
  });

  // 基本事件
  basicEvents.forEach((ev) => {
    if (!nodes.find((n) => n.id === ev.id)) {
      nodes.push({
        id: ev.id,
        node_type: 'event',
        label: ev.description || ev.label || ev.id,
        remark: ev.remark || '',
      });
    }
  });

  // 被引用但未声明的节点补全
  edges.forEach((e) => {
    if (!nodes.find((n) => n.id === e.target_id)) {
      nodes.push({ id: e.target_id, node_type: 'event', label: e.target_id, remark: '' });
    }
  });

  return { name: raw.name || topEvent?.description || '故障树分析', nodes, edges };
}

/**
 * 尝试将任意 JSON 对象标准化为 { name, nodes, edges } 格式。
 * 支持后端格式和 LLM 格式。
 */
function normalizeFaultTree(obj) {
  if (!obj || typeof obj !== 'object') return null;
  const raw = obj.fault_tree || obj;
  // 标准后端格式
  if (Array.isArray(raw.nodes) && Array.isArray(raw.edges)) return raw;
  // LLM 格式
  if (raw.top_event || raw.gates) return convertLLMFormatToStandard(raw);
  return null;
}

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

/**
 * 将后端故障树 nodes/edges 转换为 antd Tree 的 treeData 格式。
 * 返回数组，每项: { key, title, description, children }
 */
export const convertFaultTreeToTreeData = (faultTree) => {
  const rawNodes = faultTree.nodes || [];
  const rawEdges = faultTree.edges || [];

  // 建立节点索引
  const nodeMap = {};
  rawNodes.forEach((n) => { nodeMap[n.id] = n; });

  // 建立 parent -> children 映射（source_id -> [target_id]）
  const childrenMap = {};
  const hasIncoming = new Set();
  rawEdges.forEach((e) => {
    const src = e.source_id || e.source;
    const tgt = e.target_id || e.target;
    if (!childrenMap[src]) childrenMap[src] = [];
    childrenMap[src].push(tgt);
    hasIncoming.add(tgt);
  });

  // 找到根节点（没有入边的节点）
  const roots = rawNodes.filter((n) => !hasIncoming.has(n.id));

  const buildTree = (nodeId) => {
    const n = nodeMap[nodeId];
    if (!n) return null;
    const isGate = n.node_type === 'gate';
    const label = n.label || n.id;
    const desc = isGate
      ? (n.gate_type || 'OR')
      : (n.remark || '');
    const children = (childrenMap[nodeId] || [])
      .map(buildTree)
      .filter(Boolean);
    return {
      key: n.id,
      title: label,
      description: desc,
      isGate,
      gateType: isGate ? (n.gate_type || 'OR') : undefined,
      children: children.length ? children : undefined,
    };
  };

  return roots.map((r) => buildTree(r.id)).filter(Boolean);
};

/**
 * 将后端故障树数据转换为 React Flow 节点和边
 * 后端格式: { nodes: [{id, type:"event"/"gate", data:{label, remark, gateType}}], edges: [{id, source, target}] }
 * React Flow 格式: nodes 包含 type:"textUpdater"/"gate"，edges 包含 type:"smoothstep"
 */
export const convertFaultTreeToFlow = (faultTree) => {
  const rawNodes = faultTree.nodes || [];
  const rawEdges = faultTree.edges || [];

  // 后端边字段为 source_id / target_id，判断哪些节点有入边（非根节点）
  const hasIncoming = new Set(rawEdges.map(e => e.target_id));

  const nodes = rawNodes.map((n, index) => {
    // 后端 node_type 枚举值：'gate' 或 'event'
    if (n.node_type === 'gate') {
      return {
        id: n.id,
        type: 'gate',
        position: { x: 0, y: index * 100 },
        data: {
          // 后端字段直接在节点顶层：gate_type，枚举值大写如 'AND'/'OR'
          gateType: n.gate_type || 'OR',
          label: n.label || '',
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
        label: n.label || n.id,
        remark: n.remark || '',
      },
      style: {
        backgroundColor: isRoot ? '#e74c3c' : '#40b586',
        color: 'white',
      },
    };
  });

  const edges = rawEdges.map((e) => ({
    id: e.id,
    source: e.source_id,
    target: e.target_id,
    type: 'smoothstep',
  }));

  return { nodes, edges };
};
