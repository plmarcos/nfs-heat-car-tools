param(
  [string]$OutRoot = 'F:\CarsNfSHeat',
  [string]$Only = '',
  [int]$Limit = 0,
  [switch]$NoParts
)
$ErrorActionPreference = 'Stop'
# Onde esta' o Frosty Tool Suite e onde esta' o jogo. Sao os dois caminhos que
# mudam de maquina para maquina; defina as variaveis de ambiente uma vez e os
# scripts todos passam a achar sozinhos:
#
#     setx FROSTY_EDITOR "D:\FrostyToolSuite\FrostyEditor"
#     setx NFSHEAT_JOGO  "D:\Steam\steamapps\common\Need for Speed Heat"
#
# Sem as variaveis vale o padrao abaixo, que e' a maquina onde isto foi escrito.
$FE = if ($env:FROSTY_EDITOR) { $env:FROSTY_EDITOR }
      else { 'F:\SteamLibrary\steamapps\common\NFS Heat Music Modding\FrostyEditor\FrostyEditor' }
$JOGO = if ($env:NFSHEAT_JOGO) { $env:NFSHEAT_JOGO }
        else { 'F:\SteamLibrary\steamapps\common\Need for Speed Heat' }

# Falhar aqui, com o caminho na mensagem, e' muito melhor que falhar la' dentro
# com um "nao foi possivel carregar o assembly".
if (-not (Test-Path (Join-Path $FE 'FrostySdk.dll'))) {
  throw "FrostySdk.dll nao encontrado em '$FE'. Defina FROSTY_EDITOR."
}
if (-not (Test-Path $JOGO)) {
  throw "Pasta do jogo nao encontrada em '$JOGO'. Defina NFSHEAT_JOGO."
}
$SP = Split-Path -Parent $MyInvocation.MyCommand.Path   # pasta deste script (onde fica Export.cs)
Set-Location $FE
[System.IO.Directory]::SetCurrentDirectory($FE)

