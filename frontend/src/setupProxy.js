const { createProxyMiddleware } = require('http-proxy-middleware');

/**
 * CRA 自定义代理配置。
 * 使用 setupProxy.js 替代 package.json 中的 "proxy" 字段，
 * 可关闭响应压缩，确保 SSE (text/event-stream) 流式数据不被缓冲。
 */
module.exports = function (app) {
  // 不使用 app.use('/api', ...) 挂载，因为 Express 会在调用中间件前剥离挂载路径。
  // 改为 app.use(middleware)，由 pathFilter 控制哪些请求进入代理，
  // 这样 /api 前缀会原样转发到后端。
  app.use(
    createProxyMiddleware({
      target: 'http://127.0.0.1:8080',
      changeOrigin: true,
      pathFilter: '/api',
      // 关闭压缩，防止 gzip 缓冲导致 SSE 无法实时到达浏览器
      compress: false,
    })
  );
};
