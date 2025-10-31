import os
from typing import Literal, TypedDict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from tools import tavily_tool, python_repl_tool, print_pretty, get_current_date

search_tool = tavily_tool
from prompts import (
    criar_prompt_coordenador,
    criar_prompt_economia,
    criar_prompt_clima,
    criar_prompt_graficos,
)


# Configurações
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ENDPOINT = "https://models.github.ai/inference"
MODEL = "openai/gpt-4o-mini"


# Inicializar o LLM
llm = ChatOpenAI(
    model=MODEL,
    base_url=ENDPOINT,
    api_key=TOKEN,
)


# Criação dos agentes especializados
agente_coordenador = create_react_agent(
    llm,
    tools=[],  # Coordenador não usa ferramentas diretamente
    prompt=criar_prompt_coordenador(),
)

agente_economia = create_react_agent(
    llm,
    tools=[search_tool, get_current_date],  # Pesquisa web + data atual
    prompt=criar_prompt_economia(),
)

agente_clima = create_react_agent(
    llm,
    tools=[search_tool, get_current_date],  # Pesquisa web + data atual
    prompt=criar_prompt_clima(),
)

agente_graficos = create_react_agent(
    llm,
    tools=[python_repl_tool],  # Execução de código Python para gráficos
    prompt=criar_prompt_graficos(),
)


# Estado personalizado com contexto adicional
class EstadoEconomia(MessagesState):
    """Estado expandido para incluir informações sobre cidade e tipo de tarefa."""
    cidade: str = ""
    tipo_tarefa: str = ""  # "pesquisa" ou "grafico"
    

def no_coordenador(state: EstadoEconomia) -> dict:
    """
    Nó do coordenador: decide qual agente deve processar a consulta.
    Analisa a pergunta e determina se é pesquisa de dados ou geração de gráfico.
    """
    print("\n[COORDENADOR] Analisando consulta...")
    
    resultado = agente_coordenador.invoke(state)
    
    # Mostra a resposta do coordenador
    if resultado.get("messages"):
        ultima_msg = resultado["messages"][-1]
        if hasattr(ultima_msg, 'content'):
            print(f"[COORDENADOR] Decisao: {ultima_msg.content}")
    print()  # Linha em branco para separar
    
    return resultado


def no_economia(state: EstadoEconomia) -> dict:
    """
    Nó do agente de economia: pesquisa dados sobre economia da cidade.
    Busca informações atuais e históricas (até 5 anos) de indicadores econômicos.
    """
    print("[ECONOMIA] Buscando dados econômicos...")
    
    resultado = agente_economia.invoke(state)
    
    # Identifica a cidade mencionada
    cidade = extrair_cidade(state.get("messages", []))
    if cidade:
        resultado["cidade"] = cidade
    
    return resultado


def no_clima(state: EstadoEconomia) -> dict:
    """
    Nó do agente de clima: pesquisa dados climáticos da cidade.
    Busca informações atuais e históricas (até 5 anos) sobre clima e meteorologia.
    """
    print("[CLIMA] Buscando dados climáticos...")
    
    resultado = agente_clima.invoke(state)
    
    # Identifica a cidade mencionada
    cidade = extrair_cidade(state.get("messages", []))
    if cidade:
        resultado["cidade"] = cidade
    
    return resultado


def no_graficos(state: EstadoEconomia) -> dict:
    """
    Nó do agente de gráficos: gera visualizações dos dados econômicos e climáticos.
    Cria gráficos históricos usando matplotlib/seaborn com dados de até 5 anos.
    """
    print("[GRAFICOS] Gerando visualização...")
    
    resultado = agente_graficos.invoke(state)
    
    return resultado


def roteador_coordenador(state: EstadoEconomia) -> Literal["economia", "clima", END]:
    """
    Roteador após o coordenador: decide para qual agente especializado ir.
    Detecta se a pergunta é sobre economia ou clima.
    """
    mensagens = state.get("messages", [])
    if not mensagens:
        return END
    
    # Pega a pergunta original do usuário
    pergunta_original = ""
    for msg in mensagens:
        if hasattr(msg, 'content') and isinstance(msg, HumanMessage):
            pergunta_original = msg.content.lower()
            break
    
    # Palavras-chave para clima
    palavras_clima = [
        "temperatura", "clima", "chuva", "precipitação", "umidade",
        "meteorologia", "previsão", "tempo", "estações", "verão", "inverno"
    ]
    
    # Palavras-chave para economia
    palavras_economia = [
        "pib", "desemprego", "idh", "inflação", "salário", 
        "economia", "renda", "produto interno bruto"
    ]
    
    # Detecta tipo de pergunta
    pergunta_sobre_clima = any(palavra in pergunta_original for palavra in palavras_clima)
    pergunta_sobre_economia = any(palavra in pergunta_original for palavra in palavras_economia)
    
    if pergunta_sobre_clima:
        return "clima"
    elif pergunta_sobre_economia:
        return "economia"
    
    # Default: economia
    return "economia"


def roteador_economia(state: EstadoEconomia) -> Literal["graficos", END]:
    """
    Roteador após economia: decide se deve gerar gráfico ou finalizar.
    """
    mensagens = state.get("messages", [])
    if not mensagens:
        return END
    
    # Verifica se a tarefa original incluía gerar gráfico
    tarefa_original = ""
    for msg in mensagens:
        if hasattr(msg, 'content') and isinstance(msg, HumanMessage):
            tarefa_original = msg.content.lower()
            break
    
    # Determina se deve gerar gráfico
    deve_gerar = (
        "grafico" in tarefa_original or
        "gráfico" in tarefa_original or
        "chart" in tarefa_original or
        "graph" in tarefa_original or
        "visualizar" in tarefa_original or
        "histórico" in tarefa_original or
        "mostre um" in tarefa_original or
        "mostrar" in tarefa_original or
        "mostre" in tarefa_original
    )
    
    if deve_gerar:
        return "graficos"
    
    return END


