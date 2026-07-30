# Contratos de Persistencia

Esta documentacao define os contratos oficiais de persistencia da F.R.I.D.A.Y.

O objetivo desta etapa e permitir que a camada `application` dependa apenas de
abstracoes. A camada `infrastructure` implementara esses contratos em PRs
futuras, sem exigir alteracoes nas regras de negocio ou nos casos de uso.

## Organizacao

Os contratos ficam em `friday.application.persistence`:

- `repository.py`: contrato base de repositorio.
- `unit_of_work.py`: contrato de Unit of Work.
- `transaction.py`: contrato transacional minimo.
- `specifications.py`: contrato de especificacoes de consulta.
- `pagination.py`: requisicao de pagina e leitura paginada.

Nenhum contrato importa `infrastructure`, banco de dados, SQLAlchemy, SQLite ou
Alembic.

## Repository

`Repository[TEntity, TIdentifier]` define operacoes logicas de persistencia:

- `get_by_id`;
- `list`;
- `list_paginated`;
- `add`;
- `update`;
- `remove`;
- `exists`.

`TIdentifier` deve ser um identificador tipado derivado de `TypedId`. Nao usar
`str` como identificador persistente.

Exemplo conceitual:

```python
repository: Repository[Record, EntityId]
record = repository.get_by_id(record_id)
```

## Unit of Work

`UnitOfWork` representa o ciclo de vida transacional:

- `begin`;
- `commit`;
- `rollback`;
- `close`;
- suporte a context manager.

O contrato nao define conexao, sessao, engine, cursor ou qualquer detalhe de
banco de dados.

## Transaction

`Transaction` define a transacao minima:

- `is_active`;
- `commit`;
- `rollback`;
- `close`.

Nao ha niveis de isolamento, bloqueios, retry, concorrencia ou transacoes
distribuidas nesta etapa.

## Specification

`Specification[TEntity]` representa um criterio de consulta reutilizavel e
independente de SQL:

```python
class ActiveRecordSpecification:
    def is_satisfied_by(self, candidate: Record) -> bool:
        return candidate.active
```

O contrato prepara composicao futura, mas nao implementa operadores concretos,
query builder ou linguagem propria de consulta.

## Pagination

`PageRequest` representa a pagina solicitada. Ela e imutavel e valida `page` e
`page_size`.

Operacoes paginadas retornam obrigatoriamente `PagedResult`, definido em
`friday.shared.types`.

## Erros

Contratos e estruturas auxiliares utilizam apenas a hierarquia oficial de erros.
Falhas de persistencia devem usar `PersistenceError`.

Nao criar excecoes genericas ou especificas de tecnologia.

## Dependency Injection

Os contratos nao conhecem o container. Implementacoes futuras serao registradas
durante o bootstrap:

```python
container.register_instance(Repository, repository)
```

Casos de uso futuros devem receber repositorios, Unit of Work e demais
dependencias por construtor ou parametros explicitos.

## EventBus

Os contratos nao publicam eventos. Publicacao de eventos pode ocorrer em casos
de uso ou implementacoes futuras quando houver uma regra clara para isso.

## Responsabilidades

Application:

- define contratos;
- utiliza abstracoes;
- permanece independente de tecnologia.

Infrastructure futura:

- implementa contratos;
- gerencia conexoes, sessoes, SQL, migrations e detalhes concretos;
- traduz falhas concretas para erros oficiais.

## Limites

Esta PR nao implementa:

- SQLite;
- SQLAlchemy;
- Alembic;
- tabelas;
- entidades ORM;
- consultas SQL;
- repositórios concretos;
- Unit of Work concreta;
- cache;
- auditoria;
- backup;
- casos de uso;
- regras de negocio.

Esses itens pertencem as PRs futuras da Fase 1.
