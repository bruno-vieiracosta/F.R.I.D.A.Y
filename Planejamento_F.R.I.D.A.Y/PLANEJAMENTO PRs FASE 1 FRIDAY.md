# Planejamento de PRs — F.R.I.D.A.Y.
## Fase 1 — Fundação Técnica

> **Objetivo da fase:** estabelecer uma base técnica segura, testável e extensível para o F.R.I.D.A.Y., antes da implementação do shell desktop e das funcionalidades financeiras.

---

## 1. Princípios da Fase 1

- Arquitetura em camadas.
- Separação entre domínio, aplicação, infraestrutura e interface.
- Configuração centralizada.
- Tipagem rigorosa.
- Testes automatizados desde o início.
- Segurança por padrão.
- Valores financeiros sempre baseados em `Decimal`.
- Desenvolvimento incremental por PRs pequenas.
- Nenhuma integração real com bancos, corretoras ou IA nesta fase.

## 2. Resultado esperado

Ao final da Fase 1, o projeto deverá possuir repositório Python inicializado, estrutura oficial de pacotes, ambiente reproduzível, qualidade automatizada, suíte de testes, CI, configuração, logging, tratamento de erros, injeção de dependências, eventos, tipos financeiros, persistência SQLite, migrações, auditoria, backup, proteção de segredos e documentação arquitetural.

---

# 3. Sequência das PRs

```text
PR #1.0  Bootstrap do repositório
PR #1.1  Estrutura oficial de pacotes
PR #1.2  Qualidade de código
PR #1.3  Base de testes
PR #1.4  Integração contínua
PR #1.5  Configuração centralizada
PR #1.6  Logging estruturado
PR #1.7  Hierarquia de erros
PR #1.8  Tipos compartilhados
PR #1.9  Tipos financeiros fundamentais
PR #1.10 Identificadores e relógio
PR #1.11 Container de dependências
PR #1.12 Barramento de eventos
PR #1.13 Contratos de persistência
PR #1.14 Fundação do banco de dados
PR #1.15 Migrações com Alembic
PR #1.16 Auditoria técnica
PR #1.17 Fundação de backup
PR #1.18 Segurança de segredos
PR #1.19 Documentação arquitetural
PR #1.20 Validação e encerramento da Fase 1
```

---

# PR #1.0 — Bootstrap do repositório

## Objetivo
Criar o repositório mínimo executável do F.R.I.D.A.Y.

## Escopo
- Criar `pyproject.toml`.
- Definir versão mínima do Python.
- Criar pacote `friday`.
- Criar ponto de entrada básico.
- Criar `README.md`, `.gitignore` e licença.
- Criar estrutura mínima de testes.
- Validar instalação em modo editável.

## Critérios de aceite
- `python -c "import friday"` funciona.
- `pytest` executa com sucesso.
- `pip install -e .` funciona.
- A versão do pacote está acessível.
- Nenhuma dependência desktop é adicionada.

## Testes
- Importação do pacote.
- Versão.
- Ponto de entrada mínimo.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** econômico, com bom suporte a Python.

---

# PR #1.1 — Estrutura oficial de pacotes

## Objetivo
Criar a estrutura arquitetural sem implementar regras de negócio.

## Escopo

```text
friday/
├── bootstrap/
├── application/
├── domain/
├── infrastructure/
├── ai/
├── integrations/
├── security/
├── shared/
└── desktop/
```

## Regras arquiteturais
- `domain` não importa camadas externas.
- `application` depende apenas de `domain` e `shared`.
- `infrastructure` implementa contratos.
- `desktop` chama a aplicação, não repositórios diretamente.
- `ai` usa ferramentas expostas pela aplicação.
- `shared` não contém regras financeiras específicas.

## Critérios de aceite
- Todos os pacotes podem ser importados.
- Não existem dependências circulares.
- Responsabilidades estão documentadas.

## Testes
- Testes de importação.
- Teste de fronteiras arquiteturais.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** econômico ou intermediário.

---

