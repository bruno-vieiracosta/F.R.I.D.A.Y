# Gerenciamento de Segredos

Esta infraestrutura centraliza o acesso a credenciais sensiveis da F.R.I.D.A.Y.
Ela existe apenas para armazenamento, recuperacao e validacao de segredos tecnicos.
Nenhuma API externa, autenticacao ou criptografia e implementada nesta etapa.

## Organizacao

```text
friday/security/secrets/
  provider.py
  environment.py
  file_provider.py
  resolver.py
  exceptions.py
  models.py
```

## Modelos

`SecretIdentifier` representa o nome tipado do segredo. O formato aceito utiliza
letras maiusculas, digitos e underscores, iniciando por letra.

`Secret` carrega o valor apenas para o consumidor que solicitou o segredo. A
serializacao e a representacao textual sempre retornam `<redacted>`.

## Secret Provider

`SecretProvider` e o contrato oficial para providers de segredos. Ele define:

- `get_secret`;
- `contains`;
- `list_identifiers`;
- `validate`;
- `source`.

As camadas consumidoras devem depender do contrato, nao dos providers concretos.

## Environment Provider

`EnvironmentSecretProvider` le variaveis do processo capturadas em uma abstracao.
O prefixo padrao e `FRIDAY_SECRET_`, configuravel por
`FRIDAY_SECRET_ENV_PREFIX`.

Exemplo:

```text
FRIDAY_SECRET_OPENAI_API_KEY
```

Valores vazios sao ignorados. O provider nunca registra o valor do segredo.

## File Provider

`FileSecretProvider` le um arquivo JSON local configurado por
`FRIDAY_SECRETS_FILE`.

Formato atual:

```json
{
  "version": 1,
  "secrets": {
    "FRIDAY_SECRET_EXAMPLE": "value"
  }
}
```

O arquivo nao e criptografado nesta PR. A estrutura foi mantida simples para
permitir criptografia futura sem alterar a API publica.

## Resolver

`SecretProviderResolver` implementa o contrato de provider e escolhe a origem em
ordem deterministica:

1. variaveis de ambiente;
2. arquivo seguro.

Se o arquivo estiver ausente, o resolver pode continuar usando o provider de
ambiente. Se nenhum provider contiver o identificador solicitado,
`SecretNotFoundError` e gerado.

## Configuration

`ApplicationSettings.secrets` contem somente metadados:

- caminho do arquivo de segredos;
- prefixo das variaveis de ambiente.

Nenhum valor sensivel e armazenado em `ApplicationSettings`.

## Dependency Injection

O bootstrap registra:

- `EnvironmentSecretProvider`;
- `FileSecretProvider`;
- `SecretProviderResolver`;
- `SecretProvider`.

`SecretProvider` resolve para o resolver oficial. Nao existem singletons globais
nem service locator.

## Logging e Auditoria

O resolver utiliza o Logger oficial e pode registrar auditoria tecnica via
callback fornecido pelo bootstrap.

Eventos registrados:

- segredo resolvido;
- provider indisponivel;
- segredo inexistente.

Somente identificador e origem sao registrados. Valores de segredos nunca devem
aparecer em logs, auditoria, excecoes ou banco de dados.

## Limitacoes

Esta etapa nao implementa:

- OAuth;
- Open Finance;
- APIs de IA;
- cofres externos;
- criptografia;
- backup de segredos;
- interface grafica;
- autenticacao;
- autorizacao.
