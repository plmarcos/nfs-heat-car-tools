# Levanta TODAS as pecas de customizacao do jogo, inclusive as variantes _alt*
# que a extracao original descartava. So' lista: nao escreve nada no acervo.
param([string]$Csv = 'F:\CarsNfSHeat\_mods_levantamento.csv')
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

$linhas = New-Object System.Collections.ArrayList
$folders = [HeatTool.Boot]::ListVehicleFolders()
Write-Host "pastas de veiculo: $($folders.Count)"
$i = 0
foreach ($folder in $folders) {
  $i++
  $all = [HeatTool.Boot]::ListMeshes($folder)
  foreach ($m in $all) {
    $leaf = ($m -replace '.*/', '') -replace '_mesh$', ''
    $p = $leaf -replace "^$([regex]::Escape($folder))_", ''
    $prefixo = $p -replace '_alt[a-z0-9]+$', '' -replace '_set[a-z0-9]+$', ''
    $variante = ''
    if ($p -match '_(alt[a-z0-9]+)$') { $variante = $Matches[1] }
    elseif ($p -match '_(set[a-z0-9]+)$') { $variante = $Matches[1] }
    $tipo = 'outro'
    if ($m -match '/customisation/') { $tipo = 'customisation' }
    elseif ($m -match '/chopshop/') { $tipo = 'chopshop' }
    elseif ($m -match "^vehicles/player/$([regex]::Escape($folder))/[^/]+_mesh$") { $tipo = 'corpo' }
    [void]$linhas.Add([pscustomobject]@{
      pasta = $folder; mesh = $m; folha = $p; prefixo = $prefixo; variante = $variante; tipo = $tipo })
  }
  if ($i % 25 -eq 0) { Write-Host "  $i/$($folders.Count)" }
}
$linhas | Export-Csv -Path $Csv -NoTypeInformation -Encoding UTF8
Write-Host "linhas: $($linhas.Count)  ->  $Csv"
