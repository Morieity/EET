from Backend.Web.app_factory import create_app


def start_app():
    """启动由应用工厂创建的 Flask 应用。"""
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)


if __name__ == "__main__":
    start_app()
