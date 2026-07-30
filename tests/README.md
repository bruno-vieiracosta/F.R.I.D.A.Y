# Testes

A suite oficial de testes da F.R.I.D.A.Y. e organizada por tipo de verificacao.

## Estrutura

```text
tests/
  architecture/
  integration/
  unit/
  fixtures/
  conftest.py
```

## Marcadores

- `unit`: testes rapidos e isolados.
- `integration`: testes que exercitam comportamento entre modulos ou comandos.
- `architecture`: testes de fronteiras arquiteturais e estrutura fisica.
- `slow`: testes mais lentos, usados apenas quando necessario.

## Fixtures compartilhadas

- `temporary_directory`: diretorio temporario isolado.
- `temporary_paths`: caminhos temporarios comuns para entrada, saida e cache.
- `fixed_clock`: relogio fixo para cenarios deterministas.
- `read_text_file`: leitura de arquivos de texto com UTF-8.

## Comandos

```bash
python -m pytest
python -m pytest --cov=friday
```
