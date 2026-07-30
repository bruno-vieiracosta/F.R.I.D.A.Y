# Auditoria Tecnica

Esta documentacao define a infraestrutura oficial de auditoria tecnica da
F.R.I.D.A.Y.

A auditoria tecnica registra eventos internos relevantes da aplicacao para
diagnostico, suporte e observabilidade local. Ela nao registra eventos
financeiros, acoes de usuarios ou decisoes de negocio.

## Componentes

- `friday.infrastructure.audit.models`: enums e modelo imutavel do registro.
- `friday.infrastructure.audit.serializers`: serializacao JSON deterministica
  dos metadados.
- `friday.infrastructure.audit.repository`: persistencia usando a
  `SqlAlchemySessionFactory` oficial.
- `friday.infrastructure.audit.service`: ponto central para registrar auditoria.
- `friday.infrastructure.audit.events`: evento tecnico e handler para Event Bus.
- `alembic/versions/0002_technical_audit.py`: schema persistente da auditoria.

## Modelo

Cada registro tecnico contem:

- identificador tipado;
- timestamp UTC;
- categoria;
- origem;
- operacao;
- nivel;
- mensagem;
- metadados JSON.

Os metadados aceitam apenas valores compativeis com JSON, `datetime`, enums e
identificadores tipados oficiais. Objetos Python arbitrarios sao rejeitados.

## Fluxo de Registro

Uso direto:

```python
service.record(
    category=AuditCategory.INFRASTRUCTURE,
    origin="database",
    operation="initialize",
    level=AuditLevel.INFO,
    message="Database initialized",
)
```

Uso via Event Bus:

```python
event_bus.publish(
    TechnicalAuditEvent.create(
        clock=clock,
        id_generator=id_generator,
        category=AuditCategory.EVENT_BUS,
        origin="events",
        operation="publish",
        level=AuditLevel.INFO,
        message="Event published",
    )
)
```

O container registra o handler de auditoria no Event Bus. Falhas durante esse
handler sao registradas pelo Logger oficial e nao interrompem o fluxo do Event
Bus.

## Persistencia

A persistencia usa exclusivamente a infraestrutura oficial:

- Engine Factory;
- Session Factory;
- SQLite + SQLAlchemy;
- Alembic.

Nenhuma tabela e criada no bootstrap. Toda evolucao de schema ocorre por
migracoes.

## Logging

Logging e auditoria sao complementares:

- Logging registra diagnostico imediato.
- Auditoria registra historico tecnico persistente.

O servico de auditoria usa o Logger oficial para registrar sucesso e falhas.

## Boas Praticas

- registrar apenas eventos tecnicos;
- usar origem e operacao estaveis;
- manter mensagens curtas;
- evitar dados sensiveis nos metadados;
- preferir metadados pequenos e estruturados;
- criar novas tabelas apenas via Alembic.

## Limites

Esta etapa nao implementa:

- auditoria financeira;
- auditoria de usuario;
- dashboards;
- relatorios;
- monitoramento remoto;
- telemetria externa;
- backup automatico;
- criptografia.
