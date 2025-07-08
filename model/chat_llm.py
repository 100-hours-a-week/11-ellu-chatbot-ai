import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

llm = ChatOpenAI(
    model_name="o4-mini",
    temperature=1,
    max_tokens=4096,
    streaming=True,
    request_timeout=60,
    n=1
)