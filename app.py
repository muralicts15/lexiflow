"""
Streamlit UI for LexiFlow - Intelligent AI RAG Engine
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from customer_db import (
    clear_support_activity,
    create_email_draft,
    create_ticket,
    delete_email_draft,
    delete_ticket,
    ensure_email_draft_for_ticket,
    format_case_context,
    get_damage_inspections,
    get_dashboard_tickets,
    init_customer_db,
    log_damage_inspection,
    log_action,
    lookup_case,
    mark_email_draft_sent,
)
from damage_detection_agent import format_damage_report
from mcp_client import inspect_product_damage_via_mcp
from rag_pipeline import RAGPipeline


st.set_page_config(
    page_title="LexiFlow - AI Knowledge Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()
init_customer_db()

DEFAULT_DB_PATH = "./vector_db"
UPLOAD_DIR = Path("uploads")

ASSISTANT_PROMPTS = {
    "General Assistant": (
        "You are LexiFlow, a careful document AI assistant. Answer clearly using only "
        "the provided knowledge base. If the answer is not present in the context, say "
        "that the document does not provide enough information. Do not invent details."
    ),
    "Customer Care Agent": (
    "You are LexiFlow, a customer care agent. Help customers using only the provided "
    "company knowledge base. Write in a warm customer-support tone, directly addressing "
    "the customer as 'you'. Be polite, concise, and practical. First identify the "
    "customer's issue type when possible, then answer with clear next steps. If the "
    "knowledge base does not contain the answer, say that the issue should be escalated "
    "to a human support representative. Do not invent refund, warranty, pricing, or "
    "policy details. When the customer asks about refunds, use the refund policy section "
    "and do not substitute replacement, warranty, or shipping timelines. When customer "
    "database context is available, combine it with policy to explain eligibility. When a "
    "ticket is being created or the case is escalated to technical support, tell the "
    "customer that technical support will contact them within 4 working days."
    ),
}

SUGGESTED_QUESTIONS = [
    "Summarize the customer support policy.",
    "What issues should be escalated to human support?",
    "List refund, warranty, or service conditions mentioned.",
    "Generate 5 customer FAQs from this knowledge base.",
]

st.markdown(
    """
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMetric"] {
        background: #f7f8fa;
        border: 1px solid #e4e7ec;
        border-radius: 8px;
        padding: 0.75rem 1rem;
    }
    div[data-testid="stExpander"] {
        border-radius: 8px;
    }
    .small-muted {
        color: #667085;
        font-size: 0.9rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def init_state() -> None:
    defaults = {
        "rag_pipeline": None,
        "chat_history": [],
        "documents_loaded": False,
        "document_names": [],
        "auto_load_attempted": False,
        "last_pipeline_config": None,
        "selected_case": None,
        "last_created_ticket": None,
        "last_created_email_draft": None,
        "pending_complaint": None,
        "awaiting_image_for_pending": False,
        "damage_report": None,
        "uploaded_image_path": None,
        "question_input": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_pipeline_state() -> None:
    st.session_state.rag_pipeline = None
    st.session_state.chat_history = []
    st.session_state.documents_loaded = False
    st.session_state.document_names = []
    st.session_state.auto_load_attempted = False


def clear_uploaded_images() -> int:
    if not UPLOAD_DIR.exists():
        return 0

    deleted = 0
    for path in UPLOAD_DIR.iterdir():
        if path.is_file():
            path.unlink()
            deleted += 1
    return deleted


def ensure_pipeline(api_key: str, model: str, use_local: bool, chunk_size: int, chunk_overlap: int) -> None:
    config = (model, use_local, chunk_size, chunk_overlap)
    if st.session_state.last_pipeline_config != config:
        reset_pipeline_state()
        st.session_state.last_pipeline_config = config

    if st.session_state.rag_pipeline is not None:
        st.session_state.rag_pipeline.chunk_size = chunk_size
        st.session_state.rag_pipeline.chunk_overlap = chunk_overlap
        return

    st.session_state.rag_pipeline = RAGPipeline(api_key=api_key, model=model, use_local=use_local)
    st.session_state.rag_pipeline.chunk_size = chunk_size
    st.session_state.rag_pipeline.chunk_overlap = chunk_overlap


def try_auto_load_vector_db() -> None:
    if st.session_state.auto_load_attempted:
        return

    st.session_state.auto_load_attempted = True
    db_path = Path(DEFAULT_DB_PATH)
    if not db_path.exists() or st.session_state.rag_pipeline is None:
        return

    try:
        st.session_state.rag_pipeline.load_db(DEFAULT_DB_PATH)
        st.session_state.documents_loaded = True
        st.session_state.document_names = ["Saved knowledge base"]
        st.toast("Loaded saved vector database.")
    except Exception as exc:
        st.sidebar.warning(f"Saved DB found but could not be loaded: {exc}")


def process_pdf_files(pdf_files) -> None:
    loaded_count = 0
    for pdf_file in pdf_files:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_file.read())
                tmp_path = tmp.name

            docs = st.session_state.rag_pipeline.load_pdf(tmp_path)
            for doc in docs:
                doc.metadata["source"] = pdf_file.name

            if docs:
                if st.session_state.documents_loaded:
                    st.session_state.rag_pipeline.add_documents(docs)
                else:
                    st.session_state.rag_pipeline.create_vector_db(docs)
                    st.session_state.documents_loaded = True
                loaded_count += 1
                if pdf_file.name not in st.session_state.document_names:
                    st.session_state.document_names.append(pdf_file.name)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    if loaded_count:
        st.success(f"Processed {loaded_count} PDF file(s).")
    else:
        st.error("No PDF content could be processed.")


def process_website(url: str) -> None:
    docs = st.session_state.rag_pipeline.load_website(url)
    if not docs:
        st.error("No website content could be loaded.")
        return

    if st.session_state.documents_loaded:
        st.session_state.rag_pipeline.add_documents(docs)
    else:
        st.session_state.rag_pipeline.create_vector_db(docs)
        st.session_state.documents_loaded = True

    if url not in st.session_state.document_names:
        st.session_state.document_names.append(url)
    st.success("Website added to the knowledge base.")


def active_system_prompt(assistant_mode: str) -> str:
    if assistant_mode != "Customer Care Agent":
        return ASSISTANT_PROMPTS[assistant_mode]

    return (
        f"{ASSISTANT_PROMPTS[assistant_mode]}\n\n"
        "Customer/order database context:\n"
        f"{format_case_context(st.session_state.selected_case)}\n\n"
        "Damage detection context:\n"
        f"{format_damage_report(st.session_state.damage_report)}\n\n"
        "Use the database context for customer-specific facts such as delivery date, "
        "warranty status, order status, refund window, replacement window, and previous tickets. "
        "Use the damage detection context as uploaded image evidence when available. "
        "Use the knowledge base for support policy. If database context and policy conflict, "
        "explain the conflict and escalate to human support. For eligibility questions, reason "
        "step by step internally from the policy and database context, then give a concise final "
        "answer that mentions the customer name, order ID, delivery age, relevant policy window, "
        "eligibility status, and next action."
    )


def ask_question(question: str, top_k: int, assistant_mode: str) -> None:
    if not question.strip():
        return

    if handle_pending_complaint_confirmation(question):
        return

    response = st.session_state.rag_pipeline.query(
        question.strip(),
        top_k=top_k,
        system_prompt=active_system_prompt(assistant_mode),
    )
    answer = response.get("answer", "")
    agent_decision = response.get("agent_decision") or {}

    actionable_question = question_requests_support_action(question)
    fallback_offer = actionable_question and should_offer_complaint(answer, assistant_mode)
    should_offer = bool(agent_decision.get("should_offer_complaint")) or fallback_offer
    if not actionable_question:
        should_offer = False

    if should_offer:
        issue_type = agent_decision.get("issue_type")
        if not issue_type or issue_type == "general" or fallback_offer:
            issue_type = infer_issue_type(question + " " + answer)
        priority = agent_decision.get("priority") or priority_for_issue(issue_type)
        eligible, eligibility_message = evaluate_ticket_eligibility(issue_type, st.session_state.selected_case)
        if eligible:
            st.session_state.pending_complaint = {
                "issue_type": issue_type,
                "priority": priority,
                "requires_image": issue_requires_image(issue_type),
                "agent_reason": agent_decision.get("reason", ""),
                "summary": build_complaint_summary(question.strip(), answer, st.session_state.selected_case),
            }
            st.session_state.awaiting_image_for_pending = False
            answer = (
                f"{answer}\n\n"
                "Would you like me to create a ticket for this request?"
            )
        else:
            answer = f"{answer}\n\nSupport note: {eligibility_message}"

    st.session_state.chat_history.append(
        {
            "question": question.strip(),
            "answer": answer,
            "sources": response.get("sources", []),
            "mode": assistant_mode,
            "case": st.session_state.selected_case,
        }
    )


def render_sources(sources) -> None:
    if not sources:
        st.caption("No source chunks returned.")
        return

    for index, source in enumerate(sources, 1):
        content = source.get("content", "") if isinstance(source, dict) else getattr(source, "page_content", "")
        metadata = source.get("metadata", {}) if isinstance(source, dict) else getattr(source, "metadata", {})
        source_name = metadata.get("source", "Document")
        page = metadata.get("page", "N/A")
        with st.expander(f"Source {index}: {source_name} | Page {page}"):
            st.write(content)


def refresh_selected_case() -> None:
    case = st.session_state.selected_case
    if case:
        st.session_state.selected_case = lookup_case(case["order_id"])


def create_complaint(issue_type: str, priority: str, summary: str) -> None:
    case = st.session_state.selected_case
    if not case:
        st.error("Select a customer/order before creating a ticket.")
        return

    ticket = create_ticket(
        customer_id=case["customer_id"],
        order_id=case["order_id"],
        issue_type=issue_type,
        priority=priority,
        summary=summary,
    )
    log_action(
        action="create_ticket",
        detail=f"Created {ticket['ticket_id']} with issue={issue_type}, priority={priority}.",
        customer_id=case["customer_id"],
        order_id=case["order_id"],
        reference_id=ticket["ticket_id"],
    )
    st.session_state.last_created_ticket = ticket
    draft = create_email_draft_for_ticket(ticket, case, issue_type)
    st.session_state.last_created_email_draft = draft
    refresh_selected_case()
    st.session_state.chat_history.append(
        {
            "question": "Create ticket",
            "answer": (
                f"Ticket {ticket['ticket_id']} created for order {case['order_id']}.\n\n"
                f"Status: {ticket['status']}\n\n"
                f"Priority: {ticket['priority']}\n\n"
                f"Summary: {ticket['summary']}\n\n"
                f"Email draft {draft['draft_id']} created for {draft['recipient']}."
            ),
            "sources": [],
            "mode": "Support Action",
            "case": st.session_state.selected_case,
        }
    )


def issue_requires_image(issue_type: str) -> bool:
    return issue_type in {"refund", "replacement", "warranty", "technical", "delivery"}


def save_uploaded_image(uploaded_file, case: dict) -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name).suffix.lower() or ".jpg"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{case['order_id']}_{timestamp}{suffix}"
    path = UPLOAD_DIR / filename
    path.write_bytes(uploaded_file.getbuffer())
    return str(path)


