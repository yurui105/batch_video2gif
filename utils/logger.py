#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志工具模块
用于记录和显示程序执行过程中的各种日志信息
"""

from datetime import datetime
from PyQt5.QtWidgets import QTextEdit


class Logger:
    """日志记录器类，用于将日志信息输出到文本控件"""

    def __init__(self, text_widget: QTextEdit):
        """
        初始化日志记录器

        Args:
            text_widget: QTextEdit控件，用于显示日志
        """
        self.text_widget = text_widget

    def _log(self, message: str, level: str):
        """
        记录日志的内部方法

        Args:
            message: 日志消息
            level: 日志级别
        """
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 格式化日志消息
        formatted_message = f"[{timestamp}] [{level}] {message}"

        # 添加到日志窗口
        self.text_widget.append(formatted_message)

        # 滚动到底部
        self.text_widget.verticalScrollBar().setValue(
            self.text_widget.verticalScrollBar().maximum()
        )

    def info(self, message: str):
        """
        记录信息级别的日志

        Args:
            message: 日志消息
        """
        self._log(message, "INFO")

    def warning(self, message: str):
        """
        记录警告级别的日志

        Args:
            message: 日志消息
        """
        self._log(message, "WARNING")

    def error(self, message: str):
        """
        记录错误级别的日志

        Args:
            message: 日志消息
        """
        self._log(message, "ERROR")