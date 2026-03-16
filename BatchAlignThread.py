"""
批量图像对齐线程 - Batch Align Thread

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
import numpy as np

class BatchAlignThread(QThread):
    """批量图像对齐线程"""
    progress_signal = pyqtSignal(int, str)  # 发送当前处理的索引和文件名
    complete_signal = pyqtSignal()  # 对齐完成信号
    error_signal = pyqtSignal(str)  # 错误信号
    
    def __init__(self, new_folder, old_folder, aligned_new_folder, new_files, old_files):
        super().__init__()
        self.new_folder = new_folder
        self.old_folder = old_folder
        self.aligned_new_folder = aligned_new_folder
        self.new_files = new_files
        self.old_files = old_files
        self.is_canceled = False
    
    def preprocess_for_alignment(self, image_data):
        """预处理图像以增强星点检测"""
        try:
            import cv2
            
            # 确保图像是二维的
            if len(image_data.shape) == 3:
                # 如果是彩色图像，转换为灰度
                if image_data.shape[2] == 3:
                    # RGB转灰度
                    image_gray = np.dot(image_data[...,:3], [0.2989, 0.5870, 0.1140])
                else:
                    image_gray = image_data[:,:,0]  # 取第一个通道
            else:
                image_gray = image_data
            
            # 1. 数据归一化 (使用Percentile而不是Min-Max以增强鲁棒性)
            if image_gray.dtype != np.uint8:
                # 使用 np.nanpercentile 忽略 NaN
                p_min, p_max = np.nanpercentile(image_gray, (1, 99.5))
                
                if p_max > p_min:
                    # Clip and normalize
                    clipped = np.clip(image_gray, p_min, p_max)
                    normalized = (clipped - p_min) / (p_max - p_min) * 255
                else:
                    normalized = image_gray
                    # normalize entire range if flat
                    d_min, d_max = np.nanmin(image_gray), np.nanmax(image_gray)
                    if d_max > d_min:
                        normalized = (image_gray - d_min) / (d_max - d_min) * 255
                    else:
                        normalized = np.zeros_like(image_gray)
                        
                normalized = normalized.astype(np.uint8)
            else:
                normalized = image_gray
            
            # 2. 自适应直方图均衡化（CLAHE）增强对比度
            # 降低 clipLimit 防止过度增强噪声
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(normalized)
            
            # 3. 高斯模糊去噪（轻微模糊）
            blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
            
            # 4. 转换为浮点型并归一化到0-1范围
            result = blurred.astype(np.float32) / 255.0
            
            return result
            
        except ImportError:
            # 如果没有cv2，使用numpy进行简单预处理
            logging.warning("OpenCV not available, using fallback preprocessing")
            
            if len(image_data.shape) == 3:
                image_gray = np.mean(image_data, axis=2)
            else:
                image_gray = image_data
            
            # 简单的对比度拉伸
            p2, p98 = np.percentile(image_gray, (2, 98))
            if p98 > p2:
                stretched = (image_gray - p2) / (p98 - p2)
                np.clip(stretched, 0, 1, out=stretched)
                return stretched.astype(np.float32)
            else:
                return image_gray.astype(np.float32)
        
        except Exception as e:
            logging.warning(f"Preprocessing failed: {e}, using original data")
            return image_data.astype(np.float32)
    
    def run(self):
        try:
            # 遍历新图文件
            for idx, new_file in enumerate(self.new_files):
                if self.is_canceled:
                    break
                
                try:
                    # 发送进度信号
                    self.progress_signal.emit(idx, new_file)
                    
                    # 提取新图文件名（不含扩展名）
                    base_name = os.path.splitext(new_file)[0]
                    # 查找旧图文件夹中匹配的文件
                    matching_old_files = [f for f in self.old_files if base_name in os.path.splitext(f)[0]]
                    if not matching_old_files:
                        print(f"未找到与 {new_file} 匹配的旧图，跳过此图像。")
                        continue
                    old_file = matching_old_files[0]

                    # 读取图像
                    new_img_path = os.path.join(self.new_folder, new_file)
                    old_img_path = os.path.join(self.old_folder, old_file)
                    
                    try:
                        # 直接使用fits.getdata读取数据而不处理头信息
                        new_img = fits.getdata(new_img_path)
                        old_img = fits.getdata(old_img_path)
                        
                        # 检查图像维度
                        if len(new_img.shape) > 2:
                            new_img = new_img[0]  # 取第一个通道
                        if len(old_img.shape) > 2:
                            old_img = old_img[0]  # 取第一个通道
                        
                        # 转换为浮点型
                        new_img = new_img.astype(np.float32)
                        old_img = old_img.astype(np.float32)
                        
                        # 使用astroalign进行对齐，支持多项式变换处理畸变
                        try:
                            # 预处理图像以增强星点检测
                            preprocessed_new = self.preprocess_for_alignment(new_img)
                            preprocessed_old = self.preprocess_for_alignment(old_img)
                            
                            # 尝试对齐的辅助函数
                            def try_find_transform(p_new, p_old, r_new, r_old):
                                # 策略1: 预处理图像 + 默认参数
                                try:
                                    return aa.find_transform(p_new, p_old)
                                except Exception:
                                    pass
                                
                                # 策略2: 预处理图像 + 宽松参数
                                try:
                                    return aa.find_transform(p_new, p_old, detection_sigma=3)
                                except Exception:
                                    pass
                                
                                # 策略3: 原始数据 + 宽松参数
                                try:
                                    # 简单的归一化函数
                                    def simple_norm(img):
                                        if img.dtype == np.uint8: return img
                                        _min, _max = np.nanmin(img), np.nanmax(img)
                                        if _max > _min:
                                            return (img - _min) / (_max - _min)
                                        return img
                                    return aa.find_transform(simple_norm(r_new), simple_norm(r_old), detection_sigma=3)
                                except Exception:
                                    pass
                                    
                                return None

                            # 获取匹配点（使用预处理后的图像）
                            trans = None
                            src_pts = None
                            dst_pts = None
                            
                            # 变换模式记录
                            transform_ops = [] # 记录需要的预变换操作: 'flip', 'rot90'

                            # 1. 尝试直接对齐
                            result = try_find_transform(preprocessed_new, preprocessed_old, new_img, old_img)
                            
                            # 2. 如果失败，尝试水平翻转 (解决镜像问题)
                            if result is None:
                                logging.info(f"Direct alignment failed for {new_file}, trying horizontal flip...")
                                p_new_flip = np.fliplr(preprocessed_new)
                                r_new_flip = np.fliplr(new_img)
                                result = try_find_transform(p_new_flip, preprocessed_old, r_new_flip, old_img)
                                if result:
                                    transform_ops.append('flip')
                                    # 更新原始图像用于后续warp
                                    new_img = np.fliplr(new_img)

                            # 3. 如果失败，尝试旋转90度 (解决横竖构图问题)
                            # 注意：可能需要先翻转再旋转，或者直接旋转，这里简化处理，只尝试旋转
                            # 如果之前的翻转失败了，我们尝试旋转原始图像
                            if result is None:
                                logging.info(f"Flip alignment failed for {new_file}, trying 90 degree rotation...")
                                # 尝试旋转 1, 2, 3 次 90度
                                for k in [1, 2, 3]:
                                    p_new_rot = np.rot90(preprocessed_new, k)
                                    r_new_rot = np.rot90(new_img, k)
                                    result = try_find_transform(p_new_rot, preprocessed_old, r_new_rot, old_img)
                                    if result:
                                        transform_ops.append(f'rot90_{k}')
                                        new_img = np.rot90(new_img, k)
                                        break
                            
                            # 4. 如果失败，尝试 翻转 + 旋转
                            if result is None:
                                logging.info(f"Rotation alignment failed for {new_file}, trying flip + rotation...")
                                p_new_flip = np.fliplr(preprocessed_new)
                                r_new_flip = np.fliplr(new_img)
                                for k in [1, 2, 3]:
                                    p_new_comb = np.rot90(p_new_flip, k)
                                    r_new_comb = np.rot90(r_new_flip, k)
                                    result = try_find_transform(p_new_comb, preprocessed_old, r_new_comb, old_img)
                                    if result:
                                        transform_ops.append('flip')
                                        transform_ops.append(f'rot90_{k}')
                                        new_img = np.rot90(np.fliplr(new_img), k)
                                        break

                            if result is None:
                                raise Exception("All alignment strategies and geometric transformations failed")

                            trans, (src_pts, dst_pts) = result
                            
                            # 尝试使用2阶多项式变换（可以处理枕形/桶形畸变）
                            # 至少需要6对点，但为了稳定建议更多
                            # 增加对齐稳定性：
                            # 1. 增加RANSAC迭代次数，过滤异常点
                            # 2. 如果多项式拟合残差过大，回退到Projective或Similarity
                            
                            use_polynomial = False
                            if len(src_pts) > 12: # 稍微提高点数要求
                                try:
                                    logging.info(f"Using Polynomial Transform (Order 2) with {len(src_pts)} points")
                                    
                                    # 预先进行RANSAC筛选，剔除误匹配点
                                    model_robust, inliers = tf.ransac((dst_pts, src_pts), tf.PolynomialTransform, min_samples=6,
                                                                    residual_threshold=2.0, max_trials=500) # residual_threshold单位是像素
                                    
                                    if inliers is not None and np.sum(inliers) > 10:
                                        # 使用筛选后的内点重新拟合
                                        src_pts_in = src_pts[inliers]
                                        dst_pts_in = dst_pts[inliers]
                                        
                                        poly_tf = tf.PolynomialTransform(dimensionality=2)
                                        poly_tf.estimate(dst_pts_in, src_pts_in)
                                        
                                        # 应用变换
                                        aligned_new_img = tf.warp(new_img, poly_tf, 
                                                                output_shape=old_img.shape, order=3, 
                                                                mode='constant', cval=np.median(new_img))
                                        use_polynomial = True
                                    else:
                                        logging.warning("RANSAC filtered too many points, falling back to standard alignment")
                                except Exception as e_poly_fit:
                                    logging.warning(f"Polynomial transform failed: {e_poly_fit}, falling back to standard alignment")
                            
                            if not use_polynomial:
                                # 回退逻辑：
                                # 如果是简单的旋转/翻转，使用apply_transform可能不够（因为它基于find_transform最初的trans）
                                # 如果我们进行了翻转/旋转操作，trans已经是基于变换后的图像计算的，
                                # 所以直接apply_transform(trans, new_img)是正确的，因为此时new_img已经是变换过的了。
                                
                                # 但是，为了更好的精度，如果点数足够，我们可以尝试 ProjectiveTransform (单应性变换)
                                # 它比Similarity更灵活，比Polynomial更稳定
                                if len(src_pts) >= 4:
                                    try:
                                        logging.info("Falling back to Projective Transform")
                                        proj_tf = tf.ProjectiveTransform()
                                        proj_tf.estimate(dst_pts, src_pts)
                                        aligned_new_img = tf.warp(new_img, proj_tf, 
                                                                output_shape=old_img.shape, order=3, 
                                                                mode='constant', cval=np.median(new_img))
                                    except Exception:
                                         logging.warning("Projective transform failed, falling back to Similarity")
                                         aligned_new_img = aa.apply_transform(trans, new_img, old_img)[0]
                                else:
                                    logging.warning("Not enough points for advanced transform, falling back to Similarity")
                                    aligned_new_img = aa.apply_transform(trans, new_img, old_img)[0]
                                
                        except Exception as e_poly:
                            logging.error(f"Advanced alignment failed: {e_poly}")
                            # 记录错误，跳过此文件
                            self.error_signal.emit(f"文件 {new_file} 对齐失败: {str(e_poly)}")
                            print(f"对齐失败 {new_file}: {e_poly}")
                            continue
                        
                        # 保存对齐后的图像
                        aligned_new_img_path = os.path.join(self.aligned_new_folder, new_file)
                        
                        # 创建新的FITS文件
                        hdu_new = fits.PrimaryHDU(aligned_new_img.astype(np.float32))
                        hdu_new.header['OBJECT'] = 'Aligned New Image'
                        hdu_new.writeto(aligned_new_img_path, overwrite=True)
                        
                        print(f"图像 {new_file} 已对齐并保存到 {aligned_new_img_path}")
                    except Exception as e:
                        print(f"处理图像 {new_file} 和 {old_file} 时出现错误: {e}，跳过此图像。")
                        # 如果对齐失败，跳过该图像，不复制原始图像
                        continue
                
                except Exception as e:
                    print(f"处理图像 {new_file} 时出错: {e}，跳过此图像。")
            
            # 发送完成信号
            self.complete_signal.emit()
        
        except Exception as e:
            # 如果有未捕获的异常，发送错误信号
            self.error_signal.emit(str(e))
    
    def cancel(self):
        """取消对齐操作"""
        self.is_canceled = True