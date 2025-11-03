import os
import json
from typing import Literal, List, Optional
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from tools import tavily_tool, python_repl_tool, print_pretty, get_current_date
from prompts import (
    criar_prompt_economia,
    criar_prompt_clima,
    criar_prompt_graficos,
)


# ============================================================================
# MODELOS PYDANTIC PARA OUTPUTS ESTRUTURADOS
# ============================================================================

class DecisaoCoordenador(BaseModel):
    """Modelo estruturado para decisão do coordenador."""
    destino: Literal["economia", "clima"] = Field(
        description="Destino do fluxo: economia ou clima"
    )
    razao: str = Field(
        description="Razão breve da decisão"
    )


# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

TOKEN = os.environ.get("GITHUB_TOKEN", "")
ENDPOINT = "https://models.github.ai/inference"
MODEL = "openai/gpt-4o-mini"

# Inicializar o LLM
llm = ChatOpenAI(
    model=MODEL,
    base_url=ENDPOINT,
    api_key=TOKEN,
    temperature=0
)

# Parser estruturado para o coordenador
parser_coordenador = PydanticOutputParser(pydantic_object=DecisaoCoordenador)

# Template do prompt do coordenador com instruções de JSON
prompt_coordenador_template = ChatPromptTemplate.from_messages([
    ("system", """Você é um COORDENADOR de um sistema multi-agente especializado em dados de cidades brasileiras.
Sua função é analisar a consulta do usuário e determinar qual agente especializado deve processar.

AGENTES DISPONÍVEIS:
- economia: para perguntas sobre PIB, desemprego, IDH, inflação, salário, economia
- clima: para perguntas sobre temperatura, chuva, precipitação, umidade, meteorologia, condições do tempo

IMPORTANTE: Responda APENAS no formato JSON especificado.

{format_instructions}"""),
    ("human", "{consulta}")
])


# ============================================================================
# ESTADO PERSONALIZADO
# ============================================================================

class EstadoEconomia(MessagesState):
    """Estado expandido para incluir informações sobre cidade e tipo de tarefa."""
    cidade: str = ""
    tipo_tarefa: str = ""  # "pesquisa" ou "grafico"
    ultima_cidade_processada: str = ""  # Para memória curta entre consultas
    

# ============================================================================
# NÓS (AGENTES)
# ============================================================================

def no_coordenador(state: EstadoEconomia) -> dict:
    """
    Nó do coordenador: decide qual agente deve processar a consulta.
    Retorna decisão estruturada via PydanticOutputParser.
    """
    print("\n[COORDENADOR] Analisando consulta...")
    
    # Extrai a última pergunta do usuário
    mensagens = state.get("messages", [])
    consulta_usuario = ""
    for msg in reversed(mensagens):
        if isinstance(msg, HumanMessage):
            consulta_usuario = msg.content
            break
    
    if not consulta_usuario:
        # Fallback
        resultado_decisa = {"destino": "economia", "razao": "Consulta vazia"}
    else:
        # Invoca o LLM com prompt estruturado
        formato_instrucoes = parser_coordenador.get_format_instructions()
        chain = prompt_coordenador_template | llm | parser_coordenador
        
        try:
            decisao = chain.invoke({
                "consulta": consulta_usuario,
                "format_instructions": formato_instrucoes
            })
            resultado_decisa = {"destino": decisao.destino, "razao": decisao.razao}
        except Exception as e:
            print(f"[COORDENADOR] Erro no parsing: {e}")
            resultado_decisa = {"destino": "economia", "razao": "Erro no parsing"}
    
    print(f"[COORDENADOR] Decisao: {resultado_decisa['destino']} - {resultado_decisa['razao']}")
    
    # Adiciona mensagem com a decisão estruturada
    nova_mensagem = AIMessage(content=json.dumps(resultado_decisa))
    estado_atualizado = {"messages": state["messages"] + [nova_mensagem]}
    
    return estado_atualizado


# Criação dos agentes de pesquisa e gráficos
agente_economia = create_react_agent(
    llm,
    tools=[tavily_tool, get_current_date],
    prompt=criar_prompt_economia(),
)

agente_clima = create_react_agent(
    llm,
    tools=[tavily_tool, get_current_date],
    prompt=criar_prompt_clima(),
)

