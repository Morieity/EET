export const initialNodes = [
  { id: 'n1', position: { x: 0, y: 0 }, data: { label: 'Node 1' }, type: 'textUpdater', style: { backgroundColor: '#6ede87', color: 'white' } },
  { id: 'n2', position: { x: 0, y: 100 }, data: { label: 'Node 2' }, type: 'textUpdater',style: { backgroundColor: '#ff0072', color: 'white' } },
  { id: 'n3', position: { x: 0, y: 200 }, data: { label: 'Node 3' }, type: 'textUpdater', style: { backgroundColor: '#6865A5', color: 'white' } },
  { id: 'n4', position: { x: 0, y: 300 }, data: { label: 'Node 4' }, type: 'textUpdater', style: { backgroundColor: '#40b586', color: 'white' } },
];

export const initialEdges = [{ 
  id: 'n1-n2', source: 'n1', target: 'n2', type: 'default', label: 'edge from n1 to n2'
}];
