$ErrorActionPreference = "Stop"

Write-Host "OpenJarvis Windows setup" -ForegroundColor Cyan

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed. Install it from https://docs.astral.sh/uv/getting-started/installation/ and rerun this script."
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git for Windows is not installed. Install it from https://git-scm.com/download/win and rerun this script."
}

if (-not (Test-Path "pyproject.toml")) {
    throw "Run this script from the root of the OpenJarvis repository."
}

$key = [Environment]::GetEnvironmentVariable("FISH_API_KEY", "User")
if ([string]::IsNullOrWhiteSpace($key)) {
    $secureKey = Read-Host "Enter your Fish Audio API key (input is hidden)" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    try {
        $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
        if ([string]::IsNullOrWhiteSpace($key)) {
            throw "No API key was entered."
        }
        [Environment]::SetEnvironmentVariable("FISH_API_KEY", $key, "User")
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
        $key = $null
        $secureKey.Dispose()
    }
}

$env:FISH_API_KEY = [Environment]::GetEnvironmentVariable("FISH_API_KEY", "User")
$env:FISH_AUDIO_VOICE_ID = "14129c3e320149449d6bada6862f7338"
if (-not [Environment]::GetEnvironmentVariable("FISH_AUDIO_MODEL", "User")) {
    [Environment]::SetEnvironmentVariable("FISH_AUDIO_MODEL", "s2.1-pro-free", "User")
    $env:FISH_AUDIO_MODEL = "s2.1-pro-free"
}

Write-Host "Installing OpenJarvis desktop dependencies..." -ForegroundColor Cyan
uv sync --extra desktop

Write-Host "Checking the installation..." -ForegroundColor Cyan
uv run jarvis doctor

Write-Host "Setup finished. Start terminal chat with: uv run jarvis" -ForegroundColor Green
Write-Host "For the source GUI, install Node.js 22+ then run: uv run jarvis gui"
