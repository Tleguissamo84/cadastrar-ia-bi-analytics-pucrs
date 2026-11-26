"""Reproduz dados derivados, avaliação, registro da execução e figuras."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory

import numpy as np
import openpyxl
import pandas as pd
import sklearn

from preparar_serie import ABAS, PACOTE, construir_recorte, dados_originais
from prever import ATRIBUTOS, METODOS, avaliar, construir_variaveis, prever_janela, selecionar_alpha, separar_calendario
from visualizar import gerar_figuras, matplotlib

def intervalo(indice):
    return {"inicio_semana": indice.min().date().isoformat(),
            "ultima_semana": indice.max().date().isoformat(), "semanas_calendario": len(indice)}


def listar_semanas(indice):
    return [s.date().isoformat() for s in indice]


def escrever_csv(tabela, arquivo, indice=True):
    tabela.to_csv(arquivo, index=indice, sep=";", date_format="%Y-%m-%d", float_format="%.10f",
                  encoding="utf-8", lineterminator="\n")


def trilha_alternativa(principal, alternativa):
    etapas = principal.merge(alternativa, on=["aba", "linha_excel"], how="outer",
                             suffixes=("_principal", "_aba_anterior"), validate="one_to_one")
    colunas = ["motivo_principal", "motivo_aba_anterior"]
    etapas[colunas] = etapas[colunas].fillna("incluida")
    return etapas.loc[etapas[colunas[0]].ne(etapas[colunas[1]])].sort_values(["aba", "linha_excel"])


def executar(data_execucao, entrada, resultados):
    entrada, resultados = entrada.resolve(), resultados.resolve()
    if (resultados.is_relative_to(PACOTE) or PACOTE.is_relative_to(resultados)
            or resultados.is_relative_to(entrada) or entrada.is_relative_to(resultados) or resultados.exists()):
        raise ValueError("Informe uma pasta de saída nova, separada do pacote e dos dados de entrada.")
    bruto, proveniencia = dados_originais(entrada)
    print("Aplicando regras de elegibilidade e sensibilidades...", flush=True)
    principal = construir_recorte(bruto, ABAS[1])
    alternativa = construir_recorte(bruto, ABAS[0])
    del bruto

    serie = principal.serie
    variaveis = construir_variaveis(serie["unidades"])
    inicial, validacao, teste = separar_calendario(variaveis)
    if (len(inicial), len(validacao), len(teste)) != (52, 39, 13):
        raise ValueError("A divisão temporal diverge do protocolo.")
    print("Ajustando alpha somente no desenvolvimento...", flush=True)
    alpha, escolhas = selecionar_alpha(variaveis, validacao)
    previsto_validacao = prever_janela(variaveis, validacao, alpha)
    previsto_teste = prever_janela(variaveis, teste, alpha)
    metricas_teste = avaliar(previsto_teste)
    metricas_validacao = avaliar(previsto_validacao)

    cenarios = {"principal": serie, "sem_repeticoes_exatas": principal.sem_repeticoes,
                "sobreposicao_com_aba_anterior": alternativa.serie}
    sensibilidade = {}
    for nome, cenario in cenarios.items():
        prev = prever_janela(construir_variaveis(cenario["unidades"]), teste, alpha)
        if not prev["avaliada_em_comum"].equals(previsto_teste["avaliada_em_comum"]):
            raise ValueError(f"O cenário {nome} mudou o conjunto de avaliação.")
        sensibilidade[nome] = {
            "semanas_com_volume_alterado": int(cenario["unidades"].fillna(-1).ne(serie["unidades"].fillna(-1)).sum()),
            "metricas_teste": avaliar(prev),
        }

    semanas_usadas = previsto_teste.index[previsto_teste["avaliada_em_comum"]]
    registro = {
        "data_execucao": data_execucao, "fonte": proveniencia, "alvo": "Unidades registradas no recorte elegível",
        "horizonte_semanas": 1, "inicio_da_semana": "segunda-feira",
        "limpeza_principal": principal.resumo, "limpeza_sobreposicao_alternativa": alternativa.resumo,
        "treino_inicial": intervalo(inicial), "validacao": intervalo(validacao), "teste": intervalo(teste),
        "periodo_historico": intervalo(serie.index),
        "semanas_sem_alvo": listar_semanas(serie.index[serie["unidades"].isna()]),
        "distribuicao_dias_com_registro_elegivel": {
            str(k): int(v) for k, v in serie["dias_com_registros_elegiveis"].value_counts().sort_index().items()
        },
        "semanas_fora_avaliacao_validacao": {
            s.date().isoformat(): r for s, r in previsto_validacao["motivo_fora_avaliacao_comum"].items() if r
        },
        "semanas_fora_avaliacao_teste": {
            s.date().isoformat(): r for s, r in previsto_teste["motivo_fora_avaliacao_comum"].items() if r
        },
        "semanas_avaliadas_teste": listar_semanas(semanas_usadas),
        "metodos": list(METODOS), "atributos_ridge": ATRIBUTOS, "alpha_ridge": alpha,
        "selecao_alpha": escolhas, "metricas_validacao": metricas_validacao,
        "metricas_teste": metricas_teste, "sensibilidade": sensibilidade,
        "versoes": {
            "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
            "openpyxl": openpyxl.__version__, "scikit-learn": sklearn.__version__,
            "matplotlib": matplotlib.__version__,
        },
    }
    resultados.mkdir()
    with TemporaryDirectory(prefix="gerando_", dir=resultados) as temp:
        destino = Path(temp)
        escrever_csv(serie, destino / "serie_semanal.csv")
        escrever_csv(previsto_validacao, destino / "previsoes_validacao.csv")
        escrever_csv(previsto_teste, destino / "previsoes_teste.csv")
        escrever_csv(principal.exclusoes, destino / "exclusoes_por_linha.csv", indice=False)
        escrever_csv(trilha_alternativa(principal.exclusoes, alternativa.exclusoes),
                     destino / "exclusoes_sobreposicao_sensibilidade.csv", indice=False)
        comparacao = pd.DataFrame({nome: s["unidades"] for nome, s in cenarios.items()})
        escrever_csv(comparacao, destino / "serie_sensibilidade.csv")
        metricas = pd.DataFrame.from_dict(metricas_teste, orient="index").rename_axis("metodo")
        escrever_csv(metricas, destino / "metricas_teste.csv")
        gerar_figuras(serie, previsto_teste, metricas_teste, destino)
        registro["sha256_saidas"] = {
            arq.name: hashlib.sha256(arq.read_bytes()).hexdigest() for arq in sorted(destino.iterdir())
        }
        (destino / "registro_execucao.json").write_text(
            json.dumps(registro, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        for arq in sorted(destino.iterdir()):
            arq.replace(resultados / arq.name)
    print(json.dumps({"alpha": alpha, "teste": metricas_teste, "lacunas": registro["semanas_sem_alvo"]},
                     ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-execucao", type=date.fromisoformat, default=date.today(),
                        help="Data civil da execução, em AAAA-MM-DD")
    parser.add_argument("--entrada", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    executar(args.data_execucao.isoformat(), args.entrada, args.saida)

