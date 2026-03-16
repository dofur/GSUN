# -*- coding: utf-8 -*-
"""
坐标解析模块 - Coordinate Parser

作者：Guoyou Sun (孙国佑) - 天体收藏家
软件：星视 GSUN View V4.0
网站：sunguoyou.lamost.org
标识：546756
原创作品，禁止商业使用
"""

import os
import logging
import tempfile
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
from astroquery.astrometry_net import AstrometryNet
import traceback

def parse_single_coordinate_string(coord_str):
    """
    从单个字符串中自动识别并解析RA和DEC坐标
    
    支持以下格式：
    - 空格分隔: "12:34:56.7 +12:34:56.7"
    - 逗号分隔: "12:34:56.7,+12:34:56.7"
    - 多种格式组合: "12h34m56.7s +12d34m56.7s"
    - 度数格式: "123.45 -45.67"
    
    参数：
        coord_str (str): 包含RA和DEC的字符串
        
    返回：
        tuple: (ra_deg, dec_deg) 赤经和赤纬的度数值
    """
    import re
    
    try:
        # 移除首尾空白
        coord_str = coord_str.strip()
        
        # 尝试使用正则表达式分割RA和DEC
        # 匹配模式：第一个可能是负号或数字，后面跟着各种分隔符
        patterns = [
            r'([+-]?[^,]+?)\s*,\s*([+-]?.+)',  # 逗号分隔
            r'([+-]?[^+-]+?)\s+([+-].+)',  # 空格分隔，DEC有符号
            r'([+-]?[^+-]+?)\s+([+-]?.+)',  # 空格分隔
        ]
        
        for pattern in patterns:
            match = re.match(pattern, coord_str)
            if match:
                ra_text = match.group(1).strip()
                dec_text = match.group(2).strip()
                
                # 验证DEC是否包含符号，如果没有则可能是RA的一部分
                if not dec_text.startswith(('+', '-')):
                    # 尝试重新分割：找到第一个负号
                    neg_pos = coord_str.find('-')
                    if neg_pos > 0:
                        ra_text = coord_str[:neg_pos].strip()
                        dec_text = coord_str[neg_pos:].strip()
                    else:
                        # 找到第一个正号
                        plus_pos = coord_str.find('+', 1)  # 跳过第一个字符
                        if plus_pos > 0:
                            ra_text = coord_str[:plus_pos].strip()
                            dec_text = coord_str[plus_pos:].strip()
                
                # 使用现有的parse_ra_dec_coordinates函数解析
                return parse_ra_dec_coordinates(ra_text, dec_text)
        
        # 如果所有模式都失败，尝试直接使用SkyCoord解析整个字符串
        try:
            coord = SkyCoord(coord_str, unit=(u.hourangle, u.deg))
            return coord.ra.deg, coord.dec.deg
        except Exception:
            try:
                coord = SkyCoord(coord_str, unit=(u.deg, u.deg))
                return coord.ra.deg, coord.dec.deg
            except Exception:
                pass
        
        raise ValueError(f"无法解析坐标字符串: '{coord_str}'")
    
    except Exception as e:
        logging.error(f"解析坐标字符串时出错: {str(e)}")
        raise ValueError(f"无法解析坐标字符串: '{coord_str}', 错误: {str(e)}")


