import os
import sys

def check_main_program_copyright():
    """检查主程序的版权信息"""
    try:
        main_program_path = os.path.join(os.path.dirname(__file__), 'GSUNView.py')
        if not os.path.exists(main_program_path):
            return True  # 如果主程序不存在，跳过检查
        
        with open(main_program_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_copyright_counts = {
            "Guoyou Sun": 20,
            "孙国佑": 20,
            "sunguoyou.lamost.org": 20,
            "天体收藏家": 10,
            "星视 GSUN View": 20
        }
        
        for check_str, min_count in required_copyright_counts.items():
            count = content.count(check_str)
            if count < min_count:
                print("错误：主程序版权保护机制被触发！")
                print(f"检测到关键版权信息被删除：{check_str}")
                print("本软件受版权保护，未经授权不得修改。")
                print("请联系作者获取授权：http://sunguoyou.lamost.org/")
                sys.exit(1)
        
        return True
    except Exception as e:
        print(f"版权验证失败：{str(e)}")
        print("本软件受版权保护，无法运行。")
        sys.exit(1)

check_main_program_copyright()

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.colors as colors
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import astropy.io.fits as fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from astropy import units as u
from PIL import Image, ImageQt
import io
import base64
import tempfile
import traceback
import json
import logging
from pathlib import Path
import platform
from astroquery.astrometry_net import AstrometryNet
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFileDialog, QLabel, QTabWidget, QTableWidget, 
    QTableWidgetItem, QSplitter, QComboBox, QFormLayout, QLineEdit,
    QGroupBox, QCheckBox, QRadioButton, QMessageBox, QSpinBox, 
    QDoubleSpinBox, QProgressBar, QStatusBar, QToolBar, QAction,
    QMenu, QMenuBar, QDialog, QTextEdit, QDialogButtonBox, QScrollArea
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QThread, QUrl, QPointF, QRectF, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QImage, QPalette, QColor, QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView
from datetime import datetime
from astropy.visualization import ZScaleInterval, MinMaxInterval, PercentileInterval, SqrtStretch, AsinhStretch, LogStretch
from astropy.stats import sigma_clipped_stats
import re
import shutil
import configparser


class SettingsManager:
    def __init__(self):
        self.settings = self.get_default_settings()
        self._config_path = os.path.abspath('config.ini')
        self._load_from_file()

    def get_default_settings(self):
        return {
            "database_path": "H:\\catalog_grappa3e",
            "center_ra": 0.0,
            "center_dec": 0.0,
            "fov_width": 1.0,
            "fov_height": 1.0,
            "pixel_scale": 1.0,
            "search_radius": 0.5,
        }

    def update_setting(self, key, value):
        self.settings[key] = value
        self._save_to_file()

    def get_setting(self, key):
        return self.settings.get(key)

    def _load_from_file(self):
        try:
            cfg = configparser.ConfigParser()
            if os.path.exists(self._config_path):
                cfg.read(self._config_path)
                if cfg.has_section('Settings'):
                    s = cfg['Settings']
                    # 支持多种键名，做合理映射
                    if 'database_path' in s:
                        self.settings['database_path'] = s.get('database_path')
                    elif 'asteroid_db_path' in s:
                        # 使用小行星数据库路径作为数据库路径的默认值
                        self.settings['database_path'] = s.get('asteroid_db_path')
                    if 'center_ra' in s:
                        self.settings['center_ra'] = float(s.get('center_ra'))
                    if 'center_dec' in s:
                        self.settings['center_dec'] = float(s.get('center_dec'))
                    if 'fov_width' in s:
                        self.settings['fov_width'] = float(s.get('fov_width'))
                    if 'fov_height' in s:
                        self.settings['fov_height'] = float(s.get('fov_height'))
                    if 'pixel_scale' in s:
                        self.settings['pixel_scale'] = float(s.get('pixel_scale'))
                    if 'search_radius' in s:
                        self.settings['search_radius'] = float(s.get('search_radius'))
                    if 'astrometry_api_key' in s:
                        self.settings['astrometry_api_key'] = s.get('astrometry_api_key')
        except Exception:
            pass

    def _save_to_file(self):
        try:
            cfg = configparser.ConfigParser()
            if os.path.exists(self._config_path):
                cfg.read(self._config_path)
            if not cfg.has_section('Settings'):
                cfg.add_section('Settings')
            # 写回当前设置
            if 'database_path' in self.settings and self.settings['database_path'] is not None:
                cfg['Settings']['database_path'] = str(self.settings['database_path'])
            if 'center_ra' in self.settings:
                cfg['Settings']['center_ra'] = str(self.settings['center_ra'])
            if 'center_dec' in self.settings:
                cfg['Settings']['center_dec'] = str(self.settings['center_dec'])
            if 'fov_width' in self.settings:
                cfg['Settings']['fov_width'] = str(self.settings['fov_width'])
            if 'fov_height' in self.settings:
                cfg['Settings']['fov_height'] = str(self.settings['fov_height'])
            if 'pixel_scale' in self.settings:
                cfg['Settings']['pixel_scale'] = str(self.settings['pixel_scale'])
            if 'search_radius' in self.settings:
                cfg['Settings']['search_radius'] = str(self.settings['search_radius'])
            if 'astrometry_api_key' in self.settings and self.settings['astrometry_api_key']:
                cfg['Settings']['astrometry_api_key'] = str(self.settings['astrometry_api_key'])
            with open(self._config_path, 'w') as f:
                cfg.write(f)
        except Exception:
            pass


class FitsImageProcessor:
    def __init__(self):
        self.current_image = None
        self.image_path = None
        self.metadata = {}
        self.image_data = None
        self.wcs = None
        self.header = None
        self.original_header = None
        self.original_filename = None
        self.pixel_scale = None
        self.original_hdul = None
        self.coord_system = None
        self.equinox = None
        self.original_cd_matrix = None
        self.auto_parse_wcs = True
    
    def __del__(self):
        """析构函数，确保关闭文件句柄"""
        try:
            if self.original_hdul:
                self.original_hdul.close()
                self.original_hdul = None
        except Exception:
            pass

    def set_auto_parse_wcs(self, flag):
        try:
            self.auto_parse_wcs = bool(flag)
        except Exception:
            self.auto_parse_wcs = True

    def load_fits(self, file_path):
        """加载FITS文件，保存原始头信息和相关坐标系统信息"""
        try:
            self.image_path = file_path
            self.original_filename = os.path.basename(file_path)
            
            # 关闭旧的HDU，防止文件句柄泄漏
            if self.original_hdul:
                try:
                    self.original_hdul.close()
                except Exception:
                    pass
                self.original_hdul = None
            
            # 清除旧数据
            self.current_image = None
            self.metadata = {}
            self.image_data = None
            self.wcs = None
            self.header = None
            self.original_header = None
            self.coord_system = None
            self.equinox = None
            self.original_cd_matrix = None
            
            # 打开FITS文件并保存原始HDU列表
            hdul = fits.open(file_path)
            self.original_hdul = hdul
            
            # 保存头信息
            primary_header = hdul[0].header
            self.header = primary_header
            self.original_header = primary_header.copy()
            self.metadata = dict(primary_header)
            
            # 提取坐标系统信息（在自动解析启用时）
            if self.auto_parse_wcs:
                if 'RADECSYS' in primary_header:
                    self.coord_system = primary_header['RADECSYS']
                elif 'RADESYS' in primary_header:
                    self.coord_system = primary_header['RADESYS']
                if 'EQUINOX' in primary_header:
                    self.equinox = primary_header['EQUINOX']
                # 提取CD矩阵信息(如果存在)
                if all(key in primary_header for key in ['CD1_1', 'CD1_2', 'CD2_1', 'CD2_2']):
                    self.original_cd_matrix = {
                        'CD1_1': float(primary_header['CD1_1']),
                        'CD1_2': float(primary_header['CD1_2']),
                        'CD2_1': float(primary_header['CD2_1']),
                        'CD2_2': float(primary_header['CD2_2'])
                    }
                    logging.info(f"从原始FITS文件提取CD矩阵: {self.original_cd_matrix}")
                    # 计算旋转角度
                    cd_rot_angle = np.degrees(np.arctan2(float(primary_header['CD1_2']), float(primary_header['CD1_1'])))
                    cd_rot_angle = (cd_rot_angle + 360) % 360
                    logging.info(f"从原始FITS的CD矩阵计算的旋转角度: {cd_rot_angle:.2f}°")
            
            logging.info(f"加载FITS文件: {file_path}, 坐标系统: {self.coord_system}, 分点: {self.equinox}")
            
            # 获取图像数据
            image_data = hdul[0].data
            
            # 处理多维数据，如果有必要取第一帧
            if image_data is not None and len(image_data.shape) > 2:
                logging.info(f"检测到多维数据: {image_data.shape}，使用第一帧")
                if len(image_data.shape) == 3:
                    image_data = image_data[0]
                elif len(image_data.shape) == 4:
                    image_data = image_data[0, 0]
            
            # 确保数据类型为浮点型
            if image_data is not None:
                self.image_data = image_data.astype(np.float32)
            
            # 检查头信息中是否有WCS信息（在自动解析启用时）
            if self.auto_parse_wcs:
                try:
                    # 先检查是否有必要的WCS关键字
                    has_ctype1 = 'CTYPE1' in primary_header
                    has_ctype2 = 'CTYPE2' in primary_header
                    
                    # 只有在有CTYPE关键字时才尝试创建WCS
                    if has_ctype1 and has_ctype2:
                        # 创建一个只包含必要WCS关键字的新头信息，避免某些非标准关键字导致崩溃
                        clean_header = fits.Header()
                        
                        # 只保留WCS相关的关键字
                        wcs_keywords = [
                            'NAXIS', 'NAXIS1', 'NAXIS2',
                            'CTYPE1', 'CTYPE2',
                            'CRVAL1', 'CRVAL2',
                            'CRPIX1', 'CRPIX2',
                            'CDELT1', 'CDELT2',
                            'CUNIT1', 'CUNIT2',
                            'CD1_1', 'CD1_2', 'CD2_1', 'CD2_2',
                            'PC1_1', 'PC1_2', 'PC2_1', 'PC2_2',
                            'EQUINOX', 'LONPOLE', 'LATPOLE',
                            'RADESYS'
                        ]
                        
                        for key in wcs_keywords:
                            if key in primary_header:
                                clean_header[key] = primary_header[key]
                        
                        # 添加SIP相关关键字
                        sip_keywords = ['A_ORDER', 'B_ORDER', 'AP_ORDER', 'BP_ORDER']
                        for key in sip_keywords:
                            if key in primary_header:
                                clean_header[key] = primary_header[key]
                        
                        # 添加SIP系数
                        for key in primary_header:
                            if key.startswith('A_') or key.startswith('B_') or key.startswith('AP_') or key.startswith('BP_'):
                                clean_header[key] = primary_header[key]
                        
                        # 使用清理后的头信息创建WCS
                        self.wcs = WCS(clean_header, relax=True)
                        
                        if self.wcs and self.wcs.is_celestial:
                            logging.info("成功从头信息中提取WCS坐标信息")
                            # 检查WCS坐标系统
                            if hasattr(self.wcs, 'wcs'):
                                if hasattr(self.wcs.wcs, 'radesys') and self.wcs.wcs.radesys:
                                    logging.info(f"WCS坐标系统: {self.wcs.wcs.radesys}")
                                if hasattr(self.wcs.wcs, 'equinox') and self.wcs.wcs.equinox:
                                    logging.info(f"WCS分点: {self.wcs.wcs.equinox}")
                        else:
                            self.wcs = None
                            logging.warning("FITS头信息中未找到有效的WCS坐标信息")
                    else:
                        self.wcs = None
                        logging.warning("FITS头信息中缺少CTYPE关键字，无法创建WCS")
                except Exception as e:
                    self.wcs = None
                    logging.warning(f"提取WCS信息失败: {e}")
            
            # 尝试从头信息中提取像素比例
            self.pixel_scale = self.extract_pixel_scale_from_header(primary_header)
            if self.pixel_scale:
                logging.info(f"从头信息中提取到像素比例: {self.pixel_scale:.4f} arcsec/pixel")
            
            return True
        except Exception as e:
            logging.error(f"加载FITS文件失败: {e}")
            # 出错时清除数据
            self.image_data = None
            self.wcs = None
            self.original_hdul = None
            self.header = None
            self.original_cd_matrix = None
            traceback.print_exc()
            return False

    def extract_pixel_scale_from_header(self, header):
        """从FITS头信息中提取像素比例（角秒/像素）"""
        try:
            # 方法1: 检查是否存在直接的像素比例值
            if 'PIXSCALE' in header:
                return float(header['PIXSCALE'])
            
            # 方法2: 从CD矩阵计算
            if all(key in header for key in ['CD1_1', 'CD1_2', 'CD2_1', 'CD2_2']):
                cd = np.array([[header['CD1_1'], header['CD1_2']], 
                              [header['CD2_1'], header['CD2_2']]])
                scale = np.sqrt(np.abs(np.linalg.det(cd))) * 3600.0  # 转换为角秒
                return scale
            
            # 方法3: 从CDELT值计算
            if all(key in header for key in ['CDELT1', 'CDELT2']):
                cdelt1 = np.abs(header['CDELT1'])
                cdelt2 = np.abs(header['CDELT2'])
                scale = np.mean([cdelt1, cdelt2]) * 3600.0  # 转换为角秒
                return scale
                
            # 找不到像素比例信息
            return None
        except Exception as e:
            logging.warning(f"Could not extract pixel scale from header: {e}")
            return None
    
    def update_wcs_from_file(self, file_path):
        """只更新WCS信息，不重新加载整个图像数据"""
        try:
            logging.info(f"更新WCS信息: {file_path}")
            
            # 关闭旧的HDU
            if self.original_hdul:
                self.original_hdul.close()
                self.original_hdul = None
            
            # 打开FITS文件
            hdul = fits.open(file_path)
            self.original_hdul = hdul
            
            # 保存头信息
            primary_header = hdul[0].header
            self.header = primary_header
            self.original_header = primary_header.copy()
            self.metadata = dict(primary_header)
            
            # 提取坐标系统信息
            if 'RADECSYS' in primary_header:
                self.coord_system = primary_header['RADECSYS']
            elif 'RADESYS' in primary_header:
                self.coord_system = primary_header['RADESYS']
            if 'EQUINOX' in primary_header:
                self.equinox = primary_header['EQUINOX']
            
            # 提取CD矩阵信息(如果存在)
            if all(key in primary_header for key in ['CD1_1', 'CD1_2', 'CD2_1', 'CD2_2']):
                self.original_cd_matrix = {
                    'CD1_1': float(primary_header['CD1_1']),
                    'CD1_2': float(primary_header['CD1_2']),
                    'CD2_1': float(primary_header['CD2_1']),
                    'CD2_2': float(primary_header['CD2_2'])
                }
                logging.info(f"从FITS文件提取CD矩阵: {self.original_cd_matrix}")
            
            # 检查头信息中是否有WCS信息
            try:
                if 'CTYPE1' in primary_header and 'CTYPE2' in primary_header:
                    # 创建一个只包含必要WCS关键字的新头信息，避免某些非标准关键字导致崩溃
                    clean_header = fits.Header()
                    
                    # 只保留WCS相关的关键字
                    wcs_keywords = [
                        'NAXIS', 'NAXIS1', 'NAXIS2',
                        'CTYPE1', 'CTYPE2',
                        'CRVAL1', 'CRVAL2',
                        'CRPIX1', 'CRPIX2',
                        'CDELT1', 'CDELT2',
                        'CUNIT1', 'CUNIT2',
                        'CD1_1', 'CD1_2', 'CD2_1', 'CD2_2',
                        'PC1_1', 'PC1_2', 'PC2_1', 'PC2_2',
                        'EQUINOX', 'LONPOLE', 'LATPOLE',
                        'RADESYS'
                    ]
                    
                    for key in wcs_keywords:
                        if key in primary_header:
                            clean_header[key] = primary_header[key]
                    
                    # 添加SIP相关关键字
                    sip_keywords = ['A_ORDER', 'B_ORDER', 'AP_ORDER', 'BP_ORDER']
                    for key in sip_keywords:
                        if key in primary_header:
                            clean_header[key] = primary_header[key]
                    
                    # 添加SIP系数
                    for key in primary_header:
                        if key.startswith('A_') or key.startswith('B_') or key.startswith('AP_') or key.startswith('BP_'):
                            clean_header[key] = primary_header[key]
                    
                    # 使用清理后的头信息创建WCS
                    self.wcs = WCS(clean_header, relax=True)
                    logging.info("成功从头信息中提取WCS坐标信息")
                else:
                    self.wcs = None
                    logging.warning("FITS头信息中未找到WCS坐标信息")
            except Exception as e:
                self.wcs = None
                logging.warning(f"提取WCS信息失败: {e}")
            
            # 尝试从头信息中提取像素比例
            self.pixel_scale = self.extract_pixel_scale_from_header(primary_header)
            if self.pixel_scale:
                logging.info(f"从头信息中提取到像素比例: {self.pixel_scale:.4f} arcsec/pixel")
            
            logging.info("WCS信息更新完成")
            return True
        except Exception as e:
            logging.error(f"更新WCS信息失败: {e}")
            traceback.print_exc()
            return False

    def get_header_info(self):
        return self.metadata

    def get_image_data(self):
        return self.image_data

    def get_wcs(self):
        return self.wcs
        
    def get_pixel_scale(self):
        """获取像素比例（角秒/像素）"""
        return self.pixel_scale

    def get_image_size(self):
        if self.image_data is not None:
            return self.image_data.shape
        return (0, 0)

    def normalize_image_for_display(self):
        if self.image_data is None:
            return None
        data = self.image_data
        if len(data.shape) > 2:
            data = data[0]
        vmin = np.percentile(data, 1)
        vmax = np.percentile(data, 99)
        normalized = np.clip(data, vmin, vmax)
        normalized = (normalized - vmin) / (vmax - vmin)
        return normalized


class CoordinateParser:
    def __init__(self, settings_manager):
        self.wcs = None
        self.settings = settings_manager
        self.ast = AstrometryNet()
        self.ast.api_key = 'jivoxaznmyxnotlr'
        self.pixel_scale = None

    def set_wcs(self, wcs):
        """设置WCS对象，用于坐标转换"""
        self.wcs = wcs
        
        # 保存WCS相关的坐标系统信息
        if wcs is not None:
            try:
                # 尝试从WCS对象获取坐标系统信息
                self.coord_system = None
                self.equinox = None
                
                if hasattr(wcs, 'wcs'):
                    if hasattr(wcs.wcs, 'radesys'):
                        self.coord_system = wcs.wcs.radesys
                    if hasattr(wcs.wcs, 'equinox'):
                        self.equinox = wcs.wcs.equinox
                    
                logging.debug(f"从WCS获取到坐标系统: {self.coord_system}, 分点: {self.equinox}")
            except Exception as e:
                logging.warning(f"获取WCS坐标系统信息失败: {e}")
    
    def set_pixel_scale(self, scale):
        """设置像素比例（角秒/像素）"""
        self.pixel_scale = scale

    def pixel_to_world(self, x, y):
        if self.wcs is None:
            return None
        if not self.wcs.has_celestial:
            logging.warning("WCS does not contain celestial information.")
            return None
        try:
            sky = self.wcs.pixel_to_world(x, y)
            return sky
        except Exception as e:
            logging.error(f"Error converting pixel coordinates to world coordinates: {e}")
            return None

    def world_to_pixel(self, ra, dec):
        if self.wcs is None:
            return None
        try:
            coords = SkyCoord(ra * u.deg, dec * u.deg)
            x, y = self.wcs.world_to_pixel(coords)
            return (x, y)
        except Exception as e:
            logging.error(f"Error converting world coordinates to pixel coordinates: {e}")
            return None

    def parse_image_coordinates(self, image_processor, status_callback=None):
        """解析图像坐标信息，获取中心坐标、视场大小等"""
        # 初始化像素比例，从图像处理器中获取
        header_pixel_scale = image_processor.get_pixel_scale()
        if header_pixel_scale is not None:
            self.set_pixel_scale(header_pixel_scale)
            if status_callback:
                status_callback(f"Using pixel scale from FITS header: {header_pixel_scale:.2f} arcsec/pixel")
        
        # 获取WCS信息
        wcs = image_processor.get_wcs()
        
        # 获取坐标系统信息
        coord_system = None
        equinox = None
        
        # 尝试从原始FITS头文件中获取坐标系统信息
        if image_processor.original_hdul and len(image_processor.original_hdul) > 0:
            header = image_processor.original_hdul[0].header
            if 'RADECSYS' in header:
                coord_system = header['RADECSYS']
            elif 'RADESYS' in header:
                coord_system = header['RADESYS']
                
            if 'EQUINOX' in header:
                equinox = header['EQUINOX']
            
            logging.info(f"从FITS头信息中提取坐标系统: {coord_system}, 分点: {equinox}")
        
        if wcs is None:
            # 如果没有WCS信息，尝试在线盲解
            try:
                if status_callback:
                    status_callback("Performing online plate solving...")
                with tempfile.NamedTemporaryFile(delete=False, suffix='.fits') as temp_file:
                    hdu = fits.PrimaryHDU(image_processor.image_data)
                    hdu.writeto(temp_file.name)
                    temp_path = temp_file.name
                
                # 尝试在线盲解
                logging.info("Starting online plate solving...")
                result = self.ast.solve_from_image(temp_path, force_image_upload=True)
                os.unlink(temp_path)
                
                if result:
                    logging.info("Plate solving successful, processing results...")
                    
                    # 记录头信息以便调试
                    header_keys = [k for k in result.keys()]
                    logging.debug(f"Header keys in result: {header_keys}")
                    
                    # 明确地提取CD矩阵，以确保使用准确的来自盲解的值
                    original_cd_matrix = None
                    if all(key in result for key in ['CD1_1', 'CD1_2', 'CD2_1', 'CD2_2']):
                        original_cd_matrix = {
                            'CD1_1': float(result['CD1_1']),
                            'CD1_2': float(result['CD1_2']),
                            'CD2_1': float(result['CD2_1']),
                            'CD2_2': float(result['CD2_2'])
                        }
                        logging.info(f"直接从盲解结果提取CD矩阵: {original_cd_matrix}")
                        
                        # 计算此CD矩阵对应的旋转角度
                        cd_rot_angle = np.degrees(np.arctan2(float(result['CD1_2']), float(result['CD1_1'])))
                        cd_rot_angle = (cd_rot_angle + 360) % 360
                        logging.info(f"从盲解CD矩阵计算的旋转角度: {cd_rot_angle:.2f}°")
                    else:
                        logging.warning("盲解结果中未找到完整的CD矩阵信息")
                    
                    # 从盲解结果创建WCS对象
                    # 创建一个只包含必要WCS关键字的新头信息，避免某些非标准关键字导致崩溃
                    clean_result = fits.Header()
                    
                    # 只保留WCS相关的关键字
                    wcs_keywords = [
                        'NAXIS', 'NAXIS1', 'NAXIS2',
                        'CTYPE1', 'CTYPE2',
                        'CRVAL1', 'CRVAL2',
                        'CRPIX1', 'CRPIX2',
                        'CDELT1', 'CDELT2',
                        'CUNIT1', 'CUNIT2',
                        'CD1_1', 'CD1_2', 'CD2_1', 'CD2_2',
                        'PC1_1', 'PC1_2', 'PC2_1', 'PC2_2',
                        'EQUINOX', 'LONPOLE', 'LATPOLE',
                        'RADESYS'
                    ]
                    
                    for key in wcs_keywords:
                        if key in result:
                            clean_result[key] = result[key]
                    
                    # 添加SIP相关关键字
                    sip_keywords = ['A_ORDER', 'B_ORDER', 'AP_ORDER', 'BP_ORDER']
                    for key in sip_keywords:
                        if key in result:
                            clean_result[key] = result[key]
                    
                    # 添加SIP系数
                    for key in result:
                        if key.startswith('A_') or key.startswith('B_') or key.startswith('AP_') or key.startswith('BP_'):
                            clean_result[key] = result[key]
                    
                    # 使用清理后的头信息创建WCS
                    wcs = WCS(clean_result, relax=True)
                    self.set_wcs(wcs)
                    image_processor.wcs = wcs
                    
                    # 将原始CD矩阵存储到图像处理器中，以便后续使用
                    image_processor.original_cd_matrix = original_cd_matrix
                    
                    # 验证WCS对象中的CD矩阵与我们直接提取的是否一致
                    if original_cd_matrix and hasattr(wcs, 'wcs') and hasattr(wcs.wcs, 'cd'):
                        wcs_cd = wcs.wcs.cd
                        logging.info(f"WCS对象中的CD矩阵: CD1_1={wcs_cd[0, 0]:.6e}, CD1_2={wcs_cd[0, 1]:.6e}, "
                                   f"CD2_1={wcs_cd[1, 0]:.6e}, CD2_2={wcs_cd[1, 1]:.6e}")
                        
                        # 计算差异以验证一致性
                        cd_diff = np.array([
                            abs(wcs_cd[0, 0] - original_cd_matrix['CD1_1']),
                            abs(wcs_cd[0, 1] - original_cd_matrix['CD1_2']),
                            abs(wcs_cd[1, 0] - original_cd_matrix['CD2_1']),
                            abs(wcs_cd[1, 1] - original_cd_matrix['CD2_2'])
                        ])
                        
                        if np.max(cd_diff) > 1e-8:
                            logging.warning(f"直接提取的CD矩阵与WCS对象中的不一致! 最大差异: {np.max(cd_diff):.6e}")
                        else:
                            logging.info("验证成功: 直接提取的CD矩阵与WCS对象中的一致")
                    
                    # astrometry.net特定处理：专门处理astrometry.net的结果格式
                    pixel_scale = None
                    
                    # 方法1: 直接从headers中提取
                    for key in result.keys():
                        logging.debug(f"Header key: {key}, Value: {result[key]}")
                    
                    # 方法2: 从CD或CDELT矩阵直接计算
                    # 通常astrometry.net返回CD矩阵
                    if all(key in result for key in ['CD1_1', 'CD1_2', 'CD2_1', 'CD2_2']):
                        try:
                            cd = np.array([
                                [float(result['CD1_1']), float(result['CD1_2'])],
                                [float(result['CD2_1']), float(result['CD2_2'])]
                            ])
                            # 像素比例是CD矩阵行列式的平方根
                            scale = np.sqrt(np.abs(np.linalg.det(cd))) * 3600.0
                            if scale > 0:
                                pixel_scale = scale
                                logging.info(f"Calculated pixel scale from CD matrix: {pixel_scale:.4f} arcsec/pixel")
                                if status_callback:
                                    status_callback(f"Using pixel scale from CD matrix: {pixel_scale:.4f} arcsec/pixel")
                        except Exception as e:
                            logging.warning(f"Failed to calculate pixel scale from CD matrix: {e}")
                    
                    # 方法3: 如果有CDELT值，使用它们
                    if pixel_scale is None and all(key in result for key in ['CDELT1', 'CDELT2']):
                        try:
                            cdelt1 = float(result['CDELT1'])
                            cdelt2 = float(result['CDELT2'])
                            scale = np.mean([abs(cdelt1), abs(cdelt2)]) * 3600.0
                            if scale > 0:
                                pixel_scale = scale
                                logging.info(f"Calculated pixel scale from CDELT values: {pixel_scale:.4f} arcsec/pixel")
                                if status_callback:
                                    status_callback(f"Using pixel scale from CDELT values: {pixel_scale:.4f} arcsec/pixel")
                        except Exception as e:
                            logging.warning(f"Failed to calculate pixel scale from CDELT values: {e}")
                    
                    # 方法4: 使用WCS对象的pixscale方法
                    if pixel_scale is None:
                        try:
                            # 使用astropy WCS的专用方法
                            if hasattr(wcs, 'pixel_scale_matrix'):
                                scale = np.mean(np.abs(np.diag(wcs.pixel_scale_matrix))) * 3600.0
                                if scale > 0:
                                    pixel_scale = scale
                                    logging.info(f"Using WCS pixel_scale_matrix: {pixel_scale:.4f} arcsec/pixel")
                                    if status_callback:
                                        status_callback(f"Using WCS pixel_scale_matrix: {pixel_scale:.4f} arcsec/pixel")
                        except Exception as e:
                            logging.warning(f"Failed to get pixel scale from WCS object: {e}")
                    
                    # 方法5: 测量具体点的距离
                    if pixel_scale is None:
                        try:
                            # 获取图像尺寸
                            height, width = image_processor.get_image_size()
                            # 使用图像中心和相邻点
                            center_x, center_y = width // 2, height // 2
                            
                            # 计算中心点和偏移1像素的点的天球距离
                            center_coord = wcs.pixel_to_world(center_x, center_y)
                            offset_coord = wcs.pixel_to_world(center_x + 1, center_y)
                            
                            # 计算角度距离（角秒）
                            sep_arcsec = center_coord.separation(offset_coord).arcsec
                            if sep_arcsec > 0:
                                pixel_scale = sep_arcsec
                                logging.info(f"Calculated pixel scale from point separation: {pixel_scale:.4f} arcsec/pixel")
                                if status_callback:
                                    status_callback(f"Calculated pixel scale from point separation: {pixel_scale:.4f} arcsec/pixel")
                        except Exception as e:
                            logging.warning(f"Failed to calculate pixel scale from point separation: {e}")
                    
                    # 方法6: 从图像尺寸和视场估算
                    if pixel_scale is None:
                        try:
                            # 如果头信息中包含视场信息
                            if 'IMAGEW' in result and 'IMAGEH' in result:
                                width = float(result['IMAGEW'])
                                height = float(result['IMAGEH'])
                                
                                # 如果包含视场角度信息
                                if 'WCSAXES' in result and result['WCSAXES'] == 2:
                                    # 尝试计算对角线长度（角度）
                                    corner1 = wcs.pixel_to_world(0, 0)
                                    corner2 = wcs.pixel_to_world(width-1, height-1)
                                    diagonal_deg = corner1.separation(corner2).deg
                                    
                                    # 图像对角线像素长度
                                    diagonal_pix = np.sqrt(width**2 + height**2)
                                    
                                    # 像素比例（角秒/像素）
                                    if diagonal_pix > 0:
                                        calc_scale = (diagonal_deg * 3600.0) / diagonal_pix
                                        if calc_scale > 0:
                                            pixel_scale = calc_scale
                                            logging.info(f"Estimated pixel scale from image dimensions: {pixel_scale:.4f} arcsec/pixel")
                                            if status_callback:
                                                status_callback(f"Estimated pixel scale from image dimensions: {pixel_scale:.4f} arcsec/pixel")
                        except Exception as e:
                            logging.warning(f"Failed to estimate pixel scale from image dimensions: {e}")
                    
                    # 最后兜底：使用固定的非零值
                    if pixel_scale is None or pixel_scale <= 0:
                        # 使用合理的默认值
                        pixel_scale = 1.0
                        logging.warning("Could not determine pixel scale, using default value of 1.0 arcsec/pixel")
                        if status_callback:
                            status_callback("Could not determine pixel scale, using default value of 1.0 arcsec/pixel")
                    
                    # 确保像素比例是有效的正数
                    if pixel_scale <= 0:
                        pixel_scale = 1.0
                        logging.warning("Calculated pixel scale was invalid, using default value of 1.0 arcsec/pixel")
                    
                    # 设置像素比例
                    self.set_pixel_scale(pixel_scale)
                    image_processor.pixel_scale = pixel_scale
                    
                    if status_callback:
                        status_callback(f"Online plate solving successful! Pixel scale: {pixel_scale:.4f} arcsec/pixel")
                else:
                    logging.warning("Online plate solving failed")
                    if status_callback:
                        status_callback("Online plate solving failed. Please check image quality or provide additional information.")
                    return {}
            except Exception as e:
                logging.error(f"Error during online plate solving: {e}")
                if status_callback:
                    status_callback(f"Error during online plate solving: {str(e)}")
                return {}
        else:
            # 如果有WCS信息，直接使用
            self.set_wcs(wcs)
            
            # 如果还没有设置坐标系统信息，尝试从WCS获取
            if not coord_system and hasattr(wcs, 'wcs'):
                if hasattr(wcs.wcs, 'radesys') and wcs.wcs.radesys:
                    coord_system = wcs.wcs.radesys
                if hasattr(wcs.wcs, 'equinox') and wcs.wcs.equinox:
                    equinox = wcs.wcs.equinox
                    
            # 如果头信息中没有像素比例，尝试从WCS计算
            if self.pixel_scale is None:
                wcs_pixel_scale = self.extract_pixel_scale_from_wcs(wcs)
                if wcs_pixel_scale:
                    self.set_pixel_scale(wcs_pixel_scale)
                    
            if status_callback:
                pixel_scale_msg = f" (Pixel scale: {self.pixel_scale:.4f} arcsec/pixel)" if self.pixel_scale else ""
                coord_sys_msg = f", 坐标系统: {coord_system}" if coord_system else ""
                status_callback(f"Successfully obtained coordinates from image WCS information!{pixel_scale_msg}{coord_sys_msg}")

        # 获取图像尺寸并计算中心坐标
        height, width = image_processor.get_image_size()
        center_x = width // 2
        center_y = height // 2
        
        # 将中心像素坐标转换为天球坐标
        center_coords = self.pixel_to_world(center_x, center_y)
        if center_coords is None:
            logging.error("Could not determine center coordinates")
            if status_callback:
                status_callback("Could not determine center coordinates")
            return {}
        
        # 检查WCS坐标的方向性
        wcs_info = self._detect_wcs_direction()
        logging.info(f"检测到的WCS方向: {wcs_info}")
        
        # 计算视场大小
        fov = self.calculate_field_of_view(width, height, self.pixel_scale)
        
        # 确保FOV正确无论方向如何
        # FOV[0]应为赤经方向(RA)，FOV[1]应为赤纬方向(DEC)
        # 由于calculate_field_of_view已经正确处理了cos(dec)修正
        # 所以这里不需要再次修正，只需确保顺序正确
        fov_width, fov_height = fov
        
        # 获取像素比例
        pixel_scale = self.pixel_scale
        if pixel_scale is None or pixel_scale <= 0:
            # 根据FOV和图像尺寸估算像素比例
            pixel_scale = max(fov_width, fov_height) * 3600.0 / max(width, height)
            if pixel_scale <= 0:
                pixel_scale = 1.0  # 使用默认值
            logging.info(f"Estimated pixel scale from FOV: {pixel_scale:.4f} arcsec/pixel")
            if status_callback:
                status_callback(f"Estimated pixel scale from FOV: {pixel_scale:.4f} arcsec/pixel")
            
            # 更新像素比例
            self.set_pixel_scale(pixel_scale)
        
        # 创建结果字典
        result = {
            "center_ra": center_coords.ra.deg,
            "center_dec": center_coords.dec.deg,
            "center_ra_hms": center_coords.ra.to_string(unit=u.hourangle),
            "center_dec_dms": center_coords.dec.to_string(unit=u.deg),
            "fov_width": fov_width,
            "fov_height": fov_height,
            "pixel_scale": pixel_scale,
            "image_width": width,
            "image_height": height,
            "wcs_direction": wcs_info,
            "coord_system": coord_system,
            "equinox": equinox
        }
        
        # 保存设置
        self.settings.update_setting("center_ra", result["center_ra"])
        self.settings.update_setting("center_dec", result["center_dec"])
        self.settings.update_setting("fov_width", result["fov_width"])
        self.settings.update_setting("fov_height", result["fov_height"])
        self.settings.update_setting("pixel_scale", result["pixel_scale"])
        
        logging.info(f"Coordinate parsing complete: RA={result['center_ra']:.4f}°, DEC={result['center_dec']:.4f}°, FOV={result['fov_width']:.4f}°×{result['fov_height']:.4f}°, Scale={result['pixel_scale']:.4f} arcsec/pixel, System={result['coord_system']}")
        return result
        
    def _detect_wcs_direction(self):
        """检测WCS坐标系的方向和旋转角度，以确定RA/DEC与图像的X/Y轴关系
        
        返回:
            dict: 包含以下信息:
                "type": "normal" - RA主要对应X轴，DEC主要对应Y轴
                       "flipped" - RA主要对应Y轴，DEC主要对应X轴
                       "complex" - 复杂情况（有旋转或其他变换）
                "rotation_angle": 旋转角度（度，0-360）
                "cd_matrix": CD矩阵
        """
        if self.wcs is None:
            logging.warning("无法检测WCS方向：WCS信息不可用")
            return {"type": "normal", "rotation_angle": 0, "cd_matrix": None}  # 默认为正常方向
        
        try:
            # 获取WCS变换矩阵的元素
            cd = self.wcs.wcs.cd if hasattr(self.wcs.wcs, 'cd') else None
            
            # 如果CD矩阵不可用，尝试从pc矩阵和cdelt计算
            if cd is None:
                try:
                    pc = self.wcs.wcs.pc
                    cdelt = self.wcs.wcs.cdelt
                    # 计算cd = pc * diag(cdelt)
                    cd = np.dot(pc, np.diag(cdelt))
                except Exception as e:
                    logging.warning(f"无法计算CD矩阵: {e}")
                    return {"type": "normal", "rotation_angle": 0, "cd_matrix": None}
            
            # 记录CD矩阵的值，便于调试
            cd_matrix = {
                'CD1_1': cd[0, 0],
                'CD1_2': cd[0, 1],
                'CD2_1': cd[1, 0],
                'CD2_2': cd[1, 1]
            }
            logging.info(f"WCS CD矩阵: CD1_1={cd[0, 0]:.6e}, CD1_2={cd[0, 1]:.6e}, "
                        f"CD2_1={cd[1, 0]:.6e}, CD2_2={cd[1, 1]:.6e}")
            
            # 判断主要分量值的大小
            cd1_1_abs = abs(cd[0, 0])
            cd1_2_abs = abs(cd[0, 1])
            cd2_1_abs = abs(cd[1, 0])
            cd2_2_abs = abs(cd[1, 1])
            
            # 计算旋转角度 (使用反正切函数)
            # 对于"正常"方向：RA主要沿X轴，则角度近似为 atan2(CD1_2, CD1_1)
            # 对于"翻转"方向：RA主要沿Y轴，则角度近似为 atan2(CD2_2, CD2_1) - 90°
            
            # 根据分量大小确定坐标系类型
            threshold = 0.1 * max(cd1_1_abs, cd1_2_abs, cd2_1_abs, cd2_2_abs)
            
            if (cd1_1_abs > threshold or cd1_2_abs > threshold) and (cd2_1_abs > threshold or cd2_2_abs > threshold):
                # 确定主要类型
                if (cd1_1_abs + cd2_2_abs) > (cd1_2_abs + cd2_1_abs):
                    wcs_type = "normal"
                    # 对于正常类型，RA主要沿X轴，使用CD1_1和CD1_2计算角度
                    rotation_angle = np.degrees(np.arctan2(cd[0, 1], cd[0, 0]))
                    # 确保角度在0-360范围内
                    rotation_angle = (rotation_angle + 360) % 360
                    logging.info(f"检测到正常WCS方向，旋转角度: {rotation_angle:.2f}°")
                else:
                    wcs_type = "flipped"
                    # 对于翻转类型，RA主要沿Y轴，使用CD2_1和CD2_2计算角度
                    rotation_angle = np.degrees(np.arctan2(cd[1, 1], cd[1, 0])) - 90
                    # 确保角度在0-360范围内
                    rotation_angle = (rotation_angle + 360) % 360
                    logging.info(f"检测到翻转WCS方向，旋转角度: {rotation_angle:.2f}°")
            else:
                wcs_type = "complex"
                # 对于复杂情况，使用两个方向的组合来估计
                angle1 = np.degrees(np.arctan2(cd[0, 1], cd[0, 0]))
                angle2 = np.degrees(np.arctan2(cd[1, 0], cd[1, 1])) + 90
                rotation_angle = (angle1 + angle2) / 2
                # 确保角度在0-360范围内
                rotation_angle = (rotation_angle + 360) % 360
                logging.info(f"检测到复杂WCS方向，估计旋转角度: {rotation_angle:.2f}°")
            
            # 特殊情况：当CD1_1和CD2_2都为负值时
            if cd[0, 0] < 0 and cd[1, 1] < 0:
                wcs_type = "flipped_both_axes"
                # 特殊处理这种情况的旋转角度
                rotation_angle = np.degrees(np.arctan2(-cd[0, 1], -cd[0, 0]))
                rotation_angle = (rotation_angle + 360) % 360
                logging.info(f"检测到双轴翻转WCS方向，旋转角度: {rotation_angle:.2f}°")
            
            return {
                "type": wcs_type,
                "rotation_angle": rotation_angle,
                "cd_matrix": cd_matrix
            }
        
        except Exception as e:
            logging.error(f"检测WCS方向时出错: {str(e)}")
            traceback.print_exc()
            return {"type": "normal", "rotation_angle": 0, "cd_matrix": None}

    def extract_pixel_scale_from_wcs(self, wcs):
        """从WCS对象中提取像素比例（角秒/像素）"""
        try:
            # 方法1: 使用像素比例矩阵
            try:
                if hasattr(wcs, 'pixel_scale_matrix'):
                    pixel_scale = abs(wcs.pixel_scale_matrix.diagonal().mean()) * 3600
                    if pixel_scale > 0:
                        return pixel_scale
            except Exception:
                pass
            
            # 方法2: 使用CDELT
            try:
                if hasattr(wcs, 'wcs') and hasattr(wcs.wcs, 'cdelt'):
                    cdelt = wcs.wcs.cdelt
                    if cdelt is not None and len(cdelt) >= 2:
                        scale = np.mean([abs(cdelt[0]), abs(cdelt[1])]) * 3600.0
                        if scale > 0:
                            return scale
            except Exception:
                pass
                
            # 方法3: 使用两个相距一定像素的点计算
            try:
                # 中心点和一个偏移点的天球距离
                center = wcs.pixel_to_world(500, 500)
                offset = wcs.pixel_to_world(501, 500)  # 偏移1像素
                
                # 两点之间的角距离（度）
                sep = center.separation(offset).arcsec  # 直接获取角秒
                
                # 像素比例就是每像素的角秒数
                if sep > 0:
                    return sep
            except Exception:
                pass
                
            # 所有方法都失败
            return None
        except Exception as e:
            logging.warning(f"Could not extract pixel scale from WCS: {e}")
            return None

    def calculate_field_of_view(self, width, height, pixel_scale_arcsec=None):
        """计算图像视场(FOV)，返回以度为单位的宽度和高度"""
        logging.info("计算图像FOV...")
        
        # 如果未提供像素比例，使用存储的值
        if pixel_scale_arcsec is None:
            pixel_scale_arcsec = self.pixel_scale
            if pixel_scale_arcsec is None:
                logging.warning("未提供像素比例，无法计算FOV")
                return None, None
        
        # 将像素比例从角秒转换为度
        pixel_scale_deg = pixel_scale_arcsec / 3600.0
        
        # 基本FOV计算 - 不考虑赤纬效应
        basic_fov_width = width * pixel_scale_deg
        basic_fov_height = height * pixel_scale_deg
        
        logging.info(f"基本FOV计算: {basic_fov_width:.6f}° × {basic_fov_height:.6f}°")
        
        # 如果有WCS信息，使用更精确的方法计算FOV
        if self.wcs:
            logging.info("使用WCS信息计算精确FOV")
            try:
                # 获取图像中心坐标
                center_x, center_y = width / 2, height / 2
                center_coords = self.wcs.pixel_to_world(center_x, center_y)
                
                # 计算赤纬的余弦值，用于调整赤经方向的FOV
                center_dec = center_coords.dec.deg
                cos_dec = np.cos(np.radians(center_dec))
                
                # 防止在极点附近除以接近零的值
                if abs(cos_dec) < 0.01:
                    cos_dec = 0.01 if cos_dec >= 0 else -0.01
                    logging.warning(f"赤纬接近极点: {center_dec}°，余弦值被限制为 {cos_dec}")
                
                # 基础FOV计算，不考虑赤纬效应
                fov_width = basic_fov_width
                fov_height = basic_fov_height
                
                logging.info(f"中心坐标赤纬: {center_dec}°, 余弦值: {cos_dec:.6f}")
                
                # 对于赤经方向，需要考虑赤纬的影响
                # 注意：赤经方向的实际角度需要乘以cos(dec)以转换为相同的天球弧度
                # 在大多数"正常"方向的WCS中，赤经通常对应于宽度
                # 但这取决于WCS的方向，我们将在_detect_wcs_direction和parse_coordinates中处理
                
                # 检测WCS的方向
                wcs_info = self._detect_wcs_direction()
                
                # 根据WCS方向应用cos(dec)修正
                if wcs_info["type"] == "normal":
                    # 正常情况：RA对应x轴，DEC对应y轴
                    fov_width = basic_fov_width * cos_dec  # RA方向应用修正
                    fov_height = basic_fov_height         # DEC方向保持不变
                    logging.info(f"正常WCS方向：应用cos(dec)到宽度/RA方向")
                elif wcs_info["type"] == "flipped":
                    # 翻转情况：RA对应y轴，DEC对应x轴
                    fov_width = basic_fov_width           # DEC方向保持不变
                    fov_height = basic_fov_height * cos_dec  # RA方向应用修正
                    logging.info(f"翻转WCS方向：应用cos(dec)到高度/RA方向")
                else:
                    # 未知或复杂情况
                    logging.warning(f"无法确定WCS方向，使用基本FOV计算")
                
                logging.info(f"最终FOV: {fov_width:.6f}° × {fov_height:.6f}°")
                return fov_width, fov_height
                
            except Exception as e:
                logging.error(f"使用WCS计算FOV时出错: {str(e)}")
                traceback.print_exc()
        
        # 如果没有WCS信息，或WCS计算失败
        # 仍然尝试应用cos(dec)修正（如果我们知道中心赤纬）
        center_dec = None
        if hasattr(self, 'metadata') and self.metadata:
            center_dec = self.metadata.get('center_dec')
        
        if center_dec is not None:
            try:
                # 应用赤纬修正到赤经/宽度
                cos_dec = np.cos(np.radians(center_dec))
                if abs(cos_dec) < 0.01:
                    cos_dec = 0.01 if cos_dec >= 0 else -0.01
                
                # 假设标准方向（赤经对应宽度）
                fov_width = basic_fov_width * cos_dec
                fov_height = basic_fov_height
                logging.info(f"应用赤纬修正，中心赤纬: {center_dec}°, 修正后FOV: {fov_width:.6f}° × {fov_height:.6f}°")
                return fov_width, fov_height
            except Exception as e:
                logging.error(f"应用赤纬修正时出错: {str(e)}")
        
        # 如果所有尝试都失败，返回基本计算结果
        logging.info(f"使用基本FOV计算（无赤纬修正）: {basic_fov_width:.6f}° × {basic_fov_height:.6f}°")
        return basic_fov_width, basic_fov_height


class GaiaDatabase:
    def __init__(self, db_path):
        self.database_path = db_path
        self.cached_data = None
        self.current_region = None

    def connect_to_database(self):
        return os.path.exists(self.database_path) if os.name == 'nt' else False

    def get_region_path(self, ra, dec):
        hemisphere = "N" if dec >= 0 else "S"
        dec_folder = abs(int(dec))
        region = f"de_{hemisphere}{dec_folder:03d}"
        return os.path.join(self.database_path, region)

    def query_by_coordinates(self, ra, dec, radius):
        region_path = self.get_region_path(ra, dec)
        self.current_region = region_path
        # 模拟数据，实际应用中应连接真实数据库
        n_stars = np.random.randint(20, 100)
        random_offsets = np.random.normal(0, radius / 2, (n_stars, 2))
        ra_values = ra + random_offsets[:, 0]
        dec_values = dec + random_offsets[:, 1]
        g_mag = np.random.uniform(10, 20, n_stars)
        bp_mag = g_mag + np.random.normal(0, 0.2, n_stars)
        rp_mag = g_mag + np.random.normal(0, 0.2, n_stars)
        pmra = np.random.normal(0, 5, n_stars)
        pmdec = np.random.normal(0, 5, n_stars)
        parallax = np.random.uniform(0.1, 10, n_stars)
        self.cached_data = pd.DataFrame({
            "source_id": np.arange(1, n_stars + 1),
            "ra": ra_values,
            "dec": dec_values,
            "parallax": parallax,
            "pmra": pmra,
            "pmdec": pmdec,
            "phot_g_mean_mag": g_mag,
            "phot_bp_mean_mag": bp_mag,
            "phot_rp_mean_mag": rp_mag,
        })
        return self.cached_data

    def query_by_region(self, region):
        # 模拟查询区域内的数据
        n_stars = np.random.randint(50, 200)
        ra_range = np.random.uniform(0, 360)
        dec_range = np.random.uniform(-90, 90)
        ra_values = np.random.uniform(ra_range - 5, ra_range + 5, n_stars)
        dec_values = np.random.uniform(dec_range - 5, dec_range + 5, n_stars)
        g_mag = np.random.uniform(10, 20, n_stars)
        bp_mag = g_mag + np.random.normal(0, 0.2, n_stars)
        rp_mag = g_mag + np.random.normal(0, 0.2, n_stars)
        pmra = np.random.normal(0, 5, n_stars)
        pmdec = np.random.normal(0, 5, n_stars)
        parallax = np.random.uniform(0.1, 10, n_stars)
        self.cached_data = pd.DataFrame({
            "source_id": np.arange(1, n_stars + 1),
            "ra": ra_values,
            "dec": dec_values,
            "parallax": parallax,
            "pmra": pmra,
            "pmdec": pmdec,
            "phot_g_mean_mag": g_mag,
            "phot_bp_mean_mag": bp_mag,
            "phot_rp_mean_mag": rp_mag,
        })
        return self.cached_data

    def get_catalog_metadata(self):
        return {
            "name": "Gaia DR3 Simulated Data",
            "description": "This is simulated Gaia DR3 data for demonstration purposes.",
            "version": "3.0",
            "total_stars": "Approximately 100 million (simulated)",
        }


def save_parsed_coordinates_to_fits(image_processor, parser_result, output_path=None):
    if not image_processor or not parser_result:
        return False, "No image or parsing results to save"

    try:
        if not output_path:
            original_name = image_processor.original_filename
            if original_name:
                base_name = os.path.splitext(original_name)[0]
                output_path = f"{base_name}_wcs.fits"
            else:
                output_path = "output_wcs.fits"
        
        # 创建原始FITS文件的副本
        if image_processor.original_hdul:
            try:
                # 检查HDU是否已关闭，如果已关闭则使用image_data
                if hasattr(image_processor.original_hdul, '_file') and image_processor.original_hdul._file is None:
                    # HDU已关闭，使用image_data创建新的HDU
                    hdu = fits.PrimaryHDU(data=image_processor.image_data)
                    # 尝试从缓存中获取原始header
                    if hasattr(image_processor, 'original_header') and image_processor.original_header:
                        for key, value in image_processor.original_header.items():
                            if key not in hdu.header:
                                hdu.header[key] = value
                else:
                    # HDU未关闭，正常使用
                    original_hdul = image_processor.original_hdul
                    hdu = fits.PrimaryHDU(data=original_hdul[0].data, header=original_hdul[0].header.copy())
            except Exception as e:
                logging.warning(f"无法使用original_hdul，使用image_data创建HDU: {e}")
                hdu = fits.PrimaryHDU(data=image_processor.image_data)
        else:
            # 如果没有原始HDU列表，创建一个新的
            hdu = fits.PrimaryHDU(data=image_processor.image_data)
        
        # 获取原始坐标系统信息
        header = hdu.header
        
        # 优先从原始FITS头文件中提取坐标系统和CD矩阵信息
        coord_system = None
        equinox = None
        cd_matrix = None
        
        # 检查是否有直接从盲解结果提取的CD矩阵
        if hasattr(image_processor, 'original_cd_matrix') and image_processor.original_cd_matrix:
            cd_matrix = image_processor.original_cd_matrix
            logging.info(f"使用直接从盲解/原始FITS提取的CD矩阵: {cd_matrix}")
        
        # 如果没有直接提取的矩阵，尝试从原始FITS头文件中获取
        if not cd_matrix:
            # 优先使用 original_header（如果存在）
            if hasattr(image_processor, 'original_header') and image_processor.original_header:
                orig_header = image_processor.original_header
            elif image_processor.original_hdul:
                orig_header = image_processor.original_hdul[0].header
            else:
                orig_header = None
            
            if orig_header:
                # 获取坐标系统
                if 'RADECSYS' in orig_header:
                    coord_system = orig_header['RADECSYS']
                elif 'RADESYS' in orig_header:
                    coord_system = orig_header['RADESYS']
                    
                # 获取分点
                if 'EQUINOX' in orig_header:
                    equinox = orig_header['EQUINOX']
                
                # 尝试获取原始CD矩阵
                if all(key in orig_header for key in ['CD1_1', 'CD1_2', 'CD2_1', 'CD2_2']):
                    cd_matrix = {
                        'CD1_1': orig_header['CD1_1'],
                        'CD1_2': orig_header['CD1_2'],
                        'CD2_1': orig_header['CD2_1'],
                        'CD2_2': orig_header['CD2_2']
                    }
                    logging.info(f"从原始FITS头文件获取CD矩阵: {cd_matrix}")
        
        # 如果没有从FITS头文件中获取到，使用解析结果中的值
        if not coord_system:
            coord_system = parser_result.get("coord_system")
        if not equinox:
            equinox = parser_result.get("equinox")
            
        # 仍然没有，使用FK5/J2000作为默认值
        if not coord_system:
            coord_system = 'FK5'
        if not equinox:
            equinox = 2000.0
        
        logging.info(f"保存WCS信息，使用坐标系统: {coord_system}, 分点: {equinox}")
        
        # 基本WCS信息
        header['CTYPE1'] = 'RA---TAN'
        header['CTYPE2'] = 'DEC--TAN'
        
        # 中心坐标
        header['CRVAL1'] = parser_result.get("center_ra", 0)
        header['CRVAL2'] = parser_result.get("center_dec", 0)
        
        # 图像尺寸
        width = parser_result.get("image_width", 0)
        height = parser_result.get("image_height", 0)
        
        # 参考像素（通常是中心）
        header['CRPIX1'] = width / 2
        header['CRPIX2'] = height / 2
        
        # 像素比例（度/像素）
        pixel_scale_deg = parser_result.get("pixel_scale", 0) / 3600.0  # 转换为度
        
        # 获取WCS方向和旋转信息
        wcs_info = parser_result.get("wcs_direction", {"type": "normal", "rotation_angle": 0, "cd_matrix": None})
        
        # 如果wcs_direction只是一个字符串（旧格式），转换为新格式
        if isinstance(wcs_info, str):
            wcs_info = {
                "type": wcs_info,
                "rotation_angle": 0,
                "cd_matrix": None
            }
        
        # 设置CD矩阵
        if cd_matrix:
            # 使用原始CD矩阵，但需要缩放以匹配新的像素比例
            # 计算缩放因子
            orig_pixel_scale = np.sqrt(abs(cd_matrix['CD1_1'] * cd_matrix['CD2_2'] - 
                                         cd_matrix['CD1_2'] * cd_matrix['CD2_1']))
            if orig_pixel_scale <= 1e-10:
                logging.warning(f"原始CD矩阵行列式接近零: {orig_pixel_scale:.6e}，使用默认缩放因子1.0")
                scale_factor = 1.0
            else:
                scale_factor = pixel_scale_deg / orig_pixel_scale
            
            # 应用缩放
            header['CD1_1'] = cd_matrix['CD1_1'] * scale_factor
            header['CD1_2'] = cd_matrix['CD1_2'] * scale_factor
            header['CD2_1'] = cd_matrix['CD2_1'] * scale_factor
            header['CD2_2'] = cd_matrix['CD2_2'] * scale_factor
            
            logging.info(f"使用缩放后的原始CD矩阵: 缩放因子={scale_factor:.4f}")
            
            # 计算并记录旋转角度，用于验证
            cd_rot_angle = np.degrees(np.arctan2(cd_matrix['CD1_2'], cd_matrix['CD1_1']))
            cd_rot_angle = (cd_rot_angle + 360) % 360
            logging.info(f"应用的CD矩阵对应的旋转角度: {cd_rot_angle:.2f}°")
        elif wcs_info["cd_matrix"]:
            # 使用从WCS检测到的CD矩阵
            # 缩放CD矩阵以匹配期望的像素比例
            orig_cd = wcs_info["cd_matrix"]
            orig_pixel_scale = np.sqrt(abs(orig_cd['CD1_1'] * orig_cd['CD2_2'] - 
                                         orig_cd['CD1_2'] * orig_cd['CD2_1']))
            if orig_pixel_scale <= 1e-10:
                logging.warning(f"WCS检测到的CD矩阵行列式接近零: {orig_pixel_scale:.6e}，使用默认缩放因子1.0")
                scale_factor = 1.0
            else:
                scale_factor = pixel_scale_deg / orig_pixel_scale
            
            header['CD1_1'] = orig_cd['CD1_1'] * scale_factor
            header['CD1_2'] = orig_cd['CD1_2'] * scale_factor
            header['CD2_1'] = orig_cd['CD2_1'] * scale_factor
            header['CD2_2'] = orig_cd['CD2_2'] * scale_factor
            
            logging.info(f"使用从WCS检测到的CD矩阵，缩放因子={scale_factor:.4f}")
            
            # 计算并记录旋转角度，用于验证
            cd_rot_angle = np.degrees(np.arctan2(orig_cd['CD1_2'], orig_cd['CD1_1']))
            cd_rot_angle = (cd_rot_angle + 360) % 360
            logging.info(f"应用的CD矩阵对应的旋转角度: {cd_rot_angle:.2f}°")
        else:
            # 如果没有CD矩阵信息，根据WCS类型和旋转角度创建一个
            rotation_angle = wcs_info.get("rotation_angle", 0)
            wcs_type = wcs_info.get("type", "normal")
            
            # 将旋转角度转换为弧度
            theta = np.radians(rotation_angle)
            
            if wcs_type == "normal":
                # 正常方向：创建考虑旋转的CD矩阵
                header['CD1_1'] = pixel_scale_deg * np.cos(theta)
                header['CD1_2'] = pixel_scale_deg * np.sin(theta)
                header['CD2_1'] = -pixel_scale_deg * np.sin(theta)
                header['CD2_2'] = -pixel_scale_deg * np.cos(theta)
                logging.info(f"正常WCS方向，旋转角度={rotation_angle:.2f}°，创建对应的CD矩阵")
            elif wcs_type == "flipped":
                # 翻转方向：RA与Y轴对齐，DEC与X轴对齐
                # 需要添加90度旋转并可能翻转符号
                theta_adjusted = theta + np.radians(90)
                header['CD1_1'] = pixel_scale_deg * np.sin(theta_adjusted)
                header['CD1_2'] = pixel_scale_deg * np.cos(theta_adjusted)
                header['CD2_1'] = -pixel_scale_deg * np.cos(theta_adjusted)
                header['CD2_2'] = pixel_scale_deg * np.sin(theta_adjusted)
                logging.info(f"翻转WCS方向，旋转角度={rotation_angle:.2f}°，创建对应的CD矩阵")
            elif wcs_type == "flipped_both_axes":
                # 当两个轴都翻转时，保持CD矩阵的原始符号
                header['CD1_1'] = -pixel_scale_deg * np.cos(theta)
                header['CD1_2'] = -pixel_scale_deg * np.sin(theta)
                header['CD2_1'] = -pixel_scale_deg * np.sin(theta)
                header['CD2_2'] = -pixel_scale_deg * np.cos(theta)
                logging.info(f"双轴翻转WCS方向，旋转角度={rotation_angle:.2f}°，创建对应的CD矩阵")
            else:
                # 复杂情况，使用简单的旋转矩阵
                header['CD1_1'] = pixel_scale_deg * np.cos(theta)
                header['CD1_2'] = pixel_scale_deg * np.sin(theta)
                header['CD2_1'] = -pixel_scale_deg * np.sin(theta)
                header['CD2_2'] = -pixel_scale_deg * np.cos(theta)
                logging.info(f"复杂WCS方向，使用旋转角度={rotation_angle:.2f}°创建近似CD矩阵")
        
        # 为了兼容性，同时提供CDELT值
        # 注意：CDELT与CD矩阵冗余，但许多软件仍然使用CDELT
        header['CDELT1'] = pixel_scale_deg
        header['CDELT2'] = -pixel_scale_deg
        
        # 设置坐标系统信息 - 使用两种标准关键字以确保兼容性
        header['RADESYS'] = coord_system
        header['RADECSYS'] = coord_system
        header['EQUINOX'] = equinox
        
        # 保存FITS文件
        hdu.writeto(output_path, overwrite=True)
        logging.info(f"成功保存FITS文件: {output_path}")
        return True, output_path
    except Exception as e:
        error_msg = f"Error saving FITS file: {str(e)}"
        logging.error(error_msg)
        traceback.print_exc()
        return False, error_msg


class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MatplotlibCanvas, self).__init__(self.fig)
        self.setParent(parent)


