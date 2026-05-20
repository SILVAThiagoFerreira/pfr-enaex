# TASK

Reestruturar o gerador de plano de fogo em uma base modular, configurável e validada, preservando a capacidade de processar o layout PP atual e produzir o Excel final com rastreabilidade.

Evolucao atual:
- adicionar interface web local no mesmo entrypoint `main.py`;
- permitir upload dos inputs operacionais;
- executar o pipeline validado em pasta isolada por execucao;
- disponibilizar download do Excel final;
- aplicar identidade visual Enaex a partir da pasta `VISUAL`.

Regras operacionais atuais:
- `DetonatingTime` vazio é preenchido por interpolação linear determinística na sequência ordenada por `Number`.
- `DetonatingTime` imputado é arredondado para inteiro, sem casas decimais.
- Valores originais de tampão não são alterados automaticamente; padrões repetitivos devem ser tratados como sinal de validação, não com randomização.
- Em modo de teste, `tampao realizado` pode receber variação determinística de até `0,12` para mais ou para menos.

Critério objetivo de conclusão:
- o projeto possui documentação completa;
- a configuração centraliza caminhos e parâmetros;
- o fluxo executa por um único entrypoint;
- a interface web executa por `python main.py --web`;
- as etapas de leitura, validação, processamento e exportação estão separadas.
