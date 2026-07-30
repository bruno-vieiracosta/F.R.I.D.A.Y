# Identificadores e Tempo

A F.R.I.D.A.Y. utiliza `friday.shared.identifiers` e `friday.shared.clock` para padronizar identidade e acesso ao tempo.

## Identificadores Tipados

`TypedId` encapsula `uuid.UUID` e compara igualdade considerando o tipo concreto e o UUID.

Identificadores concretos iniciais:

- `EntityId`
- `CorrelationId`
- `EventId`

Exemplo:

```python
identifier = EntityId.new()
same_identifier = EntityId.from_string(str(identifier))
```

IDs de tipos diferentes nao sao iguais, mesmo quando encapsulam o mesmo UUID.

## Serializacao

IDs serializam como texto canonico de UUID:

```python
str(identifier)
identifier.to_dict()
```

## Geracao de IDs

`IdGenerator` define o contrato estrutural para geradores.

`UuidGenerator` gera UUID versao 4 e retorna o tipo de ID solicitado:

```python
generator = UuidGenerator()
entity_id = generator.new_id(EntityId)
```

Testes podem substituir o gerador por implementacoes deterministicas sem estado global.

## Relogio

`Clock` define o contrato:

```python
def now(self) -> datetime:
    ...
```

Implementacoes:

- `SystemClock`: consulta o relogio real e retorna UTC timezone-aware.
- `FixedClock`: retorna um instante controlado, permite `set(...)` e `advance(...)`.

## UTC Interno

Toda representacao interna de tempo deve usar UTC com timezone explicito. Datetimes naive sao rejeitados.

Utilitarios:

- `ensure_timezone_aware(...)`
- `normalize_to_utc(...)`
- `convert_utc_to_timezone(...)`
- `timezone_from_name(...)`
- `serialize_datetime(...)`

Conversoes de timezone sao sempre explicitas e usam `zoneinfo` da biblioteca padrao.

## Fora do Escopo

Esta PR nao implementa entidades, persistencia, eventos, auditoria, agendamentos, NTP, timezone automatico do sistema ou preferencias regionais.
