from Backend.Web.app_factory import create_app

app = create_app()

if __name__ == "__main__":
    # threaded=True 允许 Flask 同时处理多个请求（每个请求一个线程）
    # 多个终端可以同时进行对话而不会互相阻塞
    app.run(host="0.0.0.0", port=8080, debug=True, threaded=True)
