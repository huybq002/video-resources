# Tạo shortcut "Code2Video Studio" ngoài màn hình Desktop để mở app desktop không cần terminal.
# Chạy:  powershell -ExecutionPolicy Bypass -File scripts\make-desktop-shortcut.ps1
# Shortcut trỏ tới thư mục code đang chứa script này; chạy lại script nếu bạn chuyển thư mục code.
param([string]$Python = "")

$repo = Split-Path -Parent $PSScriptRoot
if (-not $Python) {
  $common = (& git -C $repo rev-parse --git-common-dir 2>$null)
  $main = if ($common) { Split-Path -Parent (Resolve-Path (Join-Path $repo $common)) } else { $repo }
  foreach ($base in @($repo, $main)) {
    $candidate = Join-Path $base ".venv\Scripts\pythonw.exe"
    if (Test-Path $candidate) { $Python = $candidate; break }
  }
}
if (-not $Python -or -not (Test-Path $Python)) { Write-Error "Không tìm thấy pythonw.exe trong .venv. Truyền -Python <đường dẫn>."; exit 1 }

$link = Join-Path ([Environment]::GetFolderPath("Desktop")) "Code2Video Studio.lnk"
$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($link)
$sc.TargetPath = (Resolve-Path $Python).Path
$sc.Arguments = '"' + (Join-Path $repo "desktop.pyw") + '"'
$sc.WorkingDirectory = $repo
$sc.Description = "Code2Video Studio (desktop)"
$sc.Save()
Write-Output "Đã tạo shortcut: $link"
Write-Output "Python: $($sc.TargetPath)"