def inspect_uploaded_image(uploaded_file) -> None:
    case = st.session_state.selected_case
    if not case:
        st.error("Select a customer/order before uploading an image.")
        return

    image_path = save_uploaded_image(uploaded_file, case)
    report = inspect_product_damage_via_mcp(
        image_path=image_path,
        image_url=image_path,
        order_id=case["order_id"],
    )
    st.session_state.uploaded_image_path = image_path
    st.session_state.damage_report = report
    log_action(
        action="damage_inspection",
        detail=(
            f"Image inspected. Status={report.get('inspection_status')}, "
            f"damage={report.get('damage_detected')}, severity={report.get('severity')}, "
            f"confidence={report.get('confidence')}, source={report.get('source')}."
        ),
        customer_id=case["customer_id"],
        order_id=case["order_id"],
        reference_id=Path(image_path).name,
    )
    log_damage_inspection(
        report=report,
        customer_id=case["customer_id"],
        order_id=case["order_id"],
    )
    st.success("Damage Detection Agent inspected the uploaded image.")


def create_email_draft_for_ticket(ticket: dict, case: dict, issue_type: str) -> dict:
    subject = f"Ticket {ticket['ticket_id']} created for order {case['order_id']}"
    body = (
        f"Hi {case['name']},\n\n"
        f"We have created ticket {ticket['ticket_id']} for your order "
        f"{case['order_id']} ({case['product_name']}).\n\n"
        f"Issue type: {issue_type}\n"
        f"Priority: {ticket['priority']}\n"
        f"Status: {ticket['status']}\n\n"
        "Our technical support team will contact you within 4 working days. "
        "Please keep any photos, videos, serial number, and purchase proof ready if requested.\n\n"
        "Regards,\n"
        "LexiFlow Support"
    )
    draft = create_email_draft(
        customer_id=case["customer_id"],
        order_id=case["order_id"],
        ticket_id=ticket["ticket_id"],
        recipient=case["email"],
        subject=subject,
        body=body,
    )
    log_action(
        action="create_email_draft",
        detail=f"Created email draft {draft['draft_id']} for ticket {ticket['ticket_id']}.",
        customer_id=case["customer_id"],
        order_id=case["order_id"],
        reference_id=draft["draft_id"],
    )
    return draft


