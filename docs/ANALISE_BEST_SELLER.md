# Oval: análise de design "best-seller"

Relatório do agente de design (visão Steam/Epic: retenção, progresso, polimento, compartilhamento).
Itens marcados com ✅ foram implementados nesta rodada.

## Estado atual

**Fortes:** muito conteúdo (32 mini jogos, 48 cosméticos, 13 pets, 25 móveis, reforma, clima real,
jukebox, álbum), base de mini jogo sólida (metas bronze/prata/ouro, anti-farm, partículas, tremor),
rotina diária (baú, desafio do ROBERT, bônus 1ª do dia), saves robustos, música procedural.

**Fracos (retenção):**
1. Sem progressão do ovo (nível/XP/idade) — núcleo emocional de Tamagotchi/Pou.
2. Sem conquistas globais / metas de médio prazo; cards do menu não mostram medalha.
3. Todos os jogos liberados no minuto 1 (sem descoberta).
4. Economia acaba no fim do catálogo (~33,5 mil moedas).
5. Streak do baú zerava no dia 8 (punia o jogador mais fiel) e quebrava em silêncio.
6. Onboarding mínimo.
7. SFX pobres: sem variação de tom, sem volume separado, contador de moedas mudo.
8. Nada compartilhável (foto, código, cartão).
9. Progresso diluído entre 5 ovos.

## Prioridades

### P0
- ✅ **P0.1 Nível do ovo (XP)** — XP por partida/comida/banho/baú/desafio, curva `60 + 40·n`, barra no HUD,
  celebração ao subir de nível com prêmio em moedas; idade em dias a partir de `criado_em`.
- ✅ **P0.2 Conquistas globais** com toasts em qualquer tela e tela de coleção.
- ✅ **P0.3 Liberar mini jogos aos poucos** — ovo novo começa com 8 jogos; 1 novo por nível ou INGRESSO na hora.
  Saves antigos ficam com tudo liberado (ninguém perde jogo).
- ✅ **P0.4 Streak do baú** sem zerar no dia 8, aviso de streak perdido e calendário de 7 dias.
- ✅ **P0.5 Tutorial guiado** — 5 passos com balão do ovo + seta pulsante, +10 por passo, botão PULAR.
- ✅ **P0.6 Chuva de moedas** ao voltar de um mini jogo para casa.

### P1
- ✅ **P1.1 Fim de partida recompensador** — "tic" no contador, confete no recorde, banner de medalha nova,
  "faltam X para o OURO".
- ✅ **P1.2 Cards do menu com status** — medalha, selo "+5 hoje", "!" do desafio.
- ✅ **P1.3 Missões do dia** — 2 missões sorteadas + o desafio do ROBERT; as 3 dão bônus + CAIXA SURPRESA.
- ✅ **P1.4 Caixa surpresa** com raridades + itens exclusivos (eventos/caixa/missões).
- ✅ **P1.5 Eventos** — fim de semana ×1,2; Páscoa (caça aos ovinhos no SOL), Halloween e Natal com presente exclusivo.
- ✅ **P1.6 Foto do ovo (F12)** com flash e som de obturador.
- ✅ **P1.7 Código do ovo** — AMIGOS na pausa: copiar/colar código; o amigo desfila na tela inicial e seus recordes viram desafios (+20).
- ✅ **P1.8 Áudio** — variação de tom nos SFX, volume de efeitos separado, novos SFX (tic, levelup, conquista, obturador).
- ✅ **P1.9 Transição em íris** com formato de ovo.
- ✅ **P1.10 Ovo com mais vida** — piscar e squash & stretch no pulo.
- ✅ **P1.11 Dias felizes seguidos** — bônus do OVO FELIZ sobe de ×1,10 até ×1,20.

### P2
- ✅ Novos mini jogos: Ovo Sobrevivente, Micro-Ovo, Pinball Ovo, Ovo Cozinheiro (solo) e Corrida na Rua (2P).
- ✅ Coração (afeição) dos pets; coleções (borboletas, peixes, receitas); NÍVEL DA VILA enfeitando a praça;
  abas COLEÇÕES e ESTATÍSTICAS; F11 tela cheia, reduzir tremor, mostrar FPS, cores daltônicas;
  aparência extra comprável (cores, cabelos, olhos, bocas, roupas); resumo "enquanto você estava fora".
- Não feito: remapear teclas.
- ✅ O "olho fechado" usado para dormir era o sprite de ÓCULOS ESCUROS (olho 3): agora os olhos
  fechados são desenhados de verdade (dormir e piscar). O agente achava que era um olho selecionável
  "sempre dormindo" — não era; nenhuma opção do criador foi removida.

## Economia (rebalanceada)

- Moedas por partida ~40-50% menores; jogo longo e difícil paga no máximo ~48 com todos os bônus,
  jogos rápidos ~16-25, multiplayer ~11-18. Bônus de recorde 10 -> 5; desafio do ROBERT 50 -> 40.
- Novos ralos: POÇÕES no MERCADO (sono, alegria, espuma, elixir, sorte x1,5 por 3 partidas, XP x2 por
  15 min), ingressos de jogos, caixa surpresa, aparência extra.

## Performance

- ✅ `core/janela.py`: a tela era esticada por software (`smoothscale`) todo frame (~10 ms em 1080p).
  Agora usa `pygame.SCALED` (a GPU estica, ~1 ms), com fallback para o modo antigo.
- ✅ Hóquei: giro do limão, squash dos ovos e placar pré-desenhados em cache; controle mais responsivo.
- ✅ Casa: superfícies por frame (sombra, manchas, setas, barras, anel da bola, dica) agora em cache;
  `desafio_do_dia()` tem caminho rápido (não importa os jogos nem monta conjuntos todo frame).
- ✅ Menu de jogos: não refaz as 27 miniaturas a cada volta; brilho do card em cache.
