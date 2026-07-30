# Infraestrutura de Banco de Dados

Esta documentacao define a fundacao oficial de persistencia concreta da
F.R.I.D.A.Y. para SQLite com SQLAlchemy.

Esta PR cria apenas a infraestrutura basica. Ela nao cria modelos ORM, tabelas,
migracoes, repositorios concretos, consultas SQL especializadas ou regras de
negocio.

## Organizacao

Os componentes ficam em `friday.infrastructure.persistence`:

- `configuration.py`: resolve a configuracao do banco a partir de
  `ApplicationSettings`.
- `engine.py`: cria e reutiliza a `Engine` SQLAlchemy.
- `session.py`: encapsula a fabrica de sessoes.
- `unit_of_work.py`: implementa a Unit of Work concreta.
- `database.py`: coordena a inicializacao da infraestrutura.

## Configuracao

O caminho do banco vem exclusivamente de `ApplicationSettings.database_path`.

A variavel `FRIDAY_DATABASE_PATH` pode alterar esse caminho por meio do sistema
oficial de configuracao. A Infrastructure nao le variaveis de ambiente
diretamente.

## Engine Factory

`SqlAlchemyEngineFactory` cria uma unica `Engine` reutilizavel para SQLite.

Antes de criar a Engine, a fabrica garante que o diretorio pai do banco exista.
Falhas de criacao ou configuracao sao encapsuladas em `InfrastructureError`.

## Session Factory

`SqlAlchemySessionFactory` encapsula `sessionmaker`.

Outras camadas nao devem criar sessoes diretamente. A sessao SQLAlchemy
permanece detalhe da Infrastructure.

## Unit of Work

`SqlAlchemyUnitOfWork` implementa o contrato `UnitOfWork` definido em
`friday.application.persistence`.

Ela suporta:

- `begin`;
- `commit`;
- `rollback`;
- `close`;
- uso como context manager.

Falhas transacionais sao encapsuladas em `PersistenceError`, preservando a
excecao original em `cause`.

## Database Infrastructure

`DatabaseInfrastructure` agrega:

- configuracao resolvida;
- Engine;
- Session Factory.

Ela tambem cria novas instancias de `SqlAlchemyUnitOfWork` quando necessario.

## Dependency Injection

`build_container()` registra:

- `DatabaseConfiguration` como instancia;
- `SqlAlchemyEngineFactory` como singleton;
- `Engine` como singleton;
- `SqlAlchemySessionFactory` como singleton;
- `UnitOfWork` como transient;
- `DatabaseInfrastructure` como singleton.

O registro e preguicoso: construir o container nao cria a Engine nem abre
sessoes. A infraestrutura e inicializada quando suas dependencias sao
resolvidas.

## Logging

A criacao da Engine e a inicializacao da infraestrutura utilizam o logger oficial
fornecido por `LoggerFactory`.

Nao existem loggers paralelos na Infrastructure.

## Responsabilidades Futuras

A PR #1.15 podera introduzir Alembic e migracoes sem alterar os contratos da
camada Application.

Implementacoes futuras de repositorios deverao usar os contratos oficiais em
`friday.application.persistence`.

## Limites

Esta etapa nao implementa:

- Alembic;
- migracoes;
- modelos ORM;
- tabelas;
- repositorios concretos;
- Specification concreta;
- auditoria;
- backup;
- criptografia;
- cache;
- regras de negocio;
- interface desktop;
- IA;
- integracoes externas.
