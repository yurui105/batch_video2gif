#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
视频处理器模块
负责视频的读取、分割和GIF转换
"""

import os
import cv2
import glob
import threading
import numpy as np
from moviepy import VideoFileClip, ImageSequenceClip
from typing import Dict, List, Tuple, Optional, Any, Union
from PyQt5.QtWidgets import QApplication


class VideoProcessor:
    """视频处理器类，用于处理视频转GIF的核心功能"""

    def __init__(self):
        """初始化视频处理器"""
        self.logger = None
        self.processing = False
        self.abort_flag = False
        self.progress_callback = None

    def set_logger(self, logger):
        """
        设置日志记录器

        Args:
            logger: 日志记录器实例
        """
        self.logger = logger

    def set_progress_callback(self, callback):
        """
        设置进度回调函数
        
        Args:
            callback: 回调函数，接收进度值(0-100)作为参数
        """
        self.progress_callback = callback

    def log(self, message: str, level: str = 'info'):
        """
        记录日志的便捷方法

        Args:
            message: 日志消息
            level: 日志级别，默认为'info'
        """
        if self.logger:
            if level == 'info':
                self.logger.info(message)
            elif level == 'warning':
                self.logger.warning(message)
            elif level == 'error':
                self.logger.error(message)

    def get_videos_from_path(self, path: str) -> List[str]:
        """
        获取指定路径下的所有视频文件

        Args:
            path: 视频文件所在的目录路径

        Returns:
            包含视频文件完整路径的列表

        Raises:
            Exception: 如果获取视频列表时发生错误
        """
        # 支持的视频文件扩展名
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        videos = []

        try:
            # 使用不区分大小写的文件模式匹配
            for ext in video_extensions:
                # 使用不区分大小写的模式，使用通配符匹配任意大小写
                pattern = os.path.join(path, f'*{ext}')
                # 使用全局扩展确保跨平台支持
                found_videos = glob.glob(pattern, recursive=False)
                videos.extend(found_videos)

                # 如果系统对大小写敏感，还需要添加大写扩展名的匹配
                if not found_videos:  # 只有当没有找到文件时，才尝试大写扩展名
                    videos.extend(glob.glob(os.path.join(path, f'*{ext.upper()}')))

            # 去重，确保每个文件只出现一次
            unique_videos = list(set(videos))

            return sorted(unique_videos)
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取视频列表时发生错误: {str(e)}")
            raise

    def process_videos(self,
                       input_path: str,
                       output_path: str,
                       start_time: float,
                       split_mode: str,
                       split_value: Union[int, float],
                       quality: int,
                       selection_regions: Dict[str, Tuple[float, float, float, float]]) -> None:
        """
        处理视频文件，启动后台线程进行处理

        Args:
            input_path: 输入视频文件所在目录
            output_path: 输出GIF文件保存目录
            start_time: 开始时间(秒)
            split_mode: 分割模式，'duration'按时长分割，'count'按数量分割
            split_value: 分割值，根据模式不同表示分割时长或分割数量
            quality: GIF质量(1-100)
            selection_regions: 视频选区，键为视频路径，值为(x, y, width, height)的相对坐标元组
        """
        # 检查是否已有处理任务在进行
        if self.processing:
            self.log("已有视频正在处理中，请等待当前处理完成", 'warning')
            return

        # 设置处理标志
        self.processing = True
        self.abort_flag = False

        try:
            # 获取视频列表
            videos = self.get_videos_from_path(input_path)

            if not videos:
                self.log("指定路径下没有找到视频文件", 'warning')
                self.processing = False
                return

            self.log(f"开始处理 {len(videos)} 个视频文件...")
            self.log(f"选区信息: {len(selection_regions)} 个视频有选区设置")

            # 创建工作线程
            thread = threading.Thread(
                target=self._process_videos_thread,
                args=(videos, output_path, start_time, split_mode, split_value, quality, selection_regions)
            )
            thread.daemon = True
            thread.start()

        except Exception as e:
            self.log(f"处理视频时发生错误: {str(e)}", 'error')
            self.processing = False
            raise

    def abort_processing(self):
        """中止当前处理任务"""
        self.abort_flag = True
        self.log("正在中止处理任务...", 'warning')

    def _process_videos_thread(self,
                               videos: List[str],
                               output_path: str,
                               start_time: float,
                               split_mode: str,
                               split_value: Union[int, float],
                               quality: int,
                               selection_regions: Dict[str, Tuple[float, float, float, float]]) -> None:
        """
        处理视频的工作线程

        Args:
            videos: 视频文件路径列表
            output_path: 输出GIF文件保存目录
            start_time: 开始时间(秒)
            split_mode: 分割模式
            split_value: 分割值
            quality: GIF质量
            selection_regions: 视频选区
        """
        try:
            total_videos = len(videos)
            
            # 初始化进度为0
            self._update_progress(0)

            for i, video_path in enumerate(videos):
                # 检查是否请求中止
                if self.abort_flag:
                    self.log("处理任务已中止", 'warning')
                    break

                try:
                    self.log(f"正在处理视频 [{i + 1}/{total_videos}]: {os.path.basename(video_path)}")
                    
                    # 计算当前视频的进度范围
                    # 每个视频占总进度的 1/total_videos
                    video_progress_start = int((i / total_videos) * 100)
                    video_progress_end = int(((i + 1) / total_videos) * 100)
                    
                    # 更新进度到当前视频的开始位置
                    self._update_progress(video_progress_start)

                    # 创建输出文件夹
                    video_name = os.path.splitext(os.path.basename(video_path))[0]
                    video_output_dir = os.path.join(output_path, video_name)
                    os.makedirs(video_output_dir, exist_ok=True)

                    # 获取视频选区
                    selection = selection_regions.get(video_path)

                    # 处理单个视频，传入进度范围
                    self.process_single_video(
                        video_path, video_output_dir, start_time,
                        split_mode, split_value, quality, selection,
                        video_progress_start, video_progress_end
                    )

                    self.log(f"视频 {os.path.basename(video_path)} 处理完成")

                    # 处理完单个视频后更新进度到当前视频的结束位置
                    self._update_progress(video_progress_end)

                except Exception as e:
                    self.log(f"处理视频 {os.path.basename(video_path)} 时发生错误: {str(e)}", 'error')

            if not self.abort_flag:
                self.log("所有视频处理完成！")
                # 完成时设置进度为100%
                self._update_progress(100)

        except Exception as e:
            self.log(f"处理过程中发生错误: {str(e)}", 'error')
        finally:
            self.processing = False

    def process_single_video(self,
                             video_path: str,
                             output_dir: str,
                             start_time: float,
                             split_mode: str,
                             split_value: Union[int, float],
                             quality: int,
                             selection: Optional[Tuple[float, float, float, float]],
                             progress_start: int,
                             progress_end: int) -> None:
        """
        处理单个视频

        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            start_time: 开始时间(秒)
            split_mode: 分割模式
            split_value: 分割值
            quality: GIF质量
            selection: 视频选区
            progress_start: 进度起始值(0-100)
            progress_end: 进度结束值(0-100)
        """
        try:
            # 打开视频
            clip = VideoFileClip(video_path)

            # 视频时长
            duration = clip.duration

            # 检查开始时间
            if start_time >= duration:
                self.log(f"开始时间 ({start_time}秒) 大于或等于视频时长 ({duration}秒)", 'warning')
                clip.close()
                return

            # 计算实际开始时间和持续时间
            actual_start = start_time
            actual_duration = duration - actual_start

            # 计算分割点
            if split_mode == 'duration':
                # 按时长分割
                split_duration = float(split_value)
                if split_duration <= 0:
                    self.log("分割时长必须大于0", 'error')
                    clip.close()
                    return

                # 计算分割点
                num_segments = max(1, int(actual_duration / split_duration))
                splits = [actual_start + i * split_duration for i in range(num_segments + 1)]

            else:
                # 按数量分割
                split_count = int(split_value)
                if split_count <= 0:
                    self.log("分割数量必须大于0", 'error')
                    clip.close()
                    return

                # 计算每段时长
                segment_duration = actual_duration / split_count

                # 计算分割点
                splits = [actual_start + i * segment_duration for i in range(split_count + 1)]

            # 处理每个分段
            total_segments = len(splits) - 1
            for i in range(total_segments):
                # 检查是否请求中止
                if self.abort_flag:
                    break

                start = splits[i]
                end = min(splits[i + 1], duration)  # 确保不超过视频时长

                # 生成GIF
                self.create_gif(
                    video_path, output_dir, i + 1,
                    start, end, quality, selection
                )

                # 更新分段进度
                # 计算当前分段在整个视频中的进度
                segment_progress = int((i + 1) / total_segments * (progress_end - progress_start))
                # 加上视频的起始进度
                current_progress = progress_start + segment_progress
                self._update_progress(current_progress)

            # 关闭视频
            clip.close()

        except Exception as e:
            self.log(f"处理视频时发生错误: {str(e)}", 'error')
            raise

    def create_gif(self,
                   video_path: str,
                   output_dir: str,
                   segment_index: int,
                   start_time: float,
                   end_time: float,
                   quality: int,
                   selection: Optional[Tuple[float, float, float, float]]) -> None:
        """
        创建GIF

        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            segment_index: 分段索引
            start_time: 开始时间(秒)
            end_time: 结束时间(秒)
            quality: GIF质量(1-100)
            selection: 视频选区
        """
        try:
            # 输出文件名
            output_file = os.path.join(output_dir, f"{segment_index}.gif")

            self.log(f"正在生成GIF: {os.path.basename(output_file)} (时间: {start_time:.1f}s - {end_time:.1f}s)")

            # 调整质量参数，MoviePy的fps越高，质量越好
            max_fps = 30  # 最大帧率
            min_fps = 10  # 最小帧率
            fps = min_fps + (max_fps - min_fps) * (quality / 100)

            # 打开视频片段
            clip = VideoFileClip(video_path).subclipped(start_time, end_time)

            # 如果有选区，进行裁剪
            if selection and all(isinstance(x, (int, float)) for x in selection):
                self.log(f"检测到选区: {selection}")

                try:
                    # 获取视频原始尺寸
                    orig_width, orig_height = clip.size
                    self.log(f"视频尺寸: {orig_width}x{orig_height}")

                    # 计算裁剪区域
                    crop_x = max(0, int(selection[0] * orig_width))
                    crop_y = max(0, int(selection[1] * orig_height))
                    crop_width = min(int(selection[2] * orig_width), orig_width - crop_x)
                    crop_height = min(int(selection[3] * orig_height), orig_height - crop_y)

                    # 确保裁剪区域有效
                    if crop_width <= 0 or crop_height <= 0:
                        self.log(f"无效的裁剪区域: ({crop_x}, {crop_y}, {crop_width}, {crop_height})", 'warning')
                        self.log(f"将使用原始视频尺寸")
                    else:
                        self.log(f"裁剪区域: ({crop_x}, {crop_y}, {crop_width}, {crop_height})")

                        # 手动处理帧并裁剪
                        frames = []
                        total_frames = int(clip.duration * clip.fps)
                        self.log(f"处理 {total_frames} 帧...")

                        # 每10%进度报告一次
                        report_interval = max(1, total_frames // 10)

                        for i, t in enumerate(np.arange(0, clip.duration, 1.0 / clip.fps)):
                            # 获取原始帧
                            frame = clip.get_frame(t)

                            # 裁剪帧
                            cropped_frame = frame[crop_y:crop_y + crop_height, crop_x:crop_x + crop_width]

                            # 添加到帧列表
                            frames.append(cropped_frame)

                            # 报告进度
                            if i % report_interval == 0 or i == total_frames - 1:
                                progress = (i + 1) / total_frames * 100
                                self.log(f"裁剪进度: {progress:.1f}% ({i + 1}/{total_frames})")

                        # 用裁剪后的帧创建新的clip
                        self.log(f"创建新的裁剪后视频剪辑...")
                        clip = ImageSequenceClip(frames, fps=clip.fps)
                        self.log(f"裁剪后视频尺寸: {clip.size}")

                except Exception as e:
                    self.log(f"裁剪过程中发生错误: {str(e)}", 'error')
                    self.log("将使用原始视频")

            # 生成GIF
            self.log(f"正在写入GIF文件: {output_file}")
            clip.write_gif(
                output_file,
                fps=fps
            )

            # 关闭视频
            clip.close()

            self.log(f"GIF生成成功: {os.path.basename(output_file)}")

        except Exception as e:
            self.log(f"生成GIF时发生错误: {str(e)}", 'error')
            raise

    def _update_progress(self, value):
        """
        更新进度
        
        Args:
            value: 进度值(0-100)
        """
        if self.progress_callback:
            try:
                # 确保值在有效范围内
                value = max(0, min(100, value))
                # 直接调用回调函数
                self.progress_callback(value)
                # 确保UI更新
                QApplication.processEvents()
            except Exception as e:
                if self.logger:
                    self.logger.error(f"更新进度时发生错误: {str(e)}")