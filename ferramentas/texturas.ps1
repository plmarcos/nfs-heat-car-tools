param(
  [string]$OutRoot = 'F:\CarsNfSHeat',
  [string]$Only = '',
  [string]$Fmt = 'png',
  [switch]$SkipShared
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
$SP = Split-Path -Parent $MyInvocation.MyCommand.Path
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

# ---- same body -> folder mapping used by extrair.ps1 ----
$bodies = @{}
foreach ($folder in [HeatTool.Boot]::ListVehicleFolders()) {
  $all = [HeatTool.Boot]::ListMeshes($folder) | Where-Object { $_ -notmatch '/chopshop/' }
  $comp = $all | Where-Object { $_ -match "^vehicles/player/$([regex]::Escape($folder))/[^/]+_mesh$" }
  $cust = @($all | Where-Object { $_ -match '/customisation/' })
  foreach ($c in $comp) {
    $name = ($c -replace '.*/', '') -replace '_mesh$', ''
    if (-not $bodies.ContainsKey($name) -or $cust.Count -gt $bodies[$name].Cust.Count) {
      $bodies[$name] = @{ Folder = $folder; Cust = $cust }
    }
  }
}
function Get-CommonPrefixLen([string]$a, [string]$b) {
  $n = [Math]::Min($a.Length, $b.Length); $i = 0
  while ($i -lt $n -and $a[$i] -eq $b[$i]) { $i++ }
  return $i
}
$folders = @{}
foreach ($k in $bodies.Keys) { $folders[$bodies[$k].Folder] = $true }
foreach ($k in @($bodies.Keys)) {
  if ([HeatTool.Boot]::ListTextures("vehicles/player/$($bodies[$k].Folder)/textures/").Count -gt 0) { continue }
  $best = $null; $bestLen = 0
  foreach ($df in $folders.Keys) {
    if ([HeatTool.Boot]::ListTextures("vehicles/player/$df/textures/").Count -eq 0) { continue }
    $l = Get-CommonPrefixLen $k $df
    if ($l -gt $bestLen) { $bestLen = $l; $best = $df }
  }
  if ($best -and $bestLen -ge 20) {
    Write-Host "  [texturas emprestadas] $k  <-  $best"
    $bodies[$k].Folder = $best
  }
}

$names = $bodies.Keys | Sort-Object
if ($Only) { $names = $names | Where-Object { $_ -like "*$Only*" } }
Write-Host "car bodies: $($names.Count)  formato: $Fmt"

$okTotal = 0; $errTotal = 0
$swAll = [Diagnostics.Stopwatch]::StartNew()

foreach ($body in $names) {
  $folder = $bodies[$body].Folder
  $tex = [HeatTool.Boot]::ListTextures("vehicles/player/$folder/textures/")
  if ($tex.Count -eq 0) { Write-Host ("{0,-50} sem texturas" -f $body); continue }
  $dir = Join-Path (Join-Path $OutRoot $body) 'textures'
  $ok = 0; $err = 0
  foreach ($t in $tex) {
    $leaf = $t -replace '.*/', ''
    $r = [HeatTool.Boot]::ExportTexture($t, (Join-Path $dir "$leaf.$Fmt"), $Fmt)
    if ($r.StartsWith('OK')) { $ok++ } else { $err++; if ($err -le 2) { Write-Host "    ! $leaf : $r" } }
  }
  $okTotal += $ok; $errTotal += $err
  Write-Host ("{0,-50} {1,4} texturas  {2}" -f $body, $ok, $(if ($err) { "($err falhas)" } else { '' }))
}

# ---- shared wheel / tire textures ----
if (-not $SkipShared) {
  foreach ($grp in @('wheels', 'tires')) {
    $tex = [HeatTool.Boot]::ListTextures("vehicles/sharedcustomizedparts/$grp/")
    $dir = Join-Path $OutRoot "_texturas_rodas\$grp"
    $ok = 0; $err = 0
    foreach ($t in $tex) {
      $leaf = $t -replace '.*/', ''
      $r = [HeatTool.Boot]::ExportTexture($t, (Join-Path $dir "$leaf.$Fmt"), $Fmt)
      if ($r.StartsWith('OK')) { $ok++ } else { $err++ }
    }
    $okTotal += $ok; $errTotal += $err
    Write-Host ("{0,-50} {1,4} texturas  {2}" -f "[compartilhado] $grp", $ok, $(if ($err) { "($err falhas)" } else { '' }))
  }
}

Write-Host "TOTAL: $okTotal texturas, $errTotal falhas, $([math]::Round($swAll.Elapsed.TotalMinutes,2)) min"
