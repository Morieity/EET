import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Flow from './features/flow/FlowLayout';
import Home from './features/home/Home';
import AiChatPanel from './features/flow/components/chat/AiChatPanel';
import FlowFaultTreePage from './features/flow/pages/FlowFaultTreePage';
import KnowledgeGraphDoc from './features/docs/KnowledgeGraphDoc';
import ContextManagementDoc from './features/docs/ContextManagementDoc';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/docs/knowledge-graph" element={<KnowledgeGraphDoc />} />
        <Route path="/docs/context-management" element={<ContextManagementDoc />} />
        <Route path="/flow" element={<Flow />}>
          <Route index element={<AiChatPanel />} />
          <Route path=":conversationId" element={<AiChatPanel />} />
          <Route path=":conversationId/:treeId" element={<FlowFaultTreePage />} />
        </Route>
      </Routes>
    </Router>
  );
}
