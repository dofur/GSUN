# GSUN View（星视） - 天文图像处理软件

## 项目简介

GSUN View（星视）是一款专业的天文图像处理软件，由孙国佑（Guoyou Sun）开发。该软件专门用于天文科学研究和教育目的，提供强大的FITS文件处理、图像对齐、平场校正和星表采集功能。
软件初衷在业余巡天中替代Astrometrica，comethunter，MaxIm等软件，可以做到一个软件实现绝大部分巡天看图和查验工作。
PS:requirements.txt安装可以用镜像，速度更快，pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

**作者**: 孙国佑 (Guoyou Sun)  
**网站**: http://sunguoyou.lamost.org/  
**版本**: 4.1  
 
尚未开发功能
1，优化伪平场和对齐功能（待优化），增加伪平场和对齐功能的应用场景，一键处理对齐和伪平场功能（后期实现一键对齐-伪平场-解析完整链条，替代TYCHO）。
2，双击获取目标详情（星等，坐标，时间，图号，fwhn，等等），跳出详情框，可获取MPC 80字符标准数据行。查询功能，集成到详情框中。
希望有能力的爱好者，帮忙一起优化功能，添加新功能。

小行星，彗星数据库下载
彗星数据库：https://minorplanetcenter.net/iau/MPCORB/CometEls.txt
小行星数据库：http://mpcorb.klet.org/  下载MPCORB.DAT（或者把MPCORB.DAT.gz，MPCORB.ZIP 解压）
设置-小天体数据库，设置数据库路径，把CometEls.txt和MPCORB.DAT放在设置的目录中。

在线解析API
需要自行注册申请http://nova.astrometry.net/ 的API，修改设置中的API。使用说明：https://nova.astrometry.net/api_help。

本地解析
本地解析需要调用ASTAP，下载及说明：http://www.hnsky.org/astap.htm。需要安装数据库如D20。在软件ASTAP配置中，配置软件astap.exe路径。软件下载，数据库下载地址在说明页面中都有，数据库下载后安装到ASTAP主目录，所有数据库文件和astap.exe放在一个目录中，不要单独一个目录。

### 版本更新

4.1正式版 2026-03-19
增加双语界面支持（中文/英文）；优化批量测光功能；修复图像翻转标记跟随问题；增加90度旋转功能；完善翻译系统

4.0正式版 2026-01-10
增加批量测光功能，支持恒星及运动天体批量测光；修复部分图片导入闪退问题；增加导入变星功能；增加图片剪切功能

3.1正式版 2026-01-05
增加本地解析功能；修复对齐bug；合并小行星/彗星导入按钮

3.0正式版 2026-01-03
增加对齐，对齐-相减，伪平场-对齐，伪平场-对齐-相减功能；优化搜索功能（仅开放给PSP管理员）；自定义快捷键；修改对齐bug；修复小行星等标记翻转不跟随

2.1版本更新功能
修复翻转，坐标错误bug；优化Screen Stretch的卡顿问题；图片导入效率问题，部分图片导入效果不佳问题；优化伪平场功能，目前基本实现秒处理；优化对齐功能，增加单独对齐功能（导入多张同天区图片，实现对齐）；增加多张天区图片解析成功，自动写入多图wcs信息；以及一些小错误。

2.0版本更新功能
1，小行星/彗星数据库导入功能（需要再设置中设置小行星数据库MPCORB.DAT所在文件夹，MPCORB.DAT下载地址http://mpcorb.klet.org/。彗星数据库: http://www.minorplanetcenter.net/iau/MPCORB/CometEls.txt，CometEls.txt下载后放在同一目录，可在设置中设置显示小行星的极限星等，强烈建议设置，导入全部小行星容易卡死。）
2，F6 在线盲解功能
3，图片放大显示增加拖动条
4，自动动画功能（设置历史图库，新图文件夹，可以自动对齐制作动画。历史图库需要自行积累，会根据识别相同文件名来生成动画。）

----------
## 主要功能

### 1. FITS文件处理
- 支持标准FITS格式天文图像文件
- 自动提取WCS坐标信息（仅限星明PSP数据）
- 图像数据显示和可视化
- 多种拉伸和色彩映射选项
- 图像旋转、翻转等基本操作

### 2. 图像对齐功能
- **对齐**：以第一张图为基准对齐其他图片
- **对齐-相减**：对齐后进行图像相减，用于发现移动天体
- **伪平场-对齐**：先进行伪平场校正，再对齐
- **伪平场-对齐-相减**：完整的处理链条（伪平场→对齐→相减）
- 批量图像对齐处理
- 基于星点匹配的精确对齐
- 支持多帧图像序列处理

