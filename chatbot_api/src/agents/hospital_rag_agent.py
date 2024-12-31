from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import (
    create_openai_functions_agent,
    Tool,
    AgentExecutor,
)
from langchain import hub
import os
import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_PATH))

from tools.wait_times import (
    get_current_wait_times,
    get_most_available_hospital,
    AvailabilityInput,
    WaitsInput
)
from chains.hospital_review_chain import reviews_vector_chain
from chains.hospital_cypher_chain import hospital_cypher_chain

HOSPITAL_AGENT_MODEL = os.getenv("HOSPITAL_AGENT_MODEL")

hospital_agent_prompt = hub.pull("hwchase17/openai-functions-agent")

# System prompt to act like a mischievous businessman
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


system_prompt = """
You are a businessperson working to attract customers to our hospital. 
If the conversation shifts towards unrelated topics, guide the discussion back smoothly to focus on our hospital and its medical services.
Maintain a fun, humorous tone while always ensuring the information shared is helpful and relevant to the hospital.
"""

system_message = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

tools = [
    Tool(
        name="Experiences",
        func=reviews_vector_chain.invoke,
        description="""Useful when you need to answer questions
        about patient experiences, feelings, or any other qualitative
        question that could be answered about a patient using semantic
        search. Not useful for answering objective questions that involve
        counting, percentages, aggregations, or listing facts. Use the
        entire prompt as input to the tool. For instance, if the prompt is
        "Are patients satisfied with their care?", the input should be
        "Are patients satisfied with their care?".
        """,
    ),
    Tool(
        name="Graph",
        func=hospital_cypher_chain.invoke,
        description="""Useful for answering questions about patients,
        physicians, hospitals, insurance payers, patient review
        statistics, and hospital visit details. Use the entire prompt as
        input to the tool. For instance, if the prompt is "How many visits
        have there been?", the input should be "How many visits have
        there been?".
        """,
    ),
    Tool(
        name="Waits",
        func=get_current_wait_times,
        description="""Use when asked about current wait times
        at a specific hospital. This tool can only get the current
        wait time at a hospital and does not have any information about
        aggregate or historical wait times. Do not pass the word "hospital"
        as input, only the hospital name itself. For example, if the prompt
        is "What is the current wait time at Jordan Inc Hospital?", the
        input should be "Jordan Inc"
        """,
        args_schema=WaitsInput
    ),
    Tool(
        name="Availability",
        func=get_most_available_hospital,
        description="""
        Use when you need to find out which hospital has the shortest
        wait time. This tool does not have any information about aggregate
        or historical wait times. This tool returns a dictionary with the
        hospital name as the key and the wait time in minutes as the value.
        """,
        args_schema=AvailabilityInput
    ),
]

chat_model = ChatGoogleGenerativeAI(
    model=HOSPITAL_AGENT_MODEL,
    temperature=0,
)

# Create chatbot memory with token limits = 300
from langchain.memory import ConversationTokenBufferMemory
from langchain.memory import ChatMessageHistory


history = ChatMessageHistory()
memory = ConversationTokenBufferMemory(
    llm=chat_model,
    memory_key="chat_history", 
    max_tokens=300,
    chat_memory=history,
    return_messages=True # Magic debug. This is very important
)

hospital_rag_agent = create_openai_functions_agent(
    llm=chat_model,
    tools=tools,
    prompt=system_message,
)

hospital_rag_agent_executor = AgentExecutor(
    agent=hospital_rag_agent,
    tools=tools,
    return_intermediate_steps=True,
    verbose=True,
    memory=memory
)