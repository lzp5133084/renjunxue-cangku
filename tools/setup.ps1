# 一键环境搭建脚本（零安装便携方案，全部装进项目 runtime 目录）
# 用法：右键 PowerShell 运行，或执行  powershell -ExecutionPolicy Bypass -File tools\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dl = "$root\runtime\downloads"
New-Item -ItemType Directory -Path $dl, "$root\runtime\python", "$root\runtime\ffmpeg", "$root\runtime\git", "$root\models", "$root\input", "$root\output" -Force | Out-Null

Write-Host "== 1/4 下载便携工具链 ==" -ForegroundColor Cyan
if (-not (Test-Path "$root\runtime\python\python.exe")) {
    curl.exe -L --retry 3 -o "$dl\python-installer.exe" "https://registry.npmmirror.com/-/binary/python/3.12.10/python-3.12.10-amd64.exe"
    Start-Process -FilePath "$dl\python-installer.exe" -ArgumentList '/quiet','InstallAllUsers=0',"TargetDir=$root\runtime\python",'PrependPath=0','Include_test=0','Include_doc=0','Include_launcher=0','Shortcuts=0','AssociateFiles=0' -Wait
}
if (-not (Test-Path "$root\runtime\ffmpeg\bin\ffmpeg.exe")) {
    curl.exe -L --retry 3 -o "$dl\ffmpeg.zip" "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    New-Item -ItemType Directory -Path "$dl\ffmpeg_tmp" -Force | Out-Null
    tar -xf "$dl\ffmpeg.zip" -C "$dl\ffmpeg_tmp"
    $子 = Get-ChildItem "$dl\ffmpeg_tmp" -Directory | Select-Object -First 1
    Move-Item "$($子.FullName)\*" "$root\runtime\ffmpeg" -Force
}
if (-not (Test-Path "$root\runtime\git\cmd\git.exe")) {
    curl.exe -L --retry 3 -o "$dl\mingit.zip" "https://ghfast.top/https://github.com/git-for-windows/git/releases/download/v2.56.0.windows.3/MinGit-2.56.0.3-64-bit.zip"
    Expand-Archive -Path "$dl\mingit.zip" -DestinationPath "$root\runtime\git" -Force
}

Write-Host "== 2/4 安装 Python 依赖 ==" -ForegroundColor Cyan
$py = "$root\runtime\python\python.exe"
& $py -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
# 注意：PyPI 的 Windows 版 torch 是 CPU 版，必须走官方 cu128 源才有 GPU 支持
& $py -m pip install torch --index-url https://download.pytorch.org/whl/cu128
& $py -m pip install transformers opencv-python pillow numpy iopaint PySide6 accelerate -i https://pypi.tuna.tsinghua.edu.cn/simple

Write-Host "== 3/4 预下载 AI 模型（约1.3GB） ==" -ForegroundColor Cyan
$env:HF_HOME = "$root\models"
$env:HF_ENDPOINT = "https://hf-mirror.com"
& $py -c "from huggingface_hub import snapshot_download; [snapshot_download(m) for m in ['IDEA-Research/grounding-dino-tiny','facebook/sam-vit-base']]"
& $py -c "import torch; from iopaint.model_manager import ModelManager; ModelManager(name='lama', device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'))"

Write-Host "== 4/4 完成 ==" -ForegroundColor Green
Write-Host "环境搭建完毕。运行界面：runtime\python\python.exe app\main.py"