### 3. 平场校正
- **伪平场**：单张平场校正
- **批量伪平场**：批量平场校正处理
- 暗场和偏置场校正支持
- 快速处理，基本实现秒处理

### 4. 天文测量解析
- **在线解析**（F6）：通过nova.astrometry.net进行在线盲解
- **本地解析**（F7）：调用ASTAP进行本地解析
- 自动覆盖WCS信息

### 5. 小行星/彗星数据库
- 支持导入MPCORB.DAT小行星数据库
- 支持导入CometEls.txt彗星数据库
- 可设置显示小行星的极限星等
- 自动标记小行星和彗星位置

### 6. 报告功能
- **报告定位**（F4）：定位报告功能
- **生成报告**（F8）：生成观测报告
- 自动解析报告数据
- 支持MPC 80字符标准数据行

### 7. 星表采集（只针对星明管理员）
- 自动从中国虚拟天文台等数据源采集星表数据
- 支持按年份和月份筛选数据
- 数据表格化显示和导出

### 8. 批量测光功能
- **孔径测光**：支持圆形孔径测光，可调整孔径半径、内环半径、外环半径
- **参考星选择**：支持手动选择参考星，自动获取UCAC4星等
- **目标星测量**：支持测量目标星的星等和流量
- **批量处理**：支持对多张图像进行批量测光
- **结果导出**：测光结果可导出为CSV格式
- **实时显示**：测光结果实时显示，包括星等、流量、信噪比等参数

### 9. 可视化界面
- 基于PyQt5的现代化图形界面
- 多标签页工作区
- 实时图像预览和处理
- 历史操作记录
- 自定义快捷键支持
- 自动动画功能
- 图像叠加模式

## 系统要求

### 硬件要求
- 处理器: Intel Core i5 或同等性能以上
- 内存: 8GB RAM 或更多（推荐16GB）
- 存储空间: 至少1GB可用空间
- 显示器: 1920x1080分辨率或更高

### 软件要求
- 操作系统: Windows 10/11, Linux, macOS
- Python: 3.8 或更高版本

## 安装指南

### 方法一：使用预配置环境（推荐）

1. 确保已安装Python 3.8+ 
2. 安装依赖包：
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

### 方法二：手动安装依赖

```bash
pip install numpy==1.24.3 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install pandas==2.0.3 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install matplotlib==3.7.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install astropy==5.3.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install Pillow==10.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install PyQt5==5.15.9 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install PyQtWebEngine==5.15.6 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install plotly==5.15.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install astroquery==0.4.6 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install requests==2.31.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install beautifulsoup4==4.12.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install astroalign==0.9.1 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install scipy==1.11.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install scikit-image==0.21.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install opencv-python==4.8.0.76 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 快速开始

### Windows用户
1. 双击运行 `启动GSUNView.bat` 文件
2. 或使用命令行：
   ```bash
   python GSUNView.py
   ```

### Linux/macOS用户
```bash
python3 GSUNView.py
```

## 使用说明

### 基本操作流程

1. **打开图像文件**
   - 点击"文件" → "打开" 选择FITS文件
   - 支持多选和批量处理

2. **图像处理**
   - 使用工具栏调整图像显示参数
   - 应用不同的拉伸和色彩映射
   - 查看图像元数据和WCS信息

3. **批量处理**
   - 使用"批量对齐"功能处理图像序列
   - 使用"平场校正"功能校正图像
   - 监控处理进度和结果

4. **星表采集**（暂不开放）
   - 打开"星表采集"对话框
   - 选择数据源和时间范围
   - 开始采集并查看结果

### 快捷键

#### 文件操作
- **F1** : 导入图片
- **Ctrl+S** : 保存图片

#### 图像导航
- **Left** : 上一张图片
- **Right** : 下一张图片

#### 图像处理
- **Ctrl+1** : 切换鼠标滚轮功能（切换图片/放大图片）
- **Ctrl+2** : 水平翻转图像
- **Ctrl+3** : 垂直翻转图像
- **Ctrl+4** : 向左旋转90度
- **Ctrl+5** : 向右旋转90度
- **Alt+D** : 自动直方图调整

#### 核心功能
- **F2** : 播放/暂停动画
- **F4** : 报告定位功能
- **F5** : 叠加图像模式
- **F6** : 在线解析功能（nova.astrometry.net）
- **F7** : 本地解析功能（ASTAP）
- **F8** : 生成报告
- **F9** : 导入小行星/彗星数据库

#### 说明
- 快捷键可以通过 `shortcuts.json` 配置文件自定义
- F1键用于导入图片，不显示帮助文档
- F6和F7分别对应在线和本地两种解析方式

## 文件结构

```
GSUN Check/
├── GSUNView.py                 # 主程序文件
├── photometry_module.py        # 批量测光模块
├── app.py                      # 图像处理核心模块
├── BatchAlignThread.py         # 批量对齐线程
├── BatchAlignNewThread.py      # 新批量对齐线程
├── BatchFlatfieldThread.py     # 批量平场线程
├── SingleFlatfieldThread.py    # 单张平场线程
├── ListFlatfieldThread.py      # 列表平场线程
├── catalog_collector.py        # 星表采集模块
├── coordinate_parser.py        # 坐标解析器
├── history_logger.py           # 历史记录器
├── screen_stretch.py           # 屏幕拉伸处理
├── image_algorithms.py         # 图像算法模块
├── asteroid_worker.py          # 小行星处理模块
├── astrometric_solver.py       # 天文测量解析器
├── catalog_query.py            # 星表查询模块
├── config.ini                  # 配置文件
├── catalog_collector_config.ini # 星表采集配置
├── image_viewer_config.json    # 图像查看器配置
├── screen_stretch_config.json  # 屏幕拉伸配置
├── shortcuts.json              # 快捷键配置
├── requirements.txt            # Python依赖包列表
├── logo.jpg                    # 程序图标
└── 启动GSUNView.bat           # Windows启动脚本
```

## 配置说明

### config.ini 配置文件

程序会自动生成配置文件，包含以下主要设置：

```ini
[database]
path = H:\catalog_grappa3e

