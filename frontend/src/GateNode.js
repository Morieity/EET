import { Handle, Position } from '@xyflow/react';

function AndGateIcon() {
  return (
    <svg width="28" height="36" viewBox="0 0 28 36" style={{ display: 'block' }}>
      <g transform="translate(0, 36) rotate(-90)">
        <path
          d="M 4 2 L 18 2 A 12 12 0 0 1 18 26 L 4 26 Z"
          fill="white"
          stroke="#333"
          strokeWidth="1.5"
        />
        <text x="12" y="18" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#333">&amp;</text>
      </g>
    </svg>
  );
}

function OrGateIcon() {
  return (
    <svg width="28" height="36" viewBox="0 0 28 36" style={{ display: 'block' }}>
      <g transform="translate(0, 36) rotate(-90)">
        <path
          d="M 4 2 Q 14 14 4 26 Q 18 26 32 14 Q 18 2 4 2 Z"
          fill="white"
          stroke="#333"
          strokeWidth="1.5"
        />
        <text x="14" y="18" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#333">≥1</text>
      </g>
    </svg>
  );
}

function GateNode({ data, isConnectable, selected }) {
  const isAnd = data.gateType === 'AND';
  
  return (
    <div className={`gate-node ${selected ? 'selected' : ''}`} style={{ padding: '2px', borderRadius: '4px', border: selected ? '2px solid #222' : '1px solid transparent' }}>
      <Handle type="target" position={Position.Top} isConnectable={isConnectable} style={{ background: '#555' }} />
      
      {isAnd ? <AndGateIcon /> : <OrGateIcon />}

      <Handle type="source" position={Position.Bottom} isConnectable={isConnectable} style={{ background: '#555' }} />
    </div>
  );
}

export default GateNode;
