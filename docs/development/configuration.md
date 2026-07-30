# Configuracao Centralizada

A F.R.I.D.A.Y. utiliza `friday.bootstrap.config` como fonte central de configuracao da aplicacao.

## Principios

- Configuracao imutavel apos a criacao.
- Leitura de variaveis de ambiente em um unico ponto.
- Validacao durante a inicializacao.
- Uso de `Enum` para ambientes e niveis de log.
- Uso de `pathlib.Path` para caminhos.
- Nenhuma dependencia de dominio, infraestrutura, banco de dados, logging ou arquivos `.env`.

## Uso

```python
from friday.bootstrap.config import load_settings

settings = load_settings()
```

Para testes, um mapping pode ser fornecido explicitamente:

```python
settings = load_settings({"FRIDAY_ENVIRONMENT": "testing"})
```

## Ambientes

`FRIDAY_ENVIRONMENT` aceita:

- `development`
- `testing`
- `production`

O valor padrao e `development`.

## Variaveis suportadas

| Variavel | Padrao |
| --- | --- |
| `FRIDAY_ENVIRONMENT` | `development` |
| `FRIDAY_DEBUG` | `false` |
| `FRIDAY_BASE_DIR` | `~/.friday` |
| `FRIDAY_DATA_DIR` | `FRIDAY_BASE_DIR/data` |
| `FRIDAY_LOGS_DIR` | `FRIDAY_BASE_DIR/logs` |
| `FRIDAY_BACKUPS_DIR` | `FRIDAY_BASE_DIR/backups` |
| `FRIDAY_TEMP_DIR` | `FRIDAY_BASE_DIR/temp` |
| `FRIDAY_LOG_LEVEL` | `INFO` |
| `FRIDAY_LOG_FILE_NAME` | `friday.log` |
| `FRIDAY_LOG_MAX_BYTES` | `1048576` |
| `FRIDAY_LOG_BACKUP_COUNT` | `5` |
| `FRIDAY_DATABASE_PATH` | `FRIDAY_DATA_DIR/friday.sqlite3` |
| `FRIDAY_FEATURE_DESKTOP` | `false` |
| `FRIDAY_FEATURE_AI` | `false` |
| `FRIDAY_FEATURE_INTEGRATIONS` | `false` |
| `FRIDAY_FEATURE_BACKUPS` | `false` |

## Validacao

A configuracao rejeita:

- ambiente desconhecido;
- booleanos fora dos valores aceitos;
- nivel de log desconhecido;
- nome de arquivo de log vazio ou com diretorios;
- tamanho maximo de log menor ou igual a zero;
- quantidade negativa de backups de log;
- caminhos vazios;
- caminhos com byte nulo;
- diretorios configurados que apontem para arquivos existentes;
- caminho de banco que aponte para diretorio;
- modo debug ativo em `production`.

Esta PR nao cria diretorios, nao inicializa banco, nao configura logging e nao carrega arquivos `.env`.
