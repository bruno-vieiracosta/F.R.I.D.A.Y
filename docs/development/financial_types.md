# Tipos Financeiros

A F.R.I.D.A.Y. utiliza `friday.shared.finance` como biblioteca oficial de Value Objects financeiros fundamentais.

## Currency

`Currency` representa uma moeda por codigo ISO de tres letras.

Exemplos:

- `BRL`
- `USD`
- `EUR`

O codigo e normalizado para maiusculas e validado localmente. Nao ha consulta a servicos externos.

## Money

`Money` representa um valor monetario com `Decimal` e uma `Currency` obrigatoria.

Operacoes suportadas:

- soma com mesma moeda;
- subtracao com mesma moeda;
- multiplicacao por escalar `Decimal` ou inteiro;
- divisao por escalar `Decimal` ou inteiro;
- comparacao entre valores da mesma moeda.

Operacoes entre moedas diferentes geram `ValidationError`.

## Arredondamento

O arredondamento monetario oficial usa:

```text
MONEY_QUANTUM = Decimal("0.01")
MONEY_ROUNDING = ROUND_HALF_UP
```

Todo `Money` e quantizado na criacao e apos operacoes matematicas.

## Percentage

`Percentage` representa percentuais com `Decimal`.

Ela fornece:

- representacao textual;
- `to_factor()`;
- `to_dict()`.

## InterestRate

`InterestRate` combina um `Percentage` com `InterestPeriod`.

Periodos suportados:

- `DAILY`
- `MONTHLY`
- `YEARLY`

Esta PR nao implementa juros simples, compostos ou calculos financeiros.

## ExchangeRate

`ExchangeRate` representa uma taxa entre duas moedas diferentes.

Campos:

- `source`;
- `target`;
- `rate`.

A taxa deve ser `Decimal`, finita e maior que zero. Esta PR nao implementa conversao automatica de `Money`.

## Fora do Escopo

Esta PR nao implementa ativos, carteira, fluxo de caixa, patrimonio, rentabilidade, impostos, inflacao, cotacoes, APIs, persistencia, banco de dados ou entidades financeiras.
