# PIPELINE

1. Carregar configuração.
2. Resolver caminhos absolutos.
3. Descobrir arquivos de entrada.
4. Validar presença e colunas mínimas.
5. Gerar backup dos insumos.
6. Extrair ID do plano.
7. Extrair data e hora do disparo.
8. Ler o projeto e o realizado.
9. Mesclar os dados pelo `Number`.
10. Preencher `DetonatingTime` vazio por interpolação linear determinística, quando habilitado.
11. Aplicar simulação determinística de variação em `tampao realizado` quando configurada.
12. Montar a tabela final de saída.
13. Montar o resumo.
14. Exportar o Excel.
15. Registrar log da execução.
