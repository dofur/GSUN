# GSUN View (Xing Shi) - Astronomical Image Processing Software

## Project Introduction

GSUN View (Xing Shi) is a professional astronomical image processing software developed by Guoyou Sun. This software is specifically designed for astronomical scientific research and educational purposes, providing powerful FITS file processing, image alignment, flat field correction, and catalog collection functions.

The software was originally designed to replace Astrometrica, Comethunter, and MaxIm in amateur sky surveys, enabling most sky survey viewing and verification tasks in a single software.
PS: For faster installation of requirements.txt, you can use a mirror: pip install -r requirements.txt
**Author**: Guoyou Sun  
**Website**: http://sunguoyou.lamost.org/  
**Version**: 4.1

## Features Under Development
1. Optimization of pseudo-flat field and alignment functions, adding application scenarios for one-click processing of alignment and pseudo-flat field (later implementation of one-click alignment-pseudo-flat field-astrometric solution complete chain, replacing TYCHO)
2. Double-click to get target details (magnitude, coordinates, time, image number, FWHM, etc.), pop up detail box, and obtain MPC 80-character standard data line. Query function integrated into detail box.

We hope capable enthusiasts can help optimize functions and add new features together.

## Asteroid and Comet Database Download
- Comet Database: https://minorplanetcenter.net/iau/MPCORB/CometEls.txt
- Asteroid Database: http://mpcorb.klet.org/ Download MPCORB.DAT (or extract MPCORB.DAT.gz, MPCORB.ZIP)
- Settings - Minor Body Database: Set the database path and place CometEls.txt and MPCORB.DAT in the configured directory.

## Online Astrometric Solution API
You need to register and apply for an API from http://nova.astrometry.net/ and modify the API in settings. Usage instructions: https://nova.astrometry.net/api_help

## Local Astrometric Solution
Local solution requires calling ASTAP. Download and instructions: http://www.hnsky.org/astap.htm. You need to install databases such as D20. In the software ASTAP configuration, configure the path to astap.exe. Software download and database download addresses are available on the instruction page. After downloading the database, install it to the ASTAP main directory. All database files and astap.exe should be placed in the same directory, not in separate directories.

## Version Updates

### v4.1 (2026-03-19)
- Added bilingual interface support (Chinese/English)
- Optimized batch photometry function
- Fixed image flip marker following issues
- Added 90-degree rotation function
- Improved translation system

### v4.0 Official Release (2026-01-10)
- Added batch photometry function, supporting batch photometry of stars and moving objects
- Fixed some image import crash issues
- Added variable star import function
- Added image cropping function

### v3.1 Official Release (2026-01-05)
- Added local astrometric solution function
- Fixed alignment bugs
- Merged asteroid/comet import buttons

### v3.0 Official Release (2026-01-03)
- Added alignment, alignment-subtraction, pseudo-flat field-alignment, pseudo-flat field-alignment-subtraction functions
- Optimized search function (only open to PSP administrators)
- Customizable shortcuts
- Modified alignment bugs
- Fixed asteroid and other marker flip issues

### v2.1 Updates
- Fixed flip and coordinate error bugs
- Optimized Screen Stretch lag issues
- Image import efficiency issues, some image import quality issues
- Optimized pseudo-flat field function, now basically achieves second-level processing
- Optimized alignment function, added separate alignment function (import multiple images of the same sky area to achieve alignment)
- Added automatic writing of multi-image WCS information after successful astrometric solution of multiple sky area images
- And some minor errors

