# Alembic

Diretorio oficial de migracoes do banco da F.R.I.D.A.Y.

Use sempre a configuracao centralizada da aplicacao. A infraestrutura em
`alembic/env.py` carrega `ApplicationSettings`, resolve o caminho do banco e
reutiliza a Engine Factory oficial.

Comandos principais:

```bash
alembic upgrade head
alembic downgrade base
```

Novas revisoes devem ser criadas apenas para alteracoes oficiais do schema.
Nao criar tabelas de dominio ou dados de negocio fora do planejamento da fase.
