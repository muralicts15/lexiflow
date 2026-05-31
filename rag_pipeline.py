"""
Dynamic RAG Pipeline Script
- User inputs PDF path at runtime
- Checks if PDF exists
- Splits documents
- Creates FAISS vector DB
- Queries LLM
"""

import os
import sys
import json
import re
from typing import List, Dict, Any

# Fix for Windows console encoding issues with emojis
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass

try:
    from langchain.document_loaders import PyPDFLoader
except ImportError:
    from langchain_community.document_loaders import PyPDFLoader

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from langchain.vectorstores import FAISS
except ImportError:
    from langchain_community.vectorstores import FAISS

try:
    from langchain.chains import RetrievalQA
except ImportError:
    from langchain_classic.chains import RetrievalQA

try:
    from langchain.prompts import PromptTemplate
except ImportError:
    from langchain_core.prompts import PromptTemplate

try:
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain_ollama import OllamaLLM
    OLLAMA_AVAILABLE = True
except ImportError:
    try:
        from langchain_community.llms import Ollama as OllamaLLM
        OLLAMA_AVAILABLE = True
    except ImportError:
        OLLAMA_AVAILABLE = False

# Fallback embeddings for local mode
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    HF_EMBEDDINGS_AVAILABLE = True
except ImportError:
    HF_EMBEDDINGS_AVAILABLE = False

