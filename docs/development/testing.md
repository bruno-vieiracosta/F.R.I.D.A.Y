# Testes

A F.R.I.D.A.Y. utiliza Pytest como framework oficial de testes e pytest-cov para relatorios de cobertura.

## Estrutura da suite

```text
tests/
  architecture/
  integration/
  unit/
  fixtures/
  conftest.py
```

- `tests/unit`: testes rapidos, isolados e sem dependencias externas.
- `tests/integration`: testes de comportamento entre modulos, comandos ou configuracoes.
- `tests/architecture`: testes de estrutura fisica e fronteiras entre camadas.
- `tests/fixtures`: utilidades compartilhadas de teste.
- `tests/conftest.py`: fixtures globais da suite.

## Marcadores oficiais

- `unit`: testes unitarios.
- `integration`: testes de integracao.
- `architecture`: testes arquiteturais.
- `slow`: testes intencionalmente mais lentos.

Os marcadores sao registrados em `pyproject.toml` e executados com `--strict-markers`.

## Fixtures compartilhadas

- `temporary_directory`: diretorio temporario isolado por teste.
- `temporary_paths`: diretorios temporarios padrao para entrada, saida e cache.
- `fixed_clock`: relogio fixo para testes deterministas.
- `read_text_file`: leitura UTF-8 reutilizavel em testes.

## Cobertura

A cobertura e configurada em `pyproject.toml` com `source = ["friday"]` e `branch = true`. Esta PR nao define meta minima de cobertura.

```bash
python -m pytest --cov=friday
```

## Validacao local

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m mypy friday
python -m pytest
python -m pytest --cov=friday
python -m friday
```
