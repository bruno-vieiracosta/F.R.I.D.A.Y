# ROADMAP --- F.R.I.D.A.Y.

## Financial Research, Intelligence, Decisions and Analytics for You

> **Visão:** Desenvolver um assistente financeiro pessoal inteligente
> para organização financeira, gestão patrimonial, investimentos, metas
> e apoio à decisão.

------------------------------------------------------------------------

# Filosofia do Projeto

-   Clean Architecture
-   PySide6 (Desktop)
-   MVP/MVVM
-   Desenvolvimento incremental por PRs pequenas
-   Alta cobertura de testes
-   Segurança por padrão
-   IA como apoio à decisão
-   Conhecimento supervisionado pelo usuário
-   Todos os cálculos auditáveis

------------------------------------------------------------------------

# FASE 1 --- Fundação Técnica

## Objetivos

-   Estrutura do repositório
-   Configuração do projeto
-   CI/CD
-   Logging
-   Testes
-   Injeção de dependências
-   Tipos financeiros (`Money`, `Currency`, `Percentage`)
-   Banco de dados e migrações
-   Convenções de código

------------------------------------------------------------------------

# FASE 2 --- Aplicativo Desktop

## Shell

-   MainWindow
-   Sidebar
-   Topbar
-   StatusBar
-   NavigationController
-   DesktopNavigationService
-   PageLifecycle
-   Theme F.R.I.D.A.Y.
-   Design System
-   Componentes reutilizáveis

------------------------------------------------------------------------

# FASE 3 --- Interface Visual

## Páginas

1.  Dashboard
2.  Alertas
3.  Fluxo de Caixa
4.  Orçamento
5.  Patrimônio
6.  Metas
7.  Carteira
8.  Ativos
9.  Proventos
10. Simulações
11. Diário de Investimentos
12. Conhecimento
13. F.R.I.D.A.Y.
14. Relatórios
15. Integrações
16. Configurações
17. Segurança
18. Backup

> Nesta fase todas as páginas são visuais e estáticas.

------------------------------------------------------------------------

# FASE 4 --- Domínio Financeiro

-   Contas
-   Transações
-   Receitas
-   Despesas
-   Fluxo de Caixa
-   Orçamentos
-   Patrimônio
-   Ativos
-   Passivos
-   Carteira
-   Proventos
-   Metas
-   Planejamento
-   Simulações
-   Indicadores
-   Regras financeiras

------------------------------------------------------------------------

# FASE 5 --- Persistência

-   SQLite
-   SQLAlchemy
-   Alembic
-   Repositórios
-   Auditoria
-   Backup
-   Criptografia
-   Versionamento

------------------------------------------------------------------------

# FASE 6 --- Integração Funcional

Conectar gradualmente cada página aos casos de uso e ao domínio:

Fluxo de Caixa → Orçamento → Patrimônio → Metas → Carteira → Ativos →
Proventos → Simulações → Diário → Dashboard → Alertas → Relatórios.

------------------------------------------------------------------------

# FASE 7 --- Conhecimento Financeiro

-   Biblioteca
-   Livros
-   PDFs
-   Artigos
-   Anotações
-   Extração de conceitos
-   Aprovação manual
-   Versionamento
-   Base oficial de conhecimento

------------------------------------------------------------------------

# FASE 8 --- IA Financeira

-   Chat especializado
-   Ferramentas determinísticas
-   Agentes financeiros
-   Memória
-   Explicabilidade
-   Rastreabilidade

------------------------------------------------------------------------

# FASE 9 --- Integrações

-   Bancos
-   Corretoras
-   Open Finance
-   B3
-   CSV
-   OFX
-   PDF
-   Planilhas
-   Google Drive
-   OneDrive

------------------------------------------------------------------------

# FASE 10 --- Segurança

-   Senha mestra
-   2FA
-   Criptografia
-   Auditoria
-   Sessões
-   Permissões
-   Backup seguro

------------------------------------------------------------------------

# FASE 11 --- Automações

-   Alertas
-   Relatórios
-   Sincronizações
-   Rebalanceamento
-   Agenda financeira

------------------------------------------------------------------------

# FASE 12 --- Versão 1.0

## Entregas

-   Gestão financeira
-   Patrimônio
-   Investimentos
-   Relatórios
-   IA especializada
-   Conhecimento supervisionado
-   Segurança
-   Backup
-   Integrações
-   Dashboard executivo

------------------------------------------------------------------------

# Ordem Recomendada

1.  Fundação técnica
2.  Desktop
3.  Interface visual
4.  Domínio financeiro
5.  Persistência
6.  Integração funcional
7.  Conhecimento
8.  IA
9.  Integrações
10. Segurança
11. Automações
12. Versão 1.0
