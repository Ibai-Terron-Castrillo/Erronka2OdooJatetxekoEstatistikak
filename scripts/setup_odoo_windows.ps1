<#
.SYNOPSIS
Instala y prepara Odoo 15 nativo en Windows Server 2022 para el addon jatetxeko_estatistikak.

.NOTES
- Ejecutar en PowerShell como Administrador.
- Por defecto NO registra el servicio NSSM. Primero prueba el arranque manual.
- Para registrar el servicio despues de una prueba correcta, ejecuta con -RegisterService.
#>

param(
    [string]$InstallDir = 'C:\odoo',
    [string]$OdooCoreRepo = 'https://github.com/odoo/odoo.git',
    [string]$OdooCoreBranch = '15.0',
    [string]$RepoRoot = '',
    [string]$RepoAddonsRelative = 'addons',
    [string]$ConfigRelative = 'config\odoo.conf',
    [string]$PostgresPassword = 'postgres',
    [string]$DbName = 'odoo',
    [string]$DbUser = 'odoo_db',
    [string]$DbPassword = 'odoo_db',
    [string]$AdminPassword = '123456',
    [string]$PythonInstallerUrl = 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe',
    [switch]$InstallPostgres = $true,
    [switch]$InstallGit = $true,
    [switch]$InstallPython = $true,
    [switch]$InstallWkhtml = $true,
    [switch]$InstallNSSM = $true,
    [switch]$RegisterService = $false
)

$ErrorActionPreference = 'Stop'

function Assert-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Este script necesita PowerShell como Administrador.'
    }
}

function Add-ToCurrentPath {
    param([string[]]$Paths)
    foreach ($path in $Paths) {
        if ($path -and (Test-Path $path) -and (($env:PATH -split ';') -notcontains $path)) {
            $env:PATH = "$path;$env:PATH"
        }
    }
}

function Refresh-CurrentPath {
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:PATH = "$machinePath;$userPath"
    Add-ToCurrentPath @(
        "$env:ProgramData\chocolatey\bin",
        'C:\Program Files\Git\cmd',
        'C:\Program Files\Git\bin',
        'C:\Program Files\Python310',
        'C:\Program Files\Python310\Scripts',
        'C:\Python310',
        'C:\Python310\Scripts'
    )
}

function Ensure-Chocolatey {
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Output 'Installing Chocolatey...'
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        iex ((New-Object Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    } else {
        Write-Output 'Chocolatey already installed.'
    }
    Refresh-CurrentPath
}

function Install-ChocoPackage {
    param(
        [Parameter(Mandatory=$true)][string]$Package,
        [string]$Params
    )

    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        throw "Chocolatey is not available. Cannot install $Package."
    }

    $args = @('install', $Package, '-y', '--no-progress')
    if ($Params) {
        $args += '--params'
        $args += $Params
    }

    Write-Output "choco $($args -join ' ')"
    & choco @args
    Refresh-CurrentPath
}

function Find-Executable {
    param(
        [string]$CommandName,
        [string[]]$Candidates
    )

    $cmd = Get-Command $CommandName -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    foreach ($candidate in $Candidates) {
        if (Test-Path $candidate) { return $candidate }
    }

    return $null
}

function Find-Git {
    return Find-Executable -CommandName 'git' -Candidates @(
        'C:\Program Files\Git\cmd\git.exe',
        'C:\Program Files\Git\bin\git.exe'
    )
}

function Find-Python310 {
    $preferredCandidates = @(
        'C:\Program Files\python\python.exe',
        'C:\Program Files\Python312\python.exe',
        'C:\Python312\python.exe',
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    )

    foreach ($candidate in $preferredCandidates) {
        if (Test-Path $candidate) {
            $version = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($version -eq '3.12') { return $candidate }
        }
    }

    $py = Find-Executable -CommandName 'py' -Candidates @(
        "$env:WINDIR\py.exe",
        'C:\Windows\py.exe'
    )

    if ($py) {
        try {
            $fromLauncher = & $py -3.10 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $fromLauncher -and (Test-Path $fromLauncher)) {
                return $fromLauncher.Trim()
            }
        } catch {
        }
    }

    $candidates = @(
        'C:\Program Files\Python310\python.exe',
        'C:\Python310\python.exe',
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            $version = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($version -eq '3.10') { return $candidate }
        }
    }

    return $null
}

