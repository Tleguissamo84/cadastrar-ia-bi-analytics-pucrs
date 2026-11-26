"""Monta o painel estático apenas com os agregados distribuíveis do pacote."""
import base64
import csv
from datetime import date
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACOTE = HERE.parent
DADOS = PACOTE / "dados"
UCI = DADOS / "uci"
ESTADOS = {"confirmado", "declarado", "ausente", "ilegivel", "conflitante",
           "pendente_validacao", "nao_avaliado", "nao_aplicavel"}
ORIGENS = {"fotografia", "etiqueta", "declaracao", "derivacao", "outro"}
BLOCOS = {"identificacao", "origem", "composicao", "conservacao", "forro"}
METODOS = ("ultima_observada", "media_4", "ridge")
FONTE = "https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii"


def exigir(condicao):
    if not condicao:
        raise ValueError("Entrada fora do contrato público de agregados.")


def ler_json(arquivo):
    return json.loads(arquivo.read_text(encoding="utf-8"))


def ler_csv(arquivo, colunas):
    with arquivo.open(encoding="utf-8-sig", newline="") as entrada:
        leitor = csv.DictReader(entrada, delimiter=";", strict=True)
        exigir(leitor.fieldnames == list(colunas))
        linhas = list(leitor)
    exigir(all(None not in linha and None not in linha.values() for linha in linhas))
    return linhas


def inteiro(v):
    return type(v) is int and v >= 0


def numerico(v):
    return type(v) in (int, float) and math.isfinite(v)


def contagens(mapa, permitidas, completo=False):
    chaves = set(mapa)
    exigir((chaves == permitidas if completo else chaves <= permitidas)
           and all(inteiro(v) for v in mapa.values()))


def documental():
    d = ler_json(DADOS / "documental.json")
    exigir(set(d) == {"atributos", "registros", "amostra_produtos", "estados", "origens",
                       "indicadores", "testes", "pendencias", "cores"})
    exigir(all(inteiro(d[k]) for k in ("atributos", "registros", "amostra_produtos")))
    exigir(d["registros"] == 2 * d["atributos"] * d["amostra_produtos"])
    for chave, enum in (("estados", ESTADOS), ("origens", ORIGENS)):
        exigir(set(d[chave]) == {"A", "B"})
        for mapa in d[chave].values():
            contagens(mapa, enum)
    exigir(sum(sum(v.values()) for v in d["estados"].values()) == d["registros"])
    contagens(d["cores"], {"mantidas", "corrigidas"}, completo=True)
    exigir(sum(d["cores"].values()) == d["amostra_produtos"])
    exigir(set(d["pendencias"]) == {"acoes_humanas", "limitacoes", "condicao_futura"})
    for mapa in d["pendencias"].values():
        contagens(mapa, {"A", "B", "A/B"}, completo=True)
    campos = {"indicador", "etapa", "bloco", "situacao", "percentual",
              "numerador", "denominador", "pendencias", "versao"}
    tipos = {"completude", "consistencia", "cobertura_testes", "rastreabilidade"}
    chaves = set()
    for r in d["indicadores"]:
        exigir(set(r) == campos and r["indicador"] in tipos and r["etapa"] in {"A", "B"}
               and r["bloco"] in BLOCOS | {"global"} and r["versao"] == "provisorio"
               and r["situacao"] in {"avaliavel", "parcial", "pendente", "nao_definido"}
               and inteiro(r["pendencias"]))
        exigir(all(r[k] is None or numerico(r[k]) and r[k] >= 0
                   for k in ("percentual", "numerador", "denominador")))
        exigir(r["percentual"] is None or r["percentual"] <= 100)
        chave = (r["indicador"], r["etapa"], r["bloco"])
        exigir(chave not in chaves)
        chaves.add(chave)
    esperadas = {(m, e, b) for m in tipos for e in "AB"
                 for b in BLOCOS | ({"global"} if m == "completude" else set())}
    exigir(chaves == esperadas)
    exigir(set(d["testes"]) == {"A", "B"})
    for recorte in d["testes"].values():
        exigir(set(recorte) == {"instancias", "avaliaveis", "comuns", "por_bloco"})
        exigir(all(inteiro(recorte[k]) for k in ("instancias", "avaliaveis", "comuns")))
        exigir(set(recorte["por_bloco"]) == BLOCOS)
        for c in recorte["por_bloco"].values():
            contagens(c, {"avaliavel", "nao_avaliavel", "nao_executado", "aplicabilidade_pendente"})
    return d