def backfill_missing_email_drafts() -> None:
    case = st.session_state.selected_case
    if not case or not case.get("tickets"):
        return

    existing_ticket_ids = {
        draft.get("ticket_id")
        for draft in case.get("email_drafts", [])
        if draft.get("ticket_id")
    }
    created = False
    for ticket in case["tickets"]:
        if ticket["ticket_id"] in existing_ticket_ids:
            continue
        draft = ensure_email_draft_for_ticket(
            ticket_id=ticket["ticket_id"],
            customer_id=case["customer_id"],
            order_id=case["order_id"],
            recipient=case["email"],
            subject=f"Ticket {ticket['ticket_id']} created for order {case['order_id']}",
            body=(
                f"Hi {case['name']},\n\n"
                f"We have created ticket {ticket['ticket_id']} for your order "
                f"{case['order_id']} ({case['product_name']}).\n\n"
                f"Issue type: {ticket['issue_type']}\n"
                f"Priority: {ticket['priority']}\n"
                f"Status: {ticket['status']}\n\n"
                "Our technical support team will contact you within 4 working days.\n\n"
                "Regards,\nLexiFlow Support"
            ),
        )
        log_action(
            action="create_email_draft",
            detail=f"Backfilled email draft {draft['draft_id']} for ticket {ticket['ticket_id']}.",
            customer_id=case["customer_id"],
            order_id=case["order_id"],
            reference_id=draft["draft_id"],
        )
        created = True

    if created:
        refresh_selected_case()


def remove_ticket(ticket_id: str) -> None:
    case = st.session_state.selected_case
    if delete_ticket(ticket_id):
        if case:
            log_action(
                action="delete_ticket",
                detail=f"Deleted ticket {ticket_id}.",
                customer_id=case["customer_id"],
                order_id=case["order_id"],
                reference_id=ticket_id,
            )
        refresh_selected_case()
        if st.session_state.last_created_ticket and st.session_state.last_created_ticket["ticket_id"] == ticket_id:
            st.session_state.last_created_ticket = None
        st.success(f"Deleted ticket {ticket_id}.")
    else:
        st.warning(f"Ticket {ticket_id} was not found.")


def remove_email_draft(draft_id: str) -> None:
    case = st.session_state.selected_case
    if delete_email_draft(draft_id):
        if case:
            log_action(
                action="delete_email_draft",
                detail=f"Deleted email draft {draft_id}.",
                customer_id=case["customer_id"],
                order_id=case["order_id"],
                reference_id=draft_id,
            )
        refresh_selected_case()
        if (
            st.session_state.last_created_email_draft
            and st.session_state.last_created_email_draft["draft_id"] == draft_id
        ):
            st.session_state.last_created_email_draft = None
        st.success(f"Deleted email draft {draft_id}.")
    else:
        st.warning(f"Email draft {draft_id} was not found.")


def mark_draft_sent(draft_id: str) -> None:
    case = st.session_state.selected_case
    if mark_email_draft_sent(draft_id):
        if case:
            log_action(
                action="mark_email_sent",
                detail=f"Marked email draft {draft_id} as sent.",
                customer_id=case["customer_id"],
                order_id=case["order_id"],
                reference_id=draft_id,
            )
        refresh_selected_case()
        if (
            st.session_state.last_created_email_draft
            and st.session_state.last_created_email_draft["draft_id"] == draft_id
        ):
            st.session_state.last_created_email_draft["status"] = "Sent"
        st.success(f"Marked email draft {draft_id} as sent.")
    else:
        st.warning(f"Email draft {draft_id} was not found.")


def infer_issue_type(text: str) -> str:
    lowered = text.lower()
    if "turning on" in lowered or "technical" in lowered or "not working" in lowered:
        return "technical"
    if "refund" in lowered or "return" in lowered:
        return "refund"
    if "replacement" in lowered or "replace" in lowered:
        return "replacement"
    if "warranty" in lowered:
        return "warranty"
    if "delivery" in lowered or "shipping" in lowered or "delivered" in lowered:
        return "delivery"
    if "payment" in lowered or "billing" in lowered or "invoice" in lowered:
        return "billing"
    return "general"


