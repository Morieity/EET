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
        <text x="12" y="18" transform="rotate(90, 12, 18)" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#333">&amp;</text>
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
        <text x="14" y="18" transform="rotate(90, 14, 18)" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#333">≥1</text>
      </g>
    </svg>
  );
}

function XorGateIcon() {
  return (
    <svg width="28" height="36" viewBox="0 0 28 36" style={{ display: 'block' }}>
      <g transform="translate(0, 36) rotate(-90)">
        <path
          d="M 4 2 Q 14 14 4 26 Q 18 26 32 14 Q 18 2 4 2 Z"
          fill="white"
          stroke="#333"
          strokeWidth="1.5"
        />
        <path
          d="M 1 2 Q 11 14 1 26"
          fill="none"
          stroke="#333"
          strokeWidth="1.5"
        />
        <text x="14" y="18" transform="rotate(90, 14, 18)" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#333">=1</text>
      </g>
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
      <g transform="translate(0, 36) rotate(-90)">
        <path
          d="M 4 2 L 18 2 A 12 12 0 0 1 18 26 L 4 26 Z"
          fill="white"
          stroke="#333"
          strokeWidth="1.5"
        />
        <text x="12" y="18" transform="rotate(90, 12, 18)" textAnchor="middle" fontSize="8" fontWeight="bold" fill="#333">P&amp;</text>
      </g>
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
      <Handle type="target" position={Position.Top} isConnectable={isConnectable} style={{ background: '#555' }} />
      
      <IconComponent />

      <Handle type="source" position={Position.Bottom} isConnectable={isConnectable} style={{ background: '#555' }} />
    </div>
  );
}

export default GateNode;
