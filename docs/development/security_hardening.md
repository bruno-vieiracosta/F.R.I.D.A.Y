# Hardening e Seguranca da Plataforma

Esta infraestrutura centraliza politicas tecnicas de seguranca para operacoes
locais da F.R.I.D.A.Y. Ela fortalece componentes ja existentes sem implementar
autenticacao, autorizacao, criptografia, rede, UI ou regras de negocio.

## Organizacao

```text
friday/security/hardening/
  exceptions.py
  filesystem.py
  models.py
  paths.py
  permissions.py
  policies.py
  validation.py
```

## Responsabilidades

A camada de hardening cobre apenas operacoes tecnicas locais:

- validacao e normalizacao de caminhos;
- protecao contra path traversal;
- protecao contra symlink traversal quando a plataforma permite verificar;
- criacao segura de diretorios;
- escrita atomica de arquivos criticos;
- copia e remocao controladas;
- validacao portatil de leitura e escrita;
- logging e auditoria tecnica sem conteudo sensivel.

## Politicas

`SecurityPolicy` define as raizes autorizadas da aplicacao. O container monta a
politica a partir de `ApplicationSettings`, incluindo:

- diretorio de dados;
- diretorio de logs;
- diretorio de backups;
- diretorio temporario;
- pasta do banco SQLite;
- pasta do arquivo local de segredos.

Qualquer operacao fora dessas raizes falha de forma segura usando a hierarquia
oficial de erros.

## Paths

Os utilitarios em `paths.py` validam texto, normalizam paths com `pathlib.Path`
e garantem pertencimento a uma raiz autorizada.

Tentativas com `..`, caminhos absolutos externos ou resolucoes que escapem da
raiz sao rejeitadas.

## Symlink Traversal

Quando links simbolicos podem ser criados e resolvidos no ambiente, a validacao
confirma que o destino final permanece dentro da raiz autorizada. Links que
apontam para fora sao rejeitados.

Em plataformas ou ambientes sem permissao para criar symlinks, os testes pulam
explicitamente esse cenario. A infraestrutura nao simula garantias quando a
plataforma nao oferece suporte verificavel.

## Filesystem

`SecureFilesystem` aplica a politica antes de executar operacoes locais:

- `ensure_directory`;
- `read_text`;
- `atomic_write_text`;
- `copy_file`;
- `remove_tree`.

A escrita atomica grava em arquivo temporario na mesma raiz autorizada e so
substitui o destino apos concluir a escrita. Em falha, o temporario e removido
e o arquivo original permanece preservado.

## Permissoes

As validacoes de permissao sao portateis e de baixo risco:

- arquivo existente e legivel;
- diretorio existente e gravavel;
- tipo do caminho compativel com a operacao.

Esta PR nao administra ACLs, permissoes NTFS avancadas, modos POSIX, usuario,
grupo ou propriedade de arquivos.

## Logging e Auditoria

O hardening usa o Logger oficial e registra auditoria tecnica via callback
fornecido pelo bootstrap.

Os registros nunca incluem:

- conteudo de arquivos;
- segredos;
- credenciais;
- dados financeiros;
- caminhos completos sensiveis.

Somente metadados tecnicos minimizados sao registrados, como nome do item,
proposito e operacao.

## Integracao com Backup

`BackupService` usa `SecureFilesystem` quando resolvido pelo container para:

- criar diretorios de backup;
- copiar o banco para o backup;
- escrever o manifesto de forma atomica;
- remover backups.

Instancias criadas diretamente continuam funcionando sem hardening injetado,
preservando compatibilidade de testes e uso isolado.

## Integracao com Segredos

`FileSecretProvider` usa `SecureFilesystem` quando resolvido pelo container para
ler o arquivo local de segredos dentro da raiz autorizada.

O conteudo do arquivo nunca e registrado em logs ou auditoria.

## Limitacoes

Esta etapa nao implementa:

- criptografia;
- autenticacao;
- autorizacao;
- OAuth;
- Open Finance;
- APIs externas;
- cofre externo;
- sandboxing;
- monitoramento continuo;
- politicas de rede.

O objetivo e endurecer a infraestrutura local existente e preparar a plataforma
para a consolidacao da Fase 1.