agente_graficos = create_react_agent(
    llm,
    tools=[python_repl_tool],
    prompt=criar_prompt_graficos(),
)


def no_economia(state: EstadoEconomia) -> dict:
    """Nó do agente de economia: pesquisa dados econômicos."""
    print("[ECONOMIA] Buscando dados econômicos...")
    
    resultado = agente_economia.invoke(state)
    
    # Identifica a cidade mencionada
    cidade = extrair_cidade(state.get("messages", []))
    if cidade:
        resultado["cidade"] = cidade
        resultado["ultima_cidade_processada"] = cidade
    
    return resultado


def no_clima(state: EstadoEconomia) -> dict:
    """Nó do agente de clima: pesquisa dados climáticos."""
    print("[CLIMA] Buscando dados climáticos...")
    
    resultado = agente_clima.invoke(state)
    
    # Identifica a cidade mencionada
    cidade = extrair_cidade(state.get("messages", []))
    if cidade:
        resultado["cidade"] = cidade
        resultado["ultima_cidade_processada"] = cidade
    
    return resultado


def no_graficos(state: EstadoEconomia) -> dict:
    """Nó do agente de gráficos: gera visualizações."""
    print("[GRAFICOS] Gerando visualização...")
    
    resultado = agente_graficos.invoke(state)
    
    return resultado


# ============================================================================
# ROTEADORES
# ============================================================================

def roteador_coordenador(state: EstadoEconomia) -> Literal["economia", "clima", END]:
    """
    Roteador após o coordenador: lê a decisão JSON estruturada.
    """
    mensagens = state.get("messages", [])
    if not mensagens:
        return END
    
    # Procura pela última AIMessage do coordenador com decisão JSON
    for msg in reversed(mensagens):
        if isinstance(msg, AIMessage):
            try:
                decisao_dict = json.loads(msg.content)
                destino = decisao_dict.get("destino", "economia")
                if destino == "clima":
                    return "clima"
                elif destino == "economia":
                    return "economia"
            except (json.JSONDecodeError, AttributeError):
                continue
    
    # Fallback para keywords se JSON não encontrado
    for msg in mensagens:
        if isinstance(msg, HumanMessage):
            pergunta_original = msg.content.lower()
            
            palavras_clima = ["temperatura", "clima", "chuva", "precipitação", "umidade", "meteorologia"]
            palavras_economia = ["pib", "desemprego", "idh", "inflação", "salário", "economia"]
            
            if any(palavra in pergunta_original for palavra in palavras_clima):
                return "clima"
            elif any(palavra in pergunta_original for palavra in palavras_economia):
                return "economia"
            break
    
    # Default: economia
    return "economia"


def roteador_economia(state: EstadoEconomia) -> Literal["graficos", END]:
    """Roteador após economia: decide se deve gerar gráfico ou finalizar."""
    mensagens = state.get("messages", [])
    if not mensagens:
        return END
    
    # Verifica se a tarefa original incluía gerar gráfico
    for msg in mensagens:
        if isinstance(msg, HumanMessage):
            tarefa_original = msg.content.lower()
            deve_gerar = (
                "grafico" in tarefa_original or "gráfico" in tarefa_original or
                "chart" in tarefa_original or "graph" in tarefa_original or
                "visualizar" in tarefa_original or "histórico" in tarefa_original or
                "mostre um" in tarefa_original or "mostrar" in tarefa_original or
                "mostre" in tarefa_original
            )
            if deve_gerar:
                return "graficos"
            break
    
    return END


def roteador_clima(state: EstadoEconomia) -> Literal["graficos", END]:
    """Roteador após clima: decide se deve gerar gráfico ou finalizar."""
    mensagens = state.get("messages", [])
    if not mensagens:
        return END
    
    # Verifica se a tarefa original incluía gerar gráfico
    for msg in mensagens:
        if isinstance(msg, HumanMessage):
            tarefa_original = msg.content.lower()
            deve_gerar = (
                "grafico" in tarefa_original or "gráfico" in tarefa_original or
                "chart" in tarefa_original or "graph" in tarefa_original or
                "visualizar" in tarefa_original or "histórico" in tarefa_original or
                "mostre um" in tarefa_original or "mostrar" in tarefa_original or
                "mostre" in tarefa_original
            )
            if deve_gerar:
                return "graficos"
            break
    
    return END


