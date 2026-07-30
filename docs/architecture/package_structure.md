# Estrutura de Pacotes

A F.R.I.D.A.Y. organiza sua arquitetura fisica em pacotes de responsabilidade unica. Nesta etapa, os pacotes ainda nao contem implementacoes funcionais; eles existem para estabelecer fronteiras claras para a evolucao incremental do projeto.

## Pacotes

- `friday.bootstrap`: ponto de composicao da aplicacao e configuracao central. Nao deve conter regra de negocio.
- `friday.application`: camada de orquestracao de casos de uso futuros. Pode depender de `domain` e `shared`.
- `friday.domain`: nucleo de regras de negocio futuras. Deve permanecer independente das demais camadas.
- `friday.infrastructure`: adaptadores tecnicos futuros, como persistencia e recursos locais.
- `friday.desktop`: camada de interface desktop futura.
- `friday.ai`: adaptadores e recursos de IA futuros.
- `friday.integrations`: integracoes externas futuras.
- `friday.security`: recursos futuros relacionados a seguranca da aplicacao.
- `friday.shared`: codigo compartilhado sem regras financeiras ou dependencias de infraestrutura.

## Fronteiras iniciais

- `domain` nao depende de `application`, `infrastructure`, `desktop`, `ai` ou `integrations`.
- `application` depende apenas de `domain` e `shared`.
- `desktop`, `ai`, `infrastructure` e `integrations` deverao depender de contratos e servicos expostos por camadas internas quando forem implementados em PRs futuras.
- Nenhum pacote deve introduzir dependencias circulares.
