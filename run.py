#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import traceback
from pathlib import Path

# 设置日志
def setup_logging():
    # 在当前目录创建logs目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(current_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "app.log")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # 设置未捕获异常处理器
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception


def main():
    # 设置日志
    setup_logging()
    
    # 添加src目录到路径
    src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
    sys.path.insert(0, src_dir)
    
    try:
        # 导入主程序
        from src.main import run as app_main
        
        # 运行应用
        app_main()
    except Exception as e:
        logging.error(f"启动应用失败: {str(e)}")
        logging.error(traceback.format_exc())
        
        # 如果是在控制台运行，显示错误信息
        # 添加None检查以避免NoneType错误
        if sys.stdout and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            print(f"启动应用失败: {str(e)}")
            print(traceback.format_exc())


if __name__ == "__main__":
    main() 