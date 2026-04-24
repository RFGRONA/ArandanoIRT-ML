import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.services.chroma_service import chroma_service

class RAGService:
    def __init__(self):
        # Model for simple questions and router
        self.llm_lite = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite", 
            temperature=0
        )

        # Model for complex reasoning
        self.llm_flash = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0.1
        )
        
        self._setup_prompts()

    def _setup_prompts(self):
        prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
        
        # --- ROUTER ---
        with open(os.path.join(prompts_dir, "router_prompt.txt"), "r", encoding="utf-8") as f:
            router_template = f.read()
        self.router_prompt = PromptTemplate.from_template(router_template)

        # --- RESPONSE TEMPLATE ---
        with open(os.path.join(prompts_dir, "expert_prompt.txt"), "r", encoding="utf-8") as f:
            self.expert_template = f.read()

    def format_docs(self, docs):
        formatted = []
        for doc in docs:
            source = os.path.basename(doc.metadata.get("source", "Doc"))
            page = doc.metadata.get("page", "?")
            obs_id = doc.metadata.get("observation_id", None)
            
            content = doc.page_content.replace("\n", " ")
            if obs_id:
                formatted.append(f"--- BITÁCORA ID: {obs_id} ---\nCONTENIDO: {content}")
            else:
                formatted.append(f"--- FUENTE: {source} (Pág {page}) ---\nCONTENIDO: {content}")
        return "\n\n".join(formatted)

    def get_router_decision(self, query: str, iot_context: str) -> str:
        try:
            chain = self.router_prompt | self.llm_lite | StrOutputParser()
            decision = chain.invoke({"question": query, "iot_context": iot_context}).strip().upper()
            return "COMPLEJA" if "COMPLEJA" in decision else "SIMPLE"
        except Exception as e:
            # En caso de error, enviar al modelo más capaz por seguridad
            return "COMPLEJA"

    def process_chat(self, question: str, iot_context: str = "", expertise_level: str = "AGRONOMO"):
        # 1. Route decision
        complexity = self.get_router_decision(question, iot_context)
        selected_llm = self.llm_flash if complexity == "COMPLEJA" else self.llm_lite

        # 2. Retrieve from both collections
        papers_retriever = chroma_service.get_papers_retriever()
        logs_retriever = chroma_service.get_logs_retriever()
        
        # Manually combine for more control
        papers_docs = papers_retriever.invoke(question)
        logs_docs = logs_retriever.invoke(question)
        
        all_docs = papers_docs + logs_docs
        context_str = self.format_docs(all_docs)

        # 3. Generate response
        prompt = ChatPromptTemplate.from_template(self.expert_template)
        
        chain = prompt | selected_llm | StrOutputParser()
        
        response = chain.invoke({
            "context": context_str,
            "iot_context": iot_context if iot_context else "Sin datos IoT recientes.",
            "question": question,
            "expertise_level": expertise_level
        })
        
        sources = []
        for doc in all_docs:
            src = doc.metadata.get("source", "Bitácora")
            pg = doc.metadata.get("page", "?")
            sources.append({"source": src, "page": pg, "observation_id": doc.metadata.get("observation_id")})
            
        return {
            "answer": response,
            "model_used": "gemini-2.5-flash" if complexity == "COMPLEJA" else "gemini-2.5-flash-lite",
            "complexity": complexity,
            "sources": sources
        }

rag_service = RAGService()
