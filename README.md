# Caminhos UFV — ciência aberta

[Abrir no Google Colab](https://colab.research.google.com/github/alexandrerodrigues2311/caminhos-ufv-ciencia-aberta/blob/main/caminhos-ufv-ciencia-aberta.ipynb)

Execute as células na ordem indicada. Python 3.12 ou superior, dependências fixadas em requirements.txt. O notebook inclui preparação, filtros, qualidade, quatro classificadores com validação cruzada, mediação exploratória por bootstrap, GEE com moderação, gráficos e rede agregada. O núcleo é o mesmo do aplicativo.

**Todos os 400 registros distribuídos são sintéticos.** Não existem respostas reais ou credenciais neste repositório. Não use estes resultados como evidência sobre Viçosa ou a UFV. Dados reais só podem ser lidos por quem já possui autorização na planilha, em uma cópia privada do notebook. A integração autenticada Google requer execução no Colab e permissão da própria conta.

Para rodar localmente, instale requirements.txt e abra o notebook no Jupyter; mantenha a fonte sintética ou configure um arquivo JSON local. A primeira célula usa a instrução %pip do IPython.

Não há licença de redistribuição de dados pessoais: eles não fazem parte deste pacote. Código e simulação disponibilizados para inspeção e reprodução; a escolha de licença formal e depósito com DOI fica a cargo dos autores.

## Cartografia e inspeção individual
O notebook inclui mapa real, contorno UFV, 14 referências, ruas vetoriais, seleção por resposta, proveniência dos destinos, diagnósticos por vínculo e testes de coerência. territorial_map e destination_for estão integralmente no notebook e em territorio.py. Cartografia © OpenStreetMap contributors, ODbL 1.0: https://www.openstreetmap.org/copyright. O contorno é colaborativo, não cadastral. Não se estimam rotas percorridas. Nomes A/B/C só recebem pontos se a opção ilustrativa for ativada e a resposta for sintética.

## Geração da base
engine.js e questionario.schema.json documentam as regras originais. Com Node.js, execute `node gerar-simulacao.mjs` para gerar uma base com a mesma semente. Datas de criação do pacote podem diferir; compare as respostas e os identificadores, não a formatação do JSON. O snapshot distribuído é verificado por SHA256 no notebook.
