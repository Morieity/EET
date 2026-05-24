/**
 * Smoke render test for the top-level App component.
 *
 * react-router-dom v7 ships as ESM-only and is not transformed by
 * react-scripts 5's default Jest setup. We mock both it and all heavy
 * feature pages so this test stays a true component-mount smoke check.
 */
import React from 'react';
import { render } from '@testing-library/react';

jest.mock(
  'react-router-dom',
  () => ({
    BrowserRouter: ({ children }) => <div data-testid="router-stub">{children}</div>,
    Routes: ({ children }) => <div data-testid="routes-stub">{children}</div>,
    Route: ({ element }) => <div data-testid="route-stub">{element}</div>,
  }),
  { virtual: true }
);

jest.mock('./features/flow/FlowLayout', () => () => <div data-testid="flow-layout-stub" />);
jest.mock('./features/flow/pages/FlowFaultTreePage', () => () => <div data-testid="flow-tree-stub" />);
jest.mock('./features/flow/components/chat/AiChatPanel', () => () => <div data-testid="chat-panel-stub" />);
jest.mock('./features/docs/KnowledgeGraphDoc', () => () => <div data-testid="kg-doc-stub" />);
jest.mock('./features/docs/ContextManagementDoc', () => () => <div data-testid="ctx-doc-stub" />);
jest.mock('./features/home/Home', () => () => <div data-testid="home-stub">home</div>);

const App = require('./App').default;

test('App mounts without throwing and wires up the Home route', () => {
  const { getByTestId, getAllByTestId } = render(<App />);
  expect(getByTestId('router-stub')).toBeInTheDocument();
  expect(getAllByTestId('route-stub').length).toBeGreaterThan(0);
  expect(getByTestId('home-stub')).toBeInTheDocument();
});
