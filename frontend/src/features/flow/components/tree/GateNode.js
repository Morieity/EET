import { Handle, Position } from '@xyflow/react';

function AndGateIcon() {
  return (
    <svg width="28" height="36" viewBox="0 0 28 36" style={{ display: 'block' }}>
      <path
        d="M 24 4 L 24 32 L 14 32 A 14 14 0 0 1 14 4 Z"
        fill="white"
        stroke="#333"
        strokeWidth="1.5"
      />
      <text x="16" y="18" textAnchor="middle" dominantBaseline="middle" fontSize="10" fontWeight="bold" fill="#333">&amp;</text>
    </svg>
  );
}

function OrGateIcon() {
  return (
    <svg width="28" height="36" viewBox="0 0 28 36" style={{ display: 'block' }}>
      <path
        d="M 24 4 Q 14 18 24 32 Q 10 32 2 18 Q 10 4 24 4 Z"
        fill="white"
        stroke="#333"
        strokeWidth="1.5"
      />
      <text x="16" y="18" textAnchor="middle" dominantBaseline="middle" fontSize="10" fontWeight="bold" fill="#333">≥1</text>
    </svg>
  );
}

function XorGateIcon() {
  return (
    <svg width="28" height="36" viewBox="0 0 28 36" style={{ display: 'block' }}>
      <path
        d="M 24 4 Q 14 18 24 32 Q 10 32 2 18 Q 10 4 24 4 Z"
        fill="white"
        stroke="#333"
        strokeWidth="1.5"
      />
      <path
        d="M 27 4 Q 17 18 27 32"
        fill="none"
        stroke="#333"
        strokeWidth="1.5"
      />
      <text x="16" y="18" textAnchor="middle" dominantBaseline="middle" fontSize="10" fontWeight="bold" fill="#333">=1</text>
    </svg>
  );
}

function InhibitGateIcon() {
  return (
    <svg width="28" height="36" viewBox="0 0 28 36" style={{ display: 'block' }}>
      <polygon
        points="14,2 26,34 2,34"
        fill="white"
        stroke="#333"
        strokeWidth="1.5"
      />
      <circle cx="14" cy="12" r="5" fill="none" stroke="#333" strokeWidth="1" />
      <text x="14" y="28" textAnchor="middle" fontSize="8" fontWeight="bold" fill="#333">⊘</text>
    </svg>
  );
}

function PriorityAndGateIcon() {
  return (
    <svg width="28" height="36" viewBox="0 0 28 36" style={{ display: 'block' }}>
      <path
        d="M 24 4 L 24 32 L 14 32 A 14 14 0 0 1 14 4 Z"
        fill="white"
        stroke="#333"
        strokeWidth="1.5"
      />
      <text x="16" y="18" textAnchor="middle" dominantBaseline="middle" fontSize="8" fontWeight="bold" fill="#333">P&amp;</text>
    </svg>
  );
}

const GATE_ICONS = {
  AND: AndGateIcon,
  OR: OrGateIcon,
  XOR: XorGateIcon,
  INHIBIT: InhibitGateIcon,
  PRIORITY_AND: PriorityAndGateIcon,
};

function GateNode({ data, isConnectable, selected }) {
  const IconComponent = GATE_ICONS[data.gateType] || OrGateIcon;
  
  return (
    <div className={`gate-node ${selected ? 'selected' : ''}`} style={{ padding: '2px', borderRadius: '4px', border: selected ? '2px solid #222' : '1px solid transparent' }}>
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} style={{ background: '#555' }} />
      
      <IconComponent />

      <Handle type="source" position={Position.Right} isConnectable={isConnectable} style={{ background: '#555' }} />
    </div>
  );
}

export default GateNode;
