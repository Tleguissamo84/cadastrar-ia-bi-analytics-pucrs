"""Gera as três figuras de BI a partir das saídas do estudo."""
import matplotlib
matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROTULOS = {
    "ultima_observada": "Última observada",
    "media_4": "Média de 4 semanas",
    "ridge": "Ridge",
}
CORES = {"observado": "#233b53", "ultima_observada": "#b45d28",
         "media_4": "#5b6fc1", "ridge": "#087f72"}
TRACOS = {"ultima_observada": "--", "media_4": ":", "ridge": "-."}


def estilo(titulo, subtitulo):
    fig, ax = plt.subplots(figsize=(10, 3.7), dpi=128)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.75, bottom=0.22)
    fig.text(0.11, 0.93, titulo, fontweight="bold", fontsize=15, color="#172c40")
    fig.text(0.11, 0.85, subtitulo, fontsize=9, color="#4b6173")
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#dce5eb")
    ax.tick_params(color="#b9c8d1", labelcolor="#344f64", labelsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#dce5eb")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda n, _: f"{n:,.0f}".replace(",", ".")))
    return fig, ax


def salvar(fig, destino):
    try:
        fig.savefig(destino, facecolor="white")
    finally:
        plt.close(fig)


def gerar_figuras(serie, teste, metricas, destino):
    inicio_teste = teste.index.min()
    fig, ax = estilo("Série histórica semanal", "Unidades registradas no recorte elegível · UCI Online Retail II")
    ax.axvspan(inicio_teste, serie.index.max(), color="#e4f2ef", label="Janela de teste")
    ax.plot(serie.index, serie["unidades"].astype(float), color=CORES["observado"], linewidth=1.65,
            label="Volume observado")
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    salvar(fig, destino / "serie_semanal.png")

    fig, ax = estilo("Observado e previsto no teste", "Previsões de uma semana à frente, produzidas em ordem cronológica")
    ax.plot(teste.index, teste["observado"], color=CORES["observado"], linewidth=2.3, marker="o",
            markersize=4, label="Observado")
    for metodo, rotulo in ROTULOS.items():
        ax.plot(teste.index, teste[metodo], color=CORES[metodo], label=rotulo,
                linestyle=TRACOS[metodo], linewidth=1.75, marker=".", markersize=4)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, ncols=4, loc="upper center", bbox_to_anchor=(0.5, -0.22), fontsize=8)
    salvar(fig, destino / "observado_previsto.png")

    fig, ax = estilo("Erros fora da amostra", "MAE e RMSE em unidades · valores menores indicam menor erro")
    fig.subplots_adjust(left=0.11, right=0.97, top=0.75, bottom=0.23)
    posicoes = list(range(len(ROTULOS)))
    ax.bar([x - 0.18 for x in posicoes], [metricas[m]["mae"] for m in ROTULOS],
           0.34, color="#087f72", label="MAE")
    ax.bar([x + 0.18 for x in posicoes], [metricas[m]["rmse"] for m in ROTULOS],
           0.34, color="#5976a3", hatch="//", label="RMSE")
    ax.set_xticks(posicoes, list(ROTULOS.values()))
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    ax.set_ylim(bottom=0, top=1.15 * max(r["rmse"] for r in metricas.values()))
    salvar(fig, destino / "erros_metodos.png")

