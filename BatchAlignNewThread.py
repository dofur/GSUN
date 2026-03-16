"""
批量对齐线程（新） - Batch Align New Thread

作者：Guoyou Sun (孙国佑) - 天体收藏家
软件：星视 GSUN View V4.0
网站：sunguoyou.lamost.org
标识：546756
原创作品，禁止商业使用
"""

from PyQt5.QtCore import QThread, pyqtSignal
import os
import numpy as np
from astropy.io import fits
import astroalign as aa
from skimage import transform as tf
import logging
from PyQt5.QtGui import QImage, QPixmap

class BatchAlignNewThread(QThread):
    """批量对齐线程 - 以第一张为基准对齐其他图片"""
    progress_signal = pyqtSignal(int, int)  # 发送当前处理的索引和总数
    complete_signal = pyqtSignal()  # 对齐完成信号
    error_signal = pyqtSignal(str)  # 错误信号
    
    def __init__(self, reference_data, image_list, original_images_list, apply_zscale_func):
        super().__init__()
        self.reference_data = reference_data
        self.image_list = image_list
        self.original_images_list = original_images_list
        self.apply_zscale_func = apply_zscale_func
        self.aligned_images = []
        self.is_canceled = False
    
    def preprocess_for_alignment(self, image_data):
        """预处理图像以增强星点检测"""
        try:
            import cv2
            
            if len(image_data.shape) > 2:
                image_gray = np.mean(image_data, axis=2)
            else:
                image_gray = image_data
            
            if image_gray.dtype != np.uint8:
                p_min, p_max = np.nanpercentile(image_gray, (1, 99.5))
                
                if p_max > p_min:
                    clipped = np.clip(image_gray, p_min, p_max)
                    normalized = (clipped - p_min) / (p_max - p_min) * 255
                else:
                    d_min, d_max = np.nanmin(image_gray), np.nanmax(image_gray)
                    if d_max > d_min:
                        normalized = (image_gray - d_min) / (d_max - d_min) * 255
                    else:
                        normalized = np.zeros_like(image_gray)
                        
                normalized = normalized.astype(np.uint8)
            else:
                normalized = image_gray
            
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(normalized)
            blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
            result = blurred.astype(np.float32) / 255.0
            
            return result
            
        except ImportError:
            logging.warning("OpenCV not available, using fallback preprocessing")
            
            if len(image_data.shape) > 2:
                image_gray = np.mean(image_data, axis=2)
            else:
                image_gray = image_data
            
            p2, p98 = np.percentile(image_gray, (2, 98))
            if p98 > p2:
                stretched = (image_gray - p2) / (p98 - p2)
                np.clip(stretched, 0, 1, out=stretched)
                return stretched.astype(np.float32)
            else:
                return image_data.astype(np.float32)
        
        except Exception as e:
            logging.warning(f"Preprocessing failed: {e}, using original data")
            return image_data.astype(np.float32)
    
    def align_single_image(self, new_data, ref_data, preprocessed_new, preprocessed_ref):
        """对齐单张图像，使用与align_images_only相同的逻辑"""
        try:
            trans = None
            src_pts = None
            dst_pts = None
            
            # 策略1: 预处理图像 + 默认参数
            try:
                trans, (src_pts, dst_pts) = aa.find_transform(preprocessed_new, preprocessed_ref)
                logging.info(f"策略1成功: 检测到 {len(src_pts)} 对匹配点")
            except Exception as e1:
                logging.warning(f"策略1失败: {e1}")
                
                # 策略2: 预处理图像 + 宽松参数
                try:
                    trans, (src_pts, dst_pts) = aa.find_transform(preprocessed_new, preprocessed_ref, detection_sigma=3)
                    logging.info(f"策略2成功: 检测到 {len(src_pts)} 对匹配点")
                except Exception as e2:
                    logging.warning(f"策略2失败: {e2}")
                    
                    # 策略3: 原始数据 + 宽松参数
                    try:
                        def simple_norm(img):
                            if img.dtype == np.uint8: return img
                            _min, _max = np.nanmin(img), np.nanmax(img)
                            if _max > _min:
                                return (img - _min) / (_max - _min)
                            return img
                        
                        raw_new = simple_norm(new_data)
                        raw_ref = simple_norm(ref_data)
                        
                        trans, (src_pts, dst_pts) = aa.find_transform(raw_new, raw_ref, detection_sigma=3)
                        logging.info(f"策略3成功: 检测到 {len(src_pts)} 对匹配点")
                    except Exception as e3:
                        logging.error(f"所有策略都失败。最后错误: {e3}")
                        raise e3
            
            # 尝试使用2阶多项式变换处理畸变
            logging.info(f"检测到 {len(src_pts)} 对匹配点")
            if len(src_pts) >= 6:
                logging.info(f"使用多项式变换（Order 2）处理畸变，匹配点数: {len(src_pts)}")
                
                try:
                    poly_tf = tf.PolynomialTransform(dimensionality=2)
                    poly_tf.estimate(dst_pts, src_pts)
                    
                    aligned_data = tf.warp(new_data, poly_tf, output_shape=ref_data.shape, order=3, mode='constant', cval=np.median(new_data))
                    return aligned_data
                except Exception as e_poly_fit:
                    logging.warning(f"多项式变换失败: {e_poly_fit}，回退到相似变换")
                    aligned_data = aa.apply_transform(trans, new_data, ref_data)[0]
                    return aligned_data
            else:
                # 点数不足，使用相似变换
                logging.warning(f"匹配点不足（{len(src_pts)} < 6），使用相似变换")
                aligned_data = aa.apply_transform(trans, new_data, ref_data)[0]
                return aligned_data
                
        except Exception as e:
            logging.error(f"对齐失败: {e}")
            raise e
    
    def run(self):
        try:
            ref_data = self.reference_data.astype(np.float32)
            preprocessed_ref = self.preprocess_for_alignment(ref_data)
            
            for idx, image_dict in enumerate(self.image_list):
                if self.is_canceled:
                    break
                
                try:
                    self.progress_signal.emit(idx, len(self.image_list))
                    
                    file_path = image_dict['filename']
                    
                    try:
                        # 使用original_images中的数据，避免重复读取FITS文件
                        if idx < len(self.original_images_list):
                            new_data = self.original_images_list[idx]
                        else:
                            # 如果没有original_data，从文件读取
                            with fits.open(file_path, memmap=False) as hdul:
                                new_data = hdul[0].data
                                if len(new_data.shape) > 2:
                                    if len(new_data.shape) == 3:
                                        new_data = new_data[0]
                                    elif len(new_data.shape) == 4:
                                        new_data = new_data[0, 0]
                        
                        new_data = new_data.astype(np.float32)
                        preprocessed_new = self.preprocess_for_alignment(new_data)
                        
                        # 对齐图像
                        aligned_data = self.align_single_image(new_data, ref_data, preprocessed_new, preprocessed_ref)
                        
                        # 应用zscale拉伸
                        normalized_aligned = self.apply_zscale_func(aligned_data)
                        
                        # 创建QImage和QPixmap
                        if len(normalized_aligned.shape) == 2:
                            height, width = normalized_aligned.shape
                            qimage = QImage(normalized_aligned.tobytes(), width, height, width, QImage.Format_Grayscale8)
                        else:
                            height, width = normalized_aligned.shape[:2]
                            qimage = QImage(normalized_aligned.tobytes(), width, height, width*3, QImage.Format_RGB888)
                        
                        pixmap = QPixmap.fromImage(qimage)
                        
                        # 保留原始信息
                        time_info = image_dict.get('time_info', '')
                        sky_region_info = image_dict.get('sky_region', '')
                        header = image_dict.get('header', None)
                        
                        new_image_dict = {
                            'filename': file_path,
                            'pixmap': pixmap,
                            'time_info': time_info,
                            'sky_region': sky_region_info,
                            'header': header,
                            'original_data_shape': aligned_data.shape,
                            'original_data': normalized_aligned,
                            'aligned': True
                        }
                        
                        self.aligned_images.append(new_image_dict)
                        print(f"图像 {os.path.basename(file_path)} 已对齐")
                        
                    except Exception as e:
                        logging.error(f"处理图像 {os.path.basename(file_path)} 时出错: {e}")
                        print(f"处理图像 {os.path.basename(file_path)} 时出错: {e}，跳过此图像。")
                        continue
                
                except Exception as e:
                    logging.error(f"处理图像 {image_dict['filename']} 时出错: {e}")
                    print(f"处理图像 {image_dict['filename']} 时出错: {e}，跳过此图像。")
            
            self.complete_signal.emit()
        
        except Exception as e:
            self.error_signal.emit(str(e))
    
    def cancel(self):
        """取消对齐操作"""
        self.is_canceled = True
