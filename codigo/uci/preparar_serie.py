"""Lê o histórico preservado, classifica cada linha e agrega o alvo semanal."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PACOTE = HERE.parents[1]
PROVENIENCIA = PACOTE / "dados/uci/proveniencia.json"
ABAS = ("Year 2009-2010", "Year 2010-2011")
COLUNAS = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate",
           "Price", "Customer ID", "Country"]
INICIO = pd.Timestamp("2009-12-07")
INICIO_TESTE = pd.Timestamp("2011-09-05")
FIM_EXCLUSIVO = pd.Timestamp("2011-12-05")
SOBREPOSICAO_INICIO = pd.Timestamp("2010-12-01")
SOBREPOSICAO_FIM = pd.Timestamp("2010-12-10")
SEMANAS = pd.date_range(INICIO, FIM_EXCLUSIVO, freq="W-MON", inclusive="left")
MOTIVOS = (
    "data_invalida", "semana_fronteira_fora_do_recorte",
    "aba_nao_escolhida_na_sobreposicao", "cancelamento", "fatura_nao_numerica",
    "quantidade_invalida_ou_nao_inteira", "quantidade_nao_positiva",
    "preco_invalido", "preco_nao_positivo", "codigo_produto_fora_do_padrao",
)


@dataclass
class Recorte:
    serie: pd.DataFrame
    exclusoes: pd.DataFrame
    resumo: dict
    sem_repeticoes: pd.DataFrame


def dados_originais(origem):
    p = json.loads(PROVENIENCIA.read_text(encoding="utf-8"))
    verificados = {}
    for item in p["arquivos_originais"]:
        arquivo = origem / item["arquivo"]
        with arquivo.open("rb") as entrada:
            digest = hashlib.file_digest(entrada, "sha256").hexdigest()
        if digest != item["sha256"] or arquivo.stat().st_size != item["bytes"]:
            raise ValueError(f"Arquivo histórico divergente da proveniência: {arquivo.name}")
        verificados[arquivo.name] = digest
    xlsx = origem / p["identificacao_arquivo_xlsx_no_zip"]
    partes, abas = [], []
    with pd.ExcelFile(xlsx, engine="openpyxl") as planilha:
        if tuple(planilha.sheet_names) != ABAS:
            raise ValueError("A estrutura das abas diverge do arquivo documentado.")
        for nome in ABAS:
            print(f"Lendo {nome}...", flush=True)
            parte = pd.read_excel(planilha, sheet_name=nome, usecols=COLUNAS)
            datas = pd.to_datetime(parte["InvoiceDate"], errors="coerce")
            abas.append({"aba": nome, "linhas": len(parte), "inicio": datas.min().isoformat(),
                         "fim": datas.max().isoformat()})
            parte["aba"] = nome
            parte["linha_excel"] = range(2, len(parte) + 2)
            partes.append(parte)
    metadados = {"fonte": p["fonte_oficial"], "licenca": p["licenca"],
                 "licenca_url": p["licenca_url"], "atribuicao": p["atribuicao"],
                 "sha256_originais": verificados, "abas": abas}
    return pd.concat(partes, ignore_index=True), metadados


def normalizar_codigo(coluna):
    return coluna.astype("string").str.strip().str.replace(r"\.0$", "", regex=True).str.upper()


def classificar(dados, aba_preferida):
    if aba_preferida not in ABAS:
        raise ValueError("A aba preferida deve ser uma das duas abas de origem.")
    data = pd.to_datetime(dados["InvoiceDate"], errors="coerce")
    semana = data.dt.normalize() - pd.to_timedelta(data.dt.weekday, unit="D")
    fatura = normalizar_codigo(dados["Invoice"])
    codigo = normalizar_codigo(dados["StockCode"])
    quantidade = pd.to_numeric(dados["Quantity"], errors="coerce")
    preco = pd.to_numeric(dados["Price"], errors="coerce")
    com_data = data.notna()
    janela = data.ge(INICIO) & data.lt(FIM_EXCLUSIVO)
    sobreposta = data.ge(SOBREPOSICAO_INICIO) & data.lt(SOBREPOSICAO_FIM)
    fora_aba = sobreposta & dados["aba"].ne(aba_preferida)
    qtd_invalida = ~np.isfinite(quantidade) | quantidade.mod(1).ne(0)
    condicoes = (
        ~com_data, ~janela, fora_aba,
        fatura.str.startswith("C", na=False),
        ~fatura.str.fullmatch(r"[0-9]+", na=False),
        qtd_invalida, quantidade.le(0),
        ~np.isfinite(preco), preco.le(0),
        ~codigo.str.fullmatch(r"[0-9]{5}[A-Z]{0,2}", na=False),
    )
    motivos = pd.Series(pd.NA, index=dados.index, dtype="string")
    for motivo, condicao in zip(MOTIVOS, condicoes, strict=True):
        motivos.loc[motivos.isna() & condicao.fillna(False)] = motivo
    return pd.DataFrame({"dia": data.dt.normalize(), "semana": semana, "quantidade": quantidade,
                         "bruto_conciliado": com_data & janela & ~fora_aba, "motivo": motivos})


def agregar(classificadas, elegiveis):
    brutas = classificadas.loc[classificadas["bruto_conciliado"]]
    usaveis = classificadas.loc[elegiveis]
    serie = pd.DataFrame({"semana": SEMANAS}).set_index("semana")
    serie["linhas_brutas"] = brutas.groupby("semana").size().reindex(SEMANAS, fill_value=0)
    serie["dias_com_registros_brutos"] = brutas.groupby("semana")["dia"].nunique().reindex(SEMANAS, fill_value=0)
    serie["linhas_elegiveis"] = usaveis.groupby("semana").size().reindex(SEMANAS, fill_value=0)
    serie["dias_com_registros_elegiveis"] = usaveis.groupby("semana")["dia"].nunique().reindex(SEMANAS, fill_value=0)
    # Ausência de grupo permanece nula. Zero só é usado nas contagens de cobertura.
    serie["unidades"] = usaveis.groupby("semana")["quantidade"].sum(min_count=1).reindex(SEMANAS).astype("Int64")
    serie["situacao"] = np.select(
        [serie["unidades"].notna(), serie["linhas_brutas"].gt(0)],
        ["observada", "sem_linha_elegivel"], default="sem_registro_bruto")
    return serie


def construir_recorte(dados, aba_preferida):
    classificadas = classificar(dados, aba_preferida)
    elegiveis = classificadas["motivo"].isna()
    aceitas = dados.loc[elegiveis]
    repetidas = aceitas.duplicated(subset=["aba", *COLUNAS], keep="first")
    sem_repeticoes = elegiveis.copy()
    sem_repeticoes.loc[repetidas[repetidas].index] = False
    excluidas = dados.loc[~elegiveis, ["aba", "linha_excel"]].copy()
    excluidas["motivo"] = classificadas.loc[~elegiveis, "motivo"]
    rep = dados.loc[repetidas[repetidas].index, ["aba", "linha_excel"]].copy()
    rep["motivo"] = pd.Series("repeticao_exata_na_mesma_aba_somente_sensibilidade",
                              index=rep.index, dtype="string")
    trilha = pd.concat([excluidas, rep], ignore_index=True).sort_values(["aba", "linha_excel"])
    contagens = classificadas["motivo"].value_counts().to_dict()
    resumo = {
        "aba_preferida_na_sobreposicao": aba_preferida, "total_bruto": len(dados),
        "exclusoes_criterio_principal": {m: int(contagens.get(m, 0)) for m in MOTIVOS},
        "linhas_elegiveis_com_repeticoes": int(elegiveis.sum()),
        "repeticoes_elegiveis_mesma_aba": int(repetidas.sum()),
        "linhas_elegiveis_sem_repeticoes": int(sem_repeticoes.sum()),
    }
    if sum(contagens.values()) + int(elegiveis.sum()) != len(dados):
        raise ValueError("A trilha de exclusões não reconcilia o total bruto.")
    return Recorte(agregar(classificadas, elegiveis), trilha, resumo, agregar(classificadas, sem_repeticoes))

