# Logging Estruturado

A F.R.I.D.A.Y. utiliza `friday.bootstrap.logging` como infraestrutura oficial de logging tecnico.

## Principios

- Configuracao baseada em `ApplicationSettings`.
- Uso exclusivo da biblioteca padrao `logging`.
- Saida em console e arquivo.
- Rotacao por tamanho com `RotatingFileHandler`.
- Mascaramento de dados sensiveis antes da escrita.
- Captura de excecoes nao tratadas via `sys.excepthook`.
- Nenhuma dependencia de dominio, aplicacao, banco de dados, auditoria ou telemetria.

## Uso

```python
from friday.bootstrap.config import load_settings
from friday.bootstrap.logging import configure_logging, install_exception_hook

settings = load_settings()
factory = configure_logging(settings)
install_exception_hook(factory)

logger = factory.get_logger("bootstrap")
logger.info("Application started")
```

## Formato

Cada linha inclui:

- timestamp;
- nivel;
- modulo de origem;
- nome do logger;
- mensagem.

## Arquivo e rotacao

O arquivo padrao e `friday.log` dentro de `settings.directories.logs`.

Variaveis relacionadas:

| Variavel | Padrao |
| --- | --- |
| `FRIDAY_LOG_LEVEL` | `INFO` |
| `FRIDAY_LOG_FILE_NAME` | `friday.log` |
| `FRIDAY_LOG_MAX_BYTES` | `1048576` |
| `FRIDAY_LOG_BACKUP_COUNT` | `5` |

O diretorio de logs e criado automaticamente quando necessario. Se a criacao do handler de arquivo falhar, o logging continua disponivel no console.

## Mascaramento

As mensagens finais sao mascaradas antes da escrita. Chaves como `password`, `token`, `api_key`, `secret` e `credential` sao substituidas por `***`. Tokens no formato `Bearer ...` tambem sao mascarados.

## Erros oficiais

As excecoes oficiais em `friday.shared.errors` nao registram logs automaticamente. Para logging, utilize `error.to_log_dict()`; a serializacao segura reutiliza o mesmo mascaramento desta infraestrutura.

## Fora do escopo atual

Esta PR nao implementa logs JSON, auditoria, metricas, OpenTelemetry, Sentry, envio remoto, correlation id, trace id, request id ou user id.
