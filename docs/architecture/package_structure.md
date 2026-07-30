# Estrutura de Pacotes

A F.R.I.D.A.Y. organiza sua arquitetura fisica em pacotes de responsabilidade unica. Ao final da Fase 1, esses pacotes ja contem a fundacao tecnica oficial do projeto e preservam fronteiras claras para a evolucao incremental da aplicacao.

## Pacotes

- `friday.bootstrap`: ponto de composicao da aplicacao, configuracao central, logging e container de dependencias. Nao deve conter regra de negocio.
- `friday.application`: camada de contratos e orquestracao de casos de uso futuros. Contem o Event Bus e contratos de persistencia, sem depender da Infrastructure.
- `friday.domain`: nucleo de regras de negocio futuras. Deve permanecer independente das demais camadas.
- `friday.infrastructure`: adaptadores tecnicos concretos, como persistencia SQLite + SQLAlchemy, migracoes, auditoria tecnica e backup local.
- `friday.desktop`: camada de interface desktop futura.
- `friday.ai`: adaptadores e recursos de IA futuros.
- `friday.integrations`: integracoes externas futuras.
- `friday.security`: infraestrutura transversal de seguranca, incluindo gerenciamento de segredos e hardening da plataforma.
- `friday.shared`: codigo compartilhado, tipos fundamentais, tipos financeiros, identificadores, relogio e erros oficiais.

## Fronteiras consolidadas

- `domain` nao depende de `application`, `infrastructure`, `desktop`, `ai`, `integrations` ou `security`.
- `application` define contratos e eventos internos sem depender de `infrastructure`, `desktop`, `ai`, `integrations` ou providers concretos de seguranca.
- `infrastructure` implementa contratos da `application` e integra recursos tecnicos concretos.
- `bootstrap` permanece como Composition Root e registra as dependencias concretas no container oficial.
- `security` fornece recursos transversais sem introduzir regra de negocio.
- `desktop`, `ai` e `integrations` permanecem isolados para a Fase 2.
- Nenhum pacote deve introduzir dependencias circulares.
