# F.R.I.D.A.Y.

Bootstrap inicial do projeto F.R.I.D.A.Y.

Esta etapa cria apenas a fundacao tecnica minima do repositorio: pacote Python instalavel, ponto de entrada executavel, configuracao inicial de empacotamento e testes basicos.

## Requisitos

- Python 3.11 ou superior

## Instalacao

```bash
pip install -e .
```

## Execucao

```bash
python -m friday
```

## Testes

```bash
pytest
```

## Qualidade de codigo

As ferramentas oficiais de desenvolvimento podem ser instaladas com:

```bash
pip install -e ".[dev]"
```

Validacao local:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy friday
python -m pytest
python -m pytest --cov=friday
python -m build
```

As convencoes estao documentadas em `docs/development/code_quality.md`.

As convencoes da suite de testes estao documentadas em `docs/development/testing.md`.

A integracao continua esta documentada em `docs/development/continuous_integration.md`.

A configuracao centralizada esta documentada em `docs/development/configuration.md`.

O logging estruturado esta documentado em `docs/development/logging.md`.

A hierarquia oficial de erros esta documentada em `docs/development/errors.md`.

Os tipos compartilhados fundamentais estao documentados em `docs/development/shared_types.md`.

Os tipos financeiros fundamentais estao documentados em `docs/development/financial_types.md`.

Identificadores tipados e tempo estao documentados em `docs/development/identifiers_and_time.md`.

O container de dependencias esta documentado em `docs/development/dependency_injection.md`.

O barramento de eventos internos esta documentado em `docs/development/event_bus.md`.

Os contratos oficiais de persistência estão documentados em `docs/development/persistence_contracts.md`.

## Estrutura

```text
friday/
  bootstrap/
  application/
  domain/
  infrastructure/
  desktop/
  ai/
  integrations/
  security/
  shared/
```

A finalidade de cada pacote esta documentada em `docs/architecture/package_structure.md`.

## Escopo atual

Esta versao nao implementa regras de negocio, interface grafica, persistencia, IA ou integracoes externas.
