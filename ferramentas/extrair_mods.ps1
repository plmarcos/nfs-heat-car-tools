# Extrai as pecas de MODIFICACAO (as variantes _alt*/_set* que a extracao
# original descartava, ficando so' com a stock de cada slot).
#
# Grava por PASTA DE VEICULO, nao por carro: 168 carros saem de 115 pastas, e
# variante de carroceria compartilha as mesmas pecas. Gravar por carro
# duplicaria o mesmo arquivo varias vezes.
param(
  [string]$OutRoot = 'F:\CarsNfSHeat',
  [string]$Only = '',
  [int]$Limit = 0,
  [switch]$IncluirStock   # tambem regrava a peca stock, para ter o slot completo
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
# Onde esta' o Export.cs: ao lado deste script. Antes era um caminho absoluto
# da maquina do autor, e quem clonasse o repositorio nao achava o arquivo.
$SP = $PSScriptRoot
if (-not (Test-Path (Join-Path $SP 'Export.cs'))) {
  throw "Export.cs nao esta' em $SP -- mantenha os scripts juntos."
}
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

$folders = [HeatTool.Boot]::ListVehicleFolders() | Sort-Object
if ($Only)      { $folders = $folders | Where-Object { $_ -like "*$Only*" } }
if ($Limit -gt 0) { $folders = $folders | Select-Object -First $Limit }
Write-Host "pastas a processar: $($folders.Count)"

$relatorio = New-Object System.Collections.ArrayList
$swAll = [Diagnostics.Stopwatch]::StartNew()
$totOk = 0; $totFalha = 0; $totPulado = 0
$iF = 0

foreach ($folder in $folders) {
  $iF++
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $all = [HeatTool.Boot]::ListMeshes($folder) | Where-Object { $_ -match '/customisation/' }
  if (-not $all -or $all.Count -eq 0) {
    Write-Host ("{0,-46} sem pecas de customizacao" -f $folder); continue
  }

  $destino = Join-Path (Join-Path $OutRoot $folder) 'mods'
  $ok = 0; $falha = 0; $pulado = 0

  foreach ($m in $all) {
    $leaf = ($m -replace '.*/', '') -replace '_mesh$', ''
    $p = $leaf -replace "^$([regex]::Escape($folder))_", ''
    $prefixo = $p -replace '_alt[a-z0-9]+$', '' -replace '_set[a-z0-9]+$', ''
    $ehStock = ($p -eq "${prefixo}_seta") -or ($p -eq "${prefixo}_set0") -or ($p -eq $prefixo)
    if ($ehStock -and -not $IncluirStock) { continue }

    $arq = Join-Path (Join-Path $destino $prefixo) ($p + '.obj')
    if (Test-Path $arq) { $pulado++; continue }
    $r = [HeatTool.Boot]::ExportOne($m, $arq, 0, $true)
    if ($r.StartsWith('OK')) { $ok++ } else { $falha++; Write-Host "    FALHOU $p : $r" }
  }

  $totOk += $ok; $totFalha += $falha; $totPulado += $pulado
  [void]$relatorio.Add([pscustomobject]@{
    pasta = $folder; exportadas = $ok; falhas = $falha; puladas = $pulado;
    segundos = [math]::Round($sw.Elapsed.TotalSeconds, 1) })
  Write-Host ("{0,3}/{1}  {2,-46} ok:{3,-5} falha:{4,-3} pulada:{5,-5} [{6:N1}s]" -f `
    $iF, $folders.Count, $folder, $ok, $falha, $pulado, $sw.Elapsed.TotalSeconds)
}

$relatorio | Export-Csv -Path (Join-Path $OutRoot '_mods_relatorio.csv') -NoTypeInformation -Encoding UTF8
Write-Host "`nTOTAL exportadas:$totOk falhas:$totFalha puladas:$totPulado  em $([math]::Round($swAll.Elapsed.TotalMinutes,2)) min"
