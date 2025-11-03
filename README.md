# Sistema Multi-Agente para Dados de Cidades Brasileiras

Sistema multi-agente especializado em responder perguntas sobre economia e clima de cidades brasileiras, com capacidade de gerar gráficos históricos.

## Arquitetura

O sistema possui **4 agentes especializados** que trabalham em conjunto:

1. **Agente Coordenador**: Analisa a consulta e determina qual agente processar
2. **Agente de Economia**: Pesquisa dados econômicos (PIB, desemprego, IDH, etc.)
3. **Agente de Clima**: Pesquisa dados meteorológicos (temperatura, chuva, umidade, etc.)
4. **Agente de Gráficos**: Gera visualizações históricas usando matplotlib/seaborn

## Características

- ✅ Responde perguntas sobre economia e clima de cidades brasileiras
- ✅ Gera gráficos históricos (até 5 anos)
- ✅ Pesquisa dados reais via Tavily Search API
- ✅ Anti-alucinação com regras explícitas nos prompts
- ✅ Data atual automática via tool customizada
- ✅ Máquina de estados com roteamento condicional
- ✅ Sistema interativo sem histórico entre consultas

## Instalação

1. Crie um ambiente virtual:
```bash
python -m venv env
source env/bin/activate  # Linux/Mac
# ou
env\Scripts\activate     # Windows
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
```bash
export GITHUB_TOKEN="seu_token_github"
export TAVILY_API_KEY="sua_chave_tavily"
```

## Uso

Execute o sistema:
```bash
python multi_agente.py
```

Exemplos de consultas:
```
Qual o PIB de São Paulo?
Qual a temperatura em Florianópolis?
Mostre um gráfico do desemprego em Campinas
Temperatura em Belo Horizonte nos últimos 5 anos
```

Digite `sair` para encerrar.

## Estrutura do Projeto

- `multi_agente.py`: Sistema principal com máquina de estados
- `prompts.py`: Prompts especializados para cada agente
- `tools.py`: Ferramentas (Tavily, PythonREPL, get_current_date)
- `IMPLEMENTACAO.md`: Documentação detalhada da lógica
- `agente_simples.py`: Exemplo básico de agente
- `requirements.txt`: Dependências do projeto

## Documentação

Consulte `IMPLEMENTACAO.md` para entender a lógica interna do sistema, incluindo:
- Definição do estado
- Vetor de cidades para matching
- Estrutura do grafo
- Lógica dos roteadores
- Fluxo de execução detalhado

## Requisitos

- Python 3.8+
- Token do GitHub para usar GitHub Models
- API Key do Tavily para pesquisa web
- Modelo usado: `gpt-4o-mini` (via GitHub Models)

## Referências

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Anthropic - Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI - A practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents)
