# MiniSun — 个人远程控制（AweSun 复刻学习版）

> 基于 AweSun 16.6 逆向分析结论，用零依赖方式重新实现的最小可用远程桌面。
> 仅供学习研究，无任何原始代码。

## 架构

```
被控端 agent.ps1  (PowerShell, Windows 原生)
  ├─ GDI 屏幕捕获 (System.Drawing.CopyFromScreen)
  ├─ JPEG 编码    (System.Drawing.Imaging, 质量可调)
  ├─ WebSocket 服务端 (原生 TcpListener 实现协议)
  └─ 输入注入     (SendInput + OpenInputDesktop 处理 UAC/锁屏)

主控端 controller.html  (纯 HTML5, 浏览器打开即用)
  ├─ WebSocket 客户端
  ├─ Canvas 渲染 JPEG 帧
  └─ 鼠标/键盘事件捕获 → JSON 转发
```

## 快速开始

### 1. 被控端（要被别人控制的电脑）

```powershell
# 在目标机器上，以普通或管理员权限运行
powershell -ExecutionPolicy Bypass -File agent.ps1 -Port 8080 -Fps 10 -Quality 60
```

参数说明：
| 参数 | 默认 | 说明 |
|------|------|------|
| `-Port` | 8080 | WebSocket 监听端口 |
| `-Fps` | 10 | 推流帧率，5–20 之间较流畅 |
| `-Quality` | 60 | JPEG 质量 1–100，越高越清晰越占带宽 |

启动后会显示本机 IP，等待主控端连接。

### 2. 主控端（用来操控别人的电脑）

直接用浏览器打开 `controller.html`，点击「连接设备」，输入被控端 IP 和端口，即可看到远程桌面并操控。

支持操作：
- 鼠标移动 / 左键 / 右键 / 中键 / 滚轮
- 键盘按键（字母、数字、方向键、F1–F12、Ctrl/Alt/Shift 等）
- 全屏模式（隐藏工具栏沉浸式控制）
- 实时显示分辨率、帧率、码率、延迟

### 2.1 手机远控（✅ 已实现）

手机浏览器直接打开即可，无需装 App。**前置条件：手机和被控电脑在同一个 WiFi**。

**步骤**：

1. 被控电脑运行两个进程：
   ```powershell
   # 被控端（WebSocket，监听 0.0.0.0:8080，手机可连）
   powershell -ExecutionPolicy Bypass -File agent.ps1 -Port 8080 -Fps 5 -Quality 40
   # 主控端静态服务器（TcpListener 实现，绕开 HTTP.sys 注册限制）
   powershell -ExecutionPolicy Bypass -File server.ps1 -Port 8081
   ```

2. 手机浏览器打开 `http://<电脑局域网IP>:8081/controller.html`
   - 电脑局域网 IP 查询：`Get-NetIPAddress -AddressFamily IPv4 | Where-Object InterfaceAlias -notmatch Loopback`
   - 例如 IP = `192.168.16.73`，手机访问 `http://192.168.16.73:8081/`

3. 点「⚡ 连接设备」，IP 填电脑 IP，端口 8080，点连接

**触屏操作映射**：

| 手势 | 电脑操作 |
|------|----------|
| 单指点击 | 鼠标左键 |
| 单指滑动 | 鼠标拖动 |
| 长按 0.45s | 鼠标右键 |
| 双指捏合 | 滚轮（张开=滚上，合拢=滚下） |
| 底部操作条 | Ctrl/Alt/Shift 修饰键、Esc、Enter、右键、滚轮↑↓ |

**故障排查**：

| 现象 | 排查 |
|------|------|
| 手机打不开页面（超时） | 在电脑上测 `curl http://127.0.0.1:8081/` 确认服务在线；Windows Defender 防火墙服务可能未启动或规则未放行（见下方"注意"） |
| 能打开页面但连接失败 | 确认 agent 在 LISTENING：`netstat -ano | findstr ":8080"`；手机和电脑必须同一 WiFi |
| 画面空白 / 卡顿 | 降低码率：`agent.ps1 -Fps 3 -Quality 30` |

**注意**：如果 Windows Defender 防火墙开启（MpsSvc 服务 Running），需要放行 8080/8081 入站规则。当前机器防火墙未启动，端口直接通。

### 3. 剪贴板同步

连接后点工具栏「📋 剪贴板」：
- **⬇ 获取远端剪贴板**：拉取被控端当前剪贴板文本到输入框
- **⧉ 复制到本机**：把输入框内容复制到主控端剪贴板
- **⬆ 发送到远端**：把输入框文本写入被控端剪贴板（远端即可直接 Ctrl+V 粘贴）

### 4. 文件传输

连接后点工具栏「📁 文件」打开远端文件面板：
- **浏览**：输入远端路径（默认 C:\），点「浏览」或回车；点目录进入，点「..（上一级）」返回
- **下载**：点任意文件自动下载到本机浏览器默认下载目录（分片 base64 传输）
- **上传**：点「⬆ 上传到此目录」选择一个或多个文件，传到当前浏览的远端目录

