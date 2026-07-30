# Event Bus Interno

Esta documentacao define o barramento oficial de eventos internos da F.R.I.D.A.Y.

O objetivo do EventBus e permitir comunicacao desacoplada entre componentes da
aplicacao dentro do mesmo processo, sem filas, mensageria distribuida,
paralelismo ou persistencia de eventos.

## Arquitetura

Os contratos ficam na camada `application`:

- `ApplicationEvent`: classe base imutavel para eventos internos.
- `EventMetadata`: cria `EventId` e timestamp UTC usando `IdGenerator` e `Clock`.
- `EventHandler`: protocolo tipado para handlers.
- `EventBus`: barramento sincrono em memoria.

O `bootstrap` registra o `EventBus` no container de dependencias. A camada
`application` nao depende do container.

## Eventos

Todo evento deve possuir:

- `EventId`;
- `occurred_at` timezone-aware e normalizado em UTC;
- `event_name`;
- serializacao simples por `to_dict()`.

Eventos concretos devem declarar seus atributos como campos tipados. Nao devem
usar payloads genericos baseados em `dict`.

Exemplo:

```python
from dataclasses import dataclass
from typing import ClassVar

from friday.application.events import ApplicationEvent


@dataclass(frozen=True, slots=True)
class ExampleEvent(ApplicationEvent):
    description: str

    event_name: ClassVar[str] = "example.event"
```

## Criacao

IDs e timestamps devem vir das abstracoes oficiais:

```python
metadata = ExampleEvent.new_metadata(clock, id_generator)
event = ExampleEvent(
    event_id=metadata.event_id,
    occurred_at=metadata.occurred_at,
    description="example",
)
```

Nao usar `datetime.now()` nem `datetime.utcnow()` ao criar eventos.

## Handlers

Handlers implementam o protocolo `EventHandler` por tipagem estrutural:

```python
class ExampleHandler:
    def handle(self, event: ExampleEvent) -> None:
        ...
```

Handlers recebem exatamente um evento e nao retornam valores.

## Registro

O registro e explicito:

```python
event_bus.subscribe(ExampleEvent, ExampleHandler())
```

Mais de um handler pode ser registrado para o mesmo evento. A ordem de execucao
preserva a ordem de registro. Registrar o mesmo handler duas vezes para o mesmo
evento e considerado erro de configuracao.

Handlers podem ser removidos explicitamente:

```python
event_bus.unsubscribe(ExampleEvent, handler)
```

## Publicacao

A publicacao e sincrona, em memoria e single-process:

```python
event_bus.publish(event)
```

Eventos sem handlers sao aceitos normalmente. Nao ha filas, threads, retry,
dead letter queue, replay ou persistencia.

## Falhas

Quando um handler falha, o EventBus:

1. encapsula a falha em `ApplicationError`;
2. registra a falha usando o logger recebido pelo barramento;
3. continua executando os handlers restantes na ordem registrada;
4. ao final, levanta um `ApplicationError` agregado se houve qualquer falha.

Nenhuma excecao e perdida silenciosamente.

## Dependency Injection

`build_container()` registra o `EventBus` como singleton:

```python
container = build_container(settings)
event_bus = container.resolve(EventBus)
```

Em testes, o registro pode ser substituido explicitamente:

```python
container.register_instance(EventBus, fake_event_bus, replace=True)
```

## Limites

Esta primeira versao nao implementa:

- eventos assincronos;
- filas;
- mensageria externa;
- Event Sourcing;
- CQRS;
- persistencia de eventos;
- auditoria;
- integracoes desktop, IA ou Open Finance.

Esses recursos pertencem a fases futuras e nao devem ser antecipados nesta PR.
