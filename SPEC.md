# SPEC

## Objetivo
Gerar um Excel de plano de fogo realizado a partir dos arquivos operacionais PP, com validação prévia, backup e rastreabilidade.

## Entradas
- Projeto: `OPIT-PP*PROJETO COMPLETO*`
- Realizado: `OPIT-PP*CONFIG FINAL*`
- Plano PDF: `PP.pdf`
- Histórico: `HISTO-*.txt`

## Regras
- O ID do plano vem do PDF; se não existir, usa fallback documentado.
- A data/hora vem do último evento `[Fire]` do histórico; se não existir, usa a hora atual.
- Registros com `eliminated == 1` não entram na saída.
- O campo `eliminated` é tratado como opcional no arquivo final; quando ausente, a validação não bloqueia a execução.
- `DetonatingTime` vazio é preenchido por interpolação linear determinística entre valores válidos da sequência ordenada por `Number`, com arredondamento para inteiro.
- Quando a simulação de teste de tampão estiver habilitada, `tampao realizado` recebe uma variação determinística de até `0,12` para mais ou para menos.
- `X` e `Y` são preenchidos a partir do arquivo final e, se faltarem, do arquivo de projeto.
- `Z (crest)` e `Z (toe)` devem refletir a geometria do arquivo final quando disponível.
- O arquivo de saída é nomeado com o ID do plano.

## Validação
- Verificar existência dos arquivos obrigatórios.
- Verificar colunas mínimas do projeto e do realizado.
- Abort ar com erro claro se algo crítico faltar.

## Determinismo
- Ordenação por `Number`.
- Formatos e nomes fixos via configuração.
- Backup por timestamp.
