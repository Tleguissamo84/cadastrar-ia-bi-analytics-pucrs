"""Audita a lista fechada, o conteúdo agregado e os hashes da versão para revisão."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

PACOTE = Path(__file__).resolve().parents[1]
MANIFESTO = "MANIFESTO_SHA256.json"
ARQUIVOS = {
    ".gitignore", "README.md", "AUDITORIA_PUBLICACAO.md", "DIREITOS_E_ATRIBUICAO.md",
    "Painel_Publico.ipynb", "requirements.txt", "docs/.nojekyll", "docs/index.html",
    "painel/gerar.py", "painel/modelo.html", "painel/estilos.css", "painel/aplicacao.js",
    "codigo/documental/preparar_base.py", "codigo/documental/indicadores.py",
    "codigo/uci/preparar_serie.py", "codigo/uci/prever.py", "codigo/uci/executar.py",
    "codigo/uci/visualizar.py", "dados/documental.json", "dados/uci/proveniencia.json",
    "dados/uci/resumo.json", "dados/uci/serie_semanal.csv", "dados/uci/metricas_teste.csv",
    "dados/uci/previsoes_teste.csv", "dados/uci/serie_semanal.png",
    "dados/uci/observado_previsto.png", "dados/uci/erros_metodos.png",
    "testes/auditar.py", "testes/navegador.cjs",
}
SINAIS = {
    "caminho de máquina": r"(?<![\w])[A-Za-z]:[\\/]+[\w]|file:/[/]|/(?:Users|home|mnt)/[\w]",
    "chave privada": r"\x2d{5}BEGIN(?: [A-Z0-9]+)* PRIVATE KEY\x2d{5}",
    "credencial reconhecível": r"\b(?:gh[pousr]_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]{18,}|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "segredo inline": r"(?:password|senha|api[_-]?key|client[_-]?secret|token)\s*[:=]\s*[\"'][A-Za-z0-9_+=/-]{12,}[\"']",
    "endereço eletrônico": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
}
PROIBIDO_EM_DADOS = r'\bP(?:0[1-9]|10)\b|\bEV-[0-9a-f]{5,}\b|\.jpe?g\b|[\"\'](?:produto_id|fonte_localizador|fotos|inventario)[\"\']\s*:'


def exigir(condicao, msg):
    if not condicao:
        raise ValueError(msg)


def inventario():
    itens = set()
    for p in PACOTE.rglob("*"):
        rel = p.relative_to(PACOTE)
        if rel.parts[0] == ".git":
            continue
        exigir(not p.is_symlink() and not getattr(p, "is_junction", lambda: False)(),
               "Atalho ou vínculo inesperado no pacote.")
        if p.is_file():
            itens.add(rel.as_posix())
    return itens


def auditar_png(conteudo, nome):
    exigir(conteudo[:8] == b"\x89PNG\r\n\x1a\n", f"PNG inválido: {nome}")
    pos = 8
    while pos + 12 <= len(conteudo):
        n, tipo = struct.unpack_from(">I4s", conteudo, pos)
        exigir(tipo in {b"IHDR", b"IDAT", b"IEND", b"tEXt", b"pHYs"}, f"Metadado PNG inesperado: {nome}")
        if tipo == b"tEXt":
            texto = conteudo[pos + 8:pos + 8 + n]
            exigir(re.fullmatch(rb"Software\x00Matplotlib version[0-9. ,]*https://matplotlib\.org/", texto) is not None,
                   f"Metadado PNG inesperado: {nome}")
        pos += n + 12
        if tipo == b"IEND":
            exigir(pos == len(conteudo), f"Dados extras no PNG: {nome}")
            return
    raise ValueError(f"PNG incompleto: {nome}")


def auditar(escrever_manifesto=False):
    presentes = inventario()
    exigir(presentes - {MANIFESTO} == ARQUIVOS,
           f"Lista fechada divergente. Extras: {sorted(presentes - ARQUIVOS - {MANIFESTO})}. "
           f"Ausentes: {sorted(ARQUIVOS - presentes)}.")
    hashes = {}
    for nome in sorted(ARQUIVOS):
        conteudo = (PACOTE / nome).read_bytes()
        hashes[nome] = hashlib.sha256(conteudo).hexdigest()
        if nome.endswith(".png"):
            auditar_png(conteudo, nome)
            continue
        texto = conteudo.decode("utf-8-sig")
        for rotulo, padrao in SINAIS.items():
            exigir(re.search(padrao, texto, re.IGNORECASE) is None, f"Sinal de {rotulo} em {nome}.")
        if nome.startswith(("dados/", "docs/", "painel/")):
            exigir(not re.search(PROIBIDO_EM_DADOS, texto, re.IGNORECASE), f"Detalhe privado em {nome}.")
    sys.path.insert(0, str(PACOTE / "painel"))
    from gerar import documental, pagina, previsao
    d = documental()
    p = previsao()
    exigir((d["amostra_produtos"], d["atributos"], d["registros"]) == (10, 19, 380), "Grade agregada divergente.")
    exigir(sum(d["pendencias"]["acoes_humanas"].values()) == 19
           and d["cores"] == {"mantidas": 7, "corrigidas": 3}, "Contagens agregadas divergentes.")
    exigir(p["metricas"]["media_4"]["mae"] < p["metricas"]["ridge"]["mae"], "Métricas divergentes.")
    with (PACOTE / "dados/uci/serie_semanal.csv").open(encoding="utf-8", newline="") as entrada:
        serie = list(csv.DictReader(entrada, delimiter=";"))
    exigir(set(serie[0]) == {"semana", "linhas_brutas", "dias_com_registros_brutos", "linhas_elegiveis",
                             "dias_com_registros_elegiveis", "unidades", "situacao"}
           and len(serie) == 104 and sum(not r["unidades"] for r in serie) == 2,
           "Série semanal fora do contrato público.")
    exigir(pagina() == (PACOTE / "docs/index.html").read_text(encoding="utf-8"),
           "O HTML não corresponde ao gerador local.")
    notebook = json.loads((PACOTE / "Painel_Publico.ipynb").read_text(encoding="utf-8"))
    for celula in notebook["cells"]:
        if celula["cell_type"] == "code":
            exigir(celula["outputs"] == [] and celula["execution_count"] is None, "Notebook contém saídas.")
            compile("".join(celula["source"]), "<notebook>", "exec")
    caminho = PACOTE / MANIFESTO
    registro = {"algoritmo": "SHA-256", "arquivos": hashes}
    if escrever_manifesto:
        caminho.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
    exigir(json.loads(caminho.read_text(encoding="utf-8")) == registro, "Hashes do manifesto divergentes.")
    print(f"{len(hashes)} arquivos auditados, HTML reproduzível e manifesto íntegro.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atualizar-manifesto", action="store_true",
                        help="Regrava os hashes após a auditoria de uma alteração autorizada.")
    auditar(parser.parse_args().atualizar_manifesto)