def priority_for_issue(issue_type: str) -> str:
    if issue_type in {"technical", "replacement", "delivery"}:
        return "High"
    if issue_type in {"refund", "warranty", "billing"}:
        return "Medium"
    return "Low"


def evaluate_ticket_eligibility(issue_type: str, case: dict) -> tuple[bool, str]:
    if not case:
        return False, "Select a customer/order before creating a ticket."

    days = int(case.get("delivery_days_ago", 9999))
    issue_type = (issue_type or "general").lower()

    if issue_type == "refund":
        if days <= 14:
            return True, "Refund ticket is allowed because the order is inside the 14 calendar day refund window."
        return (
            False,
            f"Refund ticket is not created automatically because order {case['order_id']} was delivered "
            f"{days} days ago, which is outside the 14 calendar day refund window.",
        )

    if issue_type in {"replacement", "technical"}:
        if days <= 30:
            return True, (
                f"{issue_type.title()} ticket is allowed because the order is inside the "
                "30 calendar day review window."
            )
        return (
            False,
            f"{issue_type.title()} ticket is not created automatically because order {case['order_id']} "
            f"was delivered {days} days ago, which is outside the 30 calendar day review window. "
            "No automatic ticket is available for this request.",
        )

    if issue_type == "warranty":
        return False, "Warranty questions are handled as informational answers. No automatic ticket is created."

    if issue_type == "delivery":
        if days <= 7:
            return True, "Delivery ticket is allowed because the order is inside the 7 calendar day delivery issue window."
        return (
            False,
            f"Delivery ticket is not created automatically because order {case['order_id']} was delivered "
            f"{days} days ago, which is outside the 7 calendar day delivery issue window.",
        )

    if issue_type == "billing":
        return True, "Billing ticket is allowed for payment or invoice review."

    return False, "No automatic ticket is created for general or informational questions."


def is_confirmation(message: str) -> bool:
    normalized = message.strip().lower()
    confirmations = {
        "yes",
        "yes please",
        "ok",
        "okay",
        "confirm",
        "confirmed",
        "go ahead",
        "create complaint",
        "create ticket",
        "please create",
        "proceed",
    }
    return normalized in confirmations or normalized.startswith("yes,")


def is_rejection(message: str) -> bool:
    normalized = message.strip().lower()
    return normalized in {"no", "not now", "cancel", "do not create", "dont create", "don't create"}


def should_offer_complaint(answer: str, assistant_mode: str) -> bool:
    if assistant_mode != "Customer Care Agent" or not st.session_state.selected_case:
        return False

    lowered = answer.lower()
    active_issue_signals = [
        "not working",
        "not turning on",
        "turning on",
        "refund",
        "return",
        "replacement",
        "replace",
        "damaged",
        "damage",
        "defect",
        "complaint",
        "ticket",
        "support case",
        "escalate",
        "issue",
        "problem",
    ]
    positive_signals = [
        "eligible for review",
        "eligible to return",
        "eligible for a return",
        "eligible for refund",
        "eligible for a refund",
        "eligible to request a refund",
        "eligible to request refund",
        "within the 14",
        "within 14",
        "14 calendar days",
        "within the 30",
        "within 30",
        "30 calendar days",
        "to proceed with the refund",
        "proceed with the refund",
        "start the return process",
        "escalate",
        "technical support",
        "technical support case",
        "open a technical support case",
        "open a support case",
        "support case",
    ]
    negative_signals = [
        "not eligible",
        "outside the 14",
        "outside the 30",
        "does not provide enough information",
    ]
    if not any(signal in lowered for signal in active_issue_signals):
        return False

    return any(signal in lowered for signal in positive_signals) and not any(signal in lowered for signal in negative_signals)


def question_requests_support_action(question: str) -> bool:
    lowered = question.lower()
    action_signals = [
        "refund",
        "return",
        "replace",
        "replacement",
        "not working",
        "not turning on",
        "does not work",
        "stopped working",
        "broken",
        "damaged",
        "damage",
        "defect",
        "complaint",
        "ticket",
        "claim",
        "raise",
        "escalate",
        "issue",
        "problem",
        "repair",
        "fix",
    ]
    informational_warranty_signals = [
        "warranty active",
        "warranty status",
        "under warranty",
        "warranty period",
        "what does warranty",
        "what is warranty",
        "is warranty",
    ]

    if any(signal in lowered for signal in action_signals):
        return True
    if "warranty" in lowered and any(signal in lowered for signal in informational_warranty_signals):
        return False
    return False


def build_complaint_summary(question: str, answer: str, case: dict) -> str:
    return (
        f"Customer request for order {case['order_id']} ({case['product_name']}). "
        f"Customer question: {question}. Agent response: {answer}"
    )[:1000]


def handle_pending_complaint_confirmation(message: str) -> bool:
    pending = st.session_state.pending_complaint
    if not pending:
        return False

    if is_rejection(message):
        st.session_state.pending_complaint = None
        st.session_state.awaiting_image_for_pending = False
        st.session_state.chat_history.append(
            {
                "question": message.strip(),
                "answer": "No ticket was created. I can still help with the next step if needed.",
                "sources": [],
                "mode": "Support Action",
                "case": st.session_state.selected_case,
            }
        )
        return True

    if not is_confirmation(message):
        return False

    if pending_requires_image(pending) and not st.session_state.damage_report:
        st.session_state.awaiting_image_for_pending = True
        st.session_state.chat_history.append(
            {
                "question": message.strip(),
                "answer": (
                    "Before I create the ticket, please upload a product image. "
                    f"This {pending['issue_type']} case requires image proof. I will pass it to "
                    "the Damage Detection Agent for inspection, then you can confirm again."
                ),
                "sources": [],
                "mode": "Support Action",
                "case": st.session_state.selected_case,
            }
        )
        return True

    create_complaint(
        issue_type=pending["issue_type"],
        priority=pending["priority"],
        summary=pending["summary"],
    )
    st.session_state.pending_complaint = None
    st.session_state.awaiting_image_for_pending = False
    return True


