# このパソコンから、Substack（記事とNotes）とnoteを読み、data.json を更新して GitHub に保存する。
# Windowsのタスクスケジューラから呼ばれる（ログオン時／毎日20時）。AIは使わない。記録は logs\pc_update.log。
$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath $PSScriptRoot
$python = 'C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe'
$logDir = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'pc_update.log'
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Add-Content -Encoding UTF8 -LiteralPath $log }

$env:GIT_TERMINAL_PROMPT = '0'
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Log 'start'

# ログオン直後は、ネットに繋がるまで少し待つ（最大 約2分）
$ok = $false
for ($i = 0; $i -lt 12; $i++) {
    try { Invoke-WebRequest -Uri 'https://api.github.com' -UseBasicParsing -TimeoutSec 8 | Out-Null; $ok = $true; break } catch { Start-Sleep -Seconds 10 }
}
if (-not $ok) { Log 'ERROR: ネットに繋がりませんでした（次の機会に再実行されます）'; exit 1 }

try {
    git pull --rebase --autostash 2>&1 | ForEach-Object { Log "git: $_" }
    & $python 'scripts\update_data.py' 2>&1 | ForEach-Object { Log "py: $_" }
    if (git status --porcelain data.json) {
        git add data.json
        git commit -q -m 'data.json をパソコンから更新' 2>&1 | ForEach-Object { Log "git: $_" }
        git push 2>&1 | ForEach-Object { Log "git: $_" }
        Log 'saved'
    } else {
        Log 'no change'
    }
    Log 'done'
} catch {
    Log "ERROR: $_"
    exit 1
}