def roteador_clima(state: EstadoEconomia) -> Literal["graficos", END]:
    """
    Roteador após clima: decide se deve gerar gráfico ou finalizar.
    """
    mensagens = state.get("messages", [])
    if not mensagens:
        return END
    
    # Verifica se a tarefa original incluía gerar gráfico
    tarefa_original = ""
    for msg in mensagens:
        if hasattr(msg, 'content') and isinstance(msg, HumanMessage):
            tarefa_original = msg.content.lower()
            break
    
    # Determina se deve gerar gráfico
    deve_gerar = (
        "grafico" in tarefa_original or
        "gráfico" in tarefa_original or
        "chart" in tarefa_original or
        "graph" in tarefa_original or
        "visualizar" in tarefa_original or
        "histórico" in tarefa_original or
        "mostre um" in tarefa_original or
        "mostrar" in tarefa_original or
        "mostre" in tarefa_original
    )
    
    if deve_gerar:
        return "graficos"
    
    return END


def roteador_graficos(state: EstadoEconomia) -> Literal[END]:
    """
    Roteador após gráficos: sempre finaliza após gerar o gráfico.
    """
    return END


def extrair_cidade(mensagens: List) -> str:
    """
    Extrai o nome da cidade das mensagens do usuário.
    Retorna a primeira cidade mencionada que não seja "Brasil".
    """
    for msg in mensagens:
        if hasattr(msg, 'content') and isinstance(msg, HumanMessage):
            conteudo = msg.content.lower()
            # Lista de cidades brasileiras conhecidas
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
            for cidade in cidades:
                if cidade in conteudo:
                    return cidade.title()
    return ""


def criar_grafo():
    """
    Constrói o grafo de estados do sistema multi-agente.
    Define o fluxo de execução entre coordenador, economia, clima e gráficos.
    """
    workflow = StateGraph(EstadoEconomia)
    
    # Adiciona os nós (agentes)
    workflow.add_node("coordenador", no_coordenador)
    workflow.add_node("economia", no_economia)
    workflow.add_node("clima", no_clima)
    workflow.add_node("graficos", no_graficos)
    
    # Define o ponto de entrada
    workflow.add_edge(START, "coordenador")
    
    # Adiciona rotas condicionais
    workflow.add_conditional_edges(
        "coordenador",
        roteador_coordenador,
        {
            "economia": "economia",
            "clima": "clima",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "clima",
        roteador_clima,
        {
            "graficos": "graficos",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "economia",
        roteador_economia,
        {
            "graficos": "graficos",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "graficos",
        roteador_graficos,
        {
            END: END
        }
    )
    
    # Compila e retorna o grafo
    grafo = workflow.compile()
    return grafo


def executar_consulta(consulta: str, grafo, estado_anterior=None, exibir_processo: bool = True):
    """
    Função principal para executar uma consulta sobre dados de cidades brasileiras.
    
    Args:
        consulta: Pergunta do usuário sobre economia ou clima de uma cidade brasileira
        grafo: Grafo compilado (criado uma vez e reutilizado)
        estado_anterior: Estado anterior (não usado, cada consulta é independente)
        exibir_processo: Se True, mostra cada etapa do processo
    
    Returns:
        Resultado final do processamento e None (sem histórico)
    """
    # Cada consulta é independente, não mantém histórico
    estado_inicial = {"messages": [HumanMessage(content=consulta)]}
    
    # Executa o grafo
    eventos = grafo.stream(
        estado_inicial,
        {"recursion_limit": 25}  # Limite de 25 passos
    )
    
    # Processa os eventos
    resultado_final = None
    for evento in eventos:
        if exibir_processo:
            print_pretty(evento)
            print("-" * 80)
        resultado_final = evento
    
    # Retorna resultado e None (sem histórico entre consultas)
    return resultado_final, None


def main():
    """
    Função principal para executar consultas interativas sobre dados de cidades brasileiras.
    """
    print("\n" + "="*80)
    print("SISTEMA MULTI-AGENTE PARA DADOS DE CIDADES BRASILEIRAS")
    print("Economia e Clima")
    print("="*80)
    print("ESSE AGENTE NÃO É CAPAZ DE GUARDAR O CONTEXTO ENTRE CONSULTAS.")
    
   
    grafo = criar_grafo()
    
  
    print("\nDigite 'sair' para encerrar\n")
    
    while True:
        try:
            consulta = input("Consulta: ").strip()
            
            if consulta.lower() in ['sair', 'exit', 'quit', 'q']:
                print("\nEncerrando sistema...\n")
                break
            
            if not consulta:
                print("Por favor, digite uma consulta valida.\n")
                continue
            
            # Executa a consulta (cada consulta é independente, sem histórico)
            resultado, _ = executar_consulta(
                consulta, 
                grafo, 
                None,  # Não passa estado anterior
                exibir_processo=False  # Desativa prints detalhados
            )
            
            # Exibe apenas a resposta final
            if resultado:
                for node_name, node_data in resultado.items():
                    if "messages" in node_data:
                        ultima_msg = node_data["messages"][-1]
                        if hasattr(ultima_msg, 'content'):
                            print(f"\n{'='*80}")
                            print("RESPOSTA FINAL:")
                            print('='*80)
                            print(ultima_msg.content)
                            print('='*80)
            
            print()  # Linha em branco entre consultas
            
        except KeyboardInterrupt:
            print("\n\nEncerrando sistema...\n")
            break
        except Exception as e:
            print(f"\nErro na execucao: {e}\n")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    main()