# ---------------- RAG Pipeline ---------------- #
class RAGPipeline:
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo", use_local: bool = False):
        self.use_local = use_local
        
        if use_local:
            # Use local Ollama LLM
            if not OLLAMA_AVAILABLE:
                raise ValueError("❌ Ollama integration not available. Install: pip install ollama")
            self.llm = OllamaLLM(model=model, base_url="http://localhost:11434", temperature=0)
            
            # Use local embeddings
            if HF_EMBEDDINGS_AVAILABLE:
                self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            else:
                raise ValueError("❌ Install HuggingFace embeddings: pip install sentence-transformers")
        else:
            # Use OpenAI API
            if not OPENAI_AVAILABLE:
                raise ValueError("❌ OpenAI not available. Install: pip install langchain-openai")
            
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
            else:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("❌ OPENAI_API_KEY not set!")

            self.embeddings = OpenAIEmbeddings()
            self.llm = ChatOpenAI(model=model, temperature=0)

        self.db = None
        self.documents = []
        self.chunk_size = 500
        self.chunk_overlap = 50

    # ---------------- Load PDF ---------------- #
    def load_pdf(self, file_path: str) -> List:
        file_path = os.path.abspath(file_path)
        print(f"[PDF] Attempting to load PDF from: {file_path}")

        if not os.path.isfile(file_path):
            print(f"[ERROR] File does NOT exist at path: {file_path}")
            return []

        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = file_path
            print(f"[SUCCESS] Loaded PDF: {len(docs)} pages")
            return docs
        except Exception as e:
            print(f"[ERROR] PDF load error: {e}")
            return []

    # ---------------- Load Website ---------------- #
    def load_website(self, url: str) -> List:
        """Load content from a website URL"""
        try:
            from langchain_community.document_loaders import WebBaseLoader
            print(f"[WEB] Attempting to load website: {url}")
            
            loader = WebBaseLoader(url)
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = url
            print(f"[SUCCESS] Loaded website: {len(docs)} documents")
            return docs
        except Exception as e:
            print(f"[ERROR] Website load error: {e}")
            return []

    # ---------------- Split Documents ---------------- #
    def split_documents(self, documents: List) -> List:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        chunks = splitter.split_documents(documents)
        print(f"[SUCCESS] Split into {len(chunks)} chunks")
        return chunks

    # ---------------- Vector DB ---------------- #
    def create_vector_db(self, documents: List):
        if not documents:
            raise ValueError("[ERROR] No documents to create vector DB")
        chunks = self.split_documents(documents)
        self.documents = chunks
        self.db = FAISS.from_documents(chunks, self.embeddings)
        print(f"[SUCCESS] Vector DB created with {len(chunks)} chunks")

    def add_documents(self, documents: List) -> None:
        """Add more documents to an existing vector DB."""
        if not documents:
            return
        if self.db is None:
            self.create_vector_db(documents)
            return

        chunks = self.split_documents(documents)
        self.db.add_documents(chunks)
        self.documents.extend(chunks)
        print(f"[SUCCESS] Added {len(chunks)} chunks")

    def save_db(self, path: str = "./vector_db") -> None:
        """Persist the FAISS vector DB locally."""
        if self.db is None:
            raise ValueError("[ERROR] Vector DB not initialized")
        self.db.save_local(path)
        print(f"[SUCCESS] Vector DB saved to {path}")

    def load_db(self, path: str = "./vector_db") -> None:
        """Load a previously saved FAISS vector DB."""
        if not os.path.isdir(path):
            raise FileNotFoundError(f"[ERROR] Vector DB path not found: {path}")

        try:
            self.db = FAISS.load_local(
                path,
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
        except TypeError:
            self.db = FAISS.load_local(path, self.embeddings)

        docstore = getattr(self.db, "docstore", None)
        self.documents = list(getattr(docstore, "_dict", {}).values()) if docstore else []
        print(f"[SUCCESS] Vector DB loaded from {path}")

    def similarity_search(self, query: str, k: int = 5) -> List:
        """Return similar documents with scores."""
        if self.db is None:
            raise ValueError("[ERROR] Vector DB not initialized")
        priority_docs = self._priority_documents(query)
        priority_results = [(doc, 0.0) for doc in priority_docs]
        semantic_results = self.db.similarity_search_with_score(query, k=k)

        seen = set()
        combined = []
        for doc, score in priority_results + semantic_results:
            key = (doc.page_content, tuple(sorted(doc.metadata.items())))
            if key in seen:
                continue
            seen.add(key)
            combined.append((doc, score))
        return combined[:k]

    def _expand_support_query(self, question: str) -> str:
        """Add policy terms that improve retrieval for support-style questions."""
        lowered = question.lower()
        additions = []

        if "refund" in lowered or "return" in lowered:
            additions.append("refund policy return window calendar days delivery approved refunds")
        if "replace" in lowered or "replacement" in lowered:
            additions.append("replacement policy manufacturing defect order ID serial number")
        if "warranty" in lowered:
            additions.append("warranty coverage invoice date manufacturing defects exclusions")
        if "turning on" in lowered or "power" in lowered or "not turn on" in lowered:
            additions.append("device not turning on charge original charger hard restart technical support")
        if "login" in lowered or "password" in lowered:
            additions.append("app login issue password reset forgot password registered email")
        if "shipping" in lowered or "delivery" in lowered or "delivered" in lowered:
            additions.append("shipping delivery tracking logistics delivered order")
        if "escalate" in lowered or "human" in lowered:
            additions.append("escalation rules human support technical support billing support")

        return " ".join([question] + additions)

    def _priority_documents(self, question: str) -> List:
        """Prioritize exact policy chunks before semantic matches."""
        lowered = question.lower()
        priority_terms = []

        if "refund" in lowered or "return" in lowered:
            priority_terms = ["refund policy", "refund within", "request a refund", "approved refunds"]
        elif "replace" in lowered or "replacement" in lowered:
            priority_terms = ["replacement policy", "replacement may be offered", "manufacturing defect"]
        elif "warranty" in lowered:
            priority_terms = ["warranty coverage", "standard warranty", "warranty claims"]
        elif "turning on" in lowered or "power" in lowered or "not turn on" in lowered:
            priority_terms = ["device not turning on", "hard restart", "original charger"]
        elif "login" in lowered or "password" in lowered:
            priority_terms = ["app login issue", "forgot password", "reset the password"]
        elif "escalate" in lowered or "human" in lowered:
            priority_terms = ["escalation rules", "escalate to human", "escalate to technical"]

        if not priority_terms:
            return []

        matches = []
        for doc in self.documents:
            content = doc.page_content.lower()
            if any(term in content for term in priority_terms):
                matches.append(doc)
        return matches

    @staticmethod
    def _dedupe_documents(documents: List) -> List:
        """Deduplicate retrieved documents while preserving order."""
        seen = set()
        deduped = []
        for doc in documents:
            key = (doc.page_content, tuple(sorted(doc.metadata.items())))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(doc)
        return deduped

    @staticmethod
    def _parse_json_object(text: str) -> Dict[str, Any]:
        """Parse a JSON object from an LLM response."""
        cleaned = str(text).strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    @staticmethod
    def _normalize_agent_decision(parsed: Dict[str, Any]) -> Dict[str, Any]:
        decision = parsed.get("decision") or {}
        issue_type = str(decision.get("issue_type", "general")).lower()
        if issue_type not in {"refund", "return", "replacement", "warranty", "technical", "delivery", "billing", "general"}:
            issue_type = "general"
        if issue_type == "return":
            issue_type = "refund"

        priority = str(decision.get("priority", "Low")).title()
        if priority not in {"Low", "Medium", "High"}:
            priority = "Low"

        next_action = str(decision.get("next_action", "answer_only")).lower()
        if next_action not in {"answer_only", "ask_confirmation", "ask_image", "create_ticket", "escalate"}:
            next_action = "answer_only"

        return {
            "should_offer_complaint": bool(decision.get("should_offer_complaint", False)),
            "issue_type": issue_type,
            "priority": priority,
            "requires_image": bool(decision.get("requires_image", False)),
            "next_action": next_action,
            "reason": str(decision.get("reason", "")),
        }

    # ---------------- Query ---------------- #
    def query(self, question: str, top_k: int = 5, system_prompt: str = None) -> Dict[str, Any]:
        """Query the RAG pipeline and return answer with sources"""
        if self.db is None:
            return {"error": "Vector DB not initialized"}
        
        try:
            retrieval_query = self._expand_support_query(question)

            if system_prompt:
                priority_docs = self._priority_documents(question)
                semantic_docs = self.db.similarity_search(retrieval_query, k=max(top_k, 8))
                source_docs = self._dedupe_documents(priority_docs + semantic_docs)[:max(top_k, 8)]
                context = "\n\n".join(doc.page_content for doc in source_docs)
                customer_care_instructions = ""
                if "customer care agent" in system_prompt.lower():
                    customer_care_instructions = (
                        "For customer-care eligibility questions, compare the selected customer/order "
                        "facts from the database context against the retrieved policy. Write the main "
                        "answer as a customer-facing support reply, not as an internal log. Include the "
                        "customer name, order ID, delivery age, relevant policy window, eligibility "
                        "status, and next action when those fields are available. Do not show hidden "
                        "reasoning. Use this format:\n"
                        "Hi <name>, <clear customer-facing answer in 2-4 sentences>.\n\n"
                        "Support note: Order <order_id> was delivered <days> days ago. Decision: "
                        "<eligible/not eligible/eligible for review>. Next action: <operator action>.\n\n"
                        "If the database says the customer is inside the replacement window but "
                        "the document requires defect verification or proof, the decision is "
                        "'eligible for review', not 'not eligible'. If the database says the customer "
                        "is inside the refund window but product condition is unknown, the decision is "
                        "'eligible for review', not final approval. If the next action is escalation "
                        "or complaint creation for technical support, say that technical support will "
                        "contact the customer within 4 working days.\n\n"
                        "Do not offer complaint ticket creation only because warranty is active. "
                        "If the customer only asks about warranty status, policy, delivery age, or general "
                        "eligibility without reporting an issue or requesting an action, set "
                        "should_offer_complaint to false and next_action to answer_only.\n\n"
                        "When the customer is eligible or eligible for review and the system can create "
                        "a complaint ticket, do not tell the customer to contact support through email, "
                        "live chat, or phone. Instead, explain the eligibility and set "
                        "should_offer_complaint to true so the application can ask for ticket creation.\n\n"
                        "Return only valid JSON with this exact schema:\n"
                        "{{\n"
                        '  "answer": "customer-facing answer",\n'
                        '  "decision": {{\n'
                        '    "should_offer_complaint": true,\n'
                        '    "issue_type": "refund|replacement|warranty|technical|delivery|billing|general",\n'
                        '    "priority": "Low|Medium|High",\n'
                        '    "requires_image": true,\n'
                        '    "next_action": "answer_only|ask_confirmation|ask_image|create_ticket|escalate",\n'
                        '    "reason": "short internal reason"\n'
                        "  }}\n"
                        "}}\n"
                        "Set should_offer_complaint true when the customer is eligible, eligible for review, "
                        "or should be escalated for a support case. Set it false when the answer is only "
                        "informational or the customer is clearly not eligible. Set requires_image true for "
                        "refund, replacement, warranty, technical, and delivery damage cases when product "
                        "condition or proof is relevant.\n\n"
                    )
                prompt = PromptTemplate(
                    input_variables=["context", "question"],
                    template=(
                        f"{system_prompt}\n\n"
                        "Use only the provided system context above and the retrieved document "
                        "context below to answer. If those sources do not contain the "
                        "answer, say that the available context does not provide enough information.\n\n"
                        "Important: do not mix policy categories. For example, do not use a "
                        "replacement, warranty, or shipping period as a refund window.\n\n"
                        f"{customer_care_instructions}"
                        "Context:\n{context}\n\n"
                        "Question: {question}\n\n"
                        "Answer:"
                    ),
                )
                rendered_prompt = prompt.format(context=context, question=question)
                llm_response = self.llm.invoke(rendered_prompt)
                answer_text = getattr(llm_response, "content", llm_response)
                agent_decision = None
                if "customer care agent" in system_prompt.lower():
                    try:
                        parsed = self._parse_json_object(answer_text)
                        agent_decision = self._normalize_agent_decision(parsed)
                        answer_text = parsed.get("answer", answer_text)
                    except Exception:
                        agent_decision = None

            else:
                retriever = self.db.as_retriever(search_kwargs={"k": max(top_k, 8)})
                qa_chain = RetrievalQA.from_chain_type(
                    llm=self.llm,
                    chain_type="stuff",
                    retriever=retriever,
                    return_source_documents=True,
                )
                result = qa_chain({"query": retrieval_query})

                # Normalize response keys for both OpenAI and Ollama
                answer_text = result.get("result") or result.get("answer") or ""
                source_docs = result.get("source_documents", [])
            
            return {
                "question": question,
                "answer": answer_text if answer_text else "No answer generated. Please try again.",
                "agent_decision": agent_decision if system_prompt else None,
                "sources": [
                    {"content": doc.page_content, "metadata": doc.metadata}
                    for doc in source_docs
                ] if source_docs else []
            }
        except Exception as e:
            print(f"[ERROR] Query error: {e}")
            return {
                "error": str(e),
                "question": question,
                "answer": f"Error processing query: {str(e)}",
                "sources": []
            }

    # ---------------- Clear Data ---------------- #
    def clear(self) -> None:
        """Clear all loaded data"""
        self.db = None
        self.documents = []
        print("[SUCCESS] Cleared all data")

# ---------------- MAIN SCRIPT ---------------- #
if __name__ == "__main__":
    rag = RAGPipeline()

    # Use BlueBridge PDF from Downloads as default, or ask for input
    default_pdf = r"C:\Users\ADMIN\Downloads\BlueBridge_Logical_Reasoning_Shortcuts.pdf"
    pdf_path = default_pdf if os.path.isfile(default_pdf) else input("Enter the full path of your PDF file: ").strip()

    # Debug: show what file will be used
    print(f"📍 Using PDF: {pdf_path}")
    print(f"✅ Exists? {os.path.isfile(pdf_path)}")

    # Load PDF dynamically
    docs = rag.load_pdf(pdf_path)
    if not docs:
        print("❌ No documents loaded. Exiting.")
        exit()

    # Create vector DB and query
    rag.create_vector_db(docs)
    question = input("Enter your query about this document: ").strip()
    res = rag.query(question)
    print("\nAnswer:\n", res.get("answer"))
    print("\nSources:\n", res.get("sources"))
