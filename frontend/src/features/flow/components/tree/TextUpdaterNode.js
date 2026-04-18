import { Handle, Position } from '@xyflow/react';

function TextUpdaterNode({ id, data, isConnectable, selected }) {
  return (
    <div className={`text-updater-node ${selected ? 'selected' : ''}`} style={{ padding: '10px', borderRadius: '5px', minWidth: '100px', textAlign: 'center', border: selected ? '2px solid #222' : '1px solid #777', position: 'relative' }}>
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
      <div>
        {data.label}
      </div>
      <Handle type="source" position={Position.Right} id="a" isConnectable={isConnectable} />
      {data.hasChildren && (
        <button
          className="nodrag nopan"
          onClick={(e) => { e.stopPropagation(); data.onToggleCollapse?.(id); }}
          style={{
            position: 'absolute',
            right: -14,
            top: '50%',
            transform: 'translateY(-50%)',
            width: 20,
            height: 20,
            borderRadius: '50%',
            border: '1.5px solid #aaa',
            background: '#fff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 14,
            fontWeight: 'bold',
            lineHeight: 1,
            color: '#555',
            zIndex: 10,
            padding: 0,
          }}
        >
          {data.collapsed ? '+' : '−'}
        </button>
      )}
    </div>
  );
}

export default TextUpdaterNode;

