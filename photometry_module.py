# -*- coding: utf-8 -*-
"""
测光模块 - Photometry Module

用于天文图像的测光分析，包括：
- 参考星和目标星选择
- 交叉测光（差分测光）
- 光变曲线可视化

作者：Guoyou Sun (孙国佑) - 天体收藏家
软件：星视 GSUN View V4.0
网站：sunguoyou.lamost.org
标识：546756
原创作品，禁止商业使用
"""

import sys
import os

def check_photometry_copyright():
    """检查测光模块的版权信息"""
    try:
        current_file = os.path.abspath(__file__)
        with open(current_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_copyright_counts = {
            "Guoyou Sun": 5,
            "孙国佑": 5,
            "sunguoyou.lamost.org": 5,
            "天体收藏家": 3,
            "星视 GSUN View": 5
        }
        
        for check_str, min_count in required_copyright_counts.items():
            count = content.count(check_str)
            if count < min_count:
                print("错误：测光模块版权保护机制被触发！")
                print(f"检测到关键版权信息被删除：{check_str}")
                print("本软件受版权保护，未经授权不得修改。")
                print("请联系作者获取授权：http://sunguoyou.lamost.org/")
                sys.exit(1)
        
        return True
    except Exception as e:
        print(f"版权验证失败：{str(e)}")
        print("本软件受版权保护，无法运行。")
        sys.exit(1)

check_photometry_copyright()

import numpy as np
import csv
from datetime import datetime
from astropy.time import Time

def parse_fits_time(date_str):
    """
    解析FITS文件中的时间字符串，兼容Python 3.10和3.12
    
    Args:
        date_str: FITS时间字符串
        
    Returns:
        datetime对象或None
    """
    try:
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        if not date_str:
            return None
            
        date_str = date_str.replace('Z', '+00:00')
        date_str = date_str.replace('T', ' ')
        
        try:
            dt = datetime.fromisoformat(date_str)
            return dt
        except:
            try:
                t = Time(date_str)
                return t.datetime
            except:
                return None
    except Exception as e:
        print(f"解析时间字符串失败: {date_str}, 错误: {e}")
        return None
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QSplitter, QFrame, QGroupBox, QDoubleSpinBox, QCheckBox,
    QTabWidget, QScrollArea, QMessageBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QApplication,
    QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPointF, QRectF, QEvent
from PyQt5.QtGui import QColor, QPen, QBrush, QPainter, QFont, QPixmap, QImage
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsItem, QMenu, QGraphicsTextItem, QFileDialog
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from scipy import ndimage
from scipy.optimize import curve_fit
from astropy.stats import sigma_clipped_stats
from photutils.aperture import CircularAperture, CircularAnnulus, aperture_photometry
from astropy.io import fits
import warnings
warnings.filterwarnings('ignore')
from catalog_query import CatalogQuery


class FullscreenWindow(QMainWindow):
    """全屏窗口类 - 支持ESC键关闭
    
    作者：Guoyou Sun (孙国佑) - 天体收藏家
    软件：星视 GSUN View V4.0
    网站：sunguoyou.lamost.org
    标识：546756
    原创作品，禁止商业使用
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.close_callback = None  # 关闭回调函数
    
    def set_close_callback(self, callback):
        """设置关闭回调函数"""
        self.close_callback = callback
    
    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key_Escape:
            # ESC键：关闭窗口
            if self.close_callback:
                self.close_callback()
            self.close()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.close_callback:
            self.close_callback()
        super().closeEvent(event)


class LightCurveWindow(QMainWindow):
    """独立的光变曲线显示窗口 - 非模态
    
    作者：Guoyou Sun (孙国佑) - 天体收藏家
    软件：星视 GSUN View V4.0
    网站：sunguoyou.lamost.org
    标识：546756
    原创作品，禁止商业使用
    """
    
    def __init__(self, parent=None, photometry_window=None):
        super().__init__(parent)
        self.photometry_window = photometry_window
        self.setWindowTitle("光变曲线")
        self.resize(900, 700)
        self.setWindowFlags(Qt.Window)  # 非模态窗口
        
        # 创建中央部件
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        # 创建matplotlib图形
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # 设置图形布局
        self.figure.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        
        # 添加导航工具栏
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        self.setCentralWidget(central_widget)
        
        # 全屏窗口
        self.fullscreen_window = None
        
        # 添加全屏按钮
        self.fullscreen_btn = QPushButton("全屏显示")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.toolbar.addWidget(self.fullscreen_btn)
        
        # 连接点击事件
        self.canvas.mpl_connect('button_press_event', self.on_click)
    
    def update_light_curve(self, times, magnitudes):
        """更新光变曲线"""
        self.ax.clear()
        
        if times and magnitudes:
            # 转换为相对时间
            if len(times) > 0:
                base_time = times[0]
                relative_times = [t - base_time for t in times]
            else:
                relative_times = times
            
            self.ax.plot(relative_times, magnitudes, 'o-', color='blue', markersize=4, linewidth=1)
            self.ax.set_title("光变曲线", fontname='SimHei', fontsize=14)
            self.ax.set_xlabel("时间 (天)", fontname='SimHei', fontsize=12)
            self.ax.set_ylabel("相对星等", fontname='SimHei', fontsize=12)
            self.ax.grid(True, alpha=0.3)
            
            # 设置Y轴方向（星等越小越亮）
            self.ax.invert_yaxis()
            
            # 添加统计信息
            if len(magnitudes) >= 1:
                mag_range = np.max(magnitudes) - np.min(magnitudes)
                mag_std = np.std(magnitudes)
                
                base_julian = times[0] if len(times) > 0 else 0
                base_text = f"+{base_julian:.0f}"
                
                info_text = f"{base_text}\n变幅: {mag_range:.3f} mag\n标准差: {mag_std:.3f} mag"
                
                # 移到右下角
                self.ax.text(0.98, 0.02, info_text, 
                           transform=self.ax.transAxes, 
                           verticalalignment='bottom',
                           horizontalalignment='right',
                           fontname='SimHei',
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        self.canvas.draw()
    
    def on_click(self, event):
        """点击事件处理 - 跳转到对应图像"""
        try:
            clicked_ax = event.inaxes
            
            if clicked_ax is None:
                return
            
            x_data = event.xdata
            
            if not self.photometry_window or not hasattr(self.photometry_window, 'photometry_results'):
                return
            
            times = self.photometry_window.photometry_results.get('times', [])
            if not times:
                return
            
            # 转换为相对时间
            if len(times) > 0:
                base_time = times[0]
                relative_times = [t - base_time for t in times]
            else:
                relative_times = times
            
            # 找到最近的索引
            closest_idx = None
            min_distance = float('inf')
            
            for i, time_val in enumerate(relative_times):
                distance = abs(time_val - x_data)
                if distance < min_distance:
                    min_distance = distance
                    closest_idx = i
            
            if closest_idx is not None and self.photometry_window:
                # 定位到对应的图像
                self.photometry_window.current_image_index = closest_idx
                self.photometry_window.image_list.setCurrentRow(closest_idx)
                self.photometry_window.show_current_image_in_module()
                self.photometry_window.update_markers()
                print(f"光变曲线点击：定位到图像{closest_idx+1}")
        except Exception as e:
            print(f"光变曲线点击事件处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_fullscreen(self):
        """切换全屏显示"""
        if self.fullscreen_window is None:
            # 创建全屏窗口
            self.fullscreen_window = FullscreenWindow()
            self.fullscreen_window.setWindowTitle("光变曲线 - 全屏")
            self.fullscreen_window.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint)
            
            # 设置关闭回调
            self.fullscreen_window.set_close_callback(self.on_fullscreen_closed)
            
            # 创建中央部件
            central_widget = QWidget()
            layout = QVBoxLayout(central_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            # 创建新的matplotlib图形
            fullscreen_figure = Figure()
            fullscreen_canvas = FigureCanvas(fullscreen_figure)
            fullscreen_ax = fullscreen_figure.add_subplot(111)
            
            # 设置图形布局
            fullscreen_figure.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
            fullscreen_figure.tight_layout(pad=0)
            
            # 设置canvas的sizePolicy
            fullscreen_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
            # 复制数据
            if self.photometry_window and hasattr(self.photometry_window, 'photometry_results'):
                times = self.photometry_window.photometry_results.get('times', [])
                magnitudes = self.photometry_window.photometry_results.get('relative_magnitudes', [])
                
                if times and magnitudes:
                    # 转换为相对时间
                    if len(times) > 0:
                        base_time = times[0]
                        relative_times = [t - base_time for t in times]
                    else:
                        relative_times = times
                    
                    fullscreen_ax.plot(relative_times, magnitudes, 'o-', color='blue', markersize=4, linewidth=1)
                    fullscreen_ax.set_title("光变曲线", fontname='SimHei', fontsize=16)
                    fullscreen_ax.set_xlabel("时间 (天)", fontname='SimHei', fontsize=14)
                    fullscreen_ax.set_ylabel("相对星等", fontname='SimHei', fontsize=14)
                    fullscreen_ax.grid(True, alpha=0.3)
                    fullscreen_ax.invert_yaxis()
                    
                    if len(magnitudes) >= 1:
                        mag_range = np.max(magnitudes) - np.min(magnitudes)
                        mag_std = np.std(magnitudes)
                        base_julian = times[0] if len(times) > 0 else 0
                        base_text = f"+{base_julian:.0f}"
                        info_text = f"{base_text}\n变幅: {mag_range:.3f} mag\n标准差: {mag_std:.3f} mag"
                        # 移到右下角
                        fullscreen_ax.text(0.98, 0.02, info_text, 
                                       transform=fullscreen_ax.transAxes, 
                                       verticalalignment='bottom',
                                       horizontalalignment='right',
                                       fontname='SimHei',
                                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # 添加导航工具栏
            fullscreen_toolbar = NavigationToolbar(fullscreen_canvas, self.fullscreen_window)
            layout.addWidget(fullscreen_toolbar)
            layout.addWidget(fullscreen_canvas)
            
            # 添加点击事件
            def fullscreen_on_click(event):
                if event.inaxes is None:
                    return
                self.on_click(event)
            
            fullscreen_canvas.mpl_connect('button_press_event', fullscreen_on_click)
            
            self.fullscreen_window.setCentralWidget(central_widget)
            self.fullscreen_window.show()
            self.fullscreen_window.showMaximized()
        else:
            self.fullscreen_window.close()
            self.fullscreen_window = None
    
    def on_fullscreen_closed(self):
        """全屏窗口关闭回调"""
        self.fullscreen_window = None
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.fullscreen_window:
            self.fullscreen_window.close()
        
        # 通知父窗口光变曲线窗口已关闭
        if self.photometry_window:
            self.photometry_window.light_curve_window = None
            print("光变曲线窗口已关闭，通知父窗口")
        
        super().closeEvent(event)


class DraggableStarMarker(QGraphicsItem):
    """可拖动的星标记
    
    作者：Guoyou Sun (孙国佑) - 天体收藏家
    软件：星视 GSUN View V4.0
    网站：sunguoyou.lamost.org
    标识：546756
    原创作品，禁止商业使用
    """
    
    def __init__(self, x, y, radius, color, star_type, index=0, parent=None):
        super().__init__(parent)
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.star_type = star_type  # 'reference' 或 'target'
        self.index = index  # 参考星编号
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        
        # 设置边界框
        self.setPos(x - radius, y - radius)
        
    def boundingRect(self):
        return QRectF(0, 0, self.radius * 2, self.radius * 2)
    
    def paint(self, painter, option, widget):
        # 只绘制中心点，不绘制额外的圈（因为已经有孔径、内径、外径三个圈）
        # 绘制一个小的实心圆点作为中心标记
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self.color))
        painter.drawEllipse(self.radius, self.radius, 2, 2)  # 绘制2x2像素的实心点
        
        # 绘制编号或字母
        painter.setPen(QPen(Qt.white))
        painter.setFont(QFont("Arial", 8, QFont.Bold))
        if self.star_type == 'reference':
            painter.drawText(QRectF(0, 0, self.radius * 2, self.radius * 2), 
                           Qt.AlignCenter, str(self.index + 1))
        else:
            painter.drawText(QRectF(0, 0, self.radius * 2, self.radius * 2), 
                           Qt.AlignCenter, "T")
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # 限制移动范围在场景内
            new_pos = value
            scene_rect = self.scene().sceneRect()
            if scene_rect.isValid():
                new_pos.setX(max(scene_rect.left(), min(new_pos.x(), scene_rect.right() - self.radius * 2)))
                new_pos.setY(max(scene_rect.top(), min(new_pos.y(), scene_rect.bottom() - self.radius * 2)))
            
            # 更新位置坐标
            self.x = new_pos.x() + self.radius
            self.y = new_pos.y() + self.radius
            
            return new_pos
        
        elif change == QGraphicsItem.ItemPositionHasChanged:
            # 位置改变后更新测光模块中的坐标
            scene = self.scene()
            if scene and scene.views():
                view = scene.views()[0]
                if hasattr(view, 'photometry_module'):
                    photometry_module = view.photometry_module
                    if self.star_type == 'reference' and self.index < len(photometry_module.reference_star_list):
                        old_pos = photometry_module.reference_star_list[self.index]
                        photometry_module.reference_star_list[self.index] = (self.x, self.y)
                        print(f"参考星{self.index+1}位置更新: {old_pos} -> ({self.x:.1f}, {self.y:.1f})")
                    elif self.star_type == 'target':
                        old_pos = photometry_module.target_star
                        photometry_module.target_star = (self.x, self.y)
                        print(f"目标星位置更新: {old_pos} -> ({self.x:.1f}, {self.y:.1f})")
                    
                    # 立即更新标记显示
                    photometry_module.update_markers()
                    
                    # 如果已经有测光结果，重新计算测光
                    if hasattr(photometry_module, 'photometry_results') and photometry_module.photometry_results:
                        print("标记位置已改变，重新计算测光...")
                        # 获取参考星真实星等
                        reference_magnitude = None
                        if len(photometry_module.reference_star_list) == 1:
                            reference_magnitude = 0.0
                        elif len(photometry_module.reference_star_list) > 1:
                            if photometry_module.ucac4_checkbox.isChecked():
                                reference_magnitude = photometry_module.photometry_results.get('reference_magnitude', None)
                        
                        # 重新计算测光
                        if reference_magnitude is not None or len(photometry_module.reference_star_list) == 1:
                            photometry_module.perform_photometry_calculation(reference_magnitude)
                            photometry_module.update_light_curve()
                            print("测光重新计算完成")
        
        return super().itemChange(change, value)
    
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        print(f"右键菜单事件触发: star_type={self.star_type}, index={self.index}")
        menu = QMenu()
        
        if self.star_type == 'reference':
            remove_action = menu.addAction("删除参考星")
            remove_action.triggered.connect(self.remove_reference_star)
        else:
            remove_action = menu.addAction("删除目标星")
            remove_action.triggered.connect(self.remove_target_star)
        
        print(f"右键菜单已创建，准备显示...")
        menu.exec_(event.screenPos())
        print(f"右键菜单已关闭")
    
    def remove_reference_star(self):
        """删除参考星"""
        scene = self.scene()
        if scene and scene.views():
            view = scene.views()[0]
            if hasattr(view, 'photometry_module'):
                photometry_module = view.photometry_module
                if self.index < len(photometry_module.reference_star_list):
                    print(f"删除参考星: 索引={self.index}, 坐标={photometry_module.reference_star_list[self.index]}")
                    photometry_module.reference_star_list.pop(self.index)
                    photometry_module.update_markers()
                    print(f"删除后剩余参考星数量: {len(photometry_module.reference_star_list)}")
                else:
                    print(f"删除参考星失败: 索引={self.index}超出范围，列表长度={len(photometry_module.reference_star_list)}")
    
    def remove_target_star(self):
        """删除目标星"""
        scene = self.scene()
        if scene and scene.views():
            view = scene.views()[0]
            if hasattr(view, 'photometry_module'):
                photometry_module = view.photometry_module
                print(f"删除目标星: 坐标={photometry_module.target_star}")
                photometry_module.target_star = None
                photometry_module.update_markers()
                print("目标星已删除")


class ImageListWidget(QListWidget):
    """自定义图像列表控件 - 支持键盘上下切换图片
    
    作者：Guoyou Sun (孙国佑) - 天体收藏家
    软件：星视 GSUN View V4.0
    网站：sunguoyou.lamost.org
    标识：546756
    原创作品，禁止商业使用
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.photometry_module = None  # 测光模块引用
    
    def set_photometry_module(self, module):
        """设置测光模块引用"""
        self.photometry_module = module
    
    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key_Up or event.key() == Qt.Key_Down:
            # 上下键：切换图片
            current_row = self.currentRow()
            if event.key() == Qt.Key_Up:
                # 上键
                if current_row > 0:
                    new_row = current_row - 1
                    self.setCurrentRow(new_row)
                    if self.photometry_module:
                        self.photometry_module.on_image_selected(self.item(new_row))
            elif event.key() == Qt.Key_Down:
                # 下键
                if current_row < self.count() - 1:
                    new_row = current_row + 1
                    self.setCurrentRow(new_row)
                    if self.photometry_module:
                        self.photometry_module.on_image_selected(self.item(new_row))
        else:
            # 其他按键：默认处理
            super().keyPressEvent(event)


class ImageDisplayView(QGraphicsView):
    """图像显示视图 - 用于显示图像并处理双击事件"""
    
    double_clicked = pyqtSignal(QPointF)  # 双击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene())
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)  # 使用拖拽模式，允许鼠标拖动图片
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setCursor(Qt.OpenHandCursor)  # 设置鼠标样式为打开的手形
        
        # 启用缩放功能
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # 存储当前的缩放和位置状态
        self.current_scale = 1.0
        self.current_center = QPointF(0, 0)
        
        # 存储photometry_module引用
        self.photometry_module = None
        
    def wheelEvent(self, event):
        """鼠标滚轮缩放事件"""
        zoom_factor = 1.15
        if event.angleDelta().y() < 0:
            zoom_factor = 1.0 / zoom_factor
        
        self.scale(zoom_factor, zoom_factor)
        self.current_scale *= zoom_factor
        
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.double_clicked.emit(scene_pos)
        super().mouseDoubleClickEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)  # 按下时变成闭合的手形
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.OpenHandCursor)  # 释放时变回打开的手形
        super().mouseReleaseEvent(event)
    
    def save_view_state(self):
        """保存当前视图状态（缩放和位置）"""
        self.current_scale = self.transform().m11()  # 获取当前缩放比例
        self.current_center = self.mapToScene(self.viewport().rect().center())
    
    def restore_view_state(self):
        """恢复保存的视图状态"""
        if self.current_scale > 0:
            # 重置变换矩阵
            self.resetTransform()
            # 应用保存的缩放
            self.scale(self.current_scale, self.current_scale)
            # 居中显示
            if self.scene() and self.scene().items():
                self.centerOn(self.current_center)
    
    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key_F2:
            # F2键：播放/暂停动画
            if self.photometry_module:
                if self.photometry_module.is_animating:
                    self.photometry_module.stop_animation()
                else:
                    self.photometry_module.start_animation()
        else:
            super().keyPressEvent(event)


