(function painel() {
  "use strict";

  const dados = JSON.parse(document.getElementById("dados").textContent);
  const main = document.querySelector("main");
  const int = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
  const etapas = ["A", "B"];
  const blocos = ["identificacao", "origem", "composicao", "conservacao", "forro"];
  const estados = {
    confirmado: ["Confirmado", "#188276"],
    declarado: ["Declarado", "#5279ba"],
    ausente: ["Ausente", "#abbac6"],
    ilegivel: ["Ilegível", "#a55e76"],
    conflitante: ["Conflitante", "#a0444d"],
    pendente_validacao: ["Pendente de validação", "#c28929"],
    nao_avaliado: ["Não avaliado", "#7e6d9c"],
    nao_aplicavel: ["Não aplicável", "#56707e"],
  };
  const origens = {
    fotografia: "Fotografia da peça",
    etiqueta: "Etiqueta original",
    declaracao: "Declaração humana",
    derivacao: "Valor derivado",
    outro: "Outra origem registrada",
  };
  const rotulos = {
    identificacao: "Identificação", origem: "Origem", composicao: "Composição principal",
    conservacao: "Conservação", forro: "Forro (complementar)", global: "Global",
    categoria: "Categoria", marca: "Marca", tamanho_rotulo: "Tamanho de etiqueta",
    condicao: "Condição", cor_comercial: "Cor comercial", pais_fabricacao: "País de fabricação",
    composicao_principal: "Composição principal", composicao_forro: "Composição do forro",
    lavagem_ciclo: "Ciclo de lavagem", passadoria: "Passadoria", lavagem: "Lavagem",
    alvejamento: "Alvejamento", secagem_tambor: "Secagem em tambor",
    secagem_natural: "Secagem natural", limpeza_seco: "Limpeza a seco",
    limpeza_umido: "Limpeza profissional a úmido", familias_conservacao: "Famílias de conservação",
  };
  const situacoes = {
    avaliavel: "Calculável", parcial: "Parcial", pendente: "Pendente", nao_definido: "Não definido",
  };
  const provaEtapa = etapa => `<span class="etapa etapa-${etapa === "A/B" ? "ab" : etapa.toLowerCase()}">${etapa === "A/B" ? "A/B" : `Etapa ${etapa}`}</span>`;
  const escape = valor => String(valor ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
  const label = chave => rotulos[chave] ?? chave;
  const quantidade = valor => int.format(valor);
  const pct = valor => `${quantidade(valor)}%`;
  const titulo = (nome, texto) => `<div class="page-head"><h1>${nome}</h1><p class="lead">${texto}</p></div>`;
  const badge = (situacao, texto = situacoes[situacao]) =>
    `<span class="status status-${escape(situacao)}">${escape(texto)}</span>`;
  const card = (nome, numero, texto) =>
    `<div class="card"><div class="card-label">${nome}</div><strong class="card-number">${numero}</strong><div class="card-note">${texto}</div></div>`;
  const trow = (chave, ...celulas) =>
    `<tr><th scope="row">${chave}</th>${celulas.map(c => `<td>${c}</td>`).join("")}</tr>`;
  const tabela = (cabecalhos, linhas, nome) => `
    <div class="table-wrap" tabindex="0" role="region" aria-label="${escape(nome)}">
      <table class="data-table" aria-label="${escape(nome)}"><thead><tr>${cabecalhos.map(h => `<th scope="col">${h}</th>`).join("")}</tr></thead>
      <tbody>${linhas}</tbody></table>
    </div>`;
  const resultados = new Map(dados.indicadores.map(r => [`${r.indicador}/${r.etapa}/${r.bloco}`, r]));
  const resultado = (indicador, etapa, bloco) => resultados.get(`${indicador}/${etapa}/${bloco}`);
  const totalEtapa = etapa => Object.values(dados.estados[etapa]).reduce((s, n) => s + n, 0);

  function painel(nome, texto, conteudo) {
    return `<section class="panel"><h2>${nome}</h2><p class="panel-intro">${texto}</p>${conteudo}</section>`;
  }

  function tabelaPequena(linhas, a, b, nome) {
    return `<table class="mini-table" aria-label="${escape(nome)}"><thead><tr><th scope="col">${nome}</th><th scope="col">${a}</th><th scope="col">${b}</th></tr></thead><tbody>${linhas}</tbody></table>`;
  }

  function distribuicao() {
    const barras = etapas.map(e => {
      const total = totalEtapa(e);
      const segmentos = Object.entries(estados).map(([estado, [nome, cor]]) => {
        const n = dados.estados[e][estado] ?? 0;
        return n ? `<span style="width:${100 * n / total}%;background:${cor}" title="${nome} · ${n} de ${total}"></span>` : "";
      }).join("");
      return `<div class="stack-row" aria-hidden="true">${provaEtapa(e)}<div class="stack-bar">${segmentos}</div></div>`;
    }).join("");
    const linhas = Object.entries(estados).map(([chave, [nome, cor]]) =>
      trow(`<span class="dot" style="background:${cor}" aria-hidden="true"></span>${nome}`,
        dados.estados.A[chave] ?? 0, dados.estados.B[chave] ?? 0)).join("");
    return barras + tabelaPequena(linhas, `${provaEtapa("A")} · ${totalEtapa("A")}`, `${provaEtapa("B")} · ${totalEtapa("B")}`, "Estado");
  }

  function barrasComparacao(bloco) {
    const a = resultado("completude", "A", bloco);
    const b = resultado("completude", "B", bloco);
    const comparavel = [a, b].every(r => r?.situacao === "avaliavel" && r.percentual !== null)
      && a.denominador === b.denominador;
    const diferenca = comparavel ? b.percentual - a.percentual : null;
    const delta = diferenca === null ? "" : `<span class="ganho">${diferenca > 0 ? "+" : ""}${quantidade(diferenca)} p.p.</span>`;
    const linhas = etapas.map(e => {
      const r = resultado("completude", e, bloco);
      if (!r || r.percentual === null) {
        return `<div class="metric-line">${provaEtapa(e)}<span></span>${badge(r?.situacao ?? "nao_definido")}</div>`;
      }
      return `<div class="metric-line">
        ${provaEtapa(e)}<div class="rail" aria-hidden="true" data-zero="${r.percentual === 0}" style="--bar:var(${e === "A" ? "--blue" : "--teal"})"><span style="width:${r.percentual}%"></span></div>
        <strong>${pct(r.percentual)} · ${quantidade(r.numerador)}/${quantidade(r.denominador)}</strong>
      </div>`;
    }).join("");
    return `<div class="bar-group"><div class="bar-heading"><h3>${bloco === "origem" ? "País de fabricação" : label(bloco)}</h3>${delta}</div>${linhas}</div>`;
  }

  function visaoGeral() {
    const n = totalPendencias(dados.pendencias.acoes_humanas);
    return titulo("Qualidade documental", "Compare o que foi possível documentar nas mesmas dez peças com fotografias em A e com as evidências adicionais em B.") +
      `<div class="cards">
        ${card("Peças analisadas", dados.amostra_produtos, "Amostra documental pareada")}
        ${card("Registros na Etapa A", totalEtapa("A"), `${dados.atributos} atributos por peça`)}
        ${card("Registros na Etapa B", totalEtapa("B"), `${dados.registros} registros na matriz A/B`)}
        ${card("Ações humanas em aberto", n, `De ${Object.values(dados.pendencias).reduce((t, p) => t + totalPendencias(p), 0)} entradas na lista de revisão`)}
      </div><div class="grid">
      ${painel("Estados dos atributos", "Contagens por etapa, incluindo caracterização e controles fotográficos. Os estados descrevem registros e não medem a completude documental.", distribuicao())}
      ${painel("Ganho documental em B", "Variação da completude nas mesmas dez peças, em pontos percentuais. As barras usam escala de 0 a 100%.", `
        ${barrasComparacao("origem")}${barrasComparacao("composicao")}
        <p class="callout"><strong>Completude global sem percentual.</strong> Identificação e conservação têm decisões em aberto nas duas etapas.</p>
        <p class="note">A diferença descreve o que passou a ter suporte documental em B. O estudo retrospectivo não mede acurácia da IA, causalidade ou desempenho do software.</p>
        <a class="section-link" href="#indicadores">Ver denominadores e demais blocos&nbsp; →</a>`)}
      </div>`;
  }

  function celulaCompletude(r) {
    if (!r) return badge("nao_definido");
    if (r.percentual === null) return badge(r.situacao);
    const partes = r.denominador !== null && r.numerador !== null
      ? `<span class="dim">${quantidade(r.numerador)}/${quantidade(r.denominador)} peças</span>` : "";
    return `<strong>${pct(r.percentual)}</strong>${partes}<span class="dim">${badge(r.situacao)}</span>`;
  }

  function celulaRastreabilidade(r) {
    if (!r) return badge("nao_definido");
    const comValores = r.denominador !== null && r.denominador > 0 && r.numerador !== null;
    const base = comValores
      ? `<strong>${quantidade(r.numerador)}/${quantidade(r.denominador)} ${r.denominador === 1 ? "valor" : "valores"}</strong><span class="dim">com cadeia verificável</span>`
      : `<span class="dim">${r.denominador === 0 ? "Sem valores apresentados" : "Base indisponível"}</span>`;
    const naoVerificados = comValores
      ? `<span class="dim">${quantidade(r.denominador - r.numerador)} sem cadeia verificável</span>` : "";
    const emAberto = r.pendencias ? `<span class="dim">${quantidade(r.pendencias)} ${r.pendencias === 1 ? "registro" : "registros"} com pendência no recorte</span>` : "";
    return `<div class="metric-detail">${base}
      ${r.percentual === null ? "" : `<span class="dim">${pct(r.percentual)} dos valores apresentados</span>`}
      ${naoVerificados}${emAberto}${badge(r.situacao)}
    </div>`;
  }

  function celulaTestes(etapa, bloco) {
    const cob = resultado("cobertura_testes", etapa, bloco);
    const k = resultado("consistencia", etapa, bloco);
    if (!cob || !k) return badge("nao_definido");
    const d = dados.testes[etapa].por_bloco[bloco] ?? {};
    const cobertura = cob.denominador === null
      ? `${quantidade(cob.numerador)} avaliáveis · denominador pendente`
      : `${quantidade(cob.numerador)} avaliáveis de ${quantidade(cob.denominador)} testes aplicáveis`;
    const aprovacao = k.percentual === null ? "" :
      `<span class="dim">${quantidade(k.numerador)}/${quantidade(k.denominador)} aprovados · ${pct(k.percentual)} dos avaliáveis</span>`;
    const p = d.aplicabilidade_pendente ?? 0;
    return `<div class="metric-detail">
      <strong>${cobertura}${cob.percentual === null ? "" : ` (${pct(cob.percentual)})`}</strong>
      <span class="dim">${quantidade(d.nao_avaliavel ?? 0)} não avaliáveis · ${quantidade(d.nao_executado ?? 0)} sem execução, entre os aplicáveis</span>
      ${p ? `<span class="dim">${quantidade(p)} com aplicabilidade pendente</span>` : ""}
      ${badge(cob.situacao, `Cobertura · ${situacoes[cob.situacao].toLowerCase()}`)}
      <div class="approval"><span class="reading-title">Aprovação entre os avaliáveis</span>
      ${aprovacao}${badge(k.situacao)}</div>
    </div>`;
  }

  function indicadores() {
    const c = [...blocos, "global"].map(b => trow(label(b),
      ...etapas.map(e => celulaCompletude(resultado("completude", e, b))))).join("");
    const r = blocos.map(b => trow(label(b),
      ...etapas.map(e => celulaRastreabilidade(resultado("rastreabilidade", e, b))))).join("");
    const k = blocos.map(b => trow(label(b), ...etapas.map(e => celulaTestes(e, b)))).join("");
    const cabecalho = ["Bloco", ...etapas.map(provaEtapa)];
    const total = etapas.reduce((n, e) => n + dados.testes[e].instancias, 0);
    return titulo("Indicadores documentais", "Percentuais da execução preliminar. Os rótulos distinguem recortes calculáveis, parciais, pendentes e sem base de cálculo.") +
      `<div class="grid equal">
      ${painel("Completude por bloco", "Média das peças aplicáveis. Origem usa o país de fabricação. O denominador inclui a peça cuja etiqueta de composição está ilegível.", `
        ${tabela(cabecalho, c, "Completude por bloco em A e B")}
        <p class="note">A comparação A/B descreve enriquecimento documental nas dez peças. A foi reconstruída retrospectivamente e o desenho não permite concluir acurácia de IA, efeito causal ou desempenho do software.</p>`)}
      ${painel("Rastreabilidade por bloco", "Cadeias documentais verificáveis sobre os valores analíticos apresentados. Em identificação B, um tamanho declarado permanece no denominador.", `
        ${tabela(cabecalho, r, "Rastreabilidade por bloco em A e B")}
        <p class="note">A base da taxa são os valores apresentados. Os registros com pendência podem se sobrepor aos valores sem cadeia verificável. A checagem de arquivos e metadados localiza a sustentação. A fidelidade da leitura exige conferência documental.</p>`)}
      </div>
      ${painel("Cobertura e consistência dos testes", `O catálogo provisório tem ${quantidade(total)} instâncias. Foram avaliáveis ${dados.testes.A.avaliaveis} em A e ${dados.testes.B.avaliaveis} em B. Só ${dados.testes.A.comuns} instâncias foram avaliáveis nas duas etapas.`, `
        ${tabela(cabecalho, k, "Cobertura e consistência por bloco em A e B")}
        <p class="note">A cobertura indica quanto do catálogo aplicável pôde ser avaliado. A aprovação usa somente esses testes avaliáveis. Os demais ficam identificados como sem execução, não avaliáveis ou com aplicabilidade pendente. Bases de testes distintas limitam a comparação entre etapas.</p>`)}`;
  }

  const totalPendencias = grupo => Object.values(grupo).reduce((s, n) => s + n, 0);

  function pendencias() {
    const descricoes = {
      acoes_humanas: "Ações humanas em aberto",
      limitacoes: "Limitações documentais",
      condicao_futura: "Condição metodológica futura",
    };
    const linhas = Object.entries(descricoes).map(([k, nome]) => {
      const grupo = dados.pendencias[k];
      return trow(nome, grupo.A, grupo.B, grupo["A/B"], totalPendencias(grupo));
    }).join("");
    return titulo("Pendências documentais", "Contagens agregadas por etapa e tipo de entrada na lista de revisão.") +
      painel("Entradas por etapa", "Uma ação em aberto sinaliza uma verificação ou decisão ainda necessária.", 
        tabela(["Natureza", provaEtapa("A"), provaEtapa("B"), "A/B", "Total"], linhas, "Pendências agregadas") +
        '<p class="note">A lista inclui limitações constatadas e uma condição metodológica futura. As contagens se referem a entradas de revisão.</p>');
  }

  function metodo() {
    const fontes = Object.entries(origens).filter(([k]) => etapas.some(e => dados.origens[e][k]))
      .map(([k, nome]) => trow(nome, dados.origens.A[k] ?? 0, dados.origens.B[k] ?? 0)).join("");
    return titulo("Método documental A/B", "As mesmas dez peças compõem a amostra pareada. Os 380 registros correspondem a 19 atributos por peça em duas etapas.") +
      '<div class="grid equal">' +
      painel("Etapa A", "Reconstrução retrospectiva controlada.", '<p class="note">Foram utilizadas vistas admissíveis das peças, com ocultação registrada quando necessária para impedir a leitura da etiqueta.</p>') +
      painel("Etapa B", "Complementação com etiquetas originais.", '<p class="note">Declarações humanas e valores derivados mantiveram sua natureza. A máscara de aplicabilidade é pareada entre A e B.</p>') +
      '</div>' +
      painel("Regras de cálculo", "Completude global combina identificação, origem, composição principal e conservação.", 
        '<p class="note">Conservação reúne lavagem, alvejamento, secagem, passadoria e limpeza profissional. O forro é complementar. Condição, cor e controles fotográficos não entram na completude global. Pendências mantêm recortes sem percentual quando não há base para calculá-los.</p>') +
      painel("Origem dos valores apresentados", "Contagem de valores preenchidos, incluindo caracterização e controles fotográficos.",
        tabelaPequena(fontes, provaEtapa("A"), provaEtapa("B"), "Procedência") +
        '<p class="note">O painel público apresenta resultados agregados. A galeria e as fotografias de etiquetas ficam no acervo restrito.</p>');
  }

  function cores() {
    const { mantidas, corrigidas } = dados.cores;
    return titulo("Cores da amostra", "Caracterização complementar a partir de sugestões visuais registradas e da confirmação comercial humana.") +
      `<div class="cards three">
      ${card("Sugestões documentadas", mantidas + corrigidas, "Comparação de rótulos comerciais")}
      ${card("Sugestões mantidas", mantidas, "Mesmo rótulo na confirmação")}
      ${card("Sugestões corrigidas", corrigidas, "Rótulo alterado na confirmação")}
      </div>` + painel("Escopo da comparação", "Os resultados são apresentados em conjunto para a amostra.", 
        '<p class="note">A caracterização por cor fica fora do cálculo de completude. A concordância dos rótulos não mede acurácia de um modelo ou desempenho do software.</p>');
  }

  function previsao() {
    const p = dados.previsao;
    const nomes = { ultima_observada: "Última semana observada", media_4: "Média de quatro semanas", ridge: "Ridge" };
    const data = s => s.split("-").reverse().join("/");
    const periodo = r => `${data(r.inicio_semana)} a ${data(r.ultima_semana)}`;
    const exibirNumero = n => n === null ? "Indisponível" : quantidade(n);
    const menor = campo => Object.keys(nomes).reduce((a, b) => p.metricas[a][campo] <= p.metricas[b][campo] ? a : b);
    const melhorMae = menor("mae");
    const melhorRmse = menor("rmse");
    const resumo = melhorMae === melhorRmse
      ? `${nomes[melhorMae]} obteve o menor MAE e o menor RMSE no teste.`
      : `Menor MAE com ${nomes[melhorMae].toLowerCase()} e menor RMSE com ${nomes[melhorRmse].toLowerCase()}.`;
    const metricas = Object.entries(nomes).map(([k, nome]) => {
      const m = p.metricas[k];
      return trow(nome, quantidade(m.mae), quantidade(m.rmse), m.semanas_avaliadas);
    }).join("");
    const boletim = [
      ["Alvo", "Soma semanal de unidades registradas nas transações elegíveis"],
      ["Horizonte", `${p.horizonte} semana à frente`],
      ["Histórico", `${periodo(p.historico)} · ${p.historico.semanas_calendario} semanas de calendário`],
      ["Treino inicial", `${periodo(p.treino)} · ${p.treino.semanas_calendario} semanas de calendário`],
      ["Validação cronológica", `${periodo(p.validacao)} · ${p.avaliadas_validacao}/${p.validacao.semanas_calendario} semanas comparáveis`],
      ["Teste final", `${periodo(p.teste)} · ${p.metricas.ridge.semanas_avaliadas}/${p.teste.semanas_calendario} semanas comparáveis`],
      ["Regularização Ridge", `Alpha ${quantidade(p.alpha)} escolhido pelo MAE na validação`],
      ["Semanas sem alvo", p.lacunas.map(data).join(", ") || "Nenhuma"],
      ["Limites", "Histórico de um varejista, com lacunas e um teste concentrado no fim do ano. O alvo mede unidades registradas no recorte."],
    ].map(([item, valor]) => trow(item, valor)).join("");
    const semanas = p.semanas_teste.map(s => trow(data(s.semana), exibirNumero(s.observado),
      ...Object.keys(nomes).map(k => exibirNumero(s[k])), s.avaliada ? "Avaliável" : "Fora da avaliação comum")).join("");
    const imagem = (id, alt) => `<div class="forecast-scroll" tabindex="0" role="region" aria-label="Gráfico com rolagem horizontal em telas estreitas">
      <img class="forecast-plot" src="${escape(p.figuras[id])}" alt="${escape(alt)}" decoding="async"></div>`;
    return titulo("Previsão semanal de varejo", "Estudo complementar com histórico externo da UCI Online Retail II. O alvo é o volume de unidades registradas em transações elegíveis do varejista britânico.") +
      painel("Série histórica semanal", "Cada ponto representa a semana iniciada na segunda-feira. Lacunas interrompem a linha e a faixa indica o teste reservado.", 
        imagem("serie", "Volumes semanais observados, com lacunas no fim de 2009 e 2010 e janela de teste sombreada.")) +
      painel("Observado versus previsto", "Os três métodos usam apenas informações anteriores à semana prevista. As datas indicam o início da semana.",
        imagem("teste", "Volumes reais e previsões dos três métodos no teste final.") +
        `<details class="evidence-details"><summary>Ver valores semana a semana</summary>
        ${tabela(["Semana", "Observado", "Última observada", "Média de quatro", "Ridge", "Situação"], semanas, "Observado e previsto por semana")}</details>`) +
      painel("Erros por método", resumo,
        imagem("erros", "Barras pareadas de MAE e RMSE dos três métodos, em unidades.") +
        tabela(["Método", "MAE (unidades)", "RMSE (unidades)", "Semanas avaliadas"], metricas, "Métricas do teste final") +
        `<p class="note">MAE mede o erro absoluto médio. RMSE dá mais peso aos erros grandes. Os três métodos são avaliados nas mesmas semanas.</p>`) +
      painel("Ficha metodológica", "A análise documental A/B continua em suas cinco seções. Esta previsão não mede qualidade cadastral nem desempenho do Cadastrar.IA.",
        tabela(["Item", "Descrição"], boletim, "Protocolo e limites da previsão") +
        `<p class="note">${escape(p.atribuicao)} Licença ${escape(p.licenca)}. <a href="${escape(p.fonte)}" target="_blank" rel="noopener">Fonte oficial</a></p>`);
  }

  const rotas = { "visao-geral": visaoGeral, indicadores, pendencias, metodo, cores, previsao };
  let ativa;
  function navegar(mudarFoco = false, destino = window.location.hash.slice(1)) {
    const rota = Object.hasOwn(rotas, destino) ? destino : "visao-geral";
    if (ativa === rota) return;
    ativa = rota;
    main.innerHTML = rotas[rota]();
    const complementar = rota === "previsao";
    document.querySelector("#top-contexto").textContent = complementar ? "Previsão de varejo" : "Qualidade documental";
    document.querySelector("#top-status").textContent = complementar ? "Estudo complementar" : "Resultados provisórios";
    document.querySelector("#rodape-escopo").textContent = complementar ? "UCI Online Retail II · Estudo complementar" : "10 peças · Estudo documental pareado";
    document.querySelectorAll("[data-rota]").forEach(a => {
      if (a.dataset.rota === rota) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    if (mudarFoco) {
      main.focus({ preventScroll: true });
      window.scrollTo(0, 0);
    }
  }
  document.querySelector(".skip").addEventListener("click", evento => {
    evento.preventDefault();
    main.focus();
  });
  if (window.self !== window.top) {
    // Um iframe srcdoc pode resolver links de fragmento contra o documento do notebook.
    document.addEventListener("click", evento => {
      const link = evento.target.closest('a[href^="#"]');
      const destino = link?.getAttribute("href").slice(1);
      if (Object.hasOwn(rotas, destino)) {
        evento.preventDefault();
        navegar(true, destino);
      }
    });
  }
  window.addEventListener("hashchange", () => navegar(true));
  navegar();
})();

