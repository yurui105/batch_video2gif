#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
视频转GIF工具
主程序入口
"""

import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

if __name__ == "__main__":
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序样式表
    app.setStyleSheet("""
        QMainWindow, QDialog {
            background-color: #f8f9fa;
        }
    """)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())