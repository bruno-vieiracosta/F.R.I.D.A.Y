# F.R.I.D.A.Y. Development Playbook

> **Versão:** 1.0
> **Projeto:** F.R.I.D.A.Y.
> **Objetivo:** Definir o fluxo oficial de desenvolvimento, revisão, testes e integração utilizando ChatGPT, Codex, Claude Code, Free Claude Code, OpenCode e Aider.

---

# Índice

1. Objetivos
2. Filosofia de Desenvolvimento
3. Arquitetura das Ferramentas
4. Fluxo Oficial de Desenvolvimento
5. Responsabilidades de Cada Ferramenta
6. Modelos de IA Recomendados
7. Fluxo de Desenvolvimento das PRs
8. Processo de Revisão
9. Processo de Testes
10. Processo de Merge
11. Boas Práticas
12. Economia de Créditos
13. Estratégia para Grandes Funcionalidades
14. Estratégia para Bugs
15. Estratégia para Refatorações
16. Estratégia para Documentação
17. Estratégia para Pesquisa Científica
18. Checklist Oficial da PR
19. Roadmap de Evolução da Infraestrutura

---

# 1. Objetivos

Este documento define o processo oficial de desenvolvimento da F.R.I.D.A.Y.

Os objetivos são:

- manter uma arquitetura consistente;
- maximizar a qualidade do código;
- reduzir consumo de créditos;
- aumentar produtividade;
- padronizar o fluxo de trabalho;
- facilitar futuras contribuições.

---

# 2. Filosofia de Desenvolvimento

A F.R.I.D.A.Y. será desenvolvida utilizando uma arquitetura de IA distribuída.

Nenhuma ferramenta será responsável por todo o desenvolvimento.

Cada uma será utilizada de acordo com sua especialidade.

---

# 3. Arquitetura das Ferramentas

```
                ChatGPT
        (Planejamento Estratégico)
                  │
                  ▼
          Prompt Oficial da PR
                  │
                  ▼
         Escolha da Ferramenta
                  │
      ┌───────────┼───────────┐
      │           │           │
    Codex      Claude      Aider
      │           │           │
      ├───────────┼───────────┤
      │                       │
   OpenCode              Free Claude Code
                              │
          ┌───────────────────┼──────────────────┐
          │                   │                  │
   Nemotron Ultra      DeepSeek V4 Pro     DeepSeek Flash
```

---

# 4. Fluxo Oficial de Desenvolvimento

Toda funcionalidade seguirá obrigatoriamente este fluxo.

```
Planejamento

↓

Prompt Oficial

↓

Implementação

↓

Testes

↓

Revisão

↓

Smoke Test

↓

Merge
```

---

# 5. Responsabilidades de Cada Ferramenta

## ChatGPT

Responsável por:

- planejamento;
- arquitetura;
- roadmap;
- prompts;
- documentação;
- revisão final;
- decisões técnicas.

Nunca será utilizado para modificar diretamente o código.

---

## Codex

Responsável por:

- implementação de PRs complexas;
- arquitetura;
- Presenter;
- ViewModel;
- Dependency Injection;
- Navigation;
- IA;
- integrações;
- banco de dados;
- persistência.

---

## Claude Code

Responsável por:

- compreensão do projeto;
- exploração da base de código;
- implementação localizada;
- refatorações médias.

---

## OpenCode

Responsável por:

- UI;
- documentação;
- pequenas implementações;
- exemplos;
- README;
- comentários.

---

## Aider

Responsável por:

- testes;
- renomeações;
- limpeza;
- refatorações;
- atualização de imports;
- geração de commits.

---

## Free Claude Code

Responsável por:

- roteamento inteligente;
- gerenciamento de modelos;
- integração NVIDIA.

---

# 6. Modelos Oficiais

## Arquitetura

Modelo:

```
Nemotron 3 Ultra 550B A55
```

Utilização:

- arquitetura;
- planejamento;
- revisão;
- RAG;
- MCP;
- memória.

---

## Programação

Modelo:

```
DeepSeek V4 Pro
```

Utilização:

- implementação;
- refatoração;
- geração de código.

---

## Tarefas rápidas

Modelo

```
DeepSeek V4 Flash
```

Utilização:

- testes;
- documentação;
- pequenos bugs.

---

# 7. Fluxo Oficial das PRs

Cada PR seguirá este fluxo.

## Etapa 1

Planejamento

Ferramenta:

```
ChatGPT
```

Saída:

- Prompt da PR
- Estratégia
- Ferramenta recomendada
- Modelo recomendado

---

## Etapa 2