> 传输限制：单文件 ≤ 500MB；传输期间画面帧率会短暂下降属正常现象。
> 提示：本工具无鉴权机制，请仅在可信局域网内使用。

## 常见问题

**Q: 连接失败？**
- 确认被控端 agent.ps1 正在运行且端口一致
- 检查 Windows 防火墙是否放行该端口：`netsh advfirewall firewall add rule name="MiniSun" dir=in action=allow protocol=TCP localport=8080`
- 局域网内用被控端实际 IP，不要用 127.0.0.1

**Q: 画面卡顿？**
- 降低 `-Fps` 到 5–8，或降低 `-Quality` 到 40–50
- 确保两台机器在同一局域网，跨网建议配合内网穿透（frp / 花生壳）

**Q: UAC 弹窗或锁屏界面无法控制？**
- AweSun 通过驱动 + OpenInputDesktop 解决；MiniSun 已使用 OpenInputDesktop，普通权限下大部分场景可用。若仍不行，用管理员身份运行 agent.ps1。

**Q: 想控制多台设备？**
- 在每台被控设备上运行 agent.ps1（不同端口），主控端分别连接即可。

## 与 AweSun 的差距

| 能力 | AweSun | MiniSun |
|------|--------|---------|
| 屏幕捕获 | 镜像驱动 + DWM，60 FPS | GDI，8–15 FPS |
| 编码 | H.264/HEVC/AV1 硬件编码 | JPEG 软编码 |
| 传输 | P2P UDP 打洞 + UDT | 单 WebSocket TCP |
| 剪贴板 | 全格式（文本/位图/HTML/RTF） | ✅ 文本同步（简化） |
| 文件传输 | 拖拽 + 剪贴板双通道 | ✅ 文件面板（浏览/上传/下载） |
| 虚拟显示器 | Idd64 驱动 | 未实现 |
| 服务驻留 | Windows 服务 + 守护进程 | 前台进程 |

## 实测数据（本机 loopback）

| 指标 | 数值 |
|------|------|
| 分辨率 | 2560 × 1440 |
| 帧率 | ~8 FPS |
| 码率 | ~10.5 Mbps |
| 延迟 | ~68 ms |
| JPEG 质量 | 60 |

> 注：GDI 捕获在 2K 分辨率下性能有限。降低分辨率或调低 `-Fps`/`-Quality` 可提升流畅度。

## 修改记录

| 时间 | 内容 |
|------|------|
| 2026-10-22 | 初始版本：agent.ps1 + controller.html + README |
| 2026-10-22 | 修复 WebSocket 帧头发送：PowerShell `-shr` 对 `[int]` 右移超过 32 位时移位量取模 32，导致 8 字节长度字段计算错误。改用 `[long]` 类型修复。 |
| 2026-10-22 | 新增文本剪贴板同步（clip_get / clip_set），agent 端 Get-Clipboard / Set-Clipboard 实现。 |
| 2026-10-22 | 新增文件传输：远端目录浏览（file_list）、分片下载（file_get → file_begin/chunk/end）、分片上传（file_put_begin/chunk/end），主控端新增「📁 文件」侧面板。 |
| 2026-10-22 | server.ps1 改为 $PSScriptRoot 相对路径（修复写死旧路径问题），补充 MIME 表与启动横幅。 |

## 参考开源项目

- RustDesk（Rust 远程桌面，P2P 架构参考）
- TigerVNC（VNC 协议参考）
- MeshCentral（Web 远程管理参考）
- 向日葵 / ToDesk（商业远控产品架构参考）

## 技术要点

1. **WebSocket 协议**：agent.ps1 未使用 HttpListener（需管理员注册 URLACL），而是直接用 TcpListener 实现 RFC 6455 握手与帧解析，普通权限即可运行。
2. **输入注入**：通过 Add-Type 内嵌 C# 调用 `SendInput`，并在注入前调用 `OpenInputDesktop` + `SetThreadDesktop` 切换到当前输入桌面，以处理 UAC 和锁屏。
3. **GDI 捕获**：`Graphics.CopyFromScreen` 是最兼容的捕获方式，虽然性能不如镜像驱动，但无需安装任何驱动。

## 文件清单

```
MiniSun/
├── agent.ps1        # 被控端（屏幕捕获/推流/输入注入/剪贴板/文件传输）
├── controller.html  # 主控端（单文件 Web App：桌面控制+剪贴板+文件面板）
├── server.ps1       # 主控端静态服务器（http://localhost:8081/ 打开更稳定）
├── test-minisun.ps1 # 自动化回归测试（WebSocket 客户端，7 项断言）
├── 开发对话记录.txt  # 需求沟通与开发过程留档
└── README.md        # 本说明
```
