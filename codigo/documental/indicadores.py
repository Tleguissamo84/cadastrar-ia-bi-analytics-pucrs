"""Executa diagnósticos reproduzíveis da base portátil da revisão de B."""
import argparse
import json
from collections import Counter
from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from preparar_base import (
    MATRIZ, PENDENCIAS, ROOT, chave, exigir, fontes_complementares, pasta_trabalho,
    gravar_csv, ler_csv, metadados_atributos, preparar,
)

BLOCOS = ("identificacao", "origem", "composicao", "conservacao")
FAMILIAS = ("lavagem", "alvejamento", "secagem", "passadoria", "limpeza_profissional")
ESCOPO = (*BLOCOS, "forro")
FOTOS_A = {"Fotografia real original sem alteração", "Derivado de fotografia real sem IA generativa"}
FOTO_PECA = "Fotografias reais das peças"
ETIQUETA = "Fotografias reais das etiquetas"
DECISAO_MANUAL = {"aprovada", "reprovada", "nao_avaliavel"}
ESTADOS_PENDENTES = {"pendente_validacao", "nao_avaliado"}
RESULTADOS = "resultados_preliminares.csv"
TESTES = "testes_consistencia_preliminares.csv"


def plano_atributos():
    dicionario = metadados_atributos()
    principal = {a: d["bloco_analitico"] for a, d in dicionario.items()
                 if d["participacao_completude"] == "principal"}
    familias = {familia: tuple(a for a in principal
                                if principal[a] == "conservacao"
                                and dicionario[a]["familia_conservacao"] == familia)
                for familia in FAMILIAS}
    exigir(len(principal) == 13 and sum(map(len, familias.values())) == 8
           and all(familias.values()) and set(principal.values()) == set(BLOCOS),
           "Dicionário incompatível com os quatro blocos e cinco famílias")
    por_bloco = {bloco: tuple(a for a, b in principal.items() if b == bloco) for bloco in BLOCOS}
    return {**por_bloco, "forro": ("composicao_forro",)}, familias


def fonte_admissivel(linha, tipo):
    atributo = linha["atributo_id"]
    if linha["etapa"] == "A":
        return atributo in {"categoria", "marca"} and tipo in FOTOS_A
    if atributo == "categoria":
        return tipo == FOTO_PECA
    if atributo == "marca":
        return tipo in {FOTO_PECA, ETIQUETA}
    return tipo == ETIQUETA


def fontes_admissiveis(linha):
    principal = {k: linha[k] for k in ("fonte_id", "fonte_tipo", "fonte_localizador", "fonte_sha256")}
    return [fonte for fonte in (principal, *fontes_complementares(linha))
            if fonte_admissivel(linha, fonte["fonte_tipo"])
            and all(fonte.get(k) for k in principal)]


def vetor_composicao(linha):
    vetor = json.loads(linha["valor_estruturado_json"] or "null", parse_float=Decimal)
    if not isinstance(vetor, list) or not vetor:
        return None
    if not all(isinstance(item, dict) and isinstance(item.get("fibra"), str)
               and item["fibra"].strip() and type(item.get("percentual")) in (int, Decimal)
               and Decimal(item["percentual"]).is_finite() for item in vetor):
        return None
    return [Decimal(item["percentual"]) for item in vetor]


def pontuar(linha):
    aplicabilidade, estado = linha["aplicabilidade_pareada"], linha["estado_dado"]
    if aplicabilidade == "nao":
        return "excluido", None
    if aplicabilidade == "pendente" or estado in ESTADOS_PENDENTES:
        return "pendente", None
    if estado in {"ausente", "ilegivel", "conflitante"} and not linha["valor"]:
        return "avaliavel", Fraction(0)
    if estado == "confirmado" and linha["valor"].strip() and fontes_admissiveis(linha):
        if linha["atributo_id"].startswith("composicao_") and vetor_composicao(linha) is None:
            return "pendente", None
        return "avaliavel", Fraction(1)
    return "pendente", None


def media(itens, peso_fixo=False):
    """Agrega sem omitir incerteza nem redistribuir pesos fixos."""
    ativos = [item for item in itens if item[0] != "excluido"]
    if not ativos:
        return "excluido", None
    conhecidos = [valor for _, valor in ativos if valor is not None]
    if peso_fixo and len(ativos) != len(itens):
        # Família ou bloco totalmente excluído exige decisão sobre o peso.
        return ("parcial" if conhecidos else "pendente"), None
    if len(conhecidos) != len(ativos):
        return ("parcial" if conhecidos or any(e == "parcial" for e, _ in ativos)
                else "pendente"), None
    return "avaliavel", sum(conhecidos) / len(conhecidos)


