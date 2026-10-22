# MiniSun 主控端静态服务器（TcpListener 实现，绕开 HTTP.sys）
# 用途：手机/电脑浏览器访问 http://<本机IP>:<Port>/controller.html
# 运行：powershell -ExecutionPolicy Bypass -File server.ps1 [-Port 8081]

param(
    [int]$Port = 8081
)

$root = $PSScriptRoot
if (-not $root) { $root = Split-Path -Parent $MyInvocation.MyCommand.Path }

$listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $Port)
$listener.Start()
$ips = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback|WSL|Hyper-V' -and $_.IPAddress -notmatch '^127\.' }).IPAddress -join ', '
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MiniSun Controller Server" -ForegroundColor Green
Write-Host "  端口: $Port" -ForegroundColor Yellow
Write-Host "  监听IP: 0.0.0.0" -ForegroundColor Yellow
Write-Host "  局域网访问: http://$ips`:$Port/" -ForegroundColor Yellow
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
    ".txt"  = "text/plain; charset=utf-8"
}

function Parse-HttpRequest($bytes) {
    $text = [Text.Encoding]::ASCII.GetString($bytes)
    $lines = $text -split "`r`n"
    if ($lines.Count -lt 1) { return $null }
    $parts = $lines[0] -split " "
    if ($parts.Count -lt 2) { return $null }
    return @{ Method = $parts[0]; Path = $parts[1] }
}

$buffer = New-Object byte[] 8192

while ($listener.Pending() -or $true) {
    if (-not $listener.Pending()) { Start-Sleep -Milliseconds 50; continue }
    $client = $listener.AcceptTcpClient()
    $client.NoDelay = $true
    $stream = $client.GetStream()
    try {
        $read = $stream.Read($buffer, 0, $buffer.Length)
        if ($read -le 0) { continue }
        $req = Parse-HttpRequest $buffer[0..($read-1)]
        if (-not $req) { continue }

        $path = $req.Path
        # 去掉 query string
        $qIdx = $path.IndexOf('?')
        if ($qIdx -ge 0) { $path = $path.Substring(0, $qIdx) }
        if ($path -eq "/") { $path = "/controller.html" }

        $file = Join-Path $root ($path.TrimStart("/") -replace "/", "\")
        $resp = ""
        if (Test-Path -LiteralPath $file -PathType Leaf) {
            $bytes = [IO.File]::ReadAllBytes($file)
            $ext = [IO.Path]::GetExtension($file).ToLower()
            $ct = if ($mime.ContainsKey($ext)) { $mime[$ext] } else { "application/octet-stream" }
            $head = "HTTP/1.1 200 OK`r`nContent-Type: $ct`r`nContent-Length: $($bytes.Length)`r`nConnection: close`r`nAccess-Control-Allow-Origin: *`r`n`r`n"
            $headBytes = [Text.Encoding]::ASCII.GetBytes($head)
            $stream.Write($headBytes, 0, $headBytes.Length)
            $stream.Write($bytes, 0, $bytes.Length)
        } else {
            $body = "404 Not Found"
            $head = "HTTP/1.1 404 Not Found`r`nContent-Type: text/plain`r`nContent-Length: $($body.Length)`r`nConnection: close`r`n`r`n"
            $headBytes = [Text.Encoding]::ASCII.GetBytes($head)
            $bodyBytes = [Text.Encoding]::ASCII.GetBytes($body)
            $stream.Write($headBytes, 0, $headBytes.Length)
            $stream.Write($bodyBytes, 0, $bodyBytes.Length)
        }
    } catch {}
    finally {
        $stream.Close()
        $client.Close()
    }
}