function Install-Python310 {
    $python = Find-Python310
    if ($python) { return $python }

    Write-Output 'Python 3.10 not found. Installing Python 3.10...'
    $installer = Join-Path $env:TEMP 'python-3.10-amd64.exe'
    Invoke-WebRequest -Uri $PythonInstallerUrl -OutFile $installer
    Start-Process -FilePath $installer -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_launcher=0 Include_test=0' -Wait
    Remove-Item $installer -Force -ErrorAction SilentlyContinue
    Refresh-CurrentPath

    $python = Find-Python310
    if (-not $python) {
        throw 'Python 3.10 installation finished, but python.exe was not found.'
    }

    return $python
}

function Find-PSQL {
    $cmd = Get-Command psql -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $candidates = Get-ChildItem 'C:\Program Files\PostgreSQL' -Recurse -Filter psql.exe -ErrorAction SilentlyContinue |
        Sort-Object FullName |
        Select-Object -First 1

    if ($candidates) { return $candidates.FullName }
    return $null
}

function Wait-ServiceUp {
    param([string]$Name, [int]$TimeoutSec = 60)

    $elapsed = 0
    while ($elapsed -lt $TimeoutSec) {
        $svc = Get-Service | Where-Object { $_.Name -like "*$Name*" } | Select-Object -First 1
        if ($svc -and $svc.Status -eq 'Running') { return $true }
        Start-Sleep -Seconds 2
        $elapsed += 2
    }
    return $false
}

function Ensure-OdooDatabase {
    param([string]$PsqlPath)

    if (-not $PsqlPath) {
        Write-Warning 'psql.exe not found. Skipping database creation.'
        return
    }

    Write-Output "psql found: $PsqlPath"
    $env:PGPASSWORD = $PostgresPassword
    try {
        $connectOutput = & $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -tAc 'SELECT 1;' 2>$null
        $canConnect = if ($null -eq $connectOutput) { '' } else { ([string]$connectOutput).Trim() }
        if ($LASTEXITCODE -ne 0 -or $canConnect -ne '1') {
            Write-Warning 'Could not connect as postgres with the provided password. Skipping DB/user creation.'
            return
        }

        $roleOutput = & $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DbUser';" 2>$null
        $roleExists = if ($null -eq $roleOutput) { '' } else { ([string]$roleOutput).Trim() }
        if ($roleExists -ne '1') {
            & $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -c "CREATE USER $DbUser WITH PASSWORD '$DbPassword';"
        }

        $dbOutput = & $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -tAc "SELECT 1 FROM pg_database WHERE datname='$DbName';" 2>$null
        $dbExists = if ($null -eq $dbOutput) { '' } else { ([string]$dbOutput).Trim() }
        if ($dbExists -ne '1') {
            & $PsqlPath -U postgres -h 127.0.0.1 -p 5432 -c "CREATE DATABASE $DbName OWNER $DbUser;"
        }
    } finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
}