def percentual(valor):
    return "" if valor is None else format(float(valor * 100), ".6f")


def numero(valor):
    if isinstance(valor, Fraction) and valor.denominator != 1:
        return format(float(valor), ".12g")
    return str(valor)


def resultado(indicador, etapa, escopo, produto, situacao, valor, tratamento,
              numerador="", denominador="", pendencias=0):
    return dict(indicador=indicador, etapa=etapa, escopo=escopo, produto_id=produto,
                situacao="nao_definido" if situacao == "excluido" else situacao,
                percentual=percentual(valor), numerador=numero(numerador), denominador=numero(denominador),
                pendencias=pendencias, tratamento=tratamento, versao_resultado="provisorio")


def completude(indice, produtos, grupos, familias):
    saida = []
    for etapa in "AB":
        por_bloco = {}
        for bloco, atributos in grupos.items():
            pontos = []
            for produto in produtos:
                notas = {a: pontuar(indice[produto, etapa, a]) for a in atributos}
                if bloco == "conservacao":
                    recortes = [media([notas[a] for a in campos]) for campos in familias.values()]
                    estado, valor = media(recortes, peso_fixo=True)
                else:
                    estado, valor = media(list(notas.values()))
                pontos.append((estado, valor))
                saida.append(resultado("completude", etapa, bloco, produto, estado, valor,
                                       "produto_no_bloco", pendencias=sum(e == "pendente" for e, _ in notas.values())))
            por_bloco[bloco] = media(pontos)
            estado, valor = por_bloco[bloco]
            aptos = sum(v is not None for _, v in pontos)
            ativos = sum(e != "excluido" for e, _ in pontos)
            saida.append(resultado("completude", etapa, bloco, "", estado, valor, "media_dos_produtos",
                                   sum(v for _, v in pontos if v is not None) if valor is not None else "",
                                   ativos if valor is not None else "", ativos - aptos))
        estado, valor = media([por_bloco[b] for b in BLOCOS], peso_fixo=True)
        saida.append(resultado("completude", etapa, "global", "", estado, valor,
                               "media_dos_quatro_blocos", pendencias=sum(
                                   por_bloco[b][1] is None for b in BLOCOS)))
    return saida


def derivacao_coerente(linha, pais):
    if not (linha["estado_dado"] == pais["estado_dado"] == "confirmado"
            and linha["valor"].strip() and pais["valor"].strip()):
        return None
    dados = json.loads(linha["valor_estruturado_json"] or "{}")
    origem = "Nacional" if pais["valor"].casefold().strip() == "brasil" else "Importado"
    return (isinstance(dados, dict) and linha["valor"] == origem
            and linha["origem_informacao"] == "derivacao_pais_fabricacao"
            and dados.get("registro_pais") == pais["registro_id"]
            and dados.get("pais_base") == pais["valor"]
            and dados.get("referencia_classificacao") == "Brasil"
            and dados.get("regra") == "Brasil => Nacional; outro país => Importado")


def cadeia_documental(linha, indice):
    campos = ("fonte_id", "fonte_localizador", "fonte_trecho", "validacao_responsavel",
              "validacao_data", "metodo_validacao", "fonte_sha256")
    if not (linha["estado_dado"] == "confirmado" and all(linha[k].strip() for k in campos)
            and fonte_admissivel(linha, linha["fonte_tipo"])):
        return False
    if linha["atributo_id"] != "origem_condicao":
        return True
    pais = indice[linha["produto_id"], linha["etapa"], "pais_fabricacao"]
    return derivacao_coerente(linha, pais) is True and cadeia_documental(pais, indice)


def rastreabilidade(indice, produtos, grupos):
    saida = []
    for etapa in "AB":
        for bloco, atributos in grupos.items():
            if bloco == "origem":
                atributos = (*atributos, "origem_condicao")
            for produto in (*produtos, ""):
                linhas = [indice[p, etapa, a] for p in (produtos if not produto else [produto])
                          for a in atributos if indice[p, etapa, a]["aplicabilidade_pareada"] != "nao"]
                apresentadas = [linha for linha in linhas if linha["valor"].strip()]
                v = len(apresentadas)
                l = sum(cadeia_documental(linha, indice) for linha in apresentadas)
                pendentes = sum(
                    linha["aplicabilidade_pareada"] == "pendente"
                    or linha["estado_dado"] in ESTADOS_PENDENTES
                    or (linha["estado_dado"] == "declarado" and bool(linha["valor"]))
                    for linha in linhas)
                if v:
                    estado = "parcial" if pendentes else "avaliavel"
                else:
                    estado = "pendente" if pendentes else "nao_definido"
                saida.append(resultado("rastreabilidade", etapa, bloco, produto, estado,
                                       Fraction(l, v) if v else None, "cadeia_documental_preliminar",
                                       l, v, pendentes))
    return saida


