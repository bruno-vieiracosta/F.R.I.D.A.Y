# Dependency Injection

Esta documentacao define o container oficial de dependencias da F.R.I.D.A.Y.

O objetivo do container e centralizar a composicao da aplicacao sem introduzir
frameworks externos, descoberta automatica, autowiring ou estado global mutavel.

## Localizacao

O container vive em `friday.bootstrap.container`, pois faz parte da composicao
inicial da aplicacao.

Camadas como `domain`, `shared` e `application` nao devem importar o container.
Nas proximas PRs, casos de uso e servicos devem receber dependencias por
construtor ou parametros explicitos.

## Ciclos de vida

O container suporta somente dois ciclos de vida:

- `singleton`: uma instancia compartilhada por container.
- `transient`: uma nova instancia a cada resolucao.

Nao existem escopos implicitos, escopos assincronos ou escopos por requisicao
nesta fase.

## Registro

Servicos podem ser registrados por instancia existente ou por fabrica:

```python
from friday.bootstrap.container import ServiceContainer, ServiceLifetime

container = ServiceContainer()
container.register_instance(Settings, settings)
container.register_factory(
    Service,
    lambda current_container: Service(
        settings=current_container.resolve(Settings),
    ),
    lifetime=ServiceLifetime.TRANSIENT,
)
```

Registros duplicados sao rejeitados por padrao. Em testes, uma dependencia pode
ser substituida explicitamente com `replace=True`.

## Resolucao

A resolucao utiliza a mesma chave usada no registro:

```python
service = container.resolve(Service)
```

Caso o servico nao esteja registrado, o container levanta `ConfigurationError`
da hierarquia oficial de erros.

## Bootstrap

A funcao `build_container()` e o ponto unico de composicao dos servicos
fundamentais da infraestrutura.

Ela registra:

- `ApplicationSettings`;
- `LoggerFactory`;
- `logging.Logger`;
- `Clock`;
- `IdGenerator`.

O container retornado e uma instancia comum e independente. Nao ha singleton
global nem service locator acessivel pelo resto da aplicacao.

## Testes

Testes devem criar containers independentes. Para substituir dependencias:

```python
container.register_instance(Clock, fixed_clock, replace=True)
```

Tambem e permitido remover registros temporarios com `remove()` quando o teste
precisar validar falhas de resolucao.

## Limites

Esta infraestrutura nao implementa:

- autowiring;
- decorators de injecao;
- descoberta automatica por reflexao;
- escopos alem de singleton e transient;
- registro global de servicos;
- casos de uso, persistencia ou regras de negocio.
