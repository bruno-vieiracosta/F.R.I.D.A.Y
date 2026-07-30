# Integracao Continua

A F.R.I.D.A.Y. utiliza GitHub Actions como plataforma oficial de CI.

## Workflow

O workflow fica em `.github/workflows/ci.yml` e executa automaticamente em:

- `push`
- `pull_request`

## Ambiente

- Sistema operacional: `ubuntu-latest`
- Python: `3.11`
- Cache: dependencias de `pip` com base no `pyproject.toml`

## Sequencia de validacao

O pipeline executa as etapas abaixo em ordem. Cada etapa falha imediatamente quando encontra erro.

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m mypy friday
python -m pytest
python -m pytest --cov=friday
python -m build
```

## Build

O build valida o empacotamento usando o backend definido em `pyproject.toml`. A CI nao publica pacotes nem cria releases nesta etapa.

## Escopo

Esta infraestrutura automatiza apenas a validacao tecnica do projeto. Deploy, publicacao, Docker, hooks Git, pre-commit e analises de seguranca ficam fora desta PR.
