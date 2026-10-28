"""Script independiente de instalación con intercambio de carpetas y recuperación."""

UPDATE_SCRIPT = r'''
param([string]$Settings)
$ErrorActionPreference = 'Stop'
$c = Get-Content -LiteralPath $Settings -Raw -Encoding UTF8 | ConvertFrom-Json
$target = [IO.Path]::GetFullPath($c.target)
$parent = Split-Path -Parent $target
$work = [IO.Path]::GetFullPath($c.work)
$stage = Join-Path $parent ('.yt-stage-' + $c.token)
$backup = Join-Path $parent ('.yt-backup-' + $c.token)
$failed = Join-Path $parent ('.yt-failed-' + $c.token)
$extract = Join-Path $work 'extract'
$ready = Join-Path $work 'ready'
$swapped = $false
$installed = $false
$committed = $false
$process = $null

function Retry($Action) {
    for ($i = 0; $i -lt 10; $i++) {
        try { & $Action; return } catch {
            if ($i -eq 9) { throw }
            Start-Sleep -Milliseconds 500
        }
    }
}
function Remove-Owned([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if ($full -notin @($stage, $backup, $failed, $work)) { throw 'Ruta de limpieza no autorizada.' }
    if (Test-Path -LiteralPath $full) {
        Retry { Remove-Item -LiteralPath $full -Recurse -Force -ErrorAction Stop }
    }
}
function Move-Owned([string]$From, [string]$To) {
    if ($From -notin @($target, $stage, $backup) -or $To -notin @($target, $backup, $failed)) {
        throw 'Ruta de restauracion no autorizada.'
    }
    if ((Split-Path -Parent $From) -ne $parent -or (Split-Path -Parent $To) -ne $parent) {
        throw 'Las carpetas deben estar junto a la instalacion.'
    }
    Retry { [IO.Directory]::Move($From, $To) }
}
function File-Hash([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($stream)) }
    finally { $stream.Dispose(); $sha.Dispose() }
}
function Copy-Tree([string]$From, [string]$To, [bool]$Package) {
    $argsCopy = @($From, $To, '/E', '/COPY:DAT', '/DCOPY:DAT', '/R:2', '/W:1', '/XJ', '/IS', '/IT')
    if ($Package) { $argsCopy += @('/XD', 'config') }
    & robocopy.exe @argsCopy | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Error de copia: $LASTEXITCODE" }
}
function Open-App([bool]$CheckReady) {
    $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
    if ($CheckReady) { $env:YT_UPDATE_READY = $ready } else { Remove-Item Env:YT_UPDATE_READY -ErrorAction SilentlyContinue }
    $exe = Join-Path $target $c.entry
    if ($c.python) {
        $p = Start-Process -FilePath $c.python -ArgumentList ('"' + $exe + '"') -WorkingDirectory $target -WindowStyle Hidden -PassThru
    } else {
        $p = Start-Process -FilePath $exe -WorkingDirectory $target -PassThru
    }
    return $p
}
try {
    $soundPs = $null
    $soundRs = $null
    if ($c.PSObject.Properties['sound'] -and $c.sound -and (Test-Path -LiteralPath $c.sound)) {
        try {
            $soundRs = [runspacefactory]::CreateRunspace()
            $soundRs.Open()
            $soundPs = [powershell]::Create()
            $soundPs.Runspace = $soundRs
            [void]$soundPs.AddScript({
                param($path)
                if (Test-Path -LiteralPath $path) {
                    $player = New-Object System.Media.SoundPlayer $path
                    while ($true) {
                        try { $player.PlaySync() } catch {}
                        [System.Threading.Thread]::Sleep(1800)
                    }
                }
            }).AddArgument($c.sound)
            [void]$soundPs.BeginInvoke()
        } catch {}
    }
    # Esperar al cierre sin matar otras instalaciones por nombre de ejecutable.
    $old = Get-Process -Id $c.pid -ErrorAction SilentlyContinue
    if ($old -and -not $old.WaitForExit(30000)) { throw 'La aplicacion anterior sigue abierta.' }
    # Cerrar cualquier proceso residual o secundario que se ejecute desde la carpeta de instalación
    $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.StartsWith($target, [System.StringComparison]::OrdinalIgnoreCase)
    }
    foreach ($p in $procs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 500
    New-Item -ItemType Directory -Path $extract | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory($c.zip, $extract)
    $source = $extract
    if (Test-Path -LiteralPath (Join-Path $extract 'YouTubeDownloader') -PathType Container) {
        $source = Join-Path $extract 'YouTubeDownloader'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $source $c.entry) -PathType Leaf)) {
        throw 'El paquete no contiene la aplicacion.'
    }
    # La instalacion original no se modifica mientras se prepara la nueva.
    # No omitir silenciosamente enlaces o uniones que contengan datos del usuario.
    if (Get-ChildItem -LiteralPath $target -Recurse -Force | Where-Object {
        $_.Attributes -band [IO.FileAttributes]::ReparsePoint
    }) { throw 'La instalacion contiene enlaces; se conserva la version anterior.' }
    Copy-Tree $target $stage $false
    foreach ($file in Get-ChildItem -LiteralPath $target -File -Recurse -Force) {
        $rel = $file.FullName.Substring($target.Length + 1)
        if ((File-Hash $file.FullName) -ne (File-Hash (Join-Path $stage $rel))) {
            throw "No se pudo preparar una copia completa: $rel"
        }
    }
    Copy-Tree $source $stage $true
    foreach ($file in Get-ChildItem -LiteralPath $source -File -Recurse) {
        $rel = $file.FullName.Substring($source.Length + 1)
        if (($rel -split '\\') -contains 'config') { continue }
        $dest = Join-Path $stage $rel
        if ((File-Hash $file.FullName) -ne (File-Hash $dest)) {
            throw "La verificacion fallo: $rel"
        }
    }
    Move-Owned $target $backup
    $swapped = $true
    Move-Owned $stage $target
    $installed = $true
    $process = Open-App $true
    $limit = [DateTime]::UtcNow.AddSeconds(60)
    while (-not (Test-Path -LiteralPath $ready)) {
        if ($process.HasExited -or [DateTime]::UtcNow -gt $limit) { throw 'La nueva version no confirmo el arranque.' }
        Start-Sleep -Milliseconds 250
    }
    $committed = $true
} catch {
    $problem = $_.Exception.Message
    if ($swapped -and -not $committed) {
        if ($process -and -not $process.HasExited) {
            & taskkill.exe /PID $process.Id /T /F | Out-Null
            $process.WaitForExit(10000) | Out-Null
        }
        try {
            if ($installed) { Move-Owned $target $failed }
            Move-Owned $backup $target
            $swapped = $false
        } catch {
            # Nunca destruir la unica copia recuperable si Windows impide restaurarla.
            $problem += "`nNo se pudo restaurar. La copia recuperable esta en: $backup"
        }
    }
    if (-not $swapped -and -not $old) {
        try { $process = Open-App $false } catch { $problem += "`nNo se pudo abrir la version anterior." }
    } elseif (-not $swapped -and $old.HasExited) {
        try { $process = Open-App $false } catch { $problem += "`nNo se pudo abrir la version anterior." }
    }
    $shell = New-Object -ComObject WScript.Shell
    $shell.Popup("La actualizacion no se completo.`n$problem", 10, 'Actualizacion', 48) | Out-Null
} finally {
    if ($soundPs) {
        try { $soundPs.Stop(); $soundPs.Dispose() } catch {}
    }
    if ($soundRs) {
        try { $soundRs.Close(); $soundRs.Dispose() } catch {}
    }
    $cleanupErrors = @()
    foreach ($path in @($stage, $failed)) {
        try { Remove-Owned $path } catch { $cleanupErrors += $path }
    }
    if ($committed -or -not $swapped) {
        try { Remove-Owned $backup } catch { $cleanupErrors += $backup }
    }
    try { Remove-Owned $work } catch { $cleanupErrors += $work }
    if ($cleanupErrors.Count) {
        $shell = New-Object -ComObject WScript.Shell
        $shell.Popup(('Windows impidio limpiar estos archivos: ' + ($cleanupErrors -join ', ')), 10, 'Actualizacion', 48) | Out-Null
    }
}
'''