def create_pending_complaint_from_image() -> None:
    pending = st.session_state.pending_complaint
    if not pending:
        st.warning("No pending ticket is waiting for image proof.")
        return
    if pending_requires_image(pending) and not st.session_state.damage_report:
        st.warning("Upload and inspect a product image first.")
        return

    report = st.session_state.damage_report or {}
    summary = (
        f"{pending['summary']} Damage inspection: status={report.get('inspection_status')}, "
        f"damage_detected={report.get('damage_detected')}, type={report.get('damage_type')}, "
        f"severity={report.get('severity')}, confidence={report.get('confidence')}, "
        f"recommendation={report.get('recommendation')}, image={report.get('image_url')}, "
        f"notes={report.get('notes')}"
    )[:1000]
    create_complaint(
        issue_type=pending["issue_type"],
        priority=pending["priority"],
        summary=summary,
    )
    st.session_state.pending_complaint = None
    st.session_state.awaiting_image_for_pending = False


def pending_requires_image(pending: dict) -> bool:
    if not pending:
        return False
    return bool(pending.get("requires_image", issue_requires_image(pending["issue_type"])))


def render_customer_lookup_sidebar() -> None:
    st.subheader("Customer Lookup")
    lookup_value = st.text_input("Email, phone, or order ID", placeholder="ORD-1001")
    if st.button("Lookup Customer", disabled=not lookup_value.strip(), use_container_width=True):
        st.session_state.selected_case = lookup_case(lookup_value)
        st.session_state.pending_complaint = None
        st.session_state.awaiting_image_for_pending = False
        st.session_state.damage_report = None
        st.session_state.uploaded_image_path = None
        if st.session_state.selected_case:
            case = st.session_state.selected_case
            log_action(
                action="customer_lookup",
                detail=f"Loaded customer/order using identifier {lookup_value}.",
                customer_id=case["customer_id"],
                order_id=case["order_id"],
                reference_id=lookup_value,
            )
            st.success("Customer loaded")
        else:
            st.warning("No matching customer/order found")

    sample_lookup_cols = st.columns(3)
    for col, sample_id in zip(sample_lookup_cols, ["ORD-1001", "ORD-1002", "ORD-1003"]):
        if col.button(sample_id, use_container_width=True):
            st.session_state.selected_case = lookup_case(sample_id)
            st.session_state.pending_complaint = None
            st.session_state.awaiting_image_for_pending = False
            st.session_state.damage_report = None
            st.session_state.uploaded_image_path = None
            if st.session_state.selected_case:
                case = st.session_state.selected_case
                log_action(
                    action="customer_lookup",
                    detail=f"Loaded sample customer/order {sample_id}.",
                    customer_id=case["customer_id"],
                    order_id=case["order_id"],
                    reference_id=sample_id,
                )
            st.rerun()

    if st.session_state.selected_case:
        case = st.session_state.selected_case
        st.markdown(f"**{case['name']}**")
        st.caption(f"{case['order_id']} | {case['product_name']}")
        st.caption(
            f"Delivered {case['delivery_days_ago']} days ago | "
            f"Refund: {case['refund_window_status'].replace('_', ' ')} | "
            f"Replacement: {case['replacement_window_status'].replace('_', ' ')}"
        )
        if st.button("Clear customer", use_container_width=True):
            st.session_state.selected_case = None
            st.session_state.pending_complaint = None
            st.session_state.awaiting_image_for_pending = False
            st.session_state.damage_report = None
            st.session_state.uploaded_image_path = None
            st.rerun()


def render_knowledge_base_sidebar() -> None:
    st.subheader("Knowledge Base")
    st.caption(
        f"{'Ready' if st.session_state.documents_loaded else 'Empty'} | "
        f"{len(st.session_state.rag_pipeline.documents) if st.session_state.rag_pipeline else 0} chunks | "
        f"{len(st.session_state.document_names)} sources"
    )

    pdf_files = st.file_uploader(
        "Upload Business Rules documents",
        type="pdf",
        accept_multiple_files=True,
        help="Add FAQs, refund policies, warranty documents, manuals, or troubleshooting guides.",
    )
    if st.button("Process PDFs", type="primary", disabled=not pdf_files, use_container_width=True):
        with st.spinner("Indexing PDF content..."):
            process_pdf_files(pdf_files)
        st.rerun()

    with st.expander("Website and DB tools", expanded=False):
        website_url = st.text_input("Add website URL", placeholder="https://example.com")
        if st.button("Load Website", disabled=not website_url, use_container_width=True):
            with st.spinner("Loading website content..."):
                process_website(website_url)
            st.rerun()

        db_path = st.text_input("Vector DB path", value=DEFAULT_DB_PATH)
        save_col, load_col = st.columns(2)
        if save_col.button("Save DB", disabled=not st.session_state.documents_loaded, use_container_width=True):
            st.session_state.rag_pipeline.save_db(db_path)
            st.success("Saved vector database.")
        if load_col.button("Load DB", use_container_width=True):
            st.session_state.rag_pipeline.load_db(db_path)
            st.session_state.documents_loaded = True
            if "Saved knowledge base" not in st.session_state.document_names:
                st.session_state.document_names.append("Saved knowledge base")
            st.rerun()

    with st.expander("Loaded sources", expanded=False):
        if st.session_state.document_names:
            for name in st.session_state.document_names:
                st.write(f"- {name}")
        else:
            st.caption("No documents loaded yet.")


