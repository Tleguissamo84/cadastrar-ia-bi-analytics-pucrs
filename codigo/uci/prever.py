"""Treina e avalia previsões de uma semana sem acessar o futuro."""
import math

import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from preparar_serie import INICIO_TESTE

METODOS = ("ultima_observada", "media_4", "ridge")
ATRIBUTOS = ["lag_1", "lag_2", "media_4"]
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
SEMENTE_SEMANAS = 52
MINIMO_TREINO = 24


def construir_variaveis(serie):
    if (not isinstance(serie.index, pd.DatetimeIndex) or not serie.index.is_unique
            or not serie.index.is_monotonic_increasing
            or not serie.index.equals(pd.date_range(serie.index[0], periods=len(serie), freq="W-MON"))):
        raise ValueError("A série precisa conter uma posição para cada segunda-feira.")
    y = serie.astype(float)
    passado = y.shift(1)
    return pd.DataFrame({
        "observado": y,
        "ultima_observada": passado.ffill(),
        "semana_ultima_observada": y.index.to_series().where(y.notna()).shift(1).ffill(),
        "lag_1": passado,
        "lag_2": y.shift(2),
        "media_4": passado.rolling(4, min_periods=4).mean(),
    })


def prever_janela(variaveis, semanas, alpha):
    treino = variaveis.dropna(subset=["observado", *ATRIBUTOS])
    registros = []
    for semana in semanas:
        linha = variaveis.loc[[semana]]
        x = linha[ATRIBUTOS]
        anteriores = treino.loc[treino.index < semana]
        ridge = None
        if len(anteriores) >= MINIMO_TREINO and x.notna().all(axis=None):
            modelo = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
            modelo.fit(anteriores[ATRIBUTOS], anteriores["observado"])
            ridge = float(modelo.predict(x)[0])
        valores = linha.iloc[0]
        obs = valores["observado"]
        ultima_data = valores["semana_ultima_observada"]
        registro = {
            "semana": semana, "corte_exclusivo": semana,
            "observado": obs, "ultima_observada": valores["ultima_observada"],
            "semana_ultima_observada": ultima_data, "media_4": valores["media_4"],
            "ridge": ridge, "n_treino_ridge": len(anteriores),
            "ultima_semana_treino_ridge": anteriores.index.max() if ridge is not None else pd.NaT,
        }
        if pd.isna(obs):
            motivo = "sem_alvo_observado"
        elif pd.isna(valores["ultima_observada"]):
            motivo = "sem_semana_anterior_observada"
        elif pd.isna(valores["media_4"]):
            motivo = "sem_quatro_semanas_anteriores_consecutivas"
        elif ridge is None:
            motivo = "treino_ou_atributos_insuficientes"
        else:
            motivo = ""
        registro["motivo_fora_avaliacao_comum"] = motivo
        registro["avaliada_em_comum"] = not motivo
        registros.append(registro)
    return pd.DataFrame(registros).set_index("semana")


def avaliar(previsoes):
    comuns = previsoes.dropna(subset=["observado", *METODOS])
    if not comuns.index.equals(previsoes.index[previsoes["avaliada_em_comum"]]):
        raise ValueError("A marcação das semanas avaliadas não coincide com os dados disponíveis.")
    if comuns.empty:
        raise ValueError("Nenhuma semana é avaliável pelos três métodos.")
    resultado = {}
    for identificador in METODOS:
        erro = comuns[identificador] - comuns["observado"]
        resultado[identificador] = {
            "mae": float(erro.abs().mean()),
            "rmse": math.sqrt(float(erro.pow(2).mean())),
            "semanas_avaliadas": len(comuns),
        }
    return resultado


def separar_calendario(variaveis):
    desenvolvimento = variaveis.index[variaveis.index < INICIO_TESTE]
    teste = variaveis.index[variaveis.index >= INICIO_TESTE]
    return desenvolvimento[:SEMENTE_SEMANAS], desenvolvimento[SEMENTE_SEMANAS:], teste


def selecionar_alpha(variaveis, semanas_validacao):
    # A API de seleção recebe somente as origens do desenvolvimento.
    if len(semanas_validacao) == 0 or semanas_validacao.max() >= INICIO_TESTE:
        raise ValueError("A seleção de alpha exige origens anteriores ao teste.")
    resultados = []
    for alpha in ALPHAS:
        previstas = prever_janela(variaveis, semanas_validacao, alpha)
        resultados.append({"alpha": alpha, **avaliar(previstas)["ridge"]})
    melhor = min(resultados, key=lambda r: (r["mae"], -r["alpha"]))
    return melhor["alpha"], resultados