def executar_regra(regra, linha, indice):
    estado = linha["estado_dado"]
    if estado != "confirmado" or not linha["valor"].strip():
        return "nao_avaliavel", "Valor documental confirmado indisponível."
    if regra == "soma_componente":
        percentuais = vetor_composicao(linha)
        if percentuais is None:
            return "nao_avaliavel", "Vetor de composição insuficiente."
        soma = sum(percentuais)
        ok = soma == 100 and all(0 <= p <= 100 for p in percentuais)
        return ("aprovada" if ok else "reprovada"), f"Soma exata do componente: {soma}%. Faixa por fibra: 0 a 100."
    if regra == "pais_origem":
        pais = indice[linha["produto_id"], linha["etapa"], "pais_fabricacao"]
        coerente = derivacao_coerente(linha, pais)
        if coerente is None:
            return "nao_avaliavel", "País de fabricação ou origem documental indisponível."
        return ("aprovada" if coerente else "reprovada"), "Correspondência com país, registro e regra Brasil."
    return ("aprovada" if fontes_admissiveis(linha) else "reprovada"), "Tipo e vínculo de fonte permitidos na etapa."


def testes_consistencia(indice, grupos, manuais, data_execucao):
    blocos = {a: b for b, atributos in grupos.items() for a in atributos}
    blocos["origem_condicao"] = "origem"
    testes = []
    usados = set()
    for (produto, etapa, atributo), linha in indice.items():
        if atributo not in blocos:
            continue
        bloco = blocos[atributo]
        regras = ["dominio_significado", "concordancia_fontes", "fonte_permitida"]
        if bloco in {"composicao", "forro"}:
            regras.append("soma_componente")
        if atributo == "origem_condicao":
            regras.append("pais_origem")
        if bloco == "conservacao" and etapa == "B":
            regras.append("fidelidade_cuidados")
        fontes = fontes_admissiveis(linha)
        admissiveis = {fonte["fonte_localizador"] for fonte in fontes}
        for regra in regras:
            teste_id = f"{linha['registro_id']}__{regra}"
            man = manuais.get(teste_id)
            aplicabilidade = linha["aplicabilidade_pareada"]
            resp, data, resultado_teste = "", "", ""
            localizadores = sorted(admissiveis)
            if aplicabilidade != "sim":
                execucao = "nao_executado"
                motivo = "Aplicabilidade pendente." if aplicabilidade == "pendente" else "Exclusão pareada."
            elif linha["estado_dado"] in ESTADOS_PENDENTES:
                execucao = "nao_executado"
                motivo = "Decisão documental pendente."
            elif regra in {"soma_componente", "pais_origem", "fonte_permitida"}:
                execucao = "automatico_preliminar"
                resultado_teste, motivo = executar_regra(regra, linha, indice)
                resp = "Pipeline de indicadores (checagem automática)"
                data = data_execucao
            elif regra == "concordancia_fontes" and len({f["fonte_sha256"] for f in fontes}) < 2:
                execucao = "checagem_de_criterio"
                resultado_teste, motivo = "nao_avaliavel", "Menos de duas fontes admissíveis com hashes distintos."
                resp = "Pipeline de indicadores (checagem automática)"
                data = data_execucao
            elif man:
                usados.add(teste_id)
                resp, data = man["responsavel"], man["data"]
                localizadores = json.loads(man["fontes_json"])
                exigir(isinstance(localizadores, list) and set(localizadores) <= admissiveis
                       and (man["resultado"] == "nao_avaliavel" or bool(localizadores)),
                       f"Fontes fora do registro ou insuficientes: {teste_id}")
                if regra == "concordancia_fontes" and man["resultado"] != "nao_avaliavel":
                    exigir(len({f["fonte_sha256"] for f in fontes
                                if f["fonte_localizador"] in localizadores}) >= 2,
                           f"Concordância exige duas fontes de conteúdo distinto: {teste_id}")
                execucao, resultado_teste, motivo = "registro_informado", man["resultado"], man["justificativa"]
            else:
                execucao = "nao_executado"
                motivo = "Requer julgamento documental registrado."
            testes.append(dict(teste_id=teste_id, produto_id=produto, etapa=etapa, bloco_analitico=bloco,
                               regra_id=regra, atributo_id=atributo, componente=linha["componente"],
                               aplicabilidade_teste=aplicabilidade, execucao=execucao,
                               avaliabilidade=("avaliavel" if resultado_teste in {"aprovada", "reprovada"}
                                               else "nao_avaliavel" if resultado_teste else "nao_executado"),
                               resultado=resultado_teste, fontes_json=json.dumps(localizadores, ensure_ascii=False),
                               justificativa=motivo, responsavel=resp, data=data,
                               versao_protocolo=linha["versao_protocolo"], avaliavel_em_ambas="nao",
                               versao_resultado="provisorio"))
    exigir(set(manuais) == usados, f"Decisões manuais não utilizáveis: {sorted(set(manuais) - usados)}")
    pares = Counter((t["produto_id"], t["atributo_id"], t["regra_id"])
                    for t in testes if t["avaliabilidade"] == "avaliavel")
    for teste in testes:
        if pares[teste["produto_id"], teste["atributo_id"], teste["regra_id"]] == 2:
            teste["avaliavel_em_ambas"] = "sim"
    return testes