# PR #1.2 — Qualidade de código

## Objetivo
Padronizar lint, formatação, imports e tipagem.

## Escopo
- Ruff.
- Formatação pelo Ruff ou Black.
- mypy ou Pyright.
- Regras de imports e complexidade.
- Configuração central no `pyproject.toml`.
- Pre-commit opcional.

## Comandos obrigatórios

```bash
ruff check .
ruff format --check .
mypy friday
pytest
```

## Critérios de aceite
- Lint sem erros.
- Formatação validada.
- Tipagem validada.
- Nenhuma regra desabilitada sem justificativa.

## Execução recomendada
- **Ferramenta:** Codex ou Aider.
- **Modelo:** econômico.

---

# PR #1.3 — Base de testes

## Objetivo
Criar a estratégia e a infraestrutura de testes.

## Escopo
- Configurar `pytest` e cobertura.
- Criar fixtures compartilhadas.
- Criar marcadores.
- Separar testes unitários, integração e arquitetura.
- Documentar convenções.

```text
tests/
├── unit/
├── integration/
├── architecture/
├── conftest.py
└── README.md
```

## Critérios de aceite
- Suíte executa sem warnings inesperados.
- Cobertura é gerada.
- Marcadores funcionam.
- Testes lentos podem ser separados.

## Testes
- Diretório temporário.
- Relógio fixo.
- Descoberta da suíte.
- Marcadores.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** intermediário.

---

# PR #1.4 — Integração contínua

## Objetivo
Automatizar as validações em push e pull request.

## Escopo
- Instalação.
- Lint.
- Formatação.
- Tipagem.
- Testes e cobertura.
- Build do pacote.

## Critérios de aceite
- Pipeline funciona em ambiente limpo.
- Falha corretamente quando uma validação falha.
- Cache é utilizado quando apropriado.
- Versão do Python está fixada.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** econômico ou intermediário.

---

# PR #1.5 — Configuração centralizada

## Objetivo
Criar um sistema único de configuração.

## Escopo
- Configuração da aplicação.
- Variáveis de ambiente.
- Ambientes de desenvolvimento, teste e produção.
- Caminhos de dados e banco.
- Nível de log.
- Feature flags.
- Validação de configuração.

## Critérios de aceite
- A configuração não acessa a rede.
- Testes usam diretórios temporários.
- Valores inválidos geram erro claro.
- Segredos não ficam hardcoded.

## Testes
- Valores padrão.
- Variáveis de ambiente.
- Caminhos.
- Configuração inválida.
- Isolamento de testes.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** intermediário.

---

# PR #1.6 — Logging estruturado

## Objetivo
Criar observabilidade básica e segura.

## Escopo
- Logs em console e arquivo.
- Rotação.
- Contexto e correlação.
- Níveis configuráveis.
- Mascaramento de dados sensíveis.
- Captura de exceções não tratadas.

## Dados proibidos nos logs
- Senhas e tokens.
- Números completos de contas.
- Documentos pessoais.
- Dados financeiros desnecessários.

## Critérios de aceite
- Logs possuem timestamp, nível e módulo.
- Rotação funciona.
- Dados sensíveis são mascarados.
- Falha no logging não derruba o aplicativo.

## Testes
- Console e arquivo.
- Rotação.
- Mascaramento.
- Correlação.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** intermediário.

---

# PR #1.7 — Hierarquia de erros

## Objetivo
Padronizar falhas técnicas e de negócio.

## Tipos iniciais

```text
FridayError
DomainError
ApplicationError
ValidationError
ConfigurationError
InfrastructureError
PersistenceError
SecurityError
IntegrationError
```

## Critérios de aceite
- Erros possuem códigos estáveis.
- Mensagens técnicas e públicas podem ser separadas.
- Causa original pode ser preservada.
- Segredos não são expostos.

## Testes
- Hierarquia.
- Serialização segura.
- Preservação de causa.
- Mensagens públicas.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** econômico.

---

# PR #1.8 — Tipos compartilhados

