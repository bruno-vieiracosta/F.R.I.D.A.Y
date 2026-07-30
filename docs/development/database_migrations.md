# Migracoes de Banco de Dados

Esta documentacao define a infraestrutura oficial de migracoes da F.R.I.D.A.Y.

O projeto utiliza Alembic para versionar o schema do banco criado pela
infraestrutura SQLite + SQLAlchemy.

## Estrutura

Arquivos principais:

- `alembic.ini`: configuracao base do Alembic.
- `alembic/env.py`: integra Alembic com `ApplicationSettings`, Logger oficial e
  `SqlAlchemyEngineFactory`.
- `alembic/script.py.mako`: template oficial para novas revisoes.
- `alembic/versions/`: historico de revisoes.
- `friday.infrastructure.persistence.schema`: metadata oficial do banco.
- `friday.infrastructure.persistence.migrations`: helpers programaticos de
  upgrade e downgrade.

## Metadata Oficial

`schema_metadata` e a unica metadata oficial para versionamento do schema.

Nesta etapa ela contem apenas a tabela tecnica `application_metadata`, criada
pela revisao inicial `0001_initial_revision`.

Nenhuma tabela financeira ou entidade de dominio deve ser adicionada nesta PR.

## Upgrade

Para aplicar todas as migracoes:

```bash
alembic upgrade head
```

Tambem e possivel executar programaticamente:

```python
upgrade_database(settings, logger)
```

## Downgrade

Para reverter ate a base:

```bash
alembic downgrade base
```

Programaticamente:

```python
downgrade_database(settings, logger)
```

Ao reverter para `base`, a tabela administrativa do Alembic tambem e removida
quando estiver vazia, preservando o banco sem residuos de schema.

## Configuracao

O caminho do banco vem de `ApplicationSettings.database_path`.

`alembic/env.py` nao define caminho fixo e nao cria uma Engine isolada. A Engine
e criada pela `SqlAlchemyEngineFactory`, usando a mesma configuracao oficial da
aplicacao.

## Logging e Erros

Os helpers de migracao registram inicio, fim e falhas usando o Logger oficial.

Falhas do Alembic sao encapsuladas em `PersistenceError`, preservando a excecao
original em `cause`.

## Criacao de Revisoes Futuras

Novas revisoes devem ser criadas com:

```bash
alembic revision -m "descricao curta"
```

Boas praticas:

- manter uma responsabilidade por revisao;
- criar schema apenas por migracoes;
- nao executar SQL manual no bootstrap;
- nao criar tabelas de dominio fora das PRs planejadas;
- revisar `upgrade()` e `downgrade()` antes do merge.

## Limites

Esta etapa nao implementa:

- modelos ORM financeiros;
- repositorios concretos;
- auditoria;
- backup;
- cache;
- Event Sourcing;
- CQRS;
- interface desktop;
- IA;
- integracoes externas.