def consistencia(testes, produtos):
    saida = []
    for etapa in "AB":
        for bloco in ESCOPO:
            for produto in (*produtos, ""):
                grupo = [t for t in testes if t["etapa"] == etapa and t["bloco_analitico"] == bloco
                         and (not produto or t["produto_id"] == produto)]
                previstos = [t for t in grupo if t["aplicabilidade_teste"] == "sim"]
                t = len(previstos)
                e = sum(teste["avaliabilidade"] == "avaliavel" for teste in previstos)
                a = sum(teste["resultado"] == "aprovada" for teste in previstos)
                pend_app = sum(teste["aplicabilidade_teste"] == "pendente" for teste in grupo)
                pend_exec = sum(teste["execucao"] == "nao_executado" for teste in previstos)
                pendencias = pend_app + pend_exec
                estado_k = ("parcial" if pendencias else "avaliavel") if e else (
                    "pendente" if pendencias else "nao_definido")
                if pend_app:
                    estado_cobertura, cobertura = ("parcial" if e else "pendente"), None
                elif t:
                    estado_cobertura = "parcial" if pend_exec else "avaliavel"
                    cobertura = Fraction(e, t)
                else:
                    estado_cobertura, cobertura = "nao_definido", None
                saida.extend((
                    resultado("consistencia", etapa, bloco, produto, estado_k, Fraction(a, e) if e else None,
                              "testes_avaliaveis_do_catalogo_preliminar", a, e, pendencias),
                    resultado("cobertura_testes", etapa, bloco, produto, estado_cobertura, cobertura,
                              "testes_avaliaveis_sobre_previstos_aplicaveis",
                              e, t if not pend_app else "", pendencias),
                ))
    return saida


def carregar_manuais(caminho):
    if caminho is None:
        return {}
    caminho = caminho.resolve()
    exigir(caminho.is_relative_to(ROOT), "O CSV de decisões deve estar dentro do projeto")
    linhas = ler_csv(caminho)
    resultado = {}
    campos = ("teste_id", "resultado", "responsavel", "data", "justificativa", "fontes_json")
    for linha in linhas:
        exigir(all(linha.get(k, "").strip() for k in campos), "Registro manual incompleto")
        exigir(linha["resultado"] in DECISAO_MANUAL and linha["teste_id"] not in resultado,
               "Resultado manual inválido ou duplicado")
        date.fromisoformat(linha["data"])
        resultado[linha["teste_id"]] = linha
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--testes-manuais", type=Path, help="CSV opcional com decisões já documentadas")
    parser.add_argument("--data-execucao", type=date.fromisoformat, default=date.today(),
                        help="Data técnica no formato AAAA-MM-DD; padrão: data local")
    args = parser.parse_args()
    destino = pasta_trabalho()
    linhas = ler_csv(destino / MATRIZ)
    esperadas, pendencias, _, _ = preparar()
    exigir(linhas == esperadas and ler_csv(destino / PENDENCIAS) == pendencias,
           "A cópia portátil difere da transformação verificada; execute preparar_base.py")
    indice = {chave(linha): linha for linha in linhas}
    produtos = sorted({linha["produto_id"] for linha in linhas})
    grupos, familias = plano_atributos()
    testes = testes_consistencia(indice, grupos, carregar_manuais(args.testes_manuais),
                                 args.data_execucao.isoformat())
    resultados = (completude(indice, produtos, grupos, familias)
                  + consistencia(testes, produtos)
                  + rastreabilidade(indice, produtos, grupos))
    gravar_csv(destino / TESTES, testes)
    gravar_csv(destino / RESULTADOS, resultados)
    humanos = [linha for linha in pendencias if linha["depende_estudante"] == "sim"]
    print(f"Saídas provisórias: {len(resultados)} recortes, {len(testes)} testes, "
          f"{len(humanos)} entradas que dependem de decisão ou confirmação do estudante.")


if __name__ == "__main__":
    main()