## Objetivo
Criar tipos genéricos reutilizáveis.

## Escopo
- `Result`.
- Paginação.
- Intervalos de data.
- Níveis de confiança.
- Status de operação.
- Protocolos compartilhados.

## Critérios de aceite
- Tipos são imutáveis quando apropriado.
- Não contêm regras financeiras específicas.
- Possuem tipagem rigorosa.

## Testes
- Sucesso e falha de `Result`.
- Paginação.
- Intervalos válidos e inválidos.
- Serialização.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** intermediário.

---

# PR #1.9 — Tipos financeiros fundamentais

## Objetivo
Criar os objetos de valor críticos do domínio financeiro.

## Escopo
- `Currency`.
- `Money`.
- `Percentage`.
- `InterestRate`.
- `ExchangeRate`.
- Política de arredondamento.
- Operações aritméticas seguras.

## Regras obrigatórias
- Usar `Decimal`, nunca `float`.
- Impedir soma de moedas diferentes.
- Conversão exige taxa explícita.
- Arredondamento determinístico.
- Objetos imutáveis.

## Critérios de aceite
- Operações são precisas.
- Moedas incompatíveis geram erro.
- Serialização é estável.
- Cobertura próxima de 100% no módulo.

## Testes
- Soma, subtração, multiplicação e divisão.
- Moedas incompatíveis.
- Arredondamento.
- Valores negativos e zero.
- Comparação e conversão.

## Execução recomendada
- **Ferramenta:** Codex; Aider para refinamento dos testes.
- **Modelo:** alta qualidade.

---

# PR #1.10 — Identificadores e relógio

## Objetivo
Padronizar IDs e tornar o tempo controlável nos testes.

## Escopo
- IDs tipados.
- Gerador de UUID.
- Protocolo de relógio.
- Relógio do sistema e relógio fixo.
- Utilitários de timezone.
- UTC internamente.

## Critérios de aceite
- Entidades podem usar IDs tipados.
- Testes não dependem do relógio real.
- Timezone é explícito.
- Datas possuem serialização consistente.

## Testes
- Geração e comparação de IDs.
- Relógio fixo.
- Conversão UTC/local.
- Serialização.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** intermediário.

---

# PR #1.11 — Container de dependências

## Objetivo
Centralizar a criação das dependências.

## Escopo
- `DependencyContainer`.
- Registro de configuração, logger e relógio.
- Substituições em testes.
- Ciclos de vida explícitos.
- Proibição de service locator espalhado.

## Critérios de aceite
- Container é criado no bootstrap.
- Não há globais de infraestrutura.
- Testes substituem dependências facilmente.
- Dependências ausentes geram erro claro.

## Testes
- Registro e resolução.
- Override.
- Singleton e fábrica.
- Dependência ausente.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** intermediário forte ou alta qualidade.

---

# PR #1.12 — Barramento de eventos

## Objetivo
Permitir comunicação desacoplada entre módulos.

## Escopo
- Evento base.
- Handler.
- Event bus síncrono.
- Registro e publicação.
- Tratamento de falhas.
- Sem filas externas nesta fase.

## Critérios de aceite
- Eventos são imutáveis.
- Múltiplos handlers são suportados.
- Falhas seguem política definida.
- Publicação é testável.

## Testes
- Sem handlers.
- Um e vários handlers.
- Falha em handler.
- Evento desconhecido.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** intermediário ou alta qualidade.

---

# PR #1.13 — Contratos de persistência

## Objetivo
Definir interfaces sem acoplar o domínio ao SQLAlchemy.

## Escopo
- Unidade de trabalho.
- Contrato de transação.
- Repositório base.
- Paginação de consultas.
- Erros de persistência.

## Critérios de aceite
- O domínio não importa SQLAlchemy.
- Contratos aceitam implementação em memória ou SQLite.
- Commit e rollback são explícitos.

## Testes
- Implementação fake.
- Commit e rollback.
- Context manager, se adotado.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** alta qualidade.

