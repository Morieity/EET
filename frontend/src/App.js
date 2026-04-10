import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Flow from './Flow';
import Home from './Home';
import AiChatPanel from './AiChatPanel';
import FlowFaultTreePage from './FlowFaultTreePage';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/flow" element={<Flow />}>
          <Route index element={<AiChatPanel />} />
          <Route path=":conversationId" element={<AiChatPanel />} />
          <Route path=":conversationId/:treeId" element={<FlowFaultTreePage />} />
        </Route>
      </Routes>
    </Router>
  );
}
