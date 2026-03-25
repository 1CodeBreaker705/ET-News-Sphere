import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

models_to_test = [
    'gemini-1.5-flash-8b', 
    'gemini-1.5-flash', 
    'gemini-3.1-flash-lite',
    'gemini-2.5-flash',
    'gemini-1.5-flash-lite'
]

for m in models_to_test:
    try:
        llm = ChatGoogleGenerativeAI(model=m)
        res = llm.invoke('Hi')
        print(f"SUCCESS {m}: {res.content}")
    except Exception as e:
        print(f"FAIL {m}: {str(e)[:150]}...")
