# MiniSun Agent - 被控端
# 功能：屏幕捕获 + JPEG 编码 + WebSocket Streaming + 远程输入注入
# 运行：powershell -ExecutionPolicy Bypass -File agent.ps1 [-Port 8080]

param(
    [int]$Port = 8080,
    [int]$Fps = 10,
    [int]$Quality = 60
)

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Net

$inputInjectorCode = @"
using System;
using System.Runtime.InteropServices;

public class InputInjector {
    [StructLayout(LayoutKind.Sequential)]
    public struct INPUT { public uint type; public INPUTUNION union; }
    [StructLayout(LayoutKind.Explicit)]
    public struct INPUTUNION { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; }
    [StructLayout(LayoutKind.Sequential)]
    public struct MOUSEINPUT { public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
    [StructLayout(LayoutKind.Sequential)]
    public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }

    [DllImport("user32.dll", SetLastError = true)] public static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);
    [DllImport("user32.dll")] public static extern IntPtr OpenInputDesktop(uint dwFlags, bool fInherit, uint dwDesiredAccess);
    [DllImport("user32.dll")] public static extern bool SetThreadDesktop(IntPtr hDesktop);
    [DllImport("user32.dll")] public static extern bool CloseDesktop(IntPtr hDesktop);

    public const uint INPUT_MOUSE = 0;
    public const uint INPUT_KEYBOARD = 1;
    public const uint MOUSEEVENTF_MOVE = 0x0001;
    public const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
    public const uint MOUSEEVENTF_LEFTUP = 0x0004;
    public const uint MOUSEEVENTF_RIGHTDOWN = 0x0008;
    public const uint MOUSEEVENTF_RIGHTUP = 0x0010;
    public const uint MOUSEEVENTF_MIDDLEDOWN = 0x0020;
    public const uint MOUSEEVENTF_MIDDLEUP = 0x0040;
    public const uint MOUSEEVENTF_WHEEL = 0x0800;
    public const uint MOUSEEVENTF_ABSOLUTE = 0x8000;
    public const uint KEYEVENTF_KEYUP = 0x0002;

    public static void EnsureInputDesktop() {
        IntPtr hDesk = OpenInputDesktop(0, false, 0x10000000);
        if (hDesk != IntPtr.Zero) { SetThreadDesktop(hDesk); CloseDesktop(hDesk); }
    }

    public static void MouseMove(int x, int y, int screenW, int screenH) {
        EnsureInputDesktop();
        INPUT[] inputs = new INPUT[1];
        inputs[0].type = INPUT_MOUSE;
        inputs[0].union.mi.dx = (int)((double)x / screenW * 65535.0);
        inputs[0].union.mi.dy = (int)((double)y / screenH * 65535.0);
        inputs[0].union.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE;
        SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
    }

    public static void MouseButton(string button, bool down) {
        EnsureInputDesktop();
        uint flags = 0;
        switch (button.ToLower()) {
            case "left": flags = down ? MOUSEEVENTF_LEFTDOWN : MOUSEEVENTF_LEFTUP; break;
            case "right": flags = down ? MOUSEEVENTF_RIGHTDOWN : MOUSEEVENTF_RIGHTUP; break;
            case "middle": flags = down ? MOUSEEVENTF_MIDDLEDOWN : MOUSEEVENTF_MIDDLEUP; break;
        }
        INPUT[] inputs = new INPUT[1];
        inputs[0].type = INPUT_MOUSE;
        inputs[0].union.mi.dwFlags = flags;
        SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
    }

    public static void MouseWheel(int delta) {
        EnsureInputDesktop();
        INPUT[] inputs = new INPUT[1];
        inputs[0].type = INPUT_MOUSE;
        inputs[0].union.mi.dwFlags = MOUSEEVENTF_WHEEL;
        inputs[0].union.mi.mouseData = (uint)delta;
        SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
    }

    public static void KeyEvent(ushort vk, bool down) {
        EnsureInputDesktop();
        INPUT[] inputs = new INPUT[1];
        inputs[0].type = INPUT_KEYBOARD;
        inputs[0].union.ki.wVk = vk;
        inputs[0].union.ki.dwFlags = down ? 0 : KEYEVENTF_KEYUP;
        SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
    }
}
"@

