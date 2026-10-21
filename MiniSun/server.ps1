$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:8081/")
$listener.Start()
Write-Host "HTTP server on 8081"
$root = "c:\Users\Administrator\Desktop\RJX\REA\MiniSun"
while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $path = $ctx.Request.Url.LocalPath
    if ($path -eq "/") { $path = "/controller.html" }
    $file = Join-Path $root $path.TrimStart("/")
    if (Test-Path $file) {
        $bytes = [System.IO.File]::ReadAllBytes($file)
        if ($file -match "\.html$") { $ctx.Response.ContentType = "text/html" }
        elseif ($file -match "\.js$") { $ctx.Response.ContentType = "application/javascript" }
        elseif ($file -match "\.css$") { $ctx.Response.ContentType = "text/css" }
        $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
        $ctx.Response.StatusCode = 404
    }
    $ctx.Response.Close()
}
