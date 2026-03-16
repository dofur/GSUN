"""
星表查询模块 - 支持UCAC4星表查询

作者: Guoyou Sun
版本: V1.1
"""

import os
import struct
import numpy as np
from astropy.io import fits
from astropy.coordinates import SkyCoord
from astropy import units as u
import logging
from typing import Optional, List, Dict, Tuple
from scipy import ndimage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CatalogQuery:
    """星表查询类，支持UCAC4"""
    
    def __init__(self, ucac4_path: str = None):
        """
        初始化星表查询
        
        Args:
            ucac4_path: UCAC4星表路径（如果为None，使用默认值）
        """
        # 从配置文件读取路径
        import configparser
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # 设置UCAC4路径
        if ucac4_path is None:
            ucac4_path = config.get('Settings', 'ucac4_path', 
                                     fallback=r"D:\ucac4")
        self.ucac4_path = ucac4_path
        
        # 检查路径是否存在
        self.ucac4_available = os.path.exists(ucac4_path)
        
        if self.ucac4_available:
            logger.info(f"UCAC4星表路径: {ucac4_path}")
        else:
            logger.warning(f"UCAC4星表路径不存在: {ucac4_path}")
    
    def query_star(self, ra: float, dec: float, search_radius: float = 0.1, 
                   catalog: str = 'auto') -> Optional[Dict]:
        """
        查询指定位置附近的恒星
        
        Args:
            ra: 赤经（度）
            dec: 赤纬（度）
            search_radius: 搜索半径（度）
            catalog: 使用的星表 ('ucac4')
        
        Returns:
            包含星等信息的字典，如果未找到返回None
        """
        if catalog == 'auto' or catalog == 'ucac4':
            return self.query_ucac4(ra, dec, search_radius)
        else:
            logger.error(f"不支持的星表类型: {catalog}")
            return None
    
    def query_ucac4(self, ra: float, dec: float, search_radius: float = 0.1) -> Optional[Dict]:
        """
        查询UCAC4星表（使用索引文件加速）
        
        Args:
            ra: 赤经（度）
            dec: 赤纬（度）
            search_radius: 搜索半径（度）
        
        Returns:
            包含星等信息的字典
        """
        if not self.ucac4_available:
            logger.warning("UCAC4星表不可用")
            return None
        
        try:
            # 计算Dec度数（UCAC4索引文件中Dec是1-900，对应-90°到+90°，每个区域0.2度）
            dec_deg = int((dec + 90) / 0.2) + 1  # 1-900
            
            logger.info(f"查询UCAC4: RA={ra:.6f}°, Dec={dec:.6f}° (D={dec_deg})")
            
            # 直接使用Dec值计算zone编号
            # UCAC4 zone编号规则：Zone N对应Dec=-90°+(N-1)*0.2°到-90°+N*0.2°
            zone_str = f"z{dec_deg:03d}"
            zone_file = os.path.join(self.ucac4_path, "u4b", zone_str)
            
            if not os.path.exists(zone_file):
                logger.warning(f"UCAC4区域文件不存在: {zone_file}")
                return None
            
            logger.info(f"使用Zone: {dec_deg} ({zone_str})")
            
            # 读取区域文件，只读取需要的部分
            # UCAC4按RA排序，所以我们可以二分查找
            return self._read_ucac4_zone(zone_file, ra, dec, search_radius)
            return None
            
        except Exception as e:
            logger.error(f"查询UCAC4星表失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def query_ucac4_multiple(self, ra: float, dec: float, search_radius: float = 0.5, 
                            max_stars: int = 10) -> List[Dict]:
        """
        查询UCAC4星表中的多个恒星
        
        Args:
            ra: 赤经（度）
            dec: 赤纬（度）
            search_radius: 搜索半径（度）
            max_stars: 返回的最大恒星数量
        
        Returns:
            包含星等信息的字典列表
        """
        if not self.ucac4_available:
            logger.warning("UCAC4星表不可用")
            return []
        
        try:
            # 计算Dec度数（UCAC4索引文件中Dec是1-900，对应-90°到+90°，每个区域0.2度）
            dec_deg = int((dec + 90) / 0.2) + 1  # 1-900
            
            logger.info(f"查询UCAC4多个恒星: RA={ra:.6f}°, Dec={dec:.6f}° (D={dec_deg})")
            
            # 直接使用Dec值计算zone编号
            # UCAC4 zone编号规则：Zone N对应Dec=-90°+(N-1)*0.2°到-90°+N*0.2°
            zone_str = f"z{dec_deg:03d}"
            zone_file = os.path.join(self.ucac4_path, "u4b", zone_str)
            
            if not os.path.exists(zone_file):
                logger.warning(f"UCAC4区域文件不存在: {zone_file}")
                return []
            
            logger.info(f"使用Zone: {dec_deg} ({zone_str})")
            
            # 读取区域文件，返回多个恒星
            return self._read_ucac4_zone_multiple(zone_file, ra, dec, search_radius, max_stars)
            
        except Exception as e:
            logger.error(f"查询UCAC4多个恒星失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _read_ucac4_zone(self, zone_file: str, ra: float, dec: float, search_radius: float) -> Optional[Dict]:
        """
        读取UCAC4区域文件并查找最近的恒星
        
        Args:
            zone_file: 区域文件路径
            ra: 目标赤经（度）
            dec: 目标赤纬（度）
            search_radius: 搜索半径（度）
        
        Returns:
            包含星等信息的字典
        """
        try:
            # 读取二进制文件
            with open(zone_file, 'rb') as f:
                # UCAC4每个星78字节
                star_size = 78
                file_size = os.path.getsize(zone_file)
                num_stars = file_size // star_size
                
                logger.info(f"读取区域文件: {num_stars}颗星")
                
                # 由于UCAC4按RA排序，我们可以使用二分查找
                # 将RA转换为毫角秒
                ra_mas = int(ra * 3600000.0)
                
                # 二分查找
                left, right = 0, num_stars - 1
                closest_star = None
                closest_distance = float('inf')
                
                # 先找到第一个RA >= 目标RA的位置
                first_match_idx = 0
                while first_match_idx < num_stars:
                    offset = first_match_idx * star_size
                    f.seek(offset)
                    star_bytes = f.read(star_size)
                    star = self._parse_ucac4_star(star_bytes)
                    
                    if star is not None and star['ra'] >= ra_mas:
                        break
                    first_match_idx += 1
                
                # 在附近搜索（前后各搜索一定数量）
                search_range = 1000  # 搜索1000颗星
                start_idx = max(0, first_match_idx - search_range)
                end_idx = min(num_stars, first_match_idx + search_range)
                
                for i in range(start_idx, end_idx):
                    offset = i * star_size
                    f.seek(offset)
                    star_bytes = f.read(star_size)
                    star = self._parse_ucac4_star(star_bytes)
                    
                    if star is None:
                        continue
                    
                    # 计算距离
                    star_ra = star['ra'] / 3600000.0
                    star_dec = star['spd'] / 3600000.0 - 90.0
                    
                    # 快速距离计算（使用近似公式）
                    ra_diff = abs(star_ra - ra)
                    dec_diff = abs(star_dec - dec)
                    
                    # 如果Dec差异太大，跳过
                    if dec_diff > search_radius:
                        continue
                    
                    # 计算角距离（简化公式，避免频繁创建SkyCoord对象）
                    # 对于小角度，可以使用线性近似
                    distance = np.sqrt(ra_diff**2 + dec_diff**2)
                    
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_star = star
                
                if closest_star is None:
                    logger.warning(f"未找到匹配的恒星")
                    return None
                
                # 计算精确的角距离
                target_coord = SkyCoord(ra=ra*u.degree, dec=dec*u.degree)
                star_coord = SkyCoord(ra=closest_star['ra']/3600000.0*u.degree, 
                                   dec=(closest_star['spd']/3600000.0-90.0)*u.degree)
                exact_distance = target_coord.separation(star_coord).value
                
                # 提取星等信息
                result = {
                    'catalog': 'ucac4',
                    'ra': closest_star['ra'] / 3600000.0,
                    'dec': closest_star['spd'] / 3600000.0 - 90.0,
                    'magnitude': closest_star['mag'],
                    'distance': exact_distance,
                    'id_number': closest_star['id_number'],
                    'ucac4_id': closest_star['id_number'],
                }
                
                logger.info(f"找到UCAC4恒星: RA={result['ra']:.6f}, Dec={result['dec']:.6f}, "
                          f"mag={result['magnitude']:.3f}, 距离={result['distance']:.6f}度")
                
                return result
                
        except Exception as e:
            logger.error(f"读取UCAC4区域文件失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _read_ucac4_zone_multiple(self, zone_file: str, ra: float, dec: float, 
                                 search_radius: float, max_stars: int) -> List[Dict]:
        """
        读取UCAC4区域文件并查找多个恒星
        
        Args:
            zone_file: 区域文件路径
            ra: 目标赤经（度）
            dec: 目标赤纬（度）
            search_radius: 搜索半径（度）
            max_stars: 返回的最大恒星数量
        
        Returns:
            包含星等信息的字典列表
        """
        try:
            # 读取二进制文件
            with open(zone_file, 'rb') as f:
                # UCAC4每个星78字节
                star_size = 78
                file_size = os.path.getsize(zone_file)
                num_stars = file_size // star_size
                
                logger.info(f"读取区域文件: {num_stars}颗星")
                
                # 收集所有在搜索半径内的恒星
                all_matches = []
                
                # 先找到第一个RA >= 目标RA的位置
                first_match_idx = 0
                ra_mas = int(ra * 3600000.0)
                
                while first_match_idx < num_stars:
                    offset = first_match_idx * star_size
                    f.seek(offset)
                    star_bytes = f.read(star_size)
                    star = self._parse_ucac4_star(star_bytes)
                    
                    if star is not None and star['ra'] >= ra_mas:
                        break
                    first_match_idx += 1
                
                # 在附近搜索（前后各搜索一定数量）
                search_range = 2000  # 搜索2000颗星
                start_idx = max(0, first_match_idx - search_range)
                end_idx = min(num_stars, first_match_idx + search_range)
                
                for i in range(start_idx, end_idx):
                    offset = i * star_size
                    f.seek(offset)
                    star_bytes = f.read(star_size)
                    star = self._parse_ucac4_star(star_bytes)
                    
                    if star is None:
                        continue
                    
                    # 计算距离
                    star_ra = star['ra'] / 3600000.0
                    star_dec = star['spd'] / 3600000.0 - 90.0
                    
                    # 快速距离计算
                    ra_diff = abs(star_ra - ra)
                    dec_diff = abs(star_dec - dec)
                    
                    # 如果Dec差异太大，跳过
                    if dec_diff > search_radius:
                        continue
                    
                    # 计算角距离（简化公式）
                    distance = np.sqrt(ra_diff**2 + dec_diff**2)
                    
                    # 如果在搜索半径内，添加到结果
                    if distance < search_radius:
                        all_matches.append({
                            'star': star,
                            'distance': distance
                        })
                
                if not all_matches:
                    logger.warning(f"在搜索半径{search_radius}度内未找到恒星")
                    return []
                
                # 按距离排序
                all_matches.sort(key=lambda x: x['distance'])
                
                # 计算精确的角距离并构建结果
                target_coord = SkyCoord(ra=ra*u.degree, dec=dec*u.degree)
                result = []
                
                for i in range(min(max_stars, len(all_matches))):
                    match = all_matches[i]
                    star = match['star']
                    
                    # 计算精确距离
                    star_coord = SkyCoord(ra=star['ra']/3600000.0*u.degree, 
                                       dec=(star['spd']/3600000.0-90.0)*u.degree)
                    exact_distance = target_coord.separation(star_coord).value
                    
                    star_result = {
                        'catalog': 'ucac4',
                        'ra': star['ra'] / 3600000.0,
                        'dec': star['spd'] / 3600000.0 - 90.0,
                        'magnitude': star['mag'],
                        'distance': exact_distance,
                        'id_number': star['id_number'],
                        'ucac4_id': star['id_number'],
                    }
                    
                    result.append(star_result)
                
                logger.info(f"找到{len(result)}颗UCAC4恒星（搜索半径={search_radius}度）")
                
                return result
                
        except Exception as e:
            logger.error(f"读取UCAC4区域文件失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_ucac4_star(self, star_bytes: bytes) -> Optional[Dict]:
        """
        解析UCAC4恒星数据
        
        Args:
            star_bytes: 78字节的恒星数据
        
        Returns:
            包含恒星信息的字典
        """
        try:
            # UCAC4数据格式（78字节）
            # 使用小端字节序（Intel x86）
            
            # 解析RA（毫角秒）
            ra_mas = struct.unpack('<i', star_bytes[0:4])[0]
            
            # 解析SPD（南天极距离，毫角秒）
            spd_mas = struct.unpack('<i', star_bytes[4:8])[0]
            
            # 解析星等（使用mag1和mag2的组合）
            mag1 = struct.unpack('<H', star_bytes[8:10])[0]
            mag2 = struct.unpack('<H', star_bytes[10:12])[0]
            
            # 计算平均星等
            mag = (mag1 + mag2) / 2.0 / 1000.0  # 转换为mag
            
            # 解析ID号
            id_number = struct.unpack('<I', star_bytes[20:24])[0]
            
            return {
                'ra': ra_mas,
                'spd': spd_mas,
                'mag': mag,
                'id_number': id_number,
            }
        except Exception as e:
            logger.warning(f"解析UCAC4恒星数据失败: {e}")
            return None
    
    def query_multiple_stars(self, ra: float, dec: float, search_radius: float = 0.5, 
                            max_stars: int = 10, catalog: str = 'auto') -> List[Dict]:
        """
        查询指定位置附近的多个恒星
        
        Args:
            ra: 赤经（度）
            dec: 赤纬（度）
            search_radius: 搜索半径（度）
            max_stars: 返回的最大恒星数量
            catalog: 使用的星表
        
        Returns:
            包含星等信息的字典列表
        """
        if catalog == 'auto' or catalog == 'ucac4':
            if self.ucac4_available:
                logger.info(f"使用UCAC4星表")
                return self.query_ucac4_multiple(ra, dec, search_radius, max_stars)
            else:
                logger.error("没有可用的星表")
                return []
        else:
            logger.error(f"不支持的星表类型: {catalog}")
            return []
    
    def aperture_photometry(self, image_data: np.ndarray, x: float, y: float, 
                         aperture_radius: float = 5.0,
                         sky_inner_radius: float = 8.0,
                         sky_outer_radius: float = 12.0) -> Dict:
        """
        孔径测光：提取目标星的仪器星等
        
        Args:
            image_data: 图像数据（2D numpy数组）
            x: 目标星X坐标（像素）
            y: 目标星Y坐标（像素）
            aperture_radius: 测光孔径半径（像素）
            sky_inner_radius: 天空环内径（像素）
            sky_outer_radius: 天空环外径（像素）
        
        Returns:
            包含测光结果的字典
        """
        try:
            # 创建坐标网格
            y_coords, x_coords = np.mgrid[0:image_data.shape[0], 0:image_data.shape[1]]
            
            # 计算到目标星的距离
            radius = np.sqrt((x_coords - x)**2 + (y_coords - y)**2)
            
            # 测光孔径内的总流量
            aperture_mask = radius <= aperture_radius
            total_flux = np.sum(image_data[aperture_mask])
            aperture_area = np.sum(aperture_mask)
            
            # 天空背景环内的平均流量
            sky_mask = (radius >= sky_inner_radius) & (radius <= sky_outer_radius)
            sky_flux = np.mean(image_data[sky_mask])
            sky_area = np.sum(sky_mask)
            
            # 扣除天空背景后的净流量
            net_flux = total_flux - sky_flux * aperture_area
            
            # 检查净流量是否合理（只检查是否为负，允许接近零的值）
            if net_flux < 0:
                logger.warning(f"净流量为负: {net_flux:.2e}, 天空背景可能过高")
                return None
            
            # 计算仪器星等
            instrument_mag = -2.5 * np.log10(net_flux) if net_flux > 0 else 99.9
            
            # 计算信噪比（改进的CCD噪声模型）
            # 考虑泊松噪声和读出噪声
            aperture_area = np.sum(aperture_mask)
            
            # CCD参数（可从配置文件读取，这里使用更实际的典型值）
            gain = 0.8  # 电子/ADU，更接近实际CCD相机（通常0.5-2.0）
            read_noise = 3.0  # 电子，更接近现代CCD（通常3-10电子）
            
            # 完整的噪声模型（单位：电子数）：
            # 总噪声方差 = 源信号噪声 + 天空背景噪声 + 读出噪声
            # 源信号噪声 = net_flux / gain (泊松噪声)
            # 天空背景噪声 = aperture_area * sky_flux / gain
            # 读出噪声 = aperture_area * read_noise^2
            
            # 转换为电子数计算噪声
            source_electrons = net_flux / gain if net_flux > 0 else 0
            sky_electrons = aperture_area * sky_flux / gain
            
            # 计算各噪声分量的方差（电子数^2）
            source_noise_variance = source_electrons  # 泊松噪声方差等于信号
            sky_noise_variance = sky_electrons        # 天空背景泊松噪声
            read_noise_variance = aperture_area * read_noise**2  # 读出噪声
            
            # 总噪声方差
            total_noise_variance = source_noise_variance + sky_noise_variance + read_noise_variance
            
            # 计算总噪声（电子数）
            total_noise_electrons = np.sqrt(total_noise_variance) if total_noise_variance > 0 else 0
            
            # SNR = 源信号电子数 / 总噪声电子数
            snr = source_electrons / total_noise_electrons if total_noise_electrons > 0 else 0
            
            # 计算FWHM（使用标准二阶矩方法）
            fwhm = 0.0
            try:
                # 提取孔径内的数据
                aperture_data = image_data[aperture_mask]
                
                # 计算峰值（扣除背景）
                peak_value = np.max(aperture_data) - sky_flux
                
                if peak_value > 0:
                    # 计算二阶矩（标准天文测光方法）
                    aperture_x = x_coords[aperture_mask]
                    aperture_y = y_coords[aperture_mask]
                    aperture_values = aperture_data - sky_flux
                    
                    # 只使用正值来计算质心和二阶矩
                    positive_mask = aperture_values > 0
                    if np.any(positive_mask):
                        aperture_x_pos = aperture_x[positive_mask]
                        aperture_y_pos = aperture_y[positive_mask]
                        aperture_values_pos = aperture_values[positive_mask]
                        
                        # 计算质心（加权平均）
                        centroid_x = np.sum(aperture_x_pos * aperture_values_pos) / np.sum(aperture_values_pos)
                        centroid_y = np.sum(aperture_y_pos * aperture_values_pos) / np.sum(aperture_values_pos)
                        
                        # 计算二阶矩（加权）
                        dx = aperture_x_pos - centroid_x
                        dy = aperture_y_pos - centroid_y
                        moment_x = np.sum(aperture_values_pos * dx**2) / np.sum(aperture_values_pos)
                        moment_y = np.sum(aperture_values_pos * dy**2) / np.sum(aperture_values_pos)
                        
                        # 计算标准差
                        sigma_x = np.sqrt(moment_x)
                        sigma_y = np.sqrt(moment_y)
                        
                        # 使用平均sigma（标准做法）
                        sigma = (sigma_x + sigma_y) / 2.0
                        
                        # FWHM = 2.355 * sigma（高斯分布的标准转换）
                        fwhm = 2.355 * sigma
                    else:
                        logger.warning("孔径内没有正值，无法计算FWHM")
            except Exception as e:
                logger.warning(f"FWHM计算失败: {e}")
                import traceback
                traceback.print_exc()
                fwhm = 0.0
            
            return {
                'total_flux': total_flux,
                'sky_flux': sky_flux,
                'net_flux': net_flux,
                'instrument_mag': instrument_mag,
                'snr': snr,
                'fwhm': fwhm,
                'aperture_area': aperture_area,
                'sky_area': sky_area,
            }
        except Exception as e:
            logger.error(f"孔径测光失败: {e}")
            return None
    
    def psf_photometry(self, image_data: np.ndarray, x: float, y: float,
                      psf_sigma: float = 2.0) -> Dict:
        """
        PSF测光：使用点扩散函数拟合提取目标星的仪器星等
        
        Args:
            image_data: 图像数据（2D numpy数组）
            x: 目标星X坐标（像素）
            y: 目标星Y坐标（像素）
            psf_sigma: PSF的sigma值（像素）
        
        Returns:
            包含测光结果的字典
        """
        try:
            # 创建坐标网格
            y_coords, x_coords = np.mgrid[0:image_data.shape[0], 0:image_data.shape[1]]
            
            # 计算到目标星的距离
            radius = np.sqrt((x_coords - x)**2 + (y_coords - y)**2)
            
            # 定义PSF（高斯函数）
            psf = np.exp(-radius**2 / (2 * psf_sigma**2))
            
            # 归一化PSF
            psf = psf / np.sum(psf)
            
            # 计算背景（使用远离目标星的区域）
            background_mask = radius > 5 * psf_sigma
            if np.any(background_mask):
                background = np.median(image_data[background_mask])
            else:
                background = 0
            
            # 扣除背景
            background_subtracted = image_data - background
            
            # 使用PSF拟合
            from scipy.optimize import curve_fit
            
            def gaussian_2d(coords, amplitude, x0, y0, sigma):
                x_grid, y_grid = coords
                return amplitude * np.exp(-((x_grid - x0)**2 + (y_grid - y0)**2) / (2 * sigma**2))
            
            # 提取局部区域
            box_size = int(10 * psf_sigma)
            x_start = max(0, int(x) - box_size)
            x_end = min(image_data.shape[1], int(x) + box_size)
            y_start = max(0, int(y) - box_size)
            y_end = min(image_data.shape[0], int(y) + box_size)
            
            local_data = background_subtracted[y_start:y_end, x_start:x_end]
            local_y, local_x = np.mgrid[y_start:y_end, x_start:x_end]
            
            # 初始猜测
            initial_guess = [
                np.max(local_data),
                x,
                y,
                psf_sigma
            ]
            
            # 拟合
            try:
                popt, _ = curve_fit(
                    gaussian_2d,
                    (local_x, local_y),
                    local_data.ravel(),
                    p0=initial_guess
                )
                
                amplitude, x0, y0, sigma = popt
                
                # 计算总流量（积分PSF）
                total_flux = amplitude * 2 * np.pi * sigma**2
                
                # 计算仪器星等
                instrument_mag = -2.5 * np.log10(total_flux) if total_flux > 0 else 99.9
                
                return {
                    'total_flux': total_flux,
                    'instrument_mag': instrument_mag,
                    'amplitude': amplitude,
                    'x0': x0,
                    'y0': y0,
                    'sigma': sigma,
                    'background': background,
                }
            except Exception as e:
                logger.warning(f"PSF拟合失败: {e}")
                return None
                
        except Exception as e:
            logger.error(f"PSF测光失败: {e}")
            return None
    
    def differential_photometry(self, image_data: np.ndarray, target_x: float, target_y: float,
                              ref_stars: List[Dict], catalog: str = 'ucac4',
                              aperture_radius: float = 5.0,
                              sky_inner_radius: float = 8.0,
                              sky_outer_radius: float = 12.0) -> Optional[Dict]:
        """
        差分测光：使用参考星计算目标星的星等
        
        Args:
            image_data: 图像数据（2D numpy数组）
            target_x: 目标星X坐标（像素）
            target_y: 目标星Y坐标（像素）
            ref_stars: 参考星列表，每个元素包含'ra', 'dec', 'magnitude'
            catalog: 使用的星表（'ucac4'）
            aperture_radius: 测光孔径半径（像素）
            sky_inner_radius: 天空环内径（像素）
            sky_outer_radius: 天空环外径（像素）
        
        Returns:
            包含测光结果的字典，如果失败返回None
        """
        try:
            # 1. 对目标星进行孔径测光
            target_result = self.aperture_photometry(image_data, target_x, target_y,
                                                   aperture_radius, sky_inner_radius, sky_outer_radius)
            if target_result is None:
                logger.error("目标星测光失败")
                return None
            
            # 2. 对所有参考星进行孔径测光
            ref_results = []
            for ref_star in ref_stars:
                ref_result = self.aperture_photometry(image_data, ref_star['x'], ref_star['y'],
                                                         aperture_radius, sky_inner_radius, sky_outer_radius)
                if ref_result is not None:
                    ref_results.append({
                        'ra': ref_star['ra'],
                        'dec': ref_star['dec'],
                        'catalog_magnitude': ref_star['magnitude'],
                        'instrument_magnitude': ref_result['instrument_mag'],
                        'net_flux': ref_result['net_flux'],
                        'snr': ref_result['snr'],
                    })
            
            if len(ref_results) < 3:
                logger.warning(f"参考星数量不足: {len(ref_results)}")
                return None
            
            # 3. 计算零点偏移（zero-point offset）
            # 使用最小二乘法拟合：m_inst = m_cat + zp
            ref_mag_cat = np.array([r['catalog_magnitude'] for r in ref_results])
            ref_mag_inst = np.array([r['instrument_magnitude'] for r in ref_results])
            
            # 计算零点偏移：zp = median(m_inst - m_cat)
            zp = np.median(ref_mag_inst - ref_mag_cat)
            
            # 4. 计算目标星的星等
            # m_target = m_inst_target - zp
            target_magnitude = target_result['instrument_mag'] - zp
            
            # 5. 计算误差
            residuals = ref_mag_inst - ref_mag_cat
            zp_error = np.std(residuals)
            target_magnitude_error = zp_error
            
            # 6. 根据星表选择星等类型
            if catalog.lower() == 'ucac4':
                magnitude_type = 'V'  # UCAC4使用V星等
            else:
                magnitude_type = 'Unknown'
            
            return {
                'catalog': catalog,
                'magnitude_type': magnitude_type,
                'target_x': target_x,
                'target_y': target_y,
                'catalog_magnitude': target_magnitude,
                'catalog_magnitude_error': target_magnitude_error,
                'instrument_magnitude': target_result['instrument_mag'],
                'net_flux': target_result['net_flux'],
                'snr': target_result['snr'],
                'fwhm': target_result.get('fwhm', 0.0),
                'zero_point': zp,
                'zero_point_error': zp_error,
                'ref_stars_used': len(ref_results),
                'ref_star_details': ref_results,
            }
            
        except Exception as e:
            logger.error(f"差分测光失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def find_stars_in_image(self, image_data: np.ndarray, 
                          threshold: float = 5.0,
                          min_separation: float = 5.0) -> List[Dict]:
        """
        在图像中查找恒星
        
        Args:
            image_data: 图像数据（2D numpy数组）
            threshold: 检测阈值（sigma）
            min_separation: 最小分离距离（像素）
        
        Returns:
            包含恒星信息的字典列表
        """
        try:
            # 计算背景和噪声
            background = np.median(image_data)
            noise = np.std(image_data)
            
            # 检测阈值
            detection_threshold = background + threshold * noise
            
            # 查找超过阈值的像素
            mask = image_data > detection_threshold
            
            # 使用连通区域分析找到恒星
            labeled, num_features = ndimage.label(mask)
            
            # 计算每个连通区域的质心
            objects = ndimage.find_objects(labeled)
            
            stars = []
            for i, obj in enumerate(objects, 1):
                # 提取连通区域
                region = image_data[labeled == i]
                
                # 计算质心
                y_coords, x_coords = np.where(labeled == i)
                centroid_x = np.mean(x_coords)
                centroid_y = np.mean(y_coords)
                
                # 计算峰值
                peak_value = np.max(region)
                
                # 计算总流量
                total_flux = np.sum(region - background)
                
                # 计算仪器星等
                instrument_mag = -2.5 * np.log10(total_flux) if total_flux > 0 else 99.9
                
                stars.append({
                    'x': centroid_x,
                    'y': centroid_y,
                    'peak': peak_value,
                    'flux': total_flux,
                    'instrument_mag': instrument_mag,
                })
            
            # 按流量排序
            stars.sort(key=lambda x: x['flux'], reverse=True)
            
            # 过滤太近的恒星
            filtered_stars = []
            for star in stars:
                too_close = False
                for existing_star in filtered_stars:
                    distance = np.sqrt((star['x'] - existing_star['x'])**2 + 
                                    (star['y'] - existing_star['y'])**2)
                    if distance < min_separation:
                        too_close = True
                        break
                
                if not too_close:
                    filtered_stars.append(star)
            
            logger.info(f"找到{len(filtered_stars)}颗恒星")
            
            return filtered_stars
            
        except Exception as e:
            logger.error(f"查找恒星失败: {e}")
            return []


def test_catalog_query():
    """
    测试星表查询功能
    """
    catalog = CatalogQuery()
    
    # 测试UCAC4查询
    ra = 83.633083  # 5h 34m 31.94s
    dec = -1.201944  # -1° 12' 7.0"
    
    print(f"测试查询: RA={ra:.6f}°, Dec={dec:.6f}°")
    
    # 查询单个恒星
    star = catalog.query_ucac4(ra, dec, search_radius=0.1)
    if star:
        print(f"找到恒星: RA={star['ra']:.6f}°, Dec={star['dec']:.6f}°, "
              f"mag={star['magnitude']:.3f}, 距离={star['distance']:.6f}°")
    
    # 查询多个恒星
    stars = catalog.query_ucac4_multiple(ra, dec, search_radius=0.5, max_stars=10)
    print(f"\n找到{len(stars)}颗恒星:")
    for i, star in enumerate(stars):
        print(f"  {i+1}. RA={star['ra']:.6f}°, Dec={star['dec']:.6f}°, "
              f"mag={star['magnitude']:.3f}, 距离={star['distance']:.6f}°")


if __name__ == "__main__":
    test_catalog_query()
