import sys
import io
import os
import winreg
import ctypes

if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

EXTENSIONS = [
    ".pdf", ".ai", ".eps", ".xps", ".oxps"
]
PROGID = "KPDFStudio.Document"
APP_NAME = "K-PDF Studio"
EXE_NAME = "KPDFStudio.exe"

def get_base_dir():
    # 1순위: 스크립트 위치 (__file__)
    try:
        cand = os.path.abspath(os.path.dirname(__file__))
        if os.path.exists(os.path.join(cand, EXE_NAME)):
            return cand
    except Exception:
        pass

    # 2순위: 현재 작업 디렉토리
    try:
        cwd = os.path.abspath(os.getcwd())
        if os.path.exists(os.path.join(cwd, EXE_NAME)):
            return cwd
    except Exception:
        pass

    # 3순위: 알려진 위치 폴백
    fallback = r"G:\내 드라이브\종합집계_260416\Tools_툴즈_260715\KPDFStudio"
    if os.path.exists(os.path.join(fallback, EXE_NAME)):
        return fallback

    return os.path.abspath(os.path.dirname(__file__))

def notify_shell():
    try:
        # SHCNE_ASSOCCHANGED = 0x08000000, SHCNF_IDLIST = 0
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:
        pass

def register():
    script_dir = get_base_dir()
    exe_path = os.path.join(script_dir, EXE_NAME)
    ico_path = os.path.join(script_dir, "app_icon.ico")

    if not os.path.exists(exe_path):
        print(f"[ERROR] {exe_path} not found!")
        return

    open_cmd = f'"{exe_path}" "%1"'

    # 1. ProgID 등록 (HKCU\Software\Classes\KPDFStudio.Document)
    prog_key = f"Software\\Classes\\{PROGID}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, prog_key) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "K-PDF Studio 문서")
        winreg.SetValueEx(k, "FriendlyTypeName", 0, winreg.REG_SZ, "K-PDF Studio PDF 문서")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{prog_key}\\DefaultIcon") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{ico_path}",0')

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{prog_key}\\shell\\open\\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, open_cmd)

    # 2. Applications 등록 (HKCU\Software\Classes\Applications\KPDFStudio.exe)
    app_key = f"Software\\Classes\\Applications\\{EXE_NAME}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_key) as k:
        winreg.SetValueEx(k, "FriendlyAppName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(k, "ApplicationCompany", 0, winreg.REG_SZ, APP_NAME)

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{app_key}\\DefaultIcon") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{ico_path}",0')

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{app_key}\\shell\\open\\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, open_cmd)

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{app_key}\\SupportedTypes") as k:
        for ext in EXTENSIONS:
            winreg.SetValueEx(k, ext, 0, winreg.REG_SZ, "")

    # 3. SystemFileAssociations (.pdf 우클릭 즉시 메뉴 & 연결 프로그램 등록)
    sfa_open_key = f"Software\\Classes\\SystemFileAssociations\\.pdf\\OpenWithList\\{EXE_NAME}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, sfa_open_key) as k:
        pass

    sfa_menu_key = f"Software\\Classes\\SystemFileAssociations\\.pdf\\shell\\KPDFStudio"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, sfa_menu_key) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "K-PDF Studio로 열기(&K)")
        winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, f'"{ico_path}",0')

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{sfa_menu_key}\\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, open_cmd)

    # 4. 확장자별 HKCU\Software\Classes 및 Explorer\FileExts 등록
    for ext in EXTENSIONS:
        # 4-1. Classes\{ext}\OpenWithProgids
        ext_key = f"Software\\Classes\\{ext}\\OpenWithProgids"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, ext_key) as k:
            winreg.SetValueEx(k, PROGID, 0, winreg.REG_NONE, b"")

        # 4-2. Classes\{ext}\OpenWithList\{EXE_NAME}
        owl_key = f"Software\\Classes\\{ext}\\OpenWithList\\{EXE_NAME}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, owl_key) as k:
            pass

        # 4-3. Explorer\FileExts\{ext}\OpenWithProgids
        fe_prog_key = f"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\{ext}\\OpenWithProgids"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, fe_prog_key) as k:
                winreg.SetValueEx(k, PROGID, 0, winreg.REG_NONE, b"")
        except Exception:
            pass

        # 4-4. Explorer\FileExts\{ext}\OpenWithList (MRU 추가)
        fe_owl_key = f"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\{ext}\\OpenWithList"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, fe_owl_key) as k:
                # 기존 값들 스캔
                existing = {}
                mru_val = ""
                idx = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(k, idx)
                        if name.lower() == "mrulist":
                            mru_val = val
                        else:
                            existing[name.lower()] = (name, val)
                        idx += 1
                    except OSError:
                        break

                target_letter = None
                for l_name, (orig_name, val) in existing.items():
                    if val.lower() == EXE_NAME.lower():
                        target_letter = orig_name
                        break

                if not target_letter:
                    # 새로운 문자 할당 (a-z)
                    for char in "abcdefghijklmnopqrstuvwxyz":
                        if char not in existing:
                            target_letter = char
                            break
                    if target_letter:
                        winreg.SetValueEx(k, target_letter, 0, winreg.REG_SZ, EXE_NAME)

                if target_letter:
                    # MRUList 맨 앞에 추가
                    new_mru = target_letter + mru_val.replace(target_letter, "")
                    winreg.SetValueEx(k, "MRUList", 0, winreg.REG_SZ, new_mru)
        except Exception:
            pass

    # 5. Windows 10/11 기본 앱(RegisteredApplications) 등록
    cap_key = "Software\\KPDFStudio\\Capabilities"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cap_key) as k:
        winreg.SetValueEx(k, "ApplicationName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(k, "ApplicationDescription", 0, winreg.REG_SZ, "K-PDF Studio - 초경량 한글 특화 PDF 뷰어 & 인플레이스 편집기")
        winreg.SetValueEx(k, "ApplicationIcon", 0, winreg.REG_SZ, f'"{ico_path}",0')

    file_assoc_key = f"{cap_key}\\FileAssociations"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, file_assoc_key) as k:
        for ext in EXTENSIONS:
            winreg.SetValueEx(k, ext, 0, winreg.REG_SZ, PROGID)

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\RegisteredApplications") as k:
        winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cap_key)

    notify_shell()
    print("=" * 65)
    print(f"  ✅ [성공] '{APP_NAME}' ({EXE_NAME}) 등록이 완벽하게 완료되었습니다!")
    print("=" * 65)
    print(f"  • 대상 실행 파일: {exe_path}")
    print(f"  • 대상 아이콘 파일: {ico_path}")
    print(f"  • 지원 포맷 ({len(EXTENSIONS)}종): {', '.join(EXTENSIONS)}")
    print("  • 적용 항목:")
    print("    1. PDF 파일 우클릭 시 'K-PDF Studio로 열기(K)' 바로가기 메뉴 추가")
    print("    2. '연결 프로그램' 서브메뉴에 'K-PDF Studio' 정식 아이콘과 함께 등록")
    print("    3. Windows 기본 앱 설정(RegisteredApplications) 정식 등록")
    print()