Implementação

Ferramenta:

- Codex
- Claude Code
- OpenCode
- Aider

---

## Etapa 3

Revisão

Sempre realizada pelo ChatGPT.

---

## Etapa 4

Testes

Executar obrigatoriamente:

```
pytest
```

---

## Etapa 5

Smoke Test

Executar:

```
python -m jarvis.desktop --smoke-test
```

ou equivalente para a F.R.I.D.A.Y.

---

## Etapa 6

Merge

Somente após:

- todos os testes verdes;
- smoke test aprovado;
- revisão concluída.

---

# 8. Processo Oficial de Revisão

Toda revisão verificará:

- arquitetura;
- SOLID;
- Clean Code;
- separação de responsabilidades;
- duplicação;
- nomenclatura;
- tipagem;
- documentação;
- cobertura de testes.

---

# 9. Processo Oficial de Testes

Tipos obrigatórios.

## Unitários

Sempre.

---

## Integração

Quando necessário.

---

## Smoke Test

Sempre.

---

## Regressão

Quando houver alteração arquitetural.

---

# 10. Critérios de Merge

Uma PR somente poderá ser integrada quando:

- arquitetura aprovada;
- testes aprovados;
- smoke test aprovado;
- documentação atualizada;
- sem código morto;
- sem TODOs esquecidos.

---

# 11. Boas Práticas

Sempre:

- criar pequenas PRs;
- evitar grandes merges;
- manter histórico limpo;
- revisar diff antes do commit.

Nunca:

- misturar arquitetura com UI;
- misturar refatoração com funcionalidade;
- alterar arquivos desnecessários.

---

# 12. Economia de Créditos

## Codex

Utilizar apenas para:

- arquitetura;
- grandes PRs;
- integrações.

---

## Claude Code

Utilizar para:

- exploração;
- alterações médias.

---

## OpenCode

Utilizar para:

- UI;
- documentação.

---

## Aider

Utilizar para:

- testes;
- limpeza.

---

## Free Claude Code

Sempre utilizar para aproveitar:

- Nemotron
- DeepSeek
- NVIDIA NIM

---

# 13. Grandes Funcionalidades

Fluxo:

```
Roadmap

↓

Arquitetura

↓

Implementação

↓

Testes

↓

Documentação

↓

Merge
```

Nunca implementar uma funcionalidade grande em uma única PR.

---

# 14. Correção de Bugs

Fluxo:

```
Identificar

↓

Reproduzir

↓

Corrigir

↓

Criar teste

↓

Validar

↓

Merge
```

---

# 15. Refatorações

Sempre:

- preservar comportamento;
- manter testes verdes;
- evitar mudanças desnecessárias.

---

# 16. Documentação

Toda PR deverá atualizar quando necessário:

- README
- CHANGELOG
- ROADMAP
- comentários relevantes
- documentação técnica

---

# 17. Pesquisa Científica

A F.R.I.D.A.Y. utilizará IA para:

- revisão bibliográfica;
- análise de artigos;
- organização de conhecimento;
- geração de resumos;
- auxílio em escrita científica.

Modelo principal:

```
Nemotron Ultra
```

---

# 18. Checklist Oficial da PR

Antes do Merge.

```
☐ Arquitetura validada

☐ Código revisado

☐ Testes passando

☐ Smoke Test

☐ Documentação atualizada

☐ Sem código morto

☐ Sem warnings

☐ Diff revisado

☐ Merge aprovado
```

---

# 19. Roadmap da Infraestrutura

## Atual

- ✅ ChatGPT
- ✅ Codex CLI
- ✅ Claude Code
- ✅ OpenCode
- ✅ Aider
- ✅ Free Claude Code
- ✅ NVIDIA NIM

---

## Futuro

- MCP Servers
- Memória Persistente
- RAG
- Banco Vetorial
- Agentes Especializados
- Integração Científica
- Automação de PRs
- Pipeline CI/CD Inteligente
- Sistema de Benchmark entre Modelos
- Dashboard de Produtividade
- Sistema de Métricas de IA

---

# Considerações Finais

Este documento estabelece o padrão oficial de desenvolvimento da F.R.I.D.A.Y.

Toda nova funcionalidade, correção ou evolução deverá seguir este processo para garantir:

- alta qualidade;
- consistência arquitetural;
- economia de créditos;
- facilidade de manutenção;
- escalabilidade do projeto.

O playbook deverá evoluir juntamente com o projeto, incorporando novas ferramentas, modelos de IA e práticas de engenharia de software conforme a F.R.I.D.A.Y. amadurecer.