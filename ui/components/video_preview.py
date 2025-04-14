
# -*- coding: utf-8 -*-

"""
视频预览组件
负责视频的播放、显示和框选功能
"""

import os
import cv2
from typing import Dict, List, Tuple, Optional, Any, Union

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QListWidget, QListWidgetItem,
    QSplitter, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, QSize, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QPainter, QPen, QColor, QImage, QPixmap, QFont, QBrush


class VideoDisplay(QWidget):
    """视频显示组件，负责显示视频帧和处理框选操作"""

    # 添加一个信号用于通知选区变化
    selection_changed = pyqtSignal(object)  # 选区变化信号，参数为新的选区

    def __init__(self):
        """初始化视频显示组件"""
        super().__init__()

        # 显示相关变量
        self.frame = None  # 当前原始帧
        self.scaled_frame = None  # 缩放后的帧
        self.display_rect = QRect()  # 显示区域

        # 框选相关变量
        self.selection_start = None  # 框选开始点
        self.selection_end = None  # 框选结束点
        self.selection_active = False  # 是否正在进行框选
        self.selection_region = None  # 框选区域，相对坐标(x, y, width, height)
        self.is_adjusting = False  # 是否正在调整框选
        self.adjusting_edge = None  # 正在调整的边

        # 设置鼠标追踪
        self.setMouseTracking(True)

        # 设置焦点策略
        self.setFocusPolicy(Qt.StrongFocus)

        # 设置最小尺寸
        self.setMinimumSize(400, 300)

    def set_frame(self, frame):
        """
        设置当前帧

        Args:
            frame: OpenCV格式的视频帧
        """
        self.frame = frame
        self.update_scaled_frame()
        self.update()

    def update_scaled_frame(self):
        """更新缩放后的帧以适应窗口大小"""
        try:
            if self.frame is None:
                return

            # 获取窗口大小
            widget_width = self.width()
            widget_height = self.height()

            if widget_width <= 0 or widget_height <= 0:
                return

            # 获取帧大小
            frame_height, frame_width = self.frame.shape[:2]

            if frame_width <= 0 or frame_height <= 0:
                return

            # 计算缩放比例
            width_ratio = widget_width / frame_width
            height_ratio = widget_height / frame_height
            ratio = min(width_ratio, height_ratio)

            # 计算缩放后的大小
            new_width = int(frame_width * ratio)
            new_height = int(frame_height * ratio)

            # 确保新尺寸有效
            if new_width <= 0 or new_height <= 0:
                return

            # 计算居中显示的矩形
            x = (widget_width - new_width) // 2
            y = (widget_height - new_height) // 2
            self.display_rect = QRect(x, y, new_width, new_height)

            # 缩放帧
            self.scaled_frame = cv2.resize(self.frame, (new_width, new_height))
        except Exception as e:
            print(f"更新缩放帧错误: {str(e)}")

    def paintEvent(self, event):
        """
        绘制事件

        Args:
            event: 绘制事件对象
        """
        try:
            if self.scaled_frame is None:
                # 如果没有帧，绘制黑色背景
                painter = QPainter(self)
                painter.fillRect(self.rect(), QColor(0, 0, 0))
                # 绘制提示文本
                painter.setPen(QColor(255, 255, 255))
                font = QFont()
                font.setPointSize(12)
                painter.setFont(font)
                painter.drawText(self.rect(), Qt.AlignCenter, "没有视频")
                return

            painter = QPainter(self)

            # 绘制黑色背景
            painter.fillRect(self.rect(), QColor(0, 0, 0))

            # 确保有效的scaled_frame和display_rect
            if self.scaled_frame is not None and self.scaled_frame.size > 0 and self.display_rect.isValid() and self.display_rect.width() > 0 and self.display_rect.height() > 0:
                # 绘制视频帧
                height, width = self.scaled_frame.shape[:2]
                if width > 0 and height > 0 and width <= 5000 and height <= 5000:  # 防止过大或无效的尺寸
                    bytes_per_line = 3 * width
                    q_image = QImage(self.scaled_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_image)
                    painter.drawPixmap(self.display_rect, pixmap)

            # 绘制框选区域
            if self.selection_region and self.display_rect.isValid() and self.display_rect.width() > 0 and self.display_rect.height() > 0:
                # 确保selection_region包含有效值
                if (len(self.selection_region) == 4 and
                        all(isinstance(val, (int, float)) for val in self.selection_region) and
                        all(0 <= val <= 1 for val in self.selection_region[:2]) and  # x, y应在0-1范围内
                        all(0 < val <= 1 for val in self.selection_region[2:])):  # width, height应大于0且不超过1

                    # 计算框选矩形在显示区域上的坐标
                    sel_x = int(self.display_rect.x() + self.selection_region[0] * self.display_rect.width())
                    sel_y = int(self.display_rect.y() + self.selection_region[1] * self.display_rect.height())
                    sel_width = int(self.selection_region[2] * self.display_rect.width())
                    sel_height = int(self.selection_region[3] * self.display_rect.height())

                    # 绘制半透明遮罩
                    painter.setBrush(QBrush(QColor(0, 0, 0, 100)))
                    painter.setPen(Qt.NoPen)

                    # 上方遮罩
                    painter.drawRect(
                        self.display_rect.x(), self.display_rect.y(),
                        self.display_rect.width(), sel_y - self.display_rect.y()
                    )
                    # 下方遮罩
                    painter.drawRect(
                        self.display_rect.x(), sel_y + sel_height,
                        self.display_rect.width(),
                                               self.display_rect.height() - (sel_y + sel_height - self.display_rect.y())
                    )
                    # 左侧遮罩
                    painter.drawRect(
                        self.display_rect.x(), sel_y,
                        sel_x - self.display_rect.x(), sel_height
                    )
                    # 右侧遮罩
                    painter.drawRect(
                        sel_x + sel_width, sel_y,
                        self.display_rect.width() - (sel_x + sel_width - self.display_rect.x()), sel_height
                    )

                    # 绘制框选边框
                    painter.setPen(QPen(QColor(0, 255, 0), 2, Qt.SolidLine))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRect(sel_x, sel_y, sel_width, sel_height)

                    # 绘制调整控制点
                    control_size = 10  # 增大控制点尺寸
                    painter.setBrush(QBrush(QColor(0, 255, 0)))

                    # 四个角的控制点
                    painter.drawRect(int(sel_x - control_size // 2), int(sel_y - control_size // 2), control_size,
                                     control_size)  # 左上
                    painter.drawRect(int(sel_x + sel_width - control_size // 2), int(sel_y - control_size // 2),
                                     control_size, control_size)  # 右上
                    painter.drawRect(int(sel_x - control_size // 2), int(sel_y + sel_height - control_size // 2),
                                     control_size, control_size)  # 左下
                    painter.drawRect(int(sel_x + sel_width - control_size // 2),
                                     int(sel_y + sel_height - control_size // 2), control_size, control_size)  # 右下

                    # 四边的控制点
                    painter.drawRect(int(sel_x + sel_width // 2 - control_size // 2), int(sel_y - control_size // 2),
                                     control_size, control_size)  # 上
                    painter.drawRect(int(sel_x + sel_width // 2 - control_size // 2),
                                     int(sel_y + sel_height - control_size // 2), control_size, control_size)  # 下
                    painter.drawRect(int(sel_x - control_size // 2), int(sel_y + sel_height // 2 - control_size // 2),
                                     control_size, control_size)  # 左
                    painter.drawRect(int(sel_x + sel_width - control_size // 2),
                                     int(sel_y + sel_height // 2 - control_size // 2), control_size, control_size)  # 右

                    # 添加提示文本
                    painter.setPen(QColor(255, 255, 255))
                    font = QFont()
                    font.setPointSize(9)
                    painter.setFont(font)

                    # 检查是否有足够空间显示提示信息
                    if sel_y > 30:  # 在框选区域上方有足够空间
                        painter.drawText(
                            QRect(sel_x, sel_y - 30, sel_width, 20),
                            Qt.AlignCenter,
                            "拖拽绿色方块调整选区大小"
                        )

            elif self.selection_active and self.selection_start and self.selection_end:
                # 确保selection_start和selection_end是有效的QPoint
                if (isinstance(self.selection_start, QPoint) and
                        isinstance(self.selection_end, QPoint)):

                    # 绘制正在进行的框选
                    x = min(self.selection_start.x(), self.selection_end.x())
                    y = min(self.selection_start.y(), self.selection_end.y())
                    width = abs(self.selection_end.x() - self.selection_start.x())
                    height = abs(self.selection_end.y() - self.selection_start.y())

                    # 只绘制合理大小的框选
                    if width > 0 and height > 0 and width < 5000 and height < 5000:
                        painter.setPen(QPen(QColor(0, 255, 0), 2, Qt.DashLine))
                        painter.setBrush(QBrush(QColor(0, 255, 0, 50)))
                        painter.drawRect(x, y, width, height)

            # 如果没有选区，显示提示
            elif self.scaled_frame is not None:
                # 绘制提示文本
                painter.setPen(QColor(255, 255, 255))
                font = QFont()
                font.setPointSize(10)
                painter.setFont(font)
                painter.drawText(
                    QRect(self.display_rect.x(), self.display_rect.y() + self.display_rect.height() - 30,
                          self.display_rect.width(), 20),
                    Qt.AlignCenter,
                    "鼠标拖拽可框选图像区域"
                )

        except Exception as e:
            # 出现异常时记录错误，但不中断绘制
            print(f"绘制事件错误: {str(e)}")

    def mousePressEvent(self, event):
        """
        鼠标按下事件

        Args:
            event: 鼠标事件对象
        """
        try:
            if event.button() == Qt.LeftButton:
                if self.selection_region and self.is_near_edge(event.pos()):
                    # 如果点击位置靠近边缘，开始调整
                    self.is_adjusting = True
                    self.adjusting_edge = self.get_nearest_edge(event.pos())
                elif not self.display_rect.contains(event.pos()):
                    # 如果点击位置不在显示区域内，忽略
                    return
                else:
                    # 否则开始新的框选
                    self.selection_start = event.pos()
                    self.selection_end = event.pos()
                    self.selection_active = True
                    self.selection_region = None
                    self.is_adjusting = False
        except Exception as e:
            print(f"鼠标按下事件发生错误: {str(e)}")

    def mouseMoveEvent(self, event):
        """
        鼠标移动事件

        Args:
            event: 鼠标事件对象
        """
        try:
            if self.is_adjusting and self.selection_region:
                # 调整框选区域
                self.adjust_selection(event.pos())
            elif self.selection_active:
                # 更新正在进行的框选
                self.selection_end = event.pos()
                self.update()
            elif self.selection_region:
                # 更新鼠标样式
                if self.is_near_edge(event.pos()):
                    edge = self.get_nearest_edge(event.pos())
                    self.update_cursor(edge)
                else:
                    self.setCursor(Qt.ArrowCursor)
        except Exception as e:
            print(f"鼠标移动事件发生错误: {str(e)}")

    def mouseReleaseEvent(self, event):
        """
        鼠标释放事件

        Args:
            event: 鼠标事件对象
        """
        try:
            if event.button() == Qt.LeftButton:
                if self.is_adjusting:
                    # 结束调整
                    self.is_adjusting = False
                    # 通知选区已改变
                    self.selection_changed.emit(self.selection_region)
                elif self.selection_active:
                    # 结束框选
                    self.selection_active = False

                    # 确保框选区域合法
                    if self.is_valid_selection():
                        # 计算框选区域在原始帧上的比例
                        x = min(self.selection_start.x(), self.selection_end.x())
                        y = min(self.selection_start.y(), self.selection_end.y())
                        width = abs(self.selection_end.x() - self.selection_start.x())
                        height = abs(self.selection_end.y() - self.selection_start.y())

                        # 转换为相对于显示区域的坐标
                        if self.display_rect.width() <= 0 or self.display_rect.height() <= 0:
                            return

                        # 裁剪到显示区域内
                        x = max(x, self.display_rect.x())
                        y = max(y, self.display_rect.y())
                        right = min(x + width, self.display_rect.x() + self.display_rect.width())
                        bottom = min(y + height, self.display_rect.y() + self.display_rect.height())

                        # 重新计算宽度和高度
                        width = right - x
                        height = bottom - y

                        # 计算相对坐标
                        rel_x = (x - self.display_rect.x()) / self.display_rect.width()
                        rel_y = (y - self.display_rect.y()) / self.display_rect.height()
                        rel_width = width / self.display_rect.width()
                        rel_height = height / self.display_rect.height()

                        self.selection_region = (rel_x, rel_y, rel_width, rel_height)
                        # 通知选区已改变
                        self.selection_changed.emit(self.selection_region)

                    self.update()
        except Exception as e:
            print(f"鼠标释放事件发生错误: {str(e)}")

    def is_valid_selection(self):
        """
        检查框选区域是否有效

        Returns:
            True如果框选区域有效，否则False
        """
        try:
            if not self.selection_start or not self.selection_end:
                return False

            # 检查框选区域大小是否足够
            min_size = 10
            width = abs(self.selection_end.x() - self.selection_start.x())
            height = abs(self.selection_end.y() - self.selection_start.y())

            # 检查是否与显示区域有交集
            if (self.selection_start.x() > self.display_rect.right() or
                    self.selection_end.x() < self.display_rect.left() or
                    self.selection_start.y() > self.display_rect.bottom() or
                    self.selection_end.y() < self.display_rect.top()):
                return False

            return width >= min_size and height >= min_size
        except Exception as e:
            print(f"检查框选有效性错误: {str(e)}")
            return False

    def is_near_edge(self, pos):
        """
        检查位置是否靠近框选边缘

        Args:
            pos: 鼠标位置

        Returns:
            True如果位置靠近框选边缘，否则False
        """
        try:
            if not self.selection_region or not self.display_rect.isValid():
                return False

            # 检查显示区域是否有效
            if self.display_rect.width() <= 0 or self.display_rect.height() <= 0:
                return False

            # 计算框选区域在显示区域上的坐标
            sel_x = int(self.display_rect.x() + self.selection_region[0] * self.display_rect.width())
            sel_y = int(self.display_rect.y() + self.selection_region[1] * self.display_rect.height())
            sel_width = int(self.selection_region[2] * self.display_rect.width())
            sel_height = int(self.selection_region[3] * self.display_rect.height())

            # 检查鼠标位置是否靠近边缘
            tolerance = 8  # 增加容错像素范围，使拖拽边缘更容易

            # 检查左边缘
            if abs(pos.x() - sel_x) <= tolerance and sel_y - tolerance <= pos.y() <= sel_y + sel_height + tolerance:
                return True

            # 检查右边缘
            if abs(pos.x() - (
                    sel_x + sel_width)) <= tolerance and sel_y - tolerance <= pos.y() <= sel_y + sel_height + tolerance:
                return True

            # 检查上边缘
            if abs(pos.y() - sel_y) <= tolerance and sel_x - tolerance <= pos.x() <= sel_x + sel_width + tolerance:
                return True

            # 检查下边缘
            if abs(pos.y() - (
                    sel_y + sel_height)) <= tolerance and sel_x - tolerance <= pos.x() <= sel_x + sel_width + tolerance:
                return True

            # 检查四个角 (增加容错)
            if ((abs(pos.x() - sel_x) <= tolerance * 1.5 and abs(pos.y() - sel_y) <= tolerance * 1.5) or  # 左上
                    (abs(pos.x() - (sel_x + sel_width)) <= tolerance * 1.5 and abs(
                        pos.y() - sel_y) <= tolerance * 1.5) or  # 右上
                    (abs(pos.x() - sel_x) <= tolerance * 1.5 and abs(
                        pos.y() - (sel_y + sel_height)) <= tolerance * 1.5) or  # 左下
                    (abs(pos.x() - (sel_x + sel_width)) <= tolerance * 1.5 and abs(
                        pos.y() - (sel_y + sel_height)) <= tolerance * 1.5)):  # 右下
                return True

            return False
        except Exception as e:
            print(f"边缘检测错误: {str(e)}")
            return False

    def get_nearest_edge(self, pos):
        """
        获取鼠标位置最近的边缘

        Args:
            pos: 鼠标位置

        Returns:
            表示边缘的字符串: 'left', 'right', 'top', 'bottom', 'top-left', 'top-right', 'bottom-left', 'bottom-right'
        """
        try:
            if not self.selection_region or not self.display_rect.isValid():
                return None

            # 计算框选区域在显示区域上的坐标
            sel_x = int(self.display_rect.x() + self.selection_region[0] * self.display_rect.width())
            sel_y = int(self.display_rect.y() + self.selection_region[1] * self.display_rect.height())
            sel_width = int(self.selection_region[2] * self.display_rect.width())
            sel_height = int(self.selection_region[3] * self.display_rect.height())

            # 计算鼠标到各边缘的距离
            dist_left = abs(pos.x() - sel_x)
            dist_right = abs(pos.x() - (sel_x + sel_width))
            dist_top = abs(pos.y() - sel_y)
            dist_bottom = abs(pos.y() - (sel_y + sel_height))

            tolerance = 8  # 增加容错像素范围

            # 检查四个角
            if dist_left <= tolerance and dist_top <= tolerance:
                return 'top-left'
            if dist_right <= tolerance and dist_top <= tolerance:
                return 'top-right'
            if dist_left <= tolerance and dist_bottom <= tolerance:
                return 'bottom-left'
            if dist_right <= tolerance and dist_bottom <= tolerance:
                return 'bottom-right'

            # 检查四条边
            if dist_left <= tolerance and sel_y <= pos.y() <= sel_y + sel_height:
                return 'left'
            if dist_right <= tolerance and sel_y <= pos.y() <= sel_y + sel_height:
                return 'right'
            if dist_top <= tolerance and sel_x <= pos.x() <= sel_x + sel_width:
                return 'top'
            if dist_bottom <= tolerance and sel_x <= pos.x() <= sel_x + sel_width:
                return 'bottom'

            return None
        except Exception as e:
            print(f"获取最近边缘错误: {str(e)}")
            return None

    def update_cursor(self, edge):
        """
        根据边缘更新鼠标样式

        Args:
            edge: 边缘类型
        """
        try:
            if edge in ['left', 'right']:
                self.setCursor(Qt.SizeHorCursor)
            elif edge in ['top', 'bottom']:
                self.setCursor(Qt.SizeVerCursor)
            elif edge in ['top-left', 'bottom-right']:
                self.setCursor(Qt.SizeFDiagCursor)
            elif edge in ['top-right', 'bottom-left']:
                self.setCursor(Qt.SizeBDiagCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        except Exception as e:
            print(f"更新鼠标样式错误: {str(e)}")
            self.setCursor(Qt.ArrowCursor)

    def adjust_selection(self, pos):
        """
        根据鼠标位置调整框选区域

        Args:
            pos: 鼠标位置
        """
        try:
            if not self.selection_region or not self.display_rect.isValid() or not self.adjusting_edge:
                return

            # 确保显示区域尺寸有效
            if self.display_rect.width() <= 0 or self.display_rect.height() <= 0:
                return

            # 计算框选区域在显示区域上的坐标
            sel_x = int(self.display_rect.x() + self.selection_region[0] * self.display_rect.width())
            sel_y = int(self.display_rect.y() + self.selection_region[1] * self.display_rect.height())
            sel_width = int(self.selection_region[2] * self.display_rect.width())
            sel_height = int(self.selection_region[3] * self.display_rect.height())

            # 根据调整的边缘更新坐标
            if self.adjusting_edge == 'left':
                new_x = max(self.display_rect.x(), min(pos.x(), sel_x + sel_width - 10))
                new_width = sel_width - (new_x - sel_x)
                sel_x = new_x
                sel_width = new_width
            elif self.adjusting_edge == 'right':
                new_width = max(10, min(pos.x() - sel_x, self.display_rect.right() - sel_x))
                sel_width = new_width
            elif self.adjusting_edge == 'top':
                new_y = max(self.display_rect.y(), min(pos.y(), sel_y + sel_height - 10))
                new_height = sel_height - (new_y - sel_y)
                sel_y = new_y
                sel_height = new_height
            elif self.adjusting_edge == 'bottom':
                new_height = max(10, min(pos.y() - sel_y, self.display_rect.bottom() - sel_y))
                sel_height = new_height
            elif self.adjusting_edge == 'top-left':
                new_x = max(self.display_rect.x(), min(pos.x(), sel_x + sel_width - 10))
                new_y = max(self.display_rect.y(), min(pos.y(), sel_y + sel_height - 10))
                new_width = sel_width - (new_x - sel_x)
                new_height = sel_height - (new_y - sel_y)
                sel_x = new_x
                sel_y = new_y
                sel_width = new_width
                sel_height = new_height
            elif self.adjusting_edge == 'top-right':
                new_y = max(self.display_rect.y(), min(pos.y(), sel_y + sel_height - 10))
                new_width = max(10, min(pos.x() - sel_x, self.display_rect.right() - sel_x))
                new_height = sel_height - (new_y - sel_y)
                sel_y = new_y
                sel_width = new_width
                sel_height = new_height
            elif self.adjusting_edge == 'bottom-left':
                new_x = max(self.display_rect.x(), min(pos.x(), sel_x + sel_width - 10))
                new_width = sel_width - (new_x - sel_x)
                new_height = max(10, min(pos.y() - sel_y, self.display_rect.bottom() - sel_y))
                sel_x = new_x
                sel_width = new_width
                sel_height = new_height
            elif self.adjusting_edge == 'bottom-right':
                new_width = max(10, min(pos.x() - sel_x, self.display_rect.right() - sel_x))
                new_height = max(10, min(pos.y() - sel_y, self.display_rect.bottom() - sel_y))
                sel_width = new_width
                sel_height = new_height

            # 更新选择区域的相对坐标
            rel_x = float(sel_x - self.display_rect.x()) / float(self.display_rect.width())
            rel_y = float(sel_y - self.display_rect.y()) / float(self.display_rect.height())
            rel_width = float(sel_width) / float(self.display_rect.width())
            rel_height = float(sel_height) / float(self.display_rect.height())

            self.selection_region = (rel_x, rel_y, rel_width, rel_height)
            self.update()
        except Exception as e:
            print(f"调整选择区域错误: {str(e)}")

    def set_selection_region(self, region):
        """
        设置框选区域

        Args:
            region: 框选区域，相对坐标(x, y, width, height)
        """
        self.selection_region = region
        self.selection_start = None
        self.selection_end = None
        self.selection_active = False
        self.update()
        # 发出选区变化信号
        self.selection_changed.emit(region)

    def clear_selection(self):
        """清除框选"""
        self.selection_region = None
        self.selection_start = None
        self.selection_end = None
        self.selection_active = False
        self.is_adjusting = False
        self.update()
        # 发出选区变化信号
        self.selection_changed.emit(None)

    def get_selection_region(self):
        """
        获取框选区域

        Returns:
            框选区域，相对坐标(x, y, width, height)
        """
        return self.selection_region

    def resizeEvent(self, event):
        """
        大小调整事件

        Args:
            event: 大小调整事件对象
        """
        self.update_scaled_frame()
        super().resizeEvent(event)


class VideoFrameThread(QThread):
    """视频帧处理线程"""

    # 自定义信号
    frame_ready = pyqtSignal(object)  # 帧就绪信号，参数为视频帧
    finished = pyqtSignal()  # 处理完成信号

    def __init__(self, cap=None):
        """
        初始化视频帧处理线程

        Args:
            cap: OpenCV视频捕获器
        """
        super().__init__()
        self.cap = cap
        self.running = False
        self.paused = False
        self.current_frame_index = 0
        self.target_frame_index = -1
        self.fps = 30
        self.frame_count = 0

    def set_capture(self, cap):
        """
        设置视频捕获器

        Args:
            cap: OpenCV视频捕获器
        """
        self.cap = cap
        if self.cap:
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()

    def pause(self):
        """暂停视频播放"""
        self.paused = True

    def resume(self):
        """恢复视频播放"""
        self.paused = False

    def seek(self, frame_index):
        """
        跳转到指定帧

        Args:
            frame_index: 目标帧索引
        """
        if not self.cap:
            return

        self.target_frame_index = frame_index

    def run(self):
        """线程运行方法"""
        self.running = True

        while self.running:
            if not self.cap:
                self.msleep(100)
                continue

            # 检查是否需要跳转
            if self.target_frame_index >= 0:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.target_frame_index)
                self.current_frame_index = self.target_frame_index
                self.target_frame_index = -1

            # 如果暂停，则不读取新帧
            if self.paused:
                self.msleep(100)
                continue

            # 读取当前帧
            ret, frame = self.cap.read()

            if not ret:
                # 视频结束
                self.current_frame_index = 0
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.paused = True
                self.finished.emit()
                continue

            # 增加帧索引
            self.current_frame_index += 1

            # 转换颜色空间
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 发送帧就绪信号
            self.frame_ready.emit(frame_rgb)

            # 根据帧率计算延迟时间
            delay = int(1000 / self.fps) if self.fps > 0 else 33
            self.msleep(delay)


class VideoPreview(QWidget):
    """视频预览组件，包括视频列表、视频显示和控制"""

    # 自定义信号
    video_loaded = pyqtSignal(str)  # 视频加载信号，参数为视频路径

    def __init__(self):
        """初始化视频预览组件"""
        super().__init__()

        # 初始化UI
        self.init_ui()

        # 视频相关变量
        self.videos = []  # 视频文件列表
        self.current_video = None  # 当前视频文件
        self.cap = None  # OpenCV视频捕获
        self.frame = None  # 当前帧
        self.playing = False  # 播放状态

        # 创建视频帧处理线程
        self.frame_thread = VideoFrameThread()
        self.frame_thread.frame_ready.connect(self.on_frame_ready)
        self.frame_thread.finished.connect(self.on_video_finished)

        # 框选相关变量
        self.selection_regions = {}  # 存储每个视频的框选区域
        self.selection_changed = False  # 标记选区是否被修改

        # 连接信号
        self.connect_signals()

        # 启动帧处理线程
        self.frame_thread.start()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧视频列表
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)

        # 添加视频列表标签
        list_label = QLabel("视频列表")
        list_label.setAlignment(Qt.AlignCenter)
        list_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #f0f0f0;
            border-bottom: 1px solid #ddd;
        """)
        list_layout.addWidget(list_label)

        # 添加视频列表
        self.video_list = QListWidget()
        self.video_list.setMinimumWidth(150)
        list_layout.addWidget(self.video_list)

        # 右侧视频预览和控制
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # 视频显示区域
        self.video_display = VideoDisplay()

        # 添加选区状态标签
        self.selection_status = QLabel("选区状态: 无选区")
        self.selection_status.setAlignment(Qt.AlignCenter)
        self.selection_status.setStyleSheet("""
            font-size: 12px;
            padding: 3px;
            background-color: #f8f8f8;
            color: #666;
            border-top: 1px solid #ddd;
        """)

        # 视频控制工具栏
        control_layout = QHBoxLayout()

        # 播放/暂停按钮
        self.play_button = QPushButton("播放")
        self.play_button.setMinimumWidth(80)

        # 进度条
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(100)

        # 时间标签
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMinimumWidth(100)
        self.time_label.setAlignment(Qt.AlignCenter)

        # 清除框选按钮
        self.clear_selection_button = QPushButton("清除框选")
        self.clear_selection_button.setMinimumWidth(80)

        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.progress_slider, 1)  # 进度条占据更多空间
        control_layout.addWidget(self.time_label)
        control_layout.addWidget(self.clear_selection_button)

        preview_layout.addWidget(self.video_display, 1)
        preview_layout.addWidget(self.selection_status)
        preview_layout.addLayout(control_layout)

        # 添加到分割器
        splitter.addWidget(list_widget)
        splitter.addWidget(preview_widget)

        # 设置分割比例
        splitter.setSizes([200, 800])  # 视频列表占较少空间

        layout.addWidget(splitter)

        # 设置最小高度
        self.setMinimumHeight(400)

        # 设置样式
        self.setup_styles()

    def setup_styles(self):
        """设置样式"""
        self.video_list.setStyleSheet("""
            QListWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e9ecef;
            }
        """)

        self.video_display.setStyleSheet("""
            border: 1px solid #ddd;
            border-radius: 5px;
            background-color: black;
        """)

        self.progress_slider.setStyleSheet("""
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
        """)

        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
            QPushButton:pressed {
                background-color: #005cbf;
            }
        """)

        self.clear_selection_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)

    def connect_signals(self):
        """连接信号"""
        self.video_list.itemClicked.connect(self.on_video_selected)
        self.play_button.clicked.connect(self.toggle_play)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        self.progress_slider.valueChanged.connect(self.on_slider_value_changed)
        self.clear_selection_button.clicked.connect(self.clear_selection)

        # 连接选区变化信号
        self.video_display.selection_changed.connect(self.on_selection_changed)

        # 添加定时器更新进度条和时间标签
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(100)  # 每100毫秒更新一次

    def set_videos(self, videos):
        """
        设置视频列表

        Args:
            videos: 视频文件路径列表
        """
        self.videos = videos
        self.video_list.clear()

        for video in videos:
            filename = os.path.basename(video)
            item = QListWidgetItem(filename)
            item.setData(Qt.UserRole, video)  # 存储完整路径
            self.video_list.addItem(item)

        # 保留之前已有的框选区域
        old_regions = self.selection_regions.copy()

        # 初始化框选区域字典，保留旧的选区
        new_regions = {}
        for video in videos:
            # 如果该视频之前有选区，则保留
            if video in old_regions and old_regions[video]:
                new_regions[video] = old_regions[video]
            else:
                new_regions[video] = None

        self.selection_regions = new_regions

        # 如果有视频，加载第一个
        if videos:
            self.video_list.setCurrentRow(0)
            self.on_video_selected(self.video_list.item(0))

    @pyqtSlot(object)
    def on_frame_ready(self, frame):
        """
        帧就绪事件处理

        Args:
            frame: 视频帧
        """
        # 保存当前帧
        self.frame = frame

        # 更新视频显示
        self.video_display.set_frame(frame)

    @pyqtSlot()
    def on_video_finished(self):
        """视频播放完成事件处理"""
        self.playing = False
        self.play_button.setText("播放")

    def update_ui(self):
        """更新UI元素（进度条和时间标签）"""
        if not self.cap or not self.frame_thread.running:
            return

        # 获取当前帧索引
        current_frame = self.frame_thread.current_frame_index

        # 更新进度条（仅当未被用户拖动时）
        if not self.progress_slider.isSliderDown():
            self.progress_slider.setValue(current_frame)

        # 更新时间标签
        fps = self.frame_thread.fps
        frame_count = self.frame_thread.frame_count

        current_time = current_frame / fps if fps > 0 else 0
        total_time = frame_count / fps if fps > 0 else 0

        current_time_str = self.format_time(current_time)
        total_time_str = self.format_time(total_time)

        self.time_label.setText(f"{current_time_str} / {total_time_str}")

    def on_video_selected(self, item):
        """
        视频选择事件

        Args:
            item: 选中的列表项
        """
        try:
            self.stop_playback()

            video_path = item.data(Qt.UserRole)
            self.current_video = video_path

            # 打开视频
            self.open_video(video_path)

            # 明确重置帧索引和进度条位置
            self.frame_thread.current_frame_index = 0
            self.progress_slider.setValue(0)

            # 检查是否有保存的框选区域
            if video_path in self.selection_regions and self.selection_regions.get(video_path):
                selection = self.selection_regions[video_path]
                self.video_display.set_selection_region(selection)
                print(f"已恢复视频 {os.path.basename(video_path)} 的选区")

                # 更新选区状态显示
                x, y, w, h = selection
                self.selection_status.setText(f"选区状态: 已选择区域 ({x:.2f}, {y:.2f}, {w:.2f}, {h:.2f})")
                self.selection_status.setStyleSheet("""
                    font-size: 12px;
                    padding: 3px;
                    background-color: #e6f7e6;
                    color: #28a745;
                    border-top: 1px solid #ddd;
                    font-weight: bold;
                """)
            else:
                self.video_display.clear_selection()
                # 更新选区状态显示
                self.selection_status.setText("选区状态: 无选区")
                self.selection_status.setStyleSheet("""
                    font-size: 12px;
                    padding: 3px;
                    background-color: #f8f8f8;
                    color: #666;
                    border-top: 1px solid #ddd;
                """)

            # 发送视频加载信号
            self.video_loaded.emit(video_path)
        except Exception as e:
            print(f"视频选择错误: {str(e)}")

    def open_video(self, video_path):
        """
        打开视频

        Args:
            video_path: 视频文件路径
        """
        # 停止当前视频播放
        self.frame_thread.stop()

        if self.cap:
            self.cap.release()

        # 创建新的视频捕获器
        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            raise Exception(f"无法打开视频: {video_path}")

        # 设置视频捕获器到线程
        self.frame_thread.set_capture(self.cap)

        # 重置播放状态
        self.playing = False
        self.play_button.setText("播放")

        # 重置进度条
        frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.progress_slider.setMaximum(frame_count - 1)
        self.progress_slider.setValue(0)

        # 重置显示时间
        self.time_label.setText(
            "00:00 / " + self.format_time(frame_count / self.frame_thread.fps if self.frame_thread.fps > 0 else 0))

        # 读取第一帧并显示
        ret, frame = self.cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.video_display.set_frame(frame_rgb)
            self.frame = frame_rgb

        # 确保线程暂停
        self.frame_thread.pause()
        # 重新启动线程
        self.frame_thread.start()

    def toggle_play(self):
        """切换播放/暂停状态"""
        if not self.cap:
            return

        if self.playing:
            self.stop_playback()
        else:
            self.start_playback()

    def start_playback(self):
        """开始播放"""
        if not self.cap:
            return

        self.playing = True
        self.play_button.setText("暂停")
        self.frame_thread.resume()

    def stop_playback(self):
        """停止播放"""
        self.playing = False
        self.play_button.setText("播放")
        self.frame_thread.pause()

    def on_slider_pressed(self):
        """进度条按下事件"""
        self.frame_thread.pause()

    def on_slider_released(self):
        """进度条释放事件"""
        if not self.cap:
            return

        # 获取滑块位置
        frame_pos = self.progress_slider.value()

        # 跳转到指定帧
        self.frame_thread.seek(frame_pos)

        # 如果之前是播放状态则恢复播放
        if self.playing:
            self.frame_thread.resume()

    def on_slider_value_changed(self, value):
        """
        进度条值改变事件

        Args:
            value: 进度条新值
        """
        # 只有在用户拖动时才处理
        if not self.cap or not self.progress_slider.isSliderDown():
            return

    def closeEvent(self, event):
        """
        窗口关闭事件处理

        Args:
            event: 关闭事件对象
        """
        try:
            # 停止视频帧处理线程
            if hasattr(self, 'frame_thread') and self.frame_thread and self.frame_thread.isRunning():
                self.frame_thread.stop()

            # 释放视频资源
            if hasattr(self, 'cap') and self.cap:
                self.cap.release()

            # 停止定时器
            if hasattr(self, 'update_timer') and self.update_timer and self.update_timer.isActive():
                self.update_timer.stop()

            event.accept()
        except Exception as e:
            print(f"关闭事件错误: {str(e)}")
            event.accept()

    def format_time(self, seconds):
        """
        格式化时间

        Args:
            seconds: 秒数

        Returns:
            格式化后的时间字符串，如"01:30"
        """
        minutes = int(seconds / 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def clear_selection(self):
        """清除当前视频的框选"""
        if self.current_video:
            # 清除当前视频的选区
            self.selection_regions[self.current_video] = None
            print(f"已清除视频 {os.path.basename(self.current_video)} 的选区")
            # 清除显示
            self.video_display.clear_selection()

    def has_videos(self):
        """
        检查是否有视频

        Returns:
            True如果有视频，否则False
        """
        return len(self.videos) > 0

    def get_selection_regions(self):
        """
        获取所有视频的框选区域

        Returns:
            包含所有视频框选区域的字典
        """
        try:
            # 确保获取视频显示中最新的框选区域
            if self.current_video:
                selection = self.video_display.get_selection_region()
                # 保存当前视频的选区
                if selection:
                    self.selection_regions[self.current_video] = selection
                    print(f"已保存视频 {os.path.basename(self.current_video)} 的选区")
                elif self.current_video in self.selection_regions and not selection:
                    # 如果之前有选区但现在没有，清除选区
                    self.selection_regions[self.current_video] = None
                    print(f"已清除视频 {os.path.basename(self.current_video)} 的选区")

            # 过滤掉None值，只保留有效的框选区域
            return {video: region for video, region in self.selection_regions.items() if region is not None}
        except Exception as e:
            print(f"获取选择区域错误: {str(e)}")
            return {}

    def on_selection_changed(self, selection):
        """
        处理选区变化事件

        Args:
            selection: 新的选区，相对坐标(x, y, width, height)
        """
        if self.current_video:
            # 保存当前视频的选区
            self.selection_regions[self.current_video] = selection

            # 更新选区状态显示
            if selection:
                x, y, w, h = selection
                self.selection_status.setText(f"选区状态: 已选择区域 ({x:.2f}, {y:.2f}, {w:.2f}, {h:.2f})")
                self.selection_status.setStyleSheet("""
                        font-size: 12px;
                        padding: 3px;
                        background-color: #e6f7e6;
                        color: #28a745;
                        border-top: 1px solid #ddd;
                        font-weight: bold;
                    """)
            else:
                self.selection_status.setText("选区状态: 无选区")
                self.selection_status.setStyleSheet("""
                        font-size: 12px;
                        padding: 3px;
                        background-color: #f8f8f8;
                        color: #666;
                        border-top: 1px solid #ddd;
                    """)

            print(f"已更新视频 {os.path.basename(self.current_video)} 的选区: {selection}")  # !/usr/bin/env python

