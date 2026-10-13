# Repositório de conteúdo do app de D&D

Pacotes que o app baixa em **Conteúdo → Repositórios**. O app lê o
`repositorio.json`, mostra os pacotes agrupados por categoria, com filtro
**Jogador / Mestre**, e instala só o que for marcado.

**Só entra aqui conteúdo com licença aberta.** Livros da Wizards of the Coast
(Livro do Jogador, Guia do Mestre, Xanathar, aventuras) e livros comerciais de
terceiros sem licença aberta **não** podem ser redistribuídos. Cada jogador
importa no próprio aparelho o que possui.

## O que tem

| Pacotes | Fonte | Licença | Idioma |
|---|---|---|---|
| `srd-*` (magias, criaturas, itens, itens mágicos, talentos, antecedentes, condições) | SRD 5.1 via [5e-bits/5e-database](https://github.com/5e-bits/5e-database) | CC-BY-4.0 (dados: MIT) | en; pt-BR quando há tradução |
| `o5e-*` | Documentos 5e (2014) do [Open5e](https://open5e.com) — Kobold Press, Green Ronin e outros | OGL 1.0a / CC-BY-4.0 (ver `LICENSE-OGL.md`) | en |
| `fontes_aurora.json` | Índices do Aurora com licença aberta (DAPC, Dread Necromancer, Gus) | CC0 / Apache-2.0 / MIT | en |

Pacotes `srd-*` complementam o `srd-5.1` embutido no app (`"complementa"`): o que
o app já tem em português não é repetido.

Cada pacote traz `categoria`, `publico` (`jogador` e/ou `mestre`), `idioma`,
`fonte` e `licenca`; o gerador copia esses campos para o índice.

## Atualizar o conteúdo

```
python3 tool/importar_5ebits.py .     # SRD 5.1
python3 tool/importar_open5e.py .     # Open5e (demora: milhares de criaturas e magias)
dart pub get && dart run tool/gerar_repositorio.dart .
```

O workflow `.github/workflows/repositorio.yml` regenera o `repositorio.json`
(sha256, tamanho e contagem de cada pacote) a cada push em `pacotes/`.
O app recusa um pacote cujo sha256 não confere com o índice: nunca edite um
`.json` sem regenerar o índice.

## Índices do Aurora sugeridos

`fontes_aurora.json` lista índices `.index` com licença aberta. O app os mostra
na tela do repositório com o botão **Adicionar**; o download e a conversão
acontecem no aparelho. Para sugerir outro, confira a licença do repositório de
origem e acrescente `nome`, `url` (https), `descricao`, `licenca` e `publico`.

## Pacote próprio (homebrew)

Coloque o `.json` em `pacotes/` (formato em `docs/formato_pacote.md` do app). O
nome do arquivo deve ser `<id>.json`. Para atualizar, aumente `versao`. Conteúdo
criado no Aurora pode ser importado no app e exportado com **Exportar pacote**.