function Ensure-OdooCore {
    param([string]$GitPath, [string]$OdooCoreDir)

    if (Test-Path (Join-Path $OdooCoreDir 'odoo-bin')) {
        Write-Output "Odoo core already exists in $OdooCoreDir"
        return
    }

    if ((Test-Path $OdooCoreDir) -and ((Get-ChildItem $OdooCoreDir -Force -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0)) {
        throw "Odoo directory exists but odoo-bin was not found: $OdooCoreDir"
    }

    if (-not $GitPath) {
        throw 'git.exe not found. Install Git and rerun the script.'
    }

    Write-Output "Cloning Odoo $OdooCoreBranch into $OdooCoreDir"
    & $GitPath clone --branch $OdooCoreBranch --single-branch $OdooCoreRepo $OdooCoreDir
}

function Ensure-Venv {
    param([string]$PythonExe, [string]$VenvPath)

    $targetVersion = & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    $venvPython = Join-Path $VenvPath 'Scripts\python.exe'
    if (Test-Path $venvPython) {
        $venvVersion = & $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($venvVersion -ne $targetVersion) {
            Write-Warning "Existing venv uses Python $venvVersion. Recreating it with Python $targetVersion."
            Remove-Item -LiteralPath $VenvPath -Recurse -Force
        }
    }

    if (-not (Test-Path $venvPython)) {
        & $PythonExe -m venv $VenvPath
    }

    return $venvPython
}

function Install-PythonDependencies {
    param([string]$VenvPython, [string]$ReqFile)

    & $VenvPython -m pip install -U pip wheel 'setuptools==80.9.0'

    if (-not (Test-Path $ReqFile)) {
        throw "requirements.txt not found: $ReqFile"
    }

    Write-Output 'Installing Odoo Python requirements...'
    & $VenvPython -m pip install -r $ReqFile
    if ($LASTEXITCODE -ne 0) {
        throw 'pip install -r requirements.txt failed. Check the package error above.'
    }

    Write-Output 'Installing addon Python requirements...'
    & $VenvPython -m pip install psycopg2-binary requests matplotlib
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)]$Content
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)
    if ($Content -is [array]) {
        [IO.File]::WriteAllLines($Path, [string[]]$Content, $encoding)
    } else {
        [IO.File]::WriteAllText($Path, [string]$Content, $encoding)
    }
}

function Write-OdooConfig {
    param([string]$RepoConfig, [string]$OdooCoreDir)

    $repoAddonsAbs = Join-Path $RepoRoot $RepoAddonsRelative
    if (-not (Test-Path $repoAddonsAbs)) {
        throw "Addon path not found: $repoAddonsAbs"
    }

    if (-not (Test-Path $RepoConfig)) {
        $RepoConfig = Join-Path $InstallDir 'odoo.conf'
        Write-Warning "Repo config not found. Creating $RepoConfig"
        $configText = @"
[options]
addons_path = $repoAddonsAbs,$OdooCoreDir\addons
admin_passwd = $AdminPassword
db_host = 127.0.0.1
db_user = $DbUser
db_password = $DbPassword
db_port = 5432
http_port = 8069
logfile = $InstallDir\odoo.log
proxy_mode = True
server_wide_modules = web
"@
        Write-Utf8NoBom -Path $RepoConfig -Content $configText
        return $RepoConfig
    }

    Write-Host "Updating $RepoConfig"
    $content = Get-Content $RepoConfig
    $replacements = @{
        'addons_path\s*=.*' = "addons_path = $repoAddonsAbs,$OdooCoreDir\addons"
        'admin_passwd\s*=.*' = "admin_passwd = $AdminPassword"
        'db_host\s*=.*' = 'db_host = 127.0.0.1'
        'db_user\s*=.*' = "db_user = $DbUser"
        'db_password\s*=.*' = "db_password = $DbPassword"
        'db_port\s*=.*' = 'db_port = 5432'
        'data_dir\s*=.*' = "data_dir = $InstallDir\data"
        'logfile\s*=.*' = "logfile = $InstallDir\odoo.log"
        'server_wide_modules\s*=.*' = 'server_wide_modules = web'
    }

    foreach ($pattern in $replacements.Keys) {
        if ($content -match $pattern) {
            $content = $content -replace $pattern, $replacements[$pattern]
        } else {
            $content += $replacements[$pattern]
        }
    }

    Write-Utf8NoBom -Path $RepoConfig -Content $content
    return $RepoConfig
}

