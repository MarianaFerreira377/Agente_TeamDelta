[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/fUqlqjxd)
[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=20982036&assignment_repo_type=AssignmentRepo)
# Agentes Baseados em LLM
Este repositório contém uma demonstração de como implementar um agente simples baseado em LLM e também um sistema multi-agentes, utilizando a biblioteca Langhchain.
O material foi criado para as aulas da disciplina "Tecnologias Emergentes em TI", dos cursos de Sistemas de Informação e Engenharia de Software, no segundo semestre de 2025.

Os arquivos desse repositório são:
- **agente_simples.py**: interface com LLM para responder perguntas simples diretamente.
- **multi_agentes.py**: 3 agentes com acesso a ferramentas de busca e execução de código python cooperam para atender um requisito do usuário.
- **economia_brasileira.py**: sistema multi-agente especializado em economia de cidades brasileiras (PROJETO DA ATIVIDADE).
- **prompts.py**: definições de texto utilizadas para contextualizar agentes.
- **tools.py**: definições das ferramentas disponíveis para os agentes da demonstração de multi-agentes.

## Langchain
Utilizamos o langchain como ferramenta de orquestração dos agentes.
O exemplo do sistema multi-agentes foi baseado na demonstração [multi-agent collaboration](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/tutorials/multi_agent/multi-agent-collaboration.ipynb).

## Github Models
https://docs.github.com/en/github-models/quickstart
https://github.com/marketplace/models/azure-openai/gpt-4-1/playground

# Instruções de Uso
1. Crie um ambiente virtual e instale as dependências do projeto:
Instruções para o linux:
```
python -m venv env
source env/bin/activate
python -m pip install --upgrade pip
python -m pip install -f requirements.txt

```
2. Exporte seu token de autenticação do Github, para poder utilizar o Github Models: ```export GITHUB_TOKEN=\"...\"```
3. Caso você utilize a busca com a ferramenta Tavily, deve exportar o token de autenticação da API também.
4. Execute o agente que deseja: 
   - ```python agente_simples.py``` (exemplo básico)
   - ```python multi_agentes.py``` (exemplo multi-agente)
   - ```python economia_brasileira.py``` (sistema de economia brasileira - PROJETO)

-----
# Atividade em Grupo

## Sistema Implementado: Multi-Agente para Economia de Cidades Brasileiras

Foi criado o arquivo **economia_brasileira.py** que implementa um sistema multi-agente especializado em responder perguntas sobre a economia de cidades brasileiras.

### Arquitetura do Sistema

O sistema possui **3 agentes especializados** que trabalham em conjunto:

1. **Agente Coordenador**: Analisa a consulta do usuário e decide qual agente deve processar a tarefa
2. **Agente de Economia**: Pesquisa dados econômicos atuais e históricos (até 5 anos) via web
3. **Agente de Gráficos**: Gera visualizações históricas usando matplotlib e seaborn

### Características

- ✅ Capaz de responder perguntas pontuais sobre economia atual
- ✅ Gera gráficos históricos de indicadores econômicos (até 5 anos)
- ✅ Pesquisa dados reais via DuckDuckGo
- ✅ Estrutura clara e bem comentada
- ✅ Prompts especializados para cada agente
- ✅ Controle de fluxo robusto usando LangGraph
- ✅ Usa modelo `openai/gpt-5-mini`

### Exemplos de Uso

```python
# Consulta sobre dados econômicos
"Qual é o PIB atual de São Paulo?"

# Consulta com gráfico histórico
"Mostre um gráfico do crescimento do PIB do Rio de Janeiro nos últimos 5 anos"

# Consulta sobre desemprego
"Qual a taxa de desemprego em Campinas nos últimos 5 anos?"
```

### Indicadores Suportados

- PIB (Produto Interno Bruto)
- PIB per capita
- Taxa de desemprego
- IDH (Índice de Desenvolvimento Humano)
- Salário médio
- Taxa de inflação
- Outros indicadores econômicos

### Fluxo de Execução

1. **Coordenador** analisa a consulta
2. **Economia** pesquisa dados econômicos
3. **Gráficos** cria visualização (se solicitado)
4. Sistema retorna resposta final ao usuário

---

## Requisitos da Atividade

Vocês deverão criar um sistema multi-agente que seja capaz de responder perguntas sobre a economia de qualquer cidade brasileira.
Seu sistema deve ser capaz de responder perguntas diretas sobre o clima com base em dados da WEB, e também criar gráficos históricos com informações sobre a economia de uma cidade determinada pelo usuário.
As perguntas irão envolver questões pontuais do momento atual, bem como visões históricas sobre a economia da cidade envolvendo no máximo o intervalo de 5 anos.

Lembre-se:
1. Escreva **bons prompts** para cada agente. Essa é a chave para um bom sistema.
2. Atenção ao **controle de fluxo** das ações entre agentes.
3. **Ajuste bem o contexto** que cada agente tem acesso.
4. **Estruture a saída** dos seus agentes se for necessário (JSON, por exemplo).
5. Mantenha o uso do modelo ```openai/gpt-5-mini```.

Serão penalizados:
- Sistemas complexos demais;
- Sistemas que alucinam muito;
- Sistemas que não resolvem casos básicos;

Para dicas mais detalhadas sobre o design de agentes, consulte os documentos referenciados abaixo:
- [Anthropic - Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI - A practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
- [12 Factor Agents - Principles for building reliable LLM applications](https://github.com/humanlayer/12-factor-agents)
