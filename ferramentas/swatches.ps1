param(
  [string]$OutRoot = 'F:\CarsNfSHeat',
  [string]$Fmt = 'png',
  [switch]$Liveries
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

$jobs = @(@{ Src = 'vehicles/customization/swatches/'; Dst = '_swatches' })
if ($Liveries) { $jobs += @{ Src = 'vehicles/customization/liveries/'; Dst = '_liveries' } }

$swAll = [Diagnostics.Stopwatch]::StartNew()
$grandOk = 0; $grandErr = 0

foreach ($job in $jobs) {
  $tex = [HeatTool.Boot]::ListTextures($job.Src)
  Write-Host "$($job.Src) -> $($tex.Count) texturas"
  $ok = 0; $err = 0; $i = 0
  foreach ($t in $tex) {
    # keep the game's folder tree under the destination
    $rel = $t.Substring($job.Src.Length)
    $out = Join-Path (Join-Path $OutRoot $job.Dst) (($rel -replace '/', '\') + ".$Fmt")
    $r = [HeatTool.Boot]::ExportTexture($t, $out, $Fmt)
    if ($r.StartsWith('OK')) { $ok++ } else { $err++; if ($err -le 3) { Write-Host "  ! $rel : $r" } }
    $i++
    if ($i % 500 -eq 0) { Write-Host "  ... $i / $($tex.Count)" }
  }
  Write-Host ("{0,-22} {1,5} exportadas  {2}" -f $job.Dst, $ok, $(if ($err) { "($err falhas)" } else { '' }))
  $grandOk += $ok; $grandErr += $err
}

Write-Host "TOTAL: $grandOk texturas, $grandErr falhas, $([math]::Round($swAll.Elapsed.TotalMinutes,2)) min"