def render_operations_dashboard() -> None:
    tickets = get_dashboard_tickets()
    inspections = get_damage_inspections(limit=50)

    open_tickets = [ticket for ticket in tickets if ticket["status"].lower() == "open"]
    high_priority = [ticket for ticket in tickets if ticket["priority"].lower() == "high"]
    damaged = [inspection for inspection in inspections if inspection["damage_detected"]]
    human_review = [inspection for inspection in inspections if inspection["needs_human_review"]]

    metric_cols = st.columns(5)
    metric_cols[0].metric("Tickets", len(tickets))
    metric_cols[1].metric("Open", len(open_tickets))
    metric_cols[2].metric("High Priority", len(high_priority))
    metric_cols[3].metric("Inspections", len(inspections))
    metric_cols[4].metric("Human Review", len(human_review))

    ticket_tab, inspection_tab = st.tabs(["Tickets", "Image Inspections"])

    with ticket_tab:
        if not tickets:
            st.caption("No tickets created yet.")
        else:
            status_filter = st.radio("Case status", ["All", "Open", "Closed"], horizontal=True)
            filtered_tickets = tickets
            if status_filter != "All":
                filtered_tickets = [
                    ticket for ticket in tickets if ticket["status"].lower() == status_filter.lower()
                ]
            st.dataframe(
                [
                    {
                        "Ticket": ticket["ticket_id"],
                        "Customer": ticket["customer_name"],
                        "Order": ticket["order_id"],
                        "Product": ticket["product_name"],
                        "Issue": ticket["issue_type"],
                        "Status": ticket["status"],
                        "Priority": ticket["priority"],
                        "Created": ticket["created_at"],
                        "Summary": ticket["summary"],
                    }
                    for ticket in filtered_tickets
                ],
                use_container_width=True,
                hide_index=True,
            )

    with inspection_tab:
        if not inspections:
            st.caption("No image inspections yet.")
        else:
            severity_filter = st.radio(
                "Inspection severity",
                ["All", "high", "medium", "low", "unknown"],
                horizontal=True,
            )
            filtered_inspections = inspections
            if severity_filter != "All":
                filtered_inspections = [
                    inspection
                    for inspection in inspections
                    if inspection["severity"].lower() == severity_filter
                ]
            st.dataframe(
                [
                    {
                        "Created": inspection["created_at"],
                        "Customer": inspection.get("customer_name") or "Unknown",
                        "Order": inspection.get("order_id") or "N/A",
                        "Product": inspection.get("product_name") or "N/A",
                        "Damage": "Yes" if inspection["damage_detected"] else "No",
                        "Type": inspection["damage_type"],
                        "Severity": inspection["severity"],
                        "Confidence": inspection["confidence"],
                        "Human Review": "Yes" if inspection["needs_human_review"] else "No",
                        "Source": inspection["source"],
                        "Model": inspection["model"],
                        "Image": inspection["image_url"],
                        "Notes": inspection["notes"],
                    }
                    for inspection in filtered_inspections
                ],
                use_container_width=True,
                hide_index=True,
            )
            if damaged:
                st.caption(f"{len(damaged)} inspection(s) detected visible damage.")


def render_active_customer_context() -> None:
    if not st.session_state.selected_case:
        st.info("Select a customer from the sidebar to load customer context.")
        return

    case = st.session_state.selected_case
    with st.expander("Active customer context", expanded=True):
        info_cols = st.columns(4)
        info_cols[0].metric("Customer", case["name"])
        info_cols[1].metric("Order", case["order_id"])
        info_cols[2].metric("Delivered", f"{case['delivery_days_ago']} days ago")
        info_cols[3].metric("Warranty", case["warranty_status"])
        st.caption(
            f"Product: {case['product_name']} | Serial: {case['serial_number']} | "
            f"Refund window: {case['refund_window_status'].replace('_', ' ')} | "
            f"Replacement window: {case['replacement_window_status'].replace('_', ' ')}"
        )
        record_cols = st.columns(3)
        record_cols[0].metric("Tickets", len(case.get("tickets", [])))
        record_cols[1].metric("Email Drafts", len(case.get("email_drafts", [])))
        record_cols[2].metric("Audit Events", len(case.get("audit_logs", [])))


def render_selected_customer_records() -> None:
    if not st.session_state.selected_case:
        st.caption("Select a customer to manage support records.")
        return

    case = st.session_state.selected_case
    ticket_tab, draft_tab, audit_tab = st.tabs(["Tickets", "Email Drafts", "Audit"])

    with ticket_tab:
        if case.get("tickets"):
            st.dataframe(
                [
                    {
                        "Ticket": ticket["ticket_id"],
                        "Issue": ticket["issue_type"],
                        "Status": ticket["status"],
                        "Priority": ticket["priority"],
                        "Created": ticket["created_at"],
                        "Summary": ticket["summary"],
                    }
                    for ticket in case["tickets"]
                ],
                use_container_width=True,
                hide_index=True,
                height=180,
            )
            ticket_id = st.selectbox(
                "Ticket to delete",
                [ticket["ticket_id"] for ticket in case["tickets"]],
                key="admin_ticket_to_delete",
            )
            if st.button("Delete Ticket", key=f"admin_delete_{ticket_id}"):
                remove_ticket(ticket_id)
                st.rerun()
        else:
            st.caption("No tickets for this customer/order.")

    with draft_tab:
        if case.get("email_drafts"):
            selected_draft_id = st.selectbox(
                "Email draft",
                [draft["draft_id"] for draft in case["email_drafts"]],
                key="admin_email_draft",
            )
            selected_draft = next(
                draft for draft in case["email_drafts"] if draft["draft_id"] == selected_draft_id
            )
            st.caption(
                f"To: {selected_draft['recipient']} | "
                f"Ticket: {selected_draft.get('ticket_id') or 'N/A'} | "
                f"Status: {selected_draft['status']}"
            )
            st.text_area(
                "Email body",
                value=selected_draft["body"],
                height=120,
                key=f"admin_body_{selected_draft_id}",
                disabled=True,
            )
            sent_col, delete_col = st.columns(2)
            if sent_col.button(
                "Mark Sent",
                key=f"admin_sent_{selected_draft_id}",
                disabled=selected_draft["status"] == "Sent",
                use_container_width=True,
            ):
                mark_draft_sent(selected_draft_id)
                st.rerun()
            if delete_col.button("Delete Draft", key=f"admin_delete_draft_{selected_draft_id}", use_container_width=True):
                remove_email_draft(selected_draft_id)
                st.rerun()
        else:
            st.caption("No email drafts for this customer/order.")

    with audit_tab:
        if case.get("audit_logs"):
            st.dataframe(
                [
                    {
                        "Time": log["created_at"],
                        "Action": log["action"],
                        "Reference": log.get("reference_id") or "",
                        "Detail": log["detail"],
                    }
                    for log in case["audit_logs"]
                ],
                use_container_width=True,
                hide_index=True,
                height=180,
            )
        else:
            st.caption("No audit events for this customer/order.")


