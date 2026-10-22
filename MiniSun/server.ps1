# MiniSun 主控端静态服务器
# 用途：通过 http://localhost:8081/ 打开 controller.html（比 file:// 更稳定）
# 运行：powershell -ExecutionPolicy Bypass -File server.ps1 [-Port 8081]

param(
    [int]$Port = 8081
)

$root = $PSScriptRoot
if (-not $root) { $root = Split-Path -Parent $MyInvocation.MyCommand.Path }

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MiniSun Controller Server" -ForegroundColor Green
Write-Host "  地址: http://localhost:$Port/" -ForegroundColor Yellow
Write-Host "  根目录: $root" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

$mime = @{
    ".html" = "text/html; charset=utf-8"
    ".js"   = "application/javascript; charset=utf-8"
    ".css"  = "text/css; charset=utf-8"
    ".png"  = "image/png"
    ".jpg"  = "image/jpeg"
    ".ico"  = "image/x-icon"
    ".json" = "application/json; charset=utf-8"
}

while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $path = $ctx.Request.Url.LocalPath
    if ($path -eq "/") { $path = "/controller.html" }
    $file = Join-Path $root ($path.TrimStart("/") -replace "/", "\")
    if (Test-Path $file -PathType Leaf) {
        $bytes = [IO.File]::ReadAllBytes($file)
        $ext = [IO.Path]::GetExtension($file).ToLower()
        $ctx.Response.ContentType = if ($mime.ContainsKey($ext)) { $mime[$ext] } else { "application/octet-stream" }
        $ctx.Response.ContentLength64 = $bytes.Length
        $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
        $ctx.Response.StatusCode = 404
    }
    $ctx.Response.Close()
}
