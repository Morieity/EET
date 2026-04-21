import { Handle, Position } from '@xyflow/react';

function TextUpdaterNode({ id, data, isConnectable, selected }) {
  const sourceCount = data.sources?.length || 0;

  return (
    <div className={`text-updater-node ${selected ? 'selected' : ''}`} style={{ position: 'relative', padding: '10px', borderRadius: '5px', minWidth: '100px', textAlign: 'center', border: selected ? '2px solid #222' : '1px solid #777' }}>
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
      <div>
        {data.label}
      </div>
      {sourceCount > 0 && (
        <div style={{
          position: 'absolute',
          bottom: 2,
          right: 4,
          fontSize: 10,
          color: '#1890ff',
          opacity: 0.8,
          pointerEvents: 'none',
        }}>
          {sourceCount}📄
        </div>
      )}
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