Add-Type -TypeDefinition $inputInjectorCode

function Send-WebSocketHandshake {
    param([System.Net.Sockets.NetworkStream]$Stream)
    $reader = New-Object System.IO.StreamReader($Stream, [System.Text.Encoding]::ASCII)
    $requestLine = $reader.ReadLine()
    if (-not $requestLine -or $requestLine -notmatch "GET") { return $false }
    $headers = @{}
    while ($true) {
        $line = $reader.ReadLine()
        if ([string]::IsNullOrEmpty($line)) { break }
        if ($line -match "^([^:]+):\s*(.+)$") { $headers[$matches[1].Trim().ToLower()] = $matches[2].Trim() }
    }
    if (-not $headers.ContainsKey("sec-websocket-key")) { return $false }
    $key = $headers["sec-websocket-key"]
    $accept = [Convert]::ToBase64String([System.Security.Cryptography.SHA1]::Create().ComputeHash([System.Text.Encoding]::ASCII.GetBytes($key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11")))
    $response = "HTTP/1.1 101 Switching Protocols`r`nUpgrade: websocket`r`nConnection: Upgrade`r`nSec-WebSocket-Accept: $accept`r`n`r`n"
    $bytes = [System.Text.Encoding]::ASCII.GetBytes($response)
    $Stream.Write($bytes, 0, $bytes.Length)
    return $true
}

function Send-WebSocketFrame {
    param([System.Net.Sockets.NetworkStream]$Stream, [byte[]]$Payload, [byte]$Opcode = 2)
    $len = $Payload.Length
    $headerSize = 2
    if ($len -gt 125 -and $len -le 65535) { $headerSize = 4 }
    elseif ($len -gt 65535) { $headerSize = 10 }

    $frame = New-Object byte[] ($headerSize + $len)
    $frame[0] = [byte](0x80 -bor $Opcode)

    if ($len -le 125) {
        $frame[1] = [byte]$len
    } elseif ($len -le 65535) {
        $frame[1] = 126
        $frame[2] = [byte](($len -shr 8) -band 0xFF)
        $frame[3] = [byte]($len -band 0xFF)
    } else {
        $frame[1] = 127
        $lenLong = [long]$len
        for ($i = 7; $i -ge 0; $i--) {
            $frame[2 + (7 - $i)] = [byte](($lenLong -shr ($i * 8)) -band 0xFF)
        }
    }

    [Array]::Copy($Payload, 0, $frame, $headerSize, $len)
    $Stream.Write($frame, 0, $frame.Length)
}

function Read-WebSocketFrame {
    param([System.Net.Sockets.NetworkStream]$Stream)
    try {
        $b1 = $Stream.ReadByte(); $b2 = $Stream.ReadByte()
        if ($b1 -lt 0 -or $b2 -lt 0) { return $null }
        $opcode = $b1 -band 0x0F; $masked = ($b2 -band 0x80) -ne 0; $len = $b2 -band 0x7F
        if ($len -eq 126) { $buf = New-Object byte[] 2; $Stream.Read($buf, 0, 2) | Out-Null; $len = ($buf[0] -shl 8) -bor $buf[1] }
        elseif ($len -eq 127) { $buf = New-Object byte[] 8; $Stream.Read($buf, 0, 8) | Out-Null; $len = 0; for ($i = 0; $i -lt 8; $i++) { $len = ($len -shl 8) -bor $buf[$i] } }
        $mask = @(); if ($masked) { $maskBuf = New-Object byte[] 4; $Stream.Read($maskBuf, 0, 4) | Out-Null; $mask = $maskBuf }
        $payload = New-Object byte[] $len
        $totalRead = 0
        while ($totalRead -lt $len) { $read = $Stream.Read($payload, $totalRead, $len - $totalRead); if ($read -le 0) { return $null }; $totalRead += $read }
        if ($masked -and $len -gt 0) { for ($i = 0; $i -lt $len; $i++) { $payload[$i] = $payload[$i] -bxor $mask[$i % 4] } }
        return @{ Opcode = $opcode; Payload = $payload; Text = if ($opcode -eq 1) { [System.Text.Encoding]::UTF8.GetString($payload) } else { $null } }
    } catch { return $null }
}

function Get-ScreenJpeg {
    param([int]$Quality = 60)
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
    $ms = New-Object System.IO.MemoryStream
    $encoder = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
    $params = New-Object System.Drawing.Imaging.EncoderParameters(1)
    $params.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, $Quality)
    $bmp.Save($ms, $encoder, $params)
    $g.Dispose(); $bmp.Dispose()
    return $ms.ToArray()
}

$listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $Port)
$listener.Start()
$ips = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notmatch 'Loopback'}).IPAddress -join ', '
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MiniSun Agent Started" -ForegroundColor Green
Write-Host "  Listen Port: $Port" -ForegroundColor Yellow
Write-Host "  FPS: $Fps FPS | JPEG 质量: $Quality" -ForegroundColor Yellow
Write-Host "  Local IP: $ips" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Waiting for controller......"

