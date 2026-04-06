const { createProxyMiddleware } = require('http-proxy-middleware');

/**
 * CRA 自定义代理配置。
 * 使用 setupProxy.js 替代 package.json 中的 "proxy" 字段，
 * 可关闭响应压缩，确保 SSE (text/event-stream) 流式数据不被缓冲。
 */
module.exports = function (app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://127.0.0.1:8080',
      changeOrigin: true,
      // 关闭压缩，防止 gzip 缓冲导致 SSE 无法实时到达浏览器
      compress: false,
    })
  );
};
