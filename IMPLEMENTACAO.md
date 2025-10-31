# Implementação do Sistema Multi-Agente

## Como Funciona a Máquina de Estados

### O que é o Estado?

O estado basicamente guarda todas as informações que o sistema precisa lembrar durante a execução. Pense nele como uma "memória" temporária:

```python
class EstadoEconomia(MessagesState):
    messages: List[Message]  # Histórico de mensagens
    cidade: str = ""         # Cidade extraída
    tipo_tarefa: str = ""    # "pesquisa" ou "grafico"
```

**messages**: É tipo um histórico da conversa. Quando você faz uma pergunta, cria uma HumanMessage. Quando um agente responde, cria uma AIMessage. Quando uma ferramenta é usada, cria uma ToolMessage. Todas ficam aqui.  
**cidade**: Quando a gente extrai qual cidade você mencionou, salva aqui.  
**tipo_tarefa**: Diz se é só pesquisa ou se precisa gerar gráfico também.

### Como Identificamos Cidades?

A gente criou uma lista fixa com as principais cidades brasileiras e faz um matching simples:

```python
cidades = [
    "são paulo", "rio de janeiro", "belo horizonte", "brasília",
    "salvador", "fortaleza", "curitiba", "recife", "porto alegre",
    "goiânia", "belém", "guarulhos", "campinas", "são luís",
    "são gonçalo", "maceió", "duque de caxias", "natal",
    "teresina", "campo grande", "nova iguaçu", "são bernardo",
    "joão pessoa", "santo andré", "osasco", "jaboatão",
    "são josé dos campos", "ribeirão preto", "uberlândia",
    "contagem", "aracaju", "feira de santana", "cuiabá"
]
```

A função `extrair_cidade()` pega sua pergunta, transforma tudo em minúsculas, e procura se alguma cidade dessa lista aparece no texto. Quando acha a primeira, retorna ela formatada bonitinho (primeira letra maiúscula).

### Estrutura do Grafo

O grafo é tipo um fluxograma. Tem os nós (que são os agentes trabalhando) e as setas entre eles (que são as decisões):

```
START → coordenador → [decide] → economia OU clima
                                           ↓
                                    [decide] → graficos OU END
                                              ↓
                                            END
```

**Nós**: São as funções `no_coordenador`, `no_economia`, `no_clima`, `no_graficos`. Cada uma recebe o estado atual, faz seu trabalho, e retorna o estado atualizado.  
**Arestas fixas**: START sempre vai pro coordenador, não tem escolha.  
**Arestas condicionais**: Aqui sim tem decisão. Usa uma função roteadora que retorna uma string dizendo qual é o próximo nó, ou retorna END pra parar.

### Como os Roteadores Decidem?

#### Roteador do Coordenador

Esse é o primeiro roteador, decide se vai pra economia ou clima. Ele usa duas listas de palavras-chave:

```python
palavras_clima = ["temperatura", "clima", "chuva", "precipitação", ...]
palavras_economia = ["pib", "desemprego", "idh", "inflação", ...]
```

O que ele faz: pega sua pergunta, transforma em minúsculas, e verifica se tem alguma palavra de clima OU alguma palavra de economia. A primeira que achar, vai praquele agente. Se não achar nada, usa economia como padrão.

#### Roteadores de Economia e Clima

Depois que o agente de pesquisa termina, precisa decidir: faz gráfico ou termina? Ele verifica se na pergunta original você pediu gráfico:

```python
deve_gerar = (
    "grafico" in tarefa or "gráfico" in tarefa or
    "chart" in tarefa or "graph" in tarefa or
    "visualizar" in tarefa or "histórico" in tarefa or
    "mostre" in tarefa or "mostrar" in tarefa
)
```

Se achou alguma dessas palavras, vai pro gráficos. Senão, termina.

#### Roteador de Gráficos

Esse é simples: sempre termina depois de fazer o gráfico. Não tem condicional.

### Fluxo Completo Passo a Passo

**Exemplo 1**: "Qual o PIB de São Paulo?"

1. Começa com START, estado só tem sua pergunta em HumanMessage
2. No coordenador: o agente coordenador analisa, imprime a decisão dele, retorna o estado com a resposta dele
3. Roteador coordenador: procura "PIB" na pergunta, acha que é economia, retorna "economia"
4. No economia: o agente de economia pega ferramentas (data atual, busca web), pesquisa, extrai que é São Paulo, retorna estado atualizado
5. Roteador economia: procura palavras de gráfico, não acha, retorna END
6. Fim! Resposta final é o que o agente de economia disse

**Exemplo 2**: "Gráfico de temperatura no Rio últimos 5 anos"

1. Começa com pergunta
2. No coordenador: analisa
3. Roteador coordenador: acha "temperatura", vai pra clima
4. No clima: pesquisa dados históricos, acha que é Rio de Janeiro
5. Roteador clima: acha "Gráfico", vai pra gráficos
6. No gráficos: pega os dados do clima, roda código Python com matplotlib, salva PNG
7. Roteador gráficos: sempre retorna END
8. Fim! Gráfico salvo e mensagem confirmando

### Por que Cada Consulta é Isolada?

Quando a gente executa uma consulta, sempre começa do zero:

```python
estado_inicial = {"messages": [HumanMessage(content=consulta)]}
```

Não mantemos o histórico entre consultas diferentes. Por quê? Porque se a gente fosse acumulando mensagens, ia passar muito rápido do limite de tokens do modelo (8000) e o sistema ia quebrar. Além disso, cada pergunta é independente mesmo, não precisa saber das anteriores.

### Como o Grafo é Construído?

A gente cria o grafo uma vez só quando o sistema inicializa:

```python
workflow = StateGraph(EstadoEconomia)
workflow.add_node("coordenador", no_coordenador)
workflow.add_node("economia", no_economia)
workflow.add_node("clima", no_clima)
workflow.add_node("graficos", no_graficos)

workflow.add_edge(START, "coordenador")
workflow.add_conditional_edges("coordenador", roteador_coordenador, {...})
workflow.add_conditional_edges("economia", roteador_economia, {...})
workflow.add_conditional_edges("clima", roteador_clima, {...})
workflow.add_conditional_edges("graficos", roteador_graficos, {...})

return workflow.compile()
```

O `compile()` transforma essa definição em uma máquina de estados que pode ser executada. A gente salva esse objeto e reutiliza pra todas as consultas - não precisa criar de novo toda vez, seria muito lento.

### Detalhes Importantes

**Matching de cidades**: Não importa se você escreve "São Paulo" ou "são paulo", a gente transforma tudo em minúsculas pra comparar. "Qual o PIB de São Paulo?" vira "qual o pib de são paulo?" na comparação, aí acha no vetor.

**Default**: Quando os roteadores não sabem pra onde mandar, sempre mandam pra economia. É melhor ter uma resposta do que nenhuma.

**Limite de recursão**: Tem um limite de 25 passos no grafo, senão se der algum loop infinito o sistema ia rodar pra sempre.

### Casos Especiais

**Pergunta vazia**: Se não tiver mensagens, os roteadores retornam END direto.

**Cidade não encontrada**: Se não achar nenhuma cidade conhecida, o campo cidade fica vazio no estado. Os agentes ainda funcionam, só não sabem qual cidade você quis dizer.

**Pergunta ambígua**: Se não detectar nem economia nem clima, usa economia como padrão.

**Ferramenta quebrada**: Se alguma ferramenta der erro, o agente recebe uma ToolMessage com o erro e pode tentar de novo ou avisar que deu problema.
