# Infraestrutura de Backup

Esta documentacao define a infraestrutura oficial de backup tecnico da
F.R.I.D.A.Y.

O backup desta etapa e local, deterministico e voltado exclusivamente a arquivos
tecnicos da aplicacao. Ele nao implementa backup incremental, compactacao,
criptografia, nuvem, agendamento ou interface grafica.

## Componentes

- `friday.infrastructure.backup.configuration`: configuracao derivada de
  `ApplicationSettings`.
- `friday.infrastructure.backup.manifest`: manifesto tecnico imutavel.
- `friday.infrastructure.backup.validators`: validacao de estrutura e
  integridade.
- `friday.infrastructure.backup.events`: eventos internos de backup.
- `friday.infrastructure.backup.service`: operacoes locais de backup.

## Estrutura

Cada backup e um diretorio isolado:

```text
backup-YYYYMMDD-HHMMSS-identifier.friday-backup/
  manifest.json
  database.sqlite
  metadata/
  logs/
```

O sufixo `.friday-backup` identifica diretorios oficiais de backup.

## Manifesto

O manifesto contem:

- identificador tipado;
- timestamp UTC;
- versao da aplicacao;
- versao do schema;
- arquivos incluidos;
- tamanho total;
- hash SHA-256 de integridade.

A serializacao e JSON deterministico.

## Fluxo de Criacao

1. Validar a configuracao.
2. Criar diretorio isolado.
3. Ler a versao atual do schema.
4. Copiar o banco SQLite local.
5. Gerar hashes dos arquivos.
6. Escrever `manifest.json`.
7. Registrar auditoria tecnica.
8. Publicar `BackupCreatedEvent`.

Backups parcialmente criados sao removidos em caso de falha.

## Fluxo de Restauracao

1. Validar o manifesto.
2. Validar arquivos obrigatorios.
3. Conferir hashes e tamanhos.
4. Substituir localmente o banco SQLite.
5. Registrar auditoria tecnica.
6. Publicar `BackupRestoredEvent`.

## Event Bus

O servico publica eventos internos:

- `BackupCreatedEvent`;
- `BackupValidatedEvent`;
- `BackupRestoredEvent`;
- `BackupDeletedEvent`.

Falhas de handlers sao registradas pelo Logger oficial e nao corrompem o backup.

## Auditoria Tecnica

Operacoes relevantes registram auditoria tecnica:

- criacao;
- validacao;
- restauracao;
- remocao;
- falhas.

Nao existe sistema paralelo de auditoria.

## Limites

Esta etapa nao implementa:

- backup incremental;
- backup diferencial;
- compactacao;
- criptografia;
- backup automatico;
- armazenamento remoto;
- dashboards;
- relatorios;
- interface desktop.
