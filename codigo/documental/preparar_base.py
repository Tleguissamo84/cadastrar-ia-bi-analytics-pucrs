"""Gera a cópia portátil e verifica suas fontes contra a revisão de B."""
import csv
import hashlib
import json
import os
from collections import Counter
from pathlib import Path, PurePosixPath, PureWindowsPath
from tempfile import NamedTemporaryFile

HERE = Path(__file__).resolve().parent
PACOTE = HERE.parents[1]
ROOT = Path(os.environ["CADASTRAR_PROJETO_PRIVADO"]).resolve()
FASE2 = Path("05_Desenvolvimento/FASE_2")
REVISAO = FASE2 / "Revisao_Etapa_B_2026-11-23"
ETAPA_A = FASE2 / "Reconstrucao_Etapa_A_2026-11-23"
MATRIZ = "matriz_atributos_AB.csv"
PENDENCIAS = "pendencias_revisao_B.csv"
MASCARA = ETAPA_A / "mascara_pareada_utilizada.csv"
PREFIXO_LEGADO = os.environ.get("CADASTRAR_PREFIXO_LEGADO")
RAIZ_ANTIGA = PureWindowsPath(PREFIXO_LEGADO) if PREFIXO_LEGADO else None
COLUNAS_MUDAVEIS = {
    "base_resolucao_localizadores", "fonte_localizador",
    "fontes_complementares_json", "mascara_pareada_fonte",
}


def exigir(condicao, mensagem):
    if not condicao:
        raise ValueError(mensagem)


def ler_csv(caminho):
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";", strict=True)
        campos = leitor.fieldnames or []
        linhas = list(leitor)
    exigir(campos and len(campos) == len(set(campos)), f"Cabeçalho inválido: {caminho}")
    exigir(all(None not in linha and None not in linha.values() for linha in linhas),
           f"Linha CSV irregular: {caminho}")
    return linhas


def gravar(destino, escrever, encoding):
    """Substitui somente a saída gerada, depois de concluída a escrita."""
    with NamedTemporaryFile(mode="w", encoding=encoding, newline="", dir=destino.parent,
                            delete=False) as temporario:
        caminho = Path(temporario.name)
        try:
            escrever(temporario)
            temporario.close()
            os.replace(caminho, destino)
        finally:
            temporario.close()
            caminho.unlink(missing_ok=True)


def gravar_csv(destino, linhas):
    exigir(linhas, f"Saída sem registros: {destino.name}")

    def escrever(arquivo):
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]), delimiter=";",
                                  quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        escritor.writeheader()
        escritor.writerows(linhas)

    gravar(destino, escrever, "utf-8-sig")


def gravar_json(destino, dados):
    gravar(destino, lambda arquivo: json.dump(dados, arquivo, ensure_ascii=False, indent=2),
           "utf-8")


def sha256(caminho):
    with caminho.open("rb") as arquivo:
        return hashlib.file_digest(arquivo, "sha256").hexdigest()


def arquivo_local(localizador):
    caminho = PurePosixPath(localizador)
    windows = PureWindowsPath(localizador)
    exigir(not (caminho.is_absolute() or windows.anchor or "\\" in localizador
                or ".." in caminho.parts), f"Localizador fora do padrão: {localizador}")
    destino = (ROOT / caminho).resolve()
    exigir(destino.is_relative_to(ROOT) and destino.is_file(),
           f"Arquivo ausente ou fora do projeto: {localizador}")
    return destino


def tornar_portatil(localizador, base):
    if not localizador:
        return ""
    caminho = PureWindowsPath(localizador)
    if caminho.anchor:
        exigir(RAIZ_ANTIGA is not None and caminho.is_relative_to(RAIZ_ANTIGA),
               "Configure CADASTRAR_PREFIXO_LEGADO com a raiz histórica privada.")
        relativo = PurePosixPath(*caminho.relative_to(RAIZ_ANTIGA).parts).as_posix()
    else:
        destino = (base / Path(*caminho.parts)).resolve()
        exigir(destino.is_relative_to(ROOT), f"Referência fora do projeto: {localizador}")
        relativo = destino.relative_to(ROOT).as_posix()
    arquivo_local(relativo)
    return relativo


def chave(linha):
    return linha["produto_id"], linha["etapa"], linha["atributo_id"]


