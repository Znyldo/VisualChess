# Project Visual Chess

Aplicativo web em Python com Streamlit para reproduzir partidas de xadrez exportadas do Chess.com no tempo real em que os lances aconteceram.

## Objetivo

O projeto resolve uma dor específica: assistir uma partida já finalizada como se ela estivesse acontecendo ao vivo.

Em vez de avançar um lance a cada intervalo fixo, o app lê os tempos reais registrados no `.pgn` e reproduz cada jogada respeitando quanto tempo o jogador levou para executá-la.

## Problema que o app resolve

Plataformas como o Chess.com normalmente animam a replay da partida em velocidade artificial.

Neste projeto:

- cada lance usa o tempo real registrado no PGN
- o relógio de cada jogador é atualizado durante a reprodução
- o usuário consegue assistir a partida com sensação próxima de transmissão ao vivo

## Escopo atual

O app foi feito com foco em partidas do Chess.com exportadas em `.pgn` com:

- `TimeControl "120+1"`
- comentários contendo `[%clk ...]`
- comentários contendo `[%timestamp ...]`

Hoje o app está limitado ao formato `2min + 1s de incremento`, conforme a premissa do projeto.

## Como funciona

O fluxo principal é:

1. O usuário carrega um arquivo `.pgn`.
2. O app valida os headers da partida.
3. O parser extrai metadados, SAN dos lances, relógio após cada jogada e tempo gasto por lance.
4. Um motor interno reconstrói todos os estados do tabuleiro.
5. O frontend embutido no Streamlit reproduz os snapshots no tempo correto.

## Funcionalidades atuais

- upload de arquivo `.pgn`
- uso automático do PGN de exemplo da pasta `data_test/` quando nenhum arquivo é enviado
- validação de `TimeControl "120+1"`
- tabuleiro visual com peças customizadas em PNG
- replay no tempo real dos lances
- relógios das brancas e pretas atualizados durante a execução
- destaque visual do lance atual no tabuleiro
- lista de jogadas com SAN, tempo gasto e relógio após cada lance
- controles de `Play`, `Pause`, `Reiniciar`
- velocidades de reprodução `1x`, `2x`, `4x` e `8x`
- layout responsivo para uso no navegador

## Estrutura do projeto

```text
.
├── app_chess.py
├── REAMD.md
├── requirements.txt
├── assets/
│   └── images/
├── data_test/
│   └── Znyldo_vs_llucsb_2026.04.14.pgn
└── src/
    └── chess_replay/
        ├── __init__.py
        ├── component.py
        ├── models.py
        ├── pgn_parser.py
        ├── replay_engine.py
        └── time_utils.py
```

## Arquivos principais

### `app_chess.py`

Ponto de entrada do app Streamlit.

Responsável por:

- configurar a página
- receber upload do arquivo
- carregar o PGN de exemplo
- validar o arquivo
- renderizar o replay

### `src/chess_replay/pgn_parser.py`

Responsável pela leitura do `.pgn`.

Extrai:

- headers da partida
- SAN dos lances
- `[%clk]`
- `[%timestamp]`

### `src/chess_replay/replay_engine.py`

Reconstrói o tabuleiro movimento por movimento a partir do SAN.

Suporta:

- movimentos normais
- capturas
- roque pequeno e grande
- promoção
- en passant

### `src/chess_replay/component.py`

Gera o HTML, CSS e JavaScript embutidos no Streamlit.

Responsável por:

- desenhar o tabuleiro
- renderizar as peças
- atualizar os relógios
- controlar a reprodução
- mostrar a lista de jogadas

## Como rodar localmente

No terminal, na raiz do projeto:

```bash
streamlit run app_chess.py
```

Depois abra o endereço exibido pelo Streamlit no navegador.

## Dependências

Atualmente o projeto depende apenas de:

- `streamlit`

As demais partes do replay foram implementadas localmente em Python e JavaScript embutido, sem depender de bibliotecas externas de tabuleiro carregadas por CDN.

## Publicação no Streamlit Cloud

Para publicar:

1. Suba o projeto para um repositório no GitHub.
2. Garanta que `app_chess.py` esteja na raiz.
3. Garanta que `requirements.txt` esteja atualizado.
4. No Streamlit Cloud, conecte o repositório e selecione `app_chess.py` como arquivo principal.

## Premissas do projeto

- o arquivo `.pgn` vem do Chess.com
- a partida tem `TimeControl "120+1"`
- o PGN contém `[%clk]` e `[%timestamp]`
- o objetivo é replay web em Streamlit

## Limitações atuais

- só aceita `TimeControl "120+1"`
- foi testado com o padrão de exportação do Chess.com
- ainda não há suporte para múltiplas variantes de PGN fora desse escopo
- ainda não há controle manual de avançar/voltar lance a lance

## Próximos passos sugeridos

- suportar outros `TimeControl`
- adicionar botão para avançar e voltar lances manualmente
- adicionar barra de progresso da partida
- exibir gráfico de tempo consumido por jogador
- permitir compartilhamento por link com partidas pré-carregadas

## Resultado esperado do projeto

Entregar um app web simples de usar, publicado em Streamlit Cloud, no qual qualquer pessoa possa carregar um `.pgn` e assistir a partida no tempo real em que ela aconteceu, como se estivesse vendo ao vivo.
