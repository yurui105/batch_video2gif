#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主窗口模块
包含应用程序的主窗口界面
"""

import os
import sys
import threading
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog,
    QGroupBox, QRadioButton, QSlider, QSpinBox, QDoubleSpinBox,
    QMessageBox, QSplitter, QFrame, QToolButton
)
from PyQt5.QtCore import Qt, QSize, pyqtSlot, QTimer
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

from core.video_processor import VideoProcessor
from utils.logger import Logger
from ui.components.video_preview import VideoPreview


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        """初始化主窗口"""
        super().__init__()

        # 设置窗口标题和大小
        self.setWindowTitle("视频转GIF工具")
        self.resize(1200, 800)

        # 创建视频处理器
        self.video_processor = VideoProcessor()

        # 创建UI
        self.init_ui()

        # 连接信号
        self.connect_signals()

        # 设置视频处理状态
        self.processing = False

    def init_ui(self):
        """初始化UI"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建上部分和下部分的分割器
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setHandleWidth(6)
        main_splitter.setChildrenCollapsible(False)

        # 创建上部分的容器
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # 创建参数部分
        param_widget = QWidget()
        param_layout = QGridLayout(param_widget)
        param_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.setSpacing(10)

        # 创建文件路径选择部分
        # 输入路径
        param_layout.addWidget(QLabel("输入路径:"), 0, 0)
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("输入视频文件所在目录")
        param_layout.addWidget(self.input_path_edit, 0, 1)

        self.browse_input_button = QPushButton("浏览...")
        param_layout.addWidget(self.browse_input_button, 0, 2)

        # 输出路径
        param_layout.addWidget(QLabel("输出路径:"), 1, 0)
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("输出GIF文件保存目录")
        param_layout.addWidget(self.output_path_edit, 1, 1)

        self.browse_output_button = QPushButton("浏览...")
        param_layout.addWidget(self.browse_output_button, 1, 2)

        # 创建时间和分割设置部分
        param_layout.addWidget(QLabel("开始时间(秒):"), 2, 0)
        self.start_time_spin = QDoubleSpinBox()
        self.start_time_spin.setMinimum(0)
        self.start_time_spin.setMaximum(999999)
        self.start_time_spin.setValue(0)
        self.start_time_spin.setDecimals(1)
        self.start_time_spin.setSingleStep(1.0)
        param_layout.addWidget(self.start_time_spin, 2, 1)

        # 创建分割方式选择
        split_mode_group = QGroupBox("分割方式")
        split_mode_layout = QVBoxLayout(split_mode_group)

        self.duration_radio = QRadioButton("按时长分割")
        self.duration_radio.setChecked(True)
        self.count_radio = QRadioButton("按数量分割")

        split_mode_layout.addWidget(self.duration_radio)
        split_mode_layout.addWidget(self.count_radio)

        param_layout.addWidget(split_mode_group, 3, 0)

        # 创建分割参数设置
        split_param_widget = QWidget()
        split_param_layout = QGridLayout(split_param_widget)
        split_param_layout.setContentsMargins(0, 0, 0, 0)

        split_param_layout.addWidget(QLabel("分割时长(秒):"), 0, 0)
        self.split_duration_spin = QDoubleSpinBox()
        self.split_duration_spin.setMinimum(0.1)
        self.split_duration_spin.setMaximum(999999)
        self.split_duration_spin.setValue(5.0)
        self.split_duration_spin.setSingleStep(1.0)
        split_param_layout.addWidget(self.split_duration_spin, 0, 1)

        split_param_layout.addWidget(QLabel("分割数量:"), 1, 0)
        self.split_count_spin = QSpinBox()
        self.split_count_spin.setMinimum(1)
        self.split_count_spin.setMaximum(1000)
        self.split_count_spin.setValue(5)
        self.split_count_spin.setEnabled(False)  # 初始禁用
        split_param_layout.addWidget(self.split_count_spin, 1, 1)

        param_layout.addWidget(split_param_widget, 3, 1)

        # 图像质量设置
        param_layout.addWidget(QLabel("GIF质量:"), 4, 0)
        quality_widget = QWidget()
        quality_layout = QHBoxLayout(quality_widget)
        quality_layout.setContentsMargins(0, 0, 0, 0)

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setMinimum(1)
        self.quality_slider.setMaximum(100)
        self.quality_slider.setValue(80)

        self.quality_label = QLabel("80%")

        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)

        param_layout.addWidget(quality_widget, 4, 1)

        # 开始按钮
        self.start_button = QPushButton("开始处理")
        self.start_button.setMinimumHeight(40)
        param_layout.addWidget(self.start_button, 5, 0, 1, 3)

        # 添加参数部分到上部分布局
        top_layout.addWidget(param_widget)

        # 创建视频预览组件
        self.video_preview = VideoPreview()

        # 添加视频预览到上部分布局
        top_layout.addWidget(self.video_preview, 1)  # 1表示拉伸因子

        # 创建下部分的日志显示
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)

        log_label = QLabel("处理日志")
        log_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        log_layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        log_layout.addWidget(self.log_text)

        # 创建日志记录器
        self.logger = Logger(self.log_text)
        self.video_processor.set_logger(self.logger)

        # 添加组件到分割器
        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(log_widget)

        # 设置分割比例
        main_splitter.setSizes([600, 200])

        # 添加分割器到主布局
        main_layout.addWidget(main_splitter)

        # 设置样式
        self.setup_styles()

    def setup_styles(self):
        """设置样式"""
        # 全局样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 12px;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox {
                padding: 5px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #80bdff;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
            QPushButton:pressed {
                background-color: #005cbf;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #ddd;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #007bff;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #007bff;
                border-radius: 4px;
            }
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
        """)

        # 日志文本框样式
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px;
                font-family: Consolas, Courier, monospace;
            }
        """)

        # 开始按钮样式
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)

    def connect_signals(self):
        """连接信号"""
        # 文件浏览按钮
        self.browse_input_button.clicked.connect(self.browse_input_path)
        self.browse_output_button.clicked.connect(self.browse_output_path)

        # 分割模式按钮
        self.duration_radio.toggled.connect(self.on_split_mode_changed)

        # 质量滑块
        self.quality_slider.valueChanged.connect(self.on_quality_changed)

        # 开始按钮
        self.start_button.clicked.connect(self.start_processing)

        # 输入路径改变时加载视频
        self.input_path_edit.editingFinished.connect(self.load_videos_from_path)

    def browse_input_path(self):
        """浏览输入路径"""
        path = QFileDialog.getExistingDirectory(self, "选择输入目录")
        if path:
            self.input_path_edit.setText(path)
            self.load_videos_from_path()

    def browse_output_path(self):
        """浏览输出路径"""
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.output_path_edit.setText(path)

    def load_videos_from_path(self):
        """从输入路径加载视频"""
        path = self.input_path_edit.text().strip()
        if not path:
            return

        if not os.path.isdir(path):
            self.logger.error(f"输入路径不存在或不是一个目录: {path}")
            return

        try:
            videos = self.video_processor.get_videos_from_path(path)

            if not videos:
                self.logger.warning(f"在目录 {path} 中没有找到视频文件")
                return

            self.video_preview.set_videos(videos)
            self.logger.info(f"已加载 {len(videos)} 个视频文件")

        except Exception as e:
            self.logger.error(f"加载视频时发生错误: {str(e)}")

    def on_split_mode_changed(self, checked):
        """
        分割模式改变处理

        Args:
            checked: 按钮是否选中
        """
        # 根据模式启用/禁用对应的输入框
        self.split_duration_spin.setEnabled(self.duration_radio.isChecked())
        self.split_count_spin.setEnabled(self.count_radio.isChecked())

    def on_quality_changed(self, value):
        """
        质量滑块值改变处理

        Args:
            value: 新的质量值
        """
        self.quality_label.setText(f"{value}%")

    def start_processing(self):
        """开始处理视频"""
        # 检查是否正在处理
        if self.processing:
            self.abort_processing()
            return

        # 检查输入路径
        input_path = self.input_path_edit.text().strip()
        if not input_path or not os.path.isdir(input_path):
            self.logger.error("请选择有效的输入目录")
            return

        # 检查输出路径
        output_path = self.output_path_edit.text().strip()
        if not output_path:
            self.logger.error("请选择有效的输出目录")
            return

        # 创建输出目录
        if not os.path.exists(output_path):
            try:
                os.makedirs(output_path)
            except Exception as e:
                self.logger.error(f"创建输出目录失败: {str(e)}")
                return

        # 检查是否有视频
        if not self.video_preview.has_videos():
            self.logger.error("没有找到可处理的视频文件")
            return

        # 获取参数
        start_time = self.start_time_spin.value()

        # 获取分割模式和值
        if self.duration_radio.isChecked():
            split_mode = 'duration'
            split_value = self.split_duration_spin.value()
        else:
            split_mode = 'count'
            split_value = self.split_count_spin.value()

        # 获取质量
        quality = self.quality_slider.value()

        # 获取视频选区
        selection_regions = self.video_preview.get_selection_regions()

        # 设置UI状态
        self.processing = True
        self.start_button.setText("取消处理")
        self.disable_inputs(True)

        # 开始处理
        try:
            self.video_processor.process_videos(
                input_path, output_path, start_time,
                split_mode, split_value, quality,
                selection_regions
            )

            # 启动定时器检查处理状态
            self.check_processing_timer = QTimer()
            self.check_processing_timer.timeout.connect(self.check_processing_status)
            self.check_processing_timer.start(500)  # 每500毫秒检查一次

        except Exception as e:
            self.logger.error(f"启动处理任务失败: {str(e)}")
            self.processing = False
            self.start_button.setText("开始处理")
            self.disable_inputs(False)

    def check_processing_status(self):
        """检查处理状态"""
        if not self.video_processor.processing:
            # 处理完成或中止
            self.check_processing_timer.stop()
            self.processing = False
            self.start_button.setText("开始处理")
            self.disable_inputs(False)

            # 弹出完成提示
            if not self.video_processor.abort_flag:
                QMessageBox.information(self, "处理完成", "所有视频已处理完成！")

    def abort_processing(self):
        """中止处理"""
        if not self.processing:
            return

        # 设置中止标志
        self.video_processor.abort_processing()
        self.start_button.setEnabled(False)
        self.start_button.setText("正在中止...")

    def disable_inputs(self, disabled):
        """
        禁用/启用输入控件

        Args:
            disabled: 是否禁用
        """
        self.input_path_edit.setEnabled(not disabled)
        self.output_path_edit.setEnabled(not disabled)
        self.browse_input_button.setEnabled(not disabled)
        self.browse_output_button.setEnabled(not disabled)
        self.start_time_spin.setEnabled(not disabled)
        self.duration_radio.setEnabled(not disabled)
        self.count_radio.setEnabled(not disabled)
        self.split_duration_spin.setEnabled(not disabled and self.duration_radio.isChecked())
        self.split_count_spin.setEnabled(not disabled and self.count_radio.isChecked())
        self.quality_slider.setEnabled(not disabled)

    def closeEvent(self, event):
        """
        窗口关闭事件处理

        Args:
            event: 关闭事件对象
        """
        # 中止处理任务
        if self.processing:
            self.video_processor.abort_processing()

        # 接受关闭事件
        event.accept()