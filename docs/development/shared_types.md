# Tipos Compartilhados

A F.R.I.D.A.Y. utiliza `friday.shared.types` para tipos genericos reutilizaveis por todas as camadas.

## Result

`Result[T, E]` representa uma operacao que pode terminar com sucesso ou falha.

```python
result = Result.success(10)
error = Result.failure(ValidationError())
```

Recursos disponiveis:

- `is_success`
- `is_failure`
- `value`
- `error`
- `value_or(default)`
- `error_or(default)`
- `map(...)`
- `to_dict()`

`map` transforma apenas resultados de sucesso. Falhas preservam o erro original.

## Paginacao

`PagedResult[T]` representa uma pagina ja carregada, sem executar consultas ou acessar banco de dados.

Campos:

- `items`
- `page`
- `page_size`
- `total_items`
- `total_pages`

Tambem fornece `has_previous_page`, `has_next_page` e `to_dict()`.

## Intervalo de Datas

`DateRange` representa um intervalo inclusivo entre `start` e `end`.

O inicio e o fim sao obrigatorios, e `start` nao pode ser posterior a `end`.

## Enums

`ConfidenceLevel`:

- `LOW`
- `MEDIUM`
- `HIGH`

`OperationStatus`:

- `PENDING`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

## Protocolos

Protocolos genericos:

- `SupportsToDict`
- `SupportsPublicDict`
- `SupportsText`
- `HasIdentifier`

Eles existem para tipagem estrutural e nao definem contratos de persistencia, banco de dados ou infraestrutura.

## Fora do Escopo

Esta PR nao implementa tipos financeiros, identificadores, relogio, contratos de persistencia, entidades, eventos ou regras de negocio.
