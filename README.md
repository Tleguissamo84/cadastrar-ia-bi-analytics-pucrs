# Cadastrar.IA | BI e Analytics

Versão preparada para revisão antes da divulgação. O projeto acadêmico compara a documentação disponível em duas etapas para dez peças de vestuário e apresenta, em um fluxo separado, uma previsão semanal com dados históricos externos.

## Visualizar e reconstruir o dashboard

Abra [docs/index.html](docs/index.html) em um navegador com JavaScript. O HTML é autônomo, funciona offline e incorpora somente os resultados agregados fornecidos. A seção Método A/B explica a origem dos valores e a indisponibilidade da galeria nesta versão. As cores aparecem como sete sugestões mantidas e três corrigidas, sem descrição ou código de peça.

Requer Python 3.12 para a reprodução testada. O dashboard e a auditoria do pacote usam apenas a biblioteca padrão.

~~~powershell
python -B painel/gerar.py
python -B testes/auditar.py
python -m http.server 8000 --bind 127.0.0.1 --directory docs
~~~

No modo servidor, abra `http://127.0.0.1:8000/`. O [notebook](Painel_Publico.ipynb) exibe o mesmo HTML em Jupyter/IPython. Em sessão Colab autorizada, forneça somente o index.html público, com esse nome no diretório de trabalho, e execute a célula. O notebook é distribuído sem saídas nem metadados de execução. A galeria de fotografias e etiquetas permanece no acervo restrito.

Para repetir o teste de navegação, use Node.js com Playwright e Chromium instalados e execute `node testes/navegador.cjs`. Os parâmetros opcionais PLAYWRIGHT_PATH e BROWSER_PATH permitem selecionar as instalações locais.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| docs/index.html e docs/.nojekyll | Página estática e configuração do diretório de publicação. |
| painel | Gerador, modelo HTML, CSS e JavaScript da versão agregada. |
| dados/documental.json | Estados, procedência, indicadores, testes, pendências e cores agregados. |
| dados/uci | Proveniência, resumo, série semanal, métricas, previsões agregadas e três figuras. |
| codigo/documental | Preparação e indicadores A/B com fontes e saídas mantidas fora do pacote. |
| codigo/uci | Preparação, modelos, gráficos e execução do estudo externo. |
| testes | Auditoria automatizada do pacote e verificação do dashboard no navegador. |
| MANIFESTO_SHA256.json | Lista exata dos arquivos do pacote e checksums. |

## Método documental A/B

As mesmas dez peças produzem 190 registros em cada etapa, com 19 atributos por peça. A foi reconstruída retrospectivamente de forma controlada a partir de fotografias admissíveis. B agrega etiquetas originais e preserva a distinção entre evidência, declaração humana e classificação derivada. A máscara de aplicabilidade é pareada.

A completude global usa quatro blocos com pesos iguais, incluindo as cinco famílias de conservação dentro do bloco de conservação. O forro é complementar. Condição, cor e controles fotográficos ficam fora da completude global. A cobertura divide testes avaliáveis pelos testes aplicáveis previstos. A consistência divide aprovados pelos avaliáveis. A rastreabilidade divide cadeias verificáveis pelos valores apresentados. Recortes com denominador ausente ou pendente conservam seu estado.

No recorte comparável, país de fabricação passou de 0/10 em A a 10/10 em B. A composição principal passou de 0/10 a 9/10. A completude global permanece sem percentual. Trata-se de evidência documental da amostra, com limitações de generalização, validação humana e desenho retrospectivo.

O painel público é reproduzível a partir desses agregados. A reprodução integral dos cálculos A/B requer acesso autorizado às entradas documentais e à estrutura original. Os scripts preservam a validação de hashes e registram os resultados detalhados em pasta externa ao pacote e ao projeto de entrada. Em PowerShell, configure as variáveis abaixo na sessão local do custodiante. Use caminhos reais apenas na própria sessão.

~~~powershell
$env:CADASTRAR_PROJETO_PRIVADO = '<pasta do projeto privado autorizado>'
$env:CADASTRAR_PREFIXO_LEGADO = '<prefixo original dos localizadores históricos>'
$env:CADASTRAR_SAIDA_PRIVADA = '<pasta nova fora deste pacote e do projeto privado>'
python -B codigo/documental/preparar_base.py
python -B codigo/documental/indicadores.py --data-execucao 2026-11-26
~~~

A preparação exige na estrutura original a matriz da revisão B, o registro de integridade, a lista de pendências, o catálogo de fontes B, o registro de execução B, o dicionário de dados, a máscara utilizada e as evidências referenciadas. O prefixo legado é necessário quando o registro de origem usa caminhos absolutos. A pasta de saída precisa ter um diretório pai existente. Mantenha os CSVs detalhados e suas trilhas fora do repositório.

## Estudo preditivo externo

A UCI Online Retail II é um conjunto transacional externo. O alvo é a soma semanal de unidades registradas no recorte elegível, prevista uma semana à frente. Na sobreposição de dezembro de 2010 usa-se uma aba por data. A elegibilidade usa faturas numéricas, exclui cancelamentos e exige quantidade inteira positiva, preço positivo e código compatível. A rotina registra exclusões em pasta de trabalho e avalia a sensibilidade às repetições e à escolha da aba. Semanas sem alvo permanecem nulas.

Comparam-se a última semana observada, a média de quatro semanas e Ridge com alpha definido na validação cronológica. Nos 13 casos de teste comuns, a média de quatro semanas teve o menor MAE e RMSE. A previsão cobre o histórico de um varejista e uma janela de teste concentrada no fim do ano. Seus resultados descrevem volume registrado e ficam separados da avaliação documental do Cadastrar.IA.

Para reproduzir com a base oficial, instale as dependências num ambiente Python 3.12 e mantenha a base bruta fora do repositório.

~~~powershell
python -m pip install -r requirements.txt
python -B codigo/uci/executar.py --entrada "../insumos_uci" --saida "../reproducao_uci" --data-execucao 2026-11-26
~~~

Baixe o ZIP a partir do endereço oficial em [proveniência](dados/uci/proveniencia.json), salve-o como online_retail_ii_original.zip na pasta de entrada e extraia online_retail_II.xlsx para a mesma pasta. O script valida os dois arquivos antes de ler o XLSX. Informe uma pasta de saída nova, fora do pacote e da pasta de entrada, com diretório pai existente. As trilhas por linha e a base bruta são materiais de reprodução local. Compare a série semanal, as previsões selecionadas e as métricas com as saídas agregadas distribuídas.

## Publicação e atribuição

Consulte [direitos e atribuição](DIREITOS_E_ATRIBUICAO.md) e [auditoria](AUDITORIA_PUBLICACAO.md). A divulgação do código autoral, dos agregados e do painel depende de autorização. O pacote não atribui licença aberta ao código. O plano de publicação está documentado na auditoria.

