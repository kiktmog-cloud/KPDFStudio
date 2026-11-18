import sys, io, os

if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

def find_pythonw():
    py_dir = os.path.dirname(sys.executable)
    candidate = os.path.join(py_dir, "pythonw.exe")
    if os.path.exists(candidate):
        return candidate
    return sys.executable

def make_shortcut(target_lnk, target_exe, arguments, work_dir, icon_path, description):
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(target_lnk)
        shortcut.TargetPath = target_exe
        if arguments:
            shortcut.Arguments = arguments
        shortcut.WorkingDirectory = work_dir
        if icon_path and os.path.exists(icon_path):
            shortcut.IconLocation = f"{icon_path},0"
        shortcut.Description = description
        shortcut.Save()
        return True
    except Exception:
        try:
            import subprocess, tempfile
            vbs_lines = [
                'Set ws = CreateObject("WScript.Shell")',
                f'Set sc = ws.CreateShortcut("{target_lnk}")',
                f'sc.TargetPath = "{target_exe}"',
            ]
            if arguments:
                arg_escaped = arguments.replace('"', '""')
                vbs_lines.append(f'sc.Arguments = "{arg_escaped}"')
            vbs_lines.append(f'sc.WorkingDirectory = "{work_dir}"')
            if icon_path and os.path.exists(icon_path):
                vbs_lines.append(f'sc.IconLocation = "{icon_path},0"')
            vbs_lines.append(f'sc.Description = "{description}"')
            vbs_lines.append('sc.Save')

            with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False, encoding="utf-8") as f:
                f.write("\r\n".join(vbs_lines))
                tmp_vbs = f.name

            res = subprocess.run(["cscript.exe", "//nologo", tmp_vbs], capture_output=True)
            if os.path.exists(tmp_vbs):
                os.remove(tmp_vbs)
            return res.returncode == 0
        except Exception:
            return False

def main():
    script_dir = os.path.abspath(os.path.dirname(__file__))
    py_script = os.path.join(script_dir, "kpdf_studio.py")
    ico_file = os.path.join(script_dir, "app_icon.ico")
    pythonw = find_pythonw()

    arguments = f'"{py_script}"'
    desc = "K-PDF Studio - 한국어 특화 초고속 PDF 뷰어 & 편집 스튜디오"

    # 1) 프로그램 폴더 바로가기
    folder_lnk = os.path.join(script_dir, "K-PDF Studio.lnk")
    ok1 = make_shortcut(folder_lnk, pythonw, arguments, script_dir, ico_file, desc)

    # 2) 바탕화면 바로가기
    desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    if not os.path.exists(desktop_dir):
        alt_desktop = os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "바탕 화면")
        if os.path.exists(alt_desktop):
            desktop_dir = alt_desktop
        else:
            desktop_dir = script_dir

    desktop_lnk = os.path.join(desktop_dir, "K-PDF Studio.lnk")
    ok2 = make_shortcut(desktop_lnk, pythonw, arguments, script_dir, ico_file, desc)

    print()
    print("=" * 60)
    if ok1 or ok2:
        print("  ✅ [성공] K-PDF Studio 바로가기 생성이 완료되었습니다!")
    else:
        print("  ⚠️ [경고] 바로가기 생성 중 일부 오류가 발생했습니다.")
    print("=" * 60)
    if ok1:
        print(f"1. 프로그램 폴더 바로가기 : {folder_lnk}")
    if ok2:
        print(f"2. 바탕화면 바로가기       : {desktop_lnk}")
    print()
    print("💡 윈도우 11 작업 표시줄 고정 팁:")
    print("   생성된 'K-PDF Studio.lnk' 바로가기 우클릭 -> [추가 옵션 표시] -> [작업 표시줄에 고정] 클릭!")
    print()

if __name__ == "__main__":
    main()