def previsao():
    p = ler_json(UCI / "resumo.json")
    exigir(set(p) == {"horizonte", "historico", "treino", "validacao", "teste", "lacunas",
                       "avaliadas_validacao", "alpha", "linhas_brutas", "linhas_elegiveis", "metricas"})
    for periodo in ("historico", "treino", "validacao", "teste"):
        d = p[periodo]
        exigir(set(d) == {"inicio_semana", "ultima_semana", "semanas_calendario"}
               and inteiro(d["semanas_calendario"]))
        exigir(date.fromisoformat(d["inicio_semana"]) <= date.fromisoformat(d["ultima_semana"]))
    exigir(all(date.fromisoformat(v).isoformat() == v for v in p["lacunas"]))
    exigir(all(inteiro(p[k]) for k in ("horizonte", "avaliadas_validacao", "linhas_brutas", "linhas_elegiveis"))
           and numerico(p["alpha"]) and p["alpha"] > 0)
    licenca = ler_json(UCI / "proveniencia.json")
    exigir(licenca["fonte_oficial"] == FONTE and licenca["licenca"] == "CC BY 4.0"
           and licenca["atribuicao"] ==
           "Chen, D. (2012). Online Retail II. UCI Machine Learning Repository. DOI: 10.24432/C5CG6D.")
    p.update(fonte=FONTE, licenca=licenca["licenca"], atribuicao=licenca["atribuicao"])
    metricas = ler_csv(UCI / "metricas_teste.csv", ("metodo", "mae", "rmse", "semanas_avaliadas"))
    exigir(tuple(r["metodo"] for r in metricas) == METODOS)
    exigir(set(p["metricas"]) == set(METODOS))
    for r in metricas:
        m = p["metricas"][r["metodo"]]
        exigir(set(m) == {"mae", "rmse", "semanas_avaliadas"} and inteiro(m["semanas_avaliadas"])
               and m["semanas_avaliadas"] == int(r["semanas_avaliadas"]))
        exigir(all(numerico(m[k]) and m[k] >= 0 and
                   math.isclose(m[k], float(r[k]), rel_tol=0, abs_tol=1e-9) for k in ("mae", "rmse")))
    semanas = ler_csv(UCI / "previsoes_teste.csv", ("semana", "observado", *METODOS, "avaliada_em_comum"))
    p["semanas_teste"] = []
    for r in semanas:
        exigir(date.fromisoformat(r["semana"]).isoformat() == r["semana"]
               and r["avaliada_em_comum"] in {"True", "False"})
        valores = {m: float(r[m]) if r[m] else None for m in ("observado", *METODOS)}
        exigir(all(v is None or numerico(v) for v in valores.values()))
        p["semanas_teste"].append({"semana": r["semana"], "avaliada": r["avaliada_em_comum"] == "True", **valores})
    exigir(len(semanas) == p["teste"]["semanas_calendario"]
           and {m["semanas_avaliadas"] for m in p["metricas"].values()}
           == {sum(r["avaliada"] for r in p["semanas_teste"])})
    p["figuras"] = {
        nome: "data:image/png;base64," + base64.b64encode((UCI / arq).read_bytes()).decode("ascii")
        for nome, arq in (("serie", "serie_semanal.png"), ("teste", "observado_previsto.png"),
                          ("erros", "erros_metodos.png"))
    }
    return p


def pagina():
    dados = json.dumps({**documental(), "previsao": previsao()}, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False).replace("<", r"\u003c")
    modelo = (HERE / "modelo.html").read_text(encoding="utf-8")
    return (modelo.replace("/* ESTILOS */", (HERE / "estilos.css").read_text(encoding="utf-8"))
            .replace("/* APLICACAO */", (HERE / "aplicacao.js").read_text(encoding="utf-8"))
            .replace("<!-- DADOS -->", dados))


if __name__ == "__main__":
    (PACOTE / "docs/index.html").write_text(pagina(), encoding="utf-8", newline="\n")
    print("Dashboard estático gerado.")

