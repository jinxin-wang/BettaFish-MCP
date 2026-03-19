#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP 独立服务器

提供独立的 MCP 服务，可被远程客户端调用。
默认运行在 http://localhost:5100/mcp

用法:
    python mcp_server.py                    # 默认端口 5100
    python mcp_server.py --port 8080        # 指定端口
    python mcp_server.py --host 0.0.0.0     # 监听所有接口
"""

import argparse
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

from pathlib import Path

from flask import Flask, jsonify, Response
from loguru import logger

from mcp.blueprint import mcp_bp
from mcp.task_registry import get_task_registry


def create_app(host: str = "127.0.0.1", port: int = 5100) -> Flask:
    """创建 MCP Flask 应用"""
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "MCP-Server-Secret-Key"
    app.config["JSON_AS_ASCII"] = False

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    app.register_blueprint(mcp_bp, url_prefix="/mcp")

    @app.route("/")
    def index():
        return jsonify(
            {
                "service": "BettaFish MCP Server",
                "version": "1.0.0",
                "status": "running",
                "endpoints": {
                    "mcp_base": f"http://{host}:{port}/mcp",
                    "sse": f"http://{host}:{port}/mcp/sse",
                    "message": f"http://{host}:{port}/mcp/message",
                    "tools": f"http://{host}:{port}/mcp/tools",
                    "resources": f"http://{host}:{port}/mcp/resources",
                    "prompts": f"http://{host}:{port}/mcp/prompts",
                    "status": f"http://{host}:{port}/mcp/status",
                },
                "docs": {
                    "description": "微舆 (BettaFish) MCP 服务 - 多智能体舆情分析",
                    "usage": "配置 MCP 客户端连接到此服务器",
                    "client_config_example": {
                        "mcpServers": {
                            "BettaFish": {"url": f"http://{host}:{port}/mcp"}
                        }
                    },
                },
            }
        )

    @app.route("/health")
    def health():
        return jsonify({"status": "healthy"})

    logger.info(f"MCP Blueprint registered at /mcp/*")
    logger.info(f"Available endpoints:")
    logger.info(f"  - GET  /mcp/sse        : SSE 实时连接")
    logger.info(f"  - POST /mcp/message    : MCP 协议消息")
    logger.info(f"  - GET  /mcp/tools      : 列出所有工具")
    logger.info(f"  - GET  /mcp/resources  : 列出所有资源")
    logger.info(f"  - GET  /mcp/prompts    : 列出所有提示词")
    logger.info(f"  - GET  /mcp/status     : 服务器状态")

    return app


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="BettaFish MCP 独立服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python mcp_server.py                     # 本地运行在 5100 端口
  python mcp_server.py --port 8080         # 指定端口
  python mcp_server.py --host 0.0.0.0     # 允许远程访问
  python mcp_server.py --debug             # 开启调试模式
        """,
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("MCP_HOST", "127.0.0.1"),
        help="监听地址 (默认: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "5100")),
        help="监听端口 (默认: 5100)",
    )
    parser.add_argument("--debug", action="store_true", help="开启调试模式")
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    Path("logs").mkdir(exist_ok=True)

    logger.info("=" * 60)
    logger.info("BettaFish MCP Server 启动中...")
    logger.info("=" * 60)

    try:
        get_task_registry()
        logger.info("TaskRegistry 初始化成功")
    except Exception as e:
        logger.error(f"TaskRegistry 初始化失败: {e}")
        sys.exit(1)

    app = create_app(host=args.host, port=args.port)

    access_url = (
        f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}"
    )
    logger.info("=" * 60)
    logger.info(f"MCP Server 运行在: {access_url}")
    logger.info(f"MCP 端点: {access_url}/mcp")
    logger.info(f"文档查看: {access_url}/")
    logger.info("=" * 60)

    if args.host == "0.0.0.0":
        logger.warning("警告: 监听所有接口，允许远程访问")
        logger.warning("请确保网络配置安全!")

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