def render_image_detection_agent(key_prefix: str, expanded: bool = False) -> None:
    if not st.session_state.selected_case:
        st.caption("Select a customer before inspecting a product image.")
        return

    with st.expander("Image Detection Agent", expanded=expanded):
        uploaded_image = st.file_uploader(
            "Upload product image",
            type=["png", "jpg", "jpeg", "webp"],
            help="Upload customer proof image before creating refund, replacement, warranty, or technical tickets.",
            key=f"{key_prefix}_image_upload",
        )
        if uploaded_image and st.button("Inspect Image", type="primary", key=f"{key_prefix}_inspect_image"):
            inspect_uploaded_image(uploaded_image)
            st.rerun()

        if st.session_state.damage_report:
            report = st.session_state.damage_report
            st.markdown("**Image Inspection Agent Output**")
            if st.session_state.uploaded_image_path and Path(st.session_state.uploaded_image_path).exists():
                st.image(st.session_state.uploaded_image_path, caption=Path(st.session_state.uploaded_image_path).name)
            report_cols = st.columns(4)
            report_cols[0].metric("Status", report.get("inspection_status", "unknown"))
            report_cols[1].metric("Damage", "Yes" if report.get("damage_detected") else "No")
            report_cols[2].metric("Severity", str(report.get("severity", "unknown")))
            report_cols[3].metric("Confidence", str(report.get("confidence", 0)))
            st.caption(f"Recommendation: {report.get('recommendation')}")
            st.caption(f"Inspection source: {report.get('source')} | Model: {report.get('model')}")
            st.caption(f"Image: {report.get('image_url')}")
            st.caption(report.get("notes", ""))
            with st.expander("Full inspection response", expanded=True):
                st.json(report)
            if st.session_state.pending_complaint:
                if st.button("Create Ticket from Inspection", type="primary", key=f"{key_prefix}_create_from_image"):
                    create_pending_complaint_from_image()
                    st.rerun()
            if st.button("Clear image report", key=f"{key_prefix}_clear_image_report"):
                st.session_state.damage_report = None
                st.session_state.uploaded_image_path = None
                st.rerun()


def render_status_messages() -> None:
    if st.session_state.last_created_ticket:
        ticket = st.session_state.last_created_ticket
        st.success(
            f"Created {ticket['ticket_id']} | {ticket['issue_type']} | "
            f"{ticket['priority']} | {ticket['status']}"
        )

    if st.session_state.last_created_email_draft:
        draft = st.session_state.last_created_email_draft
        st.info(f"Email draft {draft['draft_id']} ready for {draft['recipient']} | {draft['status']}")

    if not st.session_state.pending_complaint:
        return

    pending = st.session_state.pending_complaint
    requires_image = pending_requires_image(pending)

    if requires_image and st.session_state.awaiting_image_for_pending and not st.session_state.damage_report:
        st.warning(
            f"Please upload a product image for inspection before creating this "
            f"{pending['issue_type']} ticket."
        )
        if st.button("Cancel Ticket", use_container_width=True, key="customer_cancel_image_complaint"):
            handle_pending_complaint_confirmation("no")
            st.session_state.question_input = ""
            st.rerun()
    elif requires_image and st.session_state.damage_report:
        st.success("Image inspection is complete. Create the ticket now?")
        create_col, cancel_col = st.columns(2)
        if create_col.button("Create Ticket", type="primary", use_container_width=True, key="customer_create_after_image"):
            create_pending_complaint_from_image()
            st.session_state.question_input = ""
            st.rerun()
        if cancel_col.button("Cancel", use_container_width=True, key="customer_cancel_after_image"):
            handle_pending_complaint_confirmation("no")
            st.session_state.question_input = ""
            st.rerun()
    else:
        st.info(f"Create a {pending['issue_type']} ticket with {pending['priority']} priority?")
        yes_col, no_col = st.columns(2)
        if yes_col.button("Yes, Create Ticket", type="primary", use_container_width=True, key="customer_yes_create"):
            handle_pending_complaint_confirmation("yes")
            st.session_state.question_input = ""
            st.rerun()
        if no_col.button("No, Skip", use_container_width=True, key="customer_no_skip"):
            handle_pending_complaint_confirmation("no")
            st.session_state.question_input = ""
            st.rerun()


def render_customer_conversation(doc_count: int, source_count: int, question_count: int, top_k: int) -> None:
    st.subheader("Customer Conversation")

    if not st.session_state.documents_loaded:
        st.warning("Load a PDF, website, or saved vector DB from the sidebar before asking questions.")
    else:
        question = st.text_area(
            "Question",
            placeholder="Example: My product is not working. What should I do?",
            height=120,
            key="question_input",
        )
        ask_col, status_col = st.columns([0.22, 0.78])
        if ask_col.button("Ask Question", type="primary", disabled=not question.strip(), use_container_width=True):
            with st.spinner("Retrieving sources and generating answer..."):
                ask_question(question, top_k=top_k, assistant_mode=assistant_mode)
            st.rerun()
        status_col.caption(f"{doc_count} indexed chunks | {source_count} loaded sources | {question_count} questions")

    st.subheader("Conversation")
    if not st.session_state.chat_history:
        st.caption("Answers will appear here. Sources are shown below each response.")
    else:
        latest_first = list(reversed(st.session_state.chat_history))
        for turn_index, turn in enumerate(latest_first, 1):
            expanded = turn_index == 1
            with st.expander(turn["question"], expanded=expanded):
                st.caption(f"Mode: {turn.get('mode', assistant_mode)}")
                st.markdown(turn["answer"])
                st.divider()
                st.markdown("**Sources used**")
                render_sources(turn.get("sources", []))