$h = [System.ResolveEventHandler]{
  param($s, $e)
  $n = $e.Name.Split(',')[0]
  if ($n -eq 'EbxClasses') { return [Reflection.Assembly]::LoadFrom((Join-Path $FE 'Profiles\NFSHEATSDK.dll')) }
  foreach ($d in @('', 'ThirdParty\', 'Plugins\')) { $p = Join-Path $FE "$d$n.dll"; if (Test-Path $p) { return [Reflection.Assembly]::LoadFrom($p) } }
  return $null
}
[AppDomain]::CurrentDomain.add_AssemblyResolve($h)
$refs = @((Join-Path $FE 'FrostySdk.dll'), (Join-Path $FE 'Plugins\MeshSetPlugin.dll'),
          (Join-Path $FE 'Plugins\TexturePlugin.dll'), 'System.dll', 'System.Core.dll', 'System.Drawing.dll')
Add-Type -TypeDefinition (Get-Content (Join-Path $SP 'Export.cs') -Raw) -ReferencedAssemblies $refs -Language CSharp

Write-Host ([HeatTool.Boot]::Init('NeedForSpeedHeat', $JOGO, (Join-Path $FE 'NFSHEAT.key')))

# ---------------------------------------------------------------
# Build body map: every composite "<name>_mesh" sitting directly in
# a vehicle folder is one car body. Its bolt-on parts come from that
# folder's customisation/ dir; when a folder carries a body but no
# parts (variant folders), the copy living in a folder that DOES
# have parts wins.
# ---------------------------------------------------------------
$bodies = @{}
foreach ($folder in [HeatTool.Boot]::ListVehicleFolders()) {
  $all = [HeatTool.Boot]::ListMeshes($folder) | Where-Object { $_ -notmatch '/chopshop/' }
  $comp = $all | Where-Object { $_ -match "^vehicles/player/$([regex]::Escape($folder))/[^/]+_mesh$" }
  $cust = @($all | Where-Object { $_ -match '/customisation/' })
  foreach ($c in $comp) {
    $name = ($c -replace '.*/', '') -replace '_mesh$', ''
    if (-not $bodies.ContainsKey($name) -or $cust.Count -gt $bodies[$name].Cust.Count) {
      $bodies[$name] = @{ Mesh = $c; Folder = $folder; Cust = $cust }
    }
  }
}

# Some special-edition bodies live alone in a folder that carries no
# customisation parts at all (e.g. Eddie's R34 sits in the Nismo Z-Tune
# folder). Borrow the parts from the folder whose car name shares the
# longest prefix with the body name.
function Get-CommonPrefixLen([string]$a, [string]$b) {
  $n = [Math]::Min($a.Length, $b.Length); $i = 0
  while ($i -lt $n -and $a[$i] -eq $b[$i]) { $i++ }
  return $i
}
$donors = @{}
foreach ($k in $bodies.Keys) { if ($bodies[$k].Cust.Count -gt 0) { $donors[$bodies[$k].Folder] = $bodies[$k].Cust } }
foreach ($k in @($bodies.Keys)) {
  if ($bodies[$k].Cust.Count -gt 0) { continue }
  $best = $null; $bestLen = 0
  foreach ($df in $donors.Keys) {
    $l = Get-CommonPrefixLen $k $df
    if ($l -gt $bestLen) { $bestLen = $l; $best = $df }
  }
  if ($best -and $bestLen -ge 20) {
    Write-Host "  [parts borrowed] $k  <-  $best  (prefix $bestLen)"
    $bodies[$k].Folder = $best
    $bodies[$k].Cust = $donors[$best]
  }
}

$names = $bodies.Keys | Sort-Object
if ($Only) { $names = $names | Where-Object { $_ -like "*$Only*" } }
if ($Limit -gt 0) { $names = $names | Select-Object -First $Limit }
Write-Host "car bodies to export: $($names.Count)"

$report = New-Object System.Collections.ArrayList
$swAll = [Diagnostics.Stopwatch]::StartNew()

foreach ($body in $names) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $info = $bodies[$body]
  $folder = $info.Folder

  # group customisation parts by part prefix, keep only stock variants
  $groups = @{}
  foreach ($m in $info.Cust) {
    $leaf = ($m -replace '.*/', '') -replace '_mesh$', ''
    $p = $leaf -replace "^$([regex]::Escape($folder))_", ''
    $prefix = $p -replace '_alt[a-z0-9]+$', '' -replace '_set[a-z0-9]+$', ''
    if (-not $groups.ContainsKey($prefix)) { $groups[$prefix] = New-Object System.Collections.ArrayList }
    [void]$groups[$prefix].Add(@{ Name = $m; Leaf = $p })
  }

  $bodyMeshes = New-Object System.Collections.ArrayList; $bodyNames = New-Object System.Collections.ArrayList
  $wheelMeshes = New-Object System.Collections.ArrayList; $wheelNames = New-Object System.Collections.ArrayList

  foreach ($prefix in ($groups.Keys | Sort-Object)) {
    $cands = $groups[$prefix]
    $pick = $cands | Where-Object { $_.Leaf -eq "${prefix}_seta" } | Select-Object -First 1
    if (-not $pick) { $pick = $cands | Where-Object { $_.Leaf -eq "${prefix}_set0" } | Select-Object -First 1 }
    if (-not $pick) { $pick = $cands | Where-Object { $_.Leaf -eq $prefix } | Select-Object -First 1 }
    if (-not $pick) { continue }
    if ($prefix -match '^wheel|^tyre|^tire|^brakedisc|^caliper') {
      [void]$wheelMeshes.Add($pick.Name); [void]$wheelNames.Add($prefix)
    } else {
      [void]$bodyMeshes.Add($pick.Name); [void]$bodyNames.Add($prefix)
    }
  }

  $carDir = Join-Path $OutRoot $body
  $row = [ordered]@{ body = $body; folder = $folder; full = ''; wheel = ''; parts = 0 }

  $fullMeshes = New-Object System.Collections.ArrayList; $fullNames = New-Object System.Collections.ArrayList
  [void]$fullMeshes.Add($info.Mesh); [void]$fullNames.Add('base')
  for ($i = 0; $i -lt $bodyMeshes.Count; $i++) { [void]$fullMeshes.Add($bodyMeshes[$i]); [void]$fullNames.Add($bodyNames[$i]) }

  $row.full = [HeatTool.Boot]::ExportMerged([string[]]$fullMeshes.ToArray(), [string[]]$fullNames.ToArray(),
    (Join-Path $carDir "$body.obj"), 0, $true, "NFS Heat stock car: $body")

  if ($wheelMeshes.Count -gt 0) {
    $row.wheel = [HeatTool.Boot]::ExportMerged([string[]]$wheelMeshes.ToArray(), [string[]]$wheelNames.ToArray(),
      (Join-Path $carDir "${body}_wheel.obj"), 0, $true, "NFS Heat wheel: $body")
  }

  if (-not $NoParts) {
    $pdir = Join-Path $carDir 'parts'
    $n = 0
    for ($i = 0; $i -lt $bodyMeshes.Count; $i++) {
      $r = [HeatTool.Boot]::ExportOne($bodyMeshes[$i], (Join-Path $pdir ($bodyNames[$i] + '.obj')), 0, $true)
      if ($r.StartsWith('OK')) { $n++ }
    }
    $row.parts = $n
  }

  [void]$report.Add([pscustomobject]$row)
  Write-Host ("{0,-50} {1,-50} wheel:{2} parts:{3} [{4:N1}s]" -f $body, $row.full, ($(if ($row.wheel) { 'y' } else { '-' })), $row.parts, $sw.Elapsed.TotalSeconds)
}

Write-Host "TOTAL TIME: $([math]::Round($swAll.Elapsed.TotalMinutes,2)) min"
$report | Export-Csv -Path (Join-Path $SP 'relatorio.csv') -NoTypeInformation -Encoding UTF8