class PlotlyWidget(QWidget):
    def __init__(self, parent=None):
        super(PlotlyWidget, self).__init__(parent)
        self.web_view = QWebEngineView()
        layout = QVBoxLayout()
        layout.addWidget(self.web_view)
        self.setLayout(layout)
        
    def plot(self, fig):
        raw_html = '<html><head><meta charset="utf-8" /></head><body>'
        raw_html += fig.to_html(include_plotlyjs='cdn')
        raw_html += '</body></html>'
        self.web_view.setHtml(raw_html)


class ImageViewerWidget(QWidget):
    def __init__(self, parent=None):
        super(ImageViewerWidget, self).__init__(parent)
        self.image_canvas = MatplotlibCanvas(self)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.image_canvas)
        self.setLayout(self.layout)
        
    def display_image(self, image_data, cmap='gray'):
        self.image_canvas.axes.clear()
        self.image_canvas.axes.imshow(image_data, cmap=cmap)
        self.image_canvas.axes.axis('off')
        self.image_canvas.draw()


class DataTableWidget(QWidget):
    def __init__(self, parent=None):
        super(DataTableWidget, self).__init__(parent)
        self.layout = QVBoxLayout()
        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
        
    def set_data(self, dataframe):
        if dataframe is None or dataframe.empty:
            return
        
        # 设置表格行数和列数
        self.table.setRowCount(len(dataframe))
        self.table.setColumnCount(len(dataframe.columns))
        
        # 设置表头
        headers = dataframe.columns.tolist()
        self.table.setHorizontalHeaderLabels(headers)
        
        # 填充数据
        for i, row in enumerate(dataframe.itertuples()):
            for j, value in enumerate(row[1:]):  # 跳过索引
                item = QTableWidgetItem(str(value))
                self.table.setItem(i, j, item)
        
        # 自适应列宽
        self.table.resizeColumnsToContents()


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("天文图像分析工具")
        self.resize(1200, 800)
        
        # 初始化应用组件
        self.settings_manager = SettingsManager()
        self.image_processor = FitsImageProcessor()
        self.coord_parser = CoordinateParser(self.settings_manager)
        self.gaia_db = GaiaDatabase(self.settings_manager.get_setting("database_path"))
        
        # 设置UI
        self.setup_ui()
        
        # 状态变量
        self.current_results = None
        self.current_dataframe = None
        
    def setup_ui(self):
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        self.central_widget.setLayout(main_layout)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        self.load_button = QPushButton("Load FITS")
        self.load_button.clicked.connect(self.load_fits_file)
        toolbar_layout.addWidget(self.load_button)
        
        self.parse_button = QPushButton("Parse Coordinates")
        self.parse_button.clicked.connect(self.parse_coordinates)
        self.parse_button.setEnabled(False)
        toolbar_layout.addWidget(self.parse_button)
        
        self.query_button = QPushButton("Query Catalog")
        self.query_button.clicked.connect(self.query_catalog)
        self.query_button.setEnabled(False)
        toolbar_layout.addWidget(self.query_button)
        
        self.save_button = QPushButton("Save FITS (with WCS)")
        self.save_button.clicked.connect(self.save_fits_with_wcs)
        self.save_button.setEnabled(False)
        toolbar_layout.addWidget(self.save_button)
        
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)
        
        # 主要内容
        content_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：图像和坐标信息
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 图像显示
        self.image_viewer = ImageViewerWidget()
        left_layout.addWidget(self.image_viewer)
        
        # 坐标信息
        self.coords_group = QGroupBox("Coordinate Information")
        coords_layout = QFormLayout()
        self.ra_label = QLabel("RA: --")
        self.dec_label = QLabel("DEC: --")
        self.fov_label = QLabel("FOV: -- x --")
        self.pixel_scale_label = QLabel("Pixel Scale: --")
        self.wcs_direction_label = QLabel("WCS Direction: --")
        self.rotation_angle_label = QLabel("Rotation Angle: --")
        coords_layout.addRow("Right Ascension:", self.ra_label)
        coords_layout.addRow("Declination:", self.dec_label)
        coords_layout.addRow("Field of View:", self.fov_label)
        coords_layout.addRow("Pixel Scale:", self.pixel_scale_label)
        coords_layout.addRow("WCS Direction:", self.wcs_direction_label)
        coords_layout.addRow("Rotation Angle:", self.rotation_angle_label)
        self.coords_group.setLayout(coords_layout)
        left_layout.addWidget(self.coords_group)
        
        # 右侧：数据表和绘图
        right_widget = QTabWidget()
        
        # 数据表页
        self.data_table = DataTableWidget()
        right_widget.addTab(self.data_table, "Data Table")
        
        # 绘图页
        self.plotly_widget = PlotlyWidget()
        right_widget.addTab(self.plotly_widget, "Plots")
        
        # 头信息页
        self.header_text = QTextEdit()
        self.header_text.setReadOnly(True)
        right_widget.addTab(self.header_text, "FITS Header")
        
        # 添加到分割器
        content_splitter.addWidget(left_widget)
        content_splitter.addWidget(right_widget)
        content_splitter.setSizes([400, 800])
        
        main_layout.addWidget(content_splitter)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def load_fits_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open FITS File", "", "FITS Files (*.fits *.fit *.fts);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        success = self.image_processor.load_fits(file_path)
        if success:
            # 显示图像
            norm_image = self.image_processor.normalize_image_for_display()
            if norm_image is not None:
                self.image_viewer.display_image(norm_image)
            
            # 显示头信息
            header_info = self.image_processor.get_header_info()
            header_text = "\n".join([f"{key} = {value}" for key, value in header_info.items()])
            self.header_text.setText(header_text)
            
            # 更新UI状态
            self.parse_button.setEnabled(True)
            self.status_bar.showMessage(f"FITS file loaded: {file_path}")
        else:
            self.status_bar.showMessage("Failed to load FITS file")
    
    def parse_coordinates(self):
        # 添加更详细的日志记录，帮助诊断问题
        logging.info(f"解析坐标 - 图像数据状态: {self.image_processor.image_data is not None}")
        
        if self.image_processor.image_data is None:
            QMessageBox.warning(self, "Warning", "Please load a FITS file first")
            return
        
        def status_callback(msg):
            self.status_bar.showMessage(msg)
            QApplication.processEvents()
        
        results = self.coord_parser.parse_image_coordinates(self.image_processor, status_callback)
        if results:
            # 输出详细的CD矩阵信息，用于调试
            if hasattr(self.image_processor, 'original_cd_matrix') and self.image_processor.original_cd_matrix:
                cd_matrix = self.image_processor.original_cd_matrix
                logging.info(f"已存储的CD矩阵: {cd_matrix}")
                cd_rot_angle = np.degrees(np.arctan2(cd_matrix['CD1_2'], cd_matrix['CD1_1']))
                cd_rot_angle = (cd_rot_angle + 360) % 360
                logging.info(f"CD矩阵对应的旋转角度: {cd_rot_angle:.2f}°")
            else:
                logging.info("未找到直接提取的CD矩阵信息")
                
            # 检查WCS中的CD矩阵
            wcs = self.image_processor.get_wcs()
            if wcs and hasattr(wcs, 'wcs') and hasattr(wcs.wcs, 'cd'):
                wcs_cd = wcs.wcs.cd
                logging.info(f"WCS对象中的CD矩阵: CD1_1={wcs_cd[0, 0]:.6e}, CD1_2={wcs_cd[0, 1]:.6e}, "
                           f"CD2_1={wcs_cd[1, 0]:.6e}, CD2_2={wcs_cd[1, 1]:.6e}")
                wcs_rot_angle = np.degrees(np.arctan2(wcs_cd[0, 1], wcs_cd[0, 0]))
                wcs_rot_angle = (wcs_rot_angle + 360) % 360
                logging.info(f"WCS对象中CD矩阵对应的旋转角度: {wcs_rot_angle:.2f}°")
                
            # 更新坐标信息显示
            self.ra_label.setText(f"{results['center_ra']:.6f}° ({results['center_ra_hms']})")
            self.dec_label.setText(f"{results['center_dec']:.6f}° ({results['center_dec_dms']})")
            
            # 获取FOV信息
            fov_width = results['fov_width']
            fov_height = results['fov_height']
            
            # 确保显示正确的FOV，RA作为宽度，DEC作为高度
            self.fov_label.setText(f"{fov_width:.4f}° (RA) × {fov_height:.4f}° (DEC)")
            self.pixel_scale_label.setText(f"{results['pixel_scale']:.4f} arcsec/pixel")
            
            # 获取坐标系统信息
            coord_system = results.get('coord_system', 'FK5')  # 默认FK5
            equinox = results.get('equinox', 2000.0)  # 默认J2000
            
            # 检查WCS方向和旋转角度
            wcs_info = results.get('wcs_direction', {})
            if isinstance(wcs_info, dict):
                wcs_type = wcs_info.get('type', 'normal')
                rotation_angle = wcs_info.get('rotation_angle', 0)
                # 更新WCS方向和旋转角度标签
                self.wcs_direction_label.setText(f"{wcs_type}")
                self.rotation_angle_label.setText(f"{rotation_angle:.2f}°")
                direction_info = f" (WCS方向: {wcs_type}, 旋转角度: {rotation_angle:.2f}°)" if wcs_type != 'normal' or rotation_angle > 0.1 else ""
            else:
                # 向后兼容旧格式
                self.wcs_direction_label.setText(f"{wcs_info}")
                self.rotation_angle_label.setText("未知")
                direction_info = f" (WCS方向: {wcs_info})" if wcs_info != 'normal' else ""
            
            # 构建详细的状态信息
            status_msg = f"坐标系统: {coord_system}{'/J'+str(equinox) if equinox else ''}, "
            status_msg += f"中心: RA={results['center_ra']:.4f}°, DEC={results['center_dec']:.4f}°, "
            status_msg += f"FOV: {fov_width:.4f}° (RA) × {fov_height:.4f}° (DEC){direction_info}, "
            status_msg += f"像素比例: {results['pixel_scale']:.4f} arcsec/pixel"
            
            # 保存结果并更新UI状态
            self.current_results = results
            self.query_button.setEnabled(True)
            self.save_button.setEnabled(True)
            self.status_bar.showMessage(f"坐标解析成功 - {status_msg}")
            
            # 输出更详细的日志信息，用于调试
            logging.info(f"完整坐标解析结果: {results}")
        else:
            self.status_bar.showMessage("坐标解析失败")
    
    def query_catalog(self):
        if not self.current_results:
            QMessageBox.warning(self, "Warning", "Please parse coordinates first")
            return
        
        ra = self.current_results["center_ra"]
        dec = self.current_results["center_dec"]
        radius = self.settings_manager.get_setting("search_radius")
        
        self.status_bar.showMessage(f"Querying catalog (RA={ra:.4f}, DEC={dec:.4f}, radius={radius}°)...")
        QApplication.processEvents()
        
        try:
            df = self.gaia_db.query_by_coordinates(ra, dec, radius)
            if df is not None and not df.empty:
                # 显示数据表
                self.data_table.set_data(df)
                
                # 创建绘图
                fig = make_subplots(rows=1, cols=2, 
                                    subplot_titles=("Sky Distribution", "HR Diagram"))
                
                # 天球分布图
                fig.add_trace(
                    go.Scatter(
                        x=df['ra'], 
                        y=df['dec'], 
                        mode='markers',
                        marker=dict(
                            size=10,
                            color=df['phot_g_mean_mag'],
                            colorscale='Viridis',
                            showscale=True,
                            colorbar=dict(title="G magnitude")
                        ),
                        text=df['source_id'],
                        hovertemplate='ID: %{text}<br>RA: %{x:.6f}<br>DEC: %{y:.6f}<br>G: %{marker.color:.2f}',
                    ),
                    row=1, col=1
                )
                
                # HR图
                fig.add_trace(
                    go.Scatter(
                        x=df['phot_bp_mean_mag'] - df['phot_rp_mean_mag'],
                        y=df['phot_g_mean_mag'],
                        mode='markers',
                        marker=dict(
                            size=8,
                            color=df['parallax'],
                            colorscale='Cividis',
                            showscale=True,
                            colorbar=dict(title="Parallax (mas)")
                        ),
                        text=df['source_id'],
                        hovertemplate='ID: %{text}<br>BP-RP: %{x:.2f}<br>G: %{y:.2f}<br>Parallax: %{marker.color:.4f}',
                    ),
                    row=1, col=2
                )
                
                # 设置轴标签
                fig.update_xaxes(title_text="RA (deg)", row=1, col=1)
                fig.update_yaxes(title_text="DEC (deg)", row=1, col=1)
                fig.update_xaxes(title_text="BP-RP", row=1, col=2)
                fig.update_yaxes(title_text="G magnitude", row=1, col=2)
                fig.update_yaxes(autorange="reversed", row=1, col=2)  # HR图y轴反向
                
                # 布局设置
                fig.update_layout(
                    title=f"Gaia DR3 Results (RA={ra:.4f}°, DEC={dec:.4f}°, radius={radius}°)",
                    height=600,
                    width=1000,
                )
                
                # 在plotly widget中显示
                self.plotly_widget.plot(fig)
                
                # 保存dataframe
                self.current_dataframe = df
                self.status_bar.showMessage(f"Query successful, found {len(df)} stars")
            else:
                self.status_bar.showMessage("Query returned no results")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error querying catalog: {str(e)}")
            self.status_bar.showMessage("Catalog query failed")
    
    def save_fits_with_wcs(self):
        if not self.current_results or self.image_processor.image_data is None:
            QMessageBox.warning(self, "Warning", "No data to save")
            return
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save FITS File", "", "FITS Files (*.fits);;All Files (*.*)"
        )
        
        if not save_path:
            return
        
        success, message = save_parsed_coordinates_to_fits(
            self.image_processor, self.current_results, save_path
        )
        
        if success:
            QMessageBox.information(self, "Success", f"FITS file saved to: {message}")
            self.status_bar.showMessage(f"FITS file saved")
        else:
            QMessageBox.critical(self, "Error", f"Error saving file: {message}")
            self.status_bar.showMessage("Failed to save file")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())