def fontes_complementares(linha):
    fontes = json.loads(linha["fontes_complementares_json"] or "[]")
    exigir(isinstance(fontes, list), f"Fontes complementares inválidas: {linha['registro_id']}")
    return fontes


def metadados_atributos():
    return {
        linha["campo"]: linha
        for linha in ler_csv(ROOT / FASE2 / "Base_Analitica/dicionario_dados.csv")
        if linha["tipo_registro"] == "atributo"
    }


def verificar_estrutura(linhas):
    produtos = {f"P{n:02d}" for n in range(1, 11)}
    atributos = set(metadados_atributos())
    esperadas = {(p, e, a) for p in produtos for e in "AB" for a in atributos}
    chaves = Counter(map(chave, linhas))
    exigir(len(atributos) == 19 and len(linhas) == 380
           and len(chaves) == 380 and chaves.keys() == esperadas, "Matriz fora da grade A/B")
    exigir(all(linha["registro_id"] == "_".join(chave(linha)) for linha in linhas),
           "Identificador de registro divergente da chave")
    indice = {chave(linha): linha for linha in linhas}
    mascara = ler_csv(ROOT / MASCARA)
    exigir(len(mascara) == 190
           and {(m["produto_id"], m["atributo_id"]) for m in mascara}
           == {(p, a) for p in produtos for a in atributos}, "Máscara incompleta ou duplicada")
    for linha in mascara:
        p, a = linha["produto_id"], linha["atributo_id"]
        vigente_a = indice[p, "A", a]["aplicabilidade_pareada"]
        vigente_b = indice[p, "B", a]["aplicabilidade_pareada"]
        exigir(vigente_a == vigente_b == linha["aplicabilidade_A_proposta"]
               == linha["aplicabilidade_B_proposta"] and vigente_a in {"sim", "nao", "pendente"},
               f"Aplicabilidade divergente: {p}/{a}")