class PhotometryWindow(QMainWindow):
    """测光模块主窗口 - 非模态窗口
    
    作者：Guoyou Sun (孙国佑) - 天体收藏家
    软件：星视 GSUN View V4.0
    网站：sunguoyou.lamost.org
    标识：546756
    原创作品，禁止商业使用
    """
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle("批量测光 - 作者：Guoyou Sun (孙国佑)")
        
        # 获取屏幕尺寸
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        # 计算窗口尺寸（确保不超过屏幕）
        # 左侧图像显示：750像素
        # 右侧功能区域：650像素（图像列表350，选星信息150，功能操作150）
        # 总宽度：1400像素
        window_width = min(1400, screen_width - 50)  # 留50像素边距
        window_height = min(1000, screen_height - 50)  # 留50像素边距
        
        self.resize(window_width, window_height)
        print(f"批量测光窗口尺寸: {window_width}x{window_height}, 屏幕尺寸: {screen_width}x{screen_height}")
        
        self.images = []  # 存储图像数据
        self.current_image_index = -1
        self.reference_star = None  # 参考星位置 (x, y)
        self.target_star = None  # 目标星位置 (x, y)
        self.reference_stars = []  # 所有图像的参考星位置
        self.target_stars = []  # 所有图像的目标星位置
        self.reference_star_list = []  # 当前图像的参考星列表（支持多颗）
        self.target_star_list = []  # 当前图像的目标星列表
        self.selection_mode = None  # 'reference' or 'target' or None
        self.photometry_results = []  # 测光结果
        self.light_curve_data = None  # 光变曲线数据
        self.catalog_query = CatalogQuery()  # 星表查询器
        self.reference_star_magnitude = None  # 参考星的绝对星等
        self.is_photometry_active = False  # 测光模式是否激活
        self.moving_target_mode = False  # 移动天体模式
        self.moving_target_positions = []  # 移动天体的位置列表 [(frame_index, x, y, julian_time), ...]
        self.moving_target_path = []  # 移动天体的路径点列表（所有帧的预测位置）
        self.moving_target_selected_frame = None  # 当前选中的帧（标记锁死在这一帧）
        self.image_pixmaps = []  # 缓存的图像pixmap列表（用于快速切换）
        
        # 动画相关
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animation_next_frame)
        self.is_animating = False
        
        # 独立的光变曲线窗口
        self.light_curve_window = None  # LightCurveWindow实例
        
        # 测光参数保存
        self.saved_params = {
            'aperture_radius': 10.0,
            'inner_radius': 15.0,
            'outer_radius': 20.0,
            'use_ucac4': False
        }
        
        self.init_ui()
        self.setup_connections()
        self.load_photometry_params_from_json()
        
    def init_ui(self):
        """初始化UI界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局：水平分割器
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建水平分割器：左侧图片显示，右侧功能区域
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(1)
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e0e0e0;
            }
        """)
        
        # 左侧：图片显示区域（750像素宽）
        image_panel = self.create_image_panel()
        main_splitter.addWidget(image_panel)
        
        # 右侧：功能区域（垂直分割）
        function_splitter = QSplitter(Qt.Vertical)
        
        # 上部分：图像列表
        image_list_panel = self.create_image_list_panel()
        function_splitter.addWidget(image_list_panel)
        
        # 中部分：选星信息
        star_info_panel = self.create_star_info_panel()
        function_splitter.addWidget(star_info_panel)
        
        # 下部分：功能操作区
        operation_panel = self.create_operation_panel()
        function_splitter.addWidget(operation_panel)
        
        # 设置功能区域分割比例（图像列表350，选星信息150，功能操作150，总共650）
        function_splitter.setSizes([350, 150, 150])
        
        main_splitter.addWidget(function_splitter)
        
        # 设置主分割比例（图片区域750像素，功能区域650像素）
        main_splitter.setSizes([750, 650])
        
        main_layout.addWidget(main_splitter)
        
        # 设置窗口最小尺寸，确保在小分辨率屏幕中自适应
        self.setMinimumSize(800, 600)
        
        # 存储分割器引用以便在resize时调整
        self.main_splitter = main_splitter
        
    def resizeEvent(self, event):
        """窗口大小改变事件 - 确保在小分辨率屏幕中自适应"""
        super().resizeEvent(event)
        
        # 获取屏幕尺寸
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        
        # 如果窗口宽度超过屏幕宽度，调整分割器大小
        window_width = self.width()
        if window_width > screen_width:
            # 计算可用的总宽度（减去边距）
            available_width = screen_width - 50
            
            # 调整主分割器：图像显示区域占53.6%（750/1400），功能区域占46.4%（650/1400）
            image_width = int(available_width * 0.536)
            function_width = available_width - image_width
            
            # 应用新的尺寸
            if hasattr(self, 'main_splitter'):
                self.main_splitter.setSizes([image_width, function_width])
            
            print(f"窗口大小调整：屏幕宽度={screen_width}, 窗口宽度={window_width}")
            print(f"图像显示={image_width}, 功能区域={function_width}")
    
    def changeEvent(self, event):
        """窗口状态改变事件 - 处理最小化到系统托盘"""
        super().changeEvent(event)
        
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                print("测光窗口已最小化到系统托盘")
                # 窗口最小化时，分割器会自动调整，不需要额外处理
            elif self.windowState() == Qt.WindowNoState:
                print("测光窗口已从系统托盘恢复")
                # 窗口恢复时，重新调整分割器大小
                self.adjust_splitter_sizes()
    
    def adjust_splitter_sizes(self):
        """调整分割器大小以适应窗口"""
        try:
            # 获取窗口尺寸
            window_width = self.width()
            window_height = self.height()
            
            # 调整主分割器：图像显示区域占34.9%（750/2150），功能区域占65.1%（1400/2150）
            image_width = int(window_width * 0.349)
            function_width = window_width - image_width
            
            # 调整功能分割器：左侧功能区域占46.4%（650/1400），光变曲线占53.6%（750/1400）
            left_function_width = int(function_width * 0.464)
            light_curve_width = function_width - left_function_width
            
            # 应用新的尺寸
            if hasattr(self, 'main_splitter') and hasattr(self, 'function_splitter'):
                self.main_splitter.setSizes([image_width, function_width])
                self.function_splitter.setSizes([left_function_width, light_curve_width])
                
                print(f"窗口恢复后调整：图像显示={image_width}, 功能区域={function_width}, 光变曲线={light_curve_width}")
        except Exception as e:
            print(f"调整分割器大小失败: {e}")
    
    def create_image_panel(self):
        """创建图片显示面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)  # 减少间距
        
        # 标题
        title = QLabel("图像显示")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                padding: 8px 0;
            }
        """)
        layout.addWidget(title)
        
        # 图片信息显示（在图像框上方）
        self.image_info_label = QLabel("未选择图像")
        self.image_info_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                background-color: rgba(0, 0, 0, 0.7);
                padding: 5px 10px;
                border-radius: 3px;
                margin: 0px;
            }
        """)
        self.image_info_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.image_info_label)
        
        # 创建图像显示视图
        self.image_view = ImageDisplayView()
        self.image_view.photometry_module = self  # 设置photometry_module引用
        self.image_view.setMinimumSize(750, 750)  # 设置最小尺寸为750*750
        self.image_view.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f5f5f5;
            }
        """)
        
        # 设置photometry_module引用
        self.image_view.photometry_module = self
        
        # 连接双击信号
        self.image_view.double_clicked.connect(self.on_image_display_double_clicked)
        
        layout.addWidget(self.image_view)
        
        return panel
    
    def create_image_list_panel(self):
        """创建图像列表面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("图像列表")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                padding: 8px 0;
            }
        """)
        layout.addWidget(title)
        
        # 图片列表
        self.image_list = ImageListWidget()
        self.image_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fff;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #E3F2FD;
            }
        """)
        self.image_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.image_list.itemClicked.connect(self.on_image_selected)
        self.image_list.set_photometry_module(self)
        layout.addWidget(self.image_list)
        
        return panel
    
    def create_star_info_panel(self):
        """创建选星信息面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("选星信息")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                padding: 8px 0;
            }
        """)
        layout.addWidget(title)
        
        # 参考星信息
        reference_group = QGroupBox("参考星")
        reference_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #FF9800;
            }
        """)
        reference_layout = QVBoxLayout(reference_group)
        
        self.reference_info_label = QLabel("未选择")
        self.reference_info_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
            }
        """)
        reference_layout.addWidget(self.reference_info_label)
        
        layout.addWidget(reference_group)
        
        # 目标星信息
        target_group = QGroupBox("目标星")
        target_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #4CAF50;
            }
        """)
        target_layout = QVBoxLayout(target_group)
        
        self.target_info_label = QLabel("未选择")
        self.target_info_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
            }
        """)
        target_layout.addWidget(self.target_info_label)
        
        layout.addWidget(target_group)
        
        return panel
    
    def create_operation_panel(self):
        """创建功能操作面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("测光操作")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                padding: 8px 0;
            }
        """)
        layout.addWidget(title)
        
        # 选星控制区
        star_selection_group = QGroupBox("选星控制")
        star_selection_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        star_selection_layout = QVBoxLayout(star_selection_group)
        
        # 按钮水平布局
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # 参考星按钮
        self.reference_star_btn = QPushButton("参考星")
        self.reference_star_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #EF6C00;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        self.reference_star_btn.clicked.connect(self.on_reference_star_clicked)
        buttons_layout.addWidget(self.reference_star_btn)
        
        # 清除参考星按钮
        self.clear_reference_btn = QPushButton("清除参考星")
        self.clear_reference_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:pressed {
                background-color: #C62828;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        self.clear_reference_btn.clicked.connect(self.on_clear_reference_clicked)
        buttons_layout.addWidget(self.clear_reference_btn)
        
        # 目标星按钮
        self.target_star_btn = QPushButton("目标星")
        self.target_star_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:pressed {
                background-color: #2E7D32;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        self.target_star_btn.clicked.connect(self.on_target_star_clicked)
        buttons_layout.addWidget(self.target_star_btn)
        
        # 移动天体按钮
        self.moving_target_btn = QPushButton("移动天体")
        self.moving_target_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:pressed {
                background-color: #5E16CC;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        self.moving_target_btn.clicked.connect(self.on_moving_target_clicked)
        buttons_layout.addWidget(self.moving_target_btn)
        
        star_selection_layout.addLayout(buttons_layout)
        
        # 选择提示
        self.selection_hint = QLabel("请先选择参考星或目标星，然后在图像上双击选择位置")
        self.selection_hint.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
                padding: 8px;
                background-color: #FFF3E0;
                border-radius: 4px;
            }
        """)
        star_selection_layout.addWidget(self.selection_hint)
        
        layout.addWidget(star_selection_group)
        
        # 测光参数设置
        params_group = QGroupBox("测光参数")
        params_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        params_layout = QFrame()
        
        # 创建垂直布局容器
        params_container = QVBoxLayout()
        
        # 第一行：测光参数（水平布局）
        params_row_layout = QHBoxLayout()
        params_row_layout.setSpacing(10)
        
        # 孔径半径
        aperture_label = QLabel("孔径半径:")
        aperture_label.setStyleSheet("color: #333;")
        self.aperture_spinbox = QDoubleSpinBox()
        self.aperture_spinbox.setRange(1.0, 100.0)
        self.aperture_spinbox.setValue(10.0)
        self.aperture_spinbox.setSingleStep(1.0)
        self.aperture_spinbox.setFixedWidth(70)  # 增加10像素宽度
        self.aperture_spinbox.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        params_row_layout.addWidget(aperture_label)
        params_row_layout.addWidget(self.aperture_spinbox)
        
        # 内径
        inner_label = QLabel("内径:")
        inner_label.setStyleSheet("color: #333;")
        self.inner_spinbox = QDoubleSpinBox()
        self.inner_spinbox.setRange(1.0, 100.0)
        self.inner_spinbox.setValue(15.0)
        self.inner_spinbox.setSingleStep(1.0)
        self.inner_spinbox.setFixedWidth(70)  # 增加10像素宽度
        self.inner_spinbox.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        params_row_layout.addWidget(inner_label)
        params_row_layout.addWidget(self.inner_spinbox)
        
        # 外径
        outer_label = QLabel("外径:")
        outer_label.setStyleSheet("color: #333;")
        self.outer_spinbox = QDoubleSpinBox()
        self.outer_spinbox.setRange(1.0, 100.0)
        self.outer_spinbox.setValue(20.0)
        self.outer_spinbox.setSingleStep(1.0)
        self.outer_spinbox.setFixedWidth(70)  # 增加10像素宽度
        self.outer_spinbox.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        params_row_layout.addWidget(outer_label)
        params_row_layout.addWidget(self.outer_spinbox)
        
        params_row_layout.addStretch()
        
        # 将第一行添加到容器
        params_container.addLayout(params_row_layout)
        
        # 第二行：确认按钮和UCAC4星等选项
        params_row2_layout = QHBoxLayout()
        
        # 确认按钮
        confirm_button = QPushButton("确认")
        confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        confirm_button.clicked.connect(self.on_confirm_params)
        params_row2_layout.addWidget(confirm_button)
        
        params_row2_layout.addStretch()
        
        # UCAC4星等选项
        self.ucac4_checkbox = QCheckBox("获取UCAC4星等")
        self.ucac4_checkbox.setStyleSheet("""
            QCheckBox {
                color: #333;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #ddd;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
                border-color: #2196F3;
            }
        """)
        params_row2_layout.addWidget(self.ucac4_checkbox)
        
        # 将第二行添加到容器
        params_container.addLayout(params_row2_layout)
        
        # 设置布局到frame
        params_layout.setLayout(params_container)
        
        params_group.setLayout(params_container)
        layout.addWidget(params_group)
        
        # 测光操作按钮
        self.photometry_btn = QPushButton("执行测光")
        self.photometry_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        self.photometry_btn.clicked.connect(self.on_photometry_clicked)
        layout.addWidget(self.photometry_btn)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
                padding: 5px;
                background-color: #f5f5f5;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        return panel
    
    def setup_connections(self):
        """设置信号连接"""
        # 测光按钮连接
        if hasattr(self, 'photometry_btn'):
            self.photometry_btn.clicked.connect(self.on_photometry_clicked)
    
    def set_images(self, images):
        """设置图像列表 - 使用主软件的缓存逻辑"""
        self.images = images
        self.image_list.clear()
        
        # 清空旧的pixmap缓存
        self.image_pixmaps = []
        
        # 预加载所有图像的pixmap（与主软件相同的逻辑）
        print("开始预加载图像pixmap...")
        for i, img_info in enumerate(images):
            item = QListWidgetItem(f"{i+1}: {img_info.get('filename', 'Unknown')}")
            item.setData(Qt.UserRole, i)
            self.image_list.addItem(item)
            
            # 从主窗口获取缓存的pixmap
            pixmap = None
            
            # 方法1: 首先检查图片是否已对齐，如果已对齐则使用对齐后的数据创建pixmap
            if hasattr(self.main_window, 'images') and i < len(self.main_window.images):
                main_image_info = self.main_window.images[i]
                is_aligned = main_image_info.get('aligned', False)
                
                if is_aligned and hasattr(self.main_window, 'original_images') and i < len(self.main_window.original_images):
                    try:
                        # 使用对齐后的数据创建pixmap
                        aligned_data = self.main_window.original_images[i]
                        normalized_data = self.normalize_image_for_display(aligned_data)
                        if normalized_data is not None:
                            # 转换为0-255范围
                            display_data = (normalized_data * 255).astype(np.uint8)
                            
                            # 创建QImage
                            height, width = display_data.shape
                            qimage = QImage(display_data.data, width, height, width, QImage.Format_Grayscale8)
                            
                            # 创建QPixmap
                            pixmap = QPixmap.fromImage(qimage)
                            print(f"图像{i+1}: 使用对齐后的数据创建pixmap，形状: {aligned_data.shape}")
                    except Exception as e:
                        print(f"使用对齐数据创建pixmap失败: {e}")
            
            # 方法2: 如果图片未对齐或对齐数据不可用，使用主窗口缓存的pixmap
            if pixmap is None and 'pixmap' in img_info and img_info['pixmap'] is not None:
                pixmap = img_info['pixmap']
                print(f"图像{i+1}: 使用主窗口缓存的pixmap")
            
            # 方法3: 如果主窗口没有缓存，尝试从raw_fits_images加载
            if pixmap is None:
                if hasattr(self.main_window, 'raw_fits_images') and self.main_window.raw_fits_images:
                    if i < len(self.main_window.raw_fits_images):
                        raw_fits_data = self.main_window.raw_fits_images[i]
                        if raw_fits_data is not None:
                            try:
                                # 使用与软件相同的归一化方法
                                normalized_data = self.normalize_image_for_display(raw_fits_data)
                                if normalized_data is not None:
                                    # 转换为0-255范围
                                    display_data = (normalized_data * 255).astype(np.uint8)
                                    
                                    # 创建QImage
                                    height, width = display_data.shape
                                    qimage = QImage(display_data.data, width, height, width, QImage.Format_Grayscale8)
                                    
                                    # 创建QPixmap
                                    pixmap = QPixmap.fromImage(qimage)
                                    print(f"图像{i+1}: 从raw_fits_images创建pixmap，形状: {raw_fits_data.shape}")
                            except Exception as e:
                                print(f"创建图像{i+1}的pixmap失败: {e}")
            
            self.image_pixmaps.append(pixmap)
        
        print(f"图像pixmap预加载完成，共{len(self.image_pixmaps)}张图像")
        
        if images:
            self.image_list.setCurrentRow(0)
            self.on_image_selected(self.image_list.item(0))
    
    def on_image_selected(self, item):
        """图像选择事件"""
        index = item.data(Qt.UserRole)
        self.current_image_index = index
        
        img_info = self.images[index]
        filename = img_info.get('filename', 'Unknown')
        shape = img_info.get('shape', 'Unknown')
        
        self.image_info_label.setText(
            f"文件名: {filename} | 尺寸: {shape} | 索引: {index + 1}/{len(self.images)}"
        )
        
        # 在测光模块中显示当前图像
        self.show_current_image_in_module()
        
        # 更新标记显示
        self.update_markers()
    
    def normalize_image_for_display(self, image_data):
        """使用与软件相同的图像归一化方法"""
        if image_data is None:
            return None
        
        data = image_data
        if len(data.shape) > 2:
            data = data[0]
        
        # 使用与软件相同的归一化方法
        vmin = np.percentile(data, 1)
        vmax = np.percentile(data, 99)
        normalized = np.clip(data, vmin, vmax)
        normalized = (normalized - vmin) / (vmax - vmin)
        
        return normalized
    
    def show_current_image_in_module(self):
        """在测光模块中显示当前图像 - 使用缓存的pixmap，与主软件相同的逻辑"""
        if not hasattr(self, 'image_view') or self.current_image_index < 0:
            return
        
        if self.current_image_index >= len(self.images):
            return
        
        # 从缓存的pixmap列表中获取当前图像
        if self.current_image_index < len(self.image_pixmaps):
            pixmap = self.image_pixmaps[self.current_image_index]
            
            if pixmap is None:
                print(f"测光模块显示图片{self.current_image_index+1}: pixmap为空")
                return
            
            try:
                # 保存当前视图状态（如果是第一张图像，则不需要保存）
                if self.image_view.scene().items():
                    self.image_view.save_view_state()
                
                # 清空场景并添加图片
                scene = self.image_view.scene()
                scene.clear()
                pixmap_item = QGraphicsPixmapItem(pixmap)
                scene.addItem(pixmap_item)
                
                # 恢复视图状态或设置初始视图
                if hasattr(self.image_view, 'current_scale') and self.image_view.current_scale > 0:
                    self.image_view.restore_view_state()
                else:
                    # 如果是第一张图像，设置适合视图的显示
                    self.image_view.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))
                    self.image_view.fitInView(pixmap_item, Qt.KeepAspectRatio)
                    self.image_view.save_view_state()
                
                # 更新标记显示
                self.update_markers()
                
                print(f"测光模块显示图片{self.current_image_index+1}: 使用缓存的pixmap，尺寸: {pixmap.width()}x{pixmap.height()}")
                
            except Exception as e:
                print(f"显示图像时出错: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"测光模块显示图片{self.current_image_index+1}: 索引超出范围: {self.current_image_index} >= {len(self.image_pixmaps)}")
    
    def on_image_display_double_clicked(self, scene_pos):
        """测光模块图像双击事件"""
        if self.selection_mode is None:
            self.status_label.setText("请先选择参考星或目标星")
            return
        
        # 获取当前图像数据
        if self.current_image_index < 0 or self.current_image_index >= len(self.images):
            return
        
        img_info = self.images[self.current_image_index]
        image_data = img_info.get('data')
        
        if image_data is None:
            return
        
        # 获取点击位置
        x, y = scene_pos.x(), scene_pos.y()
        
        # 确保坐标在图像范围内
        if x < 0 or y < 0 or x >= image_data.shape[1] or y >= image_data.shape[0]:
            return
        
        # 移动目标模式处理
        if self.moving_target_mode:
            self.handle_moving_target_click(x, y)
            return
        
        # 根据选择模式设置星的位置
        if self.selection_mode == 'reference':
            # 支持选择多颗参考星
            if (x, y) not in self.reference_star_list:
                self.reference_star_list.append((x, y))
                self.status_label.setText(f"参考星已选择: ({x:.1f}, {y:.1f}) - 已选择 {len(self.reference_star_list)} 颗参考星")
                
                # 更新参考星信息显示
                ref_info = ""
                for i, (ref_x, ref_y) in enumerate(self.reference_star_list):
                    ref_info += f"参考星{i+1}: ({ref_x:.1f}, {ref_y:.1f})\n"
                self.reference_info_label.setText(ref_info.strip())
        elif self.selection_mode == 'target':
            # 目标星只能选择一颗
            self.target_star = (x, y)
            self.target_star_list = [(x, y)]  # 保持列表形式，但只包含一颗星
            self.status_label.setText(f"目标星已选择: ({x:.1f}, {y:.1f})")
            self.target_info_label.setText(f"位置: ({x:.1f}, {y:.1f})\n图像索引: {self.current_image_index + 1}")
        
        # 更新标记显示
        self.update_markers()
    
    def handle_moving_target_click(self, x, y):
        """处理移动天体模式下的点击"""
        # 获取当前图像的儒略历时间
        if self.current_image_index < 0 or self.current_image_index >= len(self.images):
            return
        
        img_info = self.images[self.current_image_index]
        
        # 从header中解析儒略历时间
        julian_time = 0
        if 'header' in img_info and img_info['header'] is not None:
            header = img_info['header']
            # 尝试从DATE-OBS获取时间
            if 'DATE-OBS' in header:
                date_str = str(header['DATE-OBS'])
                # 将时间字符串转换为datetime对象
                dt = parse_fits_time(date_str)
                if dt:
                    # 转换为儒略历时间
                    from astropy.time import Time
                    time_obj = Time(dt)
                    julian_time = time_obj.jd
                    print(f"第{self.current_image_index + 1}帧：DATE-OBS={date_str}, 儒略历时间={julian_time:.6f}")
            # 尝试从DATE获取时间
            elif 'DATE' in header:
                date_str = str(header['DATE'])
                dt = parse_fits_time(date_str)
                if dt:
                    from astropy.time import Time
                    time_obj = Time(dt)
                    julian_time = time_obj.jd
                    print(f"第{self.current_image_index + 1}帧：DATE={date_str}, 儒略历时间={julian_time:.6f}")
        
        # 如果没有时间信息，使用图像序号作为相对时间
        if julian_time == 0:
            julian_time = float(self.current_image_index)
            print(f"第{self.current_image_index + 1}帧：无时间信息，使用序号={julian_time}")
        
        # 添加当前位置到移动天体路径（包含帧索引和儒略历时间）
        self.moving_target_positions.append((self.current_image_index, x, y, julian_time))
        
        # 记录当前选中的帧
        self.moving_target_selected_frame = self.current_image_index
        
        # 更新目标星位置，确保显示圈（只在当前帧显示）
        self.target_star = (x, y)
        self.target_star_list = [(x, y)]
        self.target_info_label.setText(f"位置: ({x:.1f}, {y:.1f})\n图像索引: {self.current_image_index + 1}")
        
        # 根据已选择的位置数量来决定处理方式
        num_positions = len(self.moving_target_positions)
        
        if num_positions == 1:
            # 第一个位置：直接记录
            self.status_label.setText(f"第{self.current_image_index + 1}帧：小行星位置 ({x:.1f}, {y:.1f}) - 请选择另一帧")
            print(f"第{self.current_image_index + 1}帧：小行星位置 ({x:.1f}, {y:.1f}), 时间={julian_time:.5f}")
        else:
            # 有多个位置：计算所有帧的小行星位置
            self.calculate_moving_target_path()
            self.status_label.setText(f"第{self.current_image_index + 1}帧：小行星位置 ({x:.1f}, {y:.1f}) - 已计算所有帧位置")
            print(f"第{self.current_image_index + 1}帧：小行星位置 ({x:.1f}, {y:.1f}), 时间={julian_time:.5f} - 已计算路径")
        
        # 更新标记显示
        self.update_markers()
    
    def calculate_moving_target_path(self):
        """计算所有帧的移动天体位置（使用2点一线线性插值，类似MDL）"""
        if len(self.moving_target_positions) < 2:
            return
        
        # 按时间排序位置
        sorted_positions = sorted(self.moving_target_positions, key=lambda p: p[3])
        
        # 获取第一个和最后一个位置
        first_pos = sorted_positions[0]
        last_pos = sorted_positions[-1]
        
        first_frame, first_x, first_y, first_time = first_pos
        last_frame, last_x, last_y, last_time = last_pos
        
        # 计算时间间隔
        time_diff = last_time - first_time
        if time_diff == 0:
            print("时间间隔为0，无法计算路径")
            return
        
        # 计算速度（像素/时间）
        vx = (last_x - first_x) / time_diff
        vy = (last_y - first_y) / time_diff
        
        print(f"移动天体路径计算（2点一线线性插值）：")
        print(f"  起点：第{first_frame + 1}帧 ({first_x:.1f}, {first_y:.1f}), 时间={first_time:.5f}")
        print(f"  终点：第{last_frame + 1}帧 ({last_x:.1f}, {last_y:.1f}), 时间={last_time:.5f}")
        print(f"  时间间隔：{time_diff:.5f}天")
        print(f"  速度：vx={vx:.3f}, vy={vy:.3f} 像素/天")
        
        # 计算所有帧的位置
        self.moving_target_path = []
        for i, img_info in enumerate(self.images):
            # 从header中解析儒略历时间
            frame_time = 0
            if 'header' in img_info and img_info['header'] is not None:
                header = img_info['header']
                # 尝试从DATE-OBS获取时间
                if 'DATE-OBS' in header:
                    date_str = str(header['DATE-OBS'])
                    # 将时间字符串转换为datetime对象
                    dt = parse_fits_time(date_str)
                    if dt:
                        # 转换为儒略历时间
                        from astropy.time import Time
                        time_obj = Time(dt)
                        frame_time = time_obj.jd
                # 尝试从DATE获取时间
                elif 'DATE' in header:
                    date_str = str(header['DATE'])
                    dt = parse_fits_time(date_str)
                    if dt:
                        from astropy.time import Time
                        time_obj = Time(dt)
                        frame_time = time_obj.jd
            
            # 如果没有时间信息，使用图像序号作为相对时间
            if frame_time == 0:
                frame_time = float(i)
            
            # 计算相对于起点的时间差
            dt = frame_time - first_time
            
            # 计算预测位置
            pred_x = first_x + vx * dt
            pred_y = first_y + vy * dt
            
            self.moving_target_path.append((i, pred_x, pred_y))
            
            if i < 3 or i >= len(self.images) - 3:
                print(f"  第{i + 1}帧：预测位置 ({pred_x:.1f}, {pred_y:.1f}), 时间={frame_time:.5f}, dt={dt:.5f}")
        
        print(f"移动天体路径计算完成，共{len(self.moving_target_path)}帧")
    
    def animation_next_frame(self):
        """动画下一帧"""
        if self.current_image_index < len(self.images) - 1:
            next_index = self.current_image_index + 1
        else:
            # 循环播放
            next_index = 0
        
        # 更新当前图像索引
        self.current_image_index = next_index
        
        # 更新图像列表选择
        self.image_list.setCurrentRow(next_index)
        
        # 更新图像信息
        img_info = self.images[next_index]
        filename = img_info.get('filename', 'Unknown')
        shape = img_info.get('shape', 'Unknown')
        self.image_info_label.setText(
            f"文件名: {filename} | 尺寸: {shape} | 索引: {next_index + 1}/{len(self.images)}"
        )
        
        # 显示当前图像
        self.show_current_image_in_module()
        
        # 更新标记显示
        self.update_markers()
    
    def start_animation(self):
        """开始动画"""
        if self.is_animating:
            self.stop_animation()
            return
        
        # 获取主界面的动画间隔
        interval_ms = getattr(self.main_window, '_auto_anim_interval_ms', 500)
        
        self.animation_timer.start(interval_ms)
        self.is_animating = True
        self.status_label.setText("动画播放中...")
        print(f"动画开始，间隔：{interval_ms}ms")
    
    def stop_animation(self):
        """停止动画"""
        if self.animation_timer.isActive():
            self.animation_timer.stop()
        self.is_animating = False
        self.status_label.setText("动画已停止")
        print("动画停止")
    
    def detect_moving_target(self, x, y):
        """检测移动的小行星 - 改进的移动天体检测算法（类似MDL）"""
        if len(self.moving_target_positions) < 2:
            return None
        
        # 获取当前图像数据
        if self.current_image_index < 0 or self.current_image_index >= len(self.images):
            return None
        
        img_info = self.images[self.current_image_index]
        image_data = img_info.get('data')
        
        if image_data is None:
            return None
        
        # 计算移动速度和方向
        if len(self.moving_target_positions) >= 3:
            # 使用最后3个位置计算加速度
            pos1 = self.moving_target_positions[-3]
            pos2 = self.moving_target_positions[-2]
            pos3 = self.moving_target_positions[-1]
            
            # 计算两个速度向量
            v1 = (pos2[0] - pos1[0], pos2[1] - pos1[1])
            v2 = (pos3[0] - pos2[0], pos3[1] - pos2[1])
            
            # 计算加速度
            ax = v2[0] - v1[0]
            ay = v2[1] - v1[1]
            
            # 预测下一帧的位置（考虑加速度）
            predicted_x = pos3[0] + v2[0] + ax * 0.5
            predicted_y = pos3[1] + v2[1] + ay * 0.5
            
            print(f"移动天体预测（带加速度）：v1=({v1[0]:.1f}, {v1[1]:.1f}), v2=({v2[0]:.1f}, {v2[1]:.1f}), a=({ax:.1f}, {ay:.1f})")
        else:
            # 只有两个位置，使用简单的线性预测
            last_pos = self.moving_target_positions[-1]
            second_last_pos = self.moving_target_positions[-2]
            
            dx = last_pos[0] - second_last_pos[0]
            dy = last_pos[1] - second_last_pos[1]
            
            predicted_x = last_pos[0] + dx
            predicted_y = last_pos[1] + dy
            
            print(f"移动天体预测（线性）：dx={dx:.1f}, dy={dy:.1f}")
        
        print(f"移动天体预测：上一帧({self.moving_target_positions[-1][0]:.1f}, {self.moving_target_positions[-1][1]:.1f}), 预测({predicted_x:.1f}, {predicted_y:.1f})")
        
        # 在预测位置附近搜索最亮的目标
        search_radius = 50  # 搜索半径（像素），增加搜索范围
        detected_position = self.find_brightest_target(image_data, predicted_x, predicted_y, search_radius)
        
        if detected_position:
            print(f"移动天体检测：找到目标 ({detected_position[0]:.1f}, {detected_position[1]:.1f})")
            return detected_position
        else:
            print(f"移动天体检测：未找到目标，将使用用户点击位置")
            return None
    
    def find_brightest_target(self, image_data, center_x, center_y, radius):
        """在指定区域寻找最亮的目标 - 改进版（使用质心计算）"""
        if image_data is None:
            return None
        
        # 确保坐标在图像范围内
        height, width = image_data.shape[:2]
        
        # 计算搜索区域边界
        x_min = max(0, int(center_x - radius))
        x_max = min(width, int(center_x + radius + 1))
        y_min = max(0, int(center_y - radius))
        y_max = min(height, int(center_y + radius + 1))
        
        # 提取搜索区域
        search_region = image_data[y_min:y_max, x_min:x_max]
        
        if search_region.size == 0:
            return None
        
        # 计算背景噪声水平（使用区域的最低值）
        background_level = np.percentile(search_region, 10)
        
        # 计算阈值（背景水平 + 5倍标准差）
        threshold = background_level + 5 * np.std(search_region)
        
        # 创建掩码，只保留高于阈值的像素
        mask = search_region > threshold
        
        if not np.any(mask):
            print("未找到高于阈值的像素")
            return None
        
        # 计算质心（加权平均）
        y_coords, x_coords = np.where(mask)
        weights = search_region[mask] - background_level
        
        # 计算质心坐标
        centroid_x = np.sum(x_coords * weights) / np.sum(weights)
        centroid_y = np.sum(y_coords * weights) / np.sum(weights)
        
        # 转换为全局坐标
        brightest_x = x_min + centroid_x
        brightest_y = y_min + centroid_y
        
        # 计算该点到中心的距离
        distance = np.sqrt((brightest_x - center_x)**2 + (brightest_y - center_y)**2)
        
        # 如果距离超过搜索半径，返回None
        if distance > radius:
            print(f"质心距离中心太远：{distance:.1f} > {radius:.1f}")
            return None
        
        print(f"质心位置：({brightest_x:.1f}, {brightest_y:.1f}), 距离中心：{distance:.1f}, 背景水平：{background_level:.1f}")
        
        return (brightest_x, brightest_y)
    
    def on_reference_star_clicked(self):
        """参考星选择按钮点击"""
        self.selection_mode = 'reference'
        self.moving_target_mode = False  # 关闭移动天体模式
        # 恢复移动天体按钮样式
        self.moving_target_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:pressed {
                background-color: #5E16CC;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        self.status_label.setText("请双击图像选择参考星位置")
    
    def on_target_star_clicked(self):
        """目标星选择按钮点击"""
        self.selection_mode = 'target'
        self.moving_target_mode = False  # 关闭移动目标模式
        self.status_label.setText("请双击图像选择目标星位置")
    
    def on_moving_target_clicked(self):
        """移动目标按钮点击 - 开启移动天体测光模式"""
        self.moving_target_mode = not self.moving_target_mode
        
        if self.moving_target_mode:
            self.moving_target_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5E16CC;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
            """)
            self.status_label.setText("移动目标模式已开启，请在第一帧选择小行星位置")
            self.moving_target_positions = []
            self.moving_target_path = []
            print("移动目标模式已开启")
        else:
            self.moving_target_btn.setStyleSheet("""
                QPushButton {
                    background-color: #9C27B0;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
            """)
            self.status_label.setText("移动目标模式已关闭")
            print("移动目标模式已关闭")
    
    def on_clear_reference_clicked(self):
        """清除参考星按钮点击"""
        self.reference_star_list = []
        self.reference_info_label.setText("未选择")
        self.status_label.setText("参考星已清除")
        self.update_markers()
    
    def update_markers(self):
        """更新标记显示 - 显示三圈孔径"""
        if not hasattr(self, 'image_view'):
            return
        
        scene = self.image_view.scene()
        
        # 清除现有标记（只清除测光相关的标记，保留图像）
        items_to_remove = []
        for item in scene.items():
            # 只清除测光相关的标记，保留图像项
            if isinstance(item, (QGraphicsEllipseItem, QGraphicsTextItem)):
                items_to_remove.append(item)
            elif isinstance(item, DraggableStarMarker):
                items_to_remove.append(item)
        
        for item in items_to_remove:
            scene.removeItem(item)
        
        # 获取孔径参数
        aperture_radius = self.aperture_spinbox.value()
        inner_radius = self.inner_spinbox.value()
        outer_radius = self.outer_spinbox.value()
        
        # 添加参考星标记（黄色）- 支持多颗，显示三圈孔径
        for i, (x, y) in enumerate(self.reference_star_list):
            # 孔径（内圈）- 黄色实线，线宽1（与外圈一致）
            aperture = QGraphicsEllipseItem(x - aperture_radius, y - aperture_radius, 
                                           aperture_radius * 2, aperture_radius * 2)
            aperture.setPen(QPen(QColor(255, 193, 7), 1, Qt.SolidLine))  # 黄色实线边框
            aperture.setBrush(QBrush(Qt.NoBrush))  # 无填充
            scene.addItem(aperture)
            
            # 内径（中圈）- 黄色实线，线宽1
            inner = QGraphicsEllipseItem(x - inner_radius, y - inner_radius, 
                                        inner_radius * 2, inner_radius * 2)
            inner.setPen(QPen(QColor(255, 193, 7), 1, Qt.SolidLine))  # 黄色实线边框
            inner.setBrush(QBrush(Qt.NoBrush))
            scene.addItem(inner)
            
            # 半径（外圈）- 黄色实线，线宽1
            radius = QGraphicsEllipseItem(x - outer_radius, y - outer_radius, 
                                         outer_radius * 2, outer_radius * 2)
            radius.setPen(QPen(QColor(255, 193, 7), 1, Qt.SolidLine))  # 黄色实线边框
            radius.setBrush(QBrush(Qt.NoBrush))
            scene.addItem(radius)
            
            # 添加可拖动的中心标记（小圆点，不是圈）
            center_marker = DraggableStarMarker(x, y, 4, QColor(255, 193, 7), 'reference', i)
            center_marker.setPos(x - 4, y - 4)
            scene.addItem(center_marker)
        
        # 添加目标星标记（绿色）- 显示三圈孔径
        if self.target_star:
            # 在移动天体模式下，根据位置数量决定显示逻辑
            if self.moving_target_mode:
                num_positions = len(self.moving_target_positions)
                
                if num_positions == 1:
                    # 只有1个位置：标记只在那一帧显示
                    selected_frame = self.moving_target_positions[0][0]
                    if self.current_image_index != selected_frame:
                        # 不是选中的帧，不显示目标星标记（但继续显示参考星）
                        print(f"第{self.current_image_index + 1}帧不是选中的帧（第{selected_frame + 1}帧），不显示目标星标记")
                        # 不return，继续显示参考星标记
                    else:
                        # 是选中的帧，显示标记
                        x, y = self.target_star
                        print(f"第{self.current_image_index + 1}帧是选中的帧，显示目标星标记 ({x:.1f}, {y:.1f})")
                        
                        # 孔径（内圈）- 绿色实线，线宽1（与外圈一致）
                        aperture = QGraphicsEllipseItem(x - aperture_radius, y - aperture_radius, 
                                                       aperture_radius * 2, aperture_radius * 2)
                        aperture.setPen(QPen(QColor(0, 255, 0), 1, Qt.SolidLine))  # 绿色实线边框
                        aperture.setBrush(QBrush(Qt.NoBrush))  # 无填充
                        scene.addItem(aperture)
                        
                        # 内径（中圈）- 绿色实线，线宽1
                        inner = QGraphicsEllipseItem(x - inner_radius, y - inner_radius, 
                                                    inner_radius * 2, inner_radius * 2)
                        inner.setPen(QPen(QColor(0, 255, 0), 1, Qt.SolidLine))  # 绿色实线边框
                        inner.setBrush(QBrush(Qt.NoBrush))
                        scene.addItem(inner)
                        
                        # 半径（外圈）- 绿色实线，线宽1
                        radius = QGraphicsEllipseItem(x - outer_radius, y - outer_radius, 
                                                     outer_radius * 2, outer_radius * 2)
                        radius.setPen(QPen(QColor(0, 255, 0), 1, Qt.SolidLine))  # 绿色实线边框
                        radius.setBrush(QBrush(Qt.NoBrush))
                        scene.addItem(radius)
                        
                        # 添加可拖动的中心标记（小圆点，不是圈）
                        center_marker = DraggableStarMarker(x, y, 4, QColor(0, 255, 0), 'target', 0)
                        center_marker.setPos(x - 4, y - 4)
                        scene.addItem(center_marker)
                        
                elif num_positions >= 2:
                    # 有2个或更多位置：计算所有帧的位置，标记在所有帧显示
                    if len(self.moving_target_path) > 0:
                        # 查找当前帧的预测位置
                        target_pos = None
                        for frame_idx, pred_x, pred_y in self.moving_target_path:
                            if frame_idx == self.current_image_index:
                                target_pos = (pred_x, pred_y)
                                break
                        
                        # 如果找到当前帧的预测位置，使用它
                        if target_pos:
                            x, y = target_pos
                            print(f"使用预测位置：第{self.current_image_index + 1}帧 ({x:.1f}, {y:.1f})")
                        else:
                            # 如果没有找到预测位置，不显示目标星标记（但继续显示参考星）
                            print(f"第{self.current_image_index + 1}帧没有预测位置，不显示目标星标记")
                            # 不显示目标星标记，但继续显示参考星
                            return
                    else:
                        # 还没有计算路径，不显示目标星标记（但继续显示参考星）
                        print(f"还没有计算路径，不显示目标星标记")
                        # 不显示目标星标记，但继续显示参考星
                        return
                else:
                    # 没有位置，不显示目标星标记（但继续显示参考星）
                    print(f"没有位置，不显示目标星标记")
                    # 不显示目标星标记，但继续显示参考星
                    return
            else:
                # 非移动天体模式，使用目标星位置
                x, y = self.target_star
            
            # 孔径（内圈）- 绿色实线，线宽1（与外圈一致）
            aperture = QGraphicsEllipseItem(x - aperture_radius, y - aperture_radius, 
                                           aperture_radius * 2, aperture_radius * 2)
            aperture.setPen(QPen(QColor(0, 255, 0), 1, Qt.SolidLine))  # 绿色实线边框
            aperture.setBrush(QBrush(Qt.NoBrush))  # 无填充
            scene.addItem(aperture)
            
            # 内径（中圈）- 绿色实线，线宽1
            inner = QGraphicsEllipseItem(x - inner_radius, y - inner_radius, 
                                        inner_radius * 2, inner_radius * 2)
            inner.setPen(QPen(QColor(0, 255, 0), 1, Qt.SolidLine))  # 绿色实线边框
            inner.setBrush(QBrush(Qt.NoBrush))
            scene.addItem(inner)
            
            # 半径（外圈）- 绿色实线，线宽1
            radius = QGraphicsEllipseItem(x - outer_radius, y - outer_radius, 
                                         outer_radius * 2, outer_radius * 2)
            radius.setPen(QPen(QColor(0, 255, 0), 1, Qt.SolidLine))  # 绿色实线边框
            radius.setBrush(QBrush(Qt.NoBrush))
            scene.addItem(radius)
            
            # 添加可拖动的中心标记（小圆点，不是圈）
            center_marker = DraggableStarMarker(x, y, 4, QColor(0, 255, 0), 'target', 0)
            center_marker.setPos(x - 4, y - 4)
            scene.addItem(center_marker)
    
    def on_photometry_clicked(self):
        """执行测光"""
        if len(self.reference_star_list) == 0 or not self.target_star:
            self.status_label.setText("请先选择参考星和目标星")
            return
        
        self.status_label.setText("正在执行测光...")
        
        # 获取参考星的平均星等
        reference_magnitude = 0.0  # 默认0等
        
        # 获取参考星的星等（单颗参考星也需要UCAC4获取真实星等）
        reference_magnitude = None
        
        if len(self.reference_star_list) == 1:
            # 单颗参考星：检查是否勾选了UCAC4
            print(f"单颗参考星模式，UCAC4复选框状态: {self.ucac4_checkbox.isChecked()}")
            
            if self.ucac4_checkbox.isChecked():
                try:
                    # 从参考星的位置查询UCAC4星等
                    ref_x, ref_y = self.reference_star_list[0]
                    print(f"参考星坐标: ({ref_x}, {ref_y})")
                    
                    # 获取当前图像的WCS信息
                    if hasattr(self.main_window, 'image_processor') and self.main_window.image_processor:
                        print("image_processor存在")
                        if hasattr(self.main_window.image_processor, 'wcs') and self.main_window.image_processor.wcs:
                            print("WCS存在")
                            wcs = self.main_window.image_processor.wcs
                            if wcs:
                                print("WCS对象存在")
                                # 将像素坐标转换为天球坐标
                                from astropy.coordinates import SkyCoord
                                from astropy import units as u
                                
                                # 兼容不同版本的astropy
                                try:
                                    if hasattr(wcs, 'pixel_to_world'):
                                        # 新版本astropy
                                        sky_coord = wcs.pixel_to_world(ref_x, ref_y)
                                    elif hasattr(wcs, 'wcs') and hasattr(wcs.wcs, 'pixel_to_world'):
                                        # 旧版本astropy
                                        sky_coord = wcs.wcs.pixel_to_world(ref_x, ref_y)
                                    else:
                                        # 更旧的版本，使用all_pix2world
                                        sky_coord = wcs.all_pix2world(ref_x, ref_y, 1)
                                        if isinstance(sky_coord, tuple):
                                            sky_coord = SkyCoord(sky_coord[0][0], sky_coord[1][0], unit='deg')
                                except Exception as e:
                                    print(f"WCS坐标转换失败: {e}")
                                    raise
                                
                                ra = sky_coord.ra.deg
                                dec = sky_coord.dec.deg
                                
                                # 查询UCAC4星表
                                print(f"查询UCAC4星表，坐标: RA={ra:.6f}, Dec={dec:.6f}")
                                catalog_result = self.catalog_query.query_ucac4(ra, dec, search_radius=0.5)
                                
                                if catalog_result and 'magnitude' in catalog_result:
                                    reference_magnitude = catalog_result['magnitude']
                                    print(f"UCAC4查询成功，参考星星等: {reference_magnitude:.3f}")
                                else:
                                    print("UCAC4查询失败，将使用默认0等星")
                                    reference_magnitude = 0.0
                        else:
                            print("WCS对象不存在，无法查询UCAC4")
                            reference_magnitude = 0.0
                    else:
                        print("image_processor不存在，无法查询UCAC4")
                        reference_magnitude = 0.0
                except Exception as e:
                    print(f"单颗参考星UCAC4查询失败: {e}")
                    reference_magnitude = 0.0
            else:
                # 未勾选UCAC4，默认为0等星
                reference_magnitude = 0.0
                print("单颗参考星：默认参考星等为0等")
        elif len(self.reference_star_list) > 1:
            # 多颗参考星：必须从UCAC4获取真实星等
            print(f"多颗参考星模式，共{len(self.reference_star_list)}颗参考星")
            print(f"UCAC4复选框状态: {self.ucac4_checkbox.isChecked()}")
            
            if self.ucac4_checkbox.isChecked():
                try:
                    # 从第一颗参考星的位置查询UCAC4星等
                    ref_x, ref_y = self.reference_star_list[0]
                    print(f"第一颗参考星坐标: ({ref_x}, {ref_y})")
                    
                    # 获取当前图像的WCS信息
                    if hasattr(self.main_window, 'image_processor') and self.main_window.image_processor:
                        print("image_processor存在")
                        if hasattr(self.main_window.image_processor, 'wcs') and self.main_window.image_processor.wcs:
                            print("WCS存在")
                            wcs = self.main_window.image_processor.wcs
                            if wcs:
                                print("WCS对象存在")
                                # 将像素坐标转换为天球坐标
                                from astropy.coordinates import SkyCoord
                                from astropy import units as u
                                
                                # 兼容不同版本的astropy
                                try:
                                    if hasattr(wcs, 'pixel_to_world'):
                                        # 新版本astropy
                                        sky_coord = wcs.pixel_to_world(ref_x, ref_y)
                                    elif hasattr(wcs, 'wcs') and hasattr(wcs.wcs, 'pixel_to_world'):
                                        # 旧版本astropy
                                        sky_coord = wcs.wcs.pixel_to_world(ref_x, ref_y)
                                    else:
                                        # 更旧的版本，使用all_pix2world
                                        sky_coord = wcs.all_pix2world(ref_x, ref_y, 1)
                                        if isinstance(sky_coord, tuple):
                                            sky_coord = SkyCoord(sky_coord[0][0], sky_coord[1][0], unit='deg')
                                except Exception as e:
                                    print(f"WCS坐标转换失败: {e}")
                                    raise
                                
                                ra = sky_coord.ra.deg
                                dec = sky_coord.dec.deg
                                
                                print(f"参考星位置: 像素=({ref_x}, {ref_y}), RA={ra:.6f}, Dec={dec:.6f}")
                                
                                # 查询UCAC4星表
                                if hasattr(self, 'catalog_query') and self.catalog_query:
                                    print("catalog_query存在")
                                    print(f"UCAC4可用状态: {self.catalog_query.ucac4_available}")
                                    print(f"UCAC4路径: {self.catalog_query.ucac4_path}")
                                    
                                    try:
                                        # 增加搜索半径到0.5度，提高成功率
                                        search_radius = 0.5
                                        print(f"开始查询UCAC4: RA={ra:.6f}, Dec={dec:.6f}, 搜索半径={search_radius}度")
                                        star_info = self.catalog_query.query_ucac4(ra, dec, search_radius=search_radius)
                                        print(f"UCAC4查询结果: {star_info}")
                                        
                                        if star_info and 'magnitude' in star_info:
                                            reference_magnitude = star_info['magnitude']
                                            self.status_label.setText(f"已获取UCAC4星等: {reference_magnitude:.3f}")
                                            print(f"参考星UCAC4星等: {reference_magnitude:.3f}")
                                        else:
                                            print("UCAC4查询未找到匹配的恒星")
                                            QMessageBox.warning(self, "警告", "UCAC4查询未找到匹配的恒星，将使用默认0等")
                                            reference_magnitude = None
                                    except Exception as e:
                                        print(f"UCAC4查询失败: {e}")
                                        import traceback
                                        traceback.print_exc()
                                        QMessageBox.warning(self, "警告", f"UCAC4查询失败: {e}\n将使用默认0等")
                                        reference_magnitude = None
                                else:
                                    print("没有catalog_query实例")
                                    QMessageBox.warning(self, "警告", "UCAC4星表未初始化，将使用默认0等")
                                    reference_magnitude = None
                            else:
                                print("WCS.wcs无效")
                                QMessageBox.warning(self, "警告", "FITS文件中缺少WCS坐标信息，无法查询UCAC4星等\n将使用默认0等")
                                reference_magnitude = None
                        else:
                            print("没有WCS信息")
                            QMessageBox.warning(self, "警告", "FITS文件中缺少WCS坐标信息，无法查询UCAC4星等\n将使用默认0等")
                            reference_magnitude = None
                    else:
                        print("没有image_processor")
                        QMessageBox.warning(self, "警告", "无法获取图像处理器，将使用默认0等")
                        reference_magnitude = None
                except Exception as e:
                    print(f"获取UCAC4星等失败: {e}")
                    import traceback
                    traceback.print_exc()
                    QMessageBox.warning(self, "警告", f"获取UCAC4星等失败: {e}\n将使用默认0等")
                    reference_magnitude = None
            else:
                print("多颗参考星但未勾选UCAC4")
                reference_magnitude = None
        else:
            print("没有参考星")
            reference_magnitude = None
        
        # 如果多颗参考星但没有获取到星等，使用默认0等
        if len(self.reference_star_list) > 1 and reference_magnitude is None:
            print("多颗参考星但未获取到UCAC4星等，使用默认0等")
            reference_magnitude = 0.0
        
        # 如果单颗参考星但没有获取到星等，使用默认0等
        if len(self.reference_star_list) == 1 and reference_magnitude is None:
            print("单颗参考星但未获取到UCAC4星等，使用默认0等")
            reference_magnitude = 0.0
        
        # 执行测光计算
        self.perform_photometry_calculation(reference_magnitude)
        
        # 更新光变曲线
        self.update_light_curve()
    
    def perform_photometry_calculation(self, reference_magnitude):
        """执行测光计算"""
        try:
            # 获取孔径参数
            aperture_radius = self.aperture_spinbox.value()
            inner_radius = self.inner_spinbox.value()
            outer_radius = self.outer_spinbox.value()
            
            # 存储测光结果
            self.photometry_results = {
                'reference_magnitude': reference_magnitude,
                'reference_fluxes': [],
                'target_fluxes': [],
                'relative_magnitudes': [],
                'times': [],
                'aperture_radius': aperture_radius,
                'inner_radius': inner_radius,
                'outer_radius': outer_radius
            }
            
            # 计算所有图像的测光结果
            reference_fluxes = []
            target_fluxes = []
            
            for img_idx, img_info in enumerate(self.images):
                print(f"处理第{img_idx+1}张图像...")
                
                # 获取原始图像数据（不是归一化后的数据）
                image_data = None
                
                # 方法0: 首先检查图片是否已对齐，如果已对齐则使用对齐后的数据
                if hasattr(self, 'main_window') and self.main_window:
                    try:
                        # 检查主窗口中的图片是否已对齐
                        if hasattr(self.main_window, 'images') and img_idx < len(self.main_window.images):
                            main_image_info = self.main_window.images[img_idx]
                            is_aligned = main_image_info.get('aligned', False)
                            
                            # 如果图片已对齐，优先使用对齐后的数据
                            if is_aligned and hasattr(self.main_window, 'original_images') and img_idx < len(self.main_window.original_images):
                                image_data = self.main_window.original_images[img_idx].copy()
                                print(f"图片已对齐，使用对齐后的数据: {main_image_info.get('filename', 'Unknown')}, 尺寸: {image_data.shape}")
                                print(f"对齐图像数据统计: min={image_data.min():.2f}, max={image_data.max():.2f}, mean={image_data.mean():.2f}")
                    except Exception as e:
                        print(f"检查图片对齐状态失败: {e}")
                
                # 方法1: 如果图片未对齐或检查失败，使用主窗口的图像处理器获取当前图像数据
                if image_data is None and hasattr(self, 'main_window') and self.main_window:
                    try:
                        # 切换到当前图像
                        if hasattr(self.main_window, 'image_list') and self.main_window.image_list:
                            self.main_window.image_list.setCurrentRow(img_idx)
                            
                            # 等待图像加载完成
                            from PyQt5.QtCore import QTimer
                            QTimer.singleShot(100, lambda: None)
                            
                            # 获取当前显示的图像数据
                            if hasattr(self.main_window, 'image_processor') and self.main_window.image_processor:
                                if self.main_window.image_processor.image_data is not None:
                                    image_data = self.main_window.image_processor.image_data.copy()
                                    print(f"从主窗口获取第{img_idx+1}张图像数据，尺寸: {image_data.shape}")
                                else:
                                    print(f"主窗口图像处理器数据为空")
                            else:
                                print(f"主窗口没有图像处理器")
                    except Exception as e:
                        print(f"从主窗口获取图像数据失败: {e}")
                
                # 方法2: 如果方法1失败，尝试从文件加载
                if image_data is None and 'file_path' in img_info:
                    try:
                        # 直接从FITS文件加载数据
                        from astropy.io import fits
                        with fits.open(img_info['file_path']) as hdul:
                            image_data = hdul[0].data
                        print(f"从文件加载第{img_idx+1}张图像数据: {img_info['file_path']}")
                    except Exception as e:
                        print(f"从文件加载图像数据时出错: {e}")
                
                # 方法3: 从主窗口的raw_fits_images获取原始FITS数据（用于测光）
                if image_data is None:
                    try:
                        # 优先使用raw_fits_images，因为这是原始FITS数据，没有归一化
                        if hasattr(self.main_window, 'raw_fits_images') and self.main_window.raw_fits_images:
                            if img_idx < len(self.main_window.raw_fits_images):
                                raw_fits_data = self.main_window.raw_fits_images[img_idx]
                                if raw_fits_data is not None:
                                    # 确保复制图像数据，避免引用同一个对象
                                    image_data = raw_fits_data.copy() if hasattr(raw_fits_data, 'copy') else raw_fits_data
                                    print(f"从主窗口raw_fits_images获取第{img_idx+1}张图像数据，尺寸: {image_data.shape}, 数据类型: {type(image_data)}")
                                    # 打印一些统计信息来验证数据是否正确
                                    print(f"图像数据统计: min={image_data.min():.2f}, max={image_data.max():.2f}, mean={image_data.mean():.2f}")
                                else:
                                    print(f"主窗口raw_fits_images[{img_idx}]数据为空")
                            else:
                                print(f"主窗口raw_fits_images索引超出范围: {img_idx} >= {len(self.main_window.raw_fits_images)}")
                        else:
                            print(f"主窗口没有raw_fits_images数据")
                    except Exception as e:
                        print(f"从主窗口raw_fits_images获取图像数据失败: {e}")
                        import traceback
                        traceback.print_exc()
                
                # 方法4: 如果raw_fits_images没有数据，尝试使用original_images（归一化后的数据）
                if image_data is None:
                    try:
                        # 尝试从主窗口的original_images获取归一化后的数据
                        if hasattr(self.main_window, 'original_images') and self.main_window.original_images:
                            if img_idx < len(self.main_window.original_images):
                                original_data = self.main_window.original_images[img_idx]
                                if original_data is not None:
                                    # 确保复制图像数据，避免引用同一个对象
                                    image_data = original_data.copy() if hasattr(original_data, 'copy') else original_data
                                    print(f"从主窗口original_images获取第{img_idx+1}张图像数据（归一化后），尺寸: {image_data.shape}, 数据类型: {type(image_data)}")
                                    # 打印一些统计信息来验证数据是否正确
                                    print(f"图像数据统计: min={image_data.min():.2f}, max={image_data.max():.2f}, mean={image_data.mean():.2f}")
                                else:
                                    print(f"主窗口original_images[{img_idx}]数据为空")
                            else:
                                print(f"主窗口original_images索引超出范围: {img_idx} >= {len(self.main_window.original_images)}")
                        else:
                            print(f"主窗口没有original_images数据")
                    except Exception as e:
                        print(f"从主窗口original_images获取图像数据失败: {e}")
                        import traceback
                        traceback.print_exc()
                
                # 方法5: 如果图像信息中有数据字段
                if image_data is None and 'data' in img_info and img_info['data'] is not None:
                    # 确保复制图像数据，避免引用同一个对象
                    image_data = img_info['data'].copy() if hasattr(img_info['data'], 'copy') else img_info['data']
                    print(f"从图像信息获取第{img_idx+1}张图像数据，尺寸: {image_data.shape}, 数据类型: {type(image_data)}")
                    # 打印一些统计信息来验证数据是否正确
                    print(f"图像数据统计: min={image_data.min():.2f}, max={image_data.max():.2f}, mean={image_data.mean():.2f}")
                else:
                    if image_data is None:
                        print(f"图像信息中没有数据字段或数据为空")
                
                if image_data is None:
                    print(f"警告: 无法获取第{img_idx+1}张图像的数据，跳过该图像")
                    # 跳过无法获取数据的图像，不补0
                    continue
                else:
                    print(f"成功获取第{img_idx+1}张图像数据，尺寸: {image_data.shape}")
                    # 打印图像数据的统计信息，验证每帧数据是否不同
                    print(f"第{img_idx+1}张图像统计: min={image_data.min():.2f}, max={image_data.max():.2f}, mean={image_data.mean():.2f}")
                    
                    # 计算参考星的总流量
                    ref_fluxes_in_image = []
                    for ref_idx, (ref_x, ref_y) in enumerate(self.reference_star_list):
                        flux = self.calculate_star_flux(image_data, ref_x, ref_y, 
                                                       aperture_radius, inner_radius, outer_radius)
                        ref_fluxes_in_image.append(flux)
                        print(f"  参考星{ref_idx+1}流量: {flux:.2f}")
                    
                    # 计算目标星的流量
                    if self.target_star:
                        # 在移动天体模式下，使用当前帧的预测位置
                        if self.moving_target_mode and len(self.moving_target_path) > 0:
                            # 查找当前帧的预测位置
                            target_pos = None
                            for frame_idx, pred_x, pred_y in self.moving_target_path:
                                if frame_idx == img_idx:
                                    target_pos = (pred_x, pred_y)
                                    break
                            
                            # 如果找到当前帧的预测位置，使用它
                            if target_pos:
                                target_x, target_y = target_pos
                                print(f"  使用预测位置进行测光：第{img_idx+1}帧 ({target_x:.1f}, {target_y:.1f})")
                            else:
                                # 如果没有找到预测位置，使用默认位置
                                target_x, target_y = self.target_star
                                print(f"  未找到预测位置，使用默认位置：第{img_idx+1}帧 ({target_x:.1f}, {target_y:.1f})")
                        else:
                            # 非移动天体模式，使用目标星位置
                            target_x, target_y = self.target_star
                            print(f"  使用目标星位置：第{img_idx+1}帧 ({target_x:.1f}, {target_y:.1f})")
                        
                        target_flux = self.calculate_star_flux(image_data, target_x, target_y,
                                                              aperture_radius, inner_radius, outer_radius)
                        print(f"  目标星流量: {target_flux:.2f}")
                    else:
                        target_flux = 0
                    
                    # 确保图像数据是二维数组
                    if image_data.ndim > 2:
                        image_data = image_data.squeeze()
                    
                    # 计算相对星等（多颗参考星交叉测光）
                    if ref_fluxes_in_image and target_flux > 0:
                        # 使用中位数而不是平均值，减少异常值影响
                        median_ref_flux = np.median(ref_fluxes_in_image)
                        
                        # 计算每颗参考星的权重（基于流量稳定性）
                        if len(ref_fluxes_in_image) > 1:
                            # 计算每颗参考星的相对稳定性
                            ref_fluxes_array = np.array(ref_fluxes_in_image)
                            flux_std = np.std(ref_fluxes_array)
                            if flux_std > 0:
                                # 流量越稳定，权重越高
                                weights = 1.0 / (1.0 + np.abs(ref_fluxes_array - median_ref_flux) / flux_std)
                                weights = weights / np.sum(weights)  # 归一化
                                weighted_ref_flux = np.sum(ref_fluxes_array * weights)
                            else:
                                weighted_ref_flux = median_ref_flux
                        else:
                            weighted_ref_flux = median_ref_flux
                        
                        # 将流量转换为星等，然后相减
                        # 参考星等
                        if weighted_ref_flux > 0:
                            ref_magnitude = -2.5 * np.log10(weighted_ref_flux)
                        else:
                            ref_magnitude = 0
                        
                        # 目标星等
                        if target_flux > 0:
                            target_magnitude = -2.5 * np.log10(target_flux)
                        else:
                            target_magnitude = 0
                        
                        # 星等差计算
                        if reference_magnitude is not None:
                            # 如果有参考星的真实星等（多颗参考星）
                            # 先计算相对星等差
                            relative_magnitude_diff = target_magnitude - ref_magnitude
                            # 然后加上参考星的真实星等，得到目标星的绝对星等
                            magnitude_diff = relative_magnitude_diff + reference_magnitude
                            print(f"图像{img_idx+1}: 目标星流量={target_flux:.2f}, 参考星流量={weighted_ref_flux:.2f}")
                            print(f"  参考星等={ref_magnitude:.3f}, 目标星等={target_magnitude:.3f}, 参考星真实星等={reference_magnitude:.3f}")
                            print(f"  相对星等差={relative_magnitude_diff:.3f}, 目标星绝对星等={magnitude_diff:.3f}")
                        else:
                            # 如果没有参考星的真实星等（单颗参考星），直接用相对星等差
                            magnitude_diff = target_magnitude - ref_magnitude
                            print(f"图像{img_idx+1}: 目标星流量={target_flux:.2f}, 参考星流量={weighted_ref_flux:.2f}")
                            print(f"  参考星等={ref_magnitude:.3f}, 目标星等={target_magnitude:.3f}")
                            print(f"  相对星等差={magnitude_diff:.3f}")
                    else:
                        magnitude_diff = 0
                        print(f"图像{img_idx+1}: 无有效流量数据")
                
                # 存储结果
                reference_fluxes.append(ref_fluxes_in_image)
                target_fluxes.append(target_flux)
                self.photometry_results['reference_fluxes'].append(ref_fluxes_in_image)
                self.photometry_results['target_fluxes'].append(target_flux)
                self.photometry_results['relative_magnitudes'].append(magnitude_diff)
                
                # 存储实际时间（转换为儒略历时间）
                julian_time = None
                if img_idx < len(self.images):
                    img_info = self.images[img_idx]
                    # 尝试从图像信息中获取时间
                    if 'header' in img_info and img_info['header'] is not None:
                        header = img_info['header']
                        # 尝试从DATE-OBS获取时间
                        if 'DATE-OBS' in header:
                            date_str = str(header['DATE-OBS'])
                            # 将时间字符串转换为datetime对象
                            dt = parse_fits_time(date_str)
                            if dt:
                                # 转换为儒略历时间
                                from astropy.time import Time
                                time_obj = Time(dt)
                                julian_time = time_obj.jd
                                print(f"图像{img_idx+1}: DATE-OBS={date_str}, 儒略历时间={julian_time:.6f}")
                        # 尝试从DATE获取时间
                        elif 'DATE' in header:
                            date_str = str(header['DATE'])
                            dt = parse_fits_time(date_str)
                            if dt:
                                from astropy.time import Time
                                time_obj = Time(dt)
                                julian_time = time_obj.jd
                                print(f"图像{img_idx+1}: DATE={date_str}, 儒略历时间={julian_time:.6f}")
                    
                    # 如果没有时间信息，使用图像序号作为相对时间
                    if julian_time is None:
                        julian_time = float(img_idx)
                        print(f"图像{img_idx+1}: 无时间信息，使用序号={julian_time}")
                
                self.photometry_results['times'].append(julian_time)
            
            # 计算变幅
            valid_magnitudes = [m for m in self.photometry_results['relative_magnitudes'] if m != 0]
            if valid_magnitudes:
                mag_range = max(valid_magnitudes) - min(valid_magnitudes)
                mag_std = np.std(valid_magnitudes)
                self.status_label.setText(f"测光完成，变幅: {mag_range:.3f}，标准差: {mag_std:.3f}")
                print(f"测光完成，有效数据点: {len(valid_magnitudes)}，变幅: {mag_range:.3f}")
            else:
                self.status_label.setText("测光完成，但无有效数据")
                print("测光完成，但无有效数据")
            
            # 更新参考星信息显示（使用第一张图像的结果）
            if reference_fluxes and reference_fluxes[0]:
                ref_info = ""
                for i, (ref_x, ref_y) in enumerate(self.reference_star_list):
                    flux = reference_fluxes[0][i] if i < len(reference_fluxes[0]) else 0
                    ref_info += f"参考星{i+1}: ({ref_x:.1f}, {ref_y:.1f}) - 亮度: {flux:.1f}"
                    
                    # 如果获取了UCAC4星等，显示星等信息
                    if self.ucac4_checkbox.isChecked():
                        # 这里可以添加具体的星等查询逻辑
                        star_magnitude = reference_magnitude  # 暂时使用参考星等
                        ref_info += f" - 星等: {star_magnitude:.2f}"
                    
                    ref_info += "\n"
                
                ref_info += f"参考星等: {reference_magnitude:.2f}"
                
                self.reference_info_label.setText(ref_info)
            
        except Exception as e:
            self.status_label.setText(f"测光计算失败: {str(e)}")
    
    def calculate_star_flux(self, image_data, x, y, aperture_radius, inner_radius, outer_radius):
        """计算单颗星的流量（改进的三圈孔径测光算法）"""
        try:
            # 确保图像数据是二维数组
            if image_data.ndim > 2:
                image_data = image_data.squeeze()
            
            # 确保坐标在图像范围内
            x_int, y_int = int(round(x)), int(round(y))
            if x_int < 0 or y_int < 0 or x_int >= image_data.shape[1] or y_int >= image_data.shape[0]:
                print(f"坐标超出范围: ({x_int}, {y_int}), 图像尺寸: {image_data.shape}")
                return 0
            
            # 方法1: 使用photutils的孔径测光（标准方法）
            positions = [(x, y)]
            aperture = CircularAperture(positions, r=aperture_radius)
            annulus_aperture = CircularAnnulus(positions, r_in=inner_radius, r_out=outer_radius)
            
            # 执行孔径测光
            phot_table = aperture_photometry(image_data, aperture)
            annulus_phot_table = aperture_photometry(image_data, annulus_aperture)
            
            # 计算背景
            aperture_area = aperture.area
            annulus_area = annulus_aperture.area
            
            aperture_sum = phot_table['aperture_sum'][0]
            annulus_sum = annulus_phot_table['aperture_sum'][0]
            
            # 计算背景平均值
            if annulus_area > 0:
                background_per_pixel = annulus_sum / annulus_area
            else:
                background_per_pixel = 0
            
            # 减去背景
            background_subtracted_flux = aperture_sum - (background_per_pixel * aperture_area)
            
            # 方法2: 手动计算孔径内像素（更精确的方法）
            # 创建一个圆形掩码
            y_grid, x_grid = np.ogrid[:image_data.shape[0], :image_data.shape[1]]
            distance = np.sqrt((x_grid - x)**2 + (y_grid - y)**2)
            
            # 孔径内掩码
            aperture_mask = distance <= aperture_radius
            
            # 环状掩码（用于背景估计）
            annulus_mask = (distance > inner_radius) & (distance <= outer_radius)
            
            # 计算孔径内总流量
            aperture_flux = np.sum(image_data[aperture_mask])
            
            # 计算背景（使用环状区域的中位数，减少异常值影响）
            if np.sum(annulus_mask) > 0:
                background_median = np.median(image_data[annulus_mask])
                background_flux = background_median * np.sum(aperture_mask)
            else:
                background_flux = 0
            
            # 减去背景
            manual_flux = aperture_flux - background_flux
            
            # 使用两种方法的加权平均（手动方法权重更高）
            final_flux = 0.3 * background_subtracted_flux + 0.7 * manual_flux
            
            # 调试信息
            print(f"测光结果 - 位置: ({x:.1f}, {y:.1f})")
            print(f"  方法1(photutils): {background_subtracted_flux:.2f}")
            print(f"  方法2(手动): {manual_flux:.2f}")
            print(f"  最终流量: {final_flux:.2f}")
            
            return max(final_flux, 0)  # 确保非负
            
        except Exception as e:
            print(f"测光计算错误: {e}")
            return 0
    
    def update_light_curve(self):
        """更新光变曲线显示 - 打开独立的光变曲线窗口"""
        # 检查是否有测光结果
        if not hasattr(self, 'photometry_results') or not self.photometry_results:
            print("无测光数据")
            return
        
        # 获取真实测光数据
        times = self.photometry_results.get('times', [])
        magnitudes = self.photometry_results.get('relative_magnitudes', [])
        
        if not times or not magnitudes:
            print("无有效测光数据")
            return
        
        # 如果光变曲线窗口不存在，创建它
        if self.light_curve_window is None:
            self.light_curve_window = LightCurveWindow(parent=self, photometry_window=self)
            self.light_curve_window.show()
            print("光变曲线窗口已创建")
        
        # 更新光变曲线
        self.light_curve_window.update_light_curve(times, magnitudes)
        self.status_label.setText("测光完成，光变曲线已更新")
        print("光变曲线已更新到独立窗口")
    
    def on_confirm_params(self):
        """确认参数更改并更新所有标记"""
        try:
            print("确认参数更改...")
            print(f"孔径: {self.aperture_spinbox.value()}")
            print(f"内径: {self.inner_spinbox.value()}")
            print(f"外径: {self.outer_spinbox.value()}")
            
            # 更新所有标记的显示
            self.update_markers()
            
            # 保存参数到JSON文件
            self.save_photometry_params_to_json()
            
            self.status_label.setText("参数已确认，标记已更新")
            print("标记已更新")
        except Exception as e:
            print(f"确认参数失败: {e}")
            import traceback
            traceback.print_exc()
    
    def save_photometry_params(self):
        """保存测光参数"""
        try:
            self.saved_params = {
                'aperture_radius': self.aperture_spinbox.value(),
                'inner_radius': self.inner_spinbox.value(),
                'outer_radius': self.outer_spinbox.value(),
                'use_ucac4': self.ucac4_checkbox.isChecked()
            }
            # 在实际应用中，这里可以保存到文件或配置中
            self.status_label.setText("测光参数已保存")
        except Exception as e:
            print(f"保存参数失败: {e}")
    
    def load_saved_params(self):
        """加载保存的测光参数"""
        try:
            self.aperture_spinbox.setValue(self.saved_params['aperture_radius'])
            self.inner_spinbox.setValue(self.saved_params['inner_radius'])
            self.outer_spinbox.setValue(self.saved_params['outer_radius'])
            self.ucac4_checkbox.setChecked(self.saved_params['use_ucac4'])
            
            # 连接参数变化信号
            self.aperture_spinbox.valueChanged.connect(self.save_photometry_params)
            self.inner_spinbox.valueChanged.connect(self.save_photometry_params)
            self.outer_spinbox.valueChanged.connect(self.save_photometry_params)
            self.ucac4_checkbox.stateChanged.connect(self.save_photometry_params)
            
        except Exception as e:
            print(f"加载参数失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件 - 清空测光信息"""
        try:
            print("关闭测光窗口，清空所有测光信息")
            
            # 清空参考星和目标星
            self.reference_star_list = []
            self.target_star = None
            
            # 清空测光结果
            self.photometry_results = {}
            self.light_curve_data = None
            
            # 清空图像列表
            self.image_list.clear()
            
            # 清空图像数据
            self.images = []
            self.current_image_index = -1
            
            # 更新标记（如果场景存在）
            try:
                self.update_markers()
            except Exception as e:
                print(f"更新标记失败: {e}")
            
            # 更新光变曲线（如果图形存在）
            try:
                self.update_light_curve()
            except Exception as e:
                print(f"更新光变曲线失败: {e}")
            
            print("测光信息已清空")
        except Exception as e:
            print(f"清空测光信息失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 接受关闭事件，但不删除窗口对象
        event.accept()
    
    def keyPressEvent(self, event):
        """键盘事件处理 - 支持DEL键删除图像"""
        if event.key() == Qt.Key_Delete:
            self.delete_selected_images()
        else:
            super().keyPressEvent(event)
    
    def delete_selected_images(self):
        """删除选中的图像"""
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            return
        
        # 获取选中项的索引
        selected_rows = [self.image_list.row(item) for item in selected_items]
        if not selected_rows:
            return
        
        # 按索引从大到小排序，以便从后往前删除
        selected_rows.sort(reverse=True)
        
        # 确认删除
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除选中的{len(selected_rows)}张图像吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 删除图像
            for row in selected_rows:
                if row < len(self.images):
                    self.images.pop(row)
                    # PhotometryWindow没有original_images属性，跳过此检查
                    # if hasattr(self, 'original_images') and row < len(self.original_images):
                    #     self.original_images.pop(row)
            
            # 清空测光结果
            self.photometry_results = {}
            self.light_curve_data = None
            
            # 更新图像列表
            self.image_list.clear()
            for i, img in enumerate(self.images):
                filename = os.path.basename(img['filename'])
                self.image_list.addItem(f"{i+1}. {filename}")
            
            # 如果还有图像，显示第一张
            if self.images:
                self.current_image_index = 0
                self.show_current_image_in_module()
            else:
                self.current_image_index = -1
            
            self.status_label.setText(f"已删除{len(selected_rows)}张图像")
            print(f"已删除{len(selected_rows)}张图像")
    
    def save_photometry_params_to_json(self):
        """保存测光参数到JSON文件"""
        try:
            import json
            
            params = {
                'aperture_radius': self.aperture_spinbox.value(),
                'inner_radius': self.inner_spinbox.value(),
                'outer_radius': self.outer_spinbox.value(),
                'use_ucac4': self.ucac4_checkbox.isChecked()
            }
            
            # 保存到项目目录
            config_file = os.path.join(os.path.dirname(__file__), 'photometry_config.json')
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(params, f, indent=4, ensure_ascii=False)
            
            self.status_label.setText("测光参数已保存")
            print(f"测光参数已保存到: {config_file}")
            
        except Exception as e:
            print(f"保存参数失败: {e}")
            import traceback
            traceback.print_exc()
    
    def load_photometry_params_from_json(self):
        """从JSON文件加载测光参数"""
        try:
            import json
            
            config_file = os.path.join(os.path.dirname(__file__), 'photometry_config.json')
            
            if not os.path.exists(config_file):
                print("配置文件不存在，使用默认参数")
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                params = json.load(f)
            
            # 应用参数
            self.aperture_spinbox.setValue(params.get('aperture_radius', 10.0))
            self.inner_spinbox.setValue(params.get('inner_radius', 15.0))
            self.outer_spinbox.setValue(params.get('outer_radius', 20.0))
            self.ucac4_checkbox.setChecked(params.get('use_ucac4', False))
            
            self.status_label.setText("测光参数已加载")
            print(f"测光参数已从{config_file}加载")
            
        except Exception as e:
            print(f"加载参数失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # 测试代码
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建测试图像数据
    test_images = [
        {
            'filename': 'test1.fits',
            'shape': (512, 512),
            'data': np.random.normal(1000, 100, (512, 512))
        },
        {
            'filename': 'test2.fits',
            'shape': (512, 512),
            'data': np.random.normal(1000, 100, (512, 512))
        }
    ]
    
    window = PhotometryWindow()
    window.set_images(test_images)
    window.show()
    
    sys.exit(app.exec_())