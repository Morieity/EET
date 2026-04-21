# 前端说明（面向 Razor 背景）

## 先回答你的问题
不是全都是 JS。

在当前项目 frontend 目录（排除 node_modules）里，主要类型有：
- `.js`：22 个（业务逻辑与组件）
- `.json`：3 个（项目配置）
- `.css`：2 个（样式）
- `.html`：1 个（页面壳）
- `.md`：1 个（说明文档）
- `.txt`：1 个（robots）
- `.gitignore`：1 个（忽略规则）
- `.ico`：1 个（图标）
- `.bak`：1 个（备份文件）

所以：业务代码主体是 React + JavaScript，但不是“只有 JS”。

## 用 Razor 的思维理解这套前端
你可以把它类比成：
- `index.html` ≈ Razor Layout 的最外层 HTML 壳（只放挂载点）
- `index.js` ≈ 应用启动入口（类似 Program.cs + 前端初始化）
- `App.js` ≈ 路由总入口（按 URL 分发页面）
- `Home.js`、`Flow.js` ≈ Razor Page / MVC View 对应的页面组件
- `AiChatPanel.js`、`FileListPanel.js` 等 ≈ 视图里的可复用 Partial
- `setupProxy.js` ≈ 本地开发时的反向代理配置（类似 ASP.NET 里的代理转发）

## 前端运行链路（简化）
1. 浏览器先加载 `public/index.html`。
2. `src/index.js` 挂载 React 根组件。
3. `src/App.js` 根据路由渲染：
   - `/` -> `Home.js`
   - `/flow` -> `Flow.js`
4. `Flow.js` 再组合聊天、文件、历史、故障树库等面板组件。

## 目录与职责
- `frontend/public/`
  - `index.html`：SPA 的 HTML 外壳
  - `manifest.json`：PWA 元信息
  - `robots.txt`：爬虫规则
- `frontend/src/`
  - `index.js`：前端入口
  - `App.js`：路由入口
  - `Home.js`：首页
  - `Flow.js`：故障树编辑主页面（核心）
  - `AiChatPanel.js`：AI 对话面板
  - `FileListPanel.js`：文件列表面板
  - `DocumentUploadPanel.js`：文件上传子面板
  - `ConversationHistoryPanel.js`：对话历史面板
  - `FaultTreeLibraryPanel.js`：故障树库面板
  - `GateNode.js` / `TextUpdaterNode.js`：流程图节点组件
  - `utils.js` / `initialElements.js`：图数据和布局辅助
  - `ui/`：通用 UI 组件
  - `figma/ImageWithFallback.js`：图片兜底组件
- `frontend/package.json`
  - 前端依赖与脚本（`start`、`build`、`test`）

## 你最需要先懂的 4 个点（从 Razor 迁移）
1. 状态驱动 UI
- Razor 多是服务端渲染模板。
- React 主要是“状态改变 -> 自动重渲染”。

2. 组件化
- Razor Partial/ViewComponent 是局部复用。
- React 组件是更细粒度的“函数 + 状态 + 生命周期”。

3. 前后端通信
- 此项目前端通常通过 `/api/*` 访问后端。
- 开发期由 `setupProxy.js` 转发到 `http://127.0.0.1:8080`。

4. 路由在前端
- Razor 常由服务端路由分发页面。
- 这里由 `react-router-dom` 在浏览器里切换页面组件。

## 建议的阅读顺序（Razor 背景）
1. `frontend/src/index.js`
2. `frontend/src/App.js`
3. `frontend/src/Home.js`
4. `frontend/src/Flow.js`
5. `frontend/src/AiChatPanel.js` + `frontend/src/FileListPanel.js`
6. `frontend/src/utils.js`
7. `frontend/src/setupProxy.js`

## 常用命令
在 `frontend` 目录：

```bash
npm install
npm start
npm test
npm run build
```

## 给你的一个学习映射
- 你已经会 Razor，建议把 React 当成“前端版组件化 + 状态机”。
- 先只盯住 `App.js -> Flow.js -> 子面板` 这条主链，理解后再看样式和细节组件。