---

# PR #1.14 — Fundação do banco de dados

## Objetivo
Preparar SQLite e SQLAlchemy.

## Escopo
- Engine.
- Session factory.
- Pragmas SQLite.
- Base declarativa.
- Health check.
- Unidade de trabalho inicial.

## Regras
- Banco de teste isolado.
- Foreign keys ativadas.
- Transações explícitas.
- Nenhum modelo financeiro completo ainda.

## Critérios de aceite
- Banco é criado no caminho configurado.
- Sessões abrem e fecham corretamente.
- Commit, rollback e health check funcionam.

## Testes
- Criação, conexão e sessão.
- Commit e rollback.
- Erro de conexão.
- Isolamento.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** alta qualidade.

---

# PR #1.15 — Migrações com Alembic

## Objetivo
Configurar versionamento do esquema.

## Escopo
- Integrar Alembic.
- Configurar metadata.
- Criar primeira migração técnica.
- Validar upgrade e downgrade.
- Documentar comandos.

## Primeira tabela sugerida
- `application_metadata` ou `schema_metadata`.

## Critérios de aceite
- Upgrade cria o esquema.
- Downgrade reverte.
- Funciona em banco vazio.
- Pipeline pode validar migrações.

## Testes
- Upgrade, downgrade e recriação.
- Banco já atualizado.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** intermediário ou alta qualidade.

---

# PR #1.16 — Auditoria técnica

## Objetivo
Criar a base para rastrear operações relevantes.

## Escopo
- Evento de auditoria.
- Ator, ação, recurso e resultado.
- Timestamp e correlação.
- Metadados seguros.
- Repositório e serviço de auditoria.

## Regras
- Auditoria não substitui logging.
- Registros são append-only.
- Segredos nunca são armazenados.

## Critérios de aceite
- Eventos podem ser persistidos e consultados.
- Dados sensíveis são filtrados.
- Política de falha está documentada.

## Testes
- Gravação e consulta.
- Filtragem.
- Correlação.
- Campos obrigatórios.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** alta qualidade.

---

# PR #1.17 — Fundação de backup

## Objetivo
Criar backup local seguro do banco.

## Escopo
- Contrato de backup.
- Backup manual.
- Nomeação versionada.
- Checksum e manifesto.
- Retenção configurável.
- Restauração em ambiente temporário.
- Sem nuvem nesta fase.

## Critérios de aceite
- Backup pode ser criado e validado.
- Corrupção é detectada.
- Restauração não sobrescreve dados sem confirmação.
- Retenção é testável.

## Testes
- Criação e checksum.
- Corrupção.
- Retenção.
- Restauração temporária.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** alta qualidade.

---

# PR #1.18 — Segurança de segredos

## Objetivo
Preparar o armazenamento seguro de credenciais futuras.

## Escopo
- Contrato `SecretStore`.
- Implementação de desenvolvimento.
- Integração opcional com o cofre do sistema operacional.
- Mascaramento, substituição e remoção.
- Proibição de segredos em configuração comum.

## Critérios de aceite
- Segredos não aparecem em logs.
- A implementação pode ser substituída.
- Testes usam fake.
- Erros possuem mensagens seguras.

## Testes
- Salvar, ler, substituir e remover.
- Mascaramento.
- Falha de acesso.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** alta qualidade.

---

# PR #1.19 — Documentação arquitetural

## Objetivo
Registrar oficialmente as decisões da fundação.

## Estrutura

```text
docs/
├── architecture/
│   ├── overview.md
│   ├── dependency_rules.md
│   ├── configuration.md
│   ├── logging.md
│   ├── persistence.md
│   ├── security.md
│   └── testing.md
└── adr/
```

## ADRs recomendados
- Python e PySide6.
- Clean Architecture.
- Uso de `Decimal`.
- SQLite, SQLAlchemy e Alembic.
- Eventos internos.
- Injeção de dependências.

## Critérios de aceite
- A documentação reflete o código real.
- Decisões importantes possuem justificativa.
- Comandos estão atualizados.