[coordinates]
center_ra = 0.0
center_dec = 0.0
fov_width = 1.0
fov_height = 1.0
pixel_scale = 1.0
search_radius = 0.5
```

### 自定义配置

用户可以编辑 `config.ini` 文件来自定义程序行为，包括：
- 数据库路径
- 默认坐标设置
- 图像处理参数
- 网络连接设置

## 技术支持

### 常见问题

1. **无法打开FITS文件**
   - 检查文件格式是否正确
   - 确保有足够的读取权限

2. **依赖包安装失败**
   - 尝试使用conda环境
   - 或使用较新版本的Python

3. **图像显示异常**
   - 检查图像数据是否有效
   - 尝试调整显示参数

### 获取帮助

- 查看程序内置帮助文档
- 访问作者网站: http://sunguoyou.lamost.org/
- 查看日志文件获取详细错误信息

## 更新日志

### v3.1 (2026-01-05)
- 增加本地解析功能
- 修复对齐bug
- 合并小行星/彗星导入按钮

### v3.0 (2026-01-03)
- 增加对齐，对齐-相减，伪平场-对齐，伪平场-对齐-相减功能
- 优化搜索功能（仅开放给PSP管理员）
- 自定义快捷键
- 修改对齐bug
- 修复小行星等标记翻转不跟随

### v2.1
- 修复翻转，坐标错误bug
- 优化Screen Stretch的卡顿问题
- 图片导入效率问题，部分图片导入效果不佳问题
- 优化伪平场功能，目前基本实现秒处理
- 优化对齐功能，增加单独对齐功能（导入多张同天区图片，实现对齐）
- 增加多张天区图片解析成功，自动写入多图wcs信息
- 以及一些小错误

### v2.0
- 小行星/彗星数据库导入功能（需要再设置中设置小行星数据库MPCORB.DAT所在文件夹，MPCORB.DAT下载地址http://mpcorb.klet.org/。彗星数据库: http://www.minorplanetcenter.net/iau/MPCORB/CometEls.txt，CometEls.txt下载后放在同一目录，可在设置中设置显示小行星的极限星等，强烈建议设置，导入全部小行星容易卡死。）
- F6 在线盲解功能
- 图片放大显示增加拖动条
- 自动动画功能（设置历史图库，新图文件夹，可以自动对齐制作动画。历史图库需要自行积累，会根据识别相同文件名来生成动画。）

### v1.0 (2025)
- 初始版本发布
- 基本FITS文件处理功能
- 图像对齐和平场校正
- 星表采集功能
- 图形用户界面

## 许可证

版权所有 © 2025-2030 孙国佑 (Guoyou Sun)

本软件为原创作品，仅用于天文科学研究和教育目的。未经作者明确许可，禁止商业使用、复制、分发或修改本软件。

## 免责声明

作者对使用本软件导致的任何直接或间接损失不承担责任。使用者应自行承担风险。

---

*最后更新: 2025年*
