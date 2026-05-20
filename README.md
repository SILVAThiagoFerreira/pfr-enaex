# PFR

Sistema para gerar o plano de fogo realizado em Excel a partir de arquivos operacionais da frente PP.

## Fluxo
1. Descobre os arquivos de entrada.
2. Valida estrutura e colunas.
3. Cria backup dos insumos.
4. Resolve ID do plano e data/hora do disparo.
5. Consolida os dados e aplica as regras de negócio, incluindo preenchimento determinístico de `tempo detonacao (ms)` vazio e, em modo de teste, variação controlada de `tampao realizado`.
6. Exporta o Excel final com rastreabilidade.

## Entradas
- `data/inputs/PP/OPIT-PP*PROJETO COMPLETO*.csv|xlsx`
- `data/inputs/PP/OPIT-PP*CONFIG FINAL*.csv|xlsx`
- `data/inputs/PP/PP.pdf`
- `data/inputs/PP/HISTO-*.txt`

## Saídas
- `data/outputs/PP/Plano_Fogo_Realizado_<PLANO>.xlsx`
- `data/web_runs/<execucao>/output/Plano_Fogo_Realizado_<PLANO>.xlsx` quando executado pela interface web
- `data/backup/<timestamp>/...`
- `logs/geracao_<data>.log`

## Execução
```bash
python main.py --config config.yaml
```

## Interface web
```bash
python main.py --web --config config.yaml
```

Acesse `http://127.0.0.1:5000`, anexe os arquivos operacionais e baixe o Excel gerado. Cada execução web usa uma pasta isolada em `data/web_runs/`, mantendo backup, validação e logs do pipeline.

## GitHub Pages
O projeto tambem possui uma versao one page em `docs/` para GitHub Pages. Nessa versao, o processamento roda no navegador com JavaScript: o usuario anexa os inputs e baixa o XLSX na mesma URL publicada.

## Estrutura
- `src/` contém a lógica modular.
- `tests/` contém testes de fumaça e validação básica.
- `input/`, `output/`, `logs/` existem como diretórios operacionais e de suporte.
- `VISUAL/` contém os ativos de identidade usados na interface web.