def parse_ra_dec_coordinates(ra_text, dec_text):
    """
    解析赤经赤纬坐标文本，转换为度数值
    
    支持以下格式：
    - 度数格式：如 "123.45" 或 "-45.67"
    - 时分秒格式：如 "12h 34m 56.7s" 或 "12:34:56.7"
    - 度分秒格式：如 "+12° 34' 56.7\"" 或 "-12° 34' 56.7\""
    
    参数：
        ra_text (str): 赤经文本
        dec_text (str): 赤纬文本
        
    返回：
        tuple: (ra_deg, dec_deg) 赤经和赤纬的度数值
    """
    try:
        # 尝试直接解析为度数
        try:
            ra_deg = float(ra_text)
            dec_deg = float(dec_text)
            return ra_deg, dec_deg
        except ValueError:
            pass
        
        # 使用astropy的SkyCoord解析各种格式
        # 首先尝试解析赤经为时分秒格式
        ra_formats = [
            ra_text,  # 原始格式
            ra_text.replace('h', ':').replace('m', ':').replace('s', ''),  # 12h 34m 56.7s -> 12:34:56.7
            ra_text.replace('：', ':')  # 处理中文冒号
        ]
        
        # 尝试解析赤纬为度分秒格式
        dec_formats = [
            dec_text,  # 原始格式
            dec_text.replace('°', ':').replace('\'', ':').replace('"', ''),  # +12° 34' 56.7" -> +12:34:56.7
            dec_text.replace('d', ':').replace('m', ':').replace('s', ''),  # 12d 34m 56.7s -> 12:34:56.7
            dec_text.replace('：', ':')  # 处理中文冒号
        ]
        
        # 尝试不同的格式组合
        for ra_fmt in ra_formats:
            for dec_fmt in dec_formats:
                try:
                    # 尝试使用时角单位解析赤经
                    coord = SkyCoord(ra_fmt, dec_fmt, unit=(u.hourangle, u.deg))
                    return coord.ra.deg, coord.dec.deg
                except Exception:
                    try:
                        # 尝试使用度数单位解析赤经
                        coord = SkyCoord(ra_fmt, dec_fmt, unit=(u.deg, u.deg))
                        return coord.ra.deg, coord.dec.deg
                    except Exception:
                        continue
        
        # 如果所有格式都失败，尝试更复杂的解析方法
        # 处理赤经
        ra_deg = None
        if 'h' in ra_text or 'm' in ra_text or 's' in ra_text:
            # 时分秒格式
            parts = ra_text.replace('h', ' ').replace('m', ' ').replace('s', ' ').split()
            if len(parts) >= 1:
                hours = float(parts[0])
                minutes = float(parts[1]) if len(parts) > 1 else 0
                seconds = float(parts[2]) if len(parts) > 2 else 0
                ra_deg = 15 * (hours + minutes/60 + seconds/3600)  # 转换为度数
        elif ':' in ra_text:
            # 时分秒格式（使用冒号分隔）
            parts = ra_text.split(':')
            if len(parts) >= 1:
                hours = float(parts[0])
                minutes = float(parts[1]) if len(parts) > 1 else 0
                seconds = float(parts[2]) if len(parts) > 2 else 0
                ra_deg = 15 * (hours + minutes/60 + seconds/3600)  # 转换为度数
        
        # 处理赤纬
        dec_deg = None
        if '°' in dec_text or '\'' in dec_text or '"' in dec_text:
            # 度分秒格式
            # 处理符号
            sign = -1 if dec_text.startswith('-') else 1
            dec_text = dec_text.replace('-', '').replace('+', '')
            
            parts = dec_text.replace('°', ' ').replace('\'', ' ').replace('"', ' ').split()
            if len(parts) >= 1:
                degrees = float(parts[0])
                minutes = float(parts[1]) if len(parts) > 1 else 0
                seconds = float(parts[2]) if len(parts) > 2 else 0
                dec_deg = sign * (degrees + minutes/60 + seconds/3600)
        elif ':' in dec_text:
            # 度分秒格式（使用冒号分隔）
            # 处理符号
            sign = -1 if dec_text.startswith('-') else 1
            dec_text = dec_text.replace('-', '').replace('+', '')
            
            parts = dec_text.split(':')
            if len(parts) >= 1:
                degrees = float(parts[0])
                minutes = float(parts[1]) if len(parts) > 1 else 0
                seconds = float(parts[2]) if len(parts) > 2 else 0
                dec_deg = sign * (degrees + minutes/60 + seconds/3600)
        
        # 如果成功解析了两个坐标，返回结果
        if ra_deg is not None and dec_deg is not None:
            return ra_deg, dec_deg
        
        # 如果所有方法都失败，抛出异常
        raise ValueError(f"无法解析坐标: RA='{ra_text}', DEC='{dec_text}'")
    
    except Exception as e:
        logging.error(f"解析坐标时出错: {str(e)}")
        raise ValueError(f"无法解析坐标: RA='{ra_text}', DEC='{dec_text}', 错误: {str(e)}")


def format_astronomical_coords(coord_str):
    """
    格式化天文坐标字符串，确保各部分有前导零
    输入格式: "+35 30 4.10" 或 "-12 5 7.5"
    输出格式: "+35 30 04.10" 或 "-12 05 07.5"
    """
    try:
        parts = coord_str.split()
        if len(parts) != 3:
            return coord_str
            
        # 处理小时部分
        hours = parts[0]
        
        # 处理分钟部分
        minutes = parts[1]
        if len(minutes) == 1:
            minutes = f"0{minutes}"
            
        # 处理秒部分
        seconds = parts[2]
        if '.' in seconds:
            sec_parts = seconds.split('.')
            if len(sec_parts[0]) == 1:
                seconds = f"0{sec_parts[0]}.{sec_parts[1]}" if len(sec_parts) > 1 else f"0{sec_parts[0]}"
        else:
            if len(seconds) == 1:
                seconds = f"0{seconds}"
                
        return f"{hours} {minutes} {seconds}"
    except Exception:
        return coord_str

class CoordinateParser:
    def __init__(self, settings_manager):
        self.wcs = None
        self.settings = settings_manager
        self.ast = AstrometryNet()
        # 从设置中获取API密钥
        api_key = settings_manager.get_setting("astrometry_api_key")
        if api_key:
            self.ast.api_key = api_key
        else:
            logging.warning("未配置API密钥，请在设置中输入astrometry.net的API密钥")
        self.pixel_scale = None
        self.coord_system = None
        self.equinox = None

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
        else:
            # 当wcs为None时，清除所有相关状态
            self.coord_system = None
            self.equinox = None
            self.pixel_scale = None
    
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
        
        # 强制进行在线盲解，无论是否已有WCS信息
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

    def calculate_field_of_view(self, width, height, pixel_scale):
        """计算视场大小（度）
        
        参数:
            width: 图像宽度（像素）
            height: 图像高度（像素）
            pixel_scale: 像素比例（角秒/像素）
            
        返回:
            tuple: (fov_width, fov_height) 视场宽度和高度（度）
        """
        if pixel_scale is None or pixel_scale <= 0:
            # 使用默认值
            pixel_scale = 1.0
            logging.warning("Using default pixel scale of 1.0 arcsec/pixel for FOV calculation")
        
        # 计算视场大小（度）
        fov_width = (width * pixel_scale) / 3600.0
        fov_height = (height * pixel_scale) / 3600.0
        
        return (fov_width, fov_height)

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
            
    def calculate_field_of_view(self, width, height, pixel_scale):
        """计算视场大小（度）
        
        参数:
            width: 图像宽度（像素）
            height: 图像高度（像素）
            pixel_scale: 像素比例（角秒/像素）
            
        返回:
            tuple: (fov_width, fov_height) 视场宽度和高度（度）
        """
        if pixel_scale is None or pixel_scale <= 0:
            # 使用默认值
            pixel_scale = 1.0
            logging.warning("Using default pixel scale of 1.0 arcsec/pixel for FOV calculation")
        
        # 计算视场大小（度）
        fov_width = (width * pixel_scale) / 3600.0
        fov_height = (height * pixel_scale) / 3600.0
        
        return (fov_width, fov_height)
        
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