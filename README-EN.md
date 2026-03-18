# GSUN View (StarVision) - Astronomical Image Processing Software

## Project Introduction
GSUN View (StarVision) is a professional astronomical image processing software developed by Guoyou Sun.
It is designed for astronomical research and education, providing powerful FITS processing, image alignment, flat-field correction, and catalog acquisition.

This software aims to replace Astrometrica, Comethunter, MaxIm in amateur sky surveys, allowing most survey inspection tasks in one tool.

> Tip: Use Tsinghua mirror for faster dependency installation:
> `pip install -r requirements.txt`

**Author**: Guoyou Sun
**Website**: [http://sunguoyou.lamost.org/](http://sunguoyou.lamost.org/)
**Version**: 3.1

---

## Unimplemented Features
1. Photometric magnitude calculation (local catalog conversion)
2. Optimize pseudo flat-field and alignment; add one-click full processing pipeline (alignment → flat-field → solve) to replace TYCHO
3. After photometry: double-click for target details (magnitude, coordinates, FWHM, etc.) with MPC 80-character output and query tool

Contributions from astronomy enthusiasts are welcome.

---

## Asteroid & Comet Database Download
- Comet database: [https://minorplanetcenter.net/iau/MPCORB/CometEls.txt](https://minorplanetcenter.net/iau/MPCORB/CometEls.txt)
- Asteroid database: [http://mpcorb.klet.org/](http://mpcorb.klet.org/) (download MPCORB.DAT or extract from .gz/.zip)

Place both files in your configured database path.

---

## Online Astrometry API
Register API at [https://nova.astrometry.net/](https://nova.astrometry.net/)
Docs: [https://nova.astrometry.net/api_help](https://nova.astrometry.net/api_help)

---

## Local Astrometry (ASTAP)
Download ASTAP: [http://www.hnsky.org/astap.htm](http://www.hnsky.org/astap.htm)
Install database (e.g., D20) in the same folder as `astap.exe`.

---

## Version History

### 4.0 Official (2026-01-10)
- Added batch photometry for stars and moving objects
- Fixed import crash issues
- Added variable star import
- Added image crop

### 3.1 Official (2026-01-05)
- Added local astrometry
- Fixed alignment bugs
- Merged asteroid/comet import button

### 3.0 Official (2026-01-03)
- Added alignment, alignment subtract, pseudo flat + alignment, pseudo flat + alignment + subtract
- Optimized search (PSP admin only)
- Custom shortcuts
- Fixed marker rotation/flip issues

### 2.1
- Fixed flip and coordinate bugs
- Optimized Screen Stretch performance
- Optimized pseudo flat-field (near instant)
- Optimized alignment
- Auto write WCS for multiple images

### 2.0
- Asteroid/comet database support
- F6: Online blind solve
- Image zoom sliders
- Auto animation

---

## Main Features

### FITS File Processing
- Standard FITS support
- Auto WCS extraction
- Multiple stretch and colormap modes
- Rotate, flip, visualize

### Image Alignment
- Align
- Align + Subtract
- Pseudo Flat + Align
- Pseudo Flat + Align + Subtract
- Batch processing
- Star-matching based alignment

### Flat-Field Correction
- Pseudo flat-field (single/batch)
- Dark and bias support
- High-speed processing

### Astrometric Solver
- F6: Online solve (nova.astrometry.net)
- F7: Local solve (ASTAP)
- Auto WCS update

### Asteroid / Comet Database
- MPCORB.DAT support
- CometEls.txt support
- Limiting magnitude setting
- Auto mark objects

### Reporting
- F4: Report positioning
- F8: Generate observation report
- MPC 80-character format support

### GUI & Visualization
- PyQt5 interface
- Multi-tab workspace
- Custom shortcuts
- Animation mode
- Image overlay

---

## System Requirements

### Hardware
- CPU: Intel i5 or better
- RAM: 8GB+ (16GB recommended)
- Storage: 1GB+ free space
- Display: 1920x1080+

### Software
- OS: Windows 10/11, Linux, macOS
- Python: 3.8+

---


## Installation

### Recommended
```bash
pip install -r requirements.txt