while ($true) {
    $client = $listener.AcceptTcpClient()
    $client.NoDelay = $true
    $client.ReceiveTimeout = 100
    $stream = $client.GetStream()
    $remoteEP = $client.Client.RemoteEndPoint.ToString()
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Controller connected: $remoteEP" -ForegroundColor Green

    try {
        if (-not (Send-WebSocketHandshake -Stream $stream)) { Write-Host "WebSocket Handshake failed"; $client.Close(); continue }
        Write-Host "WebSocket 握手成功，开始Streaming..." -ForegroundColor Cyan

        $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $screenW = $bounds.Width; $screenH = $bounds.Height

        $meta = @{ type = "screen"; width = $screenW; height = $screenH } | ConvertTo-Json -Compress
        Send-WebSocketFrame -Stream $stream -Payload ([System.Text.Encoding]::UTF8.GetBytes($meta)) -Opcode 1

        $running = $true
        $frameInterval = [int](1000 / $Fps)

        while ($running -and $client.Connected) {
            $sw = [System.Diagnostics.Stopwatch]::StartNew()

            while ($stream.DataAvailable) {
                $frame = Read-WebSocketFrame -Stream $stream
                if ($null -eq $frame) { $running = $false; break }
                if ($frame.Opcode -eq 1 -and $frame.Text) {
                    try {
                        $msg = $frame.Text | ConvertFrom-Json
                        switch ($msg.type) {
                            "mousemove" { [InputInjector]::MouseMove($msg.x, $msg.y, $screenW, $screenH) }
                            "mousedown" { [InputInjector]::MouseButton($msg.button, $true) }
                            "mouseup"   { [InputInjector]::MouseButton($msg.button, $false) }
                            "wheel"     { [InputInjector]::MouseWheel($msg.delta) }
                            "keydown"   { [InputInjector]::KeyEvent($msg.key, $true) }
                            "keyup"     { [InputInjector]::KeyEvent($msg.key, $false) }
                        }
                    } catch { }
                }
            }
            if (-not $running) { break }

            try {
                $jpeg = Get-ScreenJpeg -Quality $Quality
                Send-WebSocketFrame -Stream $stream -Payload $jpeg -Opcode 2
            } catch { $running = $false; break }

            $sw.Stop()
            $sleep = $frameInterval - $sw.ElapsedMilliseconds
            if ($sleep -gt 0) { Start-Sleep -Milliseconds $sleep }
        }
    } catch {
        Write-Host "Session error: $_" -ForegroundColor Red
    } finally {
        try { $client.Close() } catch { }
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Controller disconnected" -ForegroundColor Yellow
    }
}