### v2.0 Updates
1. Asteroid/Comet database import function (need to set the folder where the asteroid database MPCORB.DAT is located in settings. MPCORB.DAT download address: http://mpcorb.klet.org/. Comet database: http://www.minorplanetcenter.net/iau/MPCORB/CometEls.txt. After downloading CometEls.txt, place it in the same directory. You can set the limiting magnitude for displaying asteroids in settings. It is strongly recommended to set this, as importing all asteroids can easily cause crashes.)
2. F6 Online blind astrometric solution function
3. Image zoom display added drag bar
4. Automatic animation function (set historical image library and new image folder for automatic alignment and animation creation. Historical image library needs to be accumulated by yourself, and animations will be generated based on recognizing the same file names.)

---

## Main Features

### 1. FITS File Processing
- Support for standard FITS format astronomical image files
- Automatic extraction of WCS coordinate information (limited to Xingming PSP data)
- Image data display and visualization
- Multiple stretching and color mapping options
- Image rotation, flipping, and other basic operations

### 2. Image Alignment Function
- **Alignment**: Align other images using the first image as reference
- **Alignment-Subtraction**: Perform image subtraction after alignment for discovering moving objects
- **Pseudo-Flat Field-Alignment**: Perform pseudo-flat field correction first, then align
- **Pseudo-Flat Field-Alignment-Subtraction**: Complete processing chain (Pseudo-Flat Field → Alignment → Subtraction)
- Batch image alignment processing
- Precise alignment based on star point matching
- Support for multi-frame image sequence processing

### 3. Flat Field Correction
- **Pseudo-Flat Field**: Single flat field correction
- **Batch Pseudo-Flat Field**: Batch flat field correction processing
- Dark field and bias field correction support
- Fast processing, basically achieving second-level processing

### 4. Astrometric Solution
- **Online Solution** (F6): Online blind astrometric solution through nova.astrometry.net
- **Local Solution** (F7): Local astrometric solution using ASTAP
- Automatic WCS information overlay

### 5. Asteroid/Comet Database
- Support for importing MPCORB.DAT asteroid database
- Support for importing CometEls.txt comet database
- Configurable limiting magnitude for displaying asteroids
- Automatic marking of asteroid and comet positions

### 6. Report Function
- **Report Positioning** (F4): Report positioning function
- **Generate Report** (F8): Generate observation reports
- Automatic report data parsing
- Support for MPC 80-character standard data lines

### 7. Catalog Collection (Only for Xingming Administrators)
- Automatic collection of catalog data from China-VO and other data sources
- Support for filtering data by year and month
- Data tabular display and export

### 8. Batch Photometry Function
- **Aperture Photometry**: Support for circular aperture photometry with adjustable aperture radius, inner radius, and outer radius
- **Reference Star Selection**: Support for manual selection of reference stars, automatic acquisition of UCAC4 magnitudes
- **Target Star Measurement**: Support for measuring target star magnitudes and flux
- **Batch Processing**: Support for batch photometry of multiple images
- **Result Export**: Photometry results can be exported in CSV format
- **Real-time Display**: Photometry results displayed in real-time, including magnitude, flux, signal-to-noise ratio, and other parameters

### 9. Visualization Interface
- Modern graphical interface based on PyQt5
- Multi-tab workspace
- Real-time image preview and processing
- Historical operation records
- Customizable shortcut support
- Automatic animation function
- Image stacking mode

## System Requirements

### Hardware Requirements
- Processor: Intel Core i5 or equivalent performance or higher
- Memory: 8GB RAM or more (16GB recommended)
- Storage: At least 1GB available space
- Display: 1920x1080 resolution or higher

### Software Requirements
- Operating System: Windows 10/11, Linux, macOS
- Python: 3.8 or higher

## Installation Guide

### Method 1: Using Pre-configured Environment (Recommended)

1. Ensure Python 3.8+ is installed
2. Install dependencies:
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

### Method 2: Manual Installation

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
pip install photutils==1.9.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## Quick Start

### Windows Users
1. Double-click to run `启动GSUNView.bat` file
2. Or use command line:
   ```bash
   python GSUNView.py
   ```

### Linux/macOS Users
```bash
python3 GSUNView.py
```

## Usage Instructions

### Basic Operation Process

1. **Open Image Files**
   - Click "File" → "Open" to select FITS files
   - Support for multiple selection and batch processing

2. **Image Processing**
   - Use toolbar to adjust image display parameters
   - Apply different stretching and color mapping
   - View image metadata and WCS information

3. **Batch Processing**
   - Use "Batch Alignment" function to process image sequences
   - Use "Flat Field Correction" function to correct images
   - Monitor processing progress and results

4. **Catalog Collection** (Not yet open)
   - Open "Catalog Collection" dialog
   - Select data source and time range
   - Start collection and view results

### Shortcuts

#### File Operations
- **F1**: Import images
- **Ctrl+S**: Save image

#### Image Navigation
- **Left**: Previous image
- **Right**: Next image

#### Image Processing
- **Ctrl+1**: Switch mouse wheel function (switch image/zoom image)
- **Ctrl+2**: Horizontal flip image
- **Ctrl+3**: Vertical flip image
- **Ctrl+4**: Rotate left 90 degrees
- **Ctrl+5**: Rotate right 90 degrees
- **Alt+D**: Auto histogram adjustment

#### Core Functions
- **F2**: Play/Pause animation
- **F4**: Report positioning function
- **F5**: Stack image mode
- **F6**: Online astrometric solution (nova.astrometry.net)
- **F7**: Local astrometric solution (ASTAP)
- **F8**: Generate report
- **F9**: Import asteroid/comet database

#### Notes
- Shortcuts can be customized through `shortcuts.json` configuration file
- F1 key is used for importing images, not displaying help documentation
- F6 and F7 correspond to online and local astrometric solution methods respectively

## File Structure

```
GSUN Check/
├── GSUNView.py                 # Main program file
├── photometry_module.py        # Batch photometry module
├── app.py                      # Image processing core module
├── BatchAlignThread.py         # Batch alignment thread
├── BatchAlignNewThread.py      # New batch alignment thread
├── BatchFlatfieldThread.py     # Batch flat field thread
├── SingleFlatfieldThread.py    # Single flat field thread
├── ListFlatfieldThread.py      # List flat field thread
├── catalog_collector.py        # Catalog collection module
├── coordinate_parser.py        # Coordinate parser
├── history_logger.py           # History logger
├── screen_stretch.py           # Screen stretch processing
├── image_algorithms.py         # Image algorithm module
├── asteroid_worker.py          # Asteroid processing module
├── astrometric_solver.py       # Astrometric solver
├── catalog_query.py            # Catalog query module
├── config.ini                  # Configuration file
├── catalog_collector_config.ini # Catalog collection configuration
├── image_viewer_config.json    # Image viewer configuration
├── screen_stretch_config.json  # Screen stretch configuration
├── shortcuts.json              # Shortcut configuration
├── requirements.txt            # Python dependency list
├── logo.jpg                    # Program icon
└── 启动GSUNView.bat           # Windows startup script
```

## Configuration Instructions

### config.ini Configuration File

The program will automatically generate a configuration file containing the following main settings:

```ini
[database]
path = H:\catalog_grappa3e

coordinates]
center_ra = 0.0
center_dec = 0.0
fov_width = 1.0
fov_height = 1.0
pixel_scale = 1.0
search_radius = 0.5
```

### Custom Configuration

Users can edit the `config.ini` file to customize program behavior, including:
- Database path
- Default coordinate settings
- Image processing parameters
- Network connection settings

## Technical Support

### FAQ

1. **Cannot open FITS files**
   - Check if the file format is correct
   - Ensure sufficient read permissions

2. **Dependency package installation failed**
   - Try using conda environment
   - Or use a newer version of Python

3. **Image display abnormal**
   - Check if image data is valid
   - Try adjusting display parameters

### Get Help

- View built-in help documentation
- Visit author's website: http://sunguoyou.lamost.org/
- Check log files for detailed error information

## Update Log

### v4.1 (2026-03-19)
- Added bilingual interface support (Chinese/English)
- Optimized batch photometry function
- Fixed image flip marker following issues
- Added 90-degree rotation function
- Improved translation system

### v4.0 (2026-01-10)
- Added batch photometry function
- Fixed some image import crash issues
- Added variable star import function
- Added image cropping function

### v3.1 (2026-01-05)
- Added local astrometric solution function
- Fixed alignment bugs
- Merged asteroid/comet import buttons

## Copyright Notice

Copyright © 2025-2030 Guoyou Sun (Sun Guoyou, Xingti Shoucangjia)

**Disclaimer**:
This software is an original work for astronomical scientific research and educational purposes only.
Commercial use, copying, distribution, or modification of this software is prohibited without explicit permission from the author.
The author is not responsible for any direct or indirect losses caused by using this software.

---

**Developer**: Guoyou Sun (Xingti Shoucangjia)  
**Website**: http://sunguoyou.lamost.org/  
**Version**: 4.1