def preparar():
    origem = ROOT / REVISAO / MATRIZ
    integridade = json.loads((origem.parent / "verificacao_integridade.json").read_text(encoding="utf-8-sig"))
    hash_origem = sha256(origem)
    exigir(hash_origem == integridade["sha256_matriz_nova"], "Hash da matriz histórica divergente")
    originais = ler_csv(origem)
    verificar_estrutura(originais)
    trilha, linhas, referencias, hashes = [], [], Counter(), {}

    def registrar(arquivo, registro, campo, anterior, atual, esperado=""):
        if anterior != atual:
            trilha.append(dict(arquivo=arquivo, registro=registro, campo=campo,
                               anterior=anterior, atual=atual, sha256_referencia=esperado))

    def verificar_hash(localizador, esperado, grupo):
        exigir(len(esperado) == 64, f"SHA-256 ausente ou inválido: {localizador}")
        if localizador not in hashes:
            hashes[localizador] = sha256(arquivo_local(localizador))
        exigir(hashes[localizador] == esperado.lower(), f"SHA-256 divergente: {localizador}")
        referencias[grupo] += 1

    for anterior in originais:
        linha = anterior.copy()
        registro = linha["registro_id"]
        base = origem.parent / linha["base_resolucao_localizadores"]

        def atualizar(campo, anterior, esperado, grupo):
            relativo = tornar_portatil(anterior, base)
            if relativo:
                verificar_hash(relativo, esperado, grupo)
                registrar(MATRIZ, registro, campo, anterior, relativo, esperado)
            return relativo

        linha["fonte_localizador"] = atualizar(
            "fonte_localizador", linha["fonte_localizador"], linha["fonte_sha256"], "principal")
        linha["mascara_pareada_fonte"] = atualizar(
            "mascara_pareada_fonte", linha["mascara_pareada_fonte"],
            linha["mascara_pareada_sha256"], "mascara")
        exigir(linha["mascara_pareada_fonte"] == MASCARA.as_posix(),
               f"Referência inesperada à máscara: {registro}")
        complementares = fontes_complementares(linha)
        for i, fonte in enumerate(complementares):
            fonte["fonte_localizador"] = atualizar(
                f"fontes_complementares_json[{i}].fonte_localizador", fonte["fonte_localizador"],
                fonte["fonte_sha256"], "complementar")
        if complementares:
            linha["fontes_complementares_json"] = json.dumps(complementares, ensure_ascii=False)
        registrar(MATRIZ, registro, "base_resolucao_localizadores",
                  linha["base_resolucao_localizadores"], ".")
        linha["base_resolucao_localizadores"] = "."
        exigir(all(linha[campo] == valor for campo, valor in anterior.items()
                   if campo not in COLUNAS_MUDAVEIS), f"Campo documental alterado: {registro}")
        for fonte_anterior, fonte_atual in zip(fontes_complementares(anterior), complementares, strict=True):
            exigir(all(fonte_atual[k] == v for k, v in fonte_anterior.items()
                       if k != "fonte_localizador"), f"Metadado complementar alterado: {registro}")
        linhas.append(linha)

    total_alvos_matriz = len(hashes)
    pendencias = ler_csv(ROOT / REVISAO / PENDENCIAS)
    catalogo = ler_csv(ROOT / REVISAO / "fontes_conferidas_B.csv")
    hashes_catalogo = {
        tornar_portatil(fonte["arquivo"], origem.parent): fonte["sha256_manifesto"]
        for fonte in catalogo
    }
    registro_execucao = json.loads(
        (origem.parent / "registro_execucao_B.json").read_text(encoding="utf-8-sig"))
    hashes_inventario = {
        PureWindowsPath(k).as_posix(): v for k, v in registro_execucao["baseline_sha256"].items()
    }
    alvos_pendencias = set()
    for numero, linha in enumerate(pendencias, start=2):
        antigo = linha["arquivo_a_conferir"]
        relativo = tornar_portatil(antigo, origem.parent)
        if relativo:
            esperado = hashes.get(relativo) or hashes_catalogo.get(relativo) or hashes_inventario.get(relativo, "")
            verificar_hash(relativo, esperado, "pendencias")
            alvos_pendencias.add(relativo)
            registrar(PENDENCIAS, f"linha {numero}", "arquivo_a_conferir", antigo, relativo, esperado)
            linha["arquivo_a_conferir"] = relativo

    verificacao = {
        "raiz_localizadores": ".",
        "matriz_historica": (REVISAO / MATRIZ).as_posix(),
        "sha256_matriz_historica": hash_origem,
        "registros": len(linhas),
        "registros_por_etapa": dict(Counter(linha["etapa"] for linha in linhas)),
        "produtos": sorted({linha["produto_id"] for linha in linhas}),
        "atributos": len({linha["atributo_id"] for linha in linhas}),
        "chaves_unicas": len(set(map(chave, linhas))),
        "aplicabilidade_pareada": dict(Counter(
            linha["aplicabilidade_pareada"] for linha in linhas if linha["etapa"] == "A")),
        "campos_documentais_e_metadados_de_fontes_preservados": True,
        "referencias_conferidas_por_sha256": dict(referencias),
        "arquivos_distintos_matriz": total_alvos_matriz,
        "arquivos_distintos_pendencias": len(alvos_pendencias),
        "alteracoes_registradas_por_campo": dict(Counter(item["campo"].split("[")[0] for item in trilha)),
        "entradas_dependentes_do_estudante": sum(linha["depende_estudante"] == "sim" for linha in pendencias),
    }
    return linhas, pendencias, trilha, verificacao


def pasta_trabalho():
    pasta = Path(os.environ["CADASTRAR_SAIDA_PRIVADA"]).resolve()
    exigir(not pasta.is_relative_to(PACOTE) and not pasta.is_relative_to(ROOT)
           and not ROOT.is_relative_to(pasta) and not PACOTE.is_relative_to(pasta),
           "Use uma pasta de trabalho separada do pacote e das fontes privadas.")
    return pasta


def main():
    destino = pasta_trabalho()
    linhas, pendencias, trilha, verificacao = preparar()
    destino.mkdir(exist_ok=False)
    gravar_csv(destino / MATRIZ, linhas)
    gravar_csv(destino / PENDENCIAS, pendencias)
    gravar_csv(destino / "alteracoes_localizadores.csv", trilha)
    exigir(ler_csv(destino / MATRIZ) == linhas and ler_csv(destino / PENDENCIAS) == pendencias,
           "Saída diferente após a releitura")
    verificacao["sha256_copia_portatil"] = sha256(destino / MATRIZ)
    gravar_json(destino / "verificacao_preparacao.json", verificacao)
    print(f"Preparação concluída: {len(linhas)} registros, {len(trilha)} alterações registradas.")


if __name__ == "__main__":
    main()