def render_document_intelligence(top_k: int) -> None:
    with st.expander("Document intelligence and source search", expanded=False):
        if not st.session_state.documents_loaded:
            st.caption("Load a knowledge base to generate summaries, key topics, FAQs, and source searches.")
        else:
            action_cols = st.columns(3)
            intelligence_actions = [
                ("Support Summary", "Summarize the customer support knowledge base."),
                ("Escalation Rules", "List situations that should be escalated to human support."),
                ("Generate FAQ", "Create 8 useful customer FAQs with short answers from this knowledge base."),
            ]
            for col, (label, prompt) in zip(action_cols, intelligence_actions):
                if col.button(label, use_container_width=True):
                    with st.spinner(f"Running {label.lower()}..."):
                        ask_question(prompt, top_k=top_k, assistant_mode=assistant_mode)
                    st.rerun()

        search_query = st.text_input("Search retrieved chunks", placeholder="Search the indexed knowledge base")
        if st.button("Search Sources", disabled=not search_query or not st.session_state.documents_loaded):
            results = st.session_state.rag_pipeline.similarity_search(search_query, k=top_k)
            st.markdown(f"**Found {len(results)} matching chunks**")
            for index, (doc, score) in enumerate(results, 1):
                with st.expander(f"Result {index} | Score: {score:.2f}"):
                    st.caption(f"Source: {doc.metadata.get('source', 'Document')} | Page: {doc.metadata.get('page', 'N/A')}")
                    st.write(doc.page_content)


init_state()

with st.sidebar:
    render_knowledge_base_sidebar()

    st.divider()
    render_customer_lookup_sidebar()

    st.divider()
    st.title("LexiFlow")
    st.caption("Source-backed AI assistant for PDFs and websites")

    use_local = st.toggle("Use Local Ollama", value=False, help="Run with a local Ollama model instead of OpenAI.")
    if use_local:
        model = st.selectbox(
            "Local model",
            ["qwen2:0.5b", "phi", "neural-chat", "dolphin-mixtral", "mistral", "llama2"],
            index=0,
        )
        api_key = "local"
    else:
        model = st.selectbox("OpenAI model", ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"])
        entered_api_key = st.text_input("OpenAI API key", type="password", placeholder="sk-...")
        api_key = entered_api_key or os.getenv("OPENAI_API_KEY", "")

    top_k = st.slider("Sources to retrieve", 1, 10, 4)

    with st.expander("Chunk settings", expanded=False):
        chunk_size = st.slider("Chunk size", 100, 1500, 500, step=50)
        chunk_overlap = st.slider("Chunk overlap", 0, 300, 50, step=10)
        auto_load_saved_db = st.checkbox("Auto-load saved vector DB", value=False)

    pipeline_ready = False
    if use_local or api_key:
        try:
            ensure_pipeline(api_key=api_key, model=model, use_local=use_local, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            if auto_load_saved_db:
                try_auto_load_vector_db()
            pipeline_ready = True
            st.success("Pipeline ready")
        except Exception as exc:
            st.error(f"Pipeline error: {exc}")
    else:
        st.warning("Add an OpenAI API key or enable Ollama.")

    if st.button("Clear session", use_container_width=True):
        if st.session_state.rag_pipeline:
            st.session_state.rag_pipeline.clear()
        clear_support_activity()
        clear_uploaded_images()
        st.session_state.chat_history = []
        st.session_state.documents_loaded = False
        st.session_state.document_names = []
        st.session_state.selected_case = None
        st.session_state.last_created_ticket = None
        st.session_state.last_created_email_draft = None
        st.session_state.pending_complaint = None
        st.session_state.awaiting_image_for_pending = False
        st.session_state.damage_report = None
        st.session_state.uploaded_image_path = None
        st.session_state.question_input = ""
        st.rerun()


st.title("MultiAgent Customer Care")
st.caption("Upload business rules documents, answer customer questions, and verify every response against sources.")

if not pipeline_ready:
    st.info("Configure a model in the sidebar to start the demo.")
    st.stop()

doc_count = len(st.session_state.rag_pipeline.documents) if st.session_state.rag_pipeline else 0
source_count = len(st.session_state.document_names)
question_count = len(st.session_state.chat_history)

assistant_mode = "Customer Care Agent"

if st.session_state.selected_case:
    backfill_missing_email_drafts()

customer_tab, admin_tab = st.tabs(["Customer View", "Admin View"])

with customer_tab:
    render_active_customer_context()
    render_status_messages()
    if (
        st.session_state.pending_complaint
        and issue_requires_image(st.session_state.pending_complaint["issue_type"])
        and (st.session_state.awaiting_image_for_pending or st.session_state.damage_report)
    ):
        render_image_detection_agent(
            key_prefix="customer",
            expanded=True,
        )
    render_customer_conversation(
        doc_count=doc_count,
        source_count=source_count,
        question_count=question_count,
        top_k=top_k,
    )

with admin_tab:
    with st.expander("Operations Dashboard", expanded=True):
        render_operations_dashboard()
    with st.expander("Selected customer support records", expanded=False):
        render_selected_customer_records()
    render_image_detection_agent(
        key_prefix="admin",
        expanded=bool(st.session_state.damage_report),
    )
    render_document_intelligence(top_k=top_k)
