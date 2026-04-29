#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
iOS签名工具主程序
"""

import os
import sys
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTranslator, QLocale
from PyQt5.QtGui import QIcon

from .ui.main_window import MainWindow
from .utils.config_utils import load_config, get_config_value

logger = logging.getLogger(__name__)

def setup_app():
    """
    设置应用程序
    """
    # 加载配置
    config = load_config()
    
    # 创建应用
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("iOS签名工具")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("iOS签名工具")
    
    # 设置应用图标
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    icon_path = base_dir / "resources" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # 加载样式表
    style_path = base_dir / "resources" / "style" / "main.qss"
    if style_path.exists():
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    
    # 加载语言
    language = get_config_value("language", "zh_CN")
    translator = QTranslator()
    translator_path = base_dir / "resources" / "translations" / f"{language}.qm"
    if translator_path.exists():
        translator.load(str(translator_path))
        app.installTranslator(translator)
    
    return app

def run():
    """
    运行应用程序
    """
    try:
        # 设置应用
        app = setup_app()
        
        # 创建主窗口
        main_window = MainWindow()
        main_window.show()
        
        # 运行应用
        logger.info("启动应用程序")
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"应用程序运行出错: {e}")
        raise

if __name__ == "__main__":
    run() 