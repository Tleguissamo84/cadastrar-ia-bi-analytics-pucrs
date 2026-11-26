# Auditoria de preparação para publicação

## Escopo

O manifesto identifica os arquivos incluídos e o SHA-256 de cada item, com exceção do próprio manifesto. A auditoria usa uma lista fechada e examina o texto, as chaves dos dados, o conteúdo incorporado ao HTML, as saídas do notebook e os metadados dos PNGs. Os caminhos históricos usados pelo processamento documental só são informados na sessão privada do custodiante.

| Material | Decisão |
|---|---|
| Código A/B e UCI, HTML, CSS, JavaScript e notebook | Incluídos em versão portátil. As rotinas de reprodução recebem entradas autorizadas fora do pacote. |
| Indicadores, cobertura, rastreabilidade e estados | Incluídos por etapa e bloco, com denominadores e sem linhas por peça. |
| Pendências e cores | Incluídos como contagens. A lista de revisão, as justificativas, os rótulos individuais e os códigos das peças ficam restritos. |
| Previsão UCI | Incluídos os volumes semanais, as previsões agregadas, as métricas, os gráficos e a proveniência. A fonte tem atribuição e licença próprias. |
| Fotos, etiquetas e outros anexos de evidência | Excluídos. O painel informa a indisponibilidade da galeria no recorte público. |
| Matrizes A/B, máscara e dicionário privados, inventários e trilhas | Excluídos. Contêm granularidade de peça, localizadores, trechos ou detalhes de evidência. |
| Base UCI bruta, chaves de clientes e faturas, trilhas por linha e arquivos exploratórios | Excluídos. A base pode ser obtida na fonte oficial para reprodução local. |
| Relatório, apresentação, templates, arquivos administrativos, especificações e acervo interno | Excluídos. Fazem parte da entrega acadêmica ou do ambiente privado. |
| Histórico de repositório, arquivos de ambiente, credenciais, chaves e saídas com metadados do notebook | Excluídos. O painel funciona com arquivos estáticos e o notebook é distribuído limpo. |

## Verificações executadas em 26/11/2026

- **Reprodução A/B.** O código empacotado gerou quatro CSVs byte a byte idênticos aos originais em pasta temporária externa, incluindo os 442 recortes e 1.040 testes. As entradas documentais autorizadas foram usadas localmente e as quatro saídas detalhadas ficaram fora do pacote.
- **Reprodução UCI.** A execução verificou o ZIP e o XLSX pelos hashes registrados e reproduziu de forma idêntica a série semanal, as previsões de validação e teste, as métricas e a série de sensibilidade. A comparação pública também conferiu as figuras, as 13 previsões semanais e as métricas com as saídas originais.
- **Dashboard e notebook.** O Chromium verificou as seis seções, a navegação por teclado, os valores e denominadores selecionados, os três gráficos UCI e o layout móvel. O mesmo HTML funcionou isolado e em um subcaminho de servidor estático local, sem requisições externas. O notebook foi executado em IPython e sua saída testada em iframe. O teste em hospedagem real fica para depois da autorização.
- **Integridade e confidencialidade.** A auditoria aprovou a lista fechada, a reconstrução do HTML, o notebook sem saídas e os metadados das três figuras. A última varredura não encontrou sinais de credenciais ou caminhos absolutos de máquina nos arquivos selecionados. A projeção retém somente campos agregados permitidos. Os hashes de 20 arquivos de origem conferiram antes e depois.

A busca automatizada cobre sinais conhecidos de credenciais, endereços, localizadores de máquina e campos privados. A lista fechada e a projeção dos dados complementam a busca. A seleção foi preparada para revisão e ainda depende da decisão do titular sobre divulgação, direitos do código e divulgação dos agregados documentais, incluindo a caracterização por cores.

## Procedimento após autorização

1. Aprovar a lista de arquivos e decidir a visibilidade do repositório e as condições de uso do código da Trametria. Autorizar expressamente a divulgação do dashboard e dos agregados documentais.
2. Criar um repositório independente no GitHub com o conteúdo desta pasta. Conferir a lista de arquivos a serem enviados contra o manifesto. Utilizar apenas as credenciais que o titular escolher para essa execução.
3. Para a demonstração estática, usar a aba Pages do repositório, selecionar a publicação a partir do branch autorizado e a pasta /docs. O ponto de entrada é docs/index.html. Verificar com um perfil sem credenciais se o endereço público, as seis seções e os gráficos estão acessíveis.
4. Se a entrega for apresentada via Colab, disponibilizar o notebook e o mesmo HTML público no ambiente autorizado e revisar a execução. Registrar as URLs reais do repositório e da visualização publicada no relatório acadêmico.
5. Revisar os links e o acesso do avaliador e montar a entrega acadêmica na pasta própria após autorização.

[Configuração oficial do GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

