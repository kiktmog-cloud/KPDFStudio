import sys, io
if sys.platform == 'win32':
    try:
        if getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

import os
import re
import json
import copy
import math
import uuid
import struct
import winreg
import ctypes
import ctypes.wintypes
import subprocess
import time
import tempfile
import shutil
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import pymupdf as fitz

from PyQt6.QtCore import Qt, QRectF, QPointF, QPoint, QSize, QSizeF, pyqtSignal, QBuffer, QIODevice, QTimer, QEvent, QFileSystemWatcher, QCoreApplication, QMimeData
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QPen, QColor, QBrush, QFont, QFontDatabase,
    QAction, QKeySequence, QPolygonF, QCursor, QIcon, QPalette,
    QPageSize, QPageLayout, QTextCharFormat, QTextCursor, QTextFormat,
    QLinearGradient, QPainterPath, QDragEnterEvent, QDropEvent, QShortcut, QDrag
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QListView, QScrollArea, QToolBar, QStatusBar, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QLineEdit,
    QTextEdit, QFileDialog, QMessageBox, QColorDialog, QDialog, QFormLayout,
    QGroupBox, QRadioButton, QButtonGroup, QSlider, QAbstractItemView,
    QMenu, QStackedWidget, QTabBar, QStyledItemDelegate, QStyleOptionViewItem,
    QStyle, QToolTip, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QProgressDialog, QGridLayout, QDialogButtonBox
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrinterInfo
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


# =====================================================================
# 0. Windows Theme Detection & High-Contrast Indicator Icon Generator
# =====================================================================

def detect_windows_use_dark_theme() -> bool:
    """Reads Windows Registry to check if Windows Personalization is set to Dark Mode."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return int(val) == 0
    except Exception:
        return False


def ensure_ui_indicator_icons() -> Dict[str, str]:
    """
    Generates crisp 18x18 PNG icons for QCheckBox and QRadioButton indicators
    so that unchecked and checked states are 100% visible in Light, Dark, and System themes.
    """
    icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ui_icons")
    os.makedirs(icon_dir, exist_ok=True)
    paths: Dict[str, str] = {}

    def _save_pix(name: str, draw_fn):
        fp = os.path.join(icon_dir, f"{name}.png")
        if os.path.exists(fp) and os.path.getsize(fp) > 0:
            paths[name] = fp.replace("\\", "/")
            return
        img = QImage(36, 36, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_fn(p)
        p.end()
        img.save(fp, "PNG")
        paths[name] = fp.replace("\\", "/")

    # 1. Checkbox Unchecked (Light Mode)
    def _chk_un_light(p: QPainter):
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.setPen(QPen(QColor(71, 85, 105), 3.2))
        p.drawRoundedRect(QRectF(4, 4, 28, 28), 5, 5)

    # 2. Checkbox Unchecked (Dark Mode)
    def _chk_un_dark(p: QPainter):
        p.setBrush(QBrush(QColor(30, 41, 59)))
        p.setPen(QPen(QColor(148, 163, 184), 3.2))
        p.drawRoundedRect(QRectF(4, 4, 28, 28), 5, 5)

    # 3. Checkbox Checked (Both Modes)
    def _chk_checked(p: QPainter):
        p.setBrush(QBrush(QColor(37, 99, 235)))
        p.setPen(QPen(QColor(29, 78, 216), 2.5))
        p.drawRoundedRect(QRectF(4, 4, 28, 28), 5, 5)
        pen = QPen(QColor(255, 255, 255), 4.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawLine(QPointF(10, 18.5), QPointF(15.5, 24.5))
        p.drawLine(QPointF(15.5, 24.5), QPointF(26.5, 11.5))

    # 4. Radio Unchecked (Light Mode)
    def _rad_un_light(p: QPainter):
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.setPen(QPen(QColor(71, 85, 105), 3.2))
        p.drawEllipse(QRectF(4, 4, 28, 28))

    # 5. Radio Unchecked (Dark Mode)
    def _rad_un_dark(p: QPainter):
        p.setBrush(QBrush(QColor(30, 41, 59)))
        p.setPen(QPen(QColor(148, 163, 184), 3.2))
        p.drawEllipse(QRectF(4, 4, 28, 28))

    # 6. Radio Checked (Both Modes)
    def _rad_checked(p: QPainter):
        p.setBrush(QBrush(QColor(37, 99, 235)))
        p.setPen(QPen(QColor(29, 78, 216), 2.5))
        p.drawEllipse(QRectF(4, 4, 28, 28))
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(11.5, 11.5, 13, 13))

    _save_pix("chk_un_light", _chk_un_light)
    _save_pix("chk_un_dark", _chk_un_dark)
    _save_pix("chk_checked", _chk_checked)
    _save_pix("rad_un_light", _rad_un_light)
    _save_pix("rad_un_dark", _rad_un_dark)
    _save_pix("rad_checked", _rad_checked)
    return paths


def ensure_app_icon() -> str:
    """Generates a modern multi-size app_icon.ico and app_icon.png for K-PDF Studio if not present."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(base_dir, "app_icon.ico")
    png_path = os.path.join(base_dir, "app_icon.png")
    if os.path.exists(ico_path):
        return ico_path

    try:
        def _render_icon_png(sz: int) -> bytes:
            img = QImage(sz, sz, QImage.Format.Format_ARGB32)
            img.fill(0)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

            path = QPainterPath()
            path.addRoundedRect(sz * 0.06, sz * 0.06, sz * 0.88, sz * 0.88, sz * 0.18, sz * 0.18)

            grad = QLinearGradient(0, 0, sz, sz)
            grad.setColorAt(0.0, QColor(220, 38, 38))
            grad.setColorAt(1.0, QColor(153, 27, 27))
            p.fillPath(path, grad)

            fold = QPainterPath()
            fold.moveTo(sz * 0.60, sz * 0.06)
            fold.lineTo(sz * 0.94, sz * 0.40)
            fold.lineTo(sz * 0.60, sz * 0.40)
            fold.closeSubpath()
            p.fillPath(fold, QColor(255, 255, 255, 110))

            p.setPen(QColor(255, 255, 255))
            font = QFont("Malgun Gothic", int(sz * 0.40), QFont.Weight.Black)
            p.setFont(font)
            p.drawText(int(sz * 0.16), int(sz * 0.60), "K")

            sub_font = QFont("Arial", int(sz * 0.18), QFont.Weight.Bold)
            p.setFont(sub_font)
            p.setPen(QColor(254, 240, 138))
            p.drawText(int(sz * 0.20), int(sz * 0.82), "PDF")
            p.end()

            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            img.save(buf, "PNG")
            return bytes(buf.data())

        sizes = (256, 128, 64, 48, 32, 16)
        pngs = [_render_icon_png(s) for s in sizes]
        header = struct.pack("<HHH", 0, 1, len(pngs))
        offset = 6 + 16 * len(pngs)
        entries = []
        for sz, png in zip(sizes, pngs):
            w = 0 if sz == 256 else sz
            h = 0 if sz == 256 else sz
            entry = struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png), offset)
            entries.append(entry)
            offset += len(png)

        with open(ico_path, "wb") as f:
            f.write(header + b"".join(entries) + b"".join(pngs))
        with open(png_path, "wb") as f:
            f.write(pngs[0])
    except Exception:
        pass
    return ico_path


# =====================================================================
# 1. All-PC Font Registry & Korean Smart Fallback Engine
#    (Scans all installed Korean + English/System fonts on the PC)
# =====================================================================

def _decode_sfnt_name_bytes(raw: bytes, pid: int, eid: int) -> str:
    if pid == 3 and eid == 5:
        try:
            if b"\x00" in raw:
                out = bytearray()
                for i in range(0, len(raw) - 1, 2):
                    if raw[i] == 0:
                        out.append(raw[i + 1])
                    else:
                        out.extend(raw[i : i + 2])
                return bytes(out).decode("cp949", errors="ignore")
            return raw.decode("cp949", errors="ignore")
        except Exception:
            pass
    return raw.decode("utf-16-be", errors="ignore")


def _parse_sfnt_face_names(f, table_start: int) -> Optional[Tuple[str, str, str, str]]:
    """Returns (ko_name, en_name, family_name, subfamily_style) for an SFNT face."""
    try:
        f.seek(table_start)
        hdr = f.read(12)
        if len(hdr) < 12:
            return None
        num_tables = struct.unpack(">H", hdr[4:6])[0]
        if num_tables > 120:
            return None
        td = f.read(16 * num_tables)
        name_off = None
        for i in range(num_tables):
            if len(td) < (i + 1) * 16:
                break
            tag, _, off, _ = struct.unpack(">4sIII", td[i * 16 : (i + 1) * 16])
            if tag == b"name":
                name_off = off
                break
        if not name_off:
            return None
        f.seek(name_off)
        nhdr = f.read(6)
        if len(nhdr) < 6:
            return None
        _, count, str_off = struct.unpack(">HHH", nhdr)
        if count > 400:
            return None
        recs = f.read(12 * count)
        ko_fam, en_fam, ko_full, en_full, subfam = "", "", "", "", ""
        for i in range(count):
            if len(recs) < (i + 1) * 12:
                break
            pid, eid, lid, nid, slen, soff = struct.unpack(">6H", recs[i * 12 : (i + 1) * 12])
            if nid not in (1, 2, 4, 16) or pid not in (0, 3) or slen == 0 or slen > 512:
                continue
            f.seek(name_off + str_off + soff)
            txt = _decode_sfnt_name_bytes(f.read(slen), pid, eid).strip().replace("\x00", "")
            if not txt or txt.startswith("@"):
                continue
            if nid == 2 and not subfam:
                subfam = txt
            if lid == 1042:
                if nid in (1, 16) and not ko_fam:
                    ko_fam = txt
                elif nid == 4 and not ko_full:
                    ko_full = txt
            elif lid == 1033 or pid == 0:
                if nid in (1, 16) and not en_fam:
                    en_fam = txt
                elif nid == 4 and not en_full:
                    en_full = txt
        ko_disp = ko_full or ko_fam
        en_disp = en_full or en_fam
        fam = ko_fam or en_fam or ko_disp or en_disp
        if not (ko_disp or en_disp):
            return None
        return (ko_disp, en_disp, fam, subfam)
    except Exception:
        return None


def _extract_ttc_face_bytes(fp: str, ttc_idx: int) -> Optional[bytes]:
    """Extracts a single standalone SFNT font buffer from a TrueType Collection (.ttc) at `ttc_idx`."""
    try:
        with open(fp, "rb") as f:
            data = f.read()
        if data[:4] != b"ttcf":
            return None
        _, _, num_fonts = struct.unpack(">4sII", data[:12])
        if ttc_idx < 0 or ttc_idx >= num_fonts:
            return None
        face_off = struct.unpack(">I", data[12 + ttc_idx * 4 : 16 + ttc_idx * 4])[0]
        sfnt_hdr = data[face_off : face_off + 12]
        num_tables = struct.unpack(">H", sfnt_hdr[4:6])[0]
        out = bytearray(sfnt_hdr)
        out.extend(b"\x00" * (16 * num_tables))
        for i in range(num_tables):
            rec_off = face_off + 12 + i * 16
            tag, csum, toff, tlen = struct.unpack(">4sIII", data[rec_off : rec_off + 16])
            new_toff = len(out)
            struct.pack_into(">4sIII", out, 12 + i * 16, tag, csum, new_toff, tlen)
            out.extend(data[toff : toff + tlen])
            while len(out) % 4 != 0:
                out.append(0)
        return bytes(out)
    except Exception:
        return None


class KoreanFontRegistry:
    """
    Discovers and manages ALL fonts installed on the PC (both Korean and English/System fonts)
    for 100% lossless PDF embedding with automatic Korean glyph fallback.
    """

    PRIORITY_KOREAN_CANDIDATES = [
        ("malgun", "★ 맑은 고딕 (Malgun Gothic)", "malgun.ttf", "Malgun Gothic", False, 0),
        ("malgun_bd", "★ 맑은 고딕 굵게 (Malgun Gothic Bold)", "malgunbd.ttf", "Malgun Gothic", True, 0),
        ("malgun_sl", "★ 맑은 고딕 가늘게 (Malgun Semilight)", "malgunsl.ttf", "Malgun Gothic Semilight", False, 0),
        ("batang", "★ 바탕 (Batang)", "batang.ttc", "Batang", False, 0),
        ("batangche", "★ 바탕체 (BatangChe)", "batang.ttc", "BatangChe", False, 1),
        ("gungsuh", "★ 궁서 (Gungsuh)", "batang.ttc", "Gungsuh", False, 2),
        ("gungsuhche", "★ 궁서체 (GungsuhChe)", "batang.ttc", "GungsuhChe", False, 3),
        ("gulim", "★ 굴림 (Gulim)", "gulim.ttc", "Gulim", False, 0),
        ("gulimche", "★ 굴림체 (GulimChe)", "gulim.ttc", "GulimChe", False, 1),
        ("dotum", "★ 돋움 (Dotum)", "gulim.ttc", "Dotum", False, 2),
        ("dotumche", "★ 돋움체 (DotumChe)", "gulim.ttc", "DotumChe", False, 3),
        ("hy_gothic_m", "★ HY중고딕 (HYGothic-Medium)", "H2GTRM.TTF", "HYGothic-Medium", False, 0),
        ("hy_gothic_e", "★ HY견고딕 (HYGothic-Extra)", "H2GTRE.TTF", "HYGothic-Extra", True, 0),
        ("hy_myeongjo", "★ HY견명조 (HYMyeongJo-Extra)", "H2MJRE.TTF", "HYMyeongJo-Extra", False, 0),
    ]

    def __init__(self):
        self.fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        self.user_fonts_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")
        self.available: Dict[str, dict] = {}
        self._fitz_cache: Dict[str, fitz.Font] = {}
        self._discover_fonts()

    def _get_current_fonts_signature(self) -> dict:
        """0.0001초 만에 윈도우 시스템 및 사용자 폰트 디렉토리의 파일 수와 mtime 측정"""
        return {
            "cnt_sys": len(os.listdir(self.fonts_dir)) if os.path.isdir(self.fonts_dir) else 0,
            "cnt_usr": len(os.listdir(self.user_fonts_dir)) if os.path.isdir(self.user_fonts_dir) else 0,
            "mt_sys": os.path.getmtime(self.fonts_dir) if os.path.isdir(self.fonts_dir) else 0.0,
            "mt_usr": os.path.getmtime(self.user_fonts_dir) if os.path.isdir(self.user_fonts_dir) else 0.0,
        }

    def refresh_fonts(self):
        """수동으로 시스템 폰트를 다시 전수 스캔하여 캐시 갱신"""
        self._fitz_cache.clear()
        self._discover_fonts(force=True)

    def _discover_fonts(self, force: bool = False):
        cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kpdf_font_cache.json")
        current_sig = self._get_current_fonts_signature()

        if not force and os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    cached_sig = data.get("_meta_sig")
                    cached_fonts = data.get("fonts")
                    # 시그니처(파일 수, mtime)가 완전 일치하면 새 폰트가 설치되지 않은 것이므로 캐시 즉시 채택!
                    if cached_sig == current_sig and isinstance(cached_fonts, dict) and cached_fonts:
                        self.available = cached_fonts
                        return
            except Exception:
                pass

        self.available.clear()
        seen_paths_faces = set()
        # 1. Register priority Korean fonts at the very top
        for key, label, filename, qt_family, is_bold, ttc_idx in self.PRIORITY_KOREAN_CANDIDATES:
            full_path = os.path.join(self.fonts_dir, filename)
            if os.path.exists(full_path):
                self.available[key] = {
                    "key": key,
                    "label": label,
                    "path": full_path,
                    "qt_family": qt_family,
                    "bold": is_bold,
                    "ttc_idx": ttc_idx,
                }
                seen_paths_faces.add((os.path.normcase(full_path), ttc_idx))

        # 2. Scan all installed font files (.ttf, .ttc, .otf) across system & user font folders
        scan_dirs = [d for d in (self.fonts_dir, self.user_fonts_dir) if d and os.path.isdir(d)]
        ko_discovered = []
        en_discovered = []
        seen_labels = {info["label"].lower() for info in self.available.values()}

        for d in scan_dirs:
            try:
                fnames = sorted(os.listdir(d))
            except Exception:
                continue
            for fn in fnames:
                low_fn = fn.lower()
                if not low_fn.endswith((".ttf", ".ttc", ".otf")):
                    continue
                # Skip pure symbol/icon fonts that have no text glyphs
                if low_fn in ("marlett.ttf", "segmdl2.ttf", "segoeicons.ttf", "holomdl2.ttf", "webdings.ttf", "wingding.ttf"):
                    continue
                fp = os.path.join(d, fn)
                norm_fp = os.path.normcase(fp)
                try:
                    with open(fp, "rb") as f:
                        hdr = f.read(12)
                        if len(hdr) < 12:
                            continue
                        if hdr[:4] == b"ttcf":
                            _, _, num_fonts = struct.unpack(">4sII", hdr)
                            cnt = min(num_fonts, 8)
                            offs = struct.unpack(f">{cnt}I", f.read(4 * cnt))
                            faces = [(idx, off) for idx, off in enumerate(offs)]
                        else:
                            faces = [(0, 0)]

                        for ttc_idx, off in faces:
                            if (norm_fp, ttc_idx) in seen_paths_faces:
                                continue
                            res = _parse_sfnt_face_names(f, off)
                            if not res:
                                continue
                            ko_name, en_name, fam_name, subfam = res
                            has_hangul = bool(ko_name and any("\uac00" <= c <= "\ud7a3" for c in ko_name))
                            if ko_name and en_name and ko_name != en_name:
                                label = f"{ko_name} ({en_name})"
                            else:
                                label = ko_name or en_name

                            if label.lower() in seen_labels:
                                continue
                            seen_labels.add(label.lower())
                            seen_paths_faces.add((norm_fp, ttc_idx))

                            is_b = any(k in (subfam + " " + label).lower() for k in ("bold", "heavy", "black", "extra"))
                            key = f"sys_{os.path.splitext(low_fn)[0]}_{ttc_idx}"
                            entry = {
                                "key": key,
                                "label": label,
                                "path": fp,
                                "qt_family": fam_name,
                                "bold": is_b,
                                "ttc_idx": ttc_idx,
                            }
                            if has_hangul or any(k in label.lower() for k in ("kr", "korean", "d2coding", "nanum", "malgun", "batang", "gulim", "dotum", "hy")):
                                ko_discovered.append(entry)
                            else:
                                en_discovered.append(entry)
                except Exception:
                    continue

        ko_discovered.sort(key=lambda x: x["label"])
        en_discovered.sort(key=lambda x: x["label"].lower())

        for entry in ko_discovered + en_discovered:
            self.available[entry["key"]] = entry

        if not self.available:
            self.available["default"] = {
                "key": "default",
                "label": "기본 시스템 한글 글꼴",
                "path": None,
                "qt_family": "Malgun Gothic",
                "bold": False,
                "ttc_idx": 0,
            }

        # Save to disk cache with directory signature for smart auto-invalidation
        try:
            payload = {
                "_meta_sig": current_sig,
                "fonts": self.available,
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def default_key(self) -> str:
        if "malgun" in self.available:
            return "malgun"
        return next(iter(self.available.keys()))

    def match_pdf_font_to_korean_key(self, pdf_font_name: str, is_bold: bool = False) -> str:
        low = (pdf_font_name or "").lower()
        # Strip subset prefix like 'ABCDEF+MalgunGothic'
        if "+" in low:
            low = low.split("+", 1)[1]
        if any(k in low for k in ["gungsuh", "궁서"]):
            if "gungsuh" in self.available:
                return "gungsuh"
        if any(k in low for k in ["batang", "myungjo", "myeongjo", "명조", "바탕", "smmyungjo", "nanummyeongjo"]):
            if "batang" in self.available:
                return "batang"
            if "hy_myeongjo" in self.available:
                return "hy_myeongjo"
        if any(k in low for k in ["dotum", "돋움"]):
            if "dotum" in self.available:
                return "dotum"
        if any(k in low for k in ["gulim", "굴림"]):
            if "gulim" in self.available:
                return "gulim"
        if any(k in low for k in ["hygothic", "h2gtr"]):
            if "hy_gothic_e" in self.available and is_bold:
                return "hy_gothic_e"
            if "hy_gothic_m" in self.available:
                return "hy_gothic_m"
        # Check if any installed PC font matches the PDF font family
        clean_low = low.replace("-", "").replace(" ", "").replace("regular", "").replace("bold", "")
        if len(clean_low) >= 4:
            for k, info in self.available.items():
                qf_clean = info["qt_family"].lower().replace("-", "").replace(" ", "")
                if qf_clean and (qf_clean in clean_low or clean_low in qf_clean):
                    if is_bold == info.get("bold", False):
                        return k
        if is_bold or "bold" in low or "heavy" in low or "black" in low:
            if "malgun_bd" in self.available:
                return "malgun_bd"
        return self.default_key()

    def get_fitz_font(self, key: str, bold: bool = False) -> fitz.Font:
        if bold and key == "malgun" and "malgun_bd" in self.available:
            key = "malgun_bd"
        elif bold and key == "hy_gothic_m" and "hy_gothic_e" in self.available:
            key = "hy_gothic_e"
        if key not in self.available:
            key = self.default_key()
        if key not in self._fitz_cache:
            info = self.available[key]
            path = info.get("path")
            ttc_idx = int(info.get("ttc_idx", 0))
            try:
                if path and os.path.exists(path):
                    if path.lower().endswith(".ttc") and ttc_idx > 0:
                        buf = _extract_ttc_face_bytes(path, ttc_idx)
                        if buf:
                            self._fitz_cache[key] = fitz.Font(fontbuffer=buf)
                        else:
                            self._fitz_cache[key] = fitz.Font(fontfile=path)
                    else:
                        self._fitz_cache[key] = fitz.Font(fontfile=path)
                else:
                    self._fitz_cache[key] = fitz.Font("korea")
            except Exception:
                self._fitz_cache[key] = fitz.Font("korea")
        return self._fitz_cache[key]

    def get_fallback_fitz_font(self, bold: bool = False) -> fitz.Font:
        if bold and "malgun_bd" in self.available:
            return self.get_fitz_font("malgun_bd")
        return self.get_fitz_font(self.default_key())

    def get_qfont(self, key: str, pixel_size: float, bold_override: Optional[bool] = None) -> QFont:
        if key not in self.available:
            key = self.default_key()
        info = self.available[key]
        qf = QFont(info["qt_family"])
        qf.setPixelSize(max(6, int(round(pixel_size))))
        is_b = info["bold"] if bold_override is None else (info["bold"] or bold_override)
        qf.setBold(is_b)
        return qf

    def char_width_pt(self, ch: str, font_key: str, fontsize: float, bold: bool = False) -> float:
        primary = self.get_fitz_font(font_key, bold)
        fallback = self.get_fallback_fitz_font(bold)
        fo = primary if primary.has_glyph(ord(ch)) else fallback
        return fo.text_length(ch, fontsize=fontsize)

    def write_styled_runs_to_page(
        self,
        page: fitz.Page,
        origin_pt: Tuple[float, float],
        runs: List[dict],
        opacity: float = 1.0,
    ) -> None:
        """
        Writes rich text runs (supporting per-word/per-phrase font, size, bold, and color)
        into a fitz.Page with automatic Korean glyph fallback.
        """
        base_x, base_y = origin_pt
        cur_x = base_x
        cur_y = base_y

        # Calculate max font size for line height
        max_fs = max((float(r.get("font_size", 12.0)) for r in runs), default=12.0)
        line_h = max_fs * 1.32

        for run in runs:
            txt = run.get("text", "")
            if not txt:
                continue
            fkey = run.get("font_key", self.default_key())
            fsize = float(run.get("font_size", 12.0))
            is_b = bool(run.get("bold", False))
            col_rgb = run.get("color", [0, 0, 0])
            col_fitz = (col_rgb[0] / 255.0, col_rgb[1] / 255.0, col_rgb[2] / 255.0)

            primary = self.get_fitz_font(fkey, is_b)
            fallback = self.get_fallback_fitz_font(is_b)

            parts = txt.split("\n")
            for p_idx, part in enumerate(parts):
                if p_idx > 0:
                    cur_x = base_x
                    cur_y += max(line_h, fsize * 1.32)
                if not part:
                    continue

                tw = fitz.TextWriter(page.rect, opacity=opacity)
                # Group contiguous characters with same resolved fitz.Font
                sub_runs: List[Tuple[fitz.Font, str]] = []
                for ch in part:
                    fo = primary if primary.has_glyph(ord(ch)) else fallback
                    if sub_runs and sub_runs[-1][0] is fo:
                        sub_runs[-1] = (fo, sub_runs[-1][1] + ch)
                    else:
                        sub_runs.append((fo, ch))

                for fo, s_str in sub_runs:
                    tw.append((cur_x, cur_y), s_str, font=fo, fontsize=fsize)
                    cur_x += fo.text_length(s_str, fontsize=fsize)

                tw.write_text(page, color=col_fitz)


# =====================================================================
# 2. Data Model for PDF Overlay & In-Place Edit Objects
# =====================================================================

@dataclass
class DetectedTextSegment:
    """Represents an existing text segment extracted from the PDF page (with character-level bboxes)."""
    seg_id: str
    bbox: Tuple[float, float, float, float]      # (x0, y0, x1, y1) in PDF points
    origin: Tuple[float, float]                  # Baseline (x, y) in PDF points
    text: str
    pdf_font: str
    font_size: float
    color: Tuple[int, int, int]                  # RGB 0..255
    is_bold: bool = False
    chars: List[dict] = field(default_factory=list)  # Per-char {'c', 'bbox', 'origin', 'font', 'size', 'color', 'bold'}


@dataclass
class PageEditObject:
    """
    Unified editable object on a PDF page:
    - kind == 'inplace_text': Replaces an existing PDF text segment or a selected word/phrase block
    - kind == 'free_text': Newly added Korean text box
    - kind == 'rect' | 'ellipse' | 'line' | 'arrow' | 'highlight'
    Supports `runs` for partial block (word/phrase) rich text styling!
    """
    obj_id: str
    kind: str
    rect: List[float]                            # [x0, y0, x1, y1] in PDF points
    text: str = ""
    orig_text: str = ""
    orig_bbox: Optional[List[float]] = None      # Original PDF text bbox (or sub-selection bbox) for inplace_text
    orig_origin: Optional[List[float]] = None    # Original baseline [ox, oy]
    orig_pdf_font: str = ""
    font_key: str = "malgun"
    font_size: float = 12.0
    bold: bool = False
    text_color: List[int] = field(default_factory=lambda: [0, 0, 0])
    stroke_color: List[int] = field(default_factory=lambda: [30, 64, 175])
    fill_color: List[int] = field(default_factory=lambda: [255, 255, 255])
    use_fill: bool = False
    redact_stream_text: bool = True
    stroke_width: float = 2.0
    opacity: float = 1.0
    runs: List[dict] = field(default_factory=list)   # [{'text', 'font_key', 'font_size', 'bold', 'color'}]

    def get_effective_runs(self) -> List[dict]:
        if self.runs and "".join(r.get("text", "") for r in self.runs) == self.text:
            return self.runs
        return [{
            "text": self.text,
            "font_key": self.font_key,
            "font_size": self.font_size,
            "bold": self.bold,
            "color": list(self.text_color),
        }]


def apply_partial_run_style(
    obj: PageEditObject,
    sel_start: int,
    sel_end: int,
    font_key: Optional[str] = None,
    font_size: Optional[float] = None,
    bold: Optional[bool] = None,
    color: Optional[List[int]] = None,
) -> None:
    """
    Splits `obj.runs` at character offsets `[sel_start, sel_end)` and updates ONLY the selected block's style!
    If `sel_start == sel_end`, updates all runs in `obj`.
    """
    runs = obj.get_effective_runs()
    if sel_start >= sel_end:
        for r in runs:
            if font_key is not None:
                r["font_key"] = font_key
            if font_size is not None:
                r["font_size"] = float(font_size)
            if bold is not None:
                r["bold"] = bool(bold)
            if color is not None:
                r["color"] = list(color)
        obj.runs = _merge_adjacent_runs(runs)
        return

    # Expand to per-character descriptors, apply style to [sel_start:sel_end], then re-merge contiguous identical styles
    char_items: List[dict] = []
    for r in runs:
        for ch in r.get("text", ""):
            char_items.append({
                "ch": ch,
                "font_key": r.get("font_key", obj.font_key),
                "font_size": float(r.get("font_size", obj.font_size)),
                "bold": bool(r.get("bold", obj.bold)),
                "color": list(r.get("color", obj.text_color)),
            })

    s0 = max(0, min(len(char_items), sel_start))
    s1 = max(s0, min(len(char_items), sel_end))
    for idx in range(s0, s1):
        if font_key is not None:
            char_items[idx]["font_key"] = font_key
        if font_size is not None:
            char_items[idx]["font_size"] = float(font_size)
        if bold is not None:
            char_items[idx]["bold"] = bool(bold)
        if color is not None:
            char_items[idx]["color"] = list(color)

    new_runs: List[dict] = []
    for ci in char_items:
        item_run = {
            "text": ci["ch"],
            "font_key": ci["font_key"],
            "font_size": ci["font_size"],
            "bold": ci["bold"],
            "color": ci["color"],
        }
        new_runs.append(item_run)
    obj.runs = _merge_adjacent_runs(new_runs)


def sync_runs_with_edited_text(obj: PageEditObject, new_text: str) -> None:
    """
    Updates `obj.text` and adjusts `obj.runs` when the user edits characters inside the text editor,
    preserving prefix and suffix run styles around the edited region.
    """
    old_text = obj.text
    if new_text == old_text:
        return
    runs = obj.get_effective_runs()
    if not old_text or len(runs) <= 1:
        obj.text = new_text
        base_r = runs[0] if runs else {
            "font_key": obj.font_key,
            "font_size": obj.font_size,
            "bold": obj.bold,
            "color": list(obj.text_color),
        }
        obj.runs = [{
            "text": new_text,
            "font_key": base_r["font_key"],
            "font_size": base_r["font_size"],
            "bold": base_r["bold"],
            "color": list(base_r["color"]),
        }]
        return

    # Expand old runs to per-char list
    old_chars: List[dict] = []
    for r in runs:
        for ch in r.get("text", ""):
            old_chars.append({
                "ch": ch,
                "font_key": r.get("font_key", obj.font_key),
                "font_size": float(r.get("font_size", obj.font_size)),
                "bold": bool(r.get("bold", obj.bold)),
                "color": list(r.get("color", obj.text_color)),
            })

    # Find common prefix and suffix
    prefix_len = 0
    max_pref = min(len(old_text), len(new_text))
    while prefix_len < max_pref and old_text[prefix_len] == new_text[prefix_len]:
        prefix_len += 1

    suffix_len = 0
    max_suff = min(len(old_text) - prefix_len, len(new_text) - prefix_len)
    while (
        suffix_len < max_suff
        and old_text[len(old_text) - 1 - suffix_len] == new_text[len(new_text) - 1 - suffix_len]
    ):
        suffix_len += 1

    mid_new = new_text[prefix_len : len(new_text) - suffix_len if suffix_len > 0 else len(new_text)]
    old_replaced_len = len(old_text) - prefix_len - suffix_len
    # When replacing a selected word/phrase block, inherit the style of the replaced block itself!
    if old_replaced_len > 0 and prefix_len < len(old_chars):
        inherit = old_chars[prefix_len]
    elif prefix_len > 0 and prefix_len - 1 < len(old_chars):
        inherit = old_chars[prefix_len - 1]
    elif prefix_len < len(old_chars):
        inherit = old_chars[prefix_len]
    else:
        inherit = {
            "font_key": obj.font_key,
            "font_size": obj.font_size,
            "bold": obj.bold,
            "color": list(obj.text_color),
        }

    new_chars: List[dict] = []
    new_chars.extend(old_chars[:prefix_len])
    for ch in mid_new:
        new_chars.append({
            "ch": ch,
            "font_key": inherit["font_key"],
            "font_size": inherit["font_size"],
            "bold": inherit["bold"],
            "color": list(inherit["color"]),
        })
    if suffix_len > 0:
        new_chars.extend(old_chars[len(old_chars) - suffix_len :])

    obj.text = new_text
    obj.runs = _merge_adjacent_runs([
        {
            "text": c["ch"],
            "font_key": c["font_key"],
            "font_size": c["font_size"],
            "bold": c["bold"],
            "color": c["color"],
        }
        for c in new_chars
    ])


def _merge_adjacent_runs(runs: List[dict]) -> List[dict]:
    merged: List[dict] = []
    for r in runs:
        if not r.get("text"):
            continue
        if (
            merged
            and merged[-1]["font_key"] == r["font_key"]
            and abs(float(merged[-1]["font_size"]) - float(r["font_size"])) < 0.01
            and bool(merged[-1]["bold"]) == bool(r["bold"])
            and list(merged[-1]["color"]) == list(r["color"])
        ):
            merged[-1]["text"] += r["text"]
        else:
            merged.append({
                "text": r["text"],
                "font_key": r["font_key"],
                "font_size": float(r["font_size"]),
                "bold": bool(r["bold"]),
                "color": list(r["color"]),
            })
    return merged


# =====================================================================
# 3. Interactive PDF Page Canvas Widget
# =====================================================================

class PDFCanvasWidget(QWidget):
    """
    High-DPI interactive PDF page canvas supporting:
    - Dragging across specific words/phrases on the PDF page to select & edit ONLY that substring
    - Clicking inside text to place the cursor at the clicked character & block-select substrings
    - Per-selection Rich Text styling (font, size, bold, color)
    - Adding & editing free Korean text boxes and shapes
    """

    objectSelected = pyqtSignal(object)
    shapeDoubleClicked = pyqtSignal(object)
    selectionSpanChanged = pyqtSignal(object, int, int)   # (obj, sel_start, sel_end)
    stateChanged = pyqtSignal(str)
    zoomRequest = pyqtSignal(int)
    requestViewMode = pyqtSignal()

    HANDLE_SIZE = 9.0

    def __init__(self, font_registry: KoreanFontRegistry, parent=None):
        super().__init__(parent)
        self.font_registry = font_registry
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.is_dark_theme: bool = True

        self.page_pixmap: Optional[QPixmap] = None
        self.page_rect_pt: Tuple[float, float] = (595.0, 842.0)
        self.zoom: float = 1.5

        self.detected_segments: List[DetectedTextSegment] = []
        self.hovered_segment: Optional[DetectedTextSegment] = None

        self.objects: List[PageEditObject] = []
        self.selected_obj: Optional[PageEditObject] = None

        self.search_rects: List[Tuple[float, float, float, float]] = []
        self.current_search_idx: int = -1

        self.tool_mode: str = "view"

        # Default style for new objects
        self.default_font_key: str = self.font_registry.default_key()
        self.default_font_size: float = 12.0
        self.default_text_color: List[int] = [0, 0, 0]
        self.default_stroke_color: List[int] = [220, 38, 38]
        self.default_fill_color: List[int] = [254, 240, 138]
        self.default_use_fill: bool = False
        self.default_stroke_width: float = 2.0
        self.default_opacity: float = 1.0

        # Mouse interaction state
        self._dragging_mode: Optional[str] = None
        self._drag_start_pt: Tuple[float, float] = (0.0, 0.0)
        self._drag_start_px: QPointF = QPointF(0.0, 0.0)
        self._drag_orig_rect: Optional[List[float]] = None
        self._creating_obj: Optional[PageEditObject] = None
        self._had_selected_before_press: bool = False

        # Sub-segment character drag selection state on PDF canvas
        self._pressed_segment: Optional[DetectedTextSegment] = None
        self._char_sel_rect_pt: Optional[List[float]] = None
        self._selected_seg_chars: List[dict] = []

        # On-canvas Korean IME-friendly inline rich editor
        self.inline_editor = QTextEdit(self)
        self.inline_editor.setVisible(False)
        self.inline_editor.setAcceptRichText(True)
        self.inline_editor.textChanged.connect(self._on_inline_text_changed)
        self.inline_editor.selectionChanged.connect(self._on_inline_selection_changed)
        self._inline_editing_obj: Optional[PageEditObject] = None
        self._updating_inline: bool = False
        self.last_sel_range: Tuple[int, int] = (0, 0)

    # -----------------------------------------------------------------
    # Coordinate conversions (PDF Points <-> Widget Pixels)
    # -----------------------------------------------------------------
    def _canvas_origin_px(self) -> Tuple[float, float]:
        pw = self.page_rect_pt[0] * self.zoom
        ph = self.page_rect_pt[1] * self.zoom
        ox = max(20.0, (self.width() - pw) / 2.0)
        oy = max(20.0, (self.height() - ph) / 2.0)
        return ox, oy

    def pdf_to_px(self, x_pt: float, y_pt: float) -> QPointF:
        ox, oy = self._canvas_origin_px()
        return QPointF(ox + x_pt * self.zoom, oy + y_pt * self.zoom)

    def px_to_pdf(self, x_px: float, y_px: float) -> Tuple[float, float]:
        ox, oy = self._canvas_origin_px()
        return (x_px - ox) / self.zoom, (y_px - oy) / self.zoom

    def pdf_rect_to_qrectf(self, r: List[float] | Tuple[float, float, float, float]) -> QRectF:
        p0 = self.pdf_to_px(r[0], r[1])
        p1 = self.pdf_to_px(r[2], r[3])
        return QRectF(p0, p1).normalized()

    def sizeHint(self) -> QSize:
        pw = int(self.page_rect_pt[0] * self.zoom) + 60
        ph = int(self.page_rect_pt[1] * self.zoom) + 60
        return QSize(pw, ph)

    def update_canvas_geometry(self):
        pw = int(self.page_rect_pt[0] * self.zoom) + 60
        ph = int(self.page_rect_pt[1] * self.zoom) + 60
        self.setMinimumSize(pw, ph)
        self.resize(pw, ph)
        self.updateGeometry()
        if self._inline_editing_obj:
            self.refresh_inline_editor_from_runs(self._inline_editing_obj, preserve_selection=True)
            self._reposition_inline_editor(self._inline_editing_obj)
        self.update()

    # -----------------------------------------------------------------
    # Inline Korean IME Editor & Partial Selection Formatting
    # -----------------------------------------------------------------
    def start_inline_edit(
        self,
        obj: PageEditObject,
        select_all: bool = False,
        click_pdf_pt: Optional[Tuple[float, float]] = None,
    ):
        if obj.kind not in ("inplace_text", "free_text"):
            return
        self._inline_editing_obj = obj
        self.inline_editor.setStyleSheet(
            "QTextEdit {"
            "  background-color: rgba(255, 255, 255, 250);"
            "  color: #111827;"
            "  selection-background-color: #2563EB;"
            "  selection-color: #FFFFFF;"
            "  border: 2px solid #2563EB;"
            "  border-radius: 3px;"
            "  padding: 1px 3px;"
            "}"
        )
        self.refresh_inline_editor_from_runs(obj, preserve_selection=False)
        self._reposition_inline_editor(obj)
        self.inline_editor.setVisible(True)
        self.inline_editor.setFocus()

        cursor = self.inline_editor.textCursor()
        if select_all:
            cursor.select(QTextCursor.SelectionType.Document)
            self.inline_editor.setTextCursor(cursor)
            self.last_sel_range = (cursor.selectionStart(), cursor.selectionEnd())
        elif click_pdf_pt is not None:
            # Place cursor at the exact clicked character offset instead of selecting all!
            rel_x_pt = max(0.0, click_pdf_pt[0] - obj.rect[0])
            char_idx = self._estimate_char_index_at_x(obj, rel_x_pt)
            cursor.setPosition(char_idx)
            self.inline_editor.setTextCursor(cursor)
            self.last_sel_range = (char_idx, char_idx)
        else:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.inline_editor.setTextCursor(cursor)
            pos = cursor.position()
            self.last_sel_range = (pos, pos)

        self.update()

    def _estimate_char_index_at_x(self, obj: PageEditObject, rel_x_pt: float) -> int:
        acc_x = 0.0
        idx = 0
        for r in obj.get_effective_runs():
            fk = r.get("font_key", obj.font_key)
            fs = float(r.get("font_size", obj.font_size))
            bd = bool(r.get("bold", obj.bold))
            for ch in r.get("text", ""):
                cw = self.font_registry.char_width_pt(ch, fk, fs, bd)
                if acc_x + cw * 0.5 >= rel_x_pt:
                    return idx
                acc_x += cw
                idx += 1
        return idx

    def refresh_inline_editor_from_runs(self, obj: PageEditObject, preserve_selection: bool = True):
        if self._inline_editing_obj is not obj:
            return
        old_s0, old_s1 = self.last_sel_range
        self._updating_inline = True
        self.inline_editor.clear()
        cursor = self.inline_editor.textCursor()

        for r in obj.get_effective_runs():
            fmt = QTextCharFormat()
            qf = self.font_registry.get_qfont(
                r.get("font_key", obj.font_key),
                max(10.0, float(r.get("font_size", obj.font_size)) * self.zoom),
                bool(r.get("bold", obj.bold)),
            )
            fmt.setFont(qf)
            c = r.get("color", obj.text_color)
            fmt.setForeground(QBrush(QColor(c[0], c[1], c[2])))
            cursor.insertText(r.get("text", ""), fmt)

        if preserve_selection:
            doc_len = len(obj.text)
            s0 = max(0, min(doc_len, old_s0))
            s1 = max(s0, min(doc_len, old_s1))
            cursor.setPosition(s0)
            if s1 > s0:
                cursor.setPosition(s1, QTextCursor.MoveMode.KeepAnchor)
            self.inline_editor.setTextCursor(cursor)

        self._updating_inline = False

    def _on_inline_selection_changed(self):
        if self._updating_inline or self._inline_editing_obj is None:
            return
        c = self.inline_editor.textCursor()
        self.last_sel_range = (c.selectionStart(), c.selectionEnd())
        self.selectionSpanChanged.emit(self._inline_editing_obj, c.selectionStart(), c.selectionEnd())

    def _reposition_inline_editor(self, obj: PageEditObject):
        qr = self.pdf_rect_to_qrectf(obj.rect)
        max_fs = max((float(r.get("font_size", obj.font_size)) for r in obj.get_effective_runs()), default=obj.font_size)
        min_w = max(int(qr.width()) + 36, 120)
        min_h = max(int(qr.height()) + 16, int(max_fs * self.zoom * 1.75) + 14)
        self.inline_editor.setGeometry(
            int(qr.left()) - 2,
            int(qr.top()) - 3,
            min_w,
            min_h,
        )

    def commit_inline_edit(self):
        if self._inline_editing_obj is not None:
            new_txt = self.inline_editor.toPlainText().rstrip("\r\n")
            sync_runs_with_edited_text(self._inline_editing_obj, new_txt)
            self._auto_adjust_text_rect(self._inline_editing_obj)
            self._inline_editing_obj = None
            self.inline_editor.setVisible(False)
            self.last_sel_range = (0, 0)
            self.stateChanged.emit("텍스트 편집")
            self.update()

    def _on_inline_text_changed(self):
        if self._updating_inline or self._inline_editing_obj is None:
            return
        new_txt = self.inline_editor.toPlainText().rstrip("\r\n")
        sync_runs_with_edited_text(self._inline_editing_obj, new_txt)
        self._auto_adjust_text_rect(self._inline_editing_obj)
        self._reposition_inline_editor(self._inline_editing_obj)
        self.objectSelected.emit(self._inline_editing_obj)
        self.update()

    def _auto_adjust_text_rect(self, obj: PageEditObject):
        if obj.kind not in ("inplace_text", "free_text"):
            return
        runs = obj.get_effective_runs()
        cur_line_w = 0.0
        max_w = 16.0
        line_count = 1
        max_fs = obj.font_size
        for r in runs:
            fk = r.get("font_key", obj.font_key)
            fs = float(r.get("font_size", obj.font_size))
            bd = bool(r.get("bold", obj.bold))
            max_fs = max(max_fs, fs)
            parts = r.get("text", "").split("\n")
            for p_idx, part in enumerate(parts):
                if p_idx > 0:
                    max_w = max(max_w, cur_line_w + 6.0)
                    cur_line_w = 0.0
                    line_count += 1
                for ch in part:
                    cur_line_w += self.font_registry.char_width_pt(ch, fk, fs, bd)
        max_w = max(max_w, cur_line_w + 6.0)
        total_h = max(max_fs * 1.35 * line_count, obj.rect[3] - obj.rect[1])
        obj.rect[2] = obj.rect[0] + max_w
        if obj.kind == "free_text" or line_count > 1:
            obj.rect[3] = obj.rect[1] + total_h

    # -----------------------------------------------------------------
    # Painting (Page Pixmap + Search + Sub-Segment Drag Highlight + Objects)
    # -----------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        bg_col = QColor(30, 34, 42) if self.is_dark_theme else QColor(218, 224, 233)
        painter.fillRect(self.rect(), bg_col)

        if not self.page_pixmap:
            painter.setPen(QColor(156, 163, 175) if self.is_dark_theme else QColor(71, 85, 105))
            painter.setFont(QFont("Malgun Gothic", 13))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "열린 PDF 문서가 없습니다.\n상단의 [파일 열기] 또는 [샘플 한글 PDF] 버튼을 눌러 시작하세요.",
            )
            return

        ox, oy = self._canvas_origin_px()
        pw = self.page_rect_pt[0] * self.zoom
        ph = self.page_rect_pt[1] * self.zoom
        page_qrect = QRectF(ox, oy, pw, ph)

        shadow_col = QColor(0, 0, 0, 110) if self.is_dark_theme else QColor(15, 23, 42, 55)
        painter.fillRect(page_qrect.translated(5, 5), shadow_col)
        painter.fillRect(page_qrect, QColor(255, 255, 255))
        painter.drawPixmap(page_qrect.topLeft(), self.page_pixmap)

        # 1. Search Highlights (선명한 형광 노란색 & 포커스 오렌지 테두리)
        for idx, sr in enumerate(self.search_rects):
            qr = self.pdf_rect_to_qrectf(sr)
            if idx == self.current_search_idx:
                painter.fillRect(qr, QColor(255, 170, 0, 160))
                painter.setPen(QPen(QColor(234, 88, 12), 2.2))
                painter.drawRect(qr)
            else:
                painter.fillRect(qr, QColor(255, 235, 59, 140))
                painter.setPen(QPen(QColor(202, 138, 4), 1.2))
                painter.drawRect(qr)

        # 2. In 'inplace_text' mode, draw guide boxes & active character block drag selection
        if self.tool_mode == "inplace_text":
            for seg in self.detected_segments:
                qr = self.pdf_rect_to_qrectf(seg.bbox)
                if seg is self.hovered_segment:
                    painter.fillRect(qr, QColor(59, 130, 246, 28))
                    pen = QPen(QColor(37, 99, 235, 190), 1.3, Qt.PenStyle.SolidLine)
                else:
                    pen = QPen(QColor(59, 130, 246, 95), 1.0, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.drawRect(qr)

        # Highlight characters being drag-selected on canvas (works in both view and inplace_text mode!)
        if self._selected_seg_chars:
            for ch_info in self._selected_seg_chars:
                c_qr = self.pdf_rect_to_qrectf(ch_info["bbox"])
                painter.fillRect(c_qr, QColor(37, 99, 235, 80 if self.tool_mode == "view" else 110))
            if self.tool_mode != "view":
                x0 = min(c["bbox"][0] for c in self._selected_seg_chars)
                y0 = min(c["bbox"][1] for c in self._selected_seg_chars)
                x1 = max(c["bbox"][2] for c in self._selected_seg_chars)
                y1 = max(c["bbox"][3] for c in self._selected_seg_chars)
                sel_qr = self.pdf_rect_to_qrectf((x0, y0, x1, y1))
                painter.setPen(QPen(QColor(29, 78, 216), 2.0, Qt.PenStyle.SolidLine))
                painter.drawRect(sel_qr)

        # 3. Draw PageEditObjects (including multi-run rich text!)
        for obj in self.objects:
            self._draw_edit_object(painter, obj)

        # 4. Draw Selection Handles (only in editing modes!)
        if self.tool_mode != "view" and self.selected_obj is not None:
            self._draw_selection_handles(painter, self.selected_obj)

    def _draw_edit_object(self, painter: QPainter, obj: PageEditObject):
        painter.save()
        painter.setOpacity(obj.opacity)
        qr = self.pdf_rect_to_qrectf(obj.rect)

        if obj.kind in ("inplace_text", "free_text"):
            if obj.use_fill or (obj.kind == "inplace_text" and not obj.redact_stream_text):
                fc = obj.fill_color
                painter.fillRect(qr, QColor(fc[0], fc[1], fc[2]))

            if obj.kind == "free_text" and obj.stroke_width > 0:
                sc = obj.stroke_color
                painter.setPen(QPen(QColor(sc[0], sc[1], sc[2]), obj.stroke_width * self.zoom))
                painter.drawRect(qr)

            if obj is not self._inline_editing_obj:
                runs = obj.get_effective_runs()
                max_fs = max((float(r.get("font_size", obj.font_size)) for r in runs), default=obj.font_size)
                if obj.kind == "inplace_text" and obj.orig_origin:
                    dx = obj.rect[0] - (obj.orig_bbox[0] if obj.orig_bbox else obj.rect[0])
                    dy = obj.rect[1] - (obj.orig_bbox[1] if obj.orig_bbox else obj.rect[1])
                    start_x_pt = obj.orig_origin[0] + dx
                    start_y_pt = obj.orig_origin[1] + dy
                else:
                    start_x_pt = obj.rect[0] + 2.0
                    start_y_pt = obj.rect[1] + max_fs * 0.92

                cur_x_pt = start_x_pt
                cur_y_pt = start_y_pt
                line_h_pt = max_fs * 1.32

                for r in runs:
                    fk = r.get("font_key", obj.font_key)
                    fs = float(r.get("font_size", obj.font_size))
                    bd = bool(r.get("bold", obj.bold))
                    col = r.get("color", obj.text_color)
                    painter.setPen(QColor(col[0], col[1], col[2]))
                    qf = self.font_registry.get_qfont(fk, fs * self.zoom, bd)
                    painter.setFont(qf)

                    parts = r.get("text", "").split("\n")
                    for p_idx, part in enumerate(parts):
                        if p_idx > 0:
                            cur_x_pt = start_x_pt
                            cur_y_pt += max(line_h_pt, fs * 1.32)
                        if not part:
                            continue
                        pt_px = self.pdf_to_px(cur_x_pt, cur_y_pt)
                        painter.drawText(pt_px, part)
                        for ch in part:
                            cur_x_pt += self.font_registry.char_width_pt(ch, fk, fs, bd)

            if obj.kind == "inplace_text" and self.tool_mode != "view":
                badge_pen = QPen(QColor(16, 185, 129, 175), 1.1, Qt.PenStyle.DotLine)
                painter.setPen(badge_pen)
                painter.drawRect(qr)

        elif obj.kind == "rect":
            painter.setBrush(QBrush(QColor(*obj.fill_color)) if obj.use_fill else Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(*obj.stroke_color), max(1.0, obj.stroke_width * self.zoom)))
            painter.drawRect(qr)
            if obj.text.strip():
                qf = self.font_registry.get_qfont(obj.font_key, obj.font_size * self.zoom, obj.bold)
                painter.setFont(qf)
                painter.setPen(QColor(*obj.text_color))
                painter.drawText(qr.adjusted(4, 2, -4, -2), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, obj.text)

        elif obj.kind == "ellipse":
            painter.setBrush(QBrush(QColor(*obj.fill_color)) if obj.use_fill else Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(*obj.stroke_color), max(1.0, obj.stroke_width * self.zoom)))
            painter.drawEllipse(qr)
            if obj.text.strip():
                qf = self.font_registry.get_qfont(obj.font_key, obj.font_size * self.zoom, obj.bold)
                painter.setFont(qf)
                painter.setPen(QColor(*obj.text_color))
                painter.drawText(qr.adjusted(6, 4, -6, -4), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, obj.text)

        elif obj.kind == "highlight":
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
            painter.setOpacity(max(0.65, min(obj.opacity, 0.95)))
            painter.fillRect(qr, QColor(*obj.fill_color))

        elif obj.kind == "eraser":
            painter.fillRect(qr, QColor(*obj.fill_color))
            # 편집 모드에서는 지우개 영역을 식별할 수 있도록 은은한 초미세 점선 테두리 표시
            if self.tool_mode != "view":
                dash_pen = QPen(QColor(156, 163, 175, 130), 1.0, Qt.PenStyle.DashLine)
                painter.setPen(dash_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(qr)

        elif obj.kind in ("line", "arrow"):
            p0 = self.pdf_to_px(obj.rect[0], obj.rect[1])
            p1 = self.pdf_to_px(obj.rect[2], obj.rect[3])
            pen = QPen(QColor(*obj.stroke_color), max(1.5, obj.stroke_width * self.zoom))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(p0, p1)

            if obj.kind == "arrow":
                angle = math.atan2(p1.y() - p0.y(), p1.x() - p0.x())
                head_len = max(10.0, (obj.stroke_width * 4.2) * self.zoom)
                a1 = QPointF(
                    p1.x() - head_len * math.cos(angle - math.pi / 6),
                    p1.y() - head_len * math.sin(angle - math.pi / 6),
                )
                a2 = QPointF(
                    p1.x() - head_len * math.cos(angle + math.pi / 6),
                    p1.y() - head_len * math.sin(angle + math.pi / 6),
                )
                painter.setBrush(QBrush(QColor(*obj.stroke_color)))
                painter.drawPolygon(QPolygonF([p1, a1, a2]))

        painter.restore()

    def _get_handle_rects(self, obj: PageEditObject) -> Dict[str, QRectF]:
        hs = self.HANDLE_SIZE
        if obj.kind in ("line", "arrow"):
            p0 = self.pdf_to_px(obj.rect[0], obj.rect[1])
            p1 = self.pdf_to_px(obj.rect[2], obj.rect[3])
            return {
                "p0": QRectF(p0.x() - hs / 2, p0.y() - hs / 2, hs, hs),
                "p1": QRectF(p1.x() - hs / 2, p1.y() - hs / 2, hs, hs),
            }
        qr = self.pdf_rect_to_qrectf(obj.rect)
        cx = qr.center().x()
        cy = qr.center().y()
        return {
            "tl": QRectF(qr.left() - hs / 2, qr.top() - hs / 2, hs, hs),
            "tm": QRectF(cx - hs / 2, qr.top() - hs / 2, hs, hs),
            "tr": QRectF(qr.right() - hs / 2, qr.top() - hs / 2, hs, hs),
            "ml": QRectF(qr.left() - hs / 2, cy - hs / 2, hs, hs),
            "mr": QRectF(qr.right() - hs / 2, cy - hs / 2, hs, hs),
            "bl": QRectF(qr.left() - hs / 2, qr.bottom() - hs / 2, hs, hs),
            "bm": QRectF(cx - hs / 2, qr.bottom() - hs / 2, hs, hs),
            "br": QRectF(qr.right() - hs / 2, qr.bottom() - hs / 2, hs, hs),
        }

    def _draw_selection_handles(self, painter: QPainter, obj: PageEditObject):
        painter.save()
        if obj.kind not in ("line", "arrow"):
            qr = self.pdf_rect_to_qrectf(obj.rect)
            pen = QPen(QColor(37, 99, 235), 1.8, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(qr.adjusted(-2, -2, 2, 2))

        handles = self._get_handle_rects(obj)
        painter.setPen(QPen(QColor(255, 255, 255), 1.5))
        painter.setBrush(QBrush(QColor(37, 99, 235)))
        for hrect in handles.values():
            painter.drawRect(hrect)
        painter.restore()

    # -----------------------------------------------------------------
    # Mouse & Keyboard Events (Universal Shape Selection & Re-Editing!)
    # -----------------------------------------------------------------
    def _hit_test_object(self, pos_px: QPointF) -> Optional[PageEditObject]:
        for obj in reversed(self.objects):
            if obj.kind in ("line", "arrow"):
                p0 = self.pdf_to_px(obj.rect[0], obj.rect[1])
                p1 = self.pdf_to_px(obj.rect[2], obj.rect[3])
                dx, dy = p1.x() - p0.x(), p1.y() - p0.y()
                length_sq = dx * dx + dy * dy
                if length_sq == 0:
                    dist = math.hypot(pos_px.x() - p0.x(), pos_px.y() - p0.y())
                else:
                    t = max(0.0, min(1.0, ((pos_px.x() - p0.x()) * dx + (pos_px.y() - p0.y()) * dy) / length_sq))
                    dist = math.hypot(pos_px.x() - (p0.x() + t * dx), pos_px.y() - (p0.y() + t * dy))
                if dist <= 10.0:
                    return obj
            else:
                qr = self.pdf_rect_to_qrectf(obj.rect).adjusted(-6, -6, 6, 6)
                if qr.contains(pos_px):
                    return obj
        return None

    def _hit_test_segment(self, pos_px: QPointF) -> Optional[DetectedTextSegment]:
        for seg in self.detected_segments:
            qr = self.pdf_rect_to_qrectf(seg.bbox).adjusted(-2, -2, 2, 2)
            if qr.contains(pos_px):
                return seg
        return None

    def mousePressEvent(self, event):
        if not self.page_pixmap:
            return
        pos_px = event.position()
        self._drag_start_px = pos_px

        if self._inline_editing_obj is not None:
            self.commit_inline_edit()

        if event.button() == Qt.MouseButton.LeftButton:
            x_pt, y_pt = self.px_to_pdf(pos_px.x(), pos_px.y())

            # In 'view' mode: purely reading/navigating or drag-selecting text for copying!
            if self.tool_mode == "view":
                self.selected_obj = None
                self.objectSelected.emit(None)
                self._pressed_segment = self._hit_test_segment(pos_px)
                if self._pressed_segment is not None:
                    self._dragging_mode = "view_select_text"
                    self._drag_start_pt = (x_pt, y_pt)
                    self._selected_seg_chars = []
                else:
                    self._dragging_mode = None
                    self._selected_seg_chars = []
                self.update()
                return

            # 1. Resize handles on currently selected object (works in ANY tool mode!)
            if self.selected_obj is not None:
                handles = self._get_handle_rects(self.selected_obj)
                for hname, hrect in handles.items():
                    if hrect.adjusted(-4, -4, 4, 4).contains(pos_px):
                        self._dragging_mode = f"handle_{hname}"
                        self._drag_start_pt = self.px_to_pdf(pos_px.x(), pos_px.y())
                        self._drag_orig_rect = list(self.selected_obj.rect)
                        return

            # 2. Clicking ANY existing shape or text object selects it immediately (works in ANY tool mode!)
            hit_obj = self._hit_test_object(pos_px)
            if hit_obj is not None:
                self.selected_obj = hit_obj
                self.objectSelected.emit(hit_obj)
                self._dragging_mode = "move"
                self._drag_start_pt = self.px_to_pdf(pos_px.x(), pos_px.y())
                self._drag_orig_rect = list(hit_obj.rect)
                self.update()
                return

            self._had_selected_before_press = (self.selected_obj is not None)

            # 3. In 'inplace_text' mode: allow dragging across specific words/phrases OR clicking
            if self.tool_mode == "inplace_text":
                seg = self._hit_test_segment(pos_px)
                if seg is not None:
                    self._dragging_mode = "select_text_chars"
                    self._pressed_segment = seg
                    self._drag_start_pt = (x_pt, y_pt)
                    self._char_sel_rect_pt = [x_pt, y_pt, x_pt, y_pt]
                    self._selected_seg_chars = []
                    return
                else:
                    self.selected_obj = None
                    self.objectSelected.emit(None)
                    self.update()
                    return

            elif self.tool_mode == "free_text":
                if self._had_selected_before_press:
                    # First click outside deselects current object cleanly
                    self.selected_obj = None
                    self.objectSelected.emit(None)
                    self.update()
                    return
                new_obj = PageEditObject(
                    obj_id=str(uuid.uuid4())[:8],
                    kind="free_text",
                    rect=[x_pt, y_pt, x_pt + 160.0, y_pt + max(24.0, self.default_font_size * 1.6)],
                    text="한글 텍스트 입력",
                    font_key=self.default_font_key,
                    font_size=self.default_font_size,
                    text_color=list(self.default_text_color),
                    stroke_color=list(self.default_stroke_color),
                    fill_color=list(self.default_fill_color),
                    use_fill=self.default_use_fill,
                    stroke_width=0.0,
                    opacity=self.default_opacity,
                )
                new_obj.runs = new_obj.get_effective_runs()
                self._auto_adjust_text_rect(new_obj)
                self.objects.append(new_obj)
                self.selected_obj = new_obj
                self.objectSelected.emit(new_obj)
                self.stateChanged.emit("새 한글 텍스트 상자 추가")
                self.start_inline_edit(new_obj, select_all=True)
                return

            elif self.tool_mode in ("rect", "ellipse", "line", "arrow", "highlight", "eraser"):
                # Prepare potential shape creation; only materialize on drag (or click if nothing was selected)
                self._dragging_mode = "create_pending"
                self._drag_start_pt = (x_pt, y_pt)
                self._creating_obj = None
                if self.selected_obj is not None:
                    self.selected_obj = None
                    self.objectSelected.emit(None)
                    self.update()
                return

            else:
                self.selected_obj = None
                self.objectSelected.emit(None)
                self.update()

    def mouseDoubleClickEvent(self, event):
        if not self.page_pixmap:
            return
        pos_px = event.position()
        if self.tool_mode == "view":
            seg = self._hit_test_segment(pos_px)
            if seg:
                QApplication.clipboard().setText(seg.text)
                self._selected_seg_chars = list(seg.chars)
                self.stateChanged.emit(f"📋 텍스트 복사됨 (클립보드): '{seg.text[:30]}'")
                self.update()
            return

        hit_obj = self._hit_test_object(pos_px)
        if hit_obj is not None:
            self.selected_obj = hit_obj
            self.objectSelected.emit(hit_obj)
            self._dragging_mode = None
            if hit_obj.kind in ("inplace_text", "free_text"):
                click_pt = self.px_to_pdf(pos_px.x(), pos_px.y())
                self.start_inline_edit(hit_obj, select_all=False, click_pdf_pt=click_pt)
            else:
                # Double-clicked on a shape (rect, ellipse, line, arrow, highlight): open quick shape editor!
                self.shapeDoubleClicked.emit(hit_obj)
            self.update()

    def mouseMoveEvent(self, event):
        if not self.page_pixmap:
            return
        pos_px = event.position()
        x_pt, y_pt = self.px_to_pdf(pos_px.x(), pos_px.y())

        # In View mode: allow text selection for copying, no shape dragging or hover borders!
        if self.tool_mode == "view":
            self.hovered_segment = None
            if self._dragging_mode == "view_select_text" and self._pressed_segment is not None:
                sx, _ = self._drag_start_pt
                min_x, max_x = min(sx, x_pt), max(sx, x_pt)
                if max_x - min_x >= 2.0 and self._pressed_segment.chars:
                    selected = []
                    for cinfo in self._pressed_segment.chars:
                        cb = cinfo["bbox"]
                        cx = (cb[0] + cb[2]) * 0.5
                        if min_x <= cx <= max_x or (cb[0] <= max_x and cb[2] >= min_x and abs(cx - sx) < 4.0):
                            selected.append(cinfo)
                    self._selected_seg_chars = selected
            else:
                seg = self._hit_test_segment(pos_px)
                if seg:
                    self.setCursor(Qt.CursorShape.IBeamCursor)
                    self.setToolTip("• 드래그: 텍스트 블록 선택 (Ctrl+C 복사)\n• 더블클릭: 문장 전체 복사\n• 본문 수정을 원하시면 상단 [📝 편집 모드]를 누르세요.")
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    self.setToolTip("")
            self.update()
            return

        # Drag-selecting specific characters / words inside a PDF text segment
        if self._dragging_mode == "select_text_chars" and self._pressed_segment is not None:
            sx, _ = self._drag_start_pt
            min_x, max_x = min(sx, x_pt), max(sx, x_pt)
            if max_x - min_x >= 2.0 and self._pressed_segment.chars:
                selected = []
                for cinfo in self._pressed_segment.chars:
                    cb = cinfo["bbox"]
                    cx = (cb[0] + cb[2]) * 0.5
                    if min_x <= cx <= max_x or (cb[0] <= max_x and cb[2] >= min_x and abs(cx - sx) < 4.0):
                        selected.append(cinfo)
                self._selected_seg_chars = selected
            else:
                self._selected_seg_chars = []
            self.update()
            return

        if self._dragging_mode == "create_pending":
            dist_px = math.hypot(pos_px.x() - self._drag_start_px.x(), pos_px.y() - self._drag_start_px.y())
            if dist_px >= 5.0:
                sx, sy = self._drag_start_pt
                if self.tool_mode == "eraser":
                    use_f = True
                    fill_c = [255, 255, 255]
                    opac = 1.0
                    sw = 0.0
                    sc = [255, 255, 255]
                elif self.tool_mode == "highlight":
                    use_f = True
                    fill_c = [253, 224, 71]
                    opac = 0.38
                    sw = self.default_stroke_width
                    sc = list(self.default_stroke_color)
                else:
                    use_f = self.default_use_fill
                    fill_c = list(self.default_fill_color)
                    opac = self.default_opacity
                    sw = self.default_stroke_width
                    sc = list(self.default_stroke_color)
                new_obj = PageEditObject(
                    obj_id=str(uuid.uuid4())[:8],
                    kind=self.tool_mode,
                    rect=[sx, sy, x_pt, y_pt],
                    font_key=self.default_font_key,
                    font_size=self.default_font_size,
                    text_color=list(self.default_text_color),
                    stroke_color=sc,
                    fill_color=fill_c,
                    use_fill=use_f,
                    stroke_width=sw,
                    opacity=opac,
                )
                self.objects.append(new_obj)
                self.selected_obj = new_obj
                self._creating_obj = new_obj
                self._dragging_mode = "create"
                self.objectSelected.emit(new_obj)

        if self._dragging_mode == "create" and self._creating_obj is not None:
            sx, sy = self._drag_start_pt
            is_constrained = bool(
                event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier)
            )
            if self._creating_obj.kind in ("line", "arrow"):
                if is_constrained:
                    dx = x_pt - sx
                    dy = y_pt - sy
                    angle = math.atan2(dy, dx)
                    # Snap to nearest 45 degrees
                    snapped = round(angle / (math.pi / 4.0)) * (math.pi / 4.0)
                    length = math.hypot(dx, dy)
                    cx = sx + length * math.cos(snapped)
                    cy = sy + length * math.sin(snapped)
                    self._creating_obj.rect = [sx, sy, cx, cy]
                else:
                    self._creating_obj.rect = [sx, sy, x_pt, y_pt]
            else:
                w = abs(x_pt - sx)
                h = abs(y_pt - sy)
                if is_constrained:
                    side = max(w, h)
                    cx = sx + (side if x_pt >= sx else -side)
                    cy = sy + (side if y_pt >= sy else -side)
                    self._creating_obj.rect = [min(sx, cx), min(sy, cy), max(sx, cx), max(sy, cy)]
                else:
                    self._creating_obj.rect = [min(sx, x_pt), min(sy, y_pt), max(sx, x_pt), max(sy, y_pt)]
            self.update()
            return

        if self._dragging_mode == "move" and self.selected_obj is not None and self._drag_orig_rect:
            dx = x_pt - self._drag_start_pt[0]
            dy = y_pt - self._drag_start_pt[1]
            r0 = self._drag_orig_rect
            self.selected_obj.rect = [r0[0] + dx, r0[1] + dy, r0[2] + dx, r0[3] + dy]
            self.update()
            return

        if self._dragging_mode and self._dragging_mode.startswith("handle_") and self.selected_obj is not None and self._drag_orig_rect:
            hname = self._dragging_mode.replace("handle_", "")
            r = list(self._drag_orig_rect)
            if hname == "p0":
                r[0], r[1] = x_pt, y_pt
            elif hname == "p1":
                r[2], r[3] = x_pt, y_pt
            else:
                if "l" in hname:
                    r[0] = min(x_pt, r[2] - 8.0)
                if "r" in hname:
                    r[2] = max(x_pt, r[0] + 8.0)
                if "t" in hname:
                    r[1] = min(y_pt, r[3] - 8.0)
                if "b" in hname:
                    r[3] = max(y_pt, r[1] + 8.0)
            self.selected_obj.rect = r
            self.update()
            return

        # Hover cursor feedback: prioritize handles & existing objects in ALL tool modes!
        if self.selected_obj is not None:
            for hname, hrect in self._get_handle_rects(self.selected_obj).items():
                if hrect.adjusted(-4, -4, 4, 4).contains(pos_px):
                    if hname in ("tl", "br"):
                        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                    elif hname in ("tr", "bl"):
                        self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                    elif hname in ("tm", "bm"):
                        self.setCursor(Qt.CursorShape.SizeVerCursor)
                    elif hname in ("ml", "mr"):
                        self.setCursor(Qt.CursorShape.SizeHorCursor)
                    else:
                        self.setCursor(Qt.CursorShape.CrossCursor)
                    return

        hit_obj = self._hit_test_object(pos_px)
        if hit_obj is not None:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            if hit_obj.kind in ("rect", "ellipse", "line", "arrow", "highlight"):
                self.setToolTip("• 클릭 후 드래그: 도형 이동 및 모서리 핸들 크기 조절\n• 더블클릭: 도형 스타일/텍스트 빠른 편집 창 열기")
            return

        if self.tool_mode == "inplace_text":
            seg = self._hit_test_segment(pos_px)
            if seg is not self.hovered_segment:
                self.hovered_segment = seg
                if seg is not None:
                    self.setCursor(Qt.CursorShape.IBeamCursor)
                    self.setToolTip(
                        f"• 원하는 단어나 문구만 마우스로 드래그하면 해당 부분만 블록 지정해 수정합니다.\n"
                        f"• 클릭하면 커서가 놓인 위치부터 자유롭게 부분 편집할 수 있습니다.\n"
                        f"• 원본 글꼴: {seg.pdf_font} ({seg.font_size:.1f}pt)"
                    )
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    self.setToolTip("")
                self.update()
        else:
            self.setToolTip("")
            if self.tool_mode in ("rect", "ellipse", "line", "arrow", "highlight", "free_text", "eraser"):
                self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        pos_px = event.position()
        x_pt, y_pt = self.px_to_pdf(pos_px.x(), pos_px.y())

        if self.tool_mode == "view":
            if self._dragging_mode == "view_select_text" and self._selected_seg_chars:
                txt = "".join(c["c"] for c in self._selected_seg_chars)
                if txt.strip():
                    QApplication.clipboard().setText(txt)
                    self.stateChanged.emit(f"📋 선택 텍스트 복사 완료 (Ctrl+C): '{txt[:30]}'")
            self._dragging_mode = None
            self.update()
            return

        # Finalize character/word drag selection or single-click in inplace_text mode
        if self._dragging_mode == "select_text_chars" and self._pressed_segment is not None:
            seg = self._pressed_segment
            sel_chars = list(self._selected_seg_chars)
            self._dragging_mode = None
            self._pressed_segment = None
            self._selected_seg_chars = []

            if sel_chars:
                sub_text = "".join(c["c"] for c in sel_chars)
                if sub_text.strip():
                    bx0 = min(c["bbox"][0] for c in sel_chars)
                    by0 = min(c["bbox"][1] for c in sel_chars)
                    bx1 = max(c["bbox"][2] for c in sel_chars)
                    by1 = max(c["bbox"][3] for c in sel_chars)
                    first_c = sel_chars[0]
                    matched_fk = self.font_registry.match_pdf_font_to_korean_key(
                        first_c.get("font", seg.pdf_font), first_c.get("bold", seg.is_bold)
                    )
                    new_obj = PageEditObject(
                        obj_id=str(uuid.uuid4())[:8],
                        kind="inplace_text",
                        rect=[bx0, by0, bx1, by1],
                        text=sub_text,
                        orig_text=sub_text,
                        orig_bbox=[bx0, by0, bx1, by1],
                        orig_origin=list(first_c.get("origin", seg.origin)),
                        orig_pdf_font=first_c.get("font", seg.pdf_font),
                        font_key=matched_fk,
                        font_size=round(float(first_c.get("size", seg.font_size)), 1),
                        bold=bool(first_c.get("bold", seg.is_bold)),
                        text_color=list(first_c.get("color", seg.color)),
                        fill_color=[255, 255, 255],
                        use_fill=False,
                        redact_stream_text=True,
                    )
                    new_obj.runs = new_obj.get_effective_runs()
                    self.objects.append(new_obj)
                    self.selected_obj = new_obj
                    self.objectSelected.emit(new_obj)
                    self.stateChanged.emit(f"선택 문구 부분 편집 ('{sub_text[:15]}')")
                    self.start_inline_edit(new_obj, select_all=True)
                    return

            # Otherwise, user single-clicked on `seg`: open line without selecting all, placing cursor at click!
            matched_fk = self.font_registry.match_pdf_font_to_korean_key(seg.pdf_font, seg.is_bold)
            new_obj = PageEditObject(
                obj_id=str(uuid.uuid4())[:8],
                kind="inplace_text",
                rect=list(seg.bbox),
                text=seg.text,
                orig_text=seg.text,
                orig_bbox=list(seg.bbox),
                orig_origin=list(seg.origin),
                orig_pdf_font=seg.pdf_font,
                font_key=matched_fk,
                font_size=round(seg.font_size, 1),
                bold=seg.is_bold,
                text_color=list(seg.color),
                fill_color=[255, 255, 255],
                use_fill=False,
                redact_stream_text=True,
            )
            new_obj.runs = new_obj.get_effective_runs()
            self.objects.append(new_obj)
            self.selected_obj = new_obj
            self.objectSelected.emit(new_obj)
            self.stateChanged.emit("기존 텍스트 편집")
            self.start_inline_edit(new_obj, select_all=False, click_pdf_pt=(x_pt, y_pt))
            return

        if self._dragging_mode == "create_pending":
            # User clicked on empty space without dragging while in shape mode:
            # If no object was selected prior to click, create a default-sized shape;
            # If an object WAS selected prior to click, just keep it deselected!
            if not self._had_selected_before_press:
                sx, sy = self._drag_start_pt
                if self.tool_mode == "eraser":
                    use_f = True
                    fill_c = [255, 255, 255]
                    opac = 1.0
                    sw = 0.0
                    sc = [255, 255, 255]
                    def_w, def_h = 80.0, 28.0
                elif self.tool_mode == "highlight":
                    use_f = True
                    fill_c = [253, 224, 71]
                    opac = 0.38
                    sw = self.default_stroke_width
                    sc = list(self.default_stroke_color)
                    def_w, def_h = 90.0, 22.0
                else:
                    use_f = self.default_use_fill
                    fill_c = list(self.default_fill_color)
                    opac = self.default_opacity
                    sw = self.default_stroke_width
                    sc = list(self.default_stroke_color)
                    def_w, def_h = 90.0, 50.0
                new_obj = PageEditObject(
                    obj_id=str(uuid.uuid4())[:8],
                    kind=self.tool_mode,
                    rect=[sx, sy, sx + def_w, sy + def_h],
                    font_key=self.default_font_key,
                    font_size=self.default_font_size,
                    text_color=list(self.default_text_color),
                    stroke_color=sc,
                    fill_color=fill_c,
                    use_fill=use_f,
                    stroke_width=sw,
                    opacity=opac,
                )
                self.objects.append(new_obj)
                self.selected_obj = new_obj
                self.objectSelected.emit(new_obj)
                desc = "지우개 영역 추가 (화이트아웃)" if new_obj.kind == "eraser" else f"도형 추가 ({new_obj.kind})"
                self.stateChanged.emit(desc)
            self._dragging_mode = None
            self.update()
            return

        if self._dragging_mode == "create" and self._creating_obj is not None:
            desc = "지우개 영역 추가 (화이트아웃)" if self._creating_obj.kind == "eraser" else f"도형 추가 ({self._creating_obj.kind})"
            self.stateChanged.emit(desc)
            self._creating_obj = None
        elif self._dragging_mode == "move" or (self._dragging_mode and self._dragging_mode.startswith("handle_")):
            if self.selected_obj and self._drag_orig_rect != self.selected_obj.rect:
                self.stateChanged.emit("객체 이동/크기 조절")
            elif self._dragging_mode == "move" and self.selected_obj and self.selected_obj.kind in ("inplace_text", "free_text"):
                # Single click on an already-created text object opens inline editor at click pos!
                self.start_inline_edit(self.selected_obj, select_all=False, click_pdf_pt=(x_pt, y_pt))

        self._dragging_mode = None
        self._drag_orig_rect = None
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self._inline_editing_obj is not None:
                self.commit_inline_edit()
            self.selected_obj = None
            self.objectSelected.emit(None)
            self._selected_seg_chars = []
            self.requestViewMode.emit()
            self.update()
            return

        if event.matches(QKeySequence.StandardKey.Copy) or (
            event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_C
        ):
            if self._selected_seg_chars:
                txt = "".join(c.get("c", "") for c in self._selected_seg_chars)
                if txt.strip():
                    QApplication.clipboard().setText(txt)
                    self.stateChanged.emit(f"📋 텍스트 복사됨 (클립보드): '{txt[:30]}'")
                    return

        if self._inline_editing_obj is not None:
            super().keyPressEvent(event)
            return

        if self.tool_mode != "view" and event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.selected_obj is not None:
            self.objects.remove(self.selected_obj)
            self.selected_obj = None
            self.objectSelected.emit(None)
            self.stateChanged.emit("객체 삭제")
            self.update()
            return

        if self.tool_mode != "view" and self.selected_obj is not None and event.key() in (
            Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down
        ):
            step = 5.0 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1.0
            dx = -step if event.key() == Qt.Key.Key_Left else (step if event.key() == Qt.Key.Key_Right else 0.0)
            dy = -step if event.key() == Qt.Key.Key_Up else (step if event.key() == Qt.Key.Key_Down else 0.0)
            r = self.selected_obj.rect
            self.selected_obj.rect = [r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy]
            self.stateChanged.emit("객체 위치 미세 조정")
            self.update()
            return

        super().keyPressEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoomRequest.emit(1)
            elif delta < 0:
                self.zoomRequest.emit(-1)
            event.accept()
            return
        event.ignore()


# =====================================================================
# 3.5 Smart Scroll Area with Wheel Page Navigation
# =====================================================================
class SmartPDFScrollArea(QScrollArea):
    """
    Enhanced QScrollArea with smart wheel page boundary detection.
    When scrolling down past the bottom of a page, automatically jumps to the next page.
    When scrolling up past the top of a page, automatically jumps to the previous page.
    Supports both Single Page (page-by-page jump) and Continuous Scroll modes.
    """
    pageChangeRequested = pyqtSignal(int, str)  # (direction: +1 or -1, target_pos: "top" or "bottom")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_jump_time: float = 0.0
        self.scroll_mode: str = "continuous"  # "single_page" or "continuous"
        self.viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched == self.viewport() and event.type() == QEvent.Type.Wheel:
            if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                delta = event.angleDelta().y()
                vsb = self.verticalScrollBar()
                at_bottom = (vsb.value() >= vsb.maximum() - 3)
                at_top = (vsb.value() <= vsb.minimum() + 3)
                now = time.time()

                if delta < 0 and at_bottom:
                    if now - self._last_jump_time > 0.22:
                        self._last_jump_time = now
                        self.pageChangeRequested.emit(1, "top")
                        return True

                if delta > 0 and at_top:
                    if now - self._last_jump_time > 0.22:
                        self._last_jump_time = now
                        self.pageChangeRequested.emit(-1, "bottom")
                        return True

        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            event.ignore()
            return
        super().keyPressEvent(event)


# =====================================================================
# 3.6 Continuous Page Scroll Viewer (Acrobat-Style Enable Scrolling)
# =====================================================================
class ContinuousPDFCanvas(QWidget):
    pageDoubleClicked = pyqtSignal(int)
    pageClicked = pyqtSignal(int)
    zoomRequest = pyqtSignal(int)

    PAGE_GAP = 18
    MARGIN_Y = 18
    MARGIN_X = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: Optional[fitz.Document] = None
        self.base_pdf_bytes: Optional[bytes] = None
        self.zoom: float = 1.0
        self.is_dark_theme: bool = True
        self.page_rects: List[QRectF] = []
        self._pixmap_cache: Dict[Tuple[int, int], QPixmap] = {}
        self.search_results: Dict[int, List[Tuple[float, float, float, float]]] = {}
        self.current_search_page: int = -1
        self.current_search_rect_idx: int = -1
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_document(self, doc: Optional[fitz.Document], base_pdf_bytes: Optional[bytes], zoom: float = 1.0):
        self.doc = doc
        self.base_pdf_bytes = base_pdf_bytes
        self.zoom = zoom
        self._pixmap_cache.clear()
        self.recalculate_layout()

    def set_zoom(self, zoom: float):
        if abs(self.zoom - zoom) > 1e-4:
            self.zoom = zoom
            self._pixmap_cache.clear()
            self.recalculate_layout()

    def recalculate_layout(self):
        self.page_rects.clear()
        if not self.doc or len(self.doc) == 0:
            self.resize(300, 300)
            self.update()
            return

        viewport_w = 800
        p = self.parent()
        if p is not None:
            if hasattr(p, "viewport"):
                viewport_w = max(300, p.viewport().width())
            else:
                viewport_w = max(300, p.width())

        curr_y = float(self.MARGIN_Y)
        max_pw = 0.0
        for i in range(len(self.doc)):
            page = self.doc[i]
            pw = page.rect.width * self.zoom
            ph = page.rect.height * self.zoom
            if pw > max_pw:
                max_pw = pw
            curr_y += ph + self.PAGE_GAP

        total_w = max(float(viewport_w), max_pw + self.MARGIN_X * 2)
        total_h = curr_y + self.MARGIN_Y

        curr_y = float(self.MARGIN_Y)
        for i in range(len(self.doc)):
            page = self.doc[i]
            pw = page.rect.width * self.zoom
            ph = page.rect.height * self.zoom
            x = (total_w - pw) / 2.0
            self.page_rects.append(QRectF(x, curr_y, pw, ph))
            curr_y += ph + self.PAGE_GAP

        self.resize(int(total_w), int(total_h))
        self.update()

    def _get_page_pixmap(self, page_idx: int) -> Optional[QPixmap]:
        if not self.doc or page_idx < 0 or page_idx >= len(self.doc):
            return None
        zoom_key = int(round(self.zoom * 100))
        cache_key = (page_idx, zoom_key)
        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]

        try:
            page = self.doc[page_idx]
            dpr = self.devicePixelRatioF()
            scale = self.zoom * dpr
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
            qpix = QPixmap.fromImage(qimg)
            qpix.setDevicePixelRatio(dpr)
            if len(self._pixmap_cache) > 40:
                self._pixmap_cache.pop(next(iter(self._pixmap_cache)))
            self._pixmap_cache[cache_key] = qpix
            return qpix
        except Exception:
            return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        bg_col = QColor(30, 34, 42) if self.is_dark_theme else QColor(218, 224, 233)
        painter.fillRect(event.rect(), bg_col)

        if not self.doc or len(self.doc) == 0:
            return

        clip = event.rect()
        shadow_col = QColor(0, 0, 0, 110) if self.is_dark_theme else QColor(15, 23, 42, 55)
        border_pen = QPen(QColor(75, 85, 99) if self.is_dark_theme else QColor(148, 163, 184), 1.0)
        badge_font = QFont("Malgun Gothic", 9, QFont.Weight.Bold)

        for i, r in enumerate(self.page_rects):
            if r.intersects(QRectF(clip)):
                painter.save()
                try:
                    # Shadow
                    painter.fillRect(r.translated(4, 4), shadow_col)
                    # White page sheet
                    painter.fillRect(r, Qt.GlobalColor.white)
                    # Pixmap
                    pix = self._get_page_pixmap(i)
                    if pix and not pix.isNull():
                        painter.drawPixmap(r.topLeft(), pix)

                    # Search Highlights on this page (노란색/오렌지 형광펜 강조)
                    if i in self.search_results:
                        for s_idx, sr in enumerate(self.search_results[i]):
                            hx = r.x() + sr[0] * self.zoom
                            hy = r.y() + sr[1] * self.zoom
                            hw = (sr[2] - sr[0]) * self.zoom
                            hh = (sr[3] - sr[1]) * self.zoom
                            highlight_rect = QRectF(hx, hy, hw, hh)

                            is_current = (i == self.current_search_page and s_idx == self.current_search_rect_idx)
                            if is_current:
                                # 현재 포커스된 검색어: 눈에 확 띄는 진한 오렌지/옐로우 형광펜 + 굵은 주황 테두리
                                painter.fillRect(highlight_rect, QColor(255, 170, 0, 160))
                                painter.setPen(QPen(QColor(234, 88, 12), 2.2))
                                painter.drawRect(highlight_rect)
                            else:
                                # 다른 일치 검색어: 선명한 형광 노란색 (Yellow Highlight) + 부드러운 테두리
                                painter.fillRect(highlight_rect, QColor(255, 235, 59, 140))
                                painter.setPen(QPen(QColor(202, 138, 4), 1.2))
                                painter.drawRect(highlight_rect)

                    # Border (브러시를 NoBrush로 강제하여 페이지 내부가 반투명하게 덮이지 않도록 방어)
                    painter.setPen(border_pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(r)

                    # Page number badge at bottom right
                    badge_text = f"{i + 1} / {len(self.doc)}"
                    badge_w = 64
                    badge_h = 20
                    badge_rect = QRectF(r.right() - badge_w - 6, r.bottom() - badge_h - 6, badge_w, badge_h)
                    painter.setBrush(QBrush(QColor(15, 23, 42, 180) if self.is_dark_theme else QColor(241, 245, 249, 210)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(badge_rect, 4, 4)
                    painter.setFont(badge_font)
                    painter.setPen(QColor(241, 245, 249) if self.is_dark_theme else QColor(30, 41, 59))
                    painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)
                finally:
                    painter.restore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            for i, r in enumerate(self.page_rects):
                if r.contains(pos):
                    self.pageClicked.emit(i)
                    break
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            for i, r in enumerate(self.page_rects):
                if r.contains(pos):
                    self.pageDoubleClicked.emit(i)
                    break
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoomRequest.emit(1)
            elif delta < 0:
                self.zoomRequest.emit(-1)
            event.accept()
            return
        super().wheelEvent(event)


class ContinuousPDFScrollArea(QScrollArea):
    pageChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.continuous_canvas = ContinuousPDFCanvas(self)
        self.setWidget(self.continuous_canvas)
        self.setStyleSheet("QScrollArea { background-color: #DAE0E9; border: none; }")
        if self.viewport():
            self.viewport().setStyleSheet("background-color: #DAE0E9;")

        self._current_page_idx = -1
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.continuous_canvas.recalculate_layout()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            event.ignore()
            return
        super().keyPressEvent(event)

    def _on_scroll(self, value):
        if not self.continuous_canvas.page_rects:
            return
        center_y = value + self.viewport().height() * 0.45
        found_idx = 0
        for i, r in enumerate(self.continuous_canvas.page_rects):
            if r.top() <= center_y <= r.bottom() + self.continuous_canvas.PAGE_GAP:
                found_idx = i
                break
            elif center_y < r.top():
                found_idx = max(0, i - 1)
                break
            found_idx = i

        if found_idx != self._current_page_idx:
            self._current_page_idx = found_idx
            self.pageChanged.emit(found_idx)

    def scroll_to_page(self, page_idx: int):
        if 0 <= page_idx < len(self.continuous_canvas.page_rects):
            r = self.continuous_canvas.page_rects[page_idx]
            target_y = max(0, int(r.top() - 14))
            self.verticalScrollBar().setValue(target_y)
            self._current_page_idx = page_idx

    def scroll_to_rect(self, page_idx: int, pdf_rect: Tuple[float, float, float, float]):
        """검색된 특정 단어/영역이 뷰포트의 정중앙에 위치하도록 수직 스크롤을 이동합니다."""
        if 0 <= page_idx < len(self.continuous_canvas.page_rects):
            pr = self.continuous_canvas.page_rects[page_idx]
            ry = pr.top() + pdf_rect[1] * self.continuous_canvas.zoom
            rh = (pdf_rect[3] - pdf_rect[1]) * self.continuous_canvas.zoom
            viewport_h = max(200, self.viewport().height())
            target_y = max(0, int(ry - (viewport_h - rh) / 2.0))
            self.verticalScrollBar().setValue(target_y)
            self._current_page_idx = page_idx



# =====================================================================
# 4. Acrobat-Style Print Dialog (REA ExLang32.KOR MainPrintDialog)
#    Supports 1-up (Fit/Actual/Shrink/Custom %), N-up (2/4/6/9/16/Custom Grid),
#    Paper Size, Orientation (Auto/Portrait/Landscape), Duplex, Grayscale,
#    Printer Selection, Native Printer Properties & Live Sheet Preview!
# =====================================================================

class _Win32DevModeHeader(ctypes.Structure):
    """Standard 220-byte Win32 DEVMODEW header followed by driver-specific dmDriverExtra bytes."""
    _fields_ = [
        ("dmDeviceName", ctypes.wintypes.WCHAR * 32),
        ("dmSpecVersion", ctypes.wintypes.WORD),
        ("dmDriverVersion", ctypes.wintypes.WORD),
        ("dmSize", ctypes.wintypes.WORD),
        ("dmDriverExtra", ctypes.wintypes.WORD),
        ("dmFields", ctypes.wintypes.DWORD),
        ("dmOrientation", ctypes.c_short),
        ("dmPaperSize", ctypes.c_short),
        ("dmPaperLength", ctypes.c_short),
        ("dmPaperWidth", ctypes.c_short),
        ("dmScale", ctypes.c_short),
        ("dmCopies", ctypes.c_short),
        ("dmDefaultSource", ctypes.c_short),
        ("dmPrintQuality", ctypes.c_short),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", ctypes.wintypes.WCHAR * 32),
        ("dmLogPixels", ctypes.wintypes.WORD),
        ("dmBitsPerPel", ctypes.wintypes.DWORD),
        ("dmPelsWidth", ctypes.wintypes.DWORD),
        ("dmPelsHeight", ctypes.wintypes.DWORD),
        ("dmDisplayFlags", ctypes.wintypes.DWORD),
        ("dmDisplayFrequency", ctypes.wintypes.DWORD),
        ("dmICMMethod", ctypes.wintypes.DWORD),
        ("dmICMIntent", ctypes.wintypes.DWORD),
        ("dmMediaType", ctypes.wintypes.DWORD),
        ("dmDitherType", ctypes.wintypes.DWORD),
        ("dmReserved1", ctypes.wintypes.DWORD),
        ("dmReserved2", ctypes.wintypes.DWORD),
        ("dmPanningWidth", ctypes.wintypes.DWORD),
        ("dmPanningHeight", ctypes.wintypes.DWORD),
    ]


class _Win32DocInfoW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_int),
        ("lpszDocName", ctypes.wintypes.LPCWSTR),
        ("lpszOutput", ctypes.wintypes.LPCWSTR),
        ("lpszDatatype", ctypes.wintypes.LPCWSTR),
        ("fwType", ctypes.wintypes.DWORD),
    ]


class _Win32BitmapInfoHeader(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.wintypes.DWORD),
        ("biWidth", ctypes.wintypes.LONG),
        ("biHeight", ctypes.wintypes.LONG),
        ("biPlanes", ctypes.wintypes.WORD),
        ("biBitCount", ctypes.wintypes.WORD),
        ("biCompression", ctypes.wintypes.DWORD),
        ("biSizeImage", ctypes.wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.wintypes.LONG),
        ("biYPelsPerMeter", ctypes.wintypes.LONG),
        ("biClrUsed", ctypes.wintypes.DWORD),
        ("biClrImportant", ctypes.wintypes.DWORD),
    ]


class AcrobatPrintDialog(QDialog):
    """Full-featured print dialog modeled after Adobe Acrobat DC MainPrintDialog (ExLang32.KOR)."""

    PAPER_SIZES = [
        ("A4 (210 × 297 mm)", QPageSize.PageSizeId.A4, (210.0, 297.0)),
        ("A3 (297 × 420 mm)", QPageSize.PageSizeId.A3, (297.0, 420.0)),
        ("B4 (250 × 353 mm)", QPageSize.PageSizeId.B4, (250.0, 353.0)),
        ("B5 (176 × 250 mm)", QPageSize.PageSizeId.B5, (176.0, 250.0)),
        ("Letter (215.9 × 279.4 mm)", QPageSize.PageSizeId.Letter, (215.9, 279.4)),
        ("Legal (215.9 × 355.6 mm)", QPageSize.PageSizeId.Legal, (215.9, 355.6)),
    ]

    # Map between Qt QPageSize.PageSizeId and Win32 DMPAPER_* constants
    _QT_TO_DMPAPER = {
        QPageSize.PageSizeId.A4: 9,       # DMPAPER_A4
        QPageSize.PageSizeId.A3: 8,       # DMPAPER_A3
        QPageSize.PageSizeId.B4: 12,      # DMPAPER_B4
        QPageSize.PageSizeId.B5: 13,      # DMPAPER_B5
        QPageSize.PageSizeId.Letter: 1,   # DMPAPER_LETTER
        QPageSize.PageSizeId.Legal: 5,    # DMPAPER_LEGAL
    }
    _DMPAPER_TO_QT = {v: k for k, v in _QT_TO_DMPAPER.items()}

    def __init__(self, doc: fitz.Document, current_page_1based: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("인쇄 설정 (Adobe Acrobat DC 인쇄 옵션 & 미리보기)")
        self.resize(1020, 720)
        self.doc = doc
        self.total_pages = len(doc)
        self.current_page = current_page_1based

        self.printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self.available_printers = QPrinterInfo.availablePrinters()
        default_p = QPrinterInfo.defaultPrinter()
        self._printer_devmodes: Dict[str, ctypes.Array] = {}

        self.current_sheet_idx = 0
        self.computed_sheets: List[List[int]] = []   # List of sheets, each containing 0-based page indices
        self._page_img_cache: Dict[Tuple[int, bool, bool], QImage] = {}

        main_h = QHBoxLayout(self)

        # Left column: All Acrobat Print Settings
        left_w = QWidget()
        left_v = QVBoxLayout(left_w)
        left_v.setContentsMargins(4, 4, 4, 4)

        # 1) Printer & Copies Group
        grp_printer = QGroupBox("프린터 및 기본 옵션 (Printer)")
        f_printer = QFormLayout(grp_printer)

        prn_row = QHBoxLayout()
        self.printer_combo = QComboBox()
        self.printer_combo.setView(QListView())
        default_idx = 0
        for i, pinfo in enumerate(self.available_printers):
            self.printer_combo.addItem(pinfo.printerName(), pinfo)
            if not default_p.isNull() and pinfo.printerName() == default_p.printerName():
                default_idx = i
        if self.available_printers:
            self.printer_combo.setCurrentIndex(default_idx)
        self.printer_combo.currentIndexChanged.connect(self._on_printer_changed)
        prn_row.addWidget(self.printer_combo, 1)

        btn_prn_props = QPushButton("⚙️ 프린터 속성(옵션)...")
        btn_prn_props.setToolTip("선택한 프린터의 드라이버 고유 속성 및 용지함·품질 옵션을 엽니다.")
        btn_prn_props.clicked.connect(self._open_native_printer_properties)
        prn_row.addWidget(btn_prn_props)
        f_printer.addRow("프린터:", prn_row)

        copies_row = QHBoxLayout()
        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 999)
        self.copies_spin.setValue(1)
        copies_row.addWidget(self.copies_spin)

        btn_cp_down = QPushButton("－")
        btn_cp_down.setFixedWidth(28)
        btn_cp_down.clicked.connect(self.copies_spin.stepDown)
        copies_row.addWidget(btn_cp_down)

        btn_cp_up = QPushButton("＋")
        btn_cp_up.setFixedWidth(28)
        btn_cp_up.clicked.connect(self.copies_spin.stepUp)
        copies_row.addWidget(btn_cp_up)

        self.chk_collate = QCheckBox("한 부씩 인쇄")
        self.chk_collate.setChecked(True)
        copies_row.addWidget(self.chk_collate)
        f_printer.addRow("복사 매수:", copies_row)

        color_row = QHBoxLayout()
        self.chk_grayscale = QCheckBox("회색조(흑백)로 인쇄")
        self.chk_grayscale.toggled.connect(self._recompute_and_preview)
        color_row.addWidget(self.chk_grayscale)

        self.chk_toner_save = QCheckBox("토너 절약 모드 (15% 밝게)")
        self.chk_toner_save.toggled.connect(self._recompute_and_preview)
        color_row.addWidget(self.chk_toner_save)
        f_printer.addRow("색상/토너:", color_row)

        left_v.addWidget(grp_printer)

        # 2) Pages to Print Group (인쇄할 페이지)
        grp_pages = QGroupBox("인쇄할 페이지 (Pages to Print)")
        v_pages = QVBoxLayout(grp_pages)

        self.rb_pages_all = QRadioButton(f"모든 페이지 (전체 1 ~ {self.total_pages}p)")
        self.rb_pages_cur = QRadioButton(f"현재 페이지 ({self.current_page}p)")
        self.rb_pages_range = QRadioButton("페이지 지정:")
        self.rb_pages_all.setChecked(True)

        range_h = QHBoxLayout()
        range_h.addWidget(self.rb_pages_range)
        self.page_range_edit = QLineEdit(f"1-{self.total_pages}")
        self.page_range_edit.setPlaceholderText("예: 1-3, 5, 7-10")
        self.page_range_edit.textChanged.connect(lambda: (self.rb_pages_range.setChecked(True), self._recompute_and_preview()))
        range_h.addWidget(self.page_range_edit, 1)

        v_pages.addWidget(self.rb_pages_all)
        v_pages.addWidget(self.rb_pages_cur)
        v_pages.addLayout(range_h)

        sub_page_row = QHBoxLayout()
        sub_page_row.addWidget(QLabel("홀짝 선택:"))
        self.subset_combo = QComboBox()
        self.subset_combo.setView(QListView())
        self.subset_combo.addItem("범위 내의 모든 페이지", "all")
        self.subset_combo.addItem("홀수 페이지만", "odd")
        self.subset_combo.addItem("짝수 페이지만", "even")
        self.subset_combo.currentIndexChanged.connect(self._recompute_and_preview)
        sub_page_row.addWidget(self.subset_combo, 1)

        self.chk_reverse_pages = QCheckBox("역순으로 페이지 인쇄")
        self.chk_reverse_pages.toggled.connect(self._recompute_and_preview)
        sub_page_row.addWidget(self.chk_reverse_pages)
        v_pages.addLayout(sub_page_row)

        for rb in (self.rb_pages_all, self.rb_pages_cur, self.rb_pages_range):
            rb.toggled.connect(self._recompute_and_preview)

        left_v.addWidget(grp_pages)

        # 3) Page Sizing & Handling (페이지 크기 조정 및 처리: 1면 1페이지 vs 1면 N페이지)
        grp_handling = QGroupBox("페이지 크기 조정 및 처리 (Page Sizing & Handling)")
        v_handling = QVBoxLayout(grp_handling)

        mode_btn_row = QHBoxLayout()
        self.btn_mode_1up = QPushButton("📄 크기 (1면에 1페이지)")
        self.btn_mode_1up.setCheckable(True)
        self.btn_mode_1up.setChecked(True)
        self.btn_mode_nup = QPushButton("📑 다중 (1면에 N페이지 모아찍기)")
        self.btn_mode_nup.setCheckable(True)

        self.handling_group = QButtonGroup(self)
        self.handling_group.setExclusive(True)
        self.handling_group.addButton(self.btn_mode_1up, 0)
        self.handling_group.addButton(self.btn_mode_nup, 1)
        mode_btn_row.addWidget(self.btn_mode_1up)
        mode_btn_row.addWidget(self.btn_mode_nup)
        v_handling.addLayout(mode_btn_row)

        self.handling_stack = QStackedWidget()

        # Stack Page 0: 1-up (크기: 용지 크기 맞추기, 실제 크기, 큰 페이지 축소, 사용자 지정 비율)
        page_1up = QWidget()
        v_1up = QVBoxLayout(page_1up)
        v_1up.setContentsMargins(4, 4, 4, 4)

        self.rb_scale_fit = QRadioButton("용지 크기에 맞추기 (Fit — 여백에 맞춰 확대/축소)")
        self.rb_scale_actual = QRadioButton("실제 크기 (Actual Size — 100% 원본 크기)")
        self.rb_scale_shrink = QRadioButton("큰 페이지 축소 (Shrink Oversized Pages)")
        self.rb_scale_custom = QRadioButton("사용자 지정 비율 (%):")
        self.rb_scale_fit.setChecked(True)

        custom_scale_row = QHBoxLayout()
        custom_scale_row.addWidget(self.rb_scale_custom)
        self.custom_scale_spin = QDoubleSpinBox()
        self.custom_scale_spin.setRange(10.0, 400.0)
        self.custom_scale_spin.setSingleStep(5.0)
        self.custom_scale_spin.setValue(100.0)
        self.custom_scale_spin.setSuffix(" %")
        self.custom_scale_spin.valueChanged.connect(lambda: (self.rb_scale_custom.setChecked(True), self._recompute_and_preview()))
        custom_scale_row.addWidget(self.custom_scale_spin)

        btn_sc_down = QPushButton("－")
        btn_sc_down.setFixedWidth(28)
        btn_sc_down.clicked.connect(self.custom_scale_spin.stepDown)
        custom_scale_row.addWidget(btn_sc_down)

        btn_sc_up = QPushButton("＋")
        btn_sc_up.setFixedWidth(28)
        btn_sc_up.clicked.connect(self.custom_scale_spin.stepUp)
        custom_scale_row.addWidget(btn_sc_up)
        custom_scale_row.addStretch()

        self.chk_center_page = QCheckBox("용지 가로/세로 중앙에 배치")
        self.chk_center_page.setChecked(True)
        self.chk_center_page.toggled.connect(self._recompute_and_preview)

        for rb in (self.rb_scale_fit, self.rb_scale_actual, self.rb_scale_shrink, self.rb_scale_custom):
            rb.toggled.connect(self._recompute_and_preview)

        v_1up.addWidget(self.rb_scale_fit)
        v_1up.addWidget(self.rb_scale_actual)
        v_1up.addWidget(self.rb_scale_shrink)
        v_1up.addLayout(custom_scale_row)
        v_1up.addWidget(self.chk_center_page)
        self.handling_stack.addWidget(page_1up)

        # Stack Page 1: N-up (다중: 1면에 2, 4, 6, 9, 16, 사용자 지정 열×행)
        page_nup = QWidget()
        f_nup = QFormLayout(page_nup)
        f_nup.setContentsMargins(4, 4, 4, 4)

        self.nup_preset_combo = QComboBox()
        self.nup_preset_combo.setView(QListView())
        self.nup_preset_combo.addItem("1면에 2페이지 (2-up)", (2, 1))
        self.nup_preset_combo.addItem("1면에 4페이지 (2 × 2)", (2, 2))
        self.nup_preset_combo.addItem("1면에 6페이지 (3 × 2)", (3, 2))
        self.nup_preset_combo.addItem("1면에 9페이지 (3 × 3)", (3, 3))
        self.nup_preset_combo.addItem("1면에 16페이지 (4 × 4)", (4, 4))
        self.nup_preset_combo.addItem("사용자 지정 (가로 열 × 세로 행)...", "custom")
        self.nup_preset_combo.currentIndexChanged.connect(self._on_nup_preset_changed)
        f_nup.addRow("당 페이지 수:", self.nup_preset_combo)

        grid_row = QHBoxLayout()
        grid_row.addWidget(QLabel("가로(열):"))
        self.nup_cols_spin = QSpinBox()
        self.nup_cols_spin.setRange(1, 8)
        self.nup_cols_spin.setValue(2)
        self.nup_cols_spin.setEnabled(False)
        self.nup_cols_spin.valueChanged.connect(self._recompute_and_preview)
        grid_row.addWidget(self.nup_cols_spin)

        grid_row.addWidget(QLabel("× 세로(행):"))
        self.nup_rows_spin = QSpinBox()
        self.nup_rows_spin.setRange(1, 8)
        self.nup_rows_spin.setValue(1)
        self.nup_rows_spin.setEnabled(False)
        self.nup_rows_spin.valueChanged.connect(self._recompute_and_preview)
        grid_row.addWidget(self.nup_rows_spin)
        grid_row.addStretch()
        f_nup.addRow("그리드 배열:", grid_row)

        self.nup_order_combo = QComboBox()
        self.nup_order_combo.setView(QListView())
        self.nup_order_combo.addItem("가로 (좌→우, 위→아래)", "hor")
        self.nup_order_combo.addItem("가로 반전 (우→좌, 위→아래)", "hor_rev")
        self.nup_order_combo.addItem("세로 (위→아래, 좌→우)", "ver")
        self.nup_order_combo.addItem("세로 반전 (위→아래, 우→좌)", "ver_rev")
        self.nup_order_combo.currentIndexChanged.connect(self._recompute_and_preview)
        f_nup.addRow("페이지 순서:", self.nup_order_combo)

        self.chk_nup_border = QCheckBox("각 페이지 테두리선 인쇄 (Print Page Border)")
        self.chk_nup_border.setChecked(True)
        self.chk_nup_border.toggled.connect(self._recompute_and_preview)
        f_nup.addRow("테두리:", self.chk_nup_border)

        self.handling_stack.addWidget(page_nup)
        v_handling.addWidget(self.handling_stack)

        self.btn_mode_1up.clicked.connect(lambda: (self.handling_stack.setCurrentIndex(0), self._recompute_and_preview()))
        self.btn_mode_nup.clicked.connect(lambda: (self.handling_stack.setCurrentIndex(1), self._recompute_and_preview()))

        left_v.addWidget(grp_handling)

        # 4) Paper Size, Orientation & Duplex (용지 크기, 가로/세로 방향, 양면 옵션)
        grp_paper = QGroupBox("용지 크기 및 가로/세로 방향 (Paper & Orientation)")
        f_paper = QFormLayout(grp_paper)

        self.paper_combo = QComboBox()
        self.paper_combo.setView(QListView())
        for label, pid, mm_dims in self.PAPER_SIZES:
            self.paper_combo.addItem(label, (pid, mm_dims))
        self.paper_combo.currentIndexChanged.connect(self._recompute_and_preview)
        f_paper.addRow("용지 크기:", self.paper_combo)

        orient_row = QHBoxLayout()
        self.rb_orient_auto = QRadioButton("자동 가로/세로 맞춤")
        self.rb_orient_port = QRadioButton("세로 방향 (Portrait)")
        self.rb_orient_land = QRadioButton("가로 방향 (Landscape)")
        self.rb_orient_auto.setChecked(True)

        self.orient_group = QButtonGroup(self)
        for rb in (self.rb_orient_auto, self.rb_orient_port, self.rb_orient_land):
            self.orient_group.addButton(rb)
            orient_row.addWidget(rb)
            rb.toggled.connect(self._recompute_and_preview)
        f_paper.addRow("용지 방향:", orient_row)

        self.duplex_combo = QComboBox()
        self.duplex_combo.setView(QListView())
        self.duplex_combo.addItem("단면 인쇄 (Simplex)", QPrinter.DuplexMode.DuplexNone)
        self.duplex_combo.addItem("양면 인쇄 — 긴 쪽으로 넘김 (Flip Long Edge)", QPrinter.DuplexMode.DuplexLongSide)
        self.duplex_combo.addItem("양면 인쇄 — 짧은 쪽으로 넘김 (Flip Short Edge)", QPrinter.DuplexMode.DuplexShortSide)
        f_paper.addRow("양면 인쇄:", self.duplex_combo)

        left_v.addWidget(grp_paper)
        left_v.addStretch()

        # Bottom Print / Cancel buttons
        action_row = QHBoxLayout()
        action_row.addStretch()
        btn_do_print = QPushButton("🖨️ 인쇄 실행")
        btn_do_print.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; font-size: 11pt; padding: 8px 24px;"
        )
        btn_do_print.clicked.connect(self.accept)
        btn_cancel = QPushButton("취소")
        btn_cancel.setStyleSheet("padding: 8px 18px;")
        btn_cancel.clicked.connect(self.reject)
        action_row.addWidget(btn_do_print)
        action_row.addWidget(btn_cancel)
        left_v.addLayout(action_row)

        main_h.addWidget(left_w, 5)

        # Right column: Live Sheet Preview (실시간 인쇄 시트 미리보기)
        right_group = QGroupBox("실시간 용지(시트) 미리보기 (Print Sheet Preview)")
        right_v = QVBoxLayout(right_group)

        self._is_dark = getattr(parent, "is_dark_effective", False)
        prev_bg = "#111827" if self._is_dark else "#E2E8F0"
        prev_bd = "#374151" if self._is_dark else "#CBD5E1"
        sum_col = "#93C5FD" if self._is_dark else "#1D4ED8"

        self.preview_lbl = QLabel()
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setMinimumSize(400, 520)
        self.preview_lbl.setStyleSheet(f"background-color: {prev_bg}; border: 1px solid {prev_bd}; border-radius: 6px;")
        right_v.addWidget(self.preview_lbl, 1)

        self.sheet_summary_lbl = QLabel("")
        self.sheet_summary_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sheet_summary_lbl.setStyleSheet(f"color: {sum_col}; font-weight: bold;")
        right_v.addWidget(self.sheet_summary_lbl)

        sheet_nav = QHBoxLayout()
        btn_prev_sh = QPushButton("◀ 이전 용지")
        btn_prev_sh.clicked.connect(lambda: self._step_sheet(-1))
        self.sheet_pos_lbl = QLabel("용지 1 / 1")
        self.sheet_pos_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_next_sh = QPushButton("다음 용지 ▶")
        btn_next_sh.clicked.connect(lambda: self._step_sheet(1))
        sheet_nav.addWidget(btn_prev_sh)
        sheet_nav.addWidget(self.sheet_pos_lbl, 1)
        sheet_nav.addWidget(btn_next_sh)
        right_v.addLayout(sheet_nav)

        main_h.addWidget(right_group, 4)

        self._on_printer_changed()
        self._recompute_and_preview()

    def _on_printer_changed(self):
        pinfo = self.printer_combo.currentData()
        if isinstance(pinfo, QPrinterInfo) and not pinfo.isNull():
            pname = pinfo.printerName()
            self.printer.setPrinterName(pname)

    def _get_winspool_funcs(self):
        winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)
        winspool.OpenPrinterW.argtypes = [
            ctypes.wintypes.LPCWSTR,
            ctypes.POINTER(ctypes.wintypes.HANDLE),
            ctypes.wintypes.LPVOID,
        ]
        winspool.OpenPrinterW.restype = ctypes.wintypes.BOOL
        winspool.DocumentPropertiesW.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.LPCWSTR,
            ctypes.wintypes.LPVOID,
            ctypes.wintypes.LPVOID,
            ctypes.wintypes.DWORD,
        ]
        winspool.DocumentPropertiesW.restype = ctypes.wintypes.LONG
        winspool.ClosePrinter.argtypes = [ctypes.wintypes.HANDLE]
        winspool.ClosePrinter.restype = ctypes.wintypes.BOOL
        return winspool

    def _get_or_init_devmode(self, printer_name: str) -> Optional[ctypes.Array]:
        if not printer_name or sys.platform != "win32":
            return None
        if printer_name in self._printer_devmodes:
            return self._printer_devmodes[printer_name]
        try:
            winspool = self._get_winspool_funcs()
            h_prn = ctypes.wintypes.HANDLE()
            if not winspool.OpenPrinterW(printer_name, ctypes.byref(h_prn), None) or not h_prn.value:
                return None
            try:
                sz = winspool.DocumentPropertiesW(None, h_prn, printer_name, None, None, 0)
                if sz <= ctypes.sizeof(_Win32DevModeHeader):
                    return None
                buf = ctypes.create_string_buffer(sz)
                # DM_OUT_BUFFER = 2
                res = winspool.DocumentPropertiesW(None, h_prn, printer_name, buf, None, 2)
                if res < 0:
                    return None
                self._printer_devmodes[printer_name] = buf
                return buf
            finally:
                winspool.ClosePrinter(h_prn)
        except Exception:
            return None

    def _sync_ui_to_devmode(self, printer_name: str, buf: ctypes.Array):
        try:
            dm = _Win32DevModeHeader.from_buffer(buf)
            # DM_ORIENTATION(0x1) | DM_PAPERSIZE(0x2) | DM_COPIES(0x100) | DM_COLOR(0x800) | DM_DUPLEX(0x1000) | DM_COLLATE(0x8000)
            dm.dmFields |= (0x00000001 | 0x00000002 | 0x00000100 | 0x00000800 | 0x00001000 | 0x00008000)
            dm.dmCopies = max(1, int(self.copies_spin.value()))
            dm.dmCollate = 1 if self.chk_collate.isChecked() else 0
            dm.dmColor = 1 if self.chk_grayscale.isChecked() else 2

            dup_mode = self.duplex_combo.currentData()
            if dup_mode == QPrinter.DuplexMode.DuplexLongSide:
                dm.dmDuplex = 2  # DMDUP_VERTICAL
            elif dup_mode == QPrinter.DuplexMode.DuplexShortSide:
                dm.dmDuplex = 3  # DMDUP_HORIZONTAL
            else:
                dm.dmDuplex = 1  # DMDUP_SIMPLEX

            pid, _ = self.paper_combo.currentData()
            if pid in self._QT_TO_DMPAPER:
                dm.dmPaperSize = self._QT_TO_DMPAPER[pid]

            first_sheet = self.computed_sheets[0] if self.computed_sheets else [0]
            is_land = self._is_sheet_landscape(first_sheet)
            dm.dmOrientation = 2 if is_land else 1

            winspool = self._get_winspool_funcs()
            h_prn = ctypes.wintypes.HANDLE()
            if winspool.OpenPrinterW(printer_name, ctypes.byref(h_prn), None) and h_prn.value:
                try:
                    # DM_IN_BUFFER | DM_OUT_BUFFER = 8 | 2 = 10
                    winspool.DocumentPropertiesW(None, h_prn, printer_name, buf, buf, 10)
                finally:
                    winspool.ClosePrinter(h_prn)
        except Exception:
            pass

    def _sync_devmode_to_ui(self, buf: ctypes.Array):
        try:
            dm = _Win32DevModeHeader.from_buffer(buf)
            if dm.dmCopies >= 1:
                self.copies_spin.setValue(int(dm.dmCopies))
            if dm.dmCollate in (0, 1):
                self.chk_collate.setChecked(dm.dmCollate == 1)
            if dm.dmColor in (1, 2):
                self.chk_grayscale.setChecked(dm.dmColor == 1)
            if dm.dmDuplex == 2:
                idx = self.duplex_combo.findData(QPrinter.DuplexMode.DuplexLongSide)
                if idx >= 0:
                    self.duplex_combo.setCurrentIndex(idx)
            elif dm.dmDuplex == 3:
                idx = self.duplex_combo.findData(QPrinter.DuplexMode.DuplexShortSide)
                if idx >= 0:
                    self.duplex_combo.setCurrentIndex(idx)
            elif dm.dmDuplex == 1:
                idx = self.duplex_combo.findData(QPrinter.DuplexMode.DuplexNone)
                if idx >= 0:
                    self.duplex_combo.setCurrentIndex(idx)

            if dm.dmPaperSize in self._DMPAPER_TO_QT:
                target_pid = self._DMPAPER_TO_QT[dm.dmPaperSize]
                for i in range(self.paper_combo.count()):
                    pid, _ = self.paper_combo.itemData(i)
                    if pid == target_pid:
                        self.paper_combo.setCurrentIndex(i)
                        break

            if dm.dmOrientation == 2:
                self.rb_orient_land.setChecked(True)
            elif dm.dmOrientation == 1:
                self.rb_orient_port.setChecked(True)
        except Exception:
            pass

    def _open_native_printer_properties(self):
        """Directly opens the selected printer driver's native Printing Preferences dialog (인쇄 기본 설정)."""
        self._on_printer_changed()
        printer_name = self.printer.printerName()
        if sys.platform == "win32" and printer_name:
            buf = self._get_or_init_devmode(printer_name)
            if buf is not None:
                self._sync_ui_to_devmode(printer_name, buf)
                try:
                    winspool = self._get_winspool_funcs()
                    h_prn = ctypes.wintypes.HANDLE()
                    if winspool.OpenPrinterW(printer_name, ctypes.byref(h_prn), None) and h_prn.value:
                        try:
                            hwnd = int(self.winId()) if self.winId() else None
                            # DM_IN_PROMPT (4) | DM_IN_BUFFER (8) | DM_OUT_BUFFER (2) = 14
                            res = winspool.DocumentPropertiesW(hwnd, h_prn, printer_name, buf, buf, 14)
                            if res == 1:  # IDOK
                                self._sync_devmode_to_ui(buf)
                                self._recompute_and_preview()
                            return
                        finally:
                            winspool.ClosePrinter(h_prn)
                except Exception:
                    pass
            # Fallback via printui.dll if OpenPrinterW / DocumentPropertiesW failed
            try:
                subprocess.Popen(["rundll32.exe", "printui.dll,PrintUIEntry", "/e", "/n", printer_name])
                return
            except Exception:
                pass

        dlg = QPrintDialog(self.printer, self)
        dlg.setWindowTitle("프린터 드라이버 상세 속성 및 옵션")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if self.printer.copyCount() >= 1:
                self.copies_spin.setValue(self.printer.copyCount())
            self._recompute_and_preview()

    def _on_nup_preset_changed(self):
        data = self.nup_preset_combo.currentData()
        if data == "custom":
            self.nup_cols_spin.setEnabled(True)
            self.nup_rows_spin.setEnabled(True)
        elif isinstance(data, tuple):
            self.nup_cols_spin.setEnabled(False)
            self.nup_rows_spin.setEnabled(False)
            self.nup_cols_spin.blockSignals(True)
            self.nup_rows_spin.blockSignals(True)
            self.nup_cols_spin.setValue(data[0])
            self.nup_rows_spin.setValue(data[1])
            self.nup_cols_spin.blockSignals(False)
            self.nup_rows_spin.blockSignals(False)
        self._recompute_and_preview()

    def _resolve_target_pages(self) -> List[int]:
        if self.rb_pages_all.isChecked():
            pages = list(range(self.total_pages))
        elif self.rb_pages_cur.isChecked():
            pages = [max(0, min(self.total_pages - 1, self.current_page - 1))]
        else:
            groups = parse_page_ranges(self.page_range_edit.text(), self.total_pages)
            pages = [p for grp in groups for p in grp]
            if not pages:
                pages = [0]

        subset = self.subset_combo.currentData()
        if subset == "odd":
            pages = [p for p in pages if (p + 1) % 2 == 1]
        elif subset == "even":
            pages = [p for p in pages if (p + 1) % 2 == 0]

        if self.chk_reverse_pages.isChecked():
            pages = list(reversed(pages))

        return pages if pages else [0]

    def _get_nup_grid(self) -> Tuple[int, int]:
        if self.handling_stack.currentIndex() == 0:
            return (1, 1)
        return (self.nup_cols_spin.value(), self.nup_rows_spin.value())

    def _is_sheet_landscape(self, sheet_pages: List[int]) -> bool:
        if self.rb_orient_port.isChecked():
            return False
        if self.rb_orient_land.isChecked():
            return True
        cols, rows = self._get_nup_grid()
        if cols > rows:
            return True
        if cols == 1 and rows == 1 and sheet_pages:
            r = self.doc[sheet_pages[0]].rect
            return r.width > r.height
        return False

    def _recompute_and_preview(self):
        pages = self._resolve_target_pages()
        cols, rows = self._get_nup_grid()
        per_sheet = max(1, cols * rows)
        self.computed_sheets = [pages[i : i + per_sheet] for i in range(0, len(pages), per_sheet)]
        if not self.computed_sheets:
            self.computed_sheets = [[0]]
        self.current_sheet_idx = max(0, min(len(self.computed_sheets) - 1, self.current_sheet_idx))
        self._update_preview_image()

    def _step_sheet(self, delta: int):
        if not self.computed_sheets:
            return
        self.current_sheet_idx = max(0, min(len(self.computed_sheets) - 1, self.current_sheet_idx + delta))
        self._update_preview_image()

    def _get_cached_page_qimage(self, page_idx: int, dpi_scale: float = 1.6) -> QImage:
        gray = self.chk_grayscale.isChecked()
        toner = self.chk_toner_save.isChecked()
        key = (page_idx, gray, toner, int(dpi_scale * 100))
        if key not in self._page_img_cache:
            page = self.doc[page_idx]
            cs = fitz.csGRAY if gray else fitz.csRGB
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi_scale, dpi_scale), colorspace=cs, alpha=False)
            if gray:
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_Grayscale8).copy()
                qimg = qimg.convertToFormat(QImage.Format.Format_RGB888)
            else:
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
            if toner:
                p = QPainter(qimg)
                p.fillRect(qimg.rect(), QColor(255, 255, 255, 42))
                p.end()
            self._page_img_cache[key] = qimg
        return self._page_img_cache[key]

    def render_sheet_to_painter(
        self,
        painter: QPainter,
        sheet_rect: QRectF,
        sheet_pages: List[int],
        dpi_scale: float = 2.0,
    ):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        painter.fillRect(sheet_rect, QColor(255, 255, 255))

        _, mm_dims = self.paper_combo.currentData()
        is_land = self._is_sheet_landscape(sheet_pages)
        paper_w_mm = mm_dims[1] if is_land else mm_dims[0]
        paper_h_mm = mm_dims[0] if is_land else mm_dims[1]

        margin_x = sheet_rect.width() * (6.0 / paper_w_mm)
        margin_y = sheet_rect.height() * (6.0 / paper_h_mm)
        printable = sheet_rect.adjusted(margin_x, margin_y, -margin_x, -margin_y)

        cols, rows = self._get_nup_grid()

        if self.handling_stack.currentIndex() == 0:
            pno = sheet_pages[0]
            qimg = self._get_cached_page_qimage(pno, dpi_scale=dpi_scale)
            page_pt = self.doc[pno].rect
            page_w_mm = page_pt.width * 25.4 / 72.0
            page_h_mm = page_pt.height * 25.4 / 72.0

            natural_w = sheet_rect.width() * (page_w_mm / paper_w_mm)
            natural_h = sheet_rect.height() * (page_h_mm / paper_h_mm)

            fit_scale = min(printable.width() / max(1.0, natural_w), printable.height() / max(1.0, natural_h))

            if self.rb_scale_fit.isChecked():
                scale = fit_scale
            elif self.rb_scale_actual.isChecked():
                scale = 1.0
            elif self.rb_scale_shrink.isChecked():
                scale = min(1.0, fit_scale)
            else:
                scale = self.custom_scale_spin.value() / 100.0

            draw_w = natural_w * scale
            draw_h = natural_h * scale

            if self.chk_center_page.isChecked():
                dx = sheet_rect.left() + (sheet_rect.width() - draw_w) * 0.5
                dy = sheet_rect.top() + (sheet_rect.height() - draw_h) * 0.5
            else:
                dx = printable.left()
                dy = printable.top()

            painter.setClipRect(sheet_rect)
            painter.drawImage(QRectF(dx, dy, draw_w, draw_h), qimg)

        else:
            order = self.nup_order_combo.currentData()
            gap_x = printable.width() * 0.015
            gap_y = printable.height() * 0.015
            cell_w = (printable.width() - gap_x * max(0, cols - 1)) / cols
            cell_h = (printable.height() - gap_y * max(0, rows - 1)) / rows

            for slot_idx, pno in enumerate(sheet_pages):
                if order == "hor":
                    r_idx = slot_idx // cols
                    c_idx = slot_idx % cols
                elif order == "hor_rev":
                    r_idx = slot_idx // cols
                    c_idx = (cols - 1) - (slot_idx % cols)
                elif order == "ver":
                    c_idx = slot_idx // rows
                    r_idx = slot_idx % rows
                else:
                    c_idx = (cols - 1) - (slot_idx // rows)
                    r_idx = slot_idx % rows

                cell_rect = QRectF(
                    printable.left() + c_idx * (cell_w + gap_x),
                    printable.top() + r_idx * (cell_h + gap_y),
                    cell_w,
                    cell_h,
                )
                qimg = self._get_cached_page_qimage(pno, dpi_scale=dpi_scale)
                iw, ih = qimg.width(), qimg.height()
                sc = min(cell_rect.width() / max(1, iw), cell_rect.height() / max(1, ih)) * 0.96
                dw, dh = iw * sc, ih * sc
                target_r = QRectF(
                    cell_rect.left() + (cell_rect.width() - dw) * 0.5,
                    cell_rect.top() + (cell_rect.height() - dh) * 0.5,
                    dw,
                    dh,
                )
                painter.drawImage(target_r, qimg)

                if self.chk_nup_border.isChecked():
                    painter.setPen(QPen(QColor(120, 120, 120), max(1.0, sheet_rect.width() * 0.0015)))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(target_r)

        painter.restore()

    def _update_preview_image(self):
        if not self.computed_sheets:
            return
        sheet_pages = self.computed_sheets[self.current_sheet_idx]
        _, mm_dims = self.paper_combo.currentData()
        is_land = self._is_sheet_landscape(sheet_pages)
        pw_mm = mm_dims[1] if is_land else mm_dims[0]
        ph_mm = mm_dims[0] if is_land else mm_dims[1]

        avail_w = max(340, self.preview_lbl.width() - 28)
        avail_h = max(440, self.preview_lbl.height() - 28)
        sc = min(avail_w / pw_mm, avail_h / ph_mm)
        pix_w = int(pw_mm * sc)
        pix_h = int(ph_mm * sc)

        canvas_pix = QPixmap(pix_w + 12, pix_h + 12)
        canvas_pix.fill(QColor(17, 24, 39) if self._is_dark else QColor(226, 232, 240))
        p = QPainter(canvas_pix)
        sheet_r = QRectF(4, 4, pix_w, pix_h)
        p.fillRect(sheet_r.translated(4, 4), QColor(0, 0, 0, 110 if self._is_dark else 55))
        self.render_sheet_to_painter(p, sheet_r, sheet_pages, dpi_scale=1.5)
        p.setPen(QPen(QColor(148, 163, 184), 1.0))
        p.drawRect(sheet_r)
        p.end()

        self.preview_lbl.setPixmap(canvas_pix)

        total_sheets = len(self.computed_sheets)
        total_p = sum(len(s) for s in self.computed_sheets)
        cols, rows = self._get_nup_grid()
        orient_str = "가로" if is_land else "세로"
        self.sheet_pos_lbl.setText(f"용지 {self.current_sheet_idx + 1} / {total_sheets}")
        self.sheet_summary_lbl.setText(
            f"출력 요약: 총 {total_p}페이지를 {total_sheets}장 용지에 인쇄 "
            f"(1면당 {cols * rows}페이지, {orient_str} 방향)"
        )

    def _execute_win32_devmode_print(self, printer_name: str, buf: ctypes.Array) -> Optional[Tuple[bool, str]]:
        """Prints sheets via Win32 GDI CreateDCW with the full driver DEVMODEW buffer (including dmDriverExtra)."""
        try:
            self._sync_ui_to_devmode(printer_name, buf)
            gdi32 = ctypes.WinDLL("gdi32.dll", use_last_error=True)
            gdi32.CreateDCW.argtypes = [
                ctypes.wintypes.LPCWSTR,
                ctypes.wintypes.LPCWSTR,
                ctypes.wintypes.LPCWSTR,
                ctypes.wintypes.LPVOID,
            ]
            gdi32.CreateDCW.restype = ctypes.wintypes.HDC
            gdi32.ResetDCW.argtypes = [ctypes.wintypes.HDC, ctypes.wintypes.LPVOID]
            gdi32.ResetDCW.restype = ctypes.wintypes.HDC
            gdi32.DeleteDC.argtypes = [ctypes.wintypes.HDC]
            gdi32.StartDocW.argtypes = [ctypes.wintypes.HDC, ctypes.POINTER(_Win32DocInfoW)]
            gdi32.StartDocW.restype = ctypes.c_int
            gdi32.EndDoc.argtypes = [ctypes.wintypes.HDC]
            gdi32.StartPage.argtypes = [ctypes.wintypes.HDC]
            gdi32.EndPage.argtypes = [ctypes.wintypes.HDC]
            gdi32.GetDeviceCaps.argtypes = [ctypes.wintypes.HDC, ctypes.c_int]
            gdi32.GetDeviceCaps.restype = ctypes.c_int
            gdi32.StretchDIBits.argtypes = [
                ctypes.wintypes.HDC,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.wintypes.LPVOID,
                ctypes.POINTER(_Win32BitmapInfoHeader),
                ctypes.wintypes.UINT,
                ctypes.wintypes.DWORD,
            ]

            hdc = gdi32.CreateDCW("WINSPOOL", printer_name, None, buf)
            if not hdc:
                return None

            try:
                doc_info = _Win32DocInfoW()
                doc_info.cbSize = ctypes.sizeof(_Win32DocInfoW)
                doc_info.lpszDocName = "K-PDF Studio Print Job"
                doc_info.lpszOutput = None
                doc_info.lpszDatatype = None
                doc_info.fwType = 0

                if gdi32.StartDocW(hdc, ctypes.byref(doc_info)) <= 0:
                    return None

                dm = _Win32DevModeHeader.from_buffer(buf)
                for s_idx, sheet_pages in enumerate(self.computed_sheets):
                    is_land = self._is_sheet_landscape(sheet_pages)
                    want_orient = 2 if is_land else 1
                    if dm.dmOrientation != want_orient:
                        dm.dmFields |= 0x00000001
                        dm.dmOrientation = want_orient
                        gdi32.ResetDCW(hdc, buf)

                    if gdi32.StartPage(hdc) <= 0:
                        gdi32.EndDoc(hdc)
                        return None

                    horz_res = max(600, gdi32.GetDeviceCaps(hdc, 8))   # HORZRES
                    vert_res = max(600, gdi32.GetDeviceCaps(hdc, 10))  # VERTRES

                    # Render at 300 DPI onto an offscreen QImage and StretchDIBits to full printer resolution
                    _, mm_dims = self.paper_combo.currentData()
                    pw_mm = mm_dims[1] if is_land else mm_dims[0]
                    ph_mm = mm_dims[0] if is_land else mm_dims[1]
                    img_w = max(800, int(pw_mm * 300.0 / 25.4))
                    img_h = max(800, int(ph_mm * 300.0 / 25.4))

                    sheet_img = QImage(img_w, img_h, QImage.Format.Format_RGB32)
                    sheet_img.fill(QColor(255, 255, 255))
                    qp = QPainter(sheet_img)
                    self.render_sheet_to_painter(qp, QRectF(0, 0, img_w, img_h), sheet_pages, dpi_scale=300.0 / 72.0)
                    qp.end()

                    bmi = _Win32BitmapInfoHeader()
                    bmi.biSize = ctypes.sizeof(_Win32BitmapInfoHeader)
                    bmi.biWidth = img_w
                    bmi.biHeight = -img_h  # Top-down DIB
                    bmi.biPlanes = 1
                    bmi.biBitCount = 32
                    bmi.biCompression = 0  # BI_RGB
                    bmi.biSizeImage = img_w * img_h * 4

                    bits_ptr = int(sheet_img.constBits())
                    # SRCCOPY = 0x00CC0020, DIB_RGB_COLORS = 0
                    gdi32.StretchDIBits(
                        hdc,
                        0, 0, horz_res, vert_res,
                        0, 0, img_w, img_h,
                        ctypes.c_void_p(bits_ptr),
                        ctypes.byref(bmi),
                        0,
                        0x00CC0020,
                    )
                    gdi32.EndPage(hdc)

                gdi32.EndDoc(hdc)
                total_sheets = len(self.computed_sheets)
                return True, f"프린터 '{printer_name}' (드라이버 상세 설정 포함)로 총 {total_sheets}장(시트) 인쇄 전송 완료"
            finally:
                gdi32.DeleteDC(hdc)
        except Exception:
            return None

    def execute_print(self) -> Tuple[bool, str]:
        """Executes the print job on the selected Windows printer with all configured Acrobat options."""
        self._on_printer_changed()
        if not self.computed_sheets:
            return False, "인쇄할 페이지가 없습니다."

        printer_name = self.printer.printerName()
        if sys.platform == "win32" and printer_name and printer_name in self._printer_devmodes:
            res = self._execute_win32_devmode_print(printer_name, self._printer_devmodes[printer_name])
            if res is not None:
                return res

        pid, _ = self.paper_combo.currentData()
        self.printer.setPageSize(QPageSize(pid))
        self.printer.setCopyCount(self.copies_spin.value())
        self.printer.setCollateCopies(self.chk_collate.isChecked())
        self.printer.setDuplex(self.duplex_combo.currentData())
        self.printer.setColorMode(
            QPrinter.ColorMode.GrayScale if self.chk_grayscale.isChecked() else QPrinter.ColorMode.Color
        )

        first_land = self._is_sheet_landscape(self.computed_sheets[0])
        self.printer.setPageOrientation(
            QPageLayout.Orientation.Landscape if first_land else QPageLayout.Orientation.Portrait
        )

        painter = QPainter()
        if not painter.begin(self.printer):
            return False, "선택한 프린터를 시작할 수 없습니다."

        try:
            for s_idx, sheet_pages in enumerate(self.computed_sheets):
                is_land = self._is_sheet_landscape(sheet_pages)
                self.printer.setPageOrientation(
                    QPageLayout.Orientation.Landscape if is_land else QPageLayout.Orientation.Portrait
                )
                if s_idx > 0:
                    self.printer.newPage()

                vp = QRectF(painter.viewport())
                self.render_sheet_to_painter(painter, vp, sheet_pages, dpi_scale=300.0 / 72.0)
        finally:
            painter.end()

        total_sheets = len(self.computed_sheets)
        return True, f"프린터 '{self.printer.printerName()}'로 총 {total_sheets}장(시트) 인쇄 전송 완료"


# =====================================================================
# 5. Shape Quick-Edit Dialog (Opened on Double-Clicking Any Shape)
#    & Merge / Split PDF Dialogs
# =====================================================================

class ShapeQuickEditDialog(QDialog):
    """Popup dialog opened when double-clicking any shape (rect, ellipse, line, arrow, highlight)."""

    def __init__(self, obj: PageEditObject, font_registry: KoreanFontRegistry, parent=None):
        super().__init__(parent)
        kind_names = {
            "rect": "사각형 도형 편집",
            "ellipse": "원 / 타원 도형 편집",
            "line": "직선 도형 편집",
            "arrow": "화살표 도형 편집",
            "highlight": "형광펜 하이라이트 편집",
            "eraser": "🧹 지우개 (화이트아웃) 속성 편집",
        }
        self.setWindowTitle(kind_names.get(obj.kind, "도형 속성 편집"))
        self.resize(430, 380)
        self.obj = obj
        self.font_registry = font_registry
        self.delete_requested = False

        self.stroke_rgb = list(obj.stroke_color)
        self.fill_rgb = list(obj.fill_color)
        self.text_rgb = list(obj.text_color)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Stroke color & width
        if obj.kind not in ("highlight", "eraser"):
            self.btn_stroke = QPushButton("선/테두리 색상 변경")
            self._style_color_btn(self.btn_stroke, self.stroke_rgb)
            self.btn_stroke.clicked.connect(self._pick_stroke)
            form.addRow("선 색상:", self.btn_stroke)

            sw_row = QHBoxLayout()
            self.sw_spin = QDoubleSpinBox()
            self.sw_spin.setRange(0.5, 25.0)
            self.sw_spin.setSingleStep(0.5)
            self.sw_spin.setValue(max(0.5, obj.stroke_width))
            sw_row.addWidget(self.sw_spin, 1)
            b_dn = QPushButton("－")
            b_dn.setFixedWidth(28)
            b_dn.clicked.connect(self.sw_spin.stepDown)
            b_up = QPushButton("＋")
            b_up.setFixedWidth(28)
            b_up.clicked.connect(self.sw_spin.stepUp)
            sw_row.addWidget(b_dn)
            sw_row.addWidget(b_up)
            form.addRow("선 두께 (pt):", sw_row)
        else:
            self.sw_spin = None

        # Fill color & toggle
        if obj.kind in ("rect", "ellipse", "highlight", "eraser"):
            fill_row = QHBoxLayout()
            self.chk_fill = QCheckBox("내부 채우기 사용")
            self.chk_fill.setChecked(obj.use_fill or obj.kind == "highlight")
            if obj.kind == "highlight":
                self.chk_fill.setEnabled(False)
            fill_row.addWidget(self.chk_fill)

            self.btn_fill = QPushButton("채우기 색상 변경")
            self._style_color_btn(self.btn_fill, self.fill_rgb)
            self.btn_fill.clicked.connect(self._pick_fill)
            fill_row.addWidget(self.btn_fill, 1)
            form.addRow("배경 채우기:", fill_row)
        else:
            self.chk_fill = None

        # Opacity
        self.opac_spin = QSpinBox()
        self.opac_spin.setRange(15, 100)
        self.opac_spin.setSuffix(" %")
        self.opac_spin.setValue(int(round(obj.opacity * 100)))
        form.addRow("불투명도:", self.opac_spin)

        # Optional text inside shape (for rect / ellipse)
        if obj.kind in ("rect", "ellipse"):
            self.txt_edit = QLineEdit(obj.text)
            self.txt_edit.setPlaceholderText("도형 내부에 표시할 텍스트 (선택 사항)")
            form.addRow("도형 안 텍스트:", self.txt_edit)

            t_row = QHBoxLayout()
            self.txt_size_spin = QDoubleSpinBox()
            self.txt_size_spin.setRange(6.0, 72.0)
            self.txt_size_spin.setValue(obj.font_size)
            t_row.addWidget(QLabel("크기:"))
            t_row.addWidget(self.txt_size_spin)

            self.btn_txt_col = QPushButton("글자 색상")
            self._style_color_btn(self.btn_txt_col, self.text_rgb)
            self.btn_txt_col.clicked.connect(self._pick_text_col)
            t_row.addWidget(self.btn_txt_col)
            form.addRow("텍스트 스타일:", t_row)
        else:
            self.txt_edit = None

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_del = QPushButton("🗑️ 이 도형 삭제")
        btn_del.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 6px 12px;")
        btn_del.clicked.connect(self._on_delete)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()

        btn_ok = QPushButton("적용 (확인)")
        btn_ok.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 18px;")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _style_color_btn(self, btn: QPushButton, rgb: List[int]):
        r, g, b = rgb
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        fg = "#111827" if lum > 140 else "#FFFFFF"
        btn.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); color: {fg}; font-weight: bold; border: 1px solid #9CA3AF;")

    def _pick_stroke(self):
        c = QColorDialog.getColor(QColor(*self.stroke_rgb), self, "선 색상 선택")
        if c.isValid():
            self.stroke_rgb = [c.red(), c.green(), c.blue()]
            self._style_color_btn(self.btn_stroke, self.stroke_rgb)

    def _pick_fill(self):
        c = QColorDialog.getColor(QColor(*self.fill_rgb), self, "채우기 색상 선택")
        if c.isValid():
            self.fill_rgb = [c.red(), c.green(), c.blue()]
            self._style_color_btn(self.btn_fill, self.fill_rgb)
            if self.chk_fill:
                self.chk_fill.setChecked(True)

    def _pick_text_col(self):
        c = QColorDialog.getColor(QColor(*self.text_rgb), self, "글자 색상 선택")
        if c.isValid():
            self.text_rgb = [c.red(), c.green(), c.blue()]
            self._style_color_btn(self.btn_txt_col, self.text_rgb)

    def _on_delete(self):
        self.delete_requested = True
        self.accept()

    def apply_to_object(self):
        self.obj.stroke_color = list(self.stroke_rgb)
        self.obj.fill_color = list(self.fill_rgb)
        if self.sw_spin is not None:
            self.obj.stroke_width = self.sw_spin.value()
        if self.chk_fill is not None:
            self.obj.use_fill = self.chk_fill.isChecked()
        self.obj.opacity = self.opac_spin.value() / 100.0
        if self.txt_edit is not None:
            self.obj.text = self.txt_edit.text()
            self.obj.font_size = self.txt_size_spin.value()
            self.obj.text_color = list(self.text_rgb)
            self.obj.runs = self.obj.get_effective_runs()


# =====================================================================
# PDF & Image Merge Supporting Constants and Engine
# =====================================================================

MERGE_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".jpe", ".jfif", ".png", ".bmp", ".dib",
    ".webp", ".gif", ".tiff", ".tif", ".ico"
}
MERGEABLE_EXTENSIONS = {".pdf"} | MERGE_IMAGE_EXTENSIONS


def _open_source_document(path: str) -> fitz.Document:
    """PDF 또는 이미지 파일을 열어 결합 가능한 fitz.Document 객체로 반환 (Pillow 하이브리드 폴백 지원)"""
    ext = os.path.splitext(path)[1].lower()
    if ext in MERGE_IMAGE_EXTENSIONS:
        try:
            img_doc = fitz.open(path)
            pdf_bytes = img_doc.convert_to_pdf()
            img_doc.close()
            return fitz.open("pdf", pdf_bytes)
        except Exception:
            # Pillow 하이브리드 폴백
            from PIL import Image
            import io
            img = Image.open(path)
            bio = io.BytesIO()
            if img.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                bg.save(bio, format="PDF", resolution=150.0)
            else:
                img.convert("RGB").save(bio, format="PDF", resolution=150.0)
            bio.seek(0)
            return fitz.open("pdf", bio.read())
    else:
        doc = fitz.open(path)
        if doc.needs_pass:
            ok, doc, _ = authenticate_doc_dialog(doc, path)
            if not ok or doc is None:
                raise ValueError(f"'{os.path.basename(path)}' 문서의 암호 인증이 취소되었습니다.")
        return doc


class MergeFileListWidget(QListWidget):
    files_dropped = pyqtSignal(list)
    reordered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        try:
            if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
                event.acceptProposedAction()
                return
        except Exception:
            pass
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        try:
            if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
                event.acceptProposedAction()
                return
        except Exception:
            pass
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        try:
            if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
                urls = list(event.mimeData().urls())
                valid_files = [
                    u.toLocalFile() for u in urls
                    if hasattr(u, "toLocalFile")
                    and os.path.splitext(u.toLocalFile().lower())[1] in MERGEABLE_EXTENSIONS
                    and os.path.exists(u.toLocalFile())
                ]
                if valid_files:
                    self.files_dropped.emit(valid_files)
                    event.acceptProposedAction()
                    return
        except Exception:
            pass
        super().dropEvent(event)
        self.reordered.emit()


class MergePDFDialog(QDialog):
    def __init__(self, current_pdf_path: Optional[str], parent=None):
        super().__init__(parent)
        self.current_pdf_path = current_pdf_path
        self.setWindowTitle("📑 PDF & 이미지 파일 합치기 (병합)")
        self.resize(740, 580)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Informative Header Banner with Drag-and-Drop Guidance
        banner = QFrame()
        banner.setStyleSheet("background-color: rgba(59, 130, 246, 0.08); border-radius: 8px; border: 1px dashed rgba(59, 130, 246, 0.35);")
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(14, 10, 14, 10)
        lbl_info = QLabel(
            "<b>📥 PDF 및 이미지 파일 추가 & 순서 조정 안내:</b><br>"
            "• 윈도우 파일 탐색기에서 <b>PDF 파일뿐만 아니라 이미지(JPG, PNG, WebP 등) 파일</b>을 <b>이 창 안으로 드래그 앤 드롭</b>하거나 <b>[➕ 파일 추가]</b> 버튼으로 여러 개를 선택할 수 있습니다.<br>"
            "• 이미지 파일은 고화질 단일 PDF 페이지로 자동 변환되어 지정하신 순서대로 결합됩니다.<br>"
            "• 추가된 파일은 마우스로 끌어서 순서를 바꾸거나 <b>[▲ 위로] / [▼ 아래로]</b> 버튼으로 조정할 수 있습니다."
        )
        lbl_info.setWordWrap(True)
        b_layout.addWidget(lbl_info)
        layout.addWidget(banner)

        # File List Widget supporting Drag-Drop from Explorer and Internal Reordering
        self.list_widget = MergeFileListWidget(self)
        self.list_widget.files_dropped.connect(self._add_file_paths)
        self.list_widget.reordered.connect(self._on_list_reordered)
        self.list_widget.currentRowChanged.connect(self._on_row_selected)
        layout.addWidget(self.list_widget, 1)

        # Page Range Config for Selected File
        range_row = QHBoxLayout()
        range_lbl = QLabel("선택한 파일의 페이지 범위:")
        range_lbl.setStyleSheet("font-weight: 500;")
        range_row.addWidget(range_lbl)
        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText("비워두면 전체 페이지 병합 (예: 1-3, 5, 7-9)")
        self.range_edit.textEdited.connect(self._on_range_edited)
        range_row.addWidget(self.range_edit, 1)
        layout.addLayout(range_row)

        # Toolbar Row for File Operations
        btn_row = QHBoxLayout()
        btn_add = QPushButton("➕ 파일 추가 (PDF / 이미지 복수 선택)")
        btn_add.setStyleSheet("font-weight: bold; padding: 5px 12px;")
        btn_add.clicked.connect(self.add_files)
        btn_row.addWidget(btn_add)

        btn_up = QPushButton("▲ 위로")
        btn_up.clicked.connect(lambda: self.move_item(-1))
        btn_row.addWidget(btn_up)

        btn_down = QPushButton("▼ 아래로")
        btn_down.clicked.connect(lambda: self.move_item(1))
        btn_row.addWidget(btn_down)

        btn_del = QPushButton("✕ 선택 제거")
        btn_del.clicked.connect(self.remove_selected)
        btn_row.addWidget(btn_del)

        btn_clear = QPushButton("🗑 전체 비우기")
        btn_clear.clicked.connect(self.clear_all)
        btn_row.addWidget(btn_clear)

        btn_row.addStretch()
        self.lbl_count = QLabel("총 0개 파일")
        self.lbl_count.setStyleSheet("color: #6B7280; font-weight: bold;")
        btn_row.addWidget(self.lbl_count)
        layout.addLayout(btn_row)

        # Merge Mode & Output Path Settings
        mode_group = QGroupBox("병합 저장 설정")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(8)

        if current_pdf_path and os.path.exists(current_pdf_path):
            self.rb_append = QRadioButton(f"현재 열린 문서 뒤에 이어 붙이기 ({os.path.basename(current_pdf_path)})")
            self.rb_new_file = QRadioButton("새 PDF 파일로 병합하여 저장 및 열기")
            self.rb_append.setChecked(True)
            self.rb_append.toggled.connect(self._on_mode_toggled)
            mode_layout.addWidget(self.rb_append)
            mode_layout.addWidget(self.rb_new_file)
        else:
            self.rb_append = None
            self.rb_new_file = QRadioButton("새 PDF 파일로 병합하여 저장 및 열기")
            self.rb_new_file.setChecked(True)
            mode_layout.addWidget(self.rb_new_file)

        # Save Path Row with Auto-Generated "_병합" Filename
        self.save_path_container = QWidget()
        sp_layout = QHBoxLayout(self.save_path_container)
        sp_layout.setContentsMargins(0, 0, 0, 0)
        sp_layout.addWidget(QLabel("저장 경로:"))
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setPlaceholderText("첫 번째 파일이 추가되면 자동으로 [파일명_병합.pdf]로 지정됩니다.")
        sp_layout.addWidget(self.save_path_edit, 1)
        self.btn_browse = QPushButton("📁 위치 변경...")
        self.btn_browse.clicked.connect(self._browse_save_path)
        sp_layout.addWidget(self.btn_browse)
        mode_layout.addWidget(self.save_path_container)

        layout.addWidget(mode_group)

        # If current document exists, add as first item
        if current_pdf_path and os.path.exists(current_pdf_path):
            self._append_file_entry(current_pdf_path)

        self._on_mode_toggled()

        # Bottom Action Row
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        btn_ok = QPushButton("병합 실행")
        btn_ok.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 22px; font-size: 10.5pt; border-radius: 4px;")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("취소")
        btn_cancel.setStyleSheet("padding: 7px 16px; font-size: 10.5pt;")
        btn_cancel.clicked.connect(self.reject)
        bottom_row.addWidget(btn_ok)
        bottom_row.addWidget(btn_cancel)
        layout.addLayout(bottom_row)

        self._update_count_label()

    def dragEnterEvent(self, event):
        try:
            if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
                event.acceptProposedAction()
                return
        except Exception:
            pass
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        try:
            if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
                event.acceptProposedAction()
                return
        except Exception:
            pass
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        try:
            if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
                urls = list(event.mimeData().urls())
                valid_files = [
                    u.toLocalFile() for u in urls
                    if hasattr(u, "toLocalFile")
                    and os.path.splitext(u.toLocalFile().lower())[1] in MERGEABLE_EXTENSIONS
                    and os.path.exists(u.toLocalFile())
                ]
                if valid_files:
                    self._add_file_paths(valid_files)
                    event.acceptProposedAction()
                    return
        except Exception:
            pass
        super().dropEvent(event)

    def _on_mode_toggled(self):
        is_append = bool(self.rb_append and self.rb_append.isChecked())
        self.save_path_container.setEnabled(not is_append)

    @staticmethod
    def _compute_default_merged_path(first_path: str) -> str:
        d = os.path.dirname(os.path.abspath(first_path))
        base = os.path.splitext(os.path.basename(first_path))[0]
        cand = os.path.join(d, f"{base}_병합.pdf")
        if not os.path.exists(cand):
            return cand
        idx = 1
        while True:
            c = os.path.join(d, f"{base}_병합 ({idx}).pdf")
            if not os.path.exists(c):
                return c
            idx += 1

    def _update_default_save_path(self, force: bool = False):
        if self.list_widget.count() == 0:
            self.save_path_edit.setText("")
            return

        cur_text = self.save_path_edit.text().strip()
        first_item = self.list_widget.item(0)
        first_data = first_item.data(Qt.ItemDataRole.UserRole) if first_item else None
        if not first_data or not first_data.get("path"):
            return

        first_p = first_data["path"]
        if not cur_text or force or ("_병합" in os.path.basename(cur_text)):
            self.save_path_edit.setText(self._compute_default_merged_path(first_p))

    def _browse_save_path(self):
        curr = self.save_path_edit.text().strip()
        start_dir = os.path.dirname(curr) if curr else os.path.expanduser("~")
        cand_name = os.path.basename(curr) if curr else "merged_병합문서.pdf"
        p, _ = QFileDialog.getSaveFileName(
            self, "병합된 PDF 파일 저장 위치 선택", os.path.join(start_dir, cand_name), "PDF Files (*.pdf)"
        )
        if p:
            self.save_path_edit.setText(p)

    def _append_file_entry(self, path: str):
        ext = os.path.splitext(path)[1].lower()
        is_image = ext in MERGE_IMAGE_EXTENSIONS
        try:
            if is_image:
                doc = _open_source_document(path)
                cnt = len(doc)
                doc.close()
            else:
                doc = fitz.open(path)
                cnt = len(doc)
                doc.close()
        except Exception:
            cnt = 1 if is_image else 0

        data = {"path": path, "pages": cnt or 1, "range": "", "is_image": is_image}
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, data)
        self.list_widget.addItem(item)
        self._renumber_items()
        self.list_widget.setCurrentItem(item)

    def _add_file_paths(self, paths: List[str]):
        for p in paths:
            self._append_file_entry(p)
        self._update_default_save_path(force=False)
        self._update_count_label()

    def _renumber_items(self):
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            is_image = data.get("is_image", False)
            fname = os.path.basename(data.get("path", ""))
            pages = data.get("pages", 1)
            if is_image:
                icon_tag = "🖼️"
                rng_text = f"이미지 (단일 {pages}p)" if pages == 1 else f"이미지 ({pages}p)"
            else:
                icon_tag = "📄"
                rng = data.get("range", "").strip()
                rng_text = rng if rng else f"전체 (1~{pages}p)"

            item.setText(f"{idx + 1}. {icon_tag} {fname}   [{rng_text}]   —   {data.get('path', '')}")

    def _on_list_reordered(self):
        self._renumber_items()
        self._update_default_save_path(force=False)

    def _on_row_selected(self, row: int):
        if 0 <= row < self.list_widget.count():
            item = self.list_widget.item(row)
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            if data.get("is_image", False):
                self.range_edit.setText("")
                self.range_edit.setPlaceholderText("🖼️ 이미지 파일은 1페이지로 자동 변환되어 삽입됩니다.")
                self.range_edit.setEnabled(False)
            else:
                self.range_edit.setPlaceholderText("비워두면 전체 페이지 병합 (예: 1-3, 5, 7-9)")
                self.range_edit.setText(data.get("range", ""))
                self.range_edit.setEnabled(True)
        else:
            self.range_edit.setText("")
            self.range_edit.setPlaceholderText("비워두면 전체 페이지 병합 (예: 1-3, 5, 7-9)")
            self.range_edit.setEnabled(False)

    def _on_range_edited(self, txt: str):
        row = self.list_widget.currentRow()
        if 0 <= row < self.list_widget.count():
            item = self.list_widget.item(row)
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            if data.get("is_image", False):
                return
            data["range"] = txt
            item.setData(Qt.ItemDataRole.UserRole, data)
            rng = txt.strip() or f"전체 (1~{data.get('pages', 0)}p)"
            fname = os.path.basename(data.get("path", ""))
            item.setText(f"{row + 1}. 📄 {fname}   [{rng}]   —   {data.get('path', '')}")

    def _update_count_label(self):
        cnt = self.list_widget.count()
        tot_pages = 0
        img_cnt = 0
        pdf_cnt = 0
        for i in range(cnt):
            d = self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) or {}
            tot_pages += d.get("pages", 1)
            if d.get("is_image", False):
                img_cnt += 1
            else:
                pdf_cnt += 1
        summary = []
        if pdf_cnt > 0:
            summary.append(f"PDF {pdf_cnt}개")
        if img_cnt > 0:
            summary.append(f"이미지 {img_cnt}개")
        sum_str = f" ({', '.join(summary)})" if summary else ""
        self.lbl_count.setText(f"총 {cnt}개 파일{sum_str} ➔ 총 {tot_pages}페이지 PDF 생성")

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "합칠 파일 선택 (PDF 및 이미지 복수 선택 가능)",
            "",
            "지원하는 모든 파일 (*.pdf *.jpg *.jpeg *.jpe *.jfif *.png *.bmp *.dib *.webp *.gif *.tiff *.tif *.ico);;"
            "PDF 문서 (*.pdf);;"
            "이미지 파일 (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tiff *.tif *.ico);;"
            "모든 파일 (*.*)"
        )
        if paths:
            self._add_file_paths(paths)

    def move_item(self, delta: int):
        row = self.list_widget.currentRow()
        new_row = row + delta
        if 0 <= row < self.list_widget.count() and 0 <= new_row < self.list_widget.count():
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(new_row, item)
            self.list_widget.setCurrentRow(new_row)
            self._renumber_items()
            self._update_default_save_path(force=False)

    def remove_selected(self):
        row = self.list_widget.currentRow()
        if 0 <= row < self.list_widget.count():
            self.list_widget.takeItem(row)
            self._renumber_items()
            self._on_row_selected(self.list_widget.currentRow())
            self._update_default_save_path(force=False)
            self._update_count_label()

    def clear_all(self):
        if self.list_widget.count() == 0:
            return
        reply = QMessageBox.question(
            self, "전체 비우기", "목록의 모든 PDF 파일을 비우시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.list_widget.clear()
            self.range_edit.setText("")
            self.range_edit.setEnabled(False)
            self._update_default_save_path(force=True)
            self._update_count_label()

    def accept(self):
        if self.list_widget.count() == 0:
            QMessageBox.warning(self, "파일 없음", "병합할 PDF 파일을 먼저 추가해 주세요.")
            return

        is_append = bool(self.rb_append and self.rb_append.isChecked())
        if not is_append and self.list_widget.count() < 2:
            reply = QMessageBox.question(
                self,
                "파일 확인",
                "합칠 파일이 1개만 선택되어 있습니다. 그래도 병합 저장을 진행하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if not is_append:
            spath = self.save_path_edit.text().strip()
            if not spath:
                first_p = self.list_widget.item(0).data(Qt.ItemDataRole.UserRole)["path"]
                spath = self._compute_default_merged_path(first_p)
                self.save_path_edit.setText(spath)

        super().accept()

    @property
    def items_data(self) -> List[dict]:
        res = []
        for i in range(self.list_widget.count()):
            d = self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
            if d:
                res.append(d)
        return res


class SplitPDFDialog(QDialog):
    def __init__(self, total_pages: int, current_page_1based: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"PDF 나누기 / 페이지 추출 (총 {total_pages}페이지)")
        self.resize(520, 360)
        self.total_pages = total_pages
        self.current_page = current_page_1based

        layout = QVBoxLayout(self)
        group = QGroupBox("분할 / 추출 방식 선택")
        glayout = QVBoxLayout(group)

        self.rb_range_single = QRadioButton("지정한 페이지 범위만 뽑아서 단일 PDF로 추출 (예: 1-3, 5, 8-10)")
        self.rb_range_multi = QRadioButton("입력한 구간(쉼표 구분)마다 각각 별도의 PDF 파일로 나누기")
        self.rb_every_n = QRadioButton("일정한 페이지 수(N페이지) 단위로 자동 분할 저장")
        self.rb_at_current = QRadioButton(
            f"현재 페이지({current_page_1based}p) 기준으로 앞부분(1~{current_page_1based}p) / 뒷부분으로 2등분"
        )
        self.rb_range_single.setChecked(True)
        if total_pages < 2:
            self.rb_at_current.setEnabled(False)

        for rb in (self.rb_range_single, self.rb_range_multi, self.rb_every_n, self.rb_at_current):
            glayout.addWidget(rb)
        layout.addWidget(group)

        form = QFormLayout()
        self.range_input = QLineEdit(f"{current_page_1based}")
        self.range_input.setPlaceholderText(f"예: 1-3, 5, 7-{total_pages}")
        form.addRow("페이지 범위 입력:", self.range_input)

        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(1, max(1, total_pages))
        self.chunk_spin.setValue(1)
        self.chunk_spin.setSuffix(" 페이지씩 분할")
        form.addRow("자동 분할 단위 (N):", self.chunk_spin)
        layout.addLayout(form)

        layout.addStretch()

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        btn_ok = QPushButton("실행 및 저장 위치 선택")
        btn_ok.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 16px;")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.reject)
        bottom_row.addWidget(btn_ok)
        bottom_row.addWidget(btn_cancel)
        layout.addLayout(bottom_row)


def parse_page_ranges(range_str: str, max_pages: int) -> List[List[int]]:
    groups: List[List[int]] = []
    if not range_str.strip():
        return [list(range(max_pages))]
    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                a_str, b_str = part.split("-", 1)
                a = max(1, min(max_pages, int(a_str.strip())))
                b = max(1, min(max_pages, int(b_str.strip())))
                if a <= b:
                    groups.append(list(range(a - 1, b)))
                else:
                    groups.append(list(range(a - 1, b - 2, -1)))
            else:
                p = max(1, min(max_pages, int(part)))
                groups.append([p - 1])
        except ValueError:
            continue
    return groups


class ExportImagesDialog(QDialog):
    """PDF 문서를 고화질 JPG 또는 PNG 이미지 파일로 일괄 변환/추출하기 위한 대화상자."""
    def __init__(self, total_pages: int, current_page_1based: int, default_dir: str, default_stem: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🖼️ 고화질 이미지로 내보내기 (PDF ➔ JPG/PNG)")
        self.resize(540, 500)
        self.total_pages = total_pages
        self.current_page = current_page_1based
        self.default_dir = default_dir or os.path.expanduser("~")
        self.default_stem = default_stem or "document"

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. 대상 페이지 선택
        range_group = QGroupBox("1. 대상 페이지 선택")
        r_layout = QVBoxLayout(range_group)

        self.rb_all = QRadioButton(f"전체 페이지 (1 ~ {total_pages}페이지)")
        self.rb_current = QRadioButton(f"현재 페이지만 ({current_page_1based}페이지)")
        self.rb_custom = QRadioButton("페이지 범위 직접 지정:")
        self.rb_all.setChecked(True)

        r_layout.addWidget(self.rb_all)
        r_layout.addWidget(self.rb_current)

        custom_row = QHBoxLayout()
        custom_row.addWidget(self.rb_custom)
        self.custom_input = QLineEdit(f"{current_page_1based}")
        self.custom_input.setPlaceholderText(f"예: 1-5, 8, 10-{total_pages}")
        self.custom_input.setEnabled(False)
        custom_row.addWidget(self.custom_input)
        r_layout.addLayout(custom_row)

        self.rb_custom.toggled.connect(self.custom_input.setEnabled)
        layout.addWidget(range_group)

        # 2. 이미지 포맷 및 화질 (DPI / Quality)
        fmt_group = QGroupBox("2. 포맷 및 고화질 해상도(DPI) 설정")
        f_layout = QGridLayout(fmt_group)
        f_layout.setSpacing(8)

        f_layout.addWidget(QLabel("이미지 포맷:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPG (JPEG 이미지 - 고화질 압축)", "PNG (PNG 이미지 - 무손실)"])
        f_layout.addWidget(self.format_combo, 0, 1, 1, 2)

        f_layout.addWidget(QLabel("해상도 (DPI):"), 1, 0)
        self.dpi_combo = QComboBox()
        self.dpi_combo.addItem("300 DPI (인쇄/출판용 고화질 권장 - 기본값)", 300)
        self.dpi_combo.addItem("150 DPI (일반 화면 열람 / 웹용)", 150)
        self.dpi_combo.addItem("200 DPI (표준 문서 보관용)", 200)
        self.dpi_combo.addItem("600 DPI (초고화질 / 미세 선 그래픽)", 600)
        self.dpi_combo.addItem("사용자 직접 입력 (Custom)...", -1)
        f_layout.addWidget(self.dpi_combo, 1, 1)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(50, 1200)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setSuffix(" DPI")
        self.dpi_spin.setEnabled(False)
        f_layout.addWidget(self.dpi_spin, 1, 2)

        def _on_dpi_changed(idx):
            data = self.dpi_combo.currentData()
            if data == -1:
                self.dpi_spin.setEnabled(True)
            else:
                self.dpi_spin.setValue(data)
                self.dpi_spin.setEnabled(False)

        self.dpi_combo.currentIndexChanged.connect(_on_dpi_changed)

        f_layout.addWidget(QLabel("JPG 품질(Quality):"), 2, 0)
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(70, 100)
        self.quality_slider.setValue(100)
        self.quality_label = QLabel("100% (최고 화질)")
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"{v}% (최고 화질)" if v == 100 else f"{v}%")
        )

        q_row = QHBoxLayout()
        q_row.addWidget(self.quality_slider)
        q_row.addWidget(self.quality_label)
        f_layout.addLayout(q_row, 2, 1, 1, 2)

        def _on_format_changed(idx):
            is_jpg = idx == 0
            self.quality_slider.setEnabled(is_jpg)
            self.quality_label.setEnabled(is_jpg)

        self.format_combo.currentIndexChanged.connect(_on_format_changed)
        layout.addWidget(fmt_group)

        # 3. 저장 위치
        out_group = QGroupBox("3. 저장 폴더 설정")
        o_layout = QVBoxLayout(out_group)

        default_out_dir = os.path.join(self.default_dir, f"{self.default_stem}_jpg")
        path_row = QHBoxLayout()
        self.out_dir_edit = QLineEdit(default_out_dir)
        btn_browse = QPushButton("📂 폴더 선택...")
        btn_browse.clicked.connect(self._browse_dir)
        path_row.addWidget(self.out_dir_edit)
        path_row.addWidget(btn_browse)
        o_layout.addLayout(path_row)

        self.cb_open_folder = QCheckBox("변환 완료 후 저장 폴더 탐색기에서 자동으로 열기")
        self.cb_open_folder.setChecked(True)
        o_layout.addWidget(self.cb_open_folder)
        layout.addWidget(out_group)

        # 4. 하단 버튼
        btn_box = QDialogButtonBox()
        self.btn_run = btn_box.addButton("🖼️ 고화질 이미지 내보내기 시작", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_cancel = btn_box.addButton("취소", QDialogButtonBox.ButtonRole.RejectRole)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _browse_dir(self):
        sel = QFileDialog.getExistingDirectory(self, "이미지를 저장할 폴더 선택", self.out_dir_edit.text() or self.default_dir)
        if sel:
            self.out_dir_edit.setText(sel)

    def get_selected_pages(self) -> List[int]:
        if self.rb_all.isChecked():
            return list(range(self.total_pages))
        elif self.rb_current.isChecked():
            return [self.current_page - 1]
        else:
            groups = parse_page_ranges(self.custom_input.text(), self.total_pages)
            pages = []
            for g in groups:
                pages.extend(g)
            return sorted(list(set(p for p in pages if 0 <= p < self.total_pages)))

    def get_dpi(self) -> int:
        if self.dpi_combo.currentData() == -1:
            return self.dpi_spin.value()
        return self.dpi_combo.currentData()

    def get_format(self) -> str:
        return "jpg" if self.format_combo.currentIndex() == 0 else "png"

    def get_quality(self) -> int:
        return self.quality_slider.value()

    def get_out_dir(self) -> str:
        return self.out_dir_edit.text().strip() or self.default_dir

    def should_open_folder(self) -> bool:
        return self.cb_open_folder.isChecked()


# =====================================================================
# 5-1. PowerPoint to High-Quality PDF Dialog (PPTX/PPT ➔ PDF)
# =====================================================================

class PPTXDropListWidget(QListWidget):
    """드래그 앤 드롭 및 다중 선택을 지원하는 파워포인트 파일 목록 위젯"""
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                p = url.toLocalFile()
                if p and p.lower().endswith(('.pptx', '.ppt')):
                    paths.append(os.path.normpath(p))
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            for item in self.selectedItems():
                row = self.row(item)
                self.takeItem(row)
        else:
            super().keyPressEvent(event)


class PPTXToPDFDialog(QDialog):
    """파워포인트(.pptx, .ppt) 문서를 글꼴 손실 없이 원본 그대로 선명한 고화질 PDF로 변환하는 대화상자"""
    def __init__(self, initial_files: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 PPTX ➔ 고화질 PDF 변환 (파워포인트 고해상도 변환기)")
        self.resize(660, 580)
        self.converted_pdfs: List[str] = []

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 상단 안내 배너
        info_banner = QFrame()
        info_banner.setStyleSheet("QFrame { background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; }")
        ib_layout = QHBoxLayout(info_banner)
        ib_layout.setContentsMargins(12, 10, 12, 10)
        lbl_info = QLabel(
            "<b>💡 파워포인트 화면 그대로 고화질 PDF 변환</b><br>"
            "일반 인쇄나 저품질 변환 시 발생하는 <b>글꼴(폰트) 유실 및 이미지 저해상도화(뭉개짐)</b>를 원천 방지합니다.<br>"
            "Office PowerPoint 엔진을 직접 연동하여 원본 슬라이드 품질과 글꼴을 100% 보존합니다."
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #1E3A8A; font-size: 9.5pt;")
        ib_layout.addWidget(lbl_info)
        layout.addWidget(info_banner)

        # 1. 파일 목록 그룹
        file_group = QGroupBox("1. 변환할 파워포인트 문서 (.pptx, .ppt)")
        fg_layout = QVBoxLayout(file_group)

        self.list_widget = PPTXDropListWidget(self)
        self.list_widget.setStyleSheet("QListWidget { border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px; font-size: 9.5pt; }")
        self.list_widget.files_dropped.connect(self._add_files)
        fg_layout.addWidget(self.list_widget)

        btn_bar = QHBoxLayout()
        btn_add = QPushButton("➕ PPTX 파일 추가...")
        btn_add.clicked.connect(self._browse_files)
        btn_remove = QPushButton("➖ 선택 제거")
        btn_remove.clicked.connect(self._remove_selected)
        btn_clear = QPushButton("🗑️ 전체 비우기")
        btn_clear.clicked.connect(self._clear_files)

        btn_bar.addWidget(btn_add)
        btn_bar.addWidget(btn_remove)
        btn_bar.addWidget(btn_clear)
        btn_bar.addStretch()

        self.lbl_file_count = QLabel("파일: 0개")
        self.lbl_file_count.setStyleSheet("color: #64748B; font-weight: bold;")
        btn_bar.addWidget(self.lbl_file_count)
        fg_layout.addLayout(btn_bar)

        layout.addWidget(file_group)

        # 2. 품질 및 엔진 모드 그룹
        mode_group = QGroupBox("2. 고화질 변환 엔진 및 품질 선택")
        mg_layout = QVBoxLayout(mode_group)
        mg_layout.setSpacing(8)

        self.rb_vector = QRadioButton("🖨️ 인쇄용 최고품질(Print Intent) 벡터 PDF (기본 권장, 텍스트 검색/선택 가능)")
        self.rb_vector.setChecked(True)
        self.rb_vector.setStyleSheet("font-weight: bold;")
        mg_layout.addWidget(self.rb_vector)

        lbl_vector_desc = QLabel(
            "   • 파워포인트 내장 인쇄용 최고품질(ppFixedFormatIntentPrint) 및 폰트 서브셋 임베딩 강제 적용<br>"
            "   • 텍스트 검색, 드래그 복사(Ctrl+C) 완벽 유지 및 슬림한 용량 (ISO 19005-1 제한을 풀어 폰트 왜곡 방지)"
        )
        lbl_vector_desc.setStyleSheet("color: #64748B; font-size: 8.5pt; margin-bottom: 4px;")
        mg_layout.addWidget(lbl_vector_desc)

        self.rb_raster = QRadioButton("🖼️ 300 DPI / 4K 무손실 슬라이드 이미지 PDF (화면 100% 박제, 폰트 유실률 0%)")
        self.rb_raster.setStyleSheet("font-weight: bold;")
        mg_layout.addWidget(self.rb_raster)

        lbl_raster_desc = QLabel(
            "   • 슬라이드를 4K(너비 3840px)/300DPI급 무손실 PNG로 렌더링한 후 초고화질 PDF로 결합<br>"
            "   • 특수 캘리그라피, 미설치 폰트, 자간, 투명도 효과가 파워포인트 화면 그대로 1픽셀 오차 없이 100% 보존"
        )
        lbl_raster_desc.setStyleSheet("color: #64748B; font-size: 8.5pt;")
        mg_layout.addWidget(lbl_raster_desc)

        layout.addWidget(mode_group)

        # 3. 저장 및 완료 후 옵션
        opt_group = QGroupBox("3. 저장 위치 및 변환 후 작업")
        og_layout = QVBoxLayout(opt_group)
        og_layout.setSpacing(6)

        self.rb_save_same = QRadioButton("원본 파워포인트 파일과 동일한 폴더에 저장 (<파일명>.pdf)")
        self.rb_save_same.setChecked(True)
        og_layout.addWidget(self.rb_save_same)

        custom_row = QHBoxLayout()
        self.rb_save_custom = QRadioButton("지정 폴더에 저장:")
        custom_row.addWidget(self.rb_save_custom)
        self.edit_custom_dir = QLineEdit()
        self.edit_custom_dir.setEnabled(False)
        self.edit_custom_dir.setPlaceholderText("저장할 폴더를 선택하세요...")
        custom_row.addWidget(self.edit_custom_dir)
        self.btn_browse_dir = QPushButton("찾아보기...")
        self.btn_browse_dir.setEnabled(False)
        self.btn_browse_dir.clicked.connect(self._browse_custom_dir)
        custom_row.addWidget(self.btn_browse_dir)
        og_layout.addLayout(custom_row)

        self.rb_save_custom.toggled.connect(self.edit_custom_dir.setEnabled)
        self.rb_save_custom.toggled.connect(self.btn_browse_dir.setEnabled)

        cb_row = QHBoxLayout()
        self.cb_open_tab = QCheckBox("변환 완료 후 K-PDF Studio 새 탭으로 즉시 열기")
        self.cb_open_tab.setChecked(True)
        cb_row.addWidget(self.cb_open_tab)

        self.cb_open_folder = QCheckBox("저장 폴더 열기")
        self.cb_open_folder.setChecked(True)
        cb_row.addWidget(self.cb_open_folder)
        og_layout.addLayout(cb_row)

        layout.addWidget(opt_group)

        # 하단 버튼
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QPushButton("닫기")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_convert = QPushButton("📊 고화질 PDF로 변환 시작")
        self.btn_convert.setFixedHeight(36)
        self.btn_convert.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                padding-left: 18px;
                padding-right: 18px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:disabled {
                background-color: #94A3B8;
            }
        """)
        self.btn_convert.clicked.connect(self._start_conversion)
        btn_box.addWidget(self.btn_convert)

        layout.addLayout(btn_box)

        if initial_files:
            self._add_files(initial_files)
        self._update_ui_state()

    def _browse_files(self):
        fpaths, _ = QFileDialog.getOpenFileNames(
            self, "변환할 파워포인트 문서 선택", "", "PowerPoint 프레젠테이션 (*.pptx *.ppt);;모든 파일 (*.*)"
        )
        if fpaths:
            self._add_files(fpaths)

    def _add_files(self, paths: List[str]):
        existing = {self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list_widget.count())}
        for p in paths:
            norm = os.path.normpath(p)
            if norm not in existing and os.path.isfile(norm):
                item = QListWidgetItem(f"📊  {os.path.basename(norm)}")
                item.setToolTip(norm)
                item.setData(Qt.ItemDataRole.UserRole, norm)
                self.list_widget.addItem(item)
                existing.add(norm)
        self._update_ui_state()

    def _remove_selected(self):
        for item in self.list_widget.selectedItems():
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)
        self._update_ui_state()

    def _clear_files(self):
        self.list_widget.clear()
        self._update_ui_state()

    def _update_ui_state(self):
        cnt = self.list_widget.count()
        self.lbl_file_count.setText(f"파일: {cnt}개")
        self.btn_convert.setEnabled(cnt > 0)

    def _browse_custom_dir(self):
        sel = QFileDialog.getExistingDirectory(self, "PDF를 저장할 폴더 선택", self.edit_custom_dir.text() or os.path.expanduser("~"))
        if sel:
            self.edit_custom_dir.setText(os.path.normpath(sel))

    def _start_conversion(self):
        cnt = self.list_widget.count()
        if cnt == 0:
            QMessageBox.warning(self, "알림", "변환할 파워포인트 파일을 추가해주세요.")
            return

        try:
            import win32com.client
        except ImportError:
            QMessageBox.critical(
                self, "라이브러리 필요",
                "파워포인트 변환을 위해 pywin32 라이브러리가 필요합니다.\n\n"
                "명령 프롬프트에서 아래 명령을 실행해주세요:\npip install pywin32"
            )
            return

        files = [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(cnt)]
        use_raster = self.rb_raster.isChecked()
        save_same = self.rb_save_same.isChecked()
        custom_dir = self.edit_custom_dir.text().strip()

        if not save_same and not custom_dir:
            QMessageBox.warning(self, "알림", "저장할 대상 폴더를 선택해주세요.")
            return
        if not save_same and not os.path.isdir(custom_dir):
            try:
                os.makedirs(custom_dir, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "폴더 오류", f"저장 폴더를 생성할 수 없습니다:\n{e}")
                return

        prog = QProgressDialog("PowerPoint 엔진을 초기화하는 중입니다...", "중단", 0, cnt, self)
        prog.setWindowTitle("PPTX ➔ 고화질 PDF 변환 진행 중")
        prog.setWindowModality(Qt.WindowModality.WindowModal)
        prog.setMinimumDuration(100)
        prog.show()
        QCoreApplication.processEvents()

        ppt_app = None
        converted: List[str] = []
        errors: List[str] = []

        try:
            ppt_app = win32com.client.Dispatch("PowerPoint.Application")
        except Exception as e:
            prog.close()
            QMessageBox.critical(
                self, "파워포인트 실행 오류",
                f"Microsoft PowerPoint 프로그램을 실행할 수 없습니다:\n{e}\n\n"
                "PC에 Microsoft PowerPoint가 정상 설치되어 있는지 확인해주세요."
            )
            return

        last_target_dir = ""
        try:
            for idx, fpath in enumerate(files):
                if prog.wasCanceled():
                    break
                fname = os.path.basename(fpath)
                prog.setLabelText(f"[{idx + 1}/{cnt}] 변환 중: {fname}...")
                prog.setValue(idx)
                QCoreApplication.processEvents()

                stem = os.path.splitext(fname)[0]
                target_dir = os.path.dirname(fpath) if save_same else custom_dir
                last_target_dir = target_dir
                out_pdf = os.path.join(target_dir, f"{stem}.pdf")

                dup_idx = 1
                while os.path.exists(out_pdf):
                    try:
                        with open(out_pdf, "a+b"):
                            pass
                        break
                    except PermissionError:
                        out_pdf = os.path.join(target_dir, f"{stem} ({dup_idx}).pdf")
                        dup_idx += 1

                pres = None
                try:
                    pres = ppt_app.Presentations.Open(
                        os.path.abspath(fpath),
                        ReadOnly=True,
                        Untitled=False,
                        WithWindow=False
                    )

                    if not use_raster:
                        # 모드 1: 인쇄용 최고품질 벡터 PDF 변환 (ppFixedFormatIntentPrint + ISO19005-1 해제)
                        pres.ExportAsFixedFormat(
                            Path=os.path.abspath(out_pdf),
                            FixedFormatType=2,      # ppFixedFormatTypePDF
                            Intent=2,               # ppFixedFormatIntentPrint (최고 인쇄 품질)
                            FrameSlides=False,
                            HandoutOrder=1,
                            OutputType=1,           # ppPrintOutputSlides
                            PrintHiddenSlides=False,
                            PrintRange=None,
                            RangeType=1,            # ppPrintAll
                            SlideShowName="",
                            IncludeDocProperties=True,
                            KeepIRMSettings=True,
                            DocStructureTags=True,
                            BitmapMissingFonts=True,
                            UseISO19005_1=False     # PDF/A 제한 해제 -> 특수 글꼴 온전 보존
                        )
                    else:
                        # 모드 2: 300 DPI 무손실 슬라이드 이미지 PDF (화면 100% 박제)
                        slide_w = float(pres.PageSetup.SlideWidth)
                        slide_h = float(pres.PageSetup.SlideHeight)
                        scale_w = 3840
                        scale_h = max(100, int(3840.0 * (slide_h / max(1.0, slide_w))))

                        slide_count = pres.Slides.Count
                        temp_dir = tempfile.mkdtemp(prefix="kpdf_pptx_")
                        img_paths = []
                        try:
                            for s_idx in range(1, slide_count + 1):
                                if prog.wasCanceled():
                                    break
                                prog.setLabelText(f"{fname}: 슬라이드 {s_idx}/{slide_count} 초고해상도 렌더링 중...")
                                QCoreApplication.processEvents()
                                img_p = os.path.join(temp_dir, f"slide_{s_idx:03d}.png")
                                pres.Slides(s_idx).Export(img_p, "PNG", scale_w, scale_h)
                                img_paths.append(img_p)

                            if not prog.wasCanceled() and img_paths:
                                doc = fitz.open()
                                for ip in img_paths:
                                    if os.path.exists(ip):
                                        img_doc = fitz.open(ip)
                                        pdf_bytes = img_doc.convert_to_pdf()
                                        img_doc.close()
                                        src = fitz.open("pdf", pdf_bytes)
                                        doc.insert_pdf(src)
                                        src.close()
                                doc.save(os.path.abspath(out_pdf), garbage=2, deflate=True)
                                doc.close()
                        finally:
                            shutil.rmtree(temp_dir, ignore_errors=True)

                    converted.append(os.path.abspath(out_pdf))
                except Exception as file_err:
                    errors.append(f"• {fname}: {file_err}")
                finally:
                    if pres:
                        try:
                            pres.Close()
                        except Exception:
                            pass
            prog.setValue(cnt)
        finally:
            prog.close()
            if ppt_app:
                try:
                    ppt_app.Quit()
                except Exception:
                    pass

        self.converted_pdfs = converted

        if converted:
            summary = (
                f"총 {len(converted)}개 파워포인트 문서가 고화질 PDF로 성공적으로 변환되었습니다!\n\n"
                f"📂 저장 경로: {last_target_dir}\n"
                f"⚙️ 엔진: {'인쇄용 최고화질 벡터 PDF' if not use_raster else '300 DPI 무손실 슬라이드 이미지 PDF'}"
            )
            if errors:
                summary += f"\n\n⚠️ 일부 파일 실패 ({len(errors)}개):\n" + "\n".join(errors[:5])
            QMessageBox.information(self, "변환 완료", summary)

            if self.cb_open_folder.isChecked() and last_target_dir and os.path.isdir(last_target_dir):
                try:
                    os.startfile(last_target_dir)
                except Exception:
                    pass

            self.accept()
        else:
            if errors:
                QMessageBox.critical(self, "변환 실패", "변환 중 오류가 발생했습니다:\n\n" + "\n".join(errors))
            elif prog.wasCanceled():
                QMessageBox.information(self, "변환 취소", "사용자에 의해 변환이 취소되었습니다.")


# =====================================================================
# 6. Acrobat-Style Document Properties Dialog (REA avDocPropertiesCmdTitle '문서 속성', Ctrl+D)
# =====================================================================

def format_pdf_date(pdf_date_str: str) -> str:
    """Formats PDF internal date strings (e.g. D:20261016143847+09'00') into human-readable format."""
    if not pdf_date_str:
        return "지정되지 않음"
    s = pdf_date_str.strip()
    if s.startswith("D:"):
        s = s[2:]
    try:
        if len(s) >= 14:
            yyyy, mm, dd = s[0:4], s[4:6], s[6:8]
            hh, mi, ss = s[8:10], s[10:12], s[12:14]
            res = f"{yyyy}-{mm}-{dd} {hh}:{mi}:{ss}"
            if len(s) > 14:
                tz = s[14:].replace("'", ":").rstrip(":")
                res += f" ({tz})"
            return res
        elif len(s) >= 8:
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    except Exception:
        pass
    return pdf_date_str


def get_standard_paper_name(w_pt: float, h_pt: float) -> str:
    """Infers standard paper name from page width and height in points."""
    w, h = min(w_pt, h_pt), max(w_pt, h_pt)
    if abs(w - 595.28) < 6 and abs(h - 841.89) < 6:
        return "A4"
    elif abs(w - 841.89) < 6 and abs(h - 1190.55) < 6:
        return "A3"
    elif abs(w - 419.53) < 6 and abs(h - 595.28) < 6:
        return "A5"
    elif abs(w - 612.0) < 6 and abs(h - 792.0) < 6:
        return "Letter"
    elif abs(w - 612.0) < 6 and abs(h - 1008.0) < 6:
        return "Legal"
    elif abs(w - 516.0) < 6 and abs(h - 729.0) < 6:
        return "B5 (JIS)"
    return "사용자 정의"


class DocumentPropertiesDialog(QDialog):
    """
    Adobe Acrobat DC-equivalent Document Properties Dialog (Ctrl+D).
    Exposes 3 comprehensive tabs:
    1. '설명' (Description): File metadata (Title, Author, Subject, Keywords - editable),
       creation/modification dates, creator application, PDF producer, file location/size,
       page count, page dimensions in mm and pt with standard paper name, and linearized flag.
    2. '보안' (Security): Security method and granular permissions/restrictions summary.
    3. '글꼴' (Fonts): All fonts used throughout the document pages, font type, encoding, and embedded status.
    """
    def __init__(self, doc: fitz.Document, file_path: Optional[str], current_page_idx: int = 0, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.file_path = file_path
        self.current_page_idx = max(0, min(len(doc) - 1, current_page_idx)) if doc else 0
        self.setWindowTitle("문서 속성 (Document Properties)")
        self.resize(680, 560)
        self.setMinimumSize(580, 480)

        self.metadata_changed = False
        self.new_metadata = {}

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Tab 1: 설명 (Description)
        tab_desc = self._build_description_tab()
        self.tab_widget.addTab(tab_desc, "📑 설명 (Description)")

        # Tab 2: 보안 (Security)
        tab_sec = self._build_security_tab()
        self.tab_widget.addTab(tab_sec, "🔒 보안 (Security)")

        # Tab 3: 글꼴 (Fonts)
        tab_fonts = self._build_fonts_tab()
        self.tab_widget.addTab(tab_fonts, "🔤 글꼴 (Fonts)")

        # Bottom Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)

        btn_ok = QPushButton("확인 (저장)")
        btn_ok.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; min-width: 90px; padding: 6px 16px;")
        btn_ok.clicked.connect(self._on_accept)
        btn_box.addWidget(btn_ok)

        btn_cancel = QPushButton("취소")
        btn_cancel.setStyleSheet("min-width: 80px; padding: 6px 16px;")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        main_layout.addLayout(btn_box)

    def _build_description_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        meta = self.doc.metadata if self.doc else {}

        # 1. Description Group (Editable)
        grp_desc = QGroupBox("설명 (Description)")
        form_desc = QFormLayout(grp_desc)
        form_desc.setContentsMargins(12, 12, 12, 12)
        form_desc.setSpacing(8)

        self.edit_title = QLineEdit(meta.get("title") or "")
        self.edit_title.setPlaceholderText("문서 제목을 입력하세요")
        form_desc.addRow("제목(T):", self.edit_title)

        self.edit_author = QLineEdit(meta.get("author") or "")
        self.edit_author.setPlaceholderText("작성자 이름을 입력하세요")
        form_desc.addRow("작성자(A):", self.edit_author)

        self.edit_subject = QLineEdit(meta.get("subject") or "")
        self.edit_subject.setPlaceholderText("문서 주제/설명을 입력하세요")
        form_desc.addRow("주제(S):", self.edit_subject)

        self.edit_keywords = QLineEdit(meta.get("keywords") or "")
        self.edit_keywords.setPlaceholderText("키워드 (쉼표로 구분)")
        form_desc.addRow("키워드(K):", self.edit_keywords)

        layout.addWidget(grp_desc)

        # 2. Advanced / Origin Group
        grp_adv = QGroupBox("고급 정보 (Origin & Application)")
        form_adv = QFormLayout(grp_adv)
        form_adv.setContentsMargins(12, 12, 12, 12)
        form_adv.setSpacing(6)

        lbl_creator = QLabel(meta.get("creator") or "지정되지 않음")
        form_adv.addRow("만든 이 (응용 프로그램):", lbl_creator)

        lbl_producer = QLabel(meta.get("producer") or "PyMuPDF / K-PDF Studio")
        form_adv.addRow("변환기 (PDF Producer):", lbl_producer)

        lbl_created = QLabel(format_pdf_date(meta.get("creationDate") or ""))
        form_adv.addRow("만든 날짜:", lbl_created)

        lbl_modified = QLabel(format_pdf_date(meta.get("modDate") or ""))
        form_adv.addRow("수정한 날짜:", lbl_modified)

        pdf_ver = meta.get("format") or "PDF 1.7"
        lbl_version = QLabel(f"{pdf_ver}")
        form_adv.addRow("PDF 버전:", lbl_version)

        layout.addWidget(grp_adv)

        # 3. File Summary Group
        grp_file = QGroupBox("파일 정보 (File Summary)")
        form_file = QFormLayout(grp_file)
        form_file.setContentsMargins(12, 12, 12, 12)
        form_file.setSpacing(6)

        fn = os.path.basename(self.file_path) if self.file_path else "제목 없는 문서"
        lbl_fname = QLabel(fn)
        lbl_fname.setStyleSheet("font-weight: bold;")
        form_file.addRow("파일 이름:", lbl_fname)

        loc = os.path.dirname(os.path.abspath(self.file_path)) if self.file_path else "메모리 임시 문서"
        lbl_loc = QLabel(loc)
        lbl_loc.setWordWrap(True)
        form_file.addRow("파일 위치:", lbl_loc)

        if self.file_path and os.path.exists(self.file_path):
            sz_bytes = os.path.getsize(self.file_path)
            if sz_bytes >= 1024 * 1024:
                sz_str = f"{sz_bytes / (1024 * 1024):.2f} MB ({sz_bytes:,} 바이트)"
            else:
                sz_str = f"{sz_bytes / 1024:.1f} KB ({sz_bytes:,} 바이트)"
        else:
            sz_str = "저장되지 않음 (신규 문서)"
        lbl_fsize = QLabel(sz_str)
        form_file.addRow("파일 크기:", lbl_fsize)

        pcount = len(self.doc) if self.doc else 0
        lbl_pcount = QLabel(f"총 {pcount} 페이지")
        form_file.addRow("페이지 수:", lbl_pcount)

        if self.doc and pcount > 0:
            cur_page = self.doc[self.current_page_idx]
            pw_pt = cur_page.rect.width
            ph_pt = cur_page.rect.height
            pw_mm = pw_pt * 25.4 / 72.0
            ph_mm = ph_pt * 25.4 / 72.0
            paper_name = get_standard_paper_name(pw_pt, ph_pt)
            size_str = f"{pw_mm:.1f} × {ph_mm:.1f} mm ({paper_name}) / {pw_pt:.1f} × {ph_pt:.1f} pt"
        else:
            size_str = "알 수 없음"
        lbl_psize = QLabel(size_str)
        form_file.addRow(f"페이지 크기 ({self.current_page_idx + 1}p 기준):", lbl_psize)

        layout.addWidget(grp_file)
        layout.addStretch(1)
        return widget

    def _build_security_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Security Method Group
        grp_sec = QGroupBox("문서 보안 (Document Security)")
        form_sec = QFormLayout(grp_sec)
        form_sec.setContentsMargins(12, 12, 12, 12)
        form_sec.setSpacing(8)

        is_enc = bool(self.doc and self.doc.is_encrypted)
        lbl_method = QLabel("암호 보안 (암호화됨)" if is_enc else "보안 없음 (제한 없이 모든 작업 가능)")
        lbl_method.setStyleSheet("font-weight: bold; color: " + ("#EF4444;" if is_enc else "#10B981;"))
        form_sec.addRow("보안 방법:", lbl_method)

        layout.addWidget(grp_sec)

        # 2. Document Restrictions Summary
        grp_perm = QGroupBox("문서 제한 사항 요약 (Document Restrictions Summary)")
        form_perm = QFormLayout(grp_perm)
        form_perm.setContentsMargins(12, 12, 12, 12)
        form_perm.setSpacing(6)

        allowed_txt = "허용됨" if not is_enc else "허용 안 됨"
        color_str = "#10B981" if not is_enc else "#EF4444"

        perms = [
            ("인쇄 (Printing):", "허용됨 (고해상도)"),
            ("문서 내용 복사 (Content Copying):", allowed_txt),
            ("문서 변경 (Changing the Document):", allowed_txt),
            ("접근성을 위한 내용 추출 (Accessibility):", "허용됨"),
            ("페이지 추출 (Page Extraction):", allowed_txt),
            ("주석 및 메모 작성 (Commenting):", allowed_txt),
            ("양식 필드 채우기 (Filling of form fields):", allowed_txt),
            ("문서 서명 (Signing):", allowed_txt),
            ("문서 어셈블리 (Document Assembly):", allowed_txt),
        ]
        for name, val in perms:
            lbl = QLabel(val)
            lbl.setStyleSheet(f"color: {color_str}; font-weight: bold;")
            form_perm.addRow(name, lbl)

        layout.addWidget(grp_perm)
        layout.addStretch(1)
        return widget

    def _build_fonts_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Extract all fonts across document pages
        fonts_dict = {}
        if self.doc:
            for pno in range(len(self.doc)):
                try:
                    for f in self.doc[pno].get_fonts():
                        xref, ext, ftype, basefont, name, encoding = f[:6]
                        if basefont not in fonts_dict:
                            clean_name = basefont
                            is_subset = False
                            if "+" in clean_name and len(clean_name.split("+")[0]) == 6:
                                prefix, clean_name = clean_name.split("+", 1)
                                is_subset = True
                            fonts_dict[basefont] = {
                                "name": clean_name,
                                "raw_name": basefont,
                                "type": ftype or "TrueType",
                                "encoding": encoding or "Identity-H",
                                "embedded": "포함된 서브셋" if is_subset else ("완전 포함됨" if ext else "시스템 글꼴"),
                            }
                except Exception:
                    pass

        fonts_list = list(fonts_dict.values())

        lbl_summary = QLabel(f"이 문서에 사용된 글꼴: 총 {len(fonts_list)}개")
        lbl_summary.setStyleSheet("font-weight: bold; color: #60A5FA; font-size: 10.5pt;")
        layout.addWidget(lbl_summary)

        tbl = QTableWidget(len(fonts_list), 4)
        tbl.setHorizontalHeaderLabels(["글꼴 이름 (Font Name)", "유형 (Type)", "인코딩 (Encoding)", "포함 상태 (Embedded Status)"])
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tbl.verticalHeader().setVisible(False)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        for row, f in enumerate(fonts_list):
            it_name = QTableWidgetItem(f["name"])
            it_name.setToolTip(f["raw_name"])
            it_type = QTableWidgetItem(f["type"])
            it_enc = QTableWidgetItem(f["encoding"])
            it_emb = QTableWidgetItem(f["embedded"])
            tbl.setItem(row, 0, it_name)
            tbl.setItem(row, 1, it_type)
            tbl.setItem(row, 2, it_enc)
            tbl.setItem(row, 3, it_emb)

        layout.addWidget(tbl, 1)
        return widget

    def _on_accept(self):
        if not self.doc:
            self.accept()
            return
        meta = self.doc.metadata or {}
        new_title = self.edit_title.text().strip()
        new_author = self.edit_author.text().strip()
        new_subject = self.edit_subject.text().strip()
        new_keywords = self.edit_keywords.text().strip()

        changed = (
            new_title != (meta.get("title") or "") or
            new_author != (meta.get("author") or "") or
            new_subject != (meta.get("subject") or "") or
            new_keywords != (meta.get("keywords") or "")
        )
        if changed:
            self.metadata_changed = True
            updated = dict(meta)
            updated["title"] = new_title
            updated["author"] = new_author
            updated["subject"] = new_subject
            updated["keywords"] = new_keywords
            self.new_metadata = updated
        self.accept()


# ---------------------------------------------------------------------
# F2 File Rename Dialog (nomacs style)
# ---------------------------------------------------------------------
class KPDFRenameDialog(QDialog):
    """
    KPDFStudio 파일 보기 모드에서 F2 키로 호출되는 파일명 변경 팝업창 (nomacs 스타일).
    - 확장자를 제외한 파일명 몸통(stem)이 기본 선택되어 즉시 새 이름 타이핑 가능
    - Windows 파일명 금지 문자(\\ / : * ? " < > |) 및 중복 방어
    - 확장자 생략 시 .pdf 자동 보전 (사용자 실수 방어)
    """
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.p = Path(file_path)
        self.old_name = self.p.name
        self.new_name = self.old_name

        self.setWindowTitle("이름 바꾸기")
        self.setFixedSize(430, 160)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # 상단 안내 라벨
        lbl_info = QLabel("새 파일 이름을 입력하세요:", self)
        lbl_info.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl_info)

        # 입력 라인에디트
        self.edit = QLineEdit(self.old_name, self)
        self.edit.setStyleSheet("padding: 7px 10px; font-size: 13px; border-radius: 4px;")
        layout.addWidget(self.edit)

        # 확장자 제외 몸통(stem) 자동 블록 선택 (Windows & nomacs 표준 UX)
        stem = self.p.stem
        self.edit.setFocus()
        if stem:
            self.edit.setSelection(0, len(stem))
        else:
            self.edit.selectAll()

        # 하단 버튼 (취소, 확인)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("취소", self)
        self.btn_cancel.setFixedWidth(85)
        self.btn_cancel.setStyleSheet("padding: 6px;")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("확인", self)
        self.btn_ok.setFixedWidth(85)
        self.btn_ok.setStyleSheet("padding: 6px; font-weight: bold;")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self._on_ok_clicked)
        btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)

    def _on_ok_clicked(self):
        name = self.edit.text().strip()
        if not name:
            QMessageBox.warning(self, "입력 오류", "파일 이름을 입력해주세요.")
            self.edit.setFocus()
            return

        # 윈도우 파일명 금지 문자 검사
        invalid_chars = r'\/:*?"<>|'
        found_invalid = [c for c in name if c in invalid_chars]
        if found_invalid:
            chars_str = " ".join(sorted(set(found_invalid)))
            QMessageBox.warning(
                self,
                "파일명 오류",
                f"파일명에는 다음 문자를 사용할 수 없습니다:\n\\ / : * ? \" < > |\n\n(입력된 금지 문자: {chars_str})"
            )
            self.edit.setFocus()
            return

        # 확장자가 없고 기존 파일에 확장자가 있는 경우 자동 보전 (사용자 실수 방어)
        if "." not in name and self.p.suffix:
            name = name + self.p.suffix

        if name == self.old_name:
            # 변경사항 없음 -> 조용히 닫기
            self.reject()
            return

        parent_dir = self.p.parent
        target_path = parent_dir / name

        # 동일 폴더 내 중복 파일 방어 (윈도우 대소문자만 변경하는 경우는 허용)
        if target_path.exists() and target_path.resolve() != self.p.resolve():
            QMessageBox.warning(
                self,
                "중복 오류",
                f"같은 위치에 이미 동일한 이름의 파일이 존재합니다:\n'{name}'\n\n다른 파일 이름을 입력해주세요."
            )
            self.edit.setFocus()
            return

        self.new_name = name
        self.accept()

    def get_new_name(self) -> str:
        return self.new_name


# ---------------------------------------------------------------------
# 암호로 보호된 PDF 열기 대화상자 & 힌트 자동 감지
# ---------------------------------------------------------------------
def extract_pdf_password_hint(file_path: str) -> Optional[str]:
    """파일명 등에서 암호 힌트를 자동 감지하여 추출 (예: '문서열기암호：주민번호 앞 6자리' -> '주민번호 앞 6자리')"""
    if not file_path:
        return None
    fname = os.path.basename(file_path)
    # 1. 괄호 안에 명시된 패턴: (문서열기암호：주민번호 앞 6자리), [비밀번호: ...] 등
    m = re.search(
        r'[\(\[\{<]\s*(?:문서\s*열기\s*암호|문서\s*암호|열기\s*암호|암호|비밀번호|패스워드|password|pw)\s*[:：=]\s*([^\)\]\}>]+)[\)\]\}>]',
        fname,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    # 2. 괄호 없이 콜론/등호로 구분된 패턴
    m2 = re.search(
        r'(?:문서\s*열기\s*암호|문서\s*암호|열기\s*암호|암호|비밀번호|패스워드|password|pw)\s*[:：=]\s*([^\.\/\\_\(\)\[\]]+)',
        fname,
        re.IGNORECASE,
    )
    if m2:
        return m2.group(1).strip()
    # 3. 언더스코어(_) 또는 하이픈(-)으로 연결된 패턴 (예: 명세서_암호_주민번호앞6자리.pdf)
    m3 = re.search(
        r'(?:^|[_\-\s])(?:문서\s*열기\s*암호|문서\s*암호|열기\s*암호|암호|비밀번호|패스워드|pw)[_\-\s]([^\.\/\\]+)',
        fname,
        re.IGNORECASE,
    )
    if m3:
        return m3.group(1).strip()
    return None


class KPDFPasswordDialog(QDialog):
    """
    암호로 보호된 PDF 문서 열기 대화상자.
    - 파일명 표시 및 파일명 기반 암호 힌트 자동 감지/강조 (예: '주민번호 앞 6자리')
    - 비밀번호 마스킹 입력창 + 👁️ 암호 보기/숨기기 토글 버튼
    - 실시간 인증 검증 (틀릴 시 다이얼로그 유지 및 친절한 에러 안내)
    - 다크/라이트 테마 자동 호환
    """
    def __init__(self, doc: fitz.Document, file_path: str, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.file_path = file_path
        self.authenticated_password: Optional[str] = None
        self._is_dark = getattr(parent, "is_dark_effective", False)

        self.setWindowTitle("암호로 보호된 PDF — K-PDF Studio")
        self.setFixedWidth(460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 1. 헤더: 자물쇠 아이콘 + 타이틀
        h_header = QHBoxLayout()
        h_header.setSpacing(10)
        lbl_icon = QLabel("🔒")
        lbl_icon.setStyleSheet("font-size: 26px;")
        h_header.addWidget(lbl_icon)

        v_titles = QVBoxLayout()
        v_titles.setSpacing(2)
        lbl_main_title = QLabel("문서 열기 암호 입력")
        lbl_main_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        v_titles.addWidget(lbl_main_title)

        fname = os.path.basename(self.file_path) if self.file_path else "문서"
        lbl_fname = QLabel(fname)
        lbl_fname.setWordWrap(True)
        lbl_fname.setStyleSheet("font-size: 11px; color: #888888;")
        v_titles.addWidget(lbl_fname)
        h_header.addLayout(v_titles, 1)
        layout.addLayout(h_header)

        # 2. 스마트 힌트 카드 (파일명에서 힌트 감지 시)
        hint = extract_pdf_password_hint(self.file_path)
        if hint:
            self.hint_frame = QFrame()
            hint_layout = QHBoxLayout(self.hint_frame)
            hint_layout.setContentsMargins(12, 8, 12, 8)
            hint_layout.setSpacing(8)

            lbl_bulb = QLabel("💡")
            lbl_bulb.setStyleSheet("font-size: 16px;")
            hint_layout.addWidget(lbl_bulb)

            lbl_hint_text = QLabel(f"<b>파일명 힌트:</b> {hint}")
            lbl_hint_text.setWordWrap(True)
            lbl_hint_text.setStyleSheet("font-size: 12px;")
            hint_layout.addWidget(lbl_hint_text, 1)

            layout.addWidget(self.hint_frame)
        else:
            self.hint_frame = None

        # 3. 안내 설명
        lbl_desc = QLabel("이 문서는 암호로 보호되어 있습니다.\n열람 및 편집을 위해 문서 열기 암호를 입력하십시오.")
        lbl_desc.setStyleSheet("font-size: 12px; line-height: 1.4;")
        layout.addWidget(lbl_desc)

        # 4. 암호 입력창 + 👁️ 토글 버튼
        input_container = QHBoxLayout()
        input_container.setSpacing(6)

        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_edit.setPlaceholderText("암호를 입력하세요...")
        self.pw_edit.textChanged.connect(self._on_text_changed)
        input_container.addWidget(self.pw_edit, 1)

        self.btn_eye = QPushButton("👁️")
        self.btn_eye.setToolTip("암호 표시 / 숨기기")
        self.btn_eye.setFixedWidth(40)
        self.btn_eye.setCheckable(True)
        self.btn_eye.toggled.connect(self._toggle_password_visibility)
        input_container.addWidget(self.btn_eye)

        layout.addLayout(input_container)

        # 5. 에러 메시지 라벨 (초기 숨김)
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #d32f2f; font-size: 12px; font-weight: bold;")
        self.lbl_error.hide()
        layout.addWidget(self.lbl_error)

        layout.addSpacing(4)

        # 6. 하단 버튼 (취소, 확인)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("취소")
        self.btn_cancel.setFixedWidth(90)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("열기")
        self.btn_ok.setFixedWidth(90)
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self._on_ok_clicked)
        btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)

        self.pw_edit.setFocus()

    def _toggle_password_visibility(self, checked: bool):
        if checked:
            self.pw_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.pw_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def _on_text_changed(self):
        if self.lbl_error.isVisible():
            self.lbl_error.hide()

    def _on_ok_clicked(self):
        pw = self.pw_edit.text()
        if not pw:
            self.lbl_error.setText("⚠️ 암호를 입력해 주세요.")
            self.lbl_error.show()
            self.pw_edit.setFocus()
            return

        # fitz 인증 시도
        res = self.doc.authenticate(pw)
        if res == 0:
            self.lbl_error.setText("❌ 암호가 일치하지 않습니다. 다시 확인 후 입력해 주세요.")
            self.lbl_error.show()
            self.pw_edit.selectAll()
            self.pw_edit.setFocus()
            return

        self.authenticated_password = pw
        self.accept()

    def _apply_theme(self):
        if self._is_dark:
            self.setStyleSheet("""
                QDialog {
                    background-color: #202020;
                    color: #f0f0f0;
                }
                QLabel {
                    color: #f0f0f0;
                }
                QLineEdit {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #4a4a4a;
                    border-radius: 4px;
                    padding: 8px 10px;
                    font-size: 13px;
                }
                QLineEdit:focus {
                    border: 1px solid #0078d4;
                }
                QPushButton {
                    background-color: #2e2e2e;
                    color: #f0f0f0;
                    border: 1px solid #444444;
                    border-radius: 4px;
                    padding: 7px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                }
            """)
            if self.hint_frame:
                self.hint_frame.setStyleSheet("""
                    QFrame {
                        background-color: #142e18;
                        border: 1px solid #2e7d32;
                        border-radius: 6px;
                    }
                    QLabel {
                        color: #a5d6a7;
                    }
                """)
            self.btn_ok.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    color: #ffffff;
                    font-weight: bold;
                    border: none;
                    border-radius: 4px;
                    padding: 7px 12px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #fafafa;
                    color: #202020;
                }
                QLabel {
                    color: #202020;
                }
                QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 8px 10px;
                    font-size: 13px;
                }
                QLineEdit:focus {
                    border: 1px solid #0078d4;
                }
                QPushButton {
                    background-color: #f0f0f0;
                    color: #202020;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 7px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #e4e4e4;
                }
            """)
            if self.hint_frame:
                self.hint_frame.setStyleSheet("""
                    QFrame {
                        background-color: #e8f5e9;
                        border: 1px solid #81c784;
                        border-radius: 6px;
                    }
                    QLabel {
                        color: #1b5e20;
                    }
                """)
            self.btn_ok.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    color: #ffffff;
                    font-weight: bold;
                    border: none;
                    border-radius: 4px;
                    padding: 7px 12px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
            """)


def authenticate_doc_dialog(doc: fitz.Document, file_path: str, parent=None) -> Tuple[bool, Optional[fitz.Document], Optional[bytes]]:
    """
    암호 걸린 fitz.Document에 대해 암호 입력 대화상자를 띄우고,
    인증 성공 시 복호화된 새 Document와 바이트를 반환합니다.
    취소 또는 실패 시 (False, None, None) 반환.
    """
    if not doc.needs_pass:
        return True, doc, None

    dlg = KPDFPasswordDialog(doc=doc, file_path=file_path, parent=parent)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        try:
            # 복호화된 깨끗한 PDF 바이트 추출
            decrypted_bytes = doc.tobytes(garbage=3, deflate=True)
            doc.close()
            new_doc = fitz.open(stream=decrypted_bytes, filetype="pdf")
            return True, new_doc, decrypted_bytes
        except Exception:
            # 혹시 tobytes 실패 시 기존 doc 유지 (이미 authenticate 완료 상태)
            return True, doc, None
    else:
        # 취소
        doc.close()
        return False, None, None


@dataclass
class DocumentTab:
    tab_id: str
    file_path: Optional[str]
    doc: fitz.Document
    base_pdf_bytes: bytes
    page_objects: Dict[int, List[PageEditObject]] = field(default_factory=dict)
    undo_stack: List[dict] = field(default_factory=list)
    redo_stack: List[dict] = field(default_factory=list)
    current_page_idx: int = 0
    is_modified: bool = False
    zoom: float = 1.5
    file_ino: Optional[int] = None


# ---------------------------------------------------------------------
# Acrobat-style Interactive Page Thumbnail Delegate (Hover Action Buttons)
# ---------------------------------------------------------------------

class PageThumbnailDelegate(QStyledItemDelegate):
    """
    Renders Acrobat-style page thumbnails in QListWidget with:
    - High-DPI page preview thumbnail
    - Semi-transparent overlay with quick action buttons on hover:
      [↺ 좌로 회전] [🗑️ 삭제] [↻ 우로 회전] [📤 추출]
    - Multi-page selection badge
    """
    rotateLeftRequested = pyqtSignal(int)
    rotateRightRequested = pyqtSignal(int)
    deleteRequested = pyqtSignal(int)
    extractRequested = pyqtSignal(int)

    BTN_SIZE = 24
    BTN_SPACING = 4

    def __init__(self, parent=None, card_size: Optional[QSize] = None, show_hover_menu: bool = True):
        super().__init__(parent)
        self.hovered_index = -1
        self.hovered_btn = None  # 'rot_l', 'del', 'rot_r', 'ext'
        self.card_size = card_size or QSize(155, 205)
        self.show_hover_menu = show_hover_menu
        if parent is not None and hasattr(parent, "viewport"):
            parent.viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Leave:
            if self.hovered_index != -1 or self.hovered_btn is not None:
                self.hovered_index = -1
                self.hovered_btn = None
                QToolTip.hideText()
                if watched:
                    watched.update()
        return super().eventFilter(watched, event)

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return self.card_size

    def _get_button_rects(self, option_rect) -> Dict[str, QRectF]:
        w = 4 * self.BTN_SIZE + 3 * self.BTN_SPACING + 16
        h = self.BTN_SIZE + 10
        bx = option_rect.left() + (option_rect.width() - w) / 2.0
        by = option_rect.top() + (option_rect.height() - 35 - h) / 2.0

        btn_y = by + 5
        x0 = bx + 8
        r_rot_l = QRectF(x0, btn_y, self.BTN_SIZE, self.BTN_SIZE)
        r_del = QRectF(x0 + (self.BTN_SIZE + self.BTN_SPACING), btn_y, self.BTN_SIZE, self.BTN_SIZE)
        r_rot_r = QRectF(x0 + 2 * (self.BTN_SIZE + self.BTN_SPACING), btn_y, self.BTN_SIZE, self.BTN_SIZE)
        r_ext = QRectF(x0 + 3 * (self.BTN_SIZE + self.BTN_SPACING), btn_y, self.BTN_SIZE, self.BTN_SIZE)
        return {
            "rot_l": r_rot_l,
            "del": r_del,
            "rot_r": r_rot_r,
            "ext": r_ext,
            "_bar": QRectF(bx, by, w, h),
        }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        rect = option.rect
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hovered = (index.row() == self.hovered_index)

        # Calculate bounded card rect with clean symmetrical margins so borders are never clipped at left/right edges
        card_w = min(rect.width() - 8, float(self.card_size.width()))
        card_x = rect.left() + (rect.width() - card_w) / 2.0
        card_rect = QRectF(card_x, rect.top() + 2, card_w, rect.height() - 4)

        # 1. Background selection highlight
        if is_selected:
            painter.fillRect(card_rect, QColor(37, 99, 235, 45))
            painter.setPen(QPen(QColor(37, 99, 235), 2.0))
            painter.drawRoundedRect(card_rect.adjusted(1, 1, -1, -1), 6, 6)
        elif is_hovered:
            painter.fillRect(card_rect, QColor(148, 163, 184, 25))
            painter.setPen(QPen(QColor(148, 163, 184, 180), 1.2, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(card_rect.adjusted(1, 1, -1, -1), 6, 6)

        # 2. Draw Page Thumbnail Image
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if isinstance(icon, QIcon):
            max_w = max(40, rect.width() - 26)
            max_h = max(40, rect.height() - 44)
            pix = icon.pixmap(int(max_w), int(max_h))
            if not pix.isNull():
                thumb_x = rect.left() + (rect.width() - pix.width()) / 2.0
                thumb_y = rect.top() + 8
                thumb_rect = QRectF(thumb_x, thumb_y, pix.width(), pix.height())
                # Shadow
                painter.fillRect(thumb_rect.translated(2, 2), QColor(0, 0, 0, 45))
                painter.drawPixmap(int(thumb_x), int(thumb_y), pix)
                painter.setPen(QPen(QColor(203, 213, 225), 1.0))
                painter.drawRect(thumb_rect)

        # 3. Draw Page Label (e.g., '1 페이지')
        lbl_text = index.data(Qt.ItemDataRole.DisplayRole) or f"{index.row() + 1} 페이지"
        lbl_rect = QRectF(rect.left(), rect.bottom() - 26, rect.width(), 22)
        painter.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold if is_selected else QFont.Weight.Normal))
        painter.setPen(QColor(37, 99, 235) if is_selected else (QColor(226, 232, 240) if option.palette.windowText().color().lightness() > 128 else QColor(30, 41, 59)))
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, lbl_text)

        # 4. Draw Acrobat-style Hover Overlay Buttons: [↺] [🗑️] [↻] [📤]
        if is_hovered and self.show_hover_menu:
            btns = self._get_button_rects(rect)
            # Semi-transparent pill bar behind buttons
            painter.setBrush(QBrush(QColor(15, 23, 42, 215)))
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1.0))
            painter.drawRoundedRect(btns["_bar"], 14, 14)

            specs = [
                ("rot_l", "↺", "90° 좌회전"),
                ("del", "🗑️", "페이지 삭제"),
                ("rot_r", "↻", "90° 우회전"),
                ("ext", "📤", "페이지 추출"),
            ]
            for bid, icon_sym, tip in specs:
                brect = btns[bid]
                btn_active = (self.hovered_btn == bid)
                if btn_active:
                    painter.setBrush(QBrush(QColor(220, 38, 38, 220) if bid == "del" else QColor(37, 99, 235, 230)))
                    painter.setPen(QPen(QColor(255, 255, 255), 1.5))
                else:
                    painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
                    painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(brect, 12, 12)

                painter.setFont(QFont("Segoe UI Emoji", 10 if bid != "del" else 9))
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(brect, Qt.AlignmentFlag.AlignCenter, icon_sym)

        painter.restore()

    def editorEvent(self, event, model, option, index):
        row = index.row()
        if not self.show_hover_menu:
            if event.type() == event.Type.MouseMove:
                if self.hovered_index != row:
                    self.hovered_index = row
                    if option.widget:
                        option.widget.viewport().update()
                return False
            return super().editorEvent(event, model, option, index)

        if event.type() == event.Type.MouseMove:
            pos = event.position()
            btns = self._get_button_rects(option.rect)
            prev_btn = self.hovered_btn
            self.hovered_index = row
            self.hovered_btn = None
            for bname in ("rot_l", "del", "rot_r", "ext"):
                if btns[bname].contains(pos):
                    self.hovered_btn = bname
                    break
            if self.hovered_btn != prev_btn:
                tips = {
                    "rot_l": "이 페이지 왼쪽으로 90° 회전",
                    "del": "이 페이지 삭제",
                    "rot_r": "이 페이지 오른쪽으로 90° 회전",
                    "ext": "이 페이지를 별도 PDF로 추출",
                }
                if self.hovered_btn in tips:
                    QToolTip.showText(event.globalPosition().toPoint(), tips[self.hovered_btn])
                else:
                    QToolTip.hideText()
                if option.widget:
                    option.widget.viewport().update()

            # If mouse button is pressed down, the user is performing a DRAG gesture!
            # Return False so that QAbstractItemView can initiate startDrag!
            if event.buttons() & Qt.MouseButton.LeftButton:
                return False

            # If the cursor is NOT over one of the 4 hover buttons, do NOT consume the event
            # so standard view selection / mouse processing works unimpeded!
            if self.hovered_btn is None:
                return False

            return True

        elif event.type() == event.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            btns = self._get_button_rects(option.rect)
            for bname in ("rot_l", "del", "rot_r", "ext"):
                if btns[bname].contains(pos):
                    if bname == "rot_l":
                        self.rotateLeftRequested.emit(row)
                    elif bname == "rot_r":
                        self.rotateRightRequested.emit(row)
                    elif bname == "del":
                        self.deleteRequested.emit(row)
                    elif bname == "ext":
                        self.extractRequested.emit(row)
                    return True

        return super().editorEvent(event, model, option, index)


class ThumbnailSidebarListWidget(QListWidget):
    """
    Left sidebar thumbnail list widget with interactive drag-and-drop page reordering.
    Shows glowing horizontal drop indicator line and emits pagesReordered(selected_rows, insert_idx).
    """
    pagesReordered = pyqtSignal(list, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(False)
        self._drop_indicator_rect: Optional[QRectF] = None
        self._drag_start_pos: Optional[QPoint] = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            item = self.itemAt(self._drag_start_pos)
            if item:
                if not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                    if not item.isSelected():
                        self.clearSelection()
                        item.setSelected(True)
                        self.setCurrentItem(item)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, "_drag_start_pos") and self._drag_start_pos is not None:
            item = self.itemAt(self._drag_start_pos)
            if item:
                distance = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
                if distance >= QApplication.startDragDistance():
                    self.startDrag(Qt.DropAction.MoveAction)
                    self._drag_start_pos = None
                    return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def startDrag(self, supportedActions):
        selected_rows = sorted(set(idx.row() for idx in self.selectedIndexes()))
        curr = self.currentItem()
        if not selected_rows:
            if curr:
                selected_rows = [self.row(curr)]
            else:
                return
        if curr and self.row(curr) not in selected_rows:
            selected_rows = [self.row(curr)]

        mime = QMimeData()
        mime.setData("application/x-kpdf-sidebar-pages", json.dumps(selected_rows).encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime)

        card_w, card_h = 100, 130
        pix = QPixmap(card_w, card_h)
        pix.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        card_rect = QRectF(2, 2, card_w - 4, card_h - 4)
        painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
        painter.setPen(QPen(QColor(37, 99, 235), 2.0))
        painter.drawRoundedRect(card_rect, 6, 6)

        first_item = self.item(selected_rows[0])
        if first_item:
            icon = first_item.icon()
            if not icon.isNull():
                thumb_pix = icon.pixmap(card_w - 16, card_h - 36)
                if not thumb_pix.isNull():
                    tx = (card_w - thumb_pix.width()) / 2.0
                    ty = 6
                    painter.drawPixmap(int(tx), int(ty), thumb_pix)
                    painter.setPen(QPen(QColor(203, 213, 225), 1.0))
                    painter.drawRect(QRectF(tx, ty, thumb_pix.width(), thumb_pix.height()))

        lbl_rect = QRectF(4, card_h - 22, card_w - 8, 18)
        painter.setFont(QFont("Malgun Gothic", 8, QFont.Weight.Bold))
        painter.setPen(QColor(37, 99, 235))
        if len(selected_rows) == 1:
            lbl_text = f"{selected_rows[0] + 1} 페이지"
        else:
            lbl_text = f"{len(selected_rows)}개 페이지 이동"
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, lbl_text)
        painter.end()

        drag.setPixmap(pix)
        drag.setHotSpot(QPoint(card_w // 2, card_h // 2))

        drag.exec(Qt.DropAction.MoveAction)
        self._drop_indicator_rect = None
        self.viewport().update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-kpdf-sidebar-pages"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-kpdf-sidebar-pages"):
            pos = event.position().toPoint()
            target_item = self.itemAt(pos)
            if target_item:
                rect = self.visualItemRect(target_item)
                is_bottom = (pos.y() > rect.center().y())
                line_y = rect.bottom() + 1 if is_bottom else rect.top() - 1
                self._drop_indicator_rect = QRectF(rect.left() + 4, line_y - 2, rect.width() - 8, 4)
            else:
                if self.count() > 0:
                    last_rect = self.visualItemRect(self.item(self.count() - 1))
                    self._drop_indicator_rect = QRectF(last_rect.left() + 4, last_rect.bottom() - 1, last_rect.width() - 8, 4)
                else:
                    self._drop_indicator_rect = None
            self.viewport().update()
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self._drop_indicator_rect = None
        self.viewport().update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-kpdf-sidebar-pages"):
            try:
                selected_rows = json.loads(event.mimeData().data("application/x-kpdf-sidebar-pages").data().decode("utf-8"))
            except Exception:
                selected_rows = []

            pos = event.position().toPoint()
            target_item = self.itemAt(pos)

            if target_item:
                target_row = self.row(target_item)
                rect = self.visualItemRect(target_item)
                is_bottom = (pos.y() > rect.center().y())
                insert_idx = target_row + 1 if is_bottom else target_row
            else:
                insert_idx = self.count()

            self._drop_indicator_rect = None
            self.viewport().update()

            if selected_rows and insert_idx >= 0:
                self.pagesReordered.emit(selected_rows, insert_idx)

            event.acceptProposedAction()
            return

        super().dropEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_indicator_rect:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setBrush(QBrush(QColor(37, 99, 235)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self._drop_indicator_rect, 2, 2)
            ry = self._drop_indicator_rect.center().y()
            painter.drawEllipse(QRectF(self._drop_indicator_rect.left() - 2, ry - 4, 8, 8))
            painter.drawEllipse(QRectF(self._drop_indicator_rect.right() - 6, ry - 4, 8, 8))
            painter.end()


class OrganizePagesListWidget(QListWidget):
    """
    Full-screen Acrobat-style Organize Pages grid list widget.
    Supports extended multi-selection, drag-and-drop reordering with glowing vertical drop indicator,
    Esc key to exit, Delete/Backspace key to delete selected pages,
    and Ctrl + Mouse Wheel to zoom card sizes dynamically.
    """
    escapePressed = pyqtSignal()
    deletePressed = pyqtSignal()
    zoomRequest = pyqtSignal(int)  # +1: zoom in, -1: zoom out
    pagesReordered = pyqtSignal(list, int)  # (selected_rows, insert_idx)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(False)
        self._drop_indicator_rect: Optional[QRectF] = None
        self._drag_start_pos: Optional[QPoint] = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            item = self.itemAt(self._drag_start_pos)
            if item:
                if not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                    if not item.isSelected():
                        self.clearSelection()
                        item.setSelected(True)
                        self.setCurrentItem(item)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, "_drag_start_pos") and self._drag_start_pos is not None:
            item = self.itemAt(self._drag_start_pos)
            if item:
                distance = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
                if distance >= QApplication.startDragDistance():
                    self.startDrag(Qt.DropAction.MoveAction)
                    self._drag_start_pos = None
                    return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def startDrag(self, supportedActions):
        selected_rows = sorted(set(idx.row() for idx in self.selectedIndexes()))
        curr = self.currentItem()
        if not selected_rows:
            if curr:
                selected_rows = [self.row(curr)]
            else:
                return
        if curr and self.row(curr) not in selected_rows:
            selected_rows = [self.row(curr)]

        mime = QMimeData()
        mime.setData("application/x-kpdf-organize-pages", json.dumps(selected_rows).encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime)

        card_w, card_h = 120, 160
        pix = QPixmap(card_w, card_h)
        pix.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        card_rect = QRectF(2, 2, card_w - 4, card_h - 4)
        painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
        painter.setPen(QPen(QColor(37, 99, 235), 2.5))
        painter.drawRoundedRect(card_rect, 8, 8)

        first_item = self.item(selected_rows[0])
        if first_item:
            icon = first_item.icon()
            if not icon.isNull():
                thumb_pix = icon.pixmap(card_w - 20, card_h - 45)
                if not thumb_pix.isNull():
                    tx = (card_w - thumb_pix.width()) / 2.0
                    ty = 8
                    painter.drawPixmap(int(tx), int(ty), thumb_pix)
                    painter.setPen(QPen(QColor(203, 213, 225), 1.0))
                    painter.drawRect(QRectF(tx, ty, thumb_pix.width(), thumb_pix.height()))

        lbl_rect = QRectF(4, card_h - 26, card_w - 8, 20)
        painter.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
        painter.setPen(QColor(37, 99, 235))
        if len(selected_rows) == 1:
            lbl_text = f"{selected_rows[0] + 1} 페이지"
        else:
            lbl_text = f"{len(selected_rows)}개 페이지 이동"
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, lbl_text)
        painter.end()

        drag.setPixmap(pix)
        drag.setHotSpot(QPoint(card_w // 2, card_h // 2))

        drag.exec(Qt.DropAction.MoveAction)
        self._drop_indicator_rect = None
        self.viewport().update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-kpdf-organize-pages"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-kpdf-organize-pages"):
            pos = event.position().toPoint()
            target_item = self.itemAt(pos)
            if target_item:
                rect = self.visualItemRect(target_item)
                is_right = (pos.x() > rect.center().x())
                line_x = rect.right() + 4 if is_right else rect.left() - 4
                self._drop_indicator_rect = QRectF(line_x - 2, rect.top() + 4, 4, rect.height() - 8)
            else:
                if self.count() > 0:
                    last_item = self.item(self.count() - 1)
                    last_rect = self.visualItemRect(last_item)
                    self._drop_indicator_rect = QRectF(last_rect.right() + 4, last_rect.top() + 4, 4, last_rect.height() - 8)
                else:
                    self._drop_indicator_rect = None
            self.viewport().update()
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self._drop_indicator_rect = None
        self.viewport().update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-kpdf-organize-pages"):
            try:
                selected_rows = json.loads(event.mimeData().data("application/x-kpdf-organize-pages").data().decode("utf-8"))
            except Exception:
                selected_rows = []

            pos = event.position().toPoint()
            target_item = self.itemAt(pos)

            if target_item:
                target_row = self.row(target_item)
                rect = self.visualItemRect(target_item)
                is_right = (pos.x() > rect.center().x())
                insert_idx = target_row + 1 if is_right else target_row
            else:
                insert_idx = self.count()

            self._drop_indicator_rect = None
            self.viewport().update()

            if selected_rows and insert_idx >= 0:
                self.pagesReordered.emit(selected_rows, insert_idx)

            event.acceptProposedAction()
            return

        super().dropEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_indicator_rect:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setBrush(QBrush(QColor(37, 99, 235)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self._drop_indicator_rect, 2, 2)
            rx = self._drop_indicator_rect.center().x()
            painter.drawEllipse(QRectF(rx - 4, self._drop_indicator_rect.top() - 2, 8, 8))
            painter.drawEllipse(QRectF(rx - 4, self._drop_indicator_rect.bottom() - 6, 8, 8))
            painter.end()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoomRequest.emit(1)
                event.accept()
                return
            elif delta < 0:
                self.zoomRequest.emit(-1)
                event.accept()
                return
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.escapePressed.emit()
            event.accept()
            return
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.deletePressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class DynamicStackedWidget(QStackedWidget):
    """
    QStackedWidget whose sizeHint and minimumSizeHint dynamically reflect
    ONLY the currently active page, preventing inactive large views (like
    the full-screen Organize Pages grid) from constraining the main window.
    """
    def sizeHint(self) -> QSize:
        curr = self.currentWidget()
        return curr.sizeHint() if curr is not None else super().sizeHint()

    def minimumSizeHint(self) -> QSize:
        curr = self.currentWidget()
        return curr.minimumSizeHint() if curr is not None else super().minimumSizeHint()



# =====================================================================
# 7. Main Application Window (K-PDF Studio)
# =====================================================================

class KPDFStudioWindow(QMainWindow):
    SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kpdf_settings.json")

    def __init__(self, initial_pdf: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("K-PDF Studio — 한글 특화 PDF 뷰어·부분블록편집·병합·분할·인쇄 솔루션 (REA Engine)")
        self.resize(1480, 930)

        icon_path = ensure_app_icon()
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.indicator_icons = ensure_ui_indicator_icons()
        self.font_registry = KoreanFontRegistry()

        # Multi-tab document management
        self.doc_tabs: List[DocumentTab] = []
        self.active_tab_idx: int = -1
        self.app_mode: str = "view"   # Default mode: "view" (reading/viewing), "edit" (editing)

        # Active tab state pointers (mirrors active tab)
        self.current_file_path: Optional[str] = None
        self.base_pdf_bytes: Optional[bytes] = None
        self.doc: Optional[fitz.Document] = None
        self.current_page_idx: int = 0
        self.page_objects: Dict[int, List[PageEditObject]] = {}

        self.undo_stack: List[dict] = []
        self.redo_stack: List[dict] = []
        self.is_modified: bool = False
        self._loading_file: bool = False
        self._suppress_inspector_signals: bool = False
        self._active_text_sel_range: Tuple[int, int] = (0, 0)
        self._last_left_panel_width: int = 205
        self._last_right_panel_width: int = 355

        self.theme_mode: str = self._load_saved_theme_mode()
        self.is_dark_effective: bool = False
        self.page_view_mode: str = "continuous"  # 오픈 디폴트: '연속 스크롤' 모드

        # File System Watcher & Auto-Tracking for Renamed Files
        self.fs_watcher = QFileSystemWatcher(self)
        self.fs_watcher.directoryChanged.connect(self._on_fs_directory_changed)
        self.fs_watcher.fileChanged.connect(self._on_fs_file_changed)
        self._rename_check_timer = QTimer(self)
        self._rename_check_timer.setSingleShot(True)
        self._rename_check_timer.timeout.connect(self._check_open_files_renamed)

        self._build_ui()
        self._build_shortcuts()
        self._apply_theme(self.theme_mode)

        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

        if initial_pdf:
            tab_idx = self.open_pdf_in_tab(initial_pdf, make_active=True)
            if tab_idx is None:
                if hasattr(self, "center_stack"):
                    self.center_stack.setCurrentIndex(2)
                if hasattr(self, "left_panel"):
                    self.left_panel.setVisible(False)
                if hasattr(self, "right_panel"):
                    self.right_panel.setVisible(False)
                self._update_doc_actions_enabled(False)
        else:
            if hasattr(self, "center_stack"):
                self.center_stack.setCurrentIndex(2)
            if hasattr(self, "left_panel"):
                self.left_panel.setVisible(False)
            if hasattr(self, "right_panel"):
                self.right_panel.setVisible(False)
            self._update_doc_actions_enabled(False)

        # Background Keep-Alive Heartbeat Timer
        # 방치 상태에서 Windows OS 스케줄러에 의한 프로세스 수면/워킹셋 트리밍 및
        # 사내 보안 솔루션(Cyberdigm DestinyDrive 등)과의 OLE/LPC 세션 만료를 방지하기 위해
        # 30초마다 가벼운 메시지 펌프 틱을 발생시킵니다.
        self._keepalive_timer = QTimer(self)
        self._keepalive_timer.setInterval(30000)  # 30초마다 틱
        self._keepalive_timer.timeout.connect(self._on_keepalive_tick)
        self._keepalive_timer.start()

    def _on_keepalive_tick(self):
        # 유휴 상태에서 Windows 메시지 큐와 OLE 아파트먼트 활성 유지
        pass

    # -----------------------------------------------------------------
    # Theme Engine: Windows System Default / Light / Dark + Crisp Indicators
    # -----------------------------------------------------------------
    def _load_saved_theme_mode(self) -> str:
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                m = data.get("theme_mode", "system")
                if m in ("system", "light", "dark"):
                    return m
        except Exception:
            pass
        return "system"

    def _save_theme_mode(self, mode: str):
        try:
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"theme_mode": mode}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_theme_combo_changed(self):
        mode = self.theme_combo.currentData() or "system"
        self.theme_mode = mode
        self._save_theme_mode(mode)
        self._apply_theme(mode)

    def _apply_theme(self, mode: str):
        if mode == "system":
            is_dark = detect_windows_use_dark_theme()
        else:
            is_dark = (mode == "dark")
        self.is_dark_effective = is_dark

        if hasattr(self, "canvas"):
            self.canvas.is_dark_theme = is_dark
            self.canvas.update()

        if hasattr(self, "continuous_scroll_area"):
            self.continuous_scroll_area.continuous_canvas.is_dark_theme = is_dark
            self.continuous_scroll_area.continuous_canvas.update()

        bg_hex = "#1E222A" if is_dark else "#DAE0E9"
        if hasattr(self, "scroll_area") and self.scroll_area:
            self.scroll_area.setStyleSheet(f"QScrollArea {{ background-color: {bg_hex}; border: none; }}")
            if hasattr(self.scroll_area, "viewport") and self.scroll_area.viewport():
                self.scroll_area.viewport().setStyleSheet(f"background-color: {bg_hex};")
        if hasattr(self, "continuous_scroll_area") and self.continuous_scroll_area:
            self.continuous_scroll_area.setStyleSheet(f"QScrollArea {{ background-color: {bg_hex}; border: none; }}")
            if hasattr(self.continuous_scroll_area, "viewport") and self.continuous_scroll_area.viewport():
                self.continuous_scroll_area.viewport().setStyleSheet(f"background-color: {bg_hex};")

        app = QApplication.instance()
        if app is not None:
            app.setStyle("Fusion")
            pal = QPalette()
            if is_dark:
                pal.setColor(QPalette.ColorRole.Window, QColor(24, 27, 32))
                pal.setColor(QPalette.ColorRole.WindowText, QColor(243, 244, 246))
                pal.setColor(QPalette.ColorRole.Base, QColor(17, 24, 39))
                pal.setColor(QPalette.ColorRole.AlternateBase, QColor(31, 41, 55))
                pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(31, 41, 55))
                pal.setColor(QPalette.ColorRole.ToolTipText, QColor(249, 250, 251))
                pal.setColor(QPalette.ColorRole.Text, QColor(249, 250, 251))
                pal.setColor(QPalette.ColorRole.Button, QColor(45, 51, 63))
                pal.setColor(QPalette.ColorRole.ButtonText, QColor(243, 244, 246))
                pal.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
                pal.setColor(QPalette.ColorRole.Light, QColor(75, 85, 99))
                pal.setColor(QPalette.ColorRole.Midlight, QColor(55, 65, 81))
                pal.setColor(QPalette.ColorRole.Mid, QColor(107, 114, 128))
                pal.setColor(QPalette.ColorRole.Dark, QColor(31, 41, 55))
            else:
                pal.setColor(QPalette.ColorRole.Window, QColor(243, 244, 246))
                pal.setColor(QPalette.ColorRole.WindowText, QColor(17, 24, 39))
                pal.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
                pal.setColor(QPalette.ColorRole.AlternateBase, QColor(249, 250, 251))
                pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
                pal.setColor(QPalette.ColorRole.ToolTipText, QColor(17, 24, 39))
                pal.setColor(QPalette.ColorRole.Text, QColor(17, 24, 39))
                pal.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255))
                pal.setColor(QPalette.ColorRole.ButtonText, QColor(17, 24, 39))
                pal.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
                pal.setColor(QPalette.ColorRole.Light, QColor(255, 255, 255))
                pal.setColor(QPalette.ColorRole.Midlight, QColor(229, 231, 235))
                pal.setColor(QPalette.ColorRole.Mid, QColor(156, 163, 175))
                pal.setColor(QPalette.ColorRole.Dark, QColor(107, 114, 128))

            pal.setColor(QPalette.ColorRole.Highlight, QColor(37, 99, 235))
            pal.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            pal.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, QColor(37, 99, 235))
            pal.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            app.setPalette(pal)

        chk_un = self.indicator_icons["chk_un_dark" if is_dark else "chk_un_light"]
        chk_on = self.indicator_icons["chk_checked"]
        rad_un = self.indicator_icons["rad_un_dark" if is_dark else "rad_un_light"]
        rad_on = self.indicator_icons["rad_checked"]

        if is_dark:
            self.setStyleSheet(f"""
                QMainWindow, QDialog {{
                    background-color: #181B20;
                    color: #F3F4F6;
                    font-family: 'Malgun Gothic', sans-serif;
                    font-size: 10pt;
                }}
                QMenuBar {{
                    background-color: #181B20;
                    color: #E5E7EB;
                    border-bottom: 1px solid #374151;
                    font-size: 10pt;
                    padding: 2px 6px;
                }}
                QMenuBar::item {{
                    background: transparent;
                    padding: 4px 10px;
                    border-radius: 4px;
                }}
                QMenuBar::item:selected {{
                    background-color: #2D333F;
                    color: #FFFFFF;
                }}
                QMenuBar::item:pressed {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QMenu {{
                    background-color: #1F2937;
                    color: #F3F4F6;
                    border: 1px solid #4B5563;
                    border-radius: 6px;
                    padding: 4px;
                }}
                QMenu::item {{
                    padding: 6px 26px 6px 20px;
                    border-radius: 4px;
                }}
                QMenu::item:selected {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QMenu::separator {{
                    height: 1px;
                    background-color: #374151;
                    margin: 4px 8px;
                }}
                QToolBar {{
                    background-color: #22262E;
                    border-bottom: 1px solid #374151;
                    spacing: 4px;
                    padding: 3px 6px;
                }}
                QToolBar QPushButton, QToolBar QToolButton {{
                    background-color: #2D333F;
                    color: #F3F4F6;
                    border: 1px solid #4B5563;
                    border-radius: 4px;
                    padding: 4px 7px;
                }}
                QPushButton, QToolButton {{
                    background-color: #2D333F;
                    color: #F3F4F6;
                    border: 1px solid #4B5563;
                    border-radius: 4px;
                    padding: 5px 10px;
                }}
                QPushButton:hover, QToolButton:hover {{
                    background-color: #3B4252;
                    border-color: #60A5FA;
                }}
                QPushButton:checked, QToolButton:checked {{
                    background-color: #2563EB;
                    border: 2px solid #93C5FD;
                    color: #FFFFFF;
                    font-weight: bold;
                }}
                QCheckBox, QRadioButton {{
                    color: #F3F4F6;
                    spacing: 7px;
                    padding: 2px 4px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    image: url("{chk_un}");
                }}
                QCheckBox::indicator:checked {{
                    image: url("{chk_on}");
                }}
                QRadioButton::indicator {{
                    width: 18px;
                    height: 18px;
                    image: url("{rad_un}");
                }}
                QRadioButton::indicator:checked {{
                    image: url("{rad_on}");
                }}
                QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                    background-color: #111827;
                    color: #F9FAFB;
                    selection-background-color: #2563EB;
                    selection-color: #FFFFFF;
                    border: 1px solid #4B5563;
                    border-radius: 4px;
                    padding: 4px 6px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: #1F2937;
                    color: #F9FAFB;
                    selection-background-color: #2563EB;
                    selection-color: #FFFFFF;
                    border: 1px solid #60A5FA;
                    padding: 4px;
                    outline: 0px;
                }}
                QComboBox QAbstractItemView::item {{
                    min-height: 26px;
                    padding: 4px 8px;
                    color: #F9FAFB;
                    background-color: #1F2937;
                }}
                QComboBox QAbstractItemView::item:selected,
                QComboBox QAbstractItemView::item:hover {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QListWidget {{
                    background-color: #1F242D;
                    color: #E5E7EB;
                    border: 1px solid #374151;
                    outline: none;
                }}
                QListWidget::item:hover:!selected {{
                    background-color: #2D3748;
                    color: #E5E7EB;
                }}
                QListWidget::item:selected {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QListWidget::item:selected:hover {{
                    background-color: #3B82F6;
                    color: #FFFFFF;
                }}
                QListWidget::item:selected:!active {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QGroupBox {{
                    border: 1px solid #374151;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                    color: #93C5FD;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 4px;
                }}
                QLabel {{
                    color: #E5E7EB;
                }}
                QStatusBar {{
                    background-color: #111827;
                    color: #9CA3AF;
                    border-top: 1px solid #374151;
                }}
                QTabBar {{
                    background-color: #1E222A;
                    border-bottom: 1px solid #374151;
                }}
                QTabBar::tab {{
                    background-color: #272C35;
                    color: #9CA3AF;
                    border: 1px solid #374151;
                    border-bottom: none;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    padding: 6px 14px;
                    min-width: 100px;
                    margin-right: 3px;
                    font-size: 9.5pt;
                }}
                QTabBar::tab:hover:!selected {{
                    background-color: #323844;
                    color: #F3F4F6;
                }}
                QTabBar::tab:selected {{
                    background-color: #181B20;
                    color: #60A5FA;
                    border-top: 2px solid #3B82F6;
                    font-weight: bold;
                }}
                QScrollBar:vertical {{
                    border: none;
                    background-color: #181B20;
                    width: 14px;
                    margin: 0px;
                    border-radius: 7px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: #4B5563;
                    min-height: 32px;
                    border-radius: 6px;
                    margin: 2px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: #3B82F6;
                }}
                QScrollBar::handle:vertical:pressed {{
                    background-color: #2563EB;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: none;
                }}
                QScrollBar:horizontal {{
                    border: none;
                    background-color: #181B20;
                    height: 14px;
                    margin: 0px;
                    border-radius: 7px;
                }}
                QScrollBar::handle:horizontal {{
                    background-color: #4B5563;
                    min-width: 32px;
                    border-radius: 6px;
                    margin: 2px;
                }}
                QScrollBar::handle:horizontal:hover {{
                    background-color: #3B82F6;
                }}
                QScrollBar::handle:horizontal:pressed {{
                    background-color: #2563EB;
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    height: 0px;
                }}
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                    background: none;
                }}
                QTabWidget::pane {{
                    border: 1px solid #374151;
                    background-color: #1F242D;
                    top: -1px;
                }}
                QTableWidget {{
                    background-color: #1F242D;
                    color: #F3F4F6;
                    gridline-color: #374151;
                    border: 1px solid #374151;
                }}
                QTableWidget::item:selected {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QHeaderView::section {{
                    background-color: #2D333F;
                    color: #93C5FD;
                    font-weight: bold;
                    padding: 5px 8px;
                    border: 1px solid #374151;
                }}
                QFrame#welcome_card {{
                    background-color: #1E242D;
                    border: 1px solid #334155;
                    border-radius: 12px;
                }}
                QFrame#drop_hint_box {{
                    border: 2px dashed #475569;
                    border-radius: 8px;
                    background-color: #141A22;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QMainWindow, QDialog {{
                    background-color: #F3F4F6;
                    color: #111827;
                    font-family: 'Malgun Gothic', sans-serif;
                    font-size: 10pt;
                }}
                QMenuBar {{
                    background-color: #F8FAFC;
                    color: #1E293B;
                    border-bottom: 1px solid #E2E8F0;
                    font-size: 10pt;
                    padding: 2px 6px;
                }}
                QMenuBar::item {{
                    background: transparent;
                    padding: 4px 10px;
                    border-radius: 4px;
                }}
                QMenuBar::item:selected {{
                    background-color: #E2E8F0;
                    color: #0F172A;
                }}
                QMenuBar::item:pressed {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QMenu {{
                    background-color: #FFFFFF;
                    color: #1E293B;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 4px;
                }}
                QMenu::item {{
                    padding: 6px 26px 6px 20px;
                    border-radius: 4px;
                }}
                QMenu::item:selected {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QMenu::separator {{
                    height: 1px;
                    background-color: #E2E8F0;
                    margin: 4px 8px;
                }}
                QToolBar {{
                    background-color: #FFFFFF;
                    border-bottom: 1px solid #D1D5DB;
                    spacing: 4px;
                    padding: 3px 6px;
                }}
                QToolBar QPushButton, QToolBar QToolButton {{
                    background-color: #FFFFFF;
                    color: #1F2937;
                    border: 1px solid #9CA3AF;
                    border-radius: 4px;
                    padding: 4px 7px;
                }}
                QPushButton, QToolButton {{
                    background-color: #FFFFFF;
                    color: #1F2937;
                    border: 1px solid #9CA3AF;
                    border-radius: 4px;
                    padding: 5px 10px;
                }}
                QPushButton:hover, QToolButton:hover {{
                    background-color: #EFF6FF;
                    border-color: #2563EB;
                }}
                QPushButton:checked, QToolButton:checked {{
                    background-color: #2563EB;
                    border: 2px solid #1D4ED8;
                    color: #FFFFFF;
                    font-weight: bold;
                }}
                QCheckBox, QRadioButton {{
                    color: #111827;
                    spacing: 7px;
                    padding: 2px 4px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    image: url("{chk_un}");
                }}
                QCheckBox::indicator:checked {{
                    image: url("{chk_on}");
                }}
                QRadioButton::indicator {{
                    width: 18px;
                    height: 18px;
                    image: url("{rad_un}");
                }}
                QRadioButton::indicator:checked {{
                    image: url("{rad_on}");
                }}
                QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                    background-color: #FFFFFF;
                    color: #111827;
                    selection-background-color: #2563EB;
                    selection-color: #FFFFFF;
                    border: 1px solid #9CA3AF;
                    border-radius: 4px;
                    padding: 4px 6px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: #FFFFFF;
                    color: #111827;
                    selection-background-color: #2563EB;
                    selection-color: #FFFFFF;
                    border: 1px solid #2563EB;
                    padding: 4px;
                    outline: 0px;
                }}
                QComboBox QAbstractItemView::item {{
                    min-height: 26px;
                    padding: 4px 8px;
                    color: #111827;
                    background-color: #FFFFFF;
                }}
                QComboBox QAbstractItemView::item:selected,
                QComboBox QAbstractItemView::item:hover {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QListWidget {{
                    background-color: #FFFFFF;
                    color: #111827;
                    border: 1px solid #D1D5DB;
                    outline: none;
                }}
                QListWidget::item:hover:!selected {{
                    background-color: #F3F4F6;
                    color: #111827;
                }}
                QListWidget::item:selected {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QListWidget::item:selected:hover {{
                    background-color: #3B82F6;
                    color: #FFFFFF;
                }}
                QListWidget::item:selected:!active {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QGroupBox {{
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                    color: #1D4ED8;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 4px;
                }}
                QLabel {{
                    color: #1F2937;
                }}
                QStatusBar {{
                    background-color: #E5E7EB;
                    color: #374151;
                    border-top: 1px solid #D1D5DB;
                }}
                QTabBar {{
                    background-color: #E2E8F0;
                    border-bottom: 1px solid #CBD5E1;
                }}
                QTabBar::tab {{
                    background-color: #F1F5F9;
                    color: #475569;
                    border: 1px solid #CBD5E1;
                    border-bottom: none;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    padding: 6px 14px;
                    min-width: 100px;
                    margin-right: 3px;
                    font-size: 9.5pt;
                }}
                QTabBar::tab:hover:!selected {{
                    background-color: #FFFFFF;
                    color: #0F172A;
                }}
                QTabBar::tab:selected {{
                    background-color: #FFFFFF;
                    color: #1D4ED8;
                    border-top: 2px solid #2563EB;
                    font-weight: bold;
                }}
                QScrollBar:vertical {{
                    border: none;
                    background-color: #F3F4F6;
                    width: 14px;
                    margin: 0px;
                    border-radius: 7px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: #CBD5E1;
                    min-height: 32px;
                    border-radius: 6px;
                    margin: 2px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: #3B82F6;
                }}
                QScrollBar::handle:vertical:pressed {{
                    background-color: #2563EB;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: none;
                }}
                QScrollBar:horizontal {{
                    border: none;
                    background-color: #F3F4F6;
                    height: 14px;
                    margin: 0px;
                    border-radius: 7px;
                }}
                QScrollBar::handle:horizontal {{
                    background-color: #CBD5E1;
                    min-width: 32px;
                    border-radius: 6px;
                    margin: 2px;
                }}
                QScrollBar::handle:horizontal:hover {{
                    background-color: #3B82F6;
                }}
                QScrollBar::handle:horizontal:pressed {{
                    background-color: #2563EB;
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    height: 0px;
                }}
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                    background: none;
                }}
                QTabWidget::pane {{
                    border: 1px solid #D1D5DB;
                    background-color: #FFFFFF;
                    top: -1px;
                }}
                QTableWidget {{
                    background-color: #FFFFFF;
                    color: #111827;
                    gridline-color: #E5E7EB;
                    border: 1px solid #D1D5DB;
                }}
                QTableWidget::item:selected {{
                    background-color: #2563EB;
                    color: #FFFFFF;
                }}
                QHeaderView::section {{
                    background-color: #F1F5F9;
                    color: #1D4ED8;
                    font-weight: bold;
                    padding: 5px 8px;
                    border: 1px solid #E2E8F0;
                }}
                QFrame#welcome_card {{
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }}
                QFrame#drop_hint_box {{
                    border: 2px dashed #CBD5E1;
                    border-radius: 8px;
                    background-color: #F8FAFC;
                }}
            """)

        if hasattr(self, "sel_info_lbl"):
            if is_dark:
                self.sel_info_lbl.setStyleSheet(
                    "background-color: #1F2937; color: #E5E7EB; padding: 6px; border-radius: 4px; border: 1px solid #374151;"
                )
                self.inspector_title_lbl.setStyleSheet("font-size: 11pt; font-weight: bold; color: #60A5FA; padding-bottom: 4px;")
                self.orig_font_lbl.setStyleSheet("color: #9CA3AF;")
                self.btn_del_obj.setStyleSheet("background-color: #991B1B; color: #FFFFFF; border-color: #EF4444; font-weight: bold;")
            else:
                self.sel_info_lbl.setStyleSheet(
                    "background-color: #E0E7FF; color: #1E3A8A; padding: 6px; border-radius: 4px; border: 1px solid #93C5FD; font-weight: bold;"
                )
                self.inspector_title_lbl.setStyleSheet("font-size: 11pt; font-weight: bold; color: #1D4ED8; padding-bottom: 4px;")
                self.orig_font_lbl.setStyleSheet("color: #4B5563;")
                self.btn_del_obj.setStyleSheet("background-color: #DC2626; color: #FFFFFF; border-color: #B91C1C; font-weight: bold;")
            self._update_block_scope_indicator(self.canvas.selected_obj, *self._active_text_sel_range)

        if hasattr(self, "panel_header_lbl"):
            if is_dark:
                self.panel_header_lbl.setStyleSheet("font-weight: bold; font-size: 10pt; color: #9CA3AF;")
                if hasattr(self, "btn_collapse_right_panel"):
                    self.btn_collapse_right_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #374151;
                            color: #D1D5DB;
                            border: 1px solid #4B5563;
                            border-radius: 4px;
                            padding: 2px 10px;
                            font-size: 9pt;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #4B5563;
                            color: #FFFFFF;
                        }
                    """)
            else:
                self.panel_header_lbl.setStyleSheet("font-weight: bold; font-size: 10pt; color: #4B5563;")
                if hasattr(self, "btn_collapse_right_panel"):
                    self.btn_collapse_right_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #F3F4F6;
                            color: #374151;
                            border: 1px solid #D1D5DB;
                            border-radius: 4px;
                            padding: 2px 10px;
                            font-size: 9pt;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #E5E7EB;
                            color: #111827;
                        }
                    """)

        if hasattr(self, "left_header_lbl"):
            if is_dark:
                self.left_header_lbl.setStyleSheet("font-weight: bold; font-size: 10pt; color: #9CA3AF;")
                if hasattr(self, "btn_collapse_left_panel"):
                    self.btn_collapse_left_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #374151;
                            color: #D1D5DB;
                            border: 1px solid #4B5563;
                            border-radius: 4px;
                            padding: 2px 10px;
                            font-size: 9pt;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #4B5563;
                            color: #FFFFFF;
                        }
                    """)
            else:
                self.left_header_lbl.setStyleSheet("font-weight: bold; font-size: 10pt; color: #4B5563;")
                if hasattr(self, "btn_collapse_left_panel"):
                    self.btn_collapse_left_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #F3F4F6;
                            color: #374151;
                            border: 1px solid #D1D5DB;
                            border-radius: 4px;
                            padding: 2px 10px;
                            font-size: 9pt;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #E5E7EB;
                            color: #111827;
                        }
                    """)

        self._update_toggle_panel_btn_style()

    # -----------------------------------------------------------------
    # Unsaved Modification Tracking & Save Confirmation on Close
    # -----------------------------------------------------------------
    def _set_modified(self, mod: bool):
        self.is_modified = mod
        self._update_window_title()

    def _update_window_title(self):
        if not self.doc_tabs or self.active_tab_idx < 0:
            self.setWindowTitle("K-PDF Studio")
            return
        fname = os.path.basename(self.current_file_path) if self.current_file_path else "새 문서"
        prefix = "*[수정됨] " if self.is_modified else ""
        self.setWindowTitle(f"{prefix}{fname} — K-PDF Studio")

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow():
            self._check_open_files_renamed()
        super().changeEvent(event)

    # -----------------------------------------------------------------
    # File System Watcher & Auto-Tracking for Renamed / Moved Files
    # -----------------------------------------------------------------
    def _watch_tab_file(self, tab: DocumentTab):
        """Watches the file and its parent folder for rename/change events."""
        if not tab.file_path or not os.path.exists(tab.file_path):
            return
        abs_path = os.path.abspath(tab.file_path)
        parent_dir = os.path.dirname(abs_path)
        try:
            if hasattr(self, "fs_watcher"):
                dirs = self.fs_watcher.directories()
                if parent_dir and os.path.isdir(parent_dir) and parent_dir not in dirs:
                    self.fs_watcher.addPath(parent_dir)
                files = self.fs_watcher.files()
                if abs_path not in files:
                    self.fs_watcher.addPath(abs_path)
        except Exception:
            pass

    def _unwatch_tab_file(self, tab: DocumentTab):
        """Removes the tab's file and parent folder from watcher if no other tab uses it."""
        if not tab.file_path or not hasattr(self, "fs_watcher"):
            return
        abs_path = os.path.abspath(tab.file_path)
        parent_dir = os.path.dirname(abs_path)
        try:
            if abs_path in self.fs_watcher.files():
                self.fs_watcher.removePath(abs_path)
            # Check if any other tab shares the same parent directory
            other_dirs = {
                os.path.dirname(os.path.abspath(t.file_path))
                for t in self.doc_tabs
                if t != tab and t.file_path
            }
            if parent_dir not in other_dirs and parent_dir in self.fs_watcher.directories():
                self.fs_watcher.removePath(parent_dir)
        except Exception:
            pass

    def _on_fs_directory_changed(self, path: str):
        if hasattr(self, "_rename_check_timer"):
            self._rename_check_timer.start(250)

    def _on_fs_file_changed(self, path: str):
        if hasattr(self, "_rename_check_timer"):
            self._rename_check_timer.start(250)

    def _check_open_files_renamed(self):
        """Scans open tabs to see if any file was renamed externally in Windows Explorer."""
        if not self.doc_tabs:
            return

        for idx, tab in enumerate(self.doc_tabs):
            if not tab.file_path or tab.file_ino is None:
                continue
            # If the recorded path still exists and inode matches, everything is fine
            if os.path.exists(tab.file_path):
                try:
                    cur_ino = os.stat(tab.file_path).st_ino
                    if cur_ino == tab.file_ino:
                        continue
                except Exception:
                    pass

            # The original file path no longer exists (or has different inode).
            # Look in the parent directory for a .pdf file that has the SAME inode!
            parent_dir = os.path.dirname(os.path.abspath(tab.file_path))
            if not os.path.isdir(parent_dir):
                continue

            found_new_path = None
            try:
                for entry in os.scandir(parent_dir):
                    if entry.is_file() and entry.name.lower().endswith(".pdf"):
                        try:
                            st_ino = os.stat(entry.path).st_ino
                            if st_ino == tab.file_ino:
                                found_new_path = entry.path
                                break
                        except Exception:
                            pass
            except Exception:
                pass

            if found_new_path and os.path.abspath(found_new_path) != os.path.abspath(tab.file_path):
                self._apply_file_renamed(idx, tab, found_new_path)

    def _apply_file_renamed(self, idx: int, tab: DocumentTab, new_path: str):
        """Applies external rename to the tab, updating tab bar, window title and status."""
        old_path = tab.file_path
        old_name = os.path.basename(old_path) if old_path else "이전 파일"
        new_name = os.path.basename(new_path)

        # Unwatch old file path
        try:
            if hasattr(self, "fs_watcher"):
                old_abs = os.path.abspath(old_path)
                if old_abs in self.fs_watcher.files():
                    self.fs_watcher.removePath(old_abs)
        except Exception:
            pass

        tab.file_path = new_path
        try:
            tab.file_ino = os.stat(new_path).st_ino
        except Exception:
            pass

        # If this is the currently active tab, update current_file_path and window title
        if idx == self.active_tab_idx:
            self.current_file_path = new_path
            self._update_window_title()

        # Update tab bar title and tooltip
        if hasattr(self, "tab_bar") and 0 <= idx < self.tab_bar.count():
            tab_title = new_name if len(new_name) <= 26 else (new_name[:23] + "...")
            self.tab_bar.setTabText(idx, tab_title)
            self.tab_bar.setTabToolTip(idx, new_path)

        # Watch new file path
        self._watch_tab_file(tab)

        self.status_bar.showMessage(
            f"📢 파일명 변경 감지: '{old_name}' ➔ '{new_name}' (저장 경로 자동 갱신됨)", 6000
        )

    # -----------------------------------------------------------------
    # Sibling PDF Navigation (Image Viewer Style Prev / Next in Folder)
    # -----------------------------------------------------------------
    def navigate_sibling_pdf(self, direction: int):
        """Navigates to previous (direction=-1) or next (direction=1) PDF in the same folder."""
        # 1. First check if current file was renamed externally
        self._check_open_files_renamed()

        if not self.current_file_path or not os.path.exists(self.current_file_path):
            self.status_bar.showMessage("⚠️ 열려 있거나 저장된 파일이 있는 상태에서만 같은 폴더 내 탐색이 가능합니다.", 3000)
            return

        # 2. Check for unsaved changes
        if self.is_modified:
            fname = os.path.basename(self.current_file_path)
            res = QMessageBox.question(
                self,
                "수정 사항 저장 안내",
                f"'{fname}' 문서에 저장되지 않은 수정 사항이 있습니다.\n\n저장하고 다른 파일로 이동하시겠습니까?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if res == QMessageBox.StandardButton.Cancel:
                return
            elif res == QMessageBox.StandardButton.Save:
                if not self.save_pdf():
                    return

        # 3. Scan folder for PDF files with natural sort
        folder = os.path.dirname(os.path.abspath(self.current_file_path))
        if not os.path.isdir(folder):
            return

        def _natural_key(text: str):
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", text)]

        try:
            pdf_entries = [
                f for f in os.listdir(folder)
                if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(folder, f))
            ]
            pdf_entries.sort(key=_natural_key)
        except Exception as e:
            self.status_bar.showMessage(f"폴더 탐색 오류: {e}", 3000)
            return

        if not pdf_entries:
            self.status_bar.showMessage("현재 폴더에 PDF 파일이 없습니다.", 3000)
            return

        if len(pdf_entries) == 1:
            self.status_bar.showMessage("현재 폴더에 다른 PDF 파일이 없습니다 (단일 파일).", 3000)
            return

        # 4. Locate current file index
        cur_filename = os.path.basename(self.current_file_path)
        cur_idx = -1
        for i, fn in enumerate(pdf_entries):
            if fn.lower() == cur_filename.lower():
                cur_idx = i
                break

        if cur_idx == -1:
            # If not found directly, start from 0
            cur_idx = 0

        # 5. Calculate target index (wrap-around)
        target_idx = (cur_idx + direction) % len(pdf_entries)
        target_file = pdf_entries[target_idx]
        target_path = os.path.join(folder, target_file)

        # 6. Load target file into current active tab (Replace active tab contents)
        self.load_pdf_file(target_path)
        self.switch_to_view_mode()
        self.status_bar.showMessage(
            f"📄 [{target_idx + 1}/{len(pdf_entries)}] '{target_file}' 로드 완료", 4000
        )

    def rename_current_file(self):
        """Opens a rename popup dialog (F2, nomacs style) to rename the currently active PDF file."""
        # 1. First ensure open files list is in sync
        self._check_open_files_renamed()

        if not self.current_file_path or not os.path.exists(self.current_file_path):
            self.status_bar.showMessage("⚠️ 이름을 변경할 PDF 파일이 없습니다.", 3000)
            return

        # 2. Check for unsaved changes before renaming
        if self.is_modified:
            fname = os.path.basename(self.current_file_path)
            res = QMessageBox.question(
                self,
                "수정 사항 저장 안내",
                f"'{fname}' 문서에 저장되지 않은 수정 사항이 있습니다.\n\n저장하고 이름을 변경하시겠습니까?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if res == QMessageBox.StandardButton.Cancel:
                return
            elif res == QMessageBox.StandardButton.Save:
                if not self.save_pdf():
                    return

        # 3. Open KPDFRenameDialog
        dlg = KPDFRenameDialog(self.current_file_path, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_name = dlg.get_new_name()
            old_path = os.path.abspath(self.current_file_path)
            old_name = os.path.basename(old_path)
            parent_dir = os.path.dirname(old_path)
            new_path = os.path.join(parent_dir, new_name)

            if old_path == os.path.abspath(new_path):
                return

            try:
                # Handle Windows case-only rename via temporary file
                if old_path.lower() == os.path.abspath(new_path).lower():
                    temp_path = new_path + f".kpdf_rename_tmp_{int(time.time()*1000)}"
                    os.rename(old_path, temp_path)
                    os.rename(temp_path, new_path)
                else:
                    os.rename(old_path, new_path)
            except Exception as e:
                QMessageBox.critical(self, "이름 바꾸기 실패", f"파일명을 변경하는 중 오류가 발생했습니다:\n{str(e)}")
                return

            # Synchronize active tab and UI
            if 0 <= self.active_tab_idx < len(self.doc_tabs):
                tab = self.doc_tabs[self.active_tab_idx]
                self._apply_file_renamed(self.active_tab_idx, tab, new_path)
            else:
                self.current_file_path = new_path
                self._update_window_title()

            self.status_bar.showMessage(
                f"✅ 파일명 변경 완료: '{old_name}' ➔ '{new_name}'", 5000
            )

    def _update_doc_actions_enabled(self, enabled: bool):
        """Enables or disables toolbar and menu actions depending on whether a document is open."""
        for attr in (
            "btn_mode_view", "btn_mode_edit", "btn_save", "btn_save_as",
            "btn_organize_pages", "btn_doc_props", "btn_print",
            "btn_undo", "btn_redo", "zoom_combo", "btn_page_view_mode",
            "btn_fit_w", "btn_fit_h", "btn_fit_page", "btn_zoom_in", "btn_zoom_out",
            "btn_prev_pdf", "btn_next_pdf", "btn_rename_pdf", "act_prev_pdf", "act_next_pdf", "act_rename",
            "act_save", "act_save_as", "act_print", "act_doc_props",
            "act_close_tab", "act_undo", "act_redo", "act_org_pages", "act_dup"
        ):
            if hasattr(self, attr):
                getattr(self, attr).setEnabled(enabled)
        if hasattr(self, "tb_tools"):
            self.tb_tools.setEnabled(enabled and (self.app_mode == "edit"))

    def toggle_page_view_mode(self):
        """Toggles between Single Page (page-by-page jump) and Continuous Scroll modes."""
        if self.page_view_mode == "single_page":
            self.page_view_mode = "continuous"
            if hasattr(self, "btn_page_view_mode"):
                self.btn_page_view_mode.setText("📜 연속 스크롤")
                self.btn_page_view_mode.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold;")
            if hasattr(self, "scroll_area"):
                self.scroll_area.scroll_mode = "continuous"
            self.status_bar.showMessage("📜 연속 스크롤 모드: 모든 페이지가 위아래로 연속 연결되어 매끄럽게 스크롤됩니다.")
            if self.doc and len(self.doc) > 0:
                self._switch_to_continuous_view()
        else:
            self.page_view_mode = "single_page"
            if hasattr(self, "btn_page_view_mode"):
                self.btn_page_view_mode.setText("📄 단일 페이지")
                self.btn_page_view_mode.setStyleSheet("")
            if hasattr(self, "scroll_area"):
                self.scroll_area.scroll_mode = "single_page"
            self.status_bar.showMessage("📄 단일 페이지 모드: 한 화면에 1페이지만 표시하며, 스크롤 끝에서 페이지 단위로 전환(점프)됩니다.")
            if self.doc and len(self.doc) > 0:
                self._switch_to_single_page_view()

    def _switch_to_continuous_view(self):
        if not self.doc:
            return
        self.continuous_scroll_area.continuous_canvas.is_dark_theme = self.is_dark_effective
        self.continuous_scroll_area.continuous_canvas.set_document(self.doc, self.base_pdf_bytes, self.canvas.zoom)
        self.center_stack.setCurrentIndex(3)
        if getattr(self, "_search_all_hits", None) and self._search_current_hit_idx >= 0:
            self._apply_search_hit(self._search_current_hit_idx)
        else:
            self.continuous_scroll_area.scroll_to_page(self.current_page_idx)

    def _switch_to_single_page_view(self):
        if not self.doc:
            return
        self.center_stack.setCurrentIndex(0)
        self.go_to_page(self.current_page_idx)
        if getattr(self, "_search_all_hits", None) and self._search_current_hit_idx >= 0:
            self._apply_search_hit(self._search_current_hit_idx)

    def _on_continuous_page_changed(self, page_idx: int):
        if not self.doc or page_idx < 0 or page_idx >= len(self.doc):
            return
        self.current_page_idx = page_idx
        self.page_indicator_lbl.setText(f"{page_idx + 1} / {len(self.doc)}")
        self.thumb_list.blockSignals(True)
        self.thumb_list.setCurrentRow(page_idx)
        self.thumb_list.blockSignals(False)

    def _on_continuous_page_clicked(self, page_idx: int):
        if not self.doc or page_idx < 0 or page_idx >= len(self.doc):
            return
        self.current_page_idx = page_idx
        self.page_indicator_lbl.setText(f"{page_idx + 1} / {len(self.doc)}")
        self.thumb_list.blockSignals(True)
        self.thumb_list.setCurrentRow(page_idx)
        self.thumb_list.blockSignals(False)

    def _on_continuous_page_double_clicked(self, page_idx: int):
        self.page_view_mode = "single_page"
        if hasattr(self, "btn_page_view_mode"):
            self.btn_page_view_mode.setText("📄 단일 페이지")
            self.btn_page_view_mode.setStyleSheet("")
        self.center_stack.setCurrentIndex(0)
        self.go_to_page(page_idx)
        self.switch_to_edit_mode()

    def _on_wheel_page_change_requested(self, direction: int, target_pos: str):
        """Handles smart mouse wheel page boundary navigation."""
        if not self.doc or len(self.doc) <= 1:
            return
        target_page = self.current_page_idx + direction
        if 0 <= target_page < len(self.doc):
            self.go_to_page(target_page)
            if target_pos == "top":
                QTimer.singleShot(15, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().minimum()))
            elif target_pos == "bottom":
                QTimer.singleShot(15, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))
            mode_str = "📄 페이지 단위" if self.page_view_mode == "single_page" else "📜 연속 스크롤"
            self.status_bar.showMessage(f"[{mode_str}] {target_page + 1} / {len(self.doc)} 페이지로 전환되었습니다.")

    def _confirm_discard_or_save(self, action_title: str = "프로그램 종료") -> bool:
        """
        If the current document has unsaved edits, asks the user whether to Save, Don't Save, or Cancel.
        Returns True if safe to proceed, False if the user cancelled.
        """
        if hasattr(self, "canvas"):
            self.canvas.commit_inline_edit()
        has_objs = any(len(objs) > 0 for objs in self.page_objects.values())
        if not self.is_modified and not has_objs:
            return True

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(f"변경 내용 저장 확인 ({action_title})")
        fname = os.path.basename(self.current_file_path) if self.current_file_path else "현재 문서"
        msg.setText(f"'{fname}'에 저장하지 않은 수정사항이 있습니다.\n변경 내용을 저장하시겠습니까?")
        btn_save = msg.addButton("💾 저장 (Save)", QMessageBox.ButtonRole.AcceptRole)
        btn_discard = msg.addButton("저장 안 함 (Don't Save)", QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = msg.addButton("취소 (Cancel)", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_save)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_save:
            return self.save_pdf()
        elif clicked == btn_discard:
            return True
        else:
            return False

    def closeEvent(self, event):
        # Commit any ongoing inline edit before closing
        if hasattr(self, "canvas"):
            self.canvas.commit_inline_edit()

        # Check all open tabs for unsaved modifications
        for i in range(len(self.doc_tabs) - 1, -1, -1):
            if not self._confirm_tab_close(i, action_title="프로그램 종료"):
                event.ignore()
                return
        event.accept()

    # -----------------------------------------------------------------
    # Multi-Tab Document Management & Tab Close Handling
    # -----------------------------------------------------------------
    def _confirm_tab_close(self, tab_idx: int, action_title: str = "탭 닫기") -> bool:
        """
        Confirms saving changes for tab_idx if modified.
        Returns True if safe to close, False if user cancelled.
        """
        if tab_idx < 0 or tab_idx >= len(self.doc_tabs):
            return True

        # If it's the active tab, synchronize state first
        if tab_idx == self.active_tab_idx:
            self._sync_active_tab_state()

        tab = self.doc_tabs[tab_idx]
        has_objs = any(len(objs) > 0 for objs in tab.page_objects.values())
        if not tab.is_modified and not has_objs:
            return True

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(f"변경 내용 저장 확인 ({action_title})")
        fname = os.path.basename(tab.file_path) if tab.file_path else "제목 없는 문서"
        msg.setText(f"'{fname}'에 저장하지 않은 수정사항이 있습니다.\n변경 내용을 저장하시겠습니까?")
        btn_save = msg.addButton("💾 저장 (Save)", QMessageBox.ButtonRole.AcceptRole)
        btn_discard = msg.addButton("저장 안 함 (Don't Save)", QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = msg.addButton("취소 (Cancel)", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_save)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_save:
            # Switch to this tab temporarily if needed to save
            if tab_idx != self.active_tab_idx:
                self._switch_to_tab(tab_idx)
            return self.save_pdf()
        elif clicked == btn_discard:
            return True
        else:
            return False

    def _sync_active_tab_state(self):
        """Saves current canvas and document pointers into the active DocumentTab."""
        if self.active_tab_idx < 0 or self.active_tab_idx >= len(self.doc_tabs):
            return
        tab = self.doc_tabs[self.active_tab_idx]
        tab.current_page_idx = self.current_page_idx
        tab.zoom = self.canvas.zoom if hasattr(self, "canvas") else 1.5
        tab.page_objects = copy.deepcopy(self.page_objects)
        tab.undo_stack = list(self.undo_stack)
        tab.redo_stack = list(self.redo_stack)
        tab.is_modified = self.is_modified
        tab.file_path = self.current_file_path
        tab.base_pdf_bytes = self.base_pdf_bytes
        tab.doc = self.doc

    def _on_tab_changed(self, new_idx: int):
        if self._loading_file:
            return
        if new_idx < 0 or new_idx >= len(self.doc_tabs):
            return
        if new_idx == self.active_tab_idx:
            return
        self._switch_to_tab(new_idx)

    def _switch_to_tab(self, new_idx: int):
        if hasattr(self, "canvas"):
            self.canvas.commit_inline_edit()

        if hasattr(self, "search_input"):
            self.search_input.clear()
        self._clear_search()

        # 1. Sync current active tab
        if 0 <= self.active_tab_idx < len(self.doc_tabs):
            self._sync_active_tab_state()

        # 2. Load target tab
        self.active_tab_idx = new_idx
        tab = self.doc_tabs[new_idx]
        self.current_file_path = tab.file_path
        self.base_pdf_bytes = tab.base_pdf_bytes
        self.doc = tab.doc
        self.current_page_idx = tab.current_page_idx
        self.page_objects = copy.deepcopy(tab.page_objects)
        self.undo_stack = list(tab.undo_stack)
        self.redo_stack = list(tab.redo_stack)
        self.is_modified = tab.is_modified

        if hasattr(self, "tab_bar"):
            self.tab_bar.blockSignals(True)
            self.tab_bar.setCurrentIndex(new_idx)
            self.tab_bar.blockSignals(False)

        if hasattr(self, "canvas"):
            self.canvas.zoom = tab.zoom
            if hasattr(self, "zoom_combo"):
                self.zoom_combo.blockSignals(True)
                self.zoom_combo.setCurrentText(f"{int(tab.zoom * 100)}%")
                self.zoom_combo.blockSignals(False)

        if hasattr(self, "center_stack"):
            if self.page_view_mode == "continuous":
                self.center_stack.setCurrentIndex(3)
                self.continuous_scroll_area.continuous_canvas.is_dark_theme = self.is_dark_effective
                self.continuous_scroll_area.continuous_canvas.set_document(self.doc, self.base_pdf_bytes, self.canvas.zoom)
                self.continuous_scroll_area.scroll_to_page(self.current_page_idx)
            else:
                self.center_stack.setCurrentIndex(0)
        if hasattr(self, "left_panel"):
            self.left_panel.setVisible(True)

        # 우측 속성/보기 패널은 기본이 '접기' 상태이므로, 사용자가 명시적으로 열어두지 않았다면 접힌 상태를 유지
        is_right_visible = bool(hasattr(self, "right_panel") and self.right_panel.isVisible())
        if hasattr(self, "right_panel"):
            self.right_panel.setVisible(is_right_visible)

        if hasattr(self, "main_splitter"):
            sizes = self.main_splitter.sizes()
            if len(sizes) == 3:
                total_w = sum(sizes) if sum(sizes) > 600 else max(900, self.width())
                left_w = 205
                if is_right_visible:
                    target_rw = getattr(self, "_last_right_panel_width", 345)
                    center_w = max(400, total_w - left_w - target_rw)
                    self.main_splitter.setSizes([left_w, center_w, target_rw])
                else:
                    center_w = max(400, total_w - left_w)
                    self.main_splitter.setSizes([left_w, center_w, 0])
        self._update_doc_actions_enabled(True)

        self._update_window_title()
        self._rebuild_thumbnails()
        self.go_to_page(self.current_page_idx)

        # By default when switching documents, maintain clean view mode
        self.switch_to_view_mode()
        self.status_bar.showMessage(
            f"탭 전환: {os.path.basename(self.current_file_path or '새 문서')} (총 {len(self.doc)}페이지)"
        )

    def _on_tab_close_requested(self, tab_idx: int):
        if not self._confirm_tab_close(tab_idx, action_title="탭 닫기"):
            return

        closing_tab = self.doc_tabs[tab_idx]
        self._unwatch_tab_file(closing_tab)
        if closing_tab.doc:
            try:
                closing_tab.doc.close()
            except Exception:
                pass

        self.tab_bar.blockSignals(True)
        self.tab_bar.removeTab(tab_idx)
        self.doc_tabs.pop(tab_idx)
        self.tab_bar.blockSignals(False)

        if not self.doc_tabs:
            # All tabs closed: enter Welcome / Empty screen!
            self.active_tab_idx = -1
            self.doc = None
            self.current_file_path = None
            self.page_objects.clear()
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.is_modified = False
            self.current_page_idx = 0
            if hasattr(self, "center_stack"):
                self.center_stack.setCurrentIndex(2)  # Welcome view
            if hasattr(self, "left_panel"):
                self.left_panel.setVisible(False)
            if hasattr(self, "right_panel"):
                self.right_panel.setVisible(False)
            if hasattr(self, "thumb_list"):
                self.thumb_list.clear()
            if hasattr(self, "page_indicator_lbl"):
                self.page_indicator_lbl.setText("0 / 0")
            self._update_window_title()
            self._update_doc_actions_enabled(False)
            self.status_bar.showMessage("열려 있는 모든 문서가 닫혔습니다. 새 문서를 열거나 PDF를 드래그 앤 드롭하세요.")
            return

        new_idx = min(tab_idx, len(self.doc_tabs) - 1)
        self.active_tab_idx = -1  # force full switch
        self._switch_to_tab(new_idx)

    def open_pdf_in_tab(self, path: str, make_active: bool = True) -> Optional[int]:
        """Opens a PDF file into a new tab (or activates existing if already open)."""
        # 1. If already open in an existing tab, just activate that tab!
        norm_path = os.path.abspath(path)
        for i, t in enumerate(self.doc_tabs):
            if t.file_path and os.path.abspath(t.file_path) == norm_path:
                if make_active:
                    self._switch_to_tab(i)
                return i

        try:
            with open(path, "rb") as f:
                raw_bytes = f.read()
            doc = fitz.open(stream=raw_bytes, filetype="pdf")
        except Exception as e:
            QMessageBox.critical(self, "PDF 열기 오류", f"PDF 파일을 열 수 없습니다:\n{path}\n\n오류: {e}")
            return None

        # 암호로 보호된 PDF 감지 및 사용자 인증
        if doc.needs_pass:
            ok, doc, decrypted_bytes = authenticate_doc_dialog(doc, path, parent=self)
            if not ok or doc is None:
                if hasattr(self, "status_bar"):
                    self.status_bar.showMessage("🔒 암호 입력이 취소되어 문서를 열지 않았습니다.", 4000)
                return None
            if decrypted_bytes is not None:
                raw_bytes = decrypted_bytes

        file_ino = None
        try:
            file_ino = os.stat(path).st_ino
        except Exception:
            pass

        # 2. Sync currently active tab before adding new
        if 0 <= self.active_tab_idx < len(self.doc_tabs):
            self._sync_active_tab_state()

        new_tab = DocumentTab(
            tab_id=str(uuid.uuid4())[:8],
            file_path=path,
            doc=doc,
            base_pdf_bytes=raw_bytes,
            page_objects={},
            undo_stack=[],
            redo_stack=[],
            current_page_idx=0,
            is_modified=False,
            zoom=1.5,
            file_ino=file_ino,
        )
        self.doc_tabs.append(new_tab)
        new_idx = len(self.doc_tabs) - 1
        self._watch_tab_file(new_tab)

        fname = os.path.basename(path)
        if hasattr(self, "tab_bar"):
            self.tab_bar.blockSignals(True)
            tab_title = fname if len(fname) <= 26 else (fname[:23] + "...")
            self.tab_bar.addTab(tab_title)
            self.tab_bar.setTabToolTip(new_idx, path)
            self.tab_bar.blockSignals(False)

        if make_active:
            self._switch_to_tab(new_idx)
            QTimer.singleShot(0, self.apply_smart_open_zoom)

        return new_idx

    def bring_to_front(self):
        """Brings the main window to the foreground in maximized state and gains focus."""
        try:
            self.showMaximized()
            self.raise_()
            self.activateWindow()

            if sys.platform == "win32":
                hwnd = int(self.winId())
                SW_SHOWMAXIMIZED = 3
                ctypes.windll.user32.ShowWindow(hwnd, SW_SHOWMAXIMIZED)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def handle_external_open_files(self, file_paths: List[str]):
        """
        Called when an external instance (e.g. Explorer double click or CLI) requests opening files.
        Opens them into tabs (or activates if already open) and brings this window to front.
        """
        if not file_paths:
            self.bring_to_front()
            return

        last_tab_idx = None
        for p in file_paths:
            if not p:
                continue
            cleaned = p.strip(' "\'')
            if os.path.isfile(cleaned):
                abs_p = os.path.abspath(cleaned)
                idx = self.open_pdf_in_tab(abs_p, make_active=True)
                if idx is not None:
                    last_tab_idx = idx

        if last_tab_idx is not None and 0 <= last_tab_idx < len(self.doc_tabs):
            self._switch_to_tab(last_tab_idx)

        self.bring_to_front()

    # -----------------------------------------------------------------
    # View Mode vs Edit Mode Switching
    # -----------------------------------------------------------------
    def switch_to_view_mode(self):
        """Switches the app to clean, non-intrusive View Mode (Adobe Acrobat Reader style)."""
        if hasattr(self, "canvas"):
            self.canvas.commit_inline_edit()
            self.canvas.tool_mode = "view"
            self.canvas.selected_obj = None
            self.canvas.hovered_segment = None
            self._on_canvas_object_selected(None)
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
            self.canvas.update()

        self.app_mode = "view"

        if hasattr(self, "btn_mode_view"):
            self.btn_mode_view.setChecked(True)
        if hasattr(self, "btn_mode_edit"):
            self.btn_mode_edit.setChecked(False)

        # Show View Mode Banner in inspector, collapse detailed shape/font inspector
        if hasattr(self, "view_mode_card"):
            self.view_mode_card.setVisible(True)
        if hasattr(self, "txt_inspector_group"):
            self.txt_inspector_group.setVisible(False)
        if hasattr(self, "shape_inspector_group"):
            self.shape_inspector_group.setVisible(False)
        if hasattr(self, "act_inspector_group"):
            self.act_inspector_group.setVisible(False)
        if hasattr(self, "tb_tools"):
            self.tb_tools.setEnabled(False)
            self.tb_tools.hide()

        self.status_bar.showMessage(
            "👁️ 보기 모드 (View Mode) 활성화: 깨끗한 PDF 열람 및 드래그 텍스트 복사(Ctrl+C)가 가능합니다. '📝 편집 모드' 버튼을 누르면 편집할 수 있습니다."
        )

    def switch_to_edit_mode(self):
        """Switches the app to Edit Mode, enabling in-place Korean text edits and shape tools."""
        self.app_mode = "edit"

        if hasattr(self, "btn_mode_view"):
            self.btn_mode_view.setChecked(False)
        if hasattr(self, "btn_mode_edit"):
            self.btn_mode_edit.setChecked(True)

        if hasattr(self, "tb_tools"):
            self.tb_tools.show()
            self.tb_tools.setEnabled(True)

        if hasattr(self, "view_mode_card"):
            self.view_mode_card.setVisible(False)
        if hasattr(self, "txt_inspector_group"):
            self.txt_inspector_group.setVisible(True)
        if hasattr(self, "shape_inspector_group"):
            self.shape_inspector_group.setVisible(True)
        if hasattr(self, "act_inspector_group"):
            self.act_inspector_group.setVisible(True)

        # Default edit tool: inplace_text
        self.set_tool_mode("inplace_text")
        self.status_bar.showMessage(
            "📝 편집 모드 (Edit Mode) 활성화: 수정할 글자를 드래그하거나 클릭하여 수정하세요. [Esc] 또는 상단 '👁️ 보기 모드'를 누르면 보기 모드로 돌아갑니다."
        )

    # -----------------------------------------------------------------
    # UI Construction
    # -----------------------------------------------------------------
    def _set_page_view_mode_explicit(self, target_mode: str):
        if self.page_view_mode != target_mode:
            self.toggle_page_view_mode()

    def _toggle_left_panel(self, visible: bool):
        self.toggle_left_panel(visible)

    def toggle_left_panel(self, visible: Optional[bool] = None):
        """좌측 썸네일 탐색 바를 접거나 펼치며 관련 툴바 버튼, 메뉴 및 스플리터 크기를 완벽하게 동기화합니다."""
        if not hasattr(self, "left_panel") or not hasattr(self, "main_splitter"):
            return

        if visible is None:
            visible = not self.left_panel.isVisible()

        if visible:
            # 펼치기 (Expand)
            self.left_panel.setVisible(True)
            sizes = self.main_splitter.sizes()
            target_lw = getattr(self, "_last_left_panel_width", 205)
            if target_lw < 160:
                target_lw = 205
            if len(sizes) == 3:
                cw = max(300, sizes[1] - (target_lw - sizes[0]))
                rw = sizes[2]
                self.main_splitter.setSizes([target_lw, cw, rw])
        else:
            # 접기 (Collapse)
            sizes = self.main_splitter.sizes()
            if len(sizes) == 3 and sizes[0] > 100:
                self._last_left_panel_width = sizes[0]
            self.left_panel.setVisible(False)

        # 상단 툴바 토글 버튼 상태 동기화
        if hasattr(self, "btn_toggle_left_panel"):
            self.btn_toggle_left_panel.blockSignals(True)
            self.btn_toggle_left_panel.setChecked(visible)
            if visible:
                self.btn_toggle_left_panel.setText("◧ 썸네일 접기")
                self.btn_toggle_left_panel.setToolTip("좌측 썸네일 바를 접어 본문 화면을 넓게 봅니다 (단축키: F3)")
            else:
                self.btn_toggle_left_panel.setText("◨ 썸네일 펼치기")
                self.btn_toggle_left_panel.setToolTip("접힌 좌측 썸네일 바를 다시 펼칩니다 (단축키: F3)")
            self.btn_toggle_left_panel.blockSignals(False)
            self._update_toggle_panel_btn_style()

        # 메뉴 액션 상태 동기화
        if hasattr(self, "act_toggle_left"):
            self.act_toggle_left.blockSignals(True)
            self.act_toggle_left.setChecked(visible)
            self.act_toggle_left.blockSignals(False)

    def _toggle_right_panel(self, visible: bool):
        self.toggle_right_panel(visible)

    def toggle_right_panel(self, visible: Optional[bool] = None):
        """우측 속성/보기 패널을 접거나 펼치며 관련 툴바 버튼, 메뉴 및 스플리터 크기를 완벽하게 동기화합니다."""
        if not hasattr(self, "right_panel") or not hasattr(self, "main_splitter"):
            return

        if visible is None:
            visible = not self.right_panel.isVisible()

        if visible:
            # 펼치기 (Expand)
            self.right_panel.setVisible(True)
            sizes = self.main_splitter.sizes()
            target_rw = getattr(self, "_last_right_panel_width", 355)
            if target_rw < 280:
                target_rw = 355
            if len(sizes) == 3:
                lw = sizes[0]
                cw = max(300, sizes[1] - (target_rw - sizes[2]))
                self.main_splitter.setSizes([lw, cw, target_rw])
        else:
            # 접기 (Collapse)
            sizes = self.main_splitter.sizes()
            if len(sizes) == 3 and sizes[2] > 100:
                self._last_right_panel_width = sizes[2]
            self.right_panel.setVisible(False)

        # 상단 툴바 옵션 버튼 상태 동기화
        if hasattr(self, "btn_toggle_right_panel"):
            self.btn_toggle_right_panel.blockSignals(True)
            self.btn_toggle_right_panel.setChecked(visible)
            if visible:
                self.btn_toggle_right_panel.setText("◨ 속성 패널 접기")
                self.btn_toggle_right_panel.setToolTip("우측 속성/도형 패널을 접어 본문 화면을 넓게 봅니다 (단축키: F4)")
            else:
                self.btn_toggle_right_panel.setText("◧ 속성 패널 펼치기")
                self.btn_toggle_right_panel.setToolTip("접힌 우측 속성/도형 패널을 다시 펼칩니다 (단축키: F4)")
            self.btn_toggle_right_panel.blockSignals(False)
            self._update_toggle_panel_btn_style()

        # 메뉴 액션 상태 동기화
        if hasattr(self, "act_toggle_right"):
            self.act_toggle_right.blockSignals(True)
            self.act_toggle_right.setChecked(visible)
            self.act_toggle_right.blockSignals(False)

    def _update_toggle_panel_btn_style(self):
        """테마 및 좌/우 패널 개폐 상태에 따라 상단 툴바 토글 버튼의 스타일을 갱신합니다."""
        is_dark = getattr(self, "is_dark_effective", False)

        # 1. Left Thumbnail Panel Toggle Button
        if hasattr(self, "btn_toggle_left_panel"):
            is_open_left = self.left_panel.isVisible() if hasattr(self, "left_panel") else True
            if is_open_left:
                if is_dark:
                    self.btn_toggle_left_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #374151;
                            color: #E5E7EB;
                            border: 1px solid #4B5563;
                            border-radius: 4px;
                            padding: 3px 8px;
                            font-weight: 500;
                        }
                        QPushButton:hover {
                            background-color: #4B5563;
                            color: #FFFFFF;
                        }
                    """)
                else:
                    self.btn_toggle_left_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #F1F5F9;
                            color: #1E293B;
                            border: 1px solid #CBD5E1;
                            border-radius: 4px;
                            padding: 3px 8px;
                            font-weight: 500;
                        }
                        QPushButton:hover {
                            background-color: #E2E8F0;
                            color: #0F172A;
                        }
                    """)
            else:
                if is_dark:
                    self.btn_toggle_left_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #1E3A8A;
                            color: #93C5FD;
                            border: 1.5px solid #3B82F6;
                            border-radius: 4px;
                            padding: 3px 8px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #2563EB;
                            color: #FFFFFF;
                        }
                    """)
                else:
                    self.btn_toggle_left_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #EFF6FF;
                            color: #1D4ED8;
                            border: 1.5px solid #3B82F6;
                            border-radius: 4px;
                            padding: 3px 8px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #DBEAFE;
                            color: #1E40AF;
                        }
                    """)

        # 2. Right Inspector Panel Toggle Button
        if hasattr(self, "btn_toggle_right_panel"):
            is_open_right = self.right_panel.isVisible() if hasattr(self, "right_panel") else True
            if is_open_right:
                if is_dark:
                    self.btn_toggle_right_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #374151;
                            color: #E5E7EB;
                            border: 1px solid #4B5563;
                            border-radius: 4px;
                            padding: 3px 8px;
                            font-weight: 500;
                        }
                        QPushButton:hover {
                            background-color: #4B5563;
                            color: #FFFFFF;
                        }
                    """)
                else:
                    self.btn_toggle_right_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #F1F5F9;
                            color: #1E293B;
                            border: 1px solid #CBD5E1;
                            border-radius: 4px;
                            padding: 3px 8px;
                            font-weight: 500;
                        }
                        QPushButton:hover {
                            background-color: #E2E8F0;
                            color: #0F172A;
                        }
                    """)
            else:
                # 접혀있을 때는 눈에 띄게 강조 (원클릭으로 다시 펼칠 수 있도록 안내)
                if is_dark:
                    self.btn_toggle_right_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #1E3A8A;
                            color: #93C5FD;
                            border: 1.5px solid #3B82F6;
                            border-radius: 4px;
                            padding: 3px 8px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #2563EB;
                            color: #FFFFFF;
                        }
                    """)
                else:
                    self.btn_toggle_right_panel.setStyleSheet("""
                        QPushButton {
                            background-color: #EFF6FF;
                            color: #1D4ED8;
                            border: 1.5px solid #3B82F6;
                            border-radius: 4px;
                            padding: 3px 8px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #DBEAFE;
                            color: #1E40AF;
                        }
                    """)

    def _select_tool_and_enter_edit(self, mode_id: str):
        self.switch_to_edit_mode()
        self.set_tool_mode(mode_id)
        if hasattr(self, "tool_buttons") and mode_id in self.tool_buttons:
            self.tool_buttons[mode_id].setChecked(True)

    def _set_theme_mode(self, mode: str):
        if hasattr(self, "theme_combo"):
            idx = self.theme_combo.findData(mode)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
        else:
            self._apply_theme(mode)

    def _focus_search(self):
        if hasattr(self, "search_input"):
            self.search_input.setFocus()
            self.search_input.selectAll()

    def _show_shortcuts_dialog(self):
        msg = (
            "<h3>K-PDF Studio 핵심 단축키</h3>"
            "<table cellpadding='4'>"
            "<tr><td><b>Ctrl + N</b></td><td>새 빈 PDF 문서 생성</td></tr>"
            "<tr><td><b>Ctrl + O</b></td><td>기존 PDF 파일 열기</td></tr>"
            "<tr><td><b>Ctrl + S</b></td><td>문서 저장 (편집 내용 커밋)</td></tr>"
            "<tr><td><b>Ctrl + Shift + S</b></td><td>다른 이름으로 저장</td></tr>"
            "<tr><td><b>Ctrl + P</b></td><td>Acrobat 스타일 인쇄 대화상자</td></tr>"
            "<tr><td><b>Ctrl + D</b></td><td>문서 속성 (설명/보안/글꼴 전수 분석)</td></tr>"
            "<tr><td><b>Ctrl + W</b></td><td>현재 탭 닫기</td></tr>"
            "<tr><td><b>Ctrl + Z / Y</b></td><td>실행 취소 / 다시 실행</td></tr>"
            "<tr><td><b>Ctrl + J</b></td><td>선택한 텍스트 또는 도형 객체 복제</td></tr>"
            "<tr><td><b>Ctrl + E</b></td><td>편집 모드 전환 (텍스트/도형 편집)</td></tr>"
            "<tr><td><b>Esc</b></td><td>깨끗한 보기 모드로 복귀 / 바둑판 닫기</td></tr>"
            "<tr><td><b>Ctrl + F / F3</b></td><td>본문 검색 / 다음 검색 결과</td></tr>"
            "<tr><td><b>[ / ] (또는 Alt+좌/우)</b></td><td>같은 폴더의 이전/다음 PDF 파일로 이동</td></tr>"
            "<tr><td><b>Ctrl + 휠</b></td><td>화면 확대 / 축소</td></tr>"
            "<tr><td><b>Delete</b></td><td>선택한 도형 또는 페이지 삭제</td></tr>"
            "</table>"
        )
        QMessageBox.information(self, "단축키 안내", msg)

    def _show_about_dialog(self):
        msg = (
            "<h3>K-PDF Studio</h3>"
            "<b>한글 특화 고성능 데스크톱 PDF 스튜디오</b><br>"
            "버전: 1.0 (Desktop Edition)<br><br>"
            "• 한국어 부분 블록 인플레이스 텍스트 편집 & 실시간 폰트 임베딩<br>"
            "• Windows 설치 전체 글꼴(404종) 및 TTC 서브페이스 자동 추출<br>"
            "• 자유 도형 8방향 리사이즈 핸들 및 더블클릭 상세 편집<br>"
            "• Win32 GDI 네이티브 인쇄 & 프린터 드라이버 직접 연동<br>"
            "• 단일 페이지 점프 모드 & 매끄러운 연속 스크롤 뷰 지원<br>"
        )
        QMessageBox.about(self, "K-PDF Studio 정보", msg)

    def _build_menu_bar(self):
        menubar = self.menuBar()

        # -------------------------------------------------------------
        # 1. 파일 (File)
        # -------------------------------------------------------------
        menu_file = menubar.addMenu("파일(&F)")

        self.act_new = menu_file.addAction("➕ 새 빈 PDF 문서")
        self.act_new.setShortcut(QKeySequence("Ctrl+N"))
        self.act_new.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_new.setStatusTip("A4 규격의 깨끗한 새 빈 PDF 문서를 생성합니다.")
        self.act_new.triggered.connect(self.create_blank_pdf)

        self.act_open = menu_file.addAction("📂 파일 열기...")
        self.act_open.setShortcut(QKeySequence("Ctrl+O"))
        self.act_open.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_open.setStatusTip("기존 PDF 파일을 엽니다.")
        self.act_open.triggered.connect(self.open_file_dialog)

        self.act_prev_pdf = menu_file.addAction("◀ 이전 PDF 열기")
        self.act_prev_pdf.setShortcut(QKeySequence("Alt+Left"))
        self.act_prev_pdf.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_prev_pdf.setStatusTip("같은 폴더 내의 이전 PDF 파일로 이동합니다 (단축키: Alt+Left 또는 [ ).")
        self.act_prev_pdf.triggered.connect(lambda: self.navigate_sibling_pdf(-1))

        self.act_next_pdf = menu_file.addAction("▶ 다음 PDF 열기")
        self.act_next_pdf.setShortcut(QKeySequence("Alt+Right"))
        self.act_next_pdf.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_next_pdf.setStatusTip("같은 폴더 내의 다음 PDF 파일로 이동합니다 (단축키: Alt+Right 또는 ] ).")
        self.act_next_pdf.triggered.connect(lambda: self.navigate_sibling_pdf(1))

        menu_file.addSeparator()

        self.act_save = menu_file.addAction("💾 저장")
        self.act_save.setShortcut(QKeySequence("Ctrl+S"))
        self.act_save.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_save.setStatusTip("현재 문서의 모든 편집 사항을 저장합니다.")
        self.act_save.triggered.connect(self.save_pdf)

        self.act_save_as = menu_file.addAction("💾 다른 이름으로 저장...")
        self.act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.act_save_as.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_save_as.setStatusTip("문서를 다른 파일명이나 위치로 저장합니다.")
        self.act_save_as.triggered.connect(self.save_pdf_as)

        self.act_rename = menu_file.addAction("✏️ 파일명 바꾸기 (F2)...")
        self.act_rename.setShortcut(QKeySequence("F2"))
        self.act_rename.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_rename.setStatusTip("현재 PDF 파일의 이름을 변경합니다 (단축키: F2).")
        self.act_rename.triggered.connect(self.rename_current_file)

        menu_file.addSeparator()

        self.act_merge = menu_file.addAction("📑 PDF / 이미지 파일 합치기(병합)...")
        self.act_merge.setStatusTip("여러 PDF 파일 및 이미지(JPG, PNG 등)들을 하나의 PDF 문서로 병합합니다.")
        self.act_merge.triggered.connect(self.open_merge_dialog)

        self.act_export_images = menu_file.addAction("🖼️ 고화질 이미지로 내보내기 (PDF ➔ JPG/PNG)...")
        self.act_export_images.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self.act_export_images.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_export_images.setStatusTip("PDF 문서를 300 DPI 등의 고화질 JPG 또는 PNG 이미지로 일괄 변환하여 저장합니다.")
        self.act_export_images.triggered.connect(self.export_current_pdf_to_images)

        self.act_pptx_to_pdf = menu_file.addAction("📊 PPTX ➔ 고화질 PDF 변환...")
        self.act_pptx_to_pdf.setStatusTip("파워포인트(.pptx, .ppt) 문서를 글꼴 손실 없이 원본 그대로 선명한 고화질 PDF로 변환합니다.")
        self.act_pptx_to_pdf.triggered.connect(self.open_pptx_to_pdf_dialog)

        self.act_print = menu_file.addAction("🖨️ 인쇄...")
        self.act_print.setShortcut(QKeySequence("Ctrl+P"))
        self.act_print.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_print.setStatusTip("Acrobat 스타일 인쇄 대화상자를 엽니다.")
        self.act_print.triggered.connect(self.print_pdf)

        self.act_doc_props = menu_file.addAction("ℹ️ 문서 속성...")
        self.act_doc_props.setShortcut(QKeySequence("Ctrl+D"))
        self.act_doc_props.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_doc_props.setStatusTip("문서의 설명, 보안 설정, 사용된 글꼴 목록을 확인하고 편집합니다.")
        self.act_doc_props.triggered.connect(self.open_document_properties)

        menu_file.addSeparator()

        self.act_close_tab = menu_file.addAction("✕ 현재 탭 닫기")
        self.act_close_tab.setShortcut(QKeySequence("Ctrl+W"))
        self.act_close_tab.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_close_tab.setStatusTip("현재 열려 있는 문서 탭을 닫습니다.")
        self.act_close_tab.triggered.connect(lambda: self._on_tab_close_requested(self.active_tab_idx) if self.active_tab_idx >= 0 else None)

        act_exit = menu_file.addAction("⏻ 프로그램 종료")
        act_exit.setShortcut(QKeySequence("Alt+F4"))
        act_exit.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        act_exit.setStatusTip("K-PDF Studio를 종료합니다.")
        act_exit.triggered.connect(self.close)

        # -------------------------------------------------------------
        # 2. 편집 (Edit)
        # -------------------------------------------------------------
        menu_edit = menubar.addMenu("편집(&E)")

        self.act_undo = menu_edit.addAction("↩ 실행 취소")
        self.act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.act_undo.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_undo.setStatusTip("이전 작업을 되돌립니다.")
        self.act_undo.triggered.connect(self.undo)

        self.act_redo = menu_edit.addAction("↪ 다시 실행")
        self.act_redo.setShortcut(QKeySequence("Ctrl+Y"))
        self.act_redo.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_redo.setStatusTip("되돌린 작업을 다시 실행합니다.")
        self.act_redo.triggered.connect(self.redo)

        self.act_dup = menu_edit.addAction("📑 선택 객체 복제")
        self.act_dup.setShortcut(QKeySequence("Ctrl+J"))
        self.act_dup.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_dup.setStatusTip("선택한 텍스트 또는 도형 객체를 복제합니다.")
        self.act_dup.triggered.connect(self.duplicate_selected_object)

        menu_edit.addSeparator()

        act_mode_view = menu_edit.addAction("👁️ 보기 모드로 전환")
        act_mode_view.setShortcut(QKeySequence("Esc"))
        act_mode_view.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        act_mode_view.setStatusTip("본문 선택 및 깨끗한 읽기 모드로 전환합니다. (페이지 구성 시 닫기)")
        act_mode_view.triggered.connect(self._on_global_escape_pressed)

        act_mode_edit = menu_edit.addAction("📝 편집 모드로 전환")
        act_mode_edit.setShortcut(QKeySequence("Ctrl+E"))
        act_mode_edit.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        act_mode_edit.setStatusTip("본문 텍스트 수정 및 도형 추가 편집 모드로 전환합니다.")
        act_mode_edit.triggered.connect(self.switch_to_edit_mode)

        menu_edit.addSeparator()

        act_search = menu_edit.addAction("🔍 본문 검색...")
        act_search.setShortcut(QKeySequence("Ctrl+F"))
        act_search.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        act_search.setStatusTip("본문에서 단어 또는 한글 문구를 검색합니다.")
        act_search.triggered.connect(self._focus_search)

        act_search_next = menu_edit.addAction("🔍 다음 찾기")
        act_search_next.setShortcut(QKeySequence("Ctrl+G"))
        act_search_next.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        act_search_next.setStatusTip("다음 검색 결과를 찾습니다 (단축키: Ctrl+G).")
        act_search_next.triggered.connect(self.next_search_hit)

        # -------------------------------------------------------------
        # 3. 보기 (View)
        # -------------------------------------------------------------
        menu_view = menubar.addMenu("보기(&V)")

        act_view_single = menu_view.addAction("📄 단일 페이지 모드 (페이지 단위 점프)")
        act_view_single.setStatusTip("한 화면에 1페이지만 표시하며, 스크롤 끝에서 페이지 단위로 전환합니다.")
        act_view_single.triggered.connect(lambda: self._set_page_view_mode_explicit("single_page"))

        act_view_cont = menu_view.addAction("📜 연속 스크롤 모드 (상하 연속 스크롤)")
        act_view_cont.setStatusTip("모든 페이지가 상하로 연속 연결되어 매끄럽게 스크롤됩니다.")
        act_view_cont.triggered.connect(lambda: self._set_page_view_mode_explicit("continuous"))

        menu_view.addSeparator()

        self.act_prev_page = menu_view.addAction("◀ 이전 페이지\tPgUp")
        self.act_prev_page.setStatusTip("이전 페이지로 이동합니다 (단축키: Page Up).")
        self.act_prev_page.triggered.connect(self.prev_page)

        self.act_next_page = menu_view.addAction("▶ 다음 페이지\tPgDn")
        self.act_next_page.setStatusTip("다음 페이지로 이동합니다 (단축키: Page Down).")
        self.act_next_page.triggered.connect(self.next_page)

        menu_view.addSeparator()

        self.act_org_pages = menu_view.addAction("📑 대화면 페이지 구성 (Organize Pages)")
        self.act_org_pages.setStatusTip("Acrobat 스타일의 대화면 바둑판 배열로 페이지 순서 변경 및 관리를 수행합니다.")
        self.act_org_pages.triggered.connect(lambda: self.toggle_organize_pages())

        menu_view.addSeparator()

        act_zoom_in = menu_view.addAction("＋ 확대")
        act_zoom_in.setShortcut(QKeySequence("Ctrl+="))
        act_zoom_in.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        act_zoom_in.triggered.connect(lambda: self.step_zoom(1))

        act_zoom_out = menu_view.addAction("－ 축소")
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        act_zoom_out.triggered.connect(lambda: self.step_zoom(-1))

        act_fit_w = menu_view.addAction("↔ 창 폭 맞춤")
        act_fit_w.triggered.connect(self.fit_to_width)

        act_fit_h = menu_view.addAction("↕ 창 높이 맞춤")
        act_fit_h.triggered.connect(self.fit_to_height)

        act_fit_p = menu_view.addAction("🗖 전체 화면 맞춤")
        act_fit_p.triggered.connect(self.fit_to_page)

        menu_view.addSeparator()

        self.act_toggle_left = menu_view.addAction("🗂️ 좌측 썸네일 바 표시 (F3)")
        self.act_toggle_left.setCheckable(True)
        self.act_toggle_left.setChecked(True)
        self.act_toggle_left.setShortcut(QKeySequence("F3"))
        self.act_toggle_left.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_toggle_left.setStatusTip("좌측 페이지 썸네일 탐색 바를 접거나 펼칩니다 (단축키: F3).")
        self.act_toggle_left.triggered.connect(self.toggle_left_panel)

        self.act_toggle_right = menu_view.addAction("🎛️ 우측 속성/도형 패널 표시 (F4)")
        self.act_toggle_right.setCheckable(True)
        self.act_toggle_right.setChecked(False)
        self.act_toggle_right.setShortcut(QKeySequence("F4"))
        self.act_toggle_right.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.act_toggle_right.setStatusTip("우측 속성 및 도형/보기 패널을 접거나 펼칩니다 (단축키: F4).")
        self.act_toggle_right.triggered.connect(self.toggle_right_panel)

        # -------------------------------------------------------------
        # 4. 도구 (Tools)
        # -------------------------------------------------------------
        menu_tools = menubar.addMenu("도구(&T)")

        tool_items = [
            ("inplace_text", "🔤 기존 텍스트 부분 편집", "원하는 단어나 문구만 마우스로 드래그/클릭하여 수정합니다."),
            ("free_text", "➕ 새 한글 텍스트 상자 추가", "원하는 위치를 클릭하여 새 텍스트를 작성합니다."),
            ("select", "🖱️ 객체 선택 / 이동 / 크기조절", "추가한 텍스트나 도형을 선택하여 이동/크기조절합니다."),
            ("rect", "▭ 사각형 그리기", "마우스 드래그로 사각형을 그립니다."),
            ("ellipse", "◯ 원 / 타원 그리기", "마우스 드래그로 원이나 타원을 그립니다."),
            ("line", "╱ 직선 그리기", "마우스 드래그로 직선을 그립니다."),
            ("arrow", "➔ 화살표 그리기", "마우스 드래그로 화살표를 그립니다."),
            ("highlight", "🖍️ 형광펜 하이라이트", "마우스 드래그로 반투명 형광펜을 칠합니다."),
            ("eraser", "🧹 영역 지우개 (화이트아웃)", "원래 파일의 글자, 로고, 그림, 표 등을 마우스로 덮어 지웁니다."),
        ]
        for tid, tname, ttip in tool_items:
            act = menu_tools.addAction(tname)
            act.setStatusTip(ttip)
            act.triggered.connect(lambda checked, m=tid: self._select_tool_and_enter_edit(m))

        menu_tools.addSeparator()

        act_rot_l = menu_tools.addAction("↺ 현재 페이지 90° 좌회전")
        act_rot_l.triggered.connect(lambda: self.rotate_current_page(-90))

        act_rot_r = menu_tools.addAction("↻ 현재 페이지 90° 우회전")
        act_rot_r.triggered.connect(lambda: self.rotate_current_page(90))

        act_new_p = menu_tools.addAction("📄+ 빈 페이지 삽입")
        act_new_p.triggered.connect(self.insert_blank_page)

        menu_tools.addSeparator()
        act_refresh_fonts = menu_tools.addAction("🔄 PC 설치 글꼴 새로고침 (Re-scan Fonts)")
        act_refresh_fonts.setToolTip("윈도우에 새로 설치된 글꼴을 즉시 다시 스캔하여 목록에 반영합니다.")
        act_refresh_fonts.triggered.connect(self.refresh_fonts_and_ui)

        # -------------------------------------------------------------
        # 5. 테마 (Theme)
        # -------------------------------------------------------------
        menu_theme = menubar.addMenu("테마(&S)")

        act_th_sys = menu_theme.addAction("🖥️ 윈도우 시스템 기본")
        act_th_sys.triggered.connect(lambda: self._set_theme_mode("system"))

        act_th_light = menu_theme.addAction("☀️ 밝게 (Light)")
        act_th_light.triggered.connect(lambda: self._set_theme_mode("light"))

        act_th_dark = menu_theme.addAction("🌙 어두운 테마 (Dark)")
        act_th_dark.triggered.connect(lambda: self._set_theme_mode("dark"))

        # -------------------------------------------------------------
        # 6. 도움말 (Help)
        # -------------------------------------------------------------
        menu_help = menubar.addMenu("도움말(&H)")

        act_shortcuts = menu_help.addAction("⌨️ 단축키 안내...")
        act_shortcuts.triggered.connect(self._show_shortcuts_dialog)

        act_about = menu_help.addAction("ℹ️ K-PDF Studio 정보...")
        act_about.triggered.connect(self._show_about_dialog)

    # -----------------------------------------------------------------
    # UI Construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        # 1. Build Top Menu Bar (파일 | 편집 | 보기 | 도구 | 테마 | 도움말)
        self._build_menu_bar()

        # 2. Build Modern Quick Action Toolbar
        tb_main = QToolBar("메인 빠른 실행 도구 모음")
        tb_main.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb_main)

        # Mode Selector (보기 모드 vs 편집 모드)
        self.btn_mode_view = QPushButton("👁️ 보기 모드")
        self.btn_mode_view.setCheckable(True)
        self.btn_mode_view.setChecked(True)
        self.btn_mode_view.setToolTip("깨끗한 PDF 열람 및 텍스트 선택 복사(Ctrl+C) 모드")
        self.btn_mode_view.setStyleSheet("""
            QPushButton:checked {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                border: 2px solid #93C5FD;
            }
        """)
        self.btn_mode_view.clicked.connect(self.switch_to_view_mode)
        tb_main.addWidget(self.btn_mode_view)

        self.btn_mode_edit = QPushButton("📝 편집 모드")
        self.btn_mode_edit.setCheckable(True)
        self.btn_mode_edit.setChecked(False)
        self.btn_mode_edit.setToolTip("기존 본문 텍스트 수정, 새 텍스트 상자 추가, 도형 그리기 모드")
        self.btn_mode_edit.setStyleSheet("""
            QPushButton:checked {
                background-color: #D97706;
                color: #FFFFFF;
                font-weight: bold;
                border: 2px solid #FCD34D;
            }
        """)
        self.btn_mode_edit.clicked.connect(self.switch_to_edit_mode)
        tb_main.addWidget(self.btn_mode_edit)

        tb_main.addSeparator()

        # Left Panel Toggle Option Button (Collapsible / Expandable)
        self.btn_toggle_left_panel = QPushButton("◧ 썸네일 접기")
        self.btn_toggle_left_panel.setCheckable(True)
        self.btn_toggle_left_panel.setChecked(True)
        self.btn_toggle_left_panel.setToolTip("좌측 페이지 썸네일 바를 접거나 펼칩니다 (단축키: F3)")
        self.btn_toggle_left_panel.clicked.connect(lambda: self.toggle_left_panel())
        tb_main.addWidget(self.btn_toggle_left_panel)

        self.btn_organize_pages = QPushButton("📑 페이지 구성")
        self.btn_organize_pages.setToolTip("Acrobat 스타일의 전체 화면 바둑판으로 페이지 순서 변경, 회전, 삭제, 추출을 편리하게 수행합니다")
        self.btn_organize_pages.setStyleSheet("background-color: #2563EB; color: white; border-color: #60A5FA; font-weight: bold;")
        self.btn_organize_pages.clicked.connect(lambda: self.toggle_organize_pages())
        tb_main.addWidget(self.btn_organize_pages)

        tb_main.addSeparator()

        self.btn_undo = QPushButton("↩")
        self.btn_undo.setToolTip("실행 취소 (Ctrl+Z)")
        self.btn_undo.clicked.connect(self.undo)
        tb_main.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("↪")
        self.btn_redo.setToolTip("다시 실행 (Ctrl+Y)")
        self.btn_redo.clicked.connect(self.redo)
        tb_main.addWidget(self.btn_redo)

        tb_main.addSeparator()

        self.btn_zoom_out = QPushButton("－")
        self.btn_zoom_out.setFixedWidth(28)
        self.btn_zoom_out.setToolTip("화면 축소 (Ctrl+-)")
        self.btn_zoom_out.clicked.connect(lambda: self.step_zoom(-1))
        tb_main.addWidget(self.btn_zoom_out)

        self.zoom_combo = QComboBox()
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setView(QListView())
        for z in ["50%", "75%", "100%", "125%", "150%", "200%", "250%", "300%"]:
            self.zoom_combo.addItem(z)
        self.zoom_combo.setCurrentText("폭 맞춤")
        self.zoom_combo.currentTextChanged.connect(self._on_zoom_combo_changed)
        tb_main.addWidget(self.zoom_combo)

        self.btn_zoom_in = QPushButton("＋")
        self.btn_zoom_in.setFixedWidth(28)
        self.btn_zoom_in.setToolTip("화면 확대 (Ctrl++)")
        self.btn_zoom_in.clicked.connect(lambda: self.step_zoom(1))
        tb_main.addWidget(self.btn_zoom_in)

        self.btn_fit_w = QPushButton("↔ 폭 맞춤")
        self.btn_fit_w.setToolTip("창 너비에 맞춰 문서 크기를 조절합니다")
        self.btn_fit_w.clicked.connect(self.fit_to_width)
        tb_main.addWidget(self.btn_fit_w)

        self.btn_fit_h = QPushButton("↕ 높이 맞춤")
        self.btn_fit_h.setToolTip("창 높이에 맞춰 문서 크기를 조절합니다")
        self.btn_fit_h.clicked.connect(self.fit_to_height)

        self.btn_fit_page = QPushButton("🗖 전체")
        self.btn_fit_page.setToolTip("한 화면에 페이지 전체가 다 보이도록 조절합니다")
        self.btn_fit_page.clicked.connect(self.fit_to_page)
        tb_main.addWidget(self.btn_fit_page)

        tb_main.addSeparator()

        self.btn_page_view_mode = QPushButton("📜 연속 스크롤")
        self.btn_page_view_mode.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold;")
        self.btn_page_view_mode.setToolTip("페이지 표시 모드: 클릭하여 '📜 연속 스크롤 (부드러운 스크롤)'과 '📄 단일 페이지 (페이지 단위 넘김)'을 전환합니다")
        self.btn_page_view_mode.clicked.connect(self.toggle_page_view_mode)
        tb_main.addWidget(self.btn_page_view_mode)

        tb_main.addSeparator()

        # Image Viewer Style Sibling PDF Navigation
        self.btn_prev_pdf = QPushButton("◀ 이전")
        self.btn_prev_pdf.setToolTip("같은 폴더의 이전 PDF 파일로 이동 (Alt+Left 또는 [ )")
        self.btn_prev_pdf.clicked.connect(lambda: self.navigate_sibling_pdf(-1))
        tb_main.addWidget(self.btn_prev_pdf)

        self.btn_next_pdf = QPushButton("다음 ▶")
        self.btn_next_pdf.setToolTip("같은 폴더의 다음 PDF 파일로 이동 (Alt+Right 또는 ] )")
        self.btn_next_pdf.clicked.connect(lambda: self.navigate_sibling_pdf(1))
        tb_main.addWidget(self.btn_next_pdf)

        self.btn_rename_pdf = QPushButton("✏️ 이름 변경")
        self.btn_rename_pdf.setToolTip("현재 PDF 파일명 변경 (단축키: F2)")
        self.btn_rename_pdf.clicked.connect(self.rename_current_file)
        tb_main.addWidget(self.btn_rename_pdf)

        # Right-Align Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb_main.addWidget(spacer)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 본문 검색...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(145)
        self.search_input.setToolTip("본문 검색 (Enter: 검색/다음, Esc: 초기화, ✕: 지우기)")
        self.search_input.returnPressed.connect(self.run_search)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        for act in self.search_input.findChildren(QAction):
            act.setToolTip("검색 내용 및 하이라이트 지우기 (Esc)")
        tb_main.addWidget(self.search_input)

        btn_search_next = QPushButton("찾기")
        btn_search_next.setFixedWidth(42)
        btn_search_next.setToolTip("다음 일치 검색어로 이동합니다 (Ctrl+G / F3)")
        btn_search_next.clicked.connect(self.next_search_hit)
        tb_main.addWidget(btn_search_next)

        tb_main.addSeparator()

        # Theme Selector (윈도우 기본 / 밝게 / 어둡게)
        tb_main.addWidget(QLabel("🎨"))
        self.theme_combo = QComboBox()
        self.theme_combo.setView(QListView())
        self.theme_combo.addItem("🖥️ 시스템", "system")
        self.theme_combo.addItem("☀️ 밝게", "light")
        self.theme_combo.addItem("🌙 어둡게", "dark")
        t_idx = self.theme_combo.findData(self.theme_mode)
        if t_idx >= 0:
            self.theme_combo.setCurrentIndex(t_idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)
        tb_main.addWidget(self.theme_combo)

        tb_main.addSeparator()

        # Right Panel Toggle Option Button (Collapsible / Expandable)
        self.btn_toggle_right_panel = QPushButton("◧ 속성 패널 펼치기")
        self.btn_toggle_right_panel.setCheckable(True)
        self.btn_toggle_right_panel.setChecked(False)
        self.btn_toggle_right_panel.setToolTip("접힌 우측 속성/도형 패널을 다시 펼칩니다 (단축키: F4)")
        self.btn_toggle_right_panel.clicked.connect(lambda: self.toggle_right_panel())
        tb_main.addWidget(self.btn_toggle_right_panel)
        self._update_toggle_panel_btn_style()

        # Ensure right margin so theme selector never clips at window border
        if tb_main.layout():
            tb_main.layout().setContentsMargins(4, 2, 8, 2)

        # Top Toolbar 2: Editing Tools
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self.tb_tools = QToolBar("한글 텍스트 및 도형 편집 도구")
        self.tb_tools.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.tb_tools)

        self.tool_btn_group = QButtonGroup(self)
        self.tool_btn_group.setExclusive(True)

        tools_spec = [
            (
                "inplace_text",
                "🔤 기존 텍스트 편집",
                "원하는 단어나 문구만 마우스로 드래그하거나 클릭하여 부분 블록만 수정합니다. (단어 드래그 / 부분 수정)",
            ),
            ("free_text", "➕ 새 텍스트 상자", "원하는 위치를 클릭하여 새 한글 텍스트 상자를 추가합니다."),
            ("select", "🖱️ 객체 선택 / 이동", "추가한 텍스트나 도형을 선택하여 이동하거나 크기를 조절합니다."),
            ("rect", "▭ 사각형", "마우스 드래그로 사각형을 그립니다. (기존 도형 클릭 시 선택/재편집, 더블클릭 시 상세 편집)"),
            ("ellipse", "◯ 원 / 타원", "마우스 드래그로 원 또는 타원을 그립니다. (기존 도형 클릭 시 선택/재편집, 더블클릭 시 상세 편집)"),
            ("line", "╱ 직선", "마우스 드래그로 직선을 그립니다. (기존 도형 클릭 시 선택/재편집, 더블클릭 시 상세 편집)"),
            ("arrow", "➔ 화살표", "마우스 드래그로 화살표를 그립니다. (기존 도형 클릭 시 선택/재편집, 더블클릭 시 상세 편집)"),
            ("highlight", "🖍️ 형광펜", "마우스 드래그로 반투명 형광펜 영역을 표시합니다."),
            ("eraser", "🧹 지우개", "원래 파일에 있던 본문 글자, 이미지, 표, 로고 등을 마우스 드래그로 깨끗하게 지웁니다 (화이트아웃)."),
        ]

        self.tool_buttons: Dict[str, QPushButton] = {}
        for mode_id, label, tip in tools_spec:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setToolTip(tip)
            if mode_id == "inplace_text":
                b.setChecked(True)
            b.clicked.connect(lambda checked, m=mode_id: self.set_tool_mode(m))
            self.tool_btn_group.addButton(b)
            self.tb_tools.addWidget(b)
            self.tool_buttons[mode_id] = b

        self.tb_tools.addSeparator()

        btn_rot_l = QPushButton("↺ 좌회전")
        btn_rot_l.clicked.connect(lambda: self.rotate_current_page(-90))
        self.tb_tools.addWidget(btn_rot_l)

        btn_rot_r = QPushButton("↻ 우회전")
        btn_rot_r.clicked.connect(lambda: self.rotate_current_page(90))
        self.tb_tools.addWidget(btn_rot_r)

        btn_new_page = QPushButton("📄+ 빈 페이지 삽입")
        btn_new_page.clicked.connect(self.insert_blank_page)
        self.tb_tools.addWidget(btn_new_page)

        btn_del_page = QPushButton("🗑️ 페이지 삭제")
        btn_del_page.clicked.connect(self.delete_current_page)
        self.tb_tools.addWidget(btn_del_page)

        # 3rd row toolbar is hidden by default in View Mode (only shown in Edit Mode)
        self.tb_tools.hide()

        # Central Layout: Tab Bar on top + Splitter below
        central_container = QWidget()
        central_vlayout = QVBoxLayout(central_container)
        central_vlayout.setContentsMargins(0, 0, 0, 0)
        central_vlayout.setSpacing(0)
        self.setCentralWidget(central_container)

        # Document Tab Bar (Acrobat-style Tabbed Document Interface)
        tab_header_widget = QWidget()
        tab_header_layout = QHBoxLayout(tab_header_widget)
        tab_header_layout.setContentsMargins(6, 2, 6, 0)
        tab_header_layout.setSpacing(4)

        self.tab_bar = QTabBar()
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setMovable(True)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDrawBase(False)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)
        tab_header_layout.addWidget(self.tab_bar, 1)

        btn_new_tab = QPushButton("➕")
        btn_new_tab.setFixedWidth(28)
        btn_new_tab.setFixedHeight(26)
        btn_new_tab.setToolTip("새 탭에서 PDF 파일 열기")
        btn_new_tab.clicked.connect(self.open_file_dialog)
        tab_header_layout.addWidget(btn_new_tab)

        central_vlayout.addWidget(tab_header_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        central_vlayout.addWidget(splitter, 1)

        # Left Thumbnail Sidebar
        left_panel = QWidget()
        left_panel.setMinimumWidth(200)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 6, 6, 6)

        # Top Header Strip: Left Panel Title + Direct Collapse Button
        left_header_widget = QWidget()
        left_header_layout = QHBoxLayout(left_header_widget)
        left_header_layout.setContentsMargins(0, 0, 0, 2)
        left_header_layout.setSpacing(6)

        self.left_header_lbl = QLabel("🗂️ 페이지 썸네일")
        self.left_header_lbl.setStyleSheet("font-weight: bold; font-size: 10pt; color: #4B5563;")
        left_header_layout.addWidget(self.left_header_lbl, 1)

        self.btn_collapse_left_panel = QPushButton("◀ 접기")
        self.btn_collapse_left_panel.setFixedHeight(24)
        self.btn_collapse_left_panel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse_left_panel.setToolTip("좌측 썸네일 바 접기 (단축키: F3 또는 상단 툴바 버튼)")
        self.btn_collapse_left_panel.clicked.connect(lambda: self.toggle_left_panel(False))
        left_header_layout.addWidget(self.btn_collapse_left_panel)

        left_layout.addWidget(left_header_widget)

        nav_row = QHBoxLayout()
        self.btn_prev_page = QPushButton("◀ 이전")
        self.btn_prev_page.setToolTip("이전 페이지로 이동 (단축키: Page Up)")
        self.btn_prev_page.clicked.connect(self.prev_page)
        self.page_indicator_lbl = QLabel("0 / 0")
        self.page_indicator_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_next_page = QPushButton("다음 ▶")
        self.btn_next_page.setToolTip("다음 페이지로 이동 (단축키: Page Down)")
        self.btn_next_page.clicked.connect(self.next_page)
        nav_row.addWidget(self.btn_prev_page)
        nav_row.addWidget(self.page_indicator_lbl, 1)
        nav_row.addWidget(self.btn_next_page)
        left_layout.addLayout(nav_row)

        self.thumb_list = ThumbnailSidebarListWidget()
        self.thumb_list.setIconSize(QSize(120, 160))
        self.thumb_list.setSpacing(6)
        self.thumb_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.thumb_list.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.thumb_list.setDragEnabled(True)
        self.thumb_list.setAcceptDrops(True)
        self.thumb_list.setMouseTracking(True)
        self.thumb_list.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.thumb_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.thumb_list.customContextMenuRequested.connect(self._show_thumb_context_menu)
        self.thumb_list.currentRowChanged.connect(self._on_thumb_selected)

        # Connect internal drag-drop reordering signal
        self.thumb_list.pagesReordered.connect(self._apply_pages_reorder)

        # Install thumbnail delegate with hover menu disabled for clean navigation in the left sidebar
        self.thumb_delegate = PageThumbnailDelegate(self.thumb_list, show_hover_menu=False)
        self.thumb_delegate.rotateLeftRequested.connect(lambda row: self.rotate_page(row, -90))
        self.thumb_delegate.rotateRightRequested.connect(lambda row: self.rotate_page(row, 90))
        self.thumb_delegate.deleteRequested.connect(self.delete_page)
        self.thumb_delegate.extractRequested.connect(self.extract_page)
        self.thumb_list.setItemDelegate(self.thumb_delegate)
        left_layout.addWidget(self.thumb_list, 1)

        # Batch Operations Toolbar for Multi-Selected Pages
        batch_box = QHBoxLayout()
        batch_box.setSpacing(4)
        btn_batch_rot_l = QPushButton("↺")
        btn_batch_rot_l.setToolTip("선택한 페이지(들) 왼쪽으로 90° 회전")
        btn_batch_rot_l.clicked.connect(lambda: self.rotate_selected_pages(-90))
        batch_box.addWidget(btn_batch_rot_l)

        btn_batch_rot_r = QPushButton("↻")
        btn_batch_rot_r.setToolTip("선택한 페이지(들) 오른쪽으로 90° 회전")
        btn_batch_rot_r.clicked.connect(lambda: self.rotate_selected_pages(90))
        batch_box.addWidget(btn_batch_rot_r)

        btn_batch_del = QPushButton("🗑️")
        btn_batch_del.setToolTip("선택한 페이지(들) 삭제")
        btn_batch_del.setStyleSheet("color: #EF4444; font-weight: bold;")
        btn_batch_del.clicked.connect(self.delete_selected_pages)
        batch_box.addWidget(btn_batch_del)

        btn_batch_ext = QPushButton("📤")
        btn_batch_ext.setToolTip("선택한 페이지(들) 별도 PDF로 추출")
        btn_batch_ext.setStyleSheet("color: #3B82F6; font-weight: bold;")
        btn_batch_ext.clicked.connect(self.extract_selected_pages)
        batch_box.addWidget(btn_batch_ext)
        left_layout.addLayout(batch_box)

        self.main_splitter = splitter
        self.main_splitter.setChildrenCollapsible(False)
        self.left_panel = left_panel
        self.main_splitter.addWidget(self.left_panel)

        # Center Stack (0: Single-Page Canvas View, 1: Full-Screen Organize Pages Grid, 2: Welcome / Empty Screen)
        self.center_stack = DynamicStackedWidget()

        # Page 0: Standard Scrollable PDF Canvas with Smart Wheel Navigation
        self.scroll_area = SmartPDFScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.pageChangeRequested.connect(self._on_wheel_page_change_requested)
        self.canvas = PDFCanvasWidget(self.font_registry)
        self.canvas.objectSelected.connect(self._on_canvas_object_selected)
        self.canvas.shapeDoubleClicked.connect(self._on_canvas_shape_double_clicked)
        self.canvas.selectionSpanChanged.connect(self._on_canvas_selection_span_changed)
        self.canvas.stateChanged.connect(self._on_canvas_state_changed)
        self.canvas.zoomRequest.connect(self.step_zoom)
        self.canvas.requestViewMode.connect(self.switch_to_view_mode)
        self.scroll_area.setWidget(self.canvas)
        self.center_stack.addWidget(self.scroll_area)

        # Page 1: Acrobat-Style Organize Pages Full-Screen Grid
        self.organize_widget = self._build_organize_pages_view()
        self.center_stack.addWidget(self.organize_widget)

        # Page 2: Welcome / Empty Workspace View
        self.welcome_widget = self._build_welcome_view()
        self.center_stack.addWidget(self.welcome_widget)

        # Page 3: Acrobat-Style Continuous PDF Scroll View
        self.continuous_scroll_area = ContinuousPDFScrollArea()
        self.continuous_scroll_area.pageChanged.connect(self._on_continuous_page_changed)
        self.continuous_scroll_area.continuous_canvas.pageDoubleClicked.connect(self._on_continuous_page_double_clicked)
        self.continuous_scroll_area.continuous_canvas.pageClicked.connect(self._on_continuous_page_clicked)
        self.continuous_scroll_area.continuous_canvas.zoomRequest.connect(self.step_zoom)
        self.center_stack.addWidget(self.continuous_scroll_area)

        self.main_splitter.addWidget(self.center_stack)

        # Right Inspector Panel
        self.right_panel = self._build_right_inspector()
        self.main_splitter.addWidget(self.right_panel)

        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 0)
        self.main_splitter.setSizes([205, 920, 355])

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            f"준비 완료 — PC에 설치된 총 {len(self.font_registry.available)}개의 글꼴이 로드되었습니다. 상단 탭으로 여러 PDF를 열람·편집할 수 있습니다."
        )

        self.setAcceptDrops(True)
        # 오픈 시 속성 및 보기 패널을 디폴트로 접기(Collapse) 상태로 세팅
        self.toggle_right_panel(False)

    def refresh_fonts_and_ui(self):
        """수동으로 윈도우 시스템 글꼴을 다시 스캔하고 UI 콤보박스를 갱신"""
        self.font_registry.refresh_fonts()
        cnt = len(self.font_registry.available)
        if hasattr(self, "font_combo"):
            current_key = self.font_combo.currentData()
            self.font_combo.blockSignals(True)
            self.font_combo.clear()
            for key, info in self.font_registry.available.items():
                self.font_combo.addItem(info["label"], key)
            if current_key:
                idx = self.font_combo.findData(current_key)
                if idx >= 0:
                    self.font_combo.setCurrentIndex(idx)
            self.font_combo.blockSignals(False)
            self.font_combo.setToolTip(f"PC에 설치된 전체 글꼴 ({cnt}종) 목록입니다. 한글 자주 쓰는 글꼴이 상단에 배치되어 있습니다.")
        if hasattr(self, "txt_inspector_group"):
            self.txt_inspector_group.setTitle(f"텍스트 속성 (PC 설치 글꼴 총 {cnt}개)")
        self.statusBar().showMessage(f"글꼴 새로고침 완료: 총 {cnt}종의 시스템 글꼴이 로드되었습니다.", 4000)

    def _build_right_inspector(self) -> QWidget:
        # Outer scroll area so all controls are smoothly accessible on any window height/resolution
        scroll_area = QScrollArea()
        scroll_area.setObjectName("right_inspector_scroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setMinimumWidth(330)
        scroll_area.setStyleSheet("""
            QScrollArea#right_inspector_scroll {
                border: none;
                background-color: transparent;
            }
        """)

        panel = QWidget()
        panel.setMinimumWidth(310)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 14, 12)
        layout.setSpacing(8)

        # Top Header Strip: Panel Title + Direct Collapse Button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 2)
        header_layout.setSpacing(6)

        self.panel_header_lbl = QLabel("🎛️ 속성 및 보기 패널")
        self.panel_header_lbl.setStyleSheet("font-weight: bold; font-size: 10pt; color: #4B5563;")
        header_layout.addWidget(self.panel_header_lbl, 1)

        self.btn_collapse_right_panel = QPushButton("접기 ▶")
        self.btn_collapse_right_panel.setFixedHeight(25)
        self.btn_collapse_right_panel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse_right_panel.setToolTip("우측 패널 접기 (단축키: F4 또는 상단 툴바 버튼)")
        self.btn_collapse_right_panel.clicked.connect(lambda: self.toggle_right_panel(False))
        header_layout.addWidget(self.btn_collapse_right_panel)

        layout.addWidget(header_widget)

        # View Mode Banner Card (shown in View Mode)
        self.view_mode_card = QGroupBox("👁️ 보기 모드 (Acrobat View)")
        card_layout = QVBoxLayout(self.view_mode_card)
        card_lbl = QLabel(
            "현재 깨끗한 **열람(보기) 상태**입니다.\n\n"
            "• 마우스로 드래그하여 본문 텍스트를 선택하고 **Ctrl+C**로 복사할 수 있습니다.\n"
            "• 기존 본문 글자를 고치거나 도형을 그리려면 아래 **[ 📝 편집 모드 전환 ]** 버튼을 누르세요."
        )
        card_lbl.setWordWrap(True)
        card_layout.addWidget(card_lbl)

        btn_go_edit = QPushButton("📝 본문 / 텍스트 편집 시작하기")
        btn_go_edit.setFixedHeight(34)
        btn_go_edit.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; border-radius: 4px;")
        btn_go_edit.clicked.connect(self.switch_to_edit_mode)
        card_layout.addWidget(btn_go_edit)
        layout.addWidget(self.view_mode_card)

        # Return to View Mode Button (for Edit Mode)
        self.btn_back_to_view = QPushButton("👁️ 보기 모드로 돌아가기 (Esc)")
        self.btn_back_to_view.setFixedHeight(30)
        self.btn_back_to_view.setToolTip("편집을 종료하고 깔끔한 보기 전용 화면으로 돌아갑니다 (단축키: Esc)")
        self.btn_back_to_view.clicked.connect(self.switch_to_view_mode)
        layout.addWidget(self.btn_back_to_view)

        self.inspector_title_lbl = QLabel("🛠️ 한글 텍스트 & 도형 속성 (Inspector)")
        self.inspector_title_lbl.setWordWrap(True)
        layout.addWidget(self.inspector_title_lbl)

        self.sel_info_lbl = QLabel("선택된 객체 없음 (새 객체 기본값 설정 중)")
        self.sel_info_lbl.setWordWrap(True)
        layout.addWidget(self.sel_info_lbl)

        self.txt_inspector_group = QGroupBox(f"텍스트 속성 (PC 설치 글꼴 총 {len(self.font_registry.available)}개)")
        txt_form = QFormLayout(self.txt_inspector_group)

        self.orig_font_lbl = QLabel("-")
        txt_form.addRow("원래 PDF 글꼴:", self.orig_font_lbl)

        self.block_scope_lbl = QLabel("적용 범위: 상자 전체 (부분 블록 미지정)")
        txt_form.addRow("서식 적용 범위:", self.block_scope_lbl)

        self.font_combo = QComboBox()
        self.font_combo.setView(QListView())
        self.font_combo.setMaxVisibleItems(24)
        self.font_combo.setToolTip(f"PC에 설치된 전체 글꼴 ({len(self.font_registry.available)}종) 목록입니다. 한글 자주 쓰는 글꼴이 상단에 배치되어 있습니다.")
        for key, info in self.font_registry.available.items():
            self.font_combo.addItem(info["label"], key)
        self.font_combo.currentIndexChanged.connect(self._on_font_family_changed)
        txt_form.addRow("PC 설치 글꼴:", self.font_combo)

        size_row = QHBoxLayout()
        size_row.setSpacing(4)
        self.font_size_spin = QDoubleSpinBox()
        self.font_size_spin.setRange(5.0, 120.0)
        self.font_size_spin.setSingleStep(0.5)
        self.font_size_spin.setValue(12.0)
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        size_row.addWidget(self.font_size_spin, 1)

        btn_fs_down = QPushButton("－")
        btn_fs_down.setFixedWidth(28)
        btn_fs_down.setToolTip("글꼴 크기 줄이기 (-0.5pt)")
        btn_fs_down.clicked.connect(self.font_size_spin.stepDown)
        size_row.addWidget(btn_fs_down)

        btn_fs_up = QPushButton("＋")
        btn_fs_up.setFixedWidth(28)
        btn_fs_up.setToolTip("글꼴 크기 키우기 (+0.5pt)")
        btn_fs_up.clicked.connect(self.font_size_spin.stepUp)
        size_row.addWidget(btn_fs_up)

        self.bold_chk = QCheckBox("굵게")
        self.bold_chk.toggled.connect(self._on_bold_changed)
        size_row.addWidget(self.bold_chk)
        txt_form.addRow("글꼴 크기 (pt):", size_row)

        self.btn_text_color = QPushButton("글자 색상 선택")
        self.btn_text_color.clicked.connect(self._pick_text_color)
        self._update_color_btn_style(self.btn_text_color, [0, 0, 0])
        txt_form.addRow("글자 색상:", self.btn_text_color)

        self.chk_redact_stream = QCheckBox("원본 글리프 투명 제거 (표/배경 보존)")
        self.chk_redact_stream.setChecked(True)
        self.chk_redact_stream.toggled.connect(self._on_redact_mode_toggled)
        txt_form.addRow("원본 처리:", self.chk_redact_stream)

        txt_form.addRow(QLabel("텍스트 내용 (원하는 단어만 블록 지정 후 수정 가능):"))
        self.inspector_text_edit = QTextEdit()
        self.inspector_text_edit.setAcceptRichText(False)
        self.inspector_text_edit.setFixedHeight(85)
        self.inspector_text_edit.textChanged.connect(self._on_inspector_text_edited)
        self.inspector_text_edit.selectionChanged.connect(self._on_inspector_selection_changed)
        txt_form.addRow(self.inspector_text_edit)

        layout.addWidget(self.txt_inspector_group)

        # Group 2: Shape & Box Appearance
        self.shape_inspector_group = QGroupBox("도형 및 상자 스타일 (클릭/더블클릭으로 재편집)")
        shape_form = QFormLayout(self.shape_inspector_group)

        self.btn_stroke_color = QPushButton("선/테두리 색상 선택")
        self.btn_stroke_color.clicked.connect(self._pick_stroke_color)
        self._update_color_btn_style(self.btn_stroke_color, [220, 38, 38])
        shape_form.addRow("선 색상:", self.btn_stroke_color)

        sw_row = QHBoxLayout()
        sw_row.setSpacing(4)
        self.stroke_width_spin = QDoubleSpinBox()
        self.stroke_width_spin.setRange(0.0, 25.0)
        self.stroke_width_spin.setSingleStep(0.5)
        self.stroke_width_spin.setValue(2.0)
        self.stroke_width_spin.valueChanged.connect(self._on_shape_style_changed)
        sw_row.addWidget(self.stroke_width_spin, 1)

        btn_sw_down = QPushButton("－")
        btn_sw_down.setFixedWidth(28)
        btn_sw_down.clicked.connect(self.stroke_width_spin.stepDown)
        sw_row.addWidget(btn_sw_down)

        btn_sw_up = QPushButton("＋")
        btn_sw_up.setFixedWidth(28)
        btn_sw_up.clicked.connect(self.stroke_width_spin.stepUp)
        sw_row.addWidget(btn_sw_up)
        shape_form.addRow("선 두께 (pt):", sw_row)

        fill_row = QHBoxLayout()
        self.chk_use_fill = QCheckBox("채우기 사용")
        self.chk_use_fill.toggled.connect(self._on_shape_style_changed)
        fill_row.addWidget(self.chk_use_fill)

        self.btn_fill_color = QPushButton("채우기 색상")
        self.btn_fill_color.clicked.connect(self._pick_fill_color)
        self._update_color_btn_style(self.btn_fill_color, [254, 240, 138])
        fill_row.addWidget(self.btn_fill_color, 1)
        shape_form.addRow("배경/내부 채우기:", fill_row)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(15, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._on_shape_style_changed)
        shape_form.addRow("불투명도 (%):", self.opacity_slider)

        layout.addWidget(self.shape_inspector_group)

        self.act_inspector_group = QGroupBox("선택 객체 작업")
        act_layout = QVBoxLayout(self.act_inspector_group)

        btn_dup = QPushButton("📋 선택 객체 복제 (Ctrl+D)")
        btn_dup.clicked.connect(self.duplicate_selected_object)
        act_layout.addWidget(btn_dup)

        self.btn_del_obj = QPushButton("🗑️ 선택 객체 삭제 / 원본 텍스트 복원 (Del)")
        self.btn_del_obj.clicked.connect(self.delete_selected_object)
        act_layout.addWidget(self.btn_del_obj)

        layout.addWidget(self.act_inspector_group)
        layout.addStretch(1)

        scroll_area.setWidget(panel)
        return scroll_area

    def _build_organize_pages_view(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Header toolbar for Organize Pages
        org_bar = QWidget()
        org_bar.setObjectName("organize_toolbar")
        org_bar.setStyleSheet("""
            QWidget#organize_toolbar {
                background-color: #1E242D;
                border-bottom: 2px solid #2563EB;
                padding: 6px 12px;
            }
        """)
        h_layout = QHBoxLayout(org_bar)
        h_layout.setContentsMargins(12, 6, 12, 6)
        h_layout.setSpacing(8)

        lbl_title = QLabel("📑 페이지 구성")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 11pt; color: #60A5FA;")
        h_layout.addWidget(lbl_title)

        self.organize_info_lbl = QLabel("총 0페이지")
        self.organize_info_lbl.setStyleSheet("color: #9CA3AF; font-size: 9pt;")
        h_layout.addWidget(self.organize_info_lbl)

        h_layout.addSpacing(10)

        btn_rot_l = QPushButton("↺ 좌회전")
        btn_rot_l.setToolTip("선택한 페이지를 시계 반대 방향으로 90° 회전합니다")
        btn_rot_l.clicked.connect(lambda: self.rotate_selected_pages(-90))
        h_layout.addWidget(btn_rot_l)

        btn_rot_r = QPushButton("↻ 우회전")
        btn_rot_r.setToolTip("선택한 페이지를 시계 방향으로 90° 회전합니다")
        btn_rot_r.clicked.connect(lambda: self.rotate_selected_pages(90))
        h_layout.addWidget(btn_rot_r)

        btn_del = QPushButton("🗑️ 삭제")
        btn_del.setToolTip("선택한 페이지를 문서에서 삭제합니다 (Delete 키)")
        btn_del.setStyleSheet("color: #EF4444; font-weight: bold;")
        btn_del.clicked.connect(self.delete_selected_pages)
        h_layout.addWidget(btn_del)

        btn_ext = QPushButton("📤 추출")
        btn_ext.setToolTip("선택한 페이지들을 새 PDF 문서로 추출하여 새 탭에서 엽니다")
        btn_ext.setStyleSheet("color: #60A5FA; font-weight: bold;")
        btn_ext.clicked.connect(self.extract_selected_pages)
        h_layout.addWidget(btn_ext)

        btn_blank = QPushButton("➕ 빈 페이지")
        btn_blank.setToolTip("선택한 페이지 뒤에 새로운 빈 페이지를 삽입합니다")
        btn_blank.clicked.connect(self.insert_blank_page)
        h_layout.addWidget(btn_blank)

        btn_insert_pdf = QPushButton("📁 PDF 삽입")
        btn_insert_pdf.setToolTip("다른 PDF 파일의 페이지들을 현재 문서의 선택 위치 뒤에 추가합니다")
        btn_insert_pdf.clicked.connect(self.insert_pdf_pages)
        h_layout.addWidget(btn_insert_pdf)

        btn_split_adv = QPushButton("✂️ 분할")
        btn_split_adv.setToolTip("고급 분할 다이얼로그(페이지 범위별, N페이지 단위 분할)를 엽니다")
        btn_split_adv.clicked.connect(self.open_split_dialog)
        h_layout.addWidget(btn_split_adv)

        h_layout.addStretch(1)

        # Thumbnail size zoom slider
        lbl_size = QLabel("🔍 크기:")
        lbl_size.setStyleSheet("color: #9CA3AF; font-size: 9pt;")
        h_layout.addWidget(lbl_size)

        self.org_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.org_size_slider.setRange(110, 260)
        self.org_size_slider.setValue(160)
        self.org_size_slider.setFixedWidth(100)
        self.org_size_slider.setToolTip("그리드 썸네일 카드의 표시 크기를 조절합니다 (단축키: Ctrl + 마우스 휠)")
        self.org_size_slider.valueChanged.connect(self._on_org_size_slider_changed)
        # Directly allow mouse wheel on the slider to step zoom
        self.org_size_slider.wheelEvent = lambda event: (
            self._step_organize_grid_zoom(1 if event.angleDelta().y() > 0 else -1),
            event.accept()
        )
        h_layout.addWidget(self.org_size_slider)

        h_layout.addSpacing(12)

        btn_close = QPushButton("✕ 닫기 (Esc)")
        btn_close.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px;")
        btn_close.clicked.connect(lambda: self.toggle_organize_pages(False))
        h_layout.addWidget(btn_close)

        vbox.addWidget(org_bar)

        # Main Grid ListWidget
        self.organize_grid = OrganizePagesListWidget()
        self.organize_grid.setViewMode(QListView.ViewMode.IconMode)
        self.organize_grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.organize_grid.setMovement(QListView.Movement.Snap)
        self.organize_grid.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.organize_grid.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.organize_grid.setDragEnabled(True)
        self.organize_grid.setAcceptDrops(True)
        self.organize_grid.setSpacing(16)
        self.organize_grid.setIconSize(QSize(130, 175))
        self.organize_grid.setMouseTracking(True)
        self.organize_grid.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.organize_grid.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.organize_grid.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.organize_grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.organize_grid.customContextMenuRequested.connect(self._show_organize_context_menu)
        self.organize_grid.itemDoubleClicked.connect(self._on_organize_item_double_clicked)
        self.organize_grid.escapePressed.connect(lambda: self.toggle_organize_pages(False))
        self.organize_grid.deletePressed.connect(self.delete_selected_pages)
        self.organize_grid.zoomRequest.connect(self._step_organize_grid_zoom)
        self.organize_grid.pagesReordered.connect(self._apply_pages_reorder)

        # Delegate for hover overlay on every card
        self.organize_delegate = PageThumbnailDelegate(self.organize_grid, card_size=QSize(160, 215))
        self.organize_delegate.rotateLeftRequested.connect(lambda row: self.rotate_page(row, -90))
        self.organize_delegate.rotateRightRequested.connect(lambda row: self.rotate_page(row, 90))
        self.organize_delegate.deleteRequested.connect(self.delete_page)
        self.organize_delegate.extractRequested.connect(self.extract_page)
        self.organize_grid.setItemDelegate(self.organize_delegate)

        vbox.addWidget(self.organize_grid, 1)
        return container

    def _build_welcome_view(self) -> QWidget:
        container = QWidget()
        container.setObjectName("welcome_view_container")
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)

        card = QFrame()
        card.setObjectName("welcome_card")
        card.setFixedWidth(580)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(16)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_icon = QLabel("📑")
        lbl_icon.setStyleSheet("font-size: 52pt;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl_icon)

        lbl_title = QLabel("K-PDF Studio")
        lbl_title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #3B82F6;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl_title)

        lbl_sub = QLabel("열려 있는 문서가 없습니다")
        lbl_sub.setStyleSheet("font-size: 13pt; font-weight: 500; color: #9CA3AF;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl_sub)

        drop_hint = QFrame()
        drop_hint.setObjectName("drop_hint_box")
        drop_hint_layout = QVBoxLayout(drop_hint)
        drop_hint_layout.setContentsMargins(20, 20, 20, 20)
        lbl_hint = QLabel("📥 PDF 파일을 이곳으로 끌어다 놓으세요\n(여러 파일 동시 드래그 앤 드롭 지원)")
        lbl_hint.setStyleSheet("font-size: 10.5pt; color: #6B7280; text-align: center;")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_hint_layout.addWidget(lbl_hint)
        card_layout.addWidget(drop_hint)

        btn_box = QVBoxLayout()
        btn_box.setSpacing(10)

        btn_open = QPushButton("📂  PDF 파일 열기... (Ctrl+O)")
        btn_open.setFixedHeight(42)
        btn_open.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 11pt;
                font-weight: bold;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        btn_open.clicked.connect(self.open_file_dialog)
        btn_box.addWidget(btn_open)

        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(8)

        btn_new_blank = QPushButton("➕ 새 빈 PDF")
        btn_new_blank.setFixedHeight(34)
        btn_new_blank.setToolTip("A4 규격의 깨끗한 빈 문서를 생성합니다")
        btn_new_blank.clicked.connect(self.create_blank_pdf)
        btn_row1.addWidget(btn_new_blank)

        btn_welcome_merge = QPushButton("📑 PDF/이미지 합치기")
        btn_welcome_merge.setFixedHeight(34)
        btn_welcome_merge.setToolTip("여러 PDF 파일 및 이미지(JPG, PNG 등)를 하나의 PDF로 합칩니다 (드래그 앤 드롭 지원)")
        btn_welcome_merge.clicked.connect(self.open_merge_dialog)
        btn_row1.addWidget(btn_welcome_merge)

        btn_box.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(8)

        btn_welcome_export_img = QPushButton("🖼️ PDF ➔ 고화질 이미지")
        btn_welcome_export_img.setFixedHeight(34)
        btn_welcome_export_img.setToolTip("PDF 문서를 300 DPI 등의 고화질 JPG 또는 PNG 이미지로 일괄 변환하여 저장합니다")
        btn_welcome_export_img.clicked.connect(self.export_current_pdf_to_images)
        btn_row2.addWidget(btn_welcome_export_img)

        btn_welcome_pptx = QPushButton("📊 PPTX ➔ 고화질 PDF")
        btn_welcome_pptx.setFixedHeight(34)
        btn_welcome_pptx.setToolTip("파워포인트(.pptx, .ppt)를 글꼴 손실 없이 원본 그대로 선명한 고화질 PDF로 변환합니다")
        btn_welcome_pptx.clicked.connect(self.open_pptx_to_pdf_dialog)
        btn_row2.addWidget(btn_welcome_pptx)

        btn_box.addLayout(btn_row2)
        card_layout.addLayout(btn_box)

        layout.addWidget(card)
        return container

    def create_blank_pdf(self):
        """Creates a fresh 1-page blank A4 PDF in memory and opens in a new tab."""
        doc = fitz.open()
        doc.new_page(width=595.32, height=841.92)
        raw_bytes = doc.tobytes()
        doc.close()

        new_name = f"새_문서_{len(self.doc_tabs) + 1}.pdf"
        target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), new_name)
        try:
            with open(target_path, "wb") as f:
                f.write(raw_bytes)
            self.open_pdf_in_tab(target_path, make_active=True)
            self.switch_to_edit_mode()
            self.status_bar.showMessage("새 빈 문서(A4)가 생성되었습니다. 상단 도구로 텍스트나 도형을 추가해보세요.")
        except Exception as e:
            QMessageBox.warning(self, "생성 오류", f"새 문서를 생성할 수 없습니다: {e}")

    def _build_shortcuts(self):
        # All standard shortcuts are declared in _build_menu_bar() with Qt.ShortcutContext.WindowShortcut.
        # Register them on the main window to ensure they trigger reliably regardless of focus.
        for act in self.menuBar().actions():
            menu = act.menu()
            if menu:
                for sub_act in menu.actions():
                    if not sub_act.isSeparator() and not sub_act.shortcut().isEmpty():
                        self.addAction(sub_act)

    def _on_global_escape_pressed(self):
        """Window-wide Esc key handler: exits Organize Pages, commits inline edit, clears search, or returns to View mode."""
        if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 1:
            self.toggle_organize_pages(False)
            return

        if hasattr(self, "canvas") and getattr(self.canvas, "_inline_editing_obj", None) is not None:
            self.canvas.commit_inline_edit()
            return

        is_search_focused = bool(hasattr(self, "search_input") and self.search_input.hasFocus())
        has_search_active = bool(
            (hasattr(self, "search_input") and self.search_input.text().strip())
            or getattr(self, "_search_all_hits", None)
            or (hasattr(self, "canvas") and getattr(self.canvas, "search_rects", None))
            or (
                hasattr(self, "continuous_scroll_area")
                and getattr(self.continuous_scroll_area.continuous_canvas, "search_results", None)
            )
        )
        if is_search_focused or has_search_active:
            self.clear_search_and_input()
            return

        if getattr(self, "app_mode", "view") == "edit":
            self.switch_to_view_mode()
            return

    # -----------------------------------------------------------------
    # Drag & Drop PDF Support (Robust, Non-blocking, Exception-Safe)
    # -----------------------------------------------------------------
    def dragEnterEvent(self, event):
        try:
            # 절대 dragEnter에서 event.mimeData().urls()를 동기 호출하지 않습니다!
            # 보안 프로그램(Cyberdigm DestinyDrive 등)이나 Windows OLE RPC가 장시간 유휴 후
            # urls() 쿼리 시 10초 블로킹 및 FastFail(0xc0000409) 크래시를 유발합니다.
            # 오직 포맷 존재 여부만 0.001초 만에 확인하고 즉시 수락합니다.
            if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
                event.acceptProposedAction()
                return
        except Exception:
            pass
        event.ignore()

    def dragMoveEvent(self, event):
        try:
            if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
                event.acceptProposedAction()
                return
        except Exception:
            pass
        event.ignore()

    def dropEvent(self, event):
        # 1. 즉시 OLE 트랜잭션을 수락/종료하여 탐색기(Explorer) 및 보안 모듈과의 COM IPC 락을 풀어줌
        try:
            event.acceptProposedAction()
        except Exception:
            pass

        # 2. 파일 목록 추출 및 열기는 try-except로 철저히 감싸서 비동기 QTimer로 분리 실행!
        # OLE dropEvent 컨텍스트 내부에서 무거운 I/O를 직접 수행하면 OLE 타임아웃/데드락이 발생할 수 있음.
        try:
            mime = event.mimeData()
            if not (mime.hasUrls() or mime.hasFormat("text/uri-list")):
                return
            urls = list(mime.urls())
        except Exception as e:
            if hasattr(self, "status_bar"):
                self.status_bar.showMessage(f"드래그 앤 드롭 데이터 수신 실패: {e}", 5000)
            return

        def _deferred_load_dropped_files(target_urls):
            first_opened = None
            pptx_dropped = []
            for u in target_urls:
                try:
                    f = u.toLocalFile() if hasattr(u, "toLocalFile") else str(u)
                    if not f or not os.path.exists(f):
                        continue
                    low = f.lower()
                    if low.endswith(".pdf"):
                        tab_idx = self.open_pdf_in_tab(f, make_active=False)
                        if first_opened is None and tab_idx is not None:
                            first_opened = tab_idx
                    elif low.endswith((".pptx", ".ppt")):
                        pptx_dropped.append(os.path.normpath(f))
                except Exception as ex:
                    print(f"[K-PDF Studio] 드롭 파일 열기 중 예외 발생 ({u}): {ex}")
            if first_opened is not None:
                self._switch_to_tab(first_opened)
            if pptx_dropped:
                self.open_pptx_to_pdf_dialog(pptx_dropped)

        QTimer.singleShot(10, lambda: _deferred_load_dropped_files(urls))

    # -----------------------------------------------------------------
    # PDF Loading, Character-level Extraction & Rendering
    # -----------------------------------------------------------------
    def open_file_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "PDF 파일 열기 (복수 선택 가능)", "", "PDF Files (*.pdf)")
        if not paths:
            return
        first_idx = None
        for p in paths:
            t_idx = self.open_pdf_in_tab(p, make_active=False)
            if first_idx is None and t_idx is not None:
                first_idx = t_idx
        if first_idx is not None:
            self._switch_to_tab(first_idx)

    def load_pdf_file(self, path: str):
        try:
            with open(path, "rb") as f:
                raw_bytes = f.read()
            doc = fitz.open(stream=raw_bytes, filetype="pdf")
        except Exception as e:
            QMessageBox.critical(self, "PDF 열기 오류", f"PDF 파일을 열 수 없습니다:\n{e}")
            return

        if doc.needs_pass:
            ok, doc, decrypted_bytes = authenticate_doc_dialog(doc, path, parent=self)
            if not ok or doc is None:
                if hasattr(self, "status_bar"):
                    self.status_bar.showMessage("🔒 암호 입력이 취소되어 이전 문서를 유지합니다.", 4000)
                return
            if decrypted_bytes is not None:
                raw_bytes = decrypted_bytes

        self._loading_file = True
        self.current_file_path = path
        self.base_pdf_bytes = raw_bytes
        self.doc = doc
        self.current_page_idx = 0
        self.page_objects.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        if hasattr(self, "search_input"):
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)
        self._clear_search()

        # Update active tab record if one exists
        if 0 <= self.active_tab_idx < len(self.doc_tabs):
            tab = self.doc_tabs[self.active_tab_idx]
            tab.file_path = path
            tab.doc = doc
            tab.base_pdf_bytes = raw_bytes
            tab.page_objects = {}
            tab.undo_stack = []
            tab.redo_stack = []
            tab.current_page_idx = 0
            tab.is_modified = False
            try:
                tab.file_ino = os.stat(path).st_ino
            except Exception:
                tab.file_ino = None
            self._watch_tab_file(tab)

            fname = os.path.basename(path)
            tab_title = fname if len(fname) <= 26 else (fname[:23] + "...")
            if hasattr(self, "tab_bar"):
                self.tab_bar.setTabText(self.active_tab_idx, tab_title)
                self.tab_bar.setTabToolTip(self.active_tab_idx, path)

        self._push_undo_snapshot("파일 열기")
        self._rebuild_thumbnails()
        if hasattr(self, "center_stack") and self.page_view_mode == "continuous" and hasattr(self, "continuous_scroll_area"):
            self.continuous_scroll_area.continuous_canvas.is_dark_theme = self.is_dark_effective
            self.continuous_scroll_area.continuous_canvas.set_document(self.doc, self.base_pdf_bytes, self.canvas.zoom)
            self.continuous_scroll_area.scroll_to_page(0)
        self.go_to_page(0)
        self._loading_file = False
        self._set_modified(False)
        self._update_window_title()
        self.status_bar.showMessage(f"열림: {path} (총 {len(self.doc)}페이지)")
        QTimer.singleShot(0, self.apply_smart_open_zoom)

    def _rebuild_thumbnails(self):
        self.thumb_list.blockSignals(True)
        self.thumb_list.clear()
        if hasattr(self, "organize_grid"):
            self.organize_grid.blockSignals(True)
            self.organize_grid.clear()

        if not self.doc:
            self.thumb_list.blockSignals(False)
            if hasattr(self, "organize_grid"):
                self.organize_grid.blockSignals(False)
            return

        for i in range(len(self.doc)):
            page = self.doc[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.28, 0.28), alpha=False)
            qimg = QImage(
                pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888
            ).copy()
            icon = QIcon(QPixmap.fromImage(qimg))
            item = QListWidgetItem(icon, f"{i + 1} 페이지")
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            self.thumb_list.addItem(item)

            if hasattr(self, "organize_grid"):
                item_org = QListWidgetItem(icon, f"{i + 1} 페이지")
                item_org.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
                self.organize_grid.addItem(item_org)

        if 0 <= self.current_page_idx < self.thumb_list.count():
            self.thumb_list.setCurrentRow(self.current_page_idx)
        self.thumb_list.blockSignals(False)

        if hasattr(self, "organize_grid"):
            if 0 <= self.current_page_idx < self.organize_grid.count():
                self.organize_grid.setCurrentRow(self.current_page_idx)
            self.organize_grid.blockSignals(False)
            if hasattr(self, "organize_info_lbl"):
                self.organize_info_lbl.setText(f"총 {len(self.doc)}페이지")

    def prev_page(self):
        """이전 페이지로 이동 (단일 페이지 및 연속 스크롤 모드 공통 지원, 단축키: Page Up)"""
        if not self.doc or len(self.doc) == 0:
            return
        if len(self.doc) == 1:
            self.status_bar.showMessage("단일 페이지 문서입니다 (총 1페이지).", 1500)
            return

        if self.current_page_idx > 0:
            target = self.current_page_idx - 1
            self.go_to_page(target)
            if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 0 and hasattr(self, "scroll_area"):
                QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().minimum()))
                QTimer.singleShot(10, lambda: self.scroll_area.horizontalScrollBar().setValue(self.scroll_area.horizontalScrollBar().minimum()))
            mode_str = "📄 단일 페이지" if self.page_view_mode == "single_page" else "📜 연속 스크롤"
            self.status_bar.showMessage(f"[{mode_str}] {target + 1} / {len(self.doc)} 페이지로 이동했습니다.", 1500)
        else:
            self.status_bar.showMessage("첫 번째 페이지입니다.", 1500)

    def next_page(self):
        """다음 페이지로 이동 (단일 페이지 및 연속 스크롤 모드 공통 지원, 단축키: Page Down)"""
        if not self.doc or len(self.doc) == 0:
            return
        if len(self.doc) == 1:
            self.status_bar.showMessage("단일 페이지 문서입니다 (총 1페이지).", 1500)
            return

        if self.current_page_idx < len(self.doc) - 1:
            target = self.current_page_idx + 1
            self.go_to_page(target)
            if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 0 and hasattr(self, "scroll_area"):
                QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().minimum()))
                QTimer.singleShot(10, lambda: self.scroll_area.horizontalScrollBar().setValue(self.scroll_area.horizontalScrollBar().minimum()))
            mode_str = "📄 단일 페이지" if self.page_view_mode == "single_page" else "📜 연속 스크롤"
            self.status_bar.showMessage(f"[{mode_str}] {target + 1} / {len(self.doc)} 페이지로 이동했습니다.", 1500)
        else:
            self.status_bar.showMessage("마지막 페이지입니다.", 1500)

    def go_to_page(self, page_idx: int):
        if not self.doc or len(self.doc) == 0:
            return
        self.canvas.commit_inline_edit()
        page_idx = max(0, min(len(self.doc) - 1, page_idx))
        self.current_page_idx = page_idx

        self.thumb_list.blockSignals(True)
        self.thumb_list.setCurrentRow(page_idx)
        self.thumb_list.blockSignals(False)

        if hasattr(self, "organize_grid") and 0 <= page_idx < self.organize_grid.count():
            self.organize_grid.blockSignals(True)
            self.organize_grid.setCurrentRow(page_idx)
            self.organize_grid.blockSignals(False)

        self.page_indicator_lbl.setText(f"{page_idx + 1} / {len(self.doc)}")
        if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 3:
            self.continuous_scroll_area.scroll_to_page(page_idx)
            return

        self.canvas.selected_obj = None
        self._on_canvas_object_selected(None)
        self._extract_page_text_segments(page_idx)
        self._render_current_page()

    def _extract_page_text_segments(self, page_idx: int):
        """Extracts clickable PDF text segments AND character-level bboxes via get_text('rawdict')."""
        self.canvas.detected_segments.clear()
        if not self.base_pdf_bytes:
            return
        try:
            tmp_doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
            if page_idx >= len(tmp_doc):
                tmp_doc.close()
                return
            page = tmp_doc[page_idx]
            rd = page.get_text("rawdict")
            seg_counter = 0

            for blk in rd.get("blocks", []):
                if blk.get("type") != 0:
                    continue
                for line in blk.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue
                    groups: List[List[dict]] = []
                    for sp in spans:
                        chars = sp.get("chars", [])
                        sp_txt = "".join(c.get("c", "") for c in chars)
                        sp["_text"] = sp_txt
                        if not sp_txt.strip():
                            if groups:
                                groups[-1].append(sp)
                            continue
                        if not groups:
                            groups.append([sp])
                        else:
                            prev_x1 = groups[-1][-1]["bbox"][2]
                            cur_x0 = sp["bbox"][0]
                            if cur_x0 - prev_x1 > 16.0:
                                groups.append([sp])
                            else:
                                groups[-1].append(sp)

                    for grp in groups:
                        full_txt = "".join(s.get("_text", "") for s in grp).strip()
                        if not full_txt:
                            continue
                        x0 = min(s["bbox"][0] for s in grp)
                        y0 = min(s["bbox"][1] for s in grp)
                        x1 = max(s["bbox"][2] for s in grp)
                        y1 = max(s["bbox"][3] for s in grp)
                        first = grp[0]
                        c_int = first.get("color", 0)
                        rgb = ((c_int >> 16) & 255, (c_int >> 8) & 255, c_int & 255)
                        flags = first.get("flags", 0)
                        font_name = first.get("font", "")
                        is_b = bool(flags & 16) or ("bold" in font_name.lower())

                        char_list: List[dict] = []
                        for s in grp:
                            s_c = s.get("color", 0)
                            s_rgb = ((s_c >> 16) & 255, (s_c >> 8) & 255, s_c & 255)
                            s_fn = s.get("font", font_name)
                            s_bd = bool(s.get("flags", 0) & 16) or ("bold" in s_fn.lower())
                            s_sz = float(s.get("size", 11.0))
                            for ch_dict in s.get("chars", []):
                                char_list.append({
                                    "c": ch_dict.get("c", ""),
                                    "bbox": tuple(ch_dict["bbox"]),
                                    "origin": tuple(ch_dict.get("origin", s["origin"])),
                                    "font": s_fn,
                                    "size": s_sz,
                                    "color": s_rgb,
                                    "bold": s_bd,
                                })

                        seg_counter += 1
                        self.canvas.detected_segments.append(
                            DetectedTextSegment(
                                seg_id=f"seg_{page_idx}_{seg_counter}",
                                bbox=(x0, y0, x1, y1),
                                origin=(first["origin"][0], first["origin"][1]),
                                text=full_txt,
                                pdf_font=font_name,
                                font_size=float(first.get("size", 11.0)),
                                color=rgb,
                                is_bold=is_b,
                                chars=char_list,
                            )
                        )
            tmp_doc.close()
        except Exception:
            pass

    def _render_current_page(self):
        if not self.base_pdf_bytes:
            self.canvas.page_pixmap = None
            self.canvas.update()
            return

        objs = self.page_objects.setdefault(self.current_page_idx, [])
        self.canvas.objects = objs

        tmp_doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
        if self.current_page_idx >= len(tmp_doc):
            tmp_doc.close()
            return

        page = tmp_doc[self.current_page_idx]
        self.canvas.page_rect_pt = (page.rect.width, page.rect.height)

        has_redactions = False
        for obj in objs:
            if obj.kind == "inplace_text" and obj.orig_bbox and obj.redact_stream_text:
                r = fitz.Rect(obj.orig_bbox)
                shrink_r = fitz.Rect(
                    r.x0 + 0.4,
                    r.y0 + r.height * 0.18,
                    r.x1 - 0.4,
                    r.y1 - r.height * 0.18,
                )
                page.add_redact_annot(shrink_r, fill=False)
                has_redactions = True

        if has_redactions:
            page.apply_redactions(
                images=fitz.PDF_REDACT_IMAGE_NONE,
                graphics=fitz.PDF_REDACT_LINE_ART_NONE,
            )

        scale = self.canvas.zoom * self.devicePixelRatioF()
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        qimg = QImage(
            pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888
        ).copy()
        qpix = QPixmap.fromImage(qimg)
        qpix.setDevicePixelRatio(self.devicePixelRatioF())

        self.canvas.page_pixmap = qpix
        self.canvas.update_canvas_geometry()
        tmp_doc.close()

        if hasattr(self, "continuous_scroll_area"):
            self.continuous_scroll_area.continuous_canvas.update()

    # -----------------------------------------------------------------
    # Committing All Edits (Including Partial Rich Text Runs & Shape Text) to PDF
    # -----------------------------------------------------------------
    def _build_committed_document(self) -> Optional[fitz.Document]:
        if not self.base_pdf_bytes:
            return None
        self.canvas.commit_inline_edit()
        out_doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")

        for p_idx, objs in self.page_objects.items():
            if p_idx < 0 or p_idx >= len(out_doc) or not objs:
                continue
            page = out_doc[p_idx]

            has_redact = False
            for obj in objs:
                if obj.kind == "inplace_text" and obj.orig_bbox and obj.redact_stream_text:
                    r = fitz.Rect(obj.orig_bbox)
                    shrink_r = fitz.Rect(
                        r.x0 + 0.4,
                        r.y0 + r.height * 0.18,
                        r.x1 - 0.4,
                        r.y1 - r.height * 0.18,
                    )
                    page.add_redact_annot(shrink_r, fill=False)
                    has_redact = True
                elif obj.kind == "eraser":
                    # Redact any text beneath the eraser area so it is completely removed from text stream
                    r = fitz.Rect(obj.rect)
                    fc = tuple(c / 255.0 for c in obj.fill_color)
                    page.add_redact_annot(r, fill=fc)
                    has_redact = True
            if has_redact:
                page.apply_redactions(
                    images=fitz.PDF_REDACT_IMAGE_NONE,
                    graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                )

            for obj in objs:
                r = fitz.Rect(obj.rect)
                sc = tuple(c / 255.0 for c in obj.stroke_color)
                fc = tuple(c / 255.0 for c in obj.fill_color)

                if obj.kind in ("inplace_text", "free_text"):
                    if obj.use_fill or (obj.kind == "inplace_text" and not obj.redact_stream_text):
                        sh = page.new_shape()
                        sh.draw_rect(r)
                        sh.finish(color=None, fill=fc, fill_opacity=obj.opacity)
                        sh.commit()

                    if obj.kind == "free_text" and obj.stroke_width > 0:
                        sh = page.new_shape()
                        sh.draw_rect(r)
                        sh.finish(color=sc, width=obj.stroke_width, stroke_opacity=obj.opacity)
                        sh.commit()

                    runs = obj.get_effective_runs()
                    max_fs = max((float(rn.get("font_size", obj.font_size)) for rn in runs), default=obj.font_size)
                    if obj.kind == "inplace_text" and obj.orig_origin:
                        dx = obj.rect[0] - (obj.orig_bbox[0] if obj.orig_bbox else obj.rect[0])
                        dy = obj.rect[1] - (obj.orig_bbox[1] if obj.orig_bbox else obj.rect[1])
                        tx, ty = obj.orig_origin[0] + dx, obj.orig_origin[1] + dy
                    else:
                        tx, ty = r.x0 + 2.0, r.y0 + max_fs * 0.92

                    self.font_registry.write_styled_runs_to_page(page, (tx, ty), runs, opacity=obj.opacity)

                elif obj.kind == "rect":
                    sh = page.new_shape()
                    sh.draw_rect(r)
                    sh.finish(
                        color=sc,
                        fill=fc if obj.use_fill else None,
                        width=max(0.5, obj.stroke_width),
                        stroke_opacity=obj.opacity,
                        fill_opacity=obj.opacity if obj.use_fill else 1.0,
                    )
                    sh.commit()
                    if obj.text.strip():
                        tw_w = sum(self.font_registry.char_width_pt(ch, obj.font_key, obj.font_size, obj.bold) for ch in obj.text)
                        tx = r.x0 + max(2.0, (r.width - tw_w) * 0.5)
                        ty = r.y0 + (r.height + obj.font_size * 0.72) * 0.5
                        self.font_registry.write_styled_runs_to_page(page, (tx, ty), obj.get_effective_runs(), opacity=obj.opacity)

                elif obj.kind == "ellipse":
                    sh = page.new_shape()
                    sh.draw_oval(r)
                    sh.finish(
                        color=sc,
                        fill=fc if obj.use_fill else None,
                        width=max(0.5, obj.stroke_width),
                        stroke_opacity=obj.opacity,
                        fill_opacity=obj.opacity if obj.use_fill else 1.0,
                    )
                    sh.commit()
                    if obj.text.strip():
                        tw_w = sum(self.font_registry.char_width_pt(ch, obj.font_key, obj.font_size, obj.bold) for ch in obj.text)
                        tx = r.x0 + max(4.0, (r.width - tw_w) * 0.5)
                        ty = r.y0 + (r.height + obj.font_size * 0.72) * 0.5
                        self.font_registry.write_styled_runs_to_page(page, (tx, ty), obj.get_effective_runs(), opacity=obj.opacity)

                elif obj.kind == "highlight":
                    # Acrobat-standard PDF Highlight Annotation: text is 100% sharp and visible beneath
                    annot = page.add_highlight_annot(r)
                    annot.set_colors(stroke=fc)
                    annot.set_opacity(max(0.65, min(obj.opacity, 0.95)))
                    annot.update()

                elif obj.kind == "eraser":
                    # Whiteout / Eraser: Completely covers any existing graphics/text with fill_color (default white)
                    sh = page.new_shape()
                    sh.draw_rect(r)
                    sh.finish(color=None, fill=fc, fill_opacity=1.0)
                    sh.commit()

                elif obj.kind in ("line", "arrow"):
                    p0 = fitz.Point(obj.rect[0], obj.rect[1])
                    p1 = fitz.Point(obj.rect[2], obj.rect[3])
                    sh = page.new_shape()
                    sh.draw_line(p0, p1)
                    sh.finish(color=sc, width=max(0.5, obj.stroke_width), stroke_opacity=obj.opacity)
                    if obj.kind == "arrow":
                        angle = math.atan2(p1.y - p0.y, p1.x - p0.x)
                        hlen = max(8.0, obj.stroke_width * 4.2)
                        a1 = fitz.Point(
                            p1.x - hlen * math.cos(angle - math.pi / 6),
                            p1.y - hlen * math.sin(angle - math.pi / 6),
                        )
                        a2 = fitz.Point(
                            p1.x - hlen * math.cos(angle + math.pi / 6),
                            p1.y - hlen * math.sin(angle + math.pi / 6),
                        )
                        sh.draw_polyline([p1, a1, a2, p1])
                        sh.finish(color=sc, fill=sc, width=1.0, stroke_opacity=obj.opacity, fill_opacity=obj.opacity)
                    sh.commit()

        return out_doc

    def save_pdf(self) -> bool:
        if not self.base_pdf_bytes:
            return False
        if not self.current_file_path:
            return self.save_pdf_as()
        return self._save_to_path(self.current_file_path)

    def save_pdf_as(self) -> bool:
        if not self.base_pdf_bytes:
            return False
        default_name = self.current_file_path or "edited_한글문서.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "다른 이름으로 PDF 저장", default_name, "PDF Files (*.pdf)")
        if path:
            return self._save_to_path(path)
        return False

    def _save_to_path(self, target_path: str) -> bool:
        tmp_path = None
        try:
            out_doc = self._build_committed_document()
            if not out_doc:
                return False
            out_bytes = out_doc.tobytes(garbage=3, deflate=True)
            out_doc.close()

            # 원자적 파일 교체 (Atomic Write)로 구글 드라이브 동기화 락 및 0바이트 파일 손상 원천 방지
            dir_name = os.path.dirname(os.path.abspath(target_path))
            tmp_path = os.path.join(dir_name, f"~kpdf_{uuid.uuid4().hex[:8]}.tmp")
            with open(tmp_path, "wb") as f:
                f.write(out_bytes)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, target_path)
            tmp_path = None

            self.load_pdf_file(target_path)
            self._set_modified(False)
            self.status_bar.showMessage(f"✅ 저장 완료: {target_path}")
            return True
        except Exception as e:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            QMessageBox.critical(self, "저장 오류", f"PDF 파일을 저장하는 중 오류가 발생했습니다:\n{e}")
            return False

    # -----------------------------------------------------------------
    # Acrobat-Style Print (AcrobatPrintDialog)
    # -----------------------------------------------------------------
    def print_pdf(self):
        if not self.base_pdf_bytes:
            return
        out_doc = self._build_committed_document()
        if not out_doc:
            return

        try:
            dlg = AcrobatPrintDialog(out_doc, self.current_page_idx + 1, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                ok, msg = dlg.execute_print()
                if ok:
                    self.status_bar.showMessage(f"🖨️ {msg}")
                else:
                    QMessageBox.warning(self, "인쇄 안내", msg)
        except Exception as e:
            QMessageBox.critical(self, "인쇄 오류", f"인쇄 중 오류가 발생했습니다:\n{e}")
        finally:
            out_doc.close()

    # -----------------------------------------------------------------
    # Document Properties (Ctrl+D) & Enterprise Cloudium Integration
    # -----------------------------------------------------------------
    def open_document_properties(self):
        """Opens Acrobat DC-style Document Properties Dialog (Ctrl+D)."""
        if not self.doc:
            QMessageBox.information(self, "문서 정보", "열려 있는 PDF 문서가 없습니다.")
            return
        dlg = DocumentPropertiesDialog(
            doc=self.doc,
            file_path=self.current_file_path,
            current_page_idx=self.current_page_idx,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.metadata_changed:
            committed = self._build_committed_document()
            if not committed:
                return
            committed.set_metadata(dlg.new_metadata)
            self.base_pdf_bytes = committed.tobytes()
            committed.close()
            self.doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
            self._set_modified(True)
            self._push_undo_snapshot("문서 메타데이터(제목/작성자 등) 수정")
            self.status_bar.showMessage("ℹ️ 문서 메타데이터가 업데이트되었습니다. (저장 시 PDF에 반영)")

    # -----------------------------------------------------------------
    # Merge & Split Operations
    # -----------------------------------------------------------------
    def open_merge_dialog(self):
        dlg = MergePDFDialog(self.current_file_path, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        items = dlg.items_data
        if not items:
            return

        try:
            is_append = bool(dlg.rb_append and dlg.rb_append.isChecked() and self.base_pdf_bytes)
            if is_append:
                merged_doc = self._build_committed_document()
                start_idx = 1 if (
                    items
                    and self.current_file_path
                    and os.path.abspath(items[0]["path"]) == os.path.abspath(self.current_file_path)
                ) else 0
                for item in items[start_idx:]:
                    src = _open_source_document(item["path"])
                    groups = parse_page_ranges(item["range"], len(src))
                    for grp in groups:
                        for pno in grp:
                            merged_doc.insert_pdf(src, from_page=pno, to_page=pno)
                    src.close()

                self.base_pdf_bytes = merged_doc.tobytes(garbage=2, deflate=True)
                self.doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
                self.page_objects.clear()
                self._push_undo_snapshot("PDF 합치기")
                self._rebuild_thumbnails()
                self.go_to_page(self.current_page_idx)
                self.status_bar.showMessage(f"✅ 현재 문서에 병합 완료 (총 {len(self.doc)}페이지)")
                QMessageBox.information(
                    self,
                    "PDF 병합 완료",
                    f"현재 열려 있는 문서 뒤에 성공적으로 이어 붙였습니다.\n\n총 {len(self.doc)}페이지"
                )
            else:
                save_path = dlg.save_path_edit.text().strip()
                if not save_path:
                    first_p = items[0]["path"]
                    save_path = dlg._compute_default_merged_path(first_p)

                save_dir = os.path.dirname(os.path.abspath(save_path))
                if save_dir:
                    os.makedirs(save_dir, exist_ok=True)

                merged_doc = fitz.open()
                for item in items:
                    src = _open_source_document(item["path"])
                    groups = parse_page_ranges(item["range"], len(src))
                    for grp in groups:
                        for pno in grp:
                            merged_doc.insert_pdf(src, from_page=pno, to_page=pno)
                    src.close()

                merged_doc.save(save_path, garbage=3, deflate=True)
                merged_doc.close()

                # Open into new active tab immediately and show on screen!
                self.open_pdf_in_tab(save_path, make_active=True)
                self.status_bar.showMessage(f"✅ 병합 완료 및 새 파일 생성: {os.path.basename(save_path)}")
                QMessageBox.information(
                    self,
                    "PDF 병합 완료",
                    f"성공적으로 병합되어 새 파일로 저장되고 화면에 열렸습니다:\n\n"
                    f"📄 파일명: {os.path.basename(save_path)}\n"
                    f"📂 저장 위치: {save_dir}"
                )
        except Exception as e:
            QMessageBox.critical(self, "PDF 병합 오류", f"병합 중 오류가 발생했습니다:\n{e}")

    def open_split_dialog(self):
        if not self.doc or len(self.doc) == 0:
            return
        dlg = SplitPDFDialog(len(self.doc), self.current_page_idx + 1, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        src_doc = self._build_committed_document()
        if not src_doc:
            return

        try:
            total = len(src_doc)
            if dlg.rb_range_single.isChecked():
                groups = parse_page_ranges(dlg.range_input.text(), total)
                save_path, _ = QFileDialog.getSaveFileName(
                    self, "추출한 PDF 저장", "extracted_추출문서.pdf", "PDF Files (*.pdf)"
                )
                if save_path:
                    out = fitz.open()
                    for grp in groups:
                        for pno in grp:
                            out.insert_pdf(src_doc, from_page=pno, to_page=pno)
                    out.save(save_path, garbage=3, deflate=True)
                    out.close()
                    QMessageBox.information(self, "페이지 추출 완료", f"선택한 페이지가 저장되었습니다:\n{save_path}")

            elif dlg.rb_range_multi.isChecked():
                groups = parse_page_ranges(dlg.range_input.text(), total)
                out_dir = QFileDialog.getExistingDirectory(self, "분할된 PDF들을 저장할 폴더 선택")
                if out_dir:
                    base_name = os.path.splitext(os.path.basename(self.current_file_path or "document"))[0]
                    created = []
                    for i, grp in enumerate(groups):
                        out = fitz.open()
                        for pno in grp:
                            out.insert_pdf(src_doc, from_page=pno, to_page=pno)
                        fn = os.path.join(out_dir, f"{base_name}_part{i + 1}_{grp[0] + 1}-{grp[-1] + 1}p.pdf")
                        out.save(fn, garbage=3, deflate=True)
                        out.close()
                        created.append(fn)
                    QMessageBox.information(
                        self, "구간별 분할 완료", f"총 {len(created)}개의 PDF 파일로 분할 저장되었습니다:\n{out_dir}"
                    )

            elif dlg.rb_every_n.isChecked():
                step = dlg.chunk_spin.value()
                out_dir = QFileDialog.getExistingDirectory(self, "자동 분할된 PDF들을 저장할 폴더 선택")
                if out_dir:
                    base_name = os.path.splitext(os.path.basename(self.current_file_path or "document"))[0]
                    count = 0
                    for start in range(0, total, step):
                        end = min(total - 1, start + step - 1)
                        out = fitz.open()
                        out.insert_pdf(src_doc, from_page=start, to_page=end)
                        fn = os.path.join(out_dir, f"{base_name}_{start + 1}-{end + 1}p.pdf")
                        out.save(fn, garbage=3, deflate=True)
                        out.close()
                        count += 1
                    QMessageBox.information(
                        self, "자동 분할 완료", f"총 {count}개의 PDF 파일로 분할 저장되었습니다:\n{out_dir}"
                    )

            elif dlg.rb_at_current.isChecked() and total >= 2:
                out_dir = QFileDialog.getExistingDirectory(self, "2등분된 PDF를 저장할 폴더 선택")
                if out_dir:
                    base_name = os.path.splitext(os.path.basename(self.current_file_path or "document"))[0]
                    split_idx = min(total - 2, self.current_page_idx)
                    p_a = os.path.join(out_dir, f"{base_name}_앞부분_1-{split_idx + 1}p.pdf")
                    p_b = os.path.join(out_dir, f"{base_name}_뒷부분_{split_idx + 2}-{total}p.pdf")

                    doc_a = fitz.open()
                    doc_a.insert_pdf(src_doc, from_page=0, to_page=split_idx)
                    doc_a.save(p_a, garbage=3, deflate=True)
                    doc_a.close()

                    doc_b = fitz.open()
                    doc_b.insert_pdf(src_doc, from_page=split_idx + 1, to_page=total - 1)
                    doc_b.save(p_b, garbage=3, deflate=True)
                    doc_b.close()
                    QMessageBox.information(self, "2등분 완료", f"두 개의 파일로 분할되었습니다:\n1) {p_a}\n2) {p_b}")
        except Exception as e:
            QMessageBox.critical(self, "PDF 분할 오류", f"분할 중 오류가 발생했습니다:\n{e}")
        finally:
            src_doc.close()

    def export_current_pdf_to_images(self):
        """현재 열린 PDF 문서 또는 사용자가 선택한 PDF 문서를 고화질 JPG 또는 PNG 이미지로 일괄 내보내기."""
        doc = None
        doc_path = None
        is_temp_doc = False

        if self.doc and len(self.doc) > 0:
            doc = self._build_committed_document()
            doc_path = self.current_file_path
        else:
            fpath, _ = QFileDialog.getOpenFileName(
                self, "고화질 이미지로 변환할 PDF 문서 선택", "", "PDF 문서 (*.pdf);;모든 파일 (*.*)"
            )
            if not fpath:
                return
            try:
                doc = fitz.open(fpath)
                doc_path = fpath
                is_temp_doc = True
            except Exception as e:
                QMessageBox.critical(self, "오류", f"PDF 파일을 열 수 없습니다:\n{e}")
                return

        if not doc or len(doc) == 0:
            QMessageBox.warning(self, "알림", "변환할 PDF 페이지가 없습니다.")
            return

        total_pages = len(doc)
        cur_p1 = (self.current_page_idx + 1) if (self.doc and not is_temp_doc) else 1

        if doc_path:
            def_dir = os.path.dirname(doc_path)
            stem = os.path.splitext(os.path.basename(doc_path))[0]
        else:
            def_dir = os.path.expanduser("~")
            stem = "document"

        dlg = ExportImagesDialog(total_pages, cur_p1, def_dir, stem, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            if is_temp_doc and doc:
                doc.close()
            return

        pages = dlg.get_selected_pages()
        if not pages:
            QMessageBox.warning(self, "알림", "선택된 페이지가 없습니다.")
            if is_temp_doc and doc:
                doc.close()
            return

        dpi = dlg.get_dpi()
        fmt = dlg.get_format()
        quality = dlg.get_quality()
        out_dir = dlg.get_out_dir()
        open_folder = dlg.should_open_folder()

        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "폴더 생성 오류", f"저장 폴더를 생성할 수 없습니다:\n{out_dir}\n{e}")
            if is_temp_doc and doc:
                doc.close()
            return

        prog = QProgressDialog("PDF 페이지를 고화질 이미지로 변환 중입니다...", "중단", 0, len(pages), self)
        prog.setWindowTitle("고화질 이미지 변환 진행 중")
        prog.setWindowModality(Qt.WindowModality.WindowModal)
        prog.setMinimumDuration(200)
        prog.show()

        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        saved_count = 0

        # Pillow 가용 여부 확인
        try:
            from PIL import Image
            have_pil = True
        except ImportError:
            have_pil = False

        try:
            for step, pno in enumerate(pages):
                if prog.wasCanceled():
                    break
                prog.setLabelText(f"변환 중: {pno + 1} / {total_pages} 페이지 (진행: {step + 1}/{len(pages)})...")
                prog.setValue(step)
                QCoreApplication.processEvents()

                page = doc.load_page(pno)
                pix = page.get_pixmap(matrix=matrix, alpha=(fmt == "png"))
                out_name = f"{stem}_{pno + 1:03d}.{fmt}"
                out_path = os.path.join(out_dir, out_name)

                if fmt == "jpg" and have_pil:
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img.save(out_path, "JPEG", quality=quality, subsampling=0)
                else:
                    pix.save(out_path)

                pix = None
                saved_count += 1
            prog.setValue(len(pages))
        except Exception as e:
            QMessageBox.critical(self, "이미지 변환 오류", f"변환 중 오류가 발생했습니다:\n{e}")
        finally:
            prog.close()
            if is_temp_doc and doc:
                doc.close()

        if saved_count > 0:
            msg = (
                f"총 {saved_count}개 페이지가 고화질 {fmt.upper()} 이미지로 성공적으로 변환되었습니다!\n\n"
                f"📂 저장 폴더: {out_dir}\n"
                f"⚙️ 해상도: {dpi} DPI ({'최고 품질 100%' if fmt == 'jpg' else '무손실'})"
            )
            QMessageBox.information(self, "이미지 내보내기 완료", msg)
            if open_folder and os.path.isdir(out_dir):
                try:
                    os.startfile(out_dir)
                except Exception:
                    pass

    def open_pptx_to_pdf_dialog(self, initial_files: Optional[List[str]] = None):
        """파워포인트(.pptx, .ppt)를 고화질 PDF로 변환하는 대화상자 호출 및 새 탭 오픈 연동."""
        dlg = PPTXToPDFDialog(initial_files, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.cb_open_tab.isChecked() and dlg.converted_pdfs:
                first_idx = None
                for pdf_path in dlg.converted_pdfs:
                    if os.path.isfile(pdf_path):
                        t_idx = self.open_pdf_in_tab(pdf_path, make_active=False)
                        if first_idx is None and t_idx is not None:
                            first_idx = t_idx
                if first_idx is not None:
                    self._switch_to_tab(first_idx)
                self.status_bar.showMessage(f"✅ PPTX ➔ 고화질 PDF 변환 완료 ({len(dlg.converted_pdfs)}개 문서 열림)", 6000)

    # -----------------------------------------------------------------
    # Page Operations (Single & Multi-Selection Support, Extract & Drag Reorder)
    # -----------------------------------------------------------------
    def rotate_page(self, page_idx: int, delta_deg: int):
        """Rotates a single page by delta_deg (e.g. 90 or -90)."""
        if not self.base_pdf_bytes or not self.doc:
            return
        if page_idx < 0 or page_idx >= len(self.doc):
            return
        committed = self._build_committed_document()
        if not committed:
            return
        page = committed[page_idx]
        page.set_rotation((page.rotation + delta_deg) % 360)
        self.base_pdf_bytes = committed.tobytes()
        committed.close()
        self.doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
        self.page_objects.clear()
        self._push_undo_snapshot(f"{page_idx + 1}페이지 회전")
        self._rebuild_thumbnails()
        self.go_to_page(page_idx)

    def rotate_current_page(self, delta_deg: int):
        self.rotate_page(self.current_page_idx, delta_deg)

    def _get_active_selected_page_indices(self) -> List[int]:
        if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 1 and hasattr(self, "organize_grid"):
            rows = sorted(set(idx.row() for idx in self.organize_grid.selectedIndexes()))
            if rows:
                return rows
        if hasattr(self, "thumb_list"):
            rows = sorted(set(idx.row() for idx in self.thumb_list.selectedIndexes()))
            if rows:
                return rows
        return [self.current_page_idx] if (self.doc and len(self.doc) > 0) else []

    def rotate_selected_pages(self, delta_deg: int):
        """Rotates all currently selected pages by delta_deg."""
        if not self.base_pdf_bytes or not self.doc:
            return
        sel_rows = self._get_active_selected_page_indices()
        committed = self._build_committed_document()
        if not committed:
            return
        for r in sel_rows:
            if 0 <= r < len(committed):
                page = committed[r]
                page.set_rotation((page.rotation + delta_deg) % 360)
        self.base_pdf_bytes = committed.tobytes()
        committed.close()
        self.doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
        self.page_objects.clear()
        self._push_undo_snapshot(f"선택한 {len(sel_rows)}개 페이지 회전")
        self._rebuild_thumbnails()
        self.go_to_page(sel_rows[0] if sel_rows else self.current_page_idx)
        self.status_bar.showMessage(f"↺/↻ 선택한 {len(sel_rows)}개 페이지가 회전되었습니다.")

    def delete_page(self, page_idx: int):
        """Deletes a single page."""
        if not self.doc or len(self.doc) <= 1:
            QMessageBox.warning(self, "삭제 불가", "문서에 최소 1개의 페이지는 남아 있어야 합니다.")
            return
        ret = QMessageBox.question(
            self,
            "페이지 삭제 확인",
            f"{page_idx + 1} 페이지를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        committed = self._build_committed_document()
        if not committed:
            return
        committed.delete_page(page_idx)
        self.base_pdf_bytes = committed.tobytes()
        committed.close()
        self.doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
        self.page_objects.clear()
        self._push_undo_snapshot(f"{page_idx + 1}페이지 삭제")
        self._rebuild_thumbnails()
        self.go_to_page(min(page_idx, len(self.doc) - 1))
        self.status_bar.showMessage(f"🗑️ {page_idx + 1}페이지가 삭제되었습니다.")

    def delete_current_page(self):
        self.delete_page(self.current_page_idx)

    def delete_selected_pages(self):
        """Deletes all selected pages with confirmation."""
        if not self.doc:
            return
        sel_rows = self._get_active_selected_page_indices()
        if len(sel_rows) >= len(self.doc):
            QMessageBox.warning(self, "삭제 불가", "문서의 모든 페이지를 삭제할 수는 없습니다. 최소 1페이지는 남아야 합니다.")
            return

        pages_str = ", ".join(f"{r + 1}p" for r in sel_rows[:6])
        if len(sel_rows) > 6:
            pages_str += f" 외 {len(sel_rows) - 6}개"
        ret = QMessageBox.question(
            self,
            "선택 페이지 삭제 확인",
            f"선택한 총 {len(sel_rows)}개 페이지({pages_str})를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        committed = self._build_committed_document()
        if not committed:
            return
        for r in reversed(sel_rows):
            if 0 <= r < len(committed):
                committed.delete_page(r)
        self.base_pdf_bytes = committed.tobytes()
        committed.close()
        self.doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
        self.page_objects.clear()
        self._push_undo_snapshot(f"선택한 {len(sel_rows)}개 페이지 삭제")
        self._rebuild_thumbnails()
        target_idx = min(sel_rows[0], len(self.doc) - 1)
        self.go_to_page(target_idx)
        self.status_bar.showMessage(f"🗑️ 총 {len(sel_rows)}개 페이지가 삭제되었습니다.")

    def extract_page(self, page_idx: int):
        """Extracts a single page into a new PDF file and opens it in a new tab."""
        self.extract_pages([page_idx])

    def extract_selected_pages(self):
        """Extracts all selected pages into a new PDF file and opens it in a new tab."""
        sel_rows = self._get_active_selected_page_indices()
        self.extract_pages(sel_rows)

    def extract_pages(self, page_indices: List[int]):
        """Extracts specified pages into a new file, saving and opening in a tab."""
        if not self.doc or not page_indices:
            return
        pages_lbl = "-".join(str(p + 1) for p in page_indices[:3])
        if len(page_indices) > 3:
            pages_lbl += f"_외{len(page_indices) - 3}p"
        base_name = os.path.splitext(os.path.basename(self.current_file_path or "문서"))[0]
        default_fn = f"{base_name}_추출_{pages_lbl}.pdf"

        save_path, _ = QFileDialog.getSaveFileName(self, "선택 페이지 추출 저장", default_fn, "PDF Files (*.pdf)")
        if not save_path:
            return

        try:
            committed = self._build_committed_document()
            if not committed:
                return
            out_doc = fitz.open()
            for pno in page_indices:
                if 0 <= pno < len(committed):
                    out_doc.insert_pdf(committed, from_page=pno, to_page=pno)
            out_doc.save(save_path, garbage=3, deflate=True)
            out_doc.close()
            committed.close()

            # Open the extracted PDF in a new tab right away!
            self.open_pdf_in_tab(save_path, make_active=True)
            QMessageBox.information(
                self,
                "페이지 추출 완료",
                f"총 {len(page_indices)}개 페이지가 추출되어 저장되었습니다:\n{save_path}\n\n상단 새 탭에서 즉시 열람 및 추가 편집이 가능합니다.",
            )
        except Exception as e:
            QMessageBox.critical(self, "페이지 추출 오류", f"페이지 추출 중 오류가 발생했습니다:\n{e}")

    def insert_blank_page(self):
        if not self.base_pdf_bytes:
            return
        sel_rows = self._get_active_selected_page_indices()
        target_pno = (sel_rows[-1] + 1) if sel_rows else (self.current_page_idx + 1)
        committed = self._build_committed_document()
        if not committed:
            return
        cur_rect = committed[self.current_page_idx].rect
        committed.new_page(pno=target_pno, width=cur_rect.width, height=cur_rect.height)
        self.base_pdf_bytes = committed.tobytes()
        committed.close()
        self.doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
        self.page_objects.clear()
        self._push_undo_snapshot("빈 페이지 삽입")
        self._rebuild_thumbnails()
        self.go_to_page(target_pno)

    def insert_pdf_pages(self):
        """Inserts pages from an external PDF file after the current / selected page."""
        if not self.base_pdf_bytes or not self.doc:
            return
        path, _ = QFileDialog.getOpenFileName(self, "삽입할 PDF 파일 선택", "", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            insert_doc = fitz.open(path)
            if insert_doc.needs_pass:
                ok, insert_doc, _ = authenticate_doc_dialog(insert_doc, path, parent=self)
                if not ok or insert_doc is None:
                    if hasattr(self, "status_bar"):
                        self.status_bar.showMessage("🔒 암호 입력이 취소되어 페이지 삽입을 중단했습니다.", 4000)
                    return
            if len(insert_doc) == 0:
                insert_doc.close()
                return
            sel_rows = self._get_active_selected_page_indices()
            ins_idx = (sel_rows[-1] + 1) if sel_rows else len(self.doc)

            committed = self._build_committed_document()
            if not committed:
                insert_doc.close()
                return
            committed.insert_pdf(insert_doc, start_at=ins_idx)
            num_inserted = len(insert_doc)
            insert_doc.close()

            self.base_pdf_bytes = committed.tobytes()
            committed.close()
            self.doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
            self.page_objects.clear()
            self._push_undo_snapshot(f"외부 PDF {num_inserted}페이지 삽입")
            self._rebuild_thumbnails()
            self.go_to_page(ins_idx)
            self.status_bar.showMessage(f"➕ '{os.path.basename(path)}'에서 {num_inserted}개 페이지가 삽입되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "PDF 삽입 오류", f"PDF 페이지를 삽입하는 중 오류가 발생했습니다:\n{e}")

    def toggle_organize_pages(self, enable: Optional[bool] = None):
        """Toggles between standard single-page canvas view and Acrobat-style Organize Pages grid."""
        if not self.doc or len(self.doc) == 0:
            return
        if enable is None:
            enable = (self.center_stack.currentIndex() in (0, 3))

        if enable:
            self.canvas.commit_inline_edit()
            self._saved_splitter_sizes = self.main_splitter.sizes()
            self.left_panel.hide()
            self.right_panel.hide()
            self.tb_tools.hide()
            self.btn_organize_pages.setText("✕ 페이지 구성 닫기")
            self.btn_organize_pages.setStyleSheet("background-color: #7C3AED; color: white; font-weight: bold;")
            self.center_stack.setCurrentIndex(1)
            if hasattr(self, "organize_grid"):
                if 0 <= self.current_page_idx < self.organize_grid.count():
                    self.organize_grid.setCurrentRow(self.current_page_idx)
                    self.organize_grid.scrollToItem(self.organize_grid.item(self.current_page_idx))
                self.organize_grid.setFocus()
            self.status_bar.showMessage("📑 페이지 구성 모드: 썸네일을 드래그하여 순서를 변경하거나, 마우스를 올려 회전/삭제/추출할 수 있습니다. (더블클릭 또는 Esc: 완료)")
        else:
            if self.page_view_mode == "continuous":
                self.center_stack.setCurrentIndex(3)
                self.continuous_scroll_area.continuous_canvas.set_document(self.doc, self.base_pdf_bytes, self.canvas.zoom)
            else:
                self.center_stack.setCurrentIndex(0)
            self.left_panel.show()
            is_right_open = bool(hasattr(self, "btn_toggle_right_panel") and self.btn_toggle_right_panel.isChecked())
            self.right_panel.setVisible(is_right_open)
            if getattr(self, "app_mode", "view") == "edit":
                self.tb_tools.show()
                self.tb_tools.setEnabled(True)
            else:
                self.tb_tools.hide()
                self.tb_tools.setEnabled(False)
            if hasattr(self, "_saved_splitter_sizes") and self._saved_splitter_sizes and sum(self._saved_splitter_sizes) > 600:
                self.main_splitter.setSizes(self._saved_splitter_sizes)
            else:
                total_w = self.width()
                lw = 205
                if is_right_open:
                    rw = getattr(self, "_last_right_panel_width", 345)
                    self.main_splitter.setSizes([lw, max(400, total_w - lw - rw), rw])
                else:
                    self.main_splitter.setSizes([lw, max(400, total_w - lw), 0])
            self.btn_organize_pages.setText("📑 페이지 구성")
            self.btn_organize_pages.setStyleSheet("background-color: #2563EB; color: white; border-color: #60A5FA; font-weight: bold;")
            sel_items = self.organize_grid.selectedIndexes() if hasattr(self, "organize_grid") else []
            if sel_items:
                self.go_to_page(sel_items[0].row())
            elif self.page_view_mode == "continuous":
                self.continuous_scroll_area.scroll_to_page(self.current_page_idx)
            else:
                self.go_to_page(self.current_page_idx)
            self.canvas.setFocus()

    def _step_organize_grid_zoom(self, step: int):
        """Steps Organize Pages grid card size via Ctrl + Mouse Wheel (zoom in/out)."""
        if not hasattr(self, "org_size_slider"):
            return
        curr_val = self.org_size_slider.value()
        delta = step * 15
        new_val = max(self.org_size_slider.minimum(), min(self.org_size_slider.maximum(), curr_val + delta))
        self.org_size_slider.setValue(new_val)

    def _on_org_size_slider_changed(self, val: int):
        card_w = val
        card_h = int(val * 1.33)
        self.organize_delegate.card_size = QSize(card_w, card_h)
        self.organize_grid.setIconSize(QSize(card_w - 20, card_h - 40))
        self.organize_grid.scheduleDelayedItemsLayout()

    def _on_organize_item_double_clicked(self, item: QListWidgetItem):
        row = self.organize_grid.row(item)
        if row >= 0:
            self.current_page_idx = row
        self.toggle_organize_pages(False)

    def _apply_pages_reorder(self, selected_rows: List[int], insert_idx: int):
        """
        Reorders document pages by moving selected_rows to insert_idx.
        Supports both single-page and multi-page drag-and-drop operations,
        preserving all in-flight edits and updating active tabs and undo history.
        """
        if not self.doc or not selected_rows:
            return
        total = len(self.doc)
        order = list(range(total))
        remaining = [x for x in order if x not in selected_rows]
        insert_pos_in_remaining = sum(1 for x in order[:insert_idx] if x not in selected_rows)
        new_order = remaining[:insert_pos_in_remaining] + selected_rows + remaining[insert_pos_in_remaining:]
        if new_order == order:
            return

        committed = self._build_committed_document()
        if not committed:
            return

        committed.select(new_order)
        self.base_pdf_bytes = committed.tobytes(garbage=3, deflate=True)
        committed.close()
        self.doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
        self.page_objects.clear()

        # Destination index of first moved page
        dest_first = new_order.index(selected_rows[0])

        if 0 <= self.active_tab_idx < len(self.doc_tabs):
            tab = self.doc_tabs[self.active_tab_idx]
            tab.doc = self.doc
            tab.base_pdf_bytes = self.base_pdf_bytes
            tab.page_objects = {}
            tab.current_page_idx = dest_first
            tab.is_modified = True

        desc = f"페이지 순서 변경 ({', '.join(str(r + 1) for r in selected_rows)}p)"
        self._push_undo_snapshot(desc)
        self._rebuild_thumbnails()
        self.go_to_page(dest_first)

        if hasattr(self, "organize_grid") and 0 <= dest_first < self.organize_grid.count():
            self.organize_grid.setCurrentRow(dest_first)
            self.organize_grid.scrollToItem(self.organize_grid.item(dest_first))

        if hasattr(self, "continuous_scroll_area"):
            self.continuous_scroll_area.continuous_canvas.set_document(self.doc, self.base_pdf_bytes, self.canvas.zoom)

        self._set_modified(True)
        if len(selected_rows) == 1:
            self.status_bar.showMessage(f"📑 페이지 순서가 변경되었습니다: {selected_rows[0] + 1}페이지 ➔ {dest_first + 1}페이지", 3000)
        else:
            self.status_bar.showMessage(f"📑 {len(selected_rows)}개 페이지 순서가 변경되었습니다: {dest_first + 1}페이지 위치로 이동", 3000)

    def _apply_page_move(self, start: int, dest_idx: int):
        """Backward-compatible single-page move helper."""
        if dest_idx == start:
            return
        insert_idx = dest_idx + 1 if dest_idx > start else dest_idx
        self._apply_pages_reorder([start], insert_idx)

    def _show_organize_context_menu(self, pos):
        item = self.organize_grid.itemAt(pos)
        if not item:
            return
        sel_rows = self._get_active_selected_page_indices()
        row = self.organize_grid.row(item)
        if row not in sel_rows:
            self.organize_grid.setCurrentRow(row)
            sel_rows = [row]

        count = len(sel_rows)
        menu = QMenu(self)
        if count == 1:
            act_rot_r = menu.addAction("↻ 오른쪽으로 90° 회전")
            act_rot_l = menu.addAction("↺ 왼쪽으로 90° 회전")
            act_rot_r.triggered.connect(lambda: self.rotate_page(row, 90))
            act_rot_l.triggered.connect(lambda: self.rotate_page(row, -90))
            menu.addSeparator()
            act_ins_b = menu.addAction("➕ 여기에 빈 페이지 삽입")
            act_ins_b.triggered.connect(self.insert_blank_page)
            act_ins_pdf = menu.addAction("📁 다른 PDF 파일 삽입...")
            act_ins_pdf.triggered.connect(self.insert_pdf_pages)
            menu.addSeparator()
            act_del = menu.addAction("🗑️ 이 페이지 삭제")
            act_del.triggered.connect(lambda: self.delete_page(row))
            act_ext = menu.addAction("📤 이 페이지를 별도 PDF로 추출")
            act_ext.triggered.connect(lambda: self.extract_page(row))
        else:
            act_rot_r = menu.addAction(f"↻ 선택한 {count}개 페이지 오른쪽으로 90° 회전")
            act_rot_l = menu.addAction(f"↺ 선택한 {count}개 페이지 왼쪽으로 90° 회전")
            act_rot_r.triggered.connect(lambda: self.rotate_selected_pages(90))
            act_rot_l.triggered.connect(lambda: self.rotate_selected_pages(-90))
            menu.addSeparator()
            act_del = menu.addAction(f"🗑️ 선택한 {count}개 페이지 삭제")
            act_del.triggered.connect(self.delete_selected_pages)
            act_ext = menu.addAction(f"📤 선택한 {count}개 페이지를 별도 PDF로 추출")
            act_ext.triggered.connect(self.extract_selected_pages)

        menu.addSeparator()
        act_sel_all = menu.addAction("전체 선택 (Ctrl+A)")
        act_sel_all.triggered.connect(self.organize_grid.selectAll)

        menu.exec(self.organize_grid.mapToGlobal(pos))

    def eventFilter(self, watched, event):
        """Global Application Event Filter: Catches Escape key globally and Bracket keys for sibling navigation."""
        if event.type() == QEvent.Type.KeyPress:
            # F2 Shortcut: Rename active PDF file in view mode (nomacs style)
            if event.key() == Qt.Key.Key_F2:
                focus_w = QApplication.focusWidget()
                is_text_input = isinstance(focus_w, (QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox))
                is_inline_editing = bool(
                    hasattr(self, "canvas") and getattr(self.canvas, "_inline_editing_obj", None) is not None
                )
                if not is_text_input and not is_inline_editing:
                    self.rename_current_file()
                    return True

            # Sibling PDF Navigation with '[' and ']' keys when not editing text
            if event.key() in (Qt.Key.Key_BracketLeft, Qt.Key.Key_BracketRight):
                focus_w = QApplication.focusWidget()
                is_text_input = isinstance(focus_w, (QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox))
                is_inline_editing = bool(
                    hasattr(self, "canvas") and getattr(self.canvas, "_inline_editing_obj", None) is not None
                )
                if not is_text_input and not is_inline_editing:
                    direction = -1 if event.key() == Qt.Key.Key_BracketLeft else 1
                    self.navigate_sibling_pdf(direction)
                    return True

            # Page navigation with PageUp / PageDown keys (Single Page & Continuous Scroll)
            if event.key() in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
                focus_w = QApplication.focusWidget()
                is_text_input = isinstance(focus_w, (QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox))
                is_inline_editing = bool(
                    hasattr(self, "canvas") and getattr(self.canvas, "_inline_editing_obj", None) is not None
                )
                modal = QApplication.activeModalWidget()
                if not is_text_input and not is_inline_editing and modal is None:
                    if hasattr(self, "center_stack") and self.center_stack.currentIndex() in (0, 3):
                        if not self.doc or len(self.doc) == 0:
                            return True
                        if len(self.doc) == 1:
                            self.status_bar.showMessage("단일 페이지 문서입니다 (총 1페이지).", 1500)
                            return True
                        if event.key() == Qt.Key.Key_PageUp:
                            self.prev_page()
                            return True
                        elif event.key() == Qt.Key.Key_PageDown:
                            self.next_page()
                            return True

            if event.key() == Qt.Key.Key_Escape:
                # 1. 만약 페이지 구성(Organize Pages) 화면이 열려 있다면 최우선으로 즉시 닫기!
                if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 1:
                    self.toggle_organize_pages(False)
                    return True

                # 2. 인라인 텍스트 편집 중이라면 커밋 후 종료
                if hasattr(self, "canvas") and getattr(self.canvas, "_inline_editing_obj", None) is not None:
                    self.canvas.commit_inline_edit()
                    return True

                # 3. 검색창에 포커스가 있거나 검색어가 입력되어 있거나 노란색 검색 하이라이트가 남아있는 경우 검색 즉시 초기화!
                is_search_focused = bool(hasattr(self, "search_input") and self.search_input.hasFocus())
                has_search_active = bool(
                    (hasattr(self, "search_input") and self.search_input.text().strip())
                    or getattr(self, "_search_all_hits", None)
                    or (hasattr(self, "canvas") and getattr(self.canvas, "search_rects", None))
                    or (
                        hasattr(self, "continuous_scroll_area")
                        and getattr(self.continuous_scroll_area.continuous_canvas, "search_results", None)
                    )
                )
                if is_search_focused or has_search_active:
                    self.clear_search_and_input()
                    return True

                # 4. 편집 모드라면 보기 모드로 복귀
                if getattr(self, "app_mode", "view") == "edit":
                    self.switch_to_view_mode()
                    return True

        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._on_global_escape_pressed()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_F2:
            self.rename_current_file()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_PageUp:
            self.prev_page()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_PageDown:
            self.next_page()
            event.accept()
            return
        super().keyPressEvent(event)

    def _show_thumb_context_menu(self, pos):
        item = self.thumb_list.itemAt(pos)
        if not item:
            return
        sel_rows = self._get_active_selected_page_indices()
        row = self.thumb_list.row(item)
        if row not in sel_rows:
            self.thumb_list.setCurrentRow(row)
            sel_rows = [row]

        count = len(sel_rows)
        menu = QMenu(self)
        if count == 1:
            self.go_to_page(row)
            act_rot_r = menu.addAction("↻ 오른쪽으로 90° 회전")
            act_rot_l = menu.addAction("↺ 왼쪽으로 90° 회전")
            act_ext = menu.addAction("📤 이 페이지 추출 (새 PDF)")
            menu.addSeparator()
            act_up = menu.addAction("▲ 페이지 위로 이동")
            act_down = menu.addAction("▼ 페이지 아래로 이동")
            menu.addSeparator()
            act_del = menu.addAction("🗑️ 이 페이지 삭제")

            chosen = menu.exec(self.thumb_list.mapToGlobal(pos))
            if chosen == act_rot_r:
                self.rotate_page(row, 90)
            elif chosen == act_rot_l:
                self.rotate_page(row, -90)
            elif chosen == act_ext:
                self.extract_page(row)
            elif chosen == act_up and row > 0:
                self._apply_page_move(row, row - 1)
            elif chosen == act_down and self.doc and row < len(self.doc) - 1:
                self._apply_page_move(row, row + 1)
            elif chosen == act_del:
                self.delete_page(row)
        else:
            act_b_rot_r = menu.addAction(f"↻ 선택한 {count}개 페이지 우로 90° 회전")
            act_b_rot_l = menu.addAction(f"↺ 선택한 {count}개 페이지 좌로 90° 회전")
            act_b_ext = menu.addAction(f"📤 선택한 {count}개 페이지 추출 (새 PDF)")
            menu.addSeparator()
            act_b_del = menu.addAction(f"🗑️ 선택한 {count}개 페이지 삭제")

            chosen = menu.exec(self.thumb_list.mapToGlobal(pos))
            if chosen == act_b_rot_r:
                self.rotate_selected_pages(90)
            elif chosen == act_b_rot_l:
                self.rotate_selected_pages(-90)
            elif chosen == act_b_ext:
                self.extract_selected_pages()
            elif chosen == act_b_del:
                self.delete_selected_pages()

    # -----------------------------------------------------------------
    # Tool Modes, Partial Block Selection, Shape Re-Editing & Inspector
    # -----------------------------------------------------------------
    def set_tool_mode(self, mode: str):
        self.canvas.commit_inline_edit()
        self.canvas.tool_mode = mode
        if mode in self.tool_buttons:
            self.tool_buttons[mode].setChecked(True)
        self.canvas.update()
        mode_names = {
            "inplace_text": "기존 텍스트 한글 편집 — 수정할 단어나 문구만 마우스로 드래그하거나 클릭하여 부분 수정하세요.",
            "free_text": "새 한글 텍스트 추가 모드 — 원하는 위치를 클릭하여 한글 텍스트 상자를 만드세요.",
            "select": "객체 선택/이동 모드 — 추가한 텍스트 상자나 도형을 클릭(또는 더블클릭)해 편집·이동·크기 조절·삭제하세요.",
            "rect": "사각형 그리기 모드 — 빈 곳 드래그 시 새 사각형 생성, 기존 도형 클릭/더블클릭 시 해당 도형 재편집!",
            "ellipse": "원/타원 그리기 모드 — 빈 곳 드래그 시 새 원 생성, 기존 도형 클릭/더블클릭 시 해당 도형 재편집!",
            "line": "직선 그리기 모드 — 빈 곳 드래그 시 새 직선 생성, 기존 도형 클릭/더블클릭 시 해당 도형 재편집!",
            "arrow": "화살표 그리기 모드 — 빈 곳 드래그 시 새 화살표 생성, 기존 도형 클릭/더블클릭 시 해당 도형 재편집!",
            "highlight": "형광펜 하이라이트 모드 — 강조할 영역을 마우스로 드래그하세요.",
            "eraser": "🧹 지우개 모드 — 원래 파일의 글자, 로고, 그림, 표 또는 추가 객체를 마우스 드래그로 깨끗하게 지웁니다 (화이트아웃).",
        }
        self.status_bar.showMessage(mode_names.get(mode, ""))

    def _on_thumb_selected(self, row: int):
        if row >= 0 and row != self.current_page_idx:
            self.go_to_page(row)

    def _on_canvas_shape_double_clicked(self, obj: PageEditObject):
        """Opens the ShapeQuickEditDialog when any shape is double-clicked on the PDF canvas."""
        if obj is None:
            return
        dlg = ShapeQuickEditDialog(obj, self.font_registry, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.delete_requested:
                self.delete_selected_object()
            else:
                dlg.apply_to_object()
                self._on_canvas_object_selected(obj)
                self._push_undo_snapshot("도형 상세 편집")
                self.canvas.update()
                self.status_bar.showMessage("✅ 도형 속성이 업데이트되었습니다.")

    def _on_canvas_selection_span_changed(self, obj: PageEditObject, s0: int, s1: int):
        self._active_text_sel_range = (s0, s1)
        self._update_block_scope_indicator(obj, s0, s1)

    def _on_inspector_selection_changed(self):
        if self._suppress_inspector_signals:
            return
        obj = self.canvas.selected_obj
        if obj is not None and obj.kind in ("inplace_text", "free_text"):
            c = self.inspector_text_edit.textCursor()
            s0, s1 = c.selectionStart(), c.selectionEnd()
            self._active_text_sel_range = (s0, s1)
            self.canvas.last_sel_range = (s0, s1)
            self._update_block_scope_indicator(obj, s0, s1)

    def _update_block_scope_indicator(self, obj: Optional[PageEditObject], s0: int, s1: int):
        if not hasattr(self, "block_scope_lbl"):
            return
        if obj is None or obj.kind not in ("inplace_text", "free_text", "rect", "ellipse"):
            self.block_scope_lbl.setText("-")
            return
        if s1 > s0 and (s1 - s0) < len(obj.text):
            sub = obj.text[s0:s1]
            self.block_scope_lbl.setText(f"선택 블록만 적용 ('{sub[:12]}')")
            col = "#FBBF24" if self.is_dark_effective else "#D97706"
            self.block_scope_lbl.setStyleSheet(f"color: {col}; font-weight: bold;")
        else:
            self.block_scope_lbl.setText("상자 내 텍스트 전체 적용")
            col = "#34D399" if self.is_dark_effective else "#059669"
            self.block_scope_lbl.setStyleSheet(f"color: {col}; font-weight: bold;")

    def _on_canvas_object_selected(self, obj: Optional[PageEditObject]):
        self._suppress_inspector_signals = True
        self._active_text_sel_range = self.canvas.last_sel_range
        if obj is None:
            self.sel_info_lbl.setText("선택된 객체 없음 (새 객체 기본 스타일 설정)")
            self.orig_font_lbl.setText("-")
            self.block_scope_lbl.setText("-")
            self.inspector_text_edit.setPlainText("")
            self.inspector_text_edit.setEnabled(False)
        else:
            kind_kr = {
                "inplace_text": "기존 PDF 텍스트 한글 수정",
                "free_text": "새 한글 텍스트 상자",
                "rect": "사각형 도형 (핸들 드래그 / 더블클릭 편집)",
                "ellipse": "원/타원 도형 (핸들 드래그 / 더블클릭 편집)",
                "line": "직선 도형 (끝점 드래그 / 더블클릭 편집)",
                "arrow": "화살표 도형 (끝점 드래그 / 더블클릭 편집)",
                "highlight": "형광펜 하이라이트",
                "eraser": "🧹 영역 지우개 (화이트아웃 / 더블클릭 편집)",
            }.get(obj.kind, obj.kind)
            self.sel_info_lbl.setText(f"선택됨: [{kind_kr}]")
            self.orig_font_lbl.setText(obj.orig_pdf_font if obj.orig_pdf_font else "(신규 객체)")
            self._update_block_scope_indicator(obj, *self._active_text_sel_range)

            idx = self.font_combo.findData(obj.font_key)
            if idx >= 0:
                self.font_combo.setCurrentIndex(idx)
            self.font_size_spin.setValue(obj.font_size)
            self.bold_chk.setChecked(obj.bold)
            self.chk_redact_stream.setChecked(obj.redact_stream_text)
            self.chk_redact_stream.setEnabled(obj.kind == "inplace_text")

            self._update_color_btn_style(self.btn_text_color, obj.text_color)
            self._update_color_btn_style(self.btn_stroke_color, obj.stroke_color)
            self._update_color_btn_style(self.btn_fill_color, obj.fill_color)

            self.stroke_width_spin.setValue(obj.stroke_width)
            self.chk_use_fill.setChecked(obj.use_fill)
            self.opacity_slider.setValue(int(round(obj.opacity * 100)))

            is_txt = obj.kind in ("inplace_text", "free_text", "rect", "ellipse")
            self.inspector_text_edit.setEnabled(is_txt)
            if is_txt and self.inspector_text_edit.toPlainText() != obj.text:
                self.inspector_text_edit.setPlainText(obj.text)
            elif not is_txt:
                self.inspector_text_edit.setPlainText("")
        self._suppress_inspector_signals = False

    def _apply_text_style_delta(
        self,
        font_key: Optional[str] = None,
        font_size: Optional[float] = None,
        bold: Optional[bool] = None,
        color: Optional[List[int]] = None,
    ):
        obj = self.canvas.selected_obj
        if obj is None or obj.kind not in ("inplace_text", "free_text", "rect", "ellipse"):
            return
        s0, s1 = self._active_text_sel_range
        apply_partial_run_style(obj, s0, s1, font_key=font_key, font_size=font_size, bold=bold, color=color)
        if s0 >= s1 or (s0 == 0 and s1 >= len(obj.text)):
            if font_key is not None:
                obj.font_key = font_key
            if font_size is not None:
                obj.font_size = font_size
            if bold is not None:
                obj.bold = bold
            if color is not None:
                obj.text_color = list(color)

        self.canvas._auto_adjust_text_rect(obj)
        if self.canvas._inline_editing_obj is obj:
            self.canvas.refresh_inline_editor_from_runs(obj, preserve_selection=True)
            self.canvas._reposition_inline_editor(obj)
        self._push_undo_snapshot("텍스트 서식 변경")
        self.canvas.update()

    def _on_font_family_changed(self):
        if self._suppress_inspector_signals:
            return
        fkey = self.font_combo.currentData() or self.font_registry.default_key()
        self.canvas.default_font_key = fkey
        self._apply_text_style_delta(font_key=fkey)

    def _on_font_size_changed(self):
        if self._suppress_inspector_signals:
            return
        fsize = self.font_size_spin.value()
        self.canvas.default_font_size = fsize
        self._apply_text_style_delta(font_size=fsize)

    def _on_bold_changed(self):
        if self._suppress_inspector_signals:
            return
        is_b = self.bold_chk.isChecked()
        self._apply_text_style_delta(bold=is_b)

    def _on_shape_style_changed(self):
        if self._suppress_inspector_signals:
            return
        sw = self.stroke_width_spin.value()
        use_f = self.chk_use_fill.isChecked()
        opac = self.opacity_slider.value() / 100.0

        self.canvas.default_stroke_width = sw
        self.canvas.default_use_fill = use_f
        self.canvas.default_opacity = opac

        obj = self.canvas.selected_obj
        if obj is not None:
            obj.stroke_width = sw
            obj.use_fill = use_f
            obj.opacity = opac
            self._push_undo_snapshot("도형 스타일 변경")
            self.canvas.update()

    def _on_redact_mode_toggled(self, checked: bool):
        if self._suppress_inspector_signals:
            return
        obj = self.canvas.selected_obj
        if obj is not None and obj.kind == "inplace_text":
            obj.redact_stream_text = checked
            self._set_modified(True)
            self._render_current_page()

    def _on_inspector_text_edited(self):
        if self._suppress_inspector_signals:
            return
        obj = self.canvas.selected_obj
        if obj is not None and obj.kind in ("inplace_text", "free_text", "rect", "ellipse"):
            new_t = self.inspector_text_edit.toPlainText().rstrip("\r\n")
            if obj.text != new_t:
                sync_runs_with_edited_text(obj, new_t)
                self.canvas._auto_adjust_text_rect(obj)
                if self.canvas._inline_editing_obj is obj:
                    self.canvas.refresh_inline_editor_from_runs(obj, preserve_selection=False)
                    self.canvas._reposition_inline_editor(obj)
                self._set_modified(True)
                self.canvas.update()

    def _update_color_btn_style(self, btn: QPushButton, rgb: List[int]):
        r, g, b = rgb
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        fg = "#111827" if lum > 140 else "#FFFFFF"
        btn.setStyleSheet(
            f"background-color: rgb({r}, {g}, {b}); color: {fg}; font-weight: bold; border: 1px solid #9CA3AF;"
        )

    def _pick_text_color(self):
        init = self.canvas.selected_obj.text_color if self.canvas.selected_obj else self.canvas.default_text_color
        col = QColorDialog.getColor(QColor(*init), self, "글자 색상 선택")
        if col.isValid():
            rgb = [col.red(), col.green(), col.blue()]
            self.canvas.default_text_color = list(rgb)
            self._update_color_btn_style(self.btn_text_color, rgb)
            self._apply_text_style_delta(color=rgb)

    def _pick_stroke_color(self):
        init = self.canvas.selected_obj.stroke_color if self.canvas.selected_obj else self.canvas.default_stroke_color
        col = QColorDialog.getColor(QColor(*init), self, "선 색상 선택")
        if col.isValid():
            rgb = [col.red(), col.green(), col.blue()]
            self.canvas.default_stroke_color = list(rgb)
            self._update_color_btn_style(self.btn_stroke_color, rgb)
            if self.canvas.selected_obj:
                self.canvas.selected_obj.stroke_color = list(rgb)
                self._push_undo_snapshot("선 색상 변경")
                self.canvas.update()

    def _pick_fill_color(self):
        init = self.canvas.selected_obj.fill_color if self.canvas.selected_obj else self.canvas.default_fill_color
        col = QColorDialog.getColor(QColor(*init), self, "채우기 색상 선택")
        if col.isValid():
            rgb = [col.red(), col.green(), col.blue()]
            self.canvas.default_fill_color = list(rgb)
            self._update_color_btn_style(self.btn_fill_color, rgb)
            if self.canvas.selected_obj:
                self.canvas.selected_obj.fill_color = list(rgb)
                self.canvas.selected_obj.use_fill = True
                self.chk_use_fill.setChecked(True)
                self._push_undo_snapshot("채우기 색상 변경")
                self.canvas.update()

    def duplicate_selected_object(self):
        obj = self.canvas.selected_obj
        if not obj:
            return
        dup = copy.deepcopy(obj)
        dup.obj_id = str(uuid.uuid4())[:8]
        if dup.kind == "inplace_text":
            dup.kind = "free_text"
            dup.orig_bbox = None
        dup.rect = [dup.rect[0] + 15.0, dup.rect[1] + 15.0, dup.rect[2] + 15.0, dup.rect[3] + 15.0]
        self.canvas.objects.append(dup)
        self.canvas.selected_obj = dup
        self._on_canvas_object_selected(dup)
        self._push_undo_snapshot("객체 복제")
        self.canvas.update()

    def delete_selected_object(self):
        obj = self.canvas.selected_obj
        if not obj:
            return
        self.canvas.commit_inline_edit()
        if obj in self.canvas.objects:
            self.canvas.objects.remove(obj)
        self.canvas.selected_obj = None
        self._on_canvas_object_selected(None)
        self._push_undo_snapshot("객체 삭제 / 원본 복원")
        self._render_current_page()

    # -----------------------------------------------------------------
    # Undo / Redo Engine
    # -----------------------------------------------------------------
    def _on_canvas_state_changed(self, desc: str):
        self._push_undo_snapshot(desc)
        self._render_current_page()

    def _serialize_state(self) -> dict:
        return {
            "page_idx": self.current_page_idx,
            "base_pdf_bytes": self.base_pdf_bytes,
            "objects": {
                k: [copy.deepcopy(asdict(o)) for o in v]
                for k, v in self.page_objects.items()
            },
        }

    def _restore_serialized_state(self, snap: dict):
        self.canvas.commit_inline_edit()
        rebuild_needed = False
        if "base_pdf_bytes" in snap and snap["base_pdf_bytes"] and snap["base_pdf_bytes"] != self.base_pdf_bytes:
            self.base_pdf_bytes = snap["base_pdf_bytes"]
            self.doc = fitz.open(stream=self.base_pdf_bytes, filetype="pdf")
            rebuild_needed = True

        self.page_objects = {
            int(k): [PageEditObject(**d) for d in v]
            for k, v in snap["objects"].items()
        }

        if rebuild_needed:
            self._rebuild_thumbnails()
            if hasattr(self, "continuous_scroll_area"):
                self.continuous_scroll_area.continuous_canvas.set_document(self.doc, self.base_pdf_bytes, self.canvas.zoom)

        self.go_to_page(snap.get("page_idx", self.current_page_idx))

    def _push_undo_snapshot(self, desc: str = ""):
        snap = self._serialize_state()
        if self.undo_stack and self.undo_stack[-1] == snap:
            return
        self.undo_stack.append(snap)
        if len(self.undo_stack) > 40:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        if not self._loading_file and len(self.undo_stack) > 1:
            self._set_modified(True)

    def undo(self):
        self.canvas.commit_inline_edit()
        if len(self.undo_stack) <= 1:
            self.status_bar.showMessage("더 이상 실행 취소할 작업이 없습니다.")
            return
        cur = self.undo_stack.pop()
        self.redo_stack.append(cur)
        self._restore_serialized_state(self.undo_stack[-1])
        self._set_modified(len(self.undo_stack) > 1)
        self.status_bar.showMessage("↩ 실행 취소 완료")

    def redo(self):
        self.canvas.commit_inline_edit()
        if not self.redo_stack:
            self.status_bar.showMessage("더 이상 다시 실행할 작업이 없습니다.")
            return
        nxt = self.redo_stack.pop()
        self.undo_stack.append(nxt)
        self._restore_serialized_state(nxt)
        self._set_modified(True)
        self.status_bar.showMessage("↪ 다시 실행 완료")

    # -----------------------------------------------------------------
    # Zoom & Search
    # -----------------------------------------------------------------
    def _on_zoom_combo_changed(self, text: str):
        try:
            val = float(text.replace("%", "").strip()) / 100.0
            self.canvas.zoom = max(0.3, min(4.0, val))
            if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 3:
                self.continuous_scroll_area.continuous_canvas.set_zoom(self.canvas.zoom)
                self.continuous_scroll_area.scroll_to_page(self.current_page_idx)
            else:
                self._render_current_page()
        except Exception:
            pass

    def _set_zoom_display(self, zoom_val: float):
        """Safely updates zoom combo text without dropping to default on non-preset values."""
        if not hasattr(self, "zoom_combo"):
            return
        txt = f"{int(round(zoom_val * 100))}%"
        self.zoom_combo.blockSignals(True)
        idx = self.zoom_combo.findText(txt)
        if idx >= 0:
            self.zoom_combo.setCurrentIndex(idx)
        else:
            if self.zoom_combo.isEditable():
                self.zoom_combo.setEditText(txt)
            else:
                self.zoom_combo.addItem(txt)
                self.zoom_combo.setCurrentText(txt)
        self.zoom_combo.blockSignals(False)

    def step_zoom(self, direction: int):
        new_z = round(self.canvas.zoom + direction * 0.25, 2)
        new_z = max(0.5, min(3.0, new_z))
        self.canvas.zoom = new_z
        self._set_zoom_display(new_z)
        if 0 <= self.active_tab_idx < len(self.doc_tabs):
            self.doc_tabs[self.active_tab_idx].zoom = self.canvas.zoom
        if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 3:
            self.continuous_scroll_area.continuous_canvas.set_zoom(self.canvas.zoom)
            self.continuous_scroll_area.scroll_to_page(self.current_page_idx)
        else:
            self._render_current_page()

    def fit_to_width(self, max_cap: Optional[float] = None):
        if not self.doc:
            return
        if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 3:
            vp_w = self.continuous_scroll_area.viewport().width()
            if vp_w < 400 and self.width() > 600:
                vp_w = self.width() - 240
            avail_w = max(300, vp_w - 60)
            pw = self.doc[self.current_page_idx].rect.width
            if pw > 0:
                calc_z = round(avail_w / pw, 2)
                if max_cap is not None:
                    calc_z = min(max_cap, calc_z)
                self.canvas.zoom = max(0.4, min(3.0, calc_z))
            self._set_zoom_display(self.canvas.zoom)
            if 0 <= self.active_tab_idx < len(self.doc_tabs):
                self.doc_tabs[self.active_tab_idx].zoom = self.canvas.zoom
            self.continuous_scroll_area.continuous_canvas.set_zoom(self.canvas.zoom)
            self.continuous_scroll_area.scroll_to_page(self.current_page_idx)
            return

        vp_w = self.scroll_area.viewport().width()
        if vp_w < 400 and self.width() > 600:
            vp_w = self.width() - 240
        avail_w = max(300, vp_w - 70)
        pw = self.canvas.page_rect_pt[0]
        if pw > 0:
            calc_z = round(avail_w / pw, 2)
            if max_cap is not None:
                calc_z = min(max_cap, calc_z)
            self.canvas.zoom = max(0.4, min(3.0, calc_z))
        self._set_zoom_display(self.canvas.zoom)
        if 0 <= self.active_tab_idx < len(self.doc_tabs):
            self.doc_tabs[self.active_tab_idx].zoom = self.canvas.zoom
        self._render_current_page()

    def apply_smart_open_zoom(self):
        """150%로 열되 창 너비를 벗어나면 창 너비에 맞게 축소하고, 창 안에 여유가 있으면 150% 유지"""
        self.fit_to_width(max_cap=1.5)

    def fit_to_height(self):
        if not self.doc:
            return
        if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 3:
            avail_h = max(300, self.continuous_scroll_area.viewport().height() - 60)
            ph = self.doc[self.current_page_idx].rect.height
            if ph > 0:
                self.canvas.zoom = max(0.4, min(3.0, round(avail_h / ph, 2)))
            self._set_zoom_display(self.canvas.zoom)
            if 0 <= self.active_tab_idx < len(self.doc_tabs):
                self.doc_tabs[self.active_tab_idx].zoom = self.canvas.zoom
            self.continuous_scroll_area.continuous_canvas.set_zoom(self.canvas.zoom)
            self.continuous_scroll_area.scroll_to_page(self.current_page_idx)
            return

        avail_h = max(300, self.scroll_area.viewport().height() - 70)
        ph = self.canvas.page_rect_pt[1]
        if ph > 0:
            self.canvas.zoom = max(0.4, min(3.0, round(avail_h / ph, 2)))
        self._set_zoom_display(self.canvas.zoom)
        if 0 <= self.active_tab_idx < len(self.doc_tabs):
            self.doc_tabs[self.active_tab_idx].zoom = self.canvas.zoom
        self._render_current_page()

    def fit_to_page(self):
        if not self.doc:
            return
        if hasattr(self, "center_stack") and self.center_stack.currentIndex() == 3:
            avail_w = max(300, self.continuous_scroll_area.viewport().width() - 60)
            avail_h = max(300, self.continuous_scroll_area.viewport().height() - 60)
            page = self.doc[self.current_page_idx]
            pw, ph = page.rect.width, page.rect.height
            if pw > 0 and ph > 0:
                z = min(avail_w / pw, avail_h / ph)
                self.canvas.zoom = max(0.4, min(3.0, round(z, 2)))
            self._set_zoom_display(self.canvas.zoom)
            if 0 <= self.active_tab_idx < len(self.doc_tabs):
                self.doc_tabs[self.active_tab_idx].zoom = self.canvas.zoom
            self.continuous_scroll_area.continuous_canvas.set_zoom(self.canvas.zoom)
            self.continuous_scroll_area.scroll_to_page(self.current_page_idx)
            return

        avail_w = max(300, self.scroll_area.viewport().width() - 70)
        avail_h = max(300, self.scroll_area.viewport().height() - 70)
        pw, ph = self.canvas.page_rect_pt
        if pw > 0 and ph > 0:
            z = min(avail_w / pw, avail_h / ph)
            self.canvas.zoom = max(0.4, min(3.0, round(z, 2)))
        self._set_zoom_display(self.canvas.zoom)
        if 0 <= self.active_tab_idx < len(self.doc_tabs):
            self.doc_tabs[self.active_tab_idx].zoom = self.canvas.zoom
        self._render_current_page()

    def run_search(self):
        query = self.search_input.text().strip()
        if not query or not self.doc or len(self.doc) == 0:
            self._clear_search()
            if hasattr(self, "status_bar"):
                self.status_bar.showMessage("🔍 검색어를 입력하세요.")
            return

        # 동일 검색어로 다시 검색창에서 Enter를 눌렀다면 다음 결과로 순환 점프
        if getattr(self, "_last_search_query", None) == query and getattr(self, "_search_all_hits", None):
            self.next_search_hit()
            return

        self._last_search_query = query
        self._search_all_hits = []
        self._search_results_by_page = {}

        # 문서 전체 페이지에서 검색어 좌표 전수 수집
        for p_idx in range(len(self.doc)):
            page = self.doc[p_idx]
            rects = page.search_for(query)
            if rects:
                r_tuples = [(r.x0, r.y0, r.x1, r.y1) for r in rects]
                self._search_results_by_page[p_idx] = r_tuples
                for r_idx, rt in enumerate(r_tuples):
                    self._search_all_hits.append((p_idx, r_idx, rt))

        if not self._search_all_hits:
            self._clear_search()
            if hasattr(self, "status_bar"):
                self.status_bar.showMessage(f"🔍 '{query}' 검색 결과가 없습니다.")
            return

        # 현재 열람 중인 페이지(current_page_idx)부터 시작하는 첫 번째 매칭 선택
        start_hit_idx = 0
        for idx, (p_idx, _, _) in enumerate(self._search_all_hits):
            if p_idx >= self.current_page_idx:
                start_hit_idx = idx
                break

        self._search_current_hit_idx = start_hit_idx
        self._apply_search_hit(self._search_current_hit_idx)

    def next_search_hit(self):
        if not getattr(self, "_search_all_hits", None):
            self.run_search()
            return
        self._search_current_hit_idx = (self._search_current_hit_idx + 1) % len(self._search_all_hits)
        self._apply_search_hit(self._search_current_hit_idx)

    def clear_search_and_input(self):
        """검색창 입력 내용과 본문 노란색 검색 하이라이트를 모두 초기화하고 포커스를 본문으로 복귀합니다."""
        if hasattr(self, "search_input"):
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)
            self.search_input.clearFocus()
        self._clear_search()
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage("🔍 검색이 초기화되었습니다.", 2000)
        # 활성 본문 뷰포트로 포커스 복귀
        if getattr(self, "page_view_mode", "single") == "continuous" and hasattr(self, "continuous_scroll_area"):
            self.continuous_scroll_area.setFocus()
        elif hasattr(self, "canvas"):
            self.canvas.setFocus()

    def _on_search_text_changed(self, text: str):
        """검색창의 텍스트가 지워지거나 비워졌을 때 노란색 검색 하이라이트를 즉시 제거합니다."""
        if not text.strip():
            # 검색창이 비워졌을 때(글자 지움 또는 x 버튼 클릭) 노란색 하이라이트 즉시 해제
            if getattr(self, "_search_all_hits", None) or (
                hasattr(self, "canvas") and getattr(self.canvas, "search_rects", None)
            ) or (
                hasattr(self, "continuous_scroll_area")
                and getattr(self.continuous_scroll_area.continuous_canvas, "search_results", None)
            ):
                self._clear_search()
                if hasattr(self, "status_bar"):
                    self.status_bar.showMessage("🔍 검색이 초기화되었습니다.", 1500)

    def _clear_search(self):
        self._search_all_hits = []
        self._search_results_by_page = {}
        self._search_current_hit_idx = -1
        self._last_search_query = ""
        if hasattr(self, "canvas"):
            self.canvas.search_rects = []
            self.canvas.current_search_idx = -1
            self.canvas.update()
        if hasattr(self, "continuous_scroll_area"):
            cc = self.continuous_scroll_area.continuous_canvas
            cc.search_results = {}
            cc.current_search_page = -1
            cc.current_search_rect_idx = -1
            cc.update()
        if hasattr(self, "status_bar") and self.status_bar.currentMessage().startswith("🔍 '"):
            self.status_bar.clearMessage()

    def _apply_search_hit(self, hit_idx: int):
        if not getattr(self, "_search_all_hits", None) or hit_idx < 0 or hit_idx >= len(self._search_all_hits):
            return

        p_idx, r_idx, rect = self._search_all_hits[hit_idx]
        total_hits = len(self._search_all_hits)
        query = getattr(self, "_last_search_query", "")

        # 1. 상태 표시줄 직관적 카운트 표시
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage(
                f"🔍 '{query}' 총 {total_hits}건 발견 (현재 {hit_idx + 1}/{total_hits}번째, {p_idx + 1}페이지)"
            )

        # 2. 뷰 모드별 노란색 형광펜 하이라이트 렌더링 및 뷰포트 정중앙 자동 스크롤 이동
        if self.page_view_mode == "continuous" and hasattr(self, "continuous_scroll_area"):
            cc = self.continuous_scroll_area.continuous_canvas
            cc.search_results = self._search_results_by_page
            cc.current_search_page = p_idx
            cc.current_search_rect_idx = r_idx
            cc.update()
            # 검색어가 화면 한가운데에 오도록 즉시 자동 스크롤 이동!
            self.continuous_scroll_area.scroll_to_rect(p_idx, rect)
            self.current_page_idx = p_idx
            if hasattr(self, "page_indicator_lbl"):
                self.page_indicator_lbl.setText(f"{p_idx + 1} / {len(self.doc)}")
            if hasattr(self, "thumb_list"):
                self.thumb_list.blockSignals(True)
                self.thumb_list.setCurrentRow(p_idx)
                self.thumb_list.blockSignals(False)
        else:
            if self.current_page_idx != p_idx:
                self.go_to_page(p_idx)
            if hasattr(self, "canvas"):
                self.canvas.search_rects = self._search_results_by_page.get(p_idx, [])
                self.canvas.current_search_idx = r_idx
                self.canvas.update()
                qr = self.canvas.pdf_rect_to_qrectf(rect)
                if hasattr(self, "scroll_area"):
                    self.scroll_area.ensureVisible(int(qr.center().x()), int(qr.center().y()), 180, 180)


def main():
    def _safe_excepthook(exc_type, exc_val, exc_tb):
        import traceback
        err_msg = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        print(f"[K-PDF Studio Unhandled Exception]\n{err_msg}", file=sys.stderr)

    sys.excepthook = _safe_excepthook

    app = QApplication(sys.argv)
    app.setApplicationName("K-PDF Studio")

    # Command-line argument parser: collect PDF / document files
    pdf_files_to_open = []
    force_new_window = False
    for arg in sys.argv[1:]:
        if arg in ("--new-window", "-n"):
            force_new_window = True
            continue
        cleaned = arg.strip(' "\'')
        if os.path.isfile(cleaned):
            pdf_files_to_open.append(os.path.abspath(cleaned))
        elif cleaned.lower().endswith((".pdf", ".ai", ".eps", ".xps", ".oxps")) and os.path.exists(cleaned):
            pdf_files_to_open.append(os.path.abspath(cleaned))

    # Single-instance IPC mechanism via QLocalServer / QLocalSocket
    user_tag = os.environ.get("USERNAME", "DefaultUser")
    server_name = f"KPDFStudio_SingleInstance_{user_tag}"
    local_server = None

    if not force_new_window:
        socket = QLocalSocket()
        socket.connectToServer(server_name)
        # Attempt connection to existing instance (timeout: 350ms)
        if socket.waitForConnected(350):
            try:
                payload = json.dumps({"files": pdf_files_to_open}).encode("utf-8")
                socket.write(payload)
                socket.waitForBytesWritten(1000)
                socket.disconnectFromServer()
            except Exception:
                pass
            if sys.platform == "win32":
                try:
                    # Allow running instance to take foreground focus
                    ctypes.windll.user32.AllowSetForegroundWindow(-1)
                except Exception:
                    pass
            sys.exit(0)

        # Connection failed: clean up any stale ghost server pipe and listen as master
        QLocalServer.removeServer(server_name)
        local_server = QLocalServer()
        if not local_server.listen(server_name):
            QLocalServer.removeServer(server_name)
            local_server.listen(server_name)

    icon_path = ensure_app_icon()
    if icon_path and os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    initial_file = pdf_files_to_open[0] if pdf_files_to_open else None
    win = KPDFStudioWindow(initial_pdf=initial_file)

    # If multiple files were passed on startup, open the rest in tabs
    if len(pdf_files_to_open) > 1:
        for extra in pdf_files_to_open[1:]:
            if os.path.exists(extra):
                win.open_pdf_in_tab(extra, make_active=False)

    if local_server:
        def _on_new_instance_connection():
            client_socket = local_server.nextPendingConnection()
            if not client_socket:
                return

            def _read_data():
                try:
                    raw_data = client_socket.readAll().data()
                    if raw_data:
                        msg = json.loads(raw_data.decode("utf-8"))
                        files = msg.get("files", [])
                        win.handle_external_open_files(files)
                    else:
                        win.bring_to_front()
                except Exception as e:
                    print(f"[SingleInstance IPC Error] {e}", file=sys.stderr)
                finally:
                    client_socket.close()

            client_socket.readyRead.connect(_read_data)
            if client_socket.bytesAvailable() > 0:
                _read_data()

        local_server.newConnection.connect(_on_new_instance_connection)

    win.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
