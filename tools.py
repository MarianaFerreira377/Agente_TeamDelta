import io
import sys
import os
from contextlib import redirect_stdout
from typing import Annotated
from datetime import datetime

from langchain_tavily import TavilySearch
from langchain_core.tools import tool


TAVILY_KEY = "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"

try:
    
    tavily_tool = TavilySearch(max_results=5, tavily_api_key=TAVILY_KEY)
    print("✓ Tavily configurado com sucesso")
except Exception as e1:
    try:
        # Se falhar, usa variável de ambiente
        os.environ["TAVILY_API_KEY"] = TAVILY_KEY
        tavily_tool = TavilySearch(max_results=5)
        print("✓ Tavily configurado via variável de ambiente")
    except Exception as e2:
        # SE TAVILY NÃO DISPONÍVEL, LANÇA EXCEÇÃO PARA QUEBRAR O CÓDIGO
        print(f"\n❌ ERRO CRÍTICO: Tavily não disponível!")
        print(f"Erro 1: {e1}")
        print(f"Erro 2: {e2}")
        print("\nTavily é obrigatório para o sistema funcionar.")
        print("Verifique a configuração da API key.\n")
        raise RuntimeError(
            "Tavily não pode ser configurado. Sistema não pode funcionar sem ele."
        ) from e2


class PythonREPL:
    """Executor simples de código Python sem dependência de langchain_experimental."""
    def __init__(self):
        self.locals = {}
        
    def run(self, command: str) -> str:
        """Executa código Python e retorna o output."""
        # Captura stdout
        f = io.StringIO()
        try:
            with redirect_stdout(f):
                exec(command, self.locals)
            output = f.getvalue()
            return output
        except Exception as e:
            return f"Erro: {str(e)}"


# Warning: This executes code locally, which can be unsafe when not sandboxed
repl = PythonREPL()


@tool
def get_current_date() -> str:
    """Retorna a data e hora atual do sistema. Use esta ferramenta quando precisar saber qual é o dia de hoje."""
    now = datetime.now()
    data_formatada = now.strftime("%A, %d de %B de %Y, %H:%M")
    # Converte para português se necessário
    dias_semana = {
        "Monday": "Segunda-feira",
        "Tuesday": "Terça-feira", 
        "Wednesday": "Quarta-feira",
        "Thursday": "Quinta-feira",
        "Friday": "Sexta-feira",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
    }
    meses = {
        "January": "Janeiro",
        "February": "Fevereiro",
        "March": "Março",
        "April": "Abril",
        "May": "Maio",
        "June": "Junho",
        "July": "Julho",
        "August": "Agosto",
        "September": "Setembro",
        "October": "Outubro",
        "November": "Novembro",
        "December": "Dezembro"
    }
    for eng, pt in dias_semana.items():
        data_formatada = data_formatada.replace(eng, pt)
    for eng, pt in meses.items():
        data_formatada = data_formatada.replace(eng, pt)
    return f"Data e hora atual: {data_formatada}"


@tool
def python_repl_tool(
    code: Annotated[str, "The python code to execute to generate your chart."],
):
    """Use this to execute python code. If you want to see the output of a value,
    you should print it out with `print(...)`. This is visible to the user."""
    try:
        result = repl.run(code)
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"
    result_str = f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"
    return (
        result_str + "\n\nIf you have completed all tasks, respond with FINAL ANSWER."
    )


def print_pretty(event):
    """Pretty-print the event messages for debugging or logging purposes.

    Args:
        event (dict): The event containing messages from any node.
    """
    # Versão simplificada - mostra apenas informações essenciais
    node_keys = ["researcher", "chart_generator", "coordenador", "economia", "clima", "graficos"]
    
    for node_key in node_keys:
        if node_key in event:
            # Mostra apenas que o nó foi executado
            return  # Não imprime nada, já que os prints estão nas funções dos nós
    
    # Se não encontrou nenhum nó conhecido
    pass
