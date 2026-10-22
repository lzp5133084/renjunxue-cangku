# MiniSun 新功能自动化测试（ClientWebSocket 客户端）
$ErrorActionPreference = "Stop"
$ws = New-Object System.Net.WebSockets.ClientWebSocket
$ct = [System.Threading.CancellationToken]::None
$ws.ConnectAsync([Uri]"ws://127.0.0.1:8080", $ct).Wait()
"PASS 1/7 WebSocket 连接成功"

function Recv-Msg {
    $buf = New-Object byte[] (4MB)
    $ms = New-Object System.IO.MemoryStream
    while ($true) {
        $seg = [ArraySegment[byte]]::new($buf)
        $r = $ws.ReceiveAsync($seg, $ct).Result
        if ($r.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) { return $null }
        $ms.Write($buf, 0, $r.Count)
        if ($r.EndOfMessage) { break }
    }
    $bytes = $ms.ToArray()
    if ($ws.State -ne 'Open') { return $null }
    # 判断 opcode 不行，ClientWebSocket 已整合；按首字符猜测：文本以 '{' 开头
    if ($bytes.Length -gt 0 -and $bytes[0] -eq 0x7B) {
        return @{ kind = "text"; obj = ([System.Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json) }
    }
    return @{ kind = "binary"; bytes = $bytes }
}

function Send-Json($obj) {
    $t = $obj | ConvertTo-Json -Compress -Depth 4
    $b = [System.Text.Encoding]::UTF8.GetBytes($t)
    $ws.SendAsync([ArraySegment[byte]]::new($b), [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $ct).Wait()
}

# 1. screen 元数据
$m = Recv-Msg
if ($m.kind -eq "text" -and $m.obj.type -eq "screen" -and $m.obj.width -gt 0) { "PASS 2/7 screen 元数据: $($m.obj.width)x$($m.obj.height)" } else { throw "screen 元数据失败" }

# 2. clip_get
Send-Json @{ type = "clip_get" }
do { $m = Recv-Msg } while ($m.kind -ne "text")
if ($m.obj.type -eq "clip_text") { "PASS 3/7 clip_get 返回文本长度: $($m.obj.text.Length)" } else { throw "clip_get 失败: $($m.obj.type)" }

# 3. clip_set
Send-Json @{ type = "clip_set"; text = "MiniSun测试2026-ok" }
do { $m = Recv-Msg } while ($m.kind -ne "text")
$ok = ($m.obj.type -eq "clip_ok" -and $m.obj.ok)
$clip = Get-Clipboard -Raw
if ($ok -and $clip -eq "MiniSun测试2026-ok") { "PASS 4/7 clip_set 写入成功，本机读回一致" } else { throw "clip_set 失败 ok=$($m.obj.ok) clip=$clip" }

# 4. file_list
Send-Json @{ type = "file_list"; path = "C:\" }
do { $m = Recv-Msg } while ($m.kind -ne "text")
if ($m.obj.type -eq "file_list" -and $m.obj.items.Count -gt 0) { "PASS 5/7 file_list C:\ 共 $($m.obj.items.Count) 项" } else { throw "file_list 失败" }

# 5. file_get 下载测试
$src = "c:\Users\Administrator\Desktop\rjx\MiniSun\server.ps1"
Send-Json @{ type = "file_get"; path = $src }
$parts = @{}; $total = 0; $name = ""
while ($true) {
    $m = Recv-Msg
    if ($m.kind -ne "text") { continue }
    $o = $m.obj
    if ($o.type -eq "file_begin") { $total = $o.total; $name = $o.name }
    elseif ($o.type -eq "file_chunk") { $parts[$o.idx] = $o.data }
    elseif ($o.type -eq "file_end") { break }
    elseif ($o.type -eq "file_err") { throw "file_get 错误: $($o.err)" }
}
$b64 = ($parts[0..($total-1)] | ForEach-Object { $_ }) -join ""
$dl = [Convert]::FromBase64String($b64)
$orig = [IO.File]::ReadAllBytes($src)
if ([Convert]::ToBase64String($dl) -eq [Convert]::ToBase64String($orig)) { "PASS 6/7 file_get 下载 $($dl.Length) 字节，与源文件一致" } else { throw "下载内容不一致" }

# 6. file_put 上传测试
$upBytes = [System.Text.Encoding]::UTF8.GetBytes("MiniSun upload test 你好上传 $(Get-Random)")
$upB64 = [Convert]::ToBase64String($upBytes)
$destDir = "c:\Users\Administrator\Desktop\rjx\MiniSun\test_recv"
Send-Json @{ type = "file_put_begin"; name = "upload_test.txt"; total = 1 }
Send-Json @{ type = "file_put_chunk"; idx = 0; data = $upB64 }
Send-Json @{ type = "file_put_end"; dir = $destDir }
do { $m = Recv-Msg } while ($m.kind -ne "text" -or $m.obj.type -notin @("file_done","file_err"))
if ($m.obj.type -eq "file_done") {
    $saved = [IO.File]::ReadAllBytes($m.obj.path)
    if ([Convert]::ToBase64String($saved) -eq [Convert]::ToBase64String($upBytes)) { "PASS 7/7 file_put 上传成功 $($saved.Length) 字节，内容一致 → $($m.obj.path)" } else { throw "上传内容不一致" }
} else { throw "file_put 失败: $($m.obj.err)" }

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "done", $ct).Wait()
"`n===== 全部 7 项测试通过 ====="
