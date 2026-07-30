# Qualidade de Codigo

A F.R.I.D.A.Y. utiliza uma configuracao centralizada no `pyproject.toml` para lint, formatacao, organizacao de imports, tipagem estatica e testes.

## Ferramentas oficiais

- Ruff: lint, formatacao e organizacao de imports.
- MyPy: tipagem estatica do pacote `friday`.
- Pytest: execucao da suite de testes.

As ferramentas de qualidade ficam no extra de desenvolvimento:

```bash
python -m pip install -e ".[dev]"
```

## Comandos de validacao

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy friday
python -m pytest
python -m friday
```

Quando os executaveis estiverem disponiveis no `PATH`, os comandos equivalentes `ruff`, `mypy` e `pytest` tambem podem ser usados.

## Convencoes

- Versao alvo: Python 3.11.
- Largura maxima de linha: 88 caracteres.
- Imports organizados pelo Ruff com a regra `I`.
- Strings formatadas com aspas duplas pelo Ruff.
- Arquivos `__init__.py` podem reexportar nomes publicos sem falhar por `F401`.
- O pacote `friday` deve passar em MyPy com modo `strict`.
- Dependencias de runtime devem permanecer vazias enquanto nao forem justificadas por uma PR especifica.

## Escopo das regras

O Ruff valida apenas arquivos Python em `friday` e `tests`. Documentos de planejamento e artefatos gerados por ferramentas ficam fora do escopo de lint para manter a verificacao focada no codigo da aplicacao.
