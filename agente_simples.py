import os
from openai import OpenAI
from langgraph.graph import StateGraph, START
from langgraph.graph import MessagesState, END
from tools import print_pretty

TOKEN = os.environ["GITHUB_TOKEN"]
ENDPOINT = "https://models.github.ai/inference"
MODEL = "openai/gpt-5-mini"


def basic_assistant(question: str = "Existe PUC em Campinas?"):
    client = OpenAI(
        base_url=ENDPOINT,
        api_key=TOKEN,
    )
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "Você é um assistente pessoal geral.",
            },
            {
                "role": "user",
                "content": question,  # "Qual é a capital da Bahia?",
            },
        ],
        temperature=1.0,
        top_p=1.0,
        model=MODEL,
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    basic_assistant("Qual a universidade mais antiga do Brasil?")
