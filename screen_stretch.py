"""
屏幕拉伸对话框模块 - Screen Stretch

作者：Guoyou Sun (孙国佑) - 天体收藏家
软件：星视 GSUN View V4.0
网站：sunguoyou.lamost.org
标识：546756
原创作品，禁止商业使用
"""

import numpy as np
import json
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QSlider, QSpinBox, QGroupBox, QDialogButtonBox, QComboBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QPixmap, QImage, QColor, QCursor, QPainter, QPen, QPolygon

class ScreenStretchDialog(QDialog):
    """Screen Stretch对话框，用于调节FITS图像的显示效果"""
    stretchUpdated = pyqtSignal(float, float)  # 发送拉伸范围更新信号
    
    def __init__(self, parent=None, image_data=None):
        super().__init__(parent)
        self.parent = parent
        self.image_data = image_data
        self.setWindowTitle("Screen Stretch")
        self.resize(400, 300)
        
        # 信号节流计时器
        from PyQt5.QtCore import QTimer
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(30) # 30ms 节流
        self.update_timer.timeout.connect(self._emit_stretch_updated)
        self.pending_update = False
        
        # 加载配置文件中的默认设置
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screen_stretch_config.json")
        self.load_config()
        
        # 初始化视图范围
        self.view_range = [0, 65535]  # 初始视图范围
        
        # 拖动状态变量
        self.dragging_min = False
        self.dragging_max = False
        self.dragging_both = False
        self.drag_start_pos = None
        self.drag_min_value = None
        self.drag_max_value = None
        self.selecting_range = False
        self.current_mouse_pos = None
        
        self.setup_ui()
        
        # 如果有图像数据，更新直方图
        if self.image_data is not None:
            self.update_histogram()
    
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        
        # 直方图显示区域
        self.histogram_label = QLabel()
        self.histogram_label.setMinimumHeight(100)
        self.histogram_label.setStyleSheet("background-color: black;")
        self.histogram_label.setMouseTracking(True)  # 启用鼠标跟踪
        self.histogram_label.mousePressEvent = self.histogram_mouse_press
        self.histogram_label.mouseMoveEvent = self.histogram_mouse_move
        self.histogram_label.mouseReleaseEvent = self.histogram_mouse_release
        self.histogram_label.wheelEvent = self.histogram_wheel_event
        layout.addWidget(self.histogram_label)
        
        # 最小值和最大值滑块
        min_max_layout = QHBoxLayout()
        
        # 根据图像数据类型确定范围
        if self.image_data is not None and self.image_data.max() <= 255:
            max_range = 255
        else:
            max_range = 65535
        
        # 最小值部分
        min_layout = QVBoxLayout()
        min_label = QLabel("Minimum")
        min_layout.addWidget(min_label)
        
        min_value_layout = QHBoxLayout()
        self.min_spinbox = QSpinBox()
        self.min_spinbox.setRange(0, max_range)
        self.min_spinbox.setValue(int(self.min_value))
        self.min_spinbox.valueChanged.connect(self.on_min_value_changed)
        min_value_layout.addWidget(self.min_spinbox)
        
        min_layout.addLayout(min_value_layout)
        min_max_layout.addLayout(min_layout)
        
        # 最大值部分
        max_layout = QVBoxLayout()
        max_label = QLabel("Maximum")
        max_layout.addWidget(max_label)
        
        max_value_layout = QHBoxLayout()
        self.max_spinbox = QSpinBox()
        self.max_spinbox.setRange(0, max_range)
        self.max_spinbox.setValue(int(self.max_value))
        self.max_spinbox.valueChanged.connect(self.on_max_value_changed)
        max_value_layout.addWidget(self.max_spinbox)
        
        max_layout.addLayout(max_value_layout)
        min_max_layout.addLayout(max_layout)
        
        layout.addLayout(min_max_layout)
        
        # 更新和自动拉伸按钮
        buttons_layout = QHBoxLayout()
        
        # 添加放大和缩小按钮
        zoom_layout = QHBoxLayout()
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setToolTip("放大直方图")
        self.zoom_in_button.clicked.connect(self.zoom_in_histogram)
        zoom_layout.addWidget(self.zoom_in_button)
        
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.setToolTip("缩小直方图")
        self.zoom_out_button.clicked.connect(self.zoom_out_histogram)
        zoom_layout.addWidget(self.zoom_out_button)
        buttons_layout.addLayout(zoom_layout)
        
        # 更新按钮
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_display)
        buttons_layout.addWidget(self.update_button)
        
        # 自动拉伸按钮
        self.auto_stretch_button = QPushButton()
        self.auto_stretch_button.setIcon(self.style().standardIcon(self.style().SP_BrowserReload))
        self.auto_stretch_button.setToolTip("Auto Stretch")
        self.auto_stretch_button.clicked.connect(self.auto_stretch)
        buttons_layout.addWidget(self.auto_stretch_button)
        


        
        layout.addLayout(buttons_layout)
        
        # 中间自动拉伸设置
        auto_stretch_group = QGroupBox("Medium auto-stretch settings")
        auto_stretch_layout = QHBoxLayout()
        
        # 最小百分比
        min_percent_layout = QVBoxLayout()
        min_percent_label = QLabel("Minimum Percentile")
        min_percent_layout.addWidget(min_percent_label)
        
        self.min_percent_spinbox = QDoubleSpinBox()
        self.min_percent_spinbox.setRange(0, 100)
        self.min_percent_spinbox.setDecimals(4)  # 允许4位小数，提高精度
        self.min_percent_spinbox.setSingleStep(0.05)
        self.min_percent_spinbox.setValue(self.min_percent)
        self.min_percent_spinbox.valueChanged.connect(self.on_min_percent_changed)
        min_percent_layout.addWidget(self.min_percent_spinbox)
        
        auto_stretch_layout.addLayout(min_percent_layout)
        
        # 最大百分比
        max_percent_layout = QVBoxLayout()
        max_percent_label = QLabel("Maximum percentile")
        max_percent_layout.addWidget(max_percent_label)
        
        self.max_percent_spinbox = QDoubleSpinBox()
        self.max_percent_spinbox.setRange(0, 100)
        self.max_percent_spinbox.setDecimals(4)  # 允许4位小数，提高精度
        self.max_percent_spinbox.setSingleStep(0.05)
        self.max_percent_spinbox.setValue(self.max_percent)
        self.max_percent_spinbox.valueChanged.connect(self.on_max_percent_changed)
        max_percent_layout.addWidget(self.max_percent_spinbox)
        
        auto_stretch_layout.addLayout(max_percent_layout)
        
        auto_stretch_group.setLayout(auto_stretch_layout)
        layout.addWidget(auto_stretch_group)
        
        # 底部按钮
        bottom_buttons_layout = QHBoxLayout()
        
        # Set按钮（应用并保存为默认值）
        self.set_button = QPushButton("Set")
        self.set_button.setToolTip("应用当前设置并保存为默认值")
        self.set_button.clicked.connect(self.save_and_apply_settings)
        bottom_buttons_layout.addWidget(self.set_button)
        
        # Default按钮
        self.default_button = QPushButton("Default")
        self.default_button.clicked.connect(self.reset_to_default)
        bottom_buttons_layout.addWidget(self.default_button)
        
        layout.addLayout(bottom_buttons_layout)
        
        # 对话框按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def histogram_wheel_event(self, event):
        """处理滚轮事件实现缩放功能"""
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in_histogram()
        else:
            self.zoom_out_histogram()
            
    def _get_sampled_data(self):
        """获取采样后的图像数据，用于加速计算"""
        if self.image_data is None:
            return None
            
        # 检查缓存是否有效
        # 使用对象ID来判断数据是否改变，这比比较整个数组快得多
        current_id = id(self.image_data)
        
        if hasattr(self, 'cached_data') and self.cached_data is not None:
            if self.cached_data['id'] == current_id:
                return self.cached_data['flat_image']
        
        # 重新计算
        # ravel通常比flatten快，因为它尽可能返回视图
        flat_image = self.image_data.ravel()
        total_pixels = flat_image.size
        
        # 如果像素数超过50万，进行采样
        max_samples = 500000
        if total_pixels > max_samples:
            # 使用步长切片进行均匀采样，这比随机采样快且内存效率高
            step = total_pixels // max_samples
            # 确保步长至少为1
            step = max(1, step)
            flat_image = flat_image[::step]
            print(f"直方图采样优化: {total_pixels} -> {flat_image.size} 像素 (步长: {step})")
            
        # 更新缓存
        self.cached_data = {
            'id': current_id,
            'flat_image': flat_image
        }
        
        return flat_image

    def update_histogram(self):
        """更新直方图显示"""
        flat_image = self._get_sampled_data()
        if flat_image is None:
            return
            
        # 自动检测峰值区域 - 改进算法
        if not hasattr(self, 'initial_peak_detected') or not self.initial_peak_detected:
            # 使用更智能的峰值检测
            # 根据数据范围选择合适的bin数量
            data_min = flat_image.min()
            data_max = flat_image.max()
            data_range = data_max - data_min
            
            # 对于8位图像使用256个bins，对于16位图像使用512个bins
            if data_max <= 255:
                num_bins = 256
            else:
                num_bins = 512
            
            hist, _ = np.histogram(flat_image, num_bins)
            
            # 找到峰值
            peak_pos = np.argmax(hist)
            
            # 计算峰值位置对应的值
            if data_range > 0:
                peak_value = data_min + data_range * peak_pos / num_bins
            else:
                peak_value = data_min
            
            # 根据图像类型设置不同的视图范围
            if data_max <= 255:
                # 8位图像：使用较小的范围
                range_width = data_range * 0.5
            else:
                # 16位图像：使用较大的范围
                range_width = data_range * 0.3
            
            # 确保范围不会太小
            min_range = data_range * 0.1
            if range_width < min_range:
                range_width = min_range
            
            # 设置视图范围为峰值附近区域
            self.view_range = [
                max(data_min, peak_value - range_width/2),
                min(data_max, peak_value + range_width/2)
            ]
            
            print(f"直方图自动检测: min={data_min:.1f}, max={data_max:.1f}, peak={peak_value:.1f}, range=[{self.view_range[0]:.1f}, {self.view_range[1]:.1f}]")
            
            self.initial_peak_detected = True
            
        # 获取当前视图范围
        min_view = self.view_range[0]
        max_view = self.view_range[1]
        
        # 计算直方图 - 直接使用range参数避免创建掩码数组
        # 使用采样后的数据进行直方图计算，极大提高大图性能
        hist, bin_edges = np.histogram(flat_image, 256, range=(min_view, max_view))
        
        # 创建直方图图像
        hist_height = 100
        hist_width = self.histogram_label.width()
        if hist_width <= 0:
            hist_width = 256
        
        hist_image = QImage(hist_width, hist_height, QImage.Format_RGB32)
        hist_image.fill(QColor(0, 0, 0))
        
        # 归一化直方图
        if np.max(hist) > 0:
            hist = hist * hist_height / np.max(hist)
        
        # 绘制直方图
        painter = QPainter(hist_image)
        
        # 绘制背景网格线
        pen = QPen(QColor(50, 50, 50))
        pen.setWidth(1)
        painter.setPen(pen)
        
        # 水平网格线
        for i in range(0, hist_height, 20):
            painter.drawLine(0, i, hist_width, i)
        
        # 垂直网格线
        for i in range(0, hist_width, 32):
            painter.drawLine(i, 0, i, hist_height)
        
        # 绘制直方图柱状图 - 使用多边形填充提高性能
        pen = QPen(QColor(200, 200, 200))
        pen.setWidth(1)
        painter.setPen(pen)
        
        # 使用QPolygon绘制填充区域，比逐条画线更高效
        polygon = QPolygon()
        
        # 添加底部点
        polygon.append(QPoint(0, hist_height))
        
        bin_width = hist_width / len(hist) if len(hist) > 0 else 1
        for i in range(len(hist)):
            val = int(hist[i])
            x = int((i + 0.5) * bin_width)
            y = hist_height - val
            polygon.append(QPoint(x, y))
        
        # 添加底部点
        polygon.append(QPoint(hist_width, hist_height))
        
        # 绘制填充多边形
        painter.setBrush(QColor(100, 100, 150))
        painter.drawPolygon(polygon)
        
        # 绘制轮廓线
        painter.setBrush(Qt.NoBrush)
        painter.drawPolyline(polygon)
        
        # 计算最小值和最大值在直方图上的位置
        min_pos = self._value_to_position(self.min_value, min_view, max_view, hist_width)
        max_pos = self._value_to_position(self.max_value, min_view, max_view, hist_width)
        
        # 确保位置在直方图范围内
        min_pos = max(0, min(hist_width - 1, min_pos))
        max_pos = max(0, min(hist_width - 1, max_pos))
        
        # 绘制最小值和最大值指示线
        # 红色线对应最小值调整
        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawLine(min_pos, 0, min_pos, hist_height)
        
        # 绿色线对应最大值调整
        pen = QPen(QColor(0, 255, 0))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawLine(max_pos, 0, max_pos, hist_height)
        
        # 绘制当前值标签
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        
        # 绘制最小值标签
        painter.setPen(QColor(255, 0, 0))
        painter.drawText(min_pos + 5, 15, f"{self.min_value:.0f}")
        
        # 绘制最大值标签
        painter.setPen(QColor(0, 255, 0))
        painter.drawText(max_pos + 5, 15, f"{self.max_value:.0f}")
        
        # 如果正在框选范围，绘制半透明选择区域
        if self.selecting_range and self.drag_start_pos is not None and self.current_mouse_pos is not None:
            left = min(self.drag_start_pos, self.current_mouse_pos)
            right = max(self.drag_start_pos, self.current_mouse_pos)
            
            # 绘制半透明选择区域
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 255, 80))  # 半透明蓝色
            painter.drawRect(left, 0, right - left, hist_height)
        
        painter.end()
        
        # 显示直方图
        self.histogram_label.setPixmap(QPixmap.fromImage(hist_image))
        
    def _value_to_position(self, value, min_view, max_view, width):
        """将数值转换为直方图上的位置"""
        if max_view == min_view:
            return 0
        ratio = (value - min_view) / (max_view - min_view)
        ratio = max(0, min(1, ratio))  # 确保比例在0-1之间
        return int(ratio * width)
    
    def _position_to_value(self, pos, min_view, max_view, width):
        """将直方图上的位置转换为数值"""
        if width == 0:
            return min_view
        ratio = max(0, min(1, pos / width))  # 确保比例在0-1之间
        return min_view + ratio * (max_view - min_view)
    
    def on_min_value_changed(self, value):
        """最小值改变时的处理"""
        if value >= self.max_spinbox.value():
            # 阻止信号避免递归调用
            self.min_spinbox.blockSignals(True)
            self.min_spinbox.setValue(self.max_spinbox.value() - 1)
            self.min_spinbox.blockSignals(False)
            value = self.max_spinbox.value() - 1
        self.min_value = value
        self.update_display()  # 更新显示以反映新值
    
    def on_max_value_changed(self, value):
        """最大值改变时的处理"""
        if value <= self.min_spinbox.value():
            # 确保最小值至少比最大值小1，但不超过范围
            new_value = max(self.min_spinbox.value() + 1, 0)
            new_value = min(new_value, 65535)
            self.max_spinbox.setValue(new_value)
            value = new_value
        self.max_value = value
        self.update_display()  # 更新显示以反映新值
    
    def on_min_percent_changed(self, value):
        """最小百分比改变时的处理"""
        # 确保最小值不大于最大值，留出0.01的差值避免相等（放宽限制）
        if value >= self.max_percent_spinbox.value() - 0.01:
            value = self.max_percent_spinbox.value() - 0.01
            # 阻止信号避免递归调用
            self.min_percent_spinbox.blockSignals(True)
            self.min_percent_spinbox.setValue(value)
            self.min_percent_spinbox.blockSignals(False)
        
        # 保存值
        self.min_percent = value
        
        # 计算并更新实际像素值
        # 使用采样后的数据进行百分位数计算，提高大图性能
        flat_image = self._get_sampled_data()
        if flat_image is not None:
            self.min_value = np.percentile(flat_image, self.min_percent)
            # 阻止信号避免递归调用
            self.min_spinbox.blockSignals(True)
            self.min_spinbox.setValue(int(self.min_value))
            self.min_spinbox.blockSignals(False)
            self.update_display()
    
    def on_max_percent_changed(self, value):
        """处理最大百分比变化"""
        # 确保最大值不小于最小值，留出0.01的差值避免相等（放宽限制）
        if value <= self.min_percent_spinbox.value() + 0.01:
            value = self.min_percent_spinbox.value() + 0.01
            # 阻止信号避免递归调用
            self.max_percent_spinbox.blockSignals(True)
            self.max_percent_spinbox.setValue(value)
            self.max_percent_spinbox.blockSignals(False)
        
        # 保存值
        self.max_percent = value
        
        # 计算并更新实际像素值
        # 使用采样后的数据进行百分位数计算，提高大图性能
        flat_image = self._get_sampled_data()
        if flat_image is not None:
            self.max_value = np.percentile(flat_image, self.max_percent)
            # 阻止信号避免递归调用
            self.max_spinbox.blockSignals(True)
            self.max_spinbox.setValue(int(self.max_value))
            self.max_spinbox.blockSignals(False)
            self.update_display()
    
    def update_display(self):
        """更新显示"""
        # 节流更新
        self.pending_update = True
        if not self.update_timer.isActive():
            self.update_timer.start()
            
    def _emit_stretch_updated(self):
        """实际发射信号"""
        if self.pending_update:
            self.stretchUpdated.emit(self.min_value, self.max_value)
            self.pending_update = False
    
    def auto_stretch(self):
        """自动拉伸"""
        if self.image_data is None:
            return
        
        # 使用固定的百分比值，更精确的值可以提供更好的拉伸效果
        self.min_percent = 0.6
        self.max_percent = 99.75
        
        # 更新百分比显示，使用精确值而不是整数
        self.min_percent_spinbox.blockSignals(True)
        self.max_percent_spinbox.blockSignals(True)
        self.min_percent_spinbox.setValue(self.min_percent)
        self.max_percent_spinbox.setValue(self.max_percent)
        self.min_percent_spinbox.blockSignals(False)
        self.max_percent_spinbox.blockSignals(False)
        
        # 计算对应的实际值
        # 使用采样后的数据进行百分位数计算，提高大图性能
        flat_image = self._get_sampled_data()
        if flat_image is not None:
            self.min_value = np.percentile(flat_image, self.min_percent)
            self.max_value = np.percentile(flat_image, self.max_percent)
            
            # 更新显示，阻止信号避免递归调用
            self.min_spinbox.blockSignals(True)
            self.max_spinbox.blockSignals(True)
            self.min_spinbox.setValue(int(self.min_value))
            self.max_spinbox.setValue(int(self.max_value))
            self.min_spinbox.blockSignals(False)
            self.max_spinbox.blockSignals(False)
            self.update_display()
        
    def auto_histogram(self):
        """自动直方图功能，使用与Auto Stretch相同的百分位数算法"""
        if self.image_data is None:
            return
        
        # 使用更接近峰值的百分比值，提供更清晰的图像效果
        self.min_percent = 1.0   # 设置为1%，更接近峰值左侧
        self.max_percent = 99.0  # 设置为99%，更接近峰值右侧
        
        # 更新百分比显示
        self.min_percent_spinbox.blockSignals(True)
        self.max_percent_spinbox.blockSignals(True)
        self.min_percent_spinbox.setValue(self.min_percent)
        self.max_percent_spinbox.setValue(self.max_percent)
        self.min_percent_spinbox.blockSignals(False)
        self.max_percent_spinbox.blockSignals(False)
        
        # 计算对应的实际值
        # 使用采样后的数据进行百分位数计算，提高大图性能
        flat_image = self._get_sampled_data()
        if flat_image is not None:
            self.min_value = np.percentile(flat_image, self.min_percent)
            self.max_value = np.percentile(flat_image, self.max_percent)
            
            # 更新显示，阻止信号避免递归调用
            self.min_spinbox.blockSignals(True)
            self.max_spinbox.blockSignals(True)
            self.min_spinbox.setValue(int(self.min_value))
            self.max_spinbox.setValue(int(self.max_value))
            self.min_spinbox.blockSignals(False)
            self.max_spinbox.blockSignals(False)
            
            # 更新显示
            self.update_display()

    # batch_auto_histogram uses auto_histogram so it's implicitly updated.

    def apply_settings(self):
        """应用设置"""
        if self.image_data is None:
            return
            
        # 应用百分比设置
        # 使用采样后的数据进行百分位数计算，提高大图性能
        flat_image = self._get_sampled_data()
        if flat_image is not None:
            self.min_value = np.percentile(flat_image, self.min_percent)
            self.max_value = np.percentile(flat_image, self.max_percent)
            
            # 更新显示，阻止信号避免递归调用
            self.min_spinbox.blockSignals(True)
            self.max_spinbox.blockSignals(True)
            self.min_spinbox.setValue(int(self.min_value))
            self.max_spinbox.setValue(int(self.max_value))
            self.min_spinbox.blockSignals(False)
            self.max_spinbox.blockSignals(False)
            
            # 更新显示
            self.update_display()
            
            print(f"应用Screen Stretch设置: min_percent={self.min_percent}, max_percent={self.max_percent}")
            print(f"对应的值范围: min_value={self.min_value}, max_value={self.max_value}")
    
    def save_as_default(self):
        """保存当前设置为默认值"""
        # 获取当前设置
        config = {
            "min_percent": self.min_percent,
            "max_percent": self.max_percent
        }
        
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # 确保配置文件路径是绝对路径
            abs_config_file = os.path.abspath(self.config_file)
            print(f"正在保存配置到绝对路径: {abs_config_file}")
            
            # 保存配置文件
            with open(abs_config_file, "w") as f:
                json.dump(config, f, indent=4)
            
            # 验证配置文件是否成功保存
            if os.path.exists(abs_config_file):
                with open(abs_config_file, "r") as f:
                    saved_config = json.load(f)
                print(f"成功保存并验证配置: {saved_config}")
                
                # 显示保存成功的消息
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "保存成功", f"Screen Stretch设置已成功保存为默认值。\n最小百分比: {self.min_percent}\n最大百分比: {self.max_percent}")
            else:
                raise Exception(f"配置文件未成功创建: {abs_config_file}")
        except Exception as e:
            print(f"保存配置文件时出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 显示保存失败的消息
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "保存失败", f"保存设置时出错: {str(e)}\n路径: {self.config_file}")
    
    def load_config(self):
        """加载配置文件"""
        default_config = {
            "min_percent": 1.0,
            "max_percent": 99.5
        }
        
        try:
            # 确保使用绝对路径
            abs_config_file = os.path.abspath(self.config_file)
            print(f"尝试从绝对路径加载配置: {abs_config_file}")
            
            if os.path.exists(abs_config_file):
                with open(abs_config_file, "r") as f:
                    config = json.load(f)
                    self.min_percent = config.get("min_percent", default_config["min_percent"])
                    self.max_percent = config.get("max_percent", default_config["max_percent"])
                    
                print(f"成功加载配置: min_percent={self.min_percent}, max_percent={self.max_percent}")
            else:
                # 使用默认配置
                self.min_percent = default_config["min_percent"]
                self.max_percent = default_config["max_percent"]
                
                print(f"配置文件不存在，使用默认配置: {abs_config_file}")
                
                # 保存默认配置
                try:
                    # 确保目录存在
                    config_dir = os.path.dirname(abs_config_file)
                    if not os.path.exists(config_dir):
                        os.makedirs(config_dir)
                        
                    with open(abs_config_file, "w") as f:
                        json.dump(default_config, f, indent=4)
                    print(f"已创建默认配置文件: {abs_config_file}")
                except Exception as e:
                    print(f"创建默认配置文件失败: {e}")
        except Exception as e:
            print(f"加载配置文件时出错: {e}")
            import traceback
            traceback.print_exc()
            # 使用硬编码的默认值
            self.min_percent = default_config["min_percent"]
            self.max_percent = default_config["max_percent"]
        
        # 初始化最小/最大值（根据图像数据类型自动设置）
        if self.image_data is not None:
            data_max = self.image_data.max()
            if data_max <= 255:
                # 8位图像
                self.min_value = 0
                self.max_value = 255
            else:
                # 16位图像
                self.min_value = 19579
                self.max_value = 34724
        else:
            # 没有图像数据时使用16位默认值
            self.min_value = 19579
            self.max_value = 34724
    
    def reset_to_default(self):
        """重置为默认值"""
        # 重新加载配置文件中的默认值
        self.load_config()
        
        # 更新UI，阻止信号避免递归调用
        self.min_percent_spinbox.blockSignals(True)
        self.max_percent_spinbox.blockSignals(True)
        self.min_percent_spinbox.setValue(self.min_percent)
        self.max_percent_spinbox.setValue(self.max_percent)
        self.min_percent_spinbox.blockSignals(False)
        self.max_percent_spinbox.blockSignals(False)
        
        # 应用设置
        self.apply_settings()
    
    def histogram_mouse_press(self, event):
        """处理直方图上的鼠标按下事件"""
        if self.image_data is None:
            return
            
        # 获取鼠标位置
        x = event.x()
        hist_width = self.histogram_label.width()
        
        # 计算当前视图范围
        min_view = self.view_range[0]
        max_view = self.view_range[1]
        
        # 计算最小值和最大值在直方图上的位置
        min_pos = self._value_to_position(self.min_value, min_view, max_view, hist_width)
        max_pos = self._value_to_position(self.max_value, min_view, max_view, hist_width)
        
        # 计算鼠标到两条线的距离
        dist_to_min = abs(x - min_pos)
        dist_to_max = abs(x - max_pos)
        
        # 定义拖动敏感区域（15像素）
        drag_threshold = 15
        
        # 判断是否点击了最小值或最大值指示线附近
        if dist_to_min <= drag_threshold or dist_to_max <= drag_threshold:
            # 优先处理距离更近的线
            if dist_to_min < dist_to_max:
                self.dragging_min = True
                self.dragging_max = False
            else:
                self.dragging_min = False
                self.dragging_max = True
            
            # 设置拖动状态
            self.drag_start_pos = x
            self.drag_min_value = self.min_value
            self.drag_max_value = self.max_value
            self.setCursor(Qt.SizeHorCursor)  # 设置水平调整光标
            
            # 如果两条线靠得太近（小于30像素），自动放大该区域
            if abs(min_pos - max_pos) < 30:
                center = (self.min_value + self.max_value) / 2
                range_width = (self.max_value - self.min_value) * 5  # 放大5倍
                self.view_range = [center - range_width/2, center + range_width/2]
                self.update_histogram()
        else:
            # 如果点击了其他区域，则开始框选范围
            self.selecting_range = True
            self.drag_start_pos = x
            self.current_mouse_pos = x
            self.drag_min_value = self.min_value
            self.drag_max_value = self.max_value
            self.setCursor(Qt.CrossCursor)  # 设置十字光标
    
    def histogram_mouse_move(self, event):
        """处理直方图上的鼠标移动事件"""
        if self.image_data is None:
            return
            
        # 获取鼠标位置
        x = event.x()
        hist_width = self.histogram_label.width()
        
        # 计算当前视图范围
        min_view = self.view_range[0]
        max_view = self.view_range[1]
        
        # 将位置转换为值
        value = self._position_to_value(x, min_view, max_view, hist_width)
        
        # 计算最小值和最大值在直方图上的位置
        min_pos = self._value_to_position(self.min_value, min_view, max_view, hist_width)
        max_pos = self._value_to_position(self.max_value, min_view, max_view, hist_width)
        
        # 计算鼠标到两条线的距离
        dist_to_min = abs(x - min_pos)
        dist_to_max = abs(x - max_pos)
        
        # 定义拖动敏感区域（15像素）
        drag_threshold = 15
        
        # 更新光标形状
        if dist_to_min <= drag_threshold or dist_to_max <= drag_threshold:
            if not (self.dragging_min or self.dragging_max or self.selecting_range):
                self.setCursor(Qt.SizeHorCursor)
        elif not (self.dragging_min or self.dragging_max or self.selecting_range):
            self.setCursor(Qt.ArrowCursor)
        
        # 如果正在拖动min/max标记
        if self.dragging_min or self.dragging_max:
            # 更新相应的值
            if self.dragging_min:
                # 确保最小值不大于最大值
                if value < self.max_value:
                    self.min_value = value
                    self.min_spinbox.setValue(int(self.min_value))
            elif self.dragging_max:
                # 确保最大值不小于最小值
                if value > self.min_value:
                    self.max_value = value
                    self.max_spinbox.setValue(int(self.max_value))
            
            # 更新直方图显示
            self.update_histogram()
            
            # 实时更新显示效果
            self.update_display()
        elif self.selecting_range:
            # 处理框选范围
            self.current_mouse_pos = x
            
            # 计算新的min/max值
            start_pos = min(self.drag_start_pos, self.current_mouse_pos)
            end_pos = max(self.drag_start_pos, self.current_mouse_pos)
            
            self.min_value = self._position_to_value(start_pos, min_view, max_view, hist_width)
            self.max_value = self._position_to_value(end_pos, min_view, max_view, hist_width)
            
            # 更新spinbox值
            self.min_spinbox.setValue(int(self.min_value))
            self.max_spinbox.setValue(int(self.max_value))
            
            # 更新显示
            self.update_histogram()
            self.update_display()
        else:
            # 仅鼠标移动，不拖动时，高亮显示最近的线
            self.update_histogram()
    
    def histogram_mouse_release(self, event):
        """处理直方图上的鼠标释放事件"""
        self.dragging_min = False
        self.dragging_max = False
        self.selecting_range = False
        self.drag_start_pos = None
        self.drag_min_value = None
        self.drag_max_value = None
        self.current_mouse_pos = None
        self.setCursor(Qt.ArrowCursor)  # 恢复默认光标
        
        # 更新显示
        self.update_histogram()
        self.update_display()
    
    def zoom_in_histogram(self):
        """放大直方图"""
        if self.image_data is None:
            return
            
        # 计算当前视图范围
        current_range = self.view_range[1] - self.view_range[0]
        center = (self.view_range[0] + self.view_range[1]) / 2
        
        # 缩小视图范围，相当于放大
        new_range = current_range * 0.8
        
        # 计算新的视图范围
        new_min = center - new_range / 2
        new_max = center + new_range / 2
        
        # 确保视图范围在有效范围内
        min_possible = self.image_data.min()
        max_possible = self.image_data.max()
        
        if new_min < min_possible:
            new_min = min_possible
        if new_max > max_possible:
            new_max = max_possible
            
        # 更新视图范围
        self.view_range = [new_min, new_max]
        
        # 更新直方图显示
        self.update_histogram()
    
    def zoom_out_histogram(self):
        """缩小直方图"""
        if self.image_data is None:
            return
            
        # 计算当前视图范围
        current_range = self.view_range[1] - self.view_range[0]
        center = (self.view_range[0] + self.view_range[1]) / 2
        
        # 扩大视图范围，相当于缩小
        new_range = current_range * 1.25
        
        # 计算新的视图范围
        new_min = center - new_range / 2
        new_max = center + new_range / 2
        
        # 确保视图范围在有效范围内
        min_possible = self.image_data.min()
        max_possible = self.image_data.max()
        
        if new_min < min_possible:
            new_min = min_possible
        if new_max > max_possible:
            new_max = max_possible
            
        # 更新视图范围
        self.view_range = [new_min, new_max]
        
        # 更新直方图显示
        self.update_histogram()
        
    def save_and_apply_settings(self):
        """应用当前设置并保存为默认值"""
        # 应用当前设置
        self.apply_settings()
        
        # 保存为默认值
        self.save_as_default()
    
    def on_accept(self):
        """处理确定按钮点击事件"""
        # 在关闭对话框前保存当前设置
        self.update_display()
        # 调用标准的accept方法关闭对话框
        self.accept()
    
    def set_image_data(self, image_data):
        """设置图像数据"""
        self.image_data = image_data
        # 重置缩放状态
        if image_data is not None:
            self.view_range = [image_data.min(), image_data.max()]
        
        # 重新加载配置文件，确保使用最新的设置
        self.load_config()
        # 更新UI以显示当前配置
        self.min_percent_spinbox.setValue(int(self.min_percent))
        self.max_percent_spinbox.setValue(int(self.max_percent))
        # 更新直方图
        self.update_histogram()
        # 应用保存的配置，而不是自动拉伸
        self.apply_settings()