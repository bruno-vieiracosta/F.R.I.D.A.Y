# Erros e Excecoes

A F.R.I.D.A.Y. utiliza `friday.shared.errors` como infraestrutura oficial para erros tecnicos e funcionais.

## Hierarquia

```text
FridayError
├── DomainError
├── ApplicationError
├── ValidationError
├── ConfigurationError
├── InfrastructureError
│   └── PersistenceError
├── SecurityError
└── IntegrationError
```

## Estrutura

Toda excecao oficial possui:

- codigo estavel;
- categoria;
- mensagem publica;
- mensagem tecnica;
- causa original opcional;
- metadados opcionais;
- serializacao publica e serializacao para logs.

## Codigos

Os codigos seguem o formato:

```text
FRIDAY-<CATEGORIA>-001
```

Exemplos:

- `FRIDAY-CONFIG-001`
- `FRIDAY-INFRA-001`
- `FRIDAY-SECURITY-001`

Subcasos futuros podem definir codigos mais especificos sem alterar a hierarquia base.

## Mensagens

A mensagem publica deve ser segura para exibicao futura ao usuario. Ela nao deve conter stack trace, caminhos internos, credenciais ou detalhes tecnicos.

A mensagem tecnica e destinada a diagnostico e pode conter contexto adicional, mas a serializacao para logs aplica mascaramento antes de expor dados.

## Serializacao

- `to_public_dict()`: retorna apenas codigo, categoria e mensagem publica segura.
- `to_log_dict()`: retorna codigo, categoria, mensagem publica, mensagem tecnica mascarada, metadados mascarados e causa mascarada quando existir.

## Logging

As excecoes nao registram logs automaticamente. Para integrar com o logger oficial, serialize explicitamente:

```python
logger.error("Application error: %s", error.to_log_dict())
```

O mascaramento reutiliza a infraestrutura de logging para proteger tokens, senhas, chaves de API, secrets e credenciais.

## Fora do escopo atual

Esta PR nao implementa tratamento global de excecoes, interface grafica, internacionalizacao, auditoria, metricas, telemetria, HTTP ou Dependency Injection.