def unregister():
    def delete_subkeys(root, subkey):
        try:
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as k:
                while True:
                    try:
                        child = winreg.EnumKey(k, 0)
                        delete_subkeys(root, f"{subkey}\\{child}")
                    except OSError:
                        break
            winreg.DeleteKey(root, subkey)
        except OSError:
            pass

    delete_subkeys(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{PROGID}")
    delete_subkeys(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\Applications\\{EXE_NAME}")
    delete_subkeys(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\SystemFileAssociations\\.pdf\\OpenWithList\\{EXE_NAME}")
    delete_subkeys(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\SystemFileAssociations\\.pdf\\shell\\KPDFStudio")

    for ext in EXTENSIONS:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}\\OpenWithProgids", 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, PROGID)
        except OSError:
            pass
        delete_subkeys(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}\\OpenWithList\\{EXE_NAME}")

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\{ext}\\OpenWithProgids", 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, PROGID)
        except OSError:
            pass

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\RegisteredApplications", 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, APP_NAME)
    except OSError:
        pass

    delete_subkeys(winreg.HKEY_CURRENT_USER, "Software\\KPDFStudio")

    notify_shell()
    print("=" * 65)
    print(f"  🗑️ '{APP_NAME}' 등록 정보가 성공적으로 해제되었습니다.")
    print("=" * 65)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("--unregister", "-u", "/u"):
        unregister()
    else:
        register()
