"""
小行星数据处理模块 - Asteroid Worker

作者：Guoyou Sun (孙国佑) - 天体收藏家
软件：星视 GSUN View V4.0
网站：sunguoyou.lamost.org
标识：546756
原创作品，禁止商业使用
"""

import numpy as np
from datetime import datetime

def _unpack_packed_date(s):
    if not s or len(s) < 5:
        return None
    c1 = s[0]
    yy = int(s[1:3])
    if c1 == 'I':
        year = 1800 + yy
    elif c1 == 'J':
        year = 1900 + yy
    elif c1 == 'K':
        year = 2000 + yy
    else:
        return None
    def decode_md(ch):
        if ch.isdigit():
            return int(ch)
        table = {
            'A':10,'B':11,'C':12,'D':13,'E':14,'F':15,'G':16,'H':17,'I':18,'J':19,
            'K':20,'L':21,'M':22,'N':23,'O':24,'P':25,'Q':26,'R':27,'S':28,'T':29,
            'U':30,'V':31
        }
        return table.get(ch, 1)
    month = decode_md(s[3])
    day = decode_md(s[4])
    try:
        return datetime(year, month, day)
    except Exception:
        return None

def _parse_line(line):
    if len(line) < 160:
        return None
    try:
        packed_id = line[0:7].strip()
        H = float(line[8:13].strip()) if line[8:13].strip() else None
        G = float(line[14:19].strip()) if line[14:19].strip() else 0.15
        epoch_packed = line[20:25].strip()
        M0 = float(line[26:35].strip())
        w = float(line[37:46].strip())
        Omega = float(line[48:57].strip())
        inc = float(line[59:68].strip())
        e = float(line[70:79].strip())
        n = float(line[80:91].strip())
        a = float(line[92:103].strip())
        name = line[166:194].strip()
        return {
            'id': packed_id,
            'name': name,
            'H': H,
            'G': G,
            'epoch_packed': epoch_packed,
            'M0': M0,
            'w': w,
            'Omega': Omega,
            'i': inc,
            'e': e,
            'n': n,
            'a': a
        }
    except Exception:
        return None

def _kepler_position(elems, dt_days):
    e = elems['e']
    a = elems['a']
    M = np.deg2rad((elems['M0'] + elems['n'] * dt_days) % 360.0)
    E = M
    for _ in range(15):
        f = E - e * np.sin(E) - M
        fp = 1 - e * np.cos(E)
        dE = -f / fp
        E += dE
        if abs(dE) < 1e-10:
            break
    nu = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(E / 2), np.sqrt(1 - e) * np.cos(E / 2))
    r = a * (1 - e * np.cos(E))
    x_orb = r * np.cos(nu)
    y_orb = r * np.sin(nu)
    z_orb = 0.0
    w = np.deg2rad(elems['w'])
    Omega = np.deg2rad(elems['Omega'])
    inc = np.deg2rad(elems['i'])
    cosw, sinw = np.cos(w), np.sin(w)
    cosO, sinO = np.cos(Omega), np.sin(Omega)
    cosi, sini = np.cos(inc), np.sin(inc)
    x1 = cosw * x_orb - sinw * y_orb
    y1 = sinw * x_orb + cosw * y_orb
    z1 = z_orb
    x2 = x1
    y2 = cosi * y1
    z2 = sini * y1
    xe = cosO * x2 - sinO * y2
    ye = sinO * x2 + cosO * y2
    ze = z2
    eps = np.deg2rad(23.43928)
    xq = xe
    yq = np.cos(eps) * ye - np.sin(eps) * ze
    zq = np.sin(eps) * ye + np.cos(eps) * ze
    return np.array([xq, yq, zq]), r

def _hg_magnitude(H, G, r, delta, phase_deg):
    if H is None:
        return None
    alpha = np.deg2rad(phase_deg)
    tan_a2 = np.tan(alpha / 2)
    phi1 = np.exp(-3.33 * np.power(tan_a2, 0.63))
    phi2 = np.exp(-1.87 * np.power(tan_a2, 1.22))
    return H + 5 * np.log10(max(r, 1e-6) * max(delta, 1e-6)) - 2.5 * np.log10((1 - G) * phi1 + G * phi2)

def process_chunk(chunk_lines, ex, ey, ez, cx, cy, rad, obs_ts, mag_limit=None):
    out = []
    obs_dt = datetime.fromtimestamp(obs_ts)
    for ln in chunk_lines:
        d = _parse_line(ln)
        if not d:
            continue
        epoch_dt = _unpack_packed_date(d['epoch_packed'])
        if not epoch_dt:
            continue
        dt_days = (obs_dt - epoch_dt).days + (obs_dt - epoch_dt).seconds / 86400.0
        pos_vec, r = _kepler_position(d, dt_days)
        gx = pos_vec[0] - ex
        gy = pos_vec[1] - ey
        gz = pos_vec[2] - ez
        delta = np.sqrt(gx * gx + gy * gy + gz * gz)
        ra = (np.degrees(np.arctan2(gy, gx)) + 360.0) % 360.0
        dec = np.degrees(np.arctan2(gz, np.sqrt(gx * gx + gy * gy)))
        dra = (ra - cx + 540.0) % 360.0 - 180.0
        dec1 = np.deg2rad(cy)
        dec2 = np.deg2rad(dec)
        dra_rad = np.deg2rad(dra)
        hav = np.sin((dec2 - dec1) / 2.0) ** 2 + np.cos(dec1) * np.cos(dec2) * np.sin(dra_rad / 2.0) ** 2
        ang_sep = np.degrees(2.0 * np.arcsin(np.sqrt(np.clip(hav, 0.0, 1.0))))
        if ang_sep <= rad:
            try:
                ae = np.array([-gx, -gy, -gz])  # 小行星->地球
                asun = -pos_vec                 # 小行星->太阳
                phase = np.degrees(np.arccos(np.clip(np.dot(asun, ae) / (np.linalg.norm(pos_vec) * delta), -1.0, 1.0)))
                mag = _hg_magnitude(d['H'], d['G'], r, delta, phase)
                if mag_limit is not None and mag is not None and mag > mag_limit:
                    continue
                label = d['name'] if d['name'] else d['id']
                if mag is not None:
                    label = f"{label} V{mag:.1f}"
                out.append({'ra': float(ra), 'dec': float(dec), 'label': label})
            except Exception:
                pass
    return out