## Execução recomendada
- **Ferramenta:** Aider ou Codex.
- **Modelo:** intermediário com boa escrita técnica.

---

# PR #1.20 — Validação e encerramento da Fase 1

## Objetivo
Consolidar e validar toda a fundação técnica.

## Escopo
- Revisar dependências e fronteiras.
- Remover código morto.
- Executar testes completos.
- Validar build, migrações e backup.
- Revisar segurança e documentação.
- Criar relatório de encerramento.

## Checklist obrigatório

```text
[ ] Importação do pacote
[ ] Lint
[ ] Formatação
[ ] Tipagem
[ ] Testes unitários
[ ] Testes de integração
[ ] Testes arquiteturais
[ ] Cobertura
[ ] Build
[ ] Migração upgrade/downgrade
[ ] Backup e restauração de teste
[ ] Auditoria
[ ] Logs sem dados sensíveis
[ ] Documentação atualizada
[ ] CI aprovado
```

## Critérios de aceite
- Todos os pipelines estão verdes.
- Nenhuma funcionalidade desktop foi antecipada.
- Nenhuma regra financeira concreta foi implementada indevidamente.
- Tipos financeiros estão estáveis.
- Banco, migração, auditoria e backup funcionam.
- A Fase 2 pode começar sem refatoração estrutural ampla.

## Execução recomendada
- **Ferramenta:** Codex.
- **Modelo:** alta qualidade e contexto amplo.

---

# 4. Dependências entre PRs

```text
#1.0
 └── #1.1
      ├── #1.2
      │    ├── #1.3
      │    └── #1.4
      ├── #1.5
      │    ├── #1.6
      │    ├── #1.10
      │    └── #1.18
      ├── #1.7
      ├── #1.8
      │    └── #1.9
      ├── #1.11
      │    └── #1.12
      └── #1.13
           └── #1.14
                ├── #1.15
                ├── #1.16
                └── #1.17

#1.19 consolida as decisões anteriores.
#1.20 depende de todas as PRs da Fase 1.
```

---

# 5. O que não deve entrar na Fase 1

- Shell e páginas desktop definitivas.
- Sidebar, topbar e statusbar visuais.
- Gráficos e dashboard financeiro.
- Entidades completas de contas, transações e carteira.
- Importação de extratos.
- APIs de mercado e Open Finance.
- Integrações com bancos e corretoras.
- Agentes de IA, RAG e embeddings.
- Recomendações de investimento.
- Sincronização em nuvem.
- Autenticação completa do usuário final.

---

# 6. Estratégia de execução

## Bloco A — Repositório e qualidade
- PR #1.0 a #1.4.

## Bloco B — Infraestrutura compartilhada
- PR #1.5 a #1.12.

## Bloco C — Dados, segurança e continuidade
- PR #1.13 a #1.18.

## Bloco D — Consolidação
- PR #1.19 e #1.20.

Cada PR deve possuir objetivo único, testes, documentação e manter o repositório executável. Alterações não relacionadas devem ser evitadas.

---

# 7. Definition of Done da Fase 1

A fase estará concluída quando:

- o projeto puder ser clonado e instalado com instruções claras;
- importação, lint, formatação, tipagem e testes passarem;
- o CI estiver funcional;
- configuração, logging e erros estiverem padronizados;
- os tipos financeiros fundamentais estiverem completamente testados;
- injeção de dependências e eventos estiverem operacionais;
- persistência, migrações, auditoria e backup estiverem funcionais;
- segredos não forem tratados de forma insegura;
- a documentação arquitetural refletir o estado real do projeto.

---

# 8. Próxima fase

Após a aprovação da PR #1.20, iniciar:

> **Fase 2 — Fundação do Aplicativo Desktop**

Com foco em `MainWindow`, sidebar, topbar, statusbar, navegação centralizada, catálogo tipado de destinos, ciclo de vida de páginas, tema F.R.I.D.A.Y., design system e smoke test desktop.