def roteador_graficos(state: EstadoEconomia) -> Literal[END]:
    """Roteador após gráficos: sempre finaliza."""
    return END


# ============================================================================
# UTILITÁRIOS
# ============================================================================

def extrair_cidade(mensagens: List) -> str:
    """Extrai o nome da cidade das mensagens do usuário."""
    for msg in mensagens:
        if isinstance(msg, HumanMessage):
            conteudo = msg.content.lower()
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


# ============================================================================
# CONSTRUÇÃO DO GRAFO
# ============================================================================

def criar_grafo():
    """Constrói o grafo de estados do sistema multi-agente."""
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
        {"economia": "economia", "clima": "clima", END: END}
    )
    
    workflow.add_conditional_edges(
        "clima",
        roteador_clima,
        {"graficos": "graficos", END: END}
    )
    
    workflow.add_conditional_edges(
        "economia",
        roteador_economia,
        {"graficos": "graficos", END: END}
    )
    
    workflow.add_conditional_edges(
        "graficos",
        roteador_graficos,
        {END: END}
    )
    
    # Compila e retorna o grafo
    grafo = workflow.compile()
    return grafo


# ============================================================================
# EXECUÇÃO
# ============================================================================

def executar_consulta(consulta: str, grafo, estado_anterior=None, exibir_processo: bool = False):
    """
    Executa uma consulta com suporte a memória curta para consultas sequenciais.
    
    Args:
        consulta: Pergunta do usuário
        grafo: Grafo compilado
        estado_anterior: Estado anterior (para memória curta)
        exibir_processo: Se True, mostra debug do fluxo
    """
    # Memória curta: se consulta não menciona cidade mas última tem cidade
    consulta_modificada = consulta
    
    if estado_anterior and estado_anterior.get("ultima_cidade_processada"):
        cidade_anterior = estado_anterior.get("ultima_cidade_processada", "")
        # Verifica se consulta nova não tem cidade
        cidade_atual = extrair_cidade([HumanMessage(content=consulta)])
        if not cidade_atual and cidade_anterior:
            # Modifica a consulta para incluir cidade
            consulta_modificada = f"{consulta} em {cidade_anterior}"
    
    estado_inicial = {"messages": [HumanMessage(content=consulta_modificada)]}
    
    # Executa o grafo com streaming
    eventos = grafo.stream(
        estado_inicial,
        {"recursion_limit": 25}
    )
    
    # Processa eventos com debug visual
    resultado_final = None
    for evento in eventos:
        if exibir_processo:
            # Debug visual do fluxo
            for node_name, node_data in evento.items():
                if node_name in ["coordenador", "economia", "clima", "graficos"]:
                    print(f"  → {node_name.upper()}")
        resultado_final = evento
    
    # Retorna resultado e estado para próxima consulta (memória curta)
    novo_estado = None
    if resultado_final:
        # Extrai cidade processada do último resultado
        for node_name, node_data in resultado_final.items():
            if node_name in ["economia", "clima"]:
                # Pega cidade do estado expandido
                cidade_processada = node_data.get("cidade", "")
                if not cidade_processada:
                    cidade_processada = node_data.get("ultima_cidade_processada", "")
                
                # Se ainda não achou, tenta das mensagens
                if not cidade_processada:
                    cidade_processada = extrair_cidade(node_data.get("messages", []))
                
                if cidade_processada:
                    novo_estado = {"ultima_cidade_processada": cidade_processada}
                    break
    
    return resultado_final, novo_estado


def main():
    """Função principal com loop interativo."""
    print("\n" + "="*80)
    print("SISTEMA MULTI-AGENTE PARA DADOS DE CIDADES BRASILEIRAS")
    print("Economia e Clima")
    print("="*80)
    
    grafo = criar_grafo()
    estado_atual = None
    
    print("\nExemplos:")
    print("  - Qual e o PIB de Sao Paulo?")
    print("  - Qual a temperatura em Florianopolis?")
    print("  - Mostre um grafico do desemprego em Campinas")
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
            
            # Executa com memória curta
            resultado, estado_atual = executar_consulta(
                consulta, 
                grafo, 
                estado_atual,
                exibir_processo=False
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
            
            print()
            
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
