# DATA_SCHEMA

## Projeto PP
Arquivo: `OPIT-PP*PROJETO COMPLETO*`

Campos principais:
- `Number` integer
- `UTM_X` float
- `UTM_Y` float
- `Length_m` float
- `Stemming_m` float
- `Diameter_mm` float
- `Subdrilling_m` float
- `Angle_deg` float
- `Azimuth_deg` float
- `Total_Charge_kg` float

## Realizado PP
Arquivo: `OPIT-PP*CONFIG FINAL*`

Campos principais:
- `Number` integer
- `X` float
- `Y` float
- `Z` float
- `X_Toe` float
- `Y_Toe` float
- `Z_Toe` float
- `Length` float
- `Stemming` float
- `Diameter` float
- `Subdrilling` float
- `Angle` float
- `Azimuth` float
- `DetonatingTime` float, pode ser imputado por interpolação quando vier vazio
- `InputedCharge` float
- `eliminated` integer, optional

## Simulação de teste
- `tampao realizado` pode receber variação determinística de até `0,12` para mais ou para menos quando habilitado na configuração.

## Saída Excel
Abas:
- `Dados dos Furos`
- `Resumo`

Colunas principais em `Dados dos Furos`:
- `Data`, `Horario`, `Plano`, `Tipo`, `id`, `y`, `x`, `Z (crest)`, `Z (toe)`, `profundidade prevista`, `profundidade realizada`, `azimute`, `inclinacao`, `cargas previstas`, `cargas realizadas`, `tampao previsto`, `tampao realizado`, `subfuracao`, `diametro`, `tempo detonacao (ms)`