function Register-OdooService {
    param([string]$NssmPath, [string]$VenvPython, [string]$OdooCoreDir, [string]$ConfigPath)

    if (-not $NssmPath) {
        throw 'nssm.exe not found. Cannot register service.'
    }

    $existing = Get-Service Odoo15 -ErrorAction SilentlyContinue
    if ($existing) {
        & $NssmPath stop Odoo15 2>$null
        & $NssmPath remove Odoo15 confirm
    }

    $odooBin = Join-Path $OdooCoreDir 'odoo-bin'
    & $NssmPath install Odoo15 $VenvPython "$odooBin -c `"$ConfigPath`""
    & $NssmPath set Odoo15 AppDirectory $OdooCoreDir
    & $NssmPath set Odoo15 AppStdout (Join-Path $InstallDir 'odoo-service.out.log')
    & $NssmPath set Odoo15 AppStderr (Join-Path $InstallDir 'odoo-service.err.log')
    & $NssmPath start Odoo15
}

Assert-Admin
Refresh-CurrentPath

if (-not $RepoRoot) {
    if (Test-Path (Join-Path $PSScriptRoot 'addons')) {
        $RepoRoot = $PSScriptRoot
    } else {
        $RepoRoot = Split-Path -Parent $PSScriptRoot
    }
}

Write-Output 'Parameters:'
Write-Output " InstallDir: $InstallDir"
Write-Output " RepoRoot: $RepoRoot"
Write-Output " Config relative: $ConfigRelative"

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

Ensure-Chocolatey

if ($InstallPostgres) {
    Write-Output 'Installing PostgreSQL if needed...'
    Install-ChocoPackage -Package 'postgresql' -Params "/Password:$PostgresPassword"
    Wait-ServiceUp -Name 'postgres' -TimeoutSec 60 | Out-Null
}

if ($InstallGit) {
    if (-not (Find-Git)) {
        Write-Output 'Installing Git...'
        Install-ChocoPackage -Package 'git' -Params $null
    }
}

if ($InstallWkhtml) {
    Write-Output 'Installing wkhtmltopdf if needed...'
    Install-ChocoPackage -Package 'wkhtmltopdf' -Params $null
}

if ($InstallNSSM) {
    Write-Output 'Installing NSSM if needed...'
    Install-ChocoPackage -Package 'nssm' -Params $null
}

$pythonExe = Find-Python310
if ($InstallPython -and -not $pythonExe) {
    $pythonExe = Install-Python310
}
if (-not $pythonExe) {
    throw 'Python 3.10 is required for Odoo 15. Install it and rerun the script.'
}
Write-Output "Using Python: $pythonExe"

$psqlPath = Find-PSQL
Ensure-OdooDatabase -PsqlPath $psqlPath

$gitPath = Find-Git
$odooCoreDir = Join-Path $InstallDir 'odoo-15'
Ensure-OdooCore -GitPath $gitPath -OdooCoreDir $odooCoreDir

$venvPath = Join-Path $InstallDir 'venv'
$venvPython = Ensure-Venv -PythonExe $pythonExe -VenvPath $venvPath
$reqFile = Join-Path $odooCoreDir 'requirements.txt'
Install-PythonDependencies -VenvPython $venvPython -ReqFile $reqFile

$repoConfig = Join-Path $RepoRoot $ConfigRelative
$configPath = Write-OdooConfig -RepoConfig $repoConfig -OdooCoreDir $odooCoreDir

Write-Output 'Opening firewall ports...'
if (-not (Get-NetFirewallRule -DisplayName 'Odoo 8069' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName 'Odoo 8069' -Direction Inbound -LocalPort 8069 -Protocol TCP -Action Allow | Out-Null
}
if (-not (Get-NetFirewallRule -DisplayName 'Odoo WS 8072' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName 'Odoo WS 8072' -Direction Inbound -LocalPort 8072 -Protocol TCP -Action Allow | Out-Null
}

if ($RegisterService) {
    $nssm = Find-Executable -CommandName 'nssm' -Candidates @(
        "$env:ProgramData\chocolatey\bin\nssm.exe",
        "$env:ProgramData\chocolatey\lib\NSSM\tools\nssm.exe"
    )
    Register-OdooService -NssmPath $nssm -VenvPython $venvPython -OdooCoreDir $odooCoreDir -ConfigPath $configPath
} else {
    Write-Output 'Service registration skipped. Test Odoo manually first.'
}

$odooBin = Join-Path $odooCoreDir 'odoo-bin'
Write-Output 'Done.'
Write-Output "Manual start:"
Write-Output "& '$venvPython' '$odooBin' -c '$configPath'"
Write-Output 'After manual start works, rerun this script with -RegisterService or register NSSM manually.'
