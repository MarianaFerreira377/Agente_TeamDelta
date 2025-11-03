# Implementação do Sistema Multi-Agente

## Como Funciona a Máquina de Estados

### O que é o Estado?

O estado basicamente guarda todas as informações que o sistema precisa lembrar durante a execução:

```python
class EstadoEconomia(MessagesState):
    messages: List[Message]  # Histórico de mensagens
    cidade: str = ""         # Cidade extraída
    tipo_tarefa: str = ""    # "pesquisa" ou "grafico"
    ultima_cidade_processada: str = ""  # Para memória curta
```

**messages**: É tipo um histórico da conversa. Quando você faz uma pergunta, cria uma HumanMessage. Quando um agente responde, cria uma AIMessage. Quando uma ferramenta é usada, cria uma ToolMessage. Todas ficam aqui.  
**cidade**: Quando a gente extrai qual cidade você mencionou, salva aqui.  
**tipo_tarefa**: Diz se é só pesquisa ou se precisa gerar gráfico também.  
**ultima_cidade_processada**: Guarda a última cidade pra usar na próxima consulta se você não mencionar uma nova.

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

### O Coordenador Decide de Verdade

O coordenador é diferente agora. Ele não é só decoração - ele realmente decide o fluxo usando inteligência do LLM:

```python
class DecisaoCoordenador(BaseModel):
    destino: Literal["economia", "clima"]
    razao: str
```

O coordenador usa `PydanticOutputParser` pra garantir que retorna um JSON válido sempre. O prompt dele é bem específico: deve responder com JSON contendo "destino" e "razao". 

Quando o LLM responde, o parser valida. Se estiver no formato certo, ótimo. Se não, cai no fallback (keywords).

```python
chain = prompt_coordenador_template | llm | parser_coordenador
decisao = chain.invoke({"consulta": consulta_usuario, ...})
```

Isso retorna um objeto Python válido com `destino` e `razao`. O roteador depois pega esse objeto e usa pra decidir pra onde mandar.

### Como os Roteadores Decidem?

#### Roteador do Coordenador

Esse roteador não usa mais keywords como principal. Ele lê o JSON que o coordenador retornou:

```python
for msg in reversed(mensagens):
    if isinstance(msg, AIMessage):
        decisao_dict = json.loads(msg.content)
        destino = decisao_dict.get("destino", "economia")
        if destino == "clima":
            return "clima"
        elif destino == "economia":
            return "economia"
```

Ele procura a última AIMessage, tenta fazer parse de JSON, e pega o campo "destino". Se conseguir, usa isso. Se não conseguir (não é JSON válido), cai no fallback de keywords que fica embaixo.

Fallback de keywords: mesmo que antes, verifica palavras de clima vs economia.

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
2. No coordenador: o LLM analisa, gera JSON `{"destino": "economia", "razao": "PIB é dado econômico"}`, parser valida, retorna objeto Python
3. Roteador coordenador: faz `json.loads()` da AIMessage, pega "destino": "economia", retorna `"economia"`
4. No economia: o agente de economia pega ferramentas (data atual, busca web), pesquisa, extrai que é São Paulo, salva no estado
5. Roteador economia: procura palavras de gráfico, não acha, retorna END
6. Fim! Resposta final é o que o agente de economia disse

**Exemplo 2**: "Gráfico de temperatura no Rio últimos 5 anos"

1. Começa com pergunta
2. No coordenador: LLM retorna `{"destino": "clima", "razao": "temperatura é dado climático"}`
3. Roteador coordenador: lê JSON, pega "clima"
4. No clima: pesquisa dados históricos, acha que é Rio de Janeiro, salva no estado
5. Roteador clima: acha "Gráfico", vai pra gráficos
6. No gráficos: pega os dados do clima, roda código Python com matplotlib, salva PNG
7. Roteador gráficos: sempre retorna END
8. Fim! Gráfico salvo e mensagem confirmando

### Memória Curta Entre Consultas

Cada consulta ainda é independente pro fluxo principal, MAS agora tem uma memória curta específica pra cidade:

```python
if estado_anterior and estado_anterior.get("ultima_cidade_processada"):
    cidade_anterior = estado_anterior.get("ultima_cidade_processada", "")
    cidade_atual = extrair_cidade([HumanMessage(content=consulta)])
    if not cidade_atual and cidade_anterior:
        consulta_modificada = f"{consulta} em {cidade_anterior}"
```

Se você perguntou sobre São Paulo na primeira vez e depois perguntou "qual o PIB?" sem mencionar a cidade, o sistema automaticamente adiciona "em São Paulo" na sua pergunta.

Depois de cada consulta, o sistema extrai qual cidade foi processada e salva pra próxima:

```python
for node_name, node_data in resultado_final.items():
    if node_name in ["economia", "clima"]:
        cidade_processada = node_data.get("cidade", "")
        if cidade_processada:
            novo_estado = {"ultima_cidade_processada": cidade_processada}
```

É uma memória curta porque só guarda a cidade, não todo o histórico. Evita problemas de token e deixa o sistema mais inteligente.

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

**JSON estruturado**: O coordenador sempre retorna JSON. O `PydanticOutputParser` valida antes de passar pro roteador. Se o JSON não vier no formato certo, cai no fallback de keywords. É tipo dois níveis de decisão: inteligente primeiro, regras depois.

### Casos Especiais

**Pergunta vazia**: Se não tiver mensagens, os roteadores retornam END direto.

**Cidade não encontrada**: Se não achar nenhuma cidade conhecida, o campo cidade fica vazio no estado. Os agentes ainda funcionam, só não sabem qual cidade você quis dizer.

**Pergunta ambígua**: Se o coordenador não conseguir decidir ou o JSON vier errado, usa economia como padrão.

**Ferramenta quebrada**: Se alguma ferramenta der erro, o agente recebe uma ToolMessage com o erro e pode tentar de novo ou avisar que deu problema.

**Memória curta**: Se você perguntou sobre uma cidade antes e a consulta nova não tem cidade, o sistema assume que é da mesma cidade. Funciona pra sequências tipo "qual a temperatura em SP?" depois "e o PIB?"
