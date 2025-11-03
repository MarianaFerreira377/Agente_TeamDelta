# Arquitetura do Sistema de Agentes em LangGraph (Versão Integrada)

O sistema é modelado como um Workflow Sequencial Condicional usando LangGraph sobre o EstadoEconomia. A arquitetura é projetada para rotear a consulta inicial para o agente de domínio correto antes de qualquer processamento:

```
$$\text{START} \xrightarrow{\text{Fixa}} \text{coordenador} \xrightarrow{\text{Condicional}} \begin{cases} \text{"economia"} \rightarrow \text{economia} \\ \text{"clima"} \rightarrow \text{clima} \\ \text{END} \end{cases}$$
```

## 1. Estado da Máquina: EstadoEconomia

O estado é uma extensão de MessagesState, projetado para acumular o histórico de conversação e armazenar metadados cruciais para o roteamento e a memória de curto prazo:

| Campo | Função Principal |
|-------|-----------------|
| messages | Histórico completo acumulado (Entrada/Saída/Ferramenta). |
| decisao_destino | Roteamento primário definido pelo Coordenador ("economia" ou "clima"). |
| tipo_tarefa | Tipo de solicitação ("pesquisa" ou "grafico"), definido pelo Coordenador. |
| ultima_cidade_processada | Usado para memória curta entre sessões. |
| cidade | Cidade extraída pelo agente de domínio ativo. |

## 2. Nó Coordenador: Roteamento Estruturado com Segurança

Este nó é o ponto de inteligência primário, focado em converter a intenção livre do usuário em uma decisão determinística:

- **Decisão Forçada (Prioridade Máxima)**: Utiliza um chain LLM configurada com PydanticOutputParser, forçando o retorno de um JSON válido (DecisaoCoordenador) para preencher destino e tipo_tarefa.

- **Roteador do Coordenador**: Verifica primeiro o campo decisao_destino. Em caso de falha, ele recorre a um Acompanhamento por Keyword (Fallback), analisando a consulta original para forçar o direcionamento ou seguir para END.

## 3. Nós de Domínio: Pesquisa (Economia/Clima) e Extração de Entidades

Estes nós utilizam o agente ReAct com ferramentas específicas.

- **Execução**: Invocam o agente com o estado completo para contextualização.

- **Extração de Cidade**: Após a execução, o nó chama a função extrair_cidade, que realiza uma correspondência de texto fixa (keyword matching) contra uma lista interna de cidades brasileiras (em minúsculas). Se houver correspondência, a cidade é retornada em Title Case e salva em cidade e ultima_cidade_processada.

## 4. Nó de Gráficos: Execução de Código Isolada

Este nó é ativado se o Coordenador ou os roteadores secundários sinalizarem a necessidade de visualização.

- **Agente**: ReAct configurado com a ferramenta python_repl_tool.

- **Isolamento de Código**: A ferramenta executa o código Python gerado pelo LLM usando exec() dentro de um namespace local isolado (self.locals), capturando a saída padrão (stdout) via redirect_stdout() para retornar o resultado ou o código gerado.

## 5. Roteamento Secundário (Tipo de Tarefa)

Os roteadores após os nós de domínio validam se o fluxo deve continuar para a visualização.

- **Prioridade**: Confiam primariamente no tipo_tarefa preenchido pelo Coordenador.

- **Fallback de Visualização**: Se o campo estiver vazio, eles usam um Acompanhamento por Keyword, escaneando a consulta original em busca de termos como "gráfico" ou "chart". O retorno é "graficos" ou END.

## 6. Ferramentas Utilizadas (Tools)

O sistema expande a capacidade do LLM com três ferramentas essenciais:

- **tavily_tool**: Permite pesquisa de fatos e dados atuais na web (ex: PIB, previsão do tempo).

- **get_current_date**: Fornece o timestamp exato da execução, crucial para contexto temporal em consultas.

- **python_repl_tool**: Habilita a execução segura (isolada via namespace) de código Python, sendo vital para a geração de gráficos e cálculos complexos.

## 7. Execução, Memória e Saída Composta

- **Streaming**: A execução usa grafo.stream() para acumular o estado passo a passo.

- **Memória Curta**: A função executar_consulta injeta a ultima_cidade_processada na consulta atual se a nova entrada for ambígua.

- **Saída Composta**: Em fluxos de gráfico, o sistema compõe a saída, exibindo a última AIMessage dos agentes de pesquisa (dados brutos) antes de mostrar o resultado final do nó graficos, garantindo transparência sobre os dados utilizados.

## 8. Limitações e Trade-offs Adotados

- **Recursão**: Limite fixo de 25 passos.

- **Segurança**: A execução de código via python_repl_tool não utiliza sandboxing externo.

- **Roteamento**: Dependência de fallback por regras/keywords em caso de falha do LLM estruturado.

- **Memória**: A persistência é limitada à cidade da consulta imediatamente anterior.
