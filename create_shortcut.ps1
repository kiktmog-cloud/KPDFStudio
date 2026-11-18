# K-PDF Studio 바로가기 생성 스크립트
$ErrorActionPreference = 'Stop'

$workDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $workDir) { $workDir = (Get-Location).Path }
$script = Join-Path $workDir "kpdf_studio.py"
$ico = Join-Path $workDir "app_icon.ico"

# pythonw.exe 탐색
$pyCmd = Get-Command pythonw -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
}
if ($pyCmd) {
    $pythonw = $pyCmd.Source
} else {
    $pythonw = "pythonw.exe"
}

$WshShell = New-Object -ComObject WScript.Shell

# 1. KPDFStudio 폴더 내 바로가기
$lnk1 = Join-Path $workDir "K-PDF Studio.lnk"
$s1 = $WshShell.CreateShortcut($lnk1)
$s1.TargetPath = $pythonw
$s1.Arguments = "`"$script`""
$s1.WorkingDirectory = $workDir
if (Test-Path $ico) {
    $s1.IconLocation = "$ico,0"
}
$s1.Description = "K-PDF Studio (한글 특화 PDF 뷰어 & 편집기)"
$s1.Save()

# 2. 바탕화면 바로가기
$desktop = [System.Environment]::GetFolderPath("Desktop")
$lnk2 = Join-Path $desktop "K-PDF Studio.lnk"
$s2 = $WshShell.CreateShortcut($lnk2)
$s2.TargetPath = $pythonw
$s2.Arguments = "`"$script`""
$s2.WorkingDirectory = $workDir
if (Test-Path $ico) {
    $s2.IconLocation = "$ico,0"
}
$s2.Description = "K-PDF Studio (한글 특화 PDF 뷰어 & 편집기)"
$s2.Save()

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  [성공] K-PDF Studio 바로가기 생성이 완료되었습니다!" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "1. 폴더 내 바로가기 : " -NoNewline; Write-Host $lnk1 -ForegroundColor Yellow
Write-Host "2. 바탕화면 바로가기 : " -NoNewline; Write-Host $lnk2 -ForegroundColor Yellow
Write-Host ""
