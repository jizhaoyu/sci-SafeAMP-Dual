# SafeAMP-Dual & DTI Studio - A2A 跨端协同流水线脚本
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  SafeAMP-Dual & DTI Studio - A2A 跨端协同流水线" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# [1/4] 环境核验
Write-Host "[1/4] 正在核验执行环境..." -ForegroundColor Yellow
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
$agyCandidates = @(
    "C:\Users\888\AppData\Local\agy\bin\agy.exe",
    "$env:USERPROFILE\AppData\Local\agy\bin\agy.exe",
    "$env:USERPROFILE\.gemini\antigravity\bin\agy.exe"
)
$agy = $null
foreach ($c in $agyCandidates) {
    if (Test-Path $c) {
        $agy = $c
        break
    }
}
if (-not $agy) {
    $agy = (Get-Command agy -ErrorAction SilentlyContinue).Source
}

Write-Host "  Python:  $py" -ForegroundColor Gray
Write-Host "  AGY CLI: $agy" -ForegroundColor Gray
Write-Host ""

# [2/4] 核心单测回归
Write-Host "[2/4] 运行核心后端单测回归 (pytest)..." -ForegroundColor Yellow
$env:PYTHONUTF8 = "1"
$testFiles = @(
    "02_code/tests/test_agent_orchestrator.py",
    "02_code/tests/test_dti_f1_runtime.py",
    "02_code/tests/test_dti_bilinear_runtime.py",
    "02_code/tests/test_dti_strict_validation.py"
)
pytest $testFiles -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [FAIL] 核心单测出现失败，流水线中断！" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] 核心单测全部通过！" -ForegroundColor Green
Write-Host ""

# [3/4] 前端打包
Write-Host "[3/4] 编译前端生产静态资源 (Vite + TS)..." -ForegroundColor Yellow
npm --prefix frontend run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [FAIL] 前端构建失败！" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] 前端 dist/ 编译成功并对齐后端挂载！" -ForegroundColor Green
Write-Host ""

# [4/4] 调度 A2A CLI 巡检
Write-Host "[4/4] 调度 A2A CLI 子智能体健康走查..." -ForegroundColor Yellow
python 02_code/a2a_agent_bridge.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [!] A2A CLI 巡检警告，但不阻断交付。" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  [ALL DONE] A2A 流水线运行完成！" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
