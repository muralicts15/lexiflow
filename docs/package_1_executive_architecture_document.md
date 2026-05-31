# Package 1 - Executive Architecture Document

**Project:** LexiFlow MultiAgent Customer Care  
**Document Type:** Executive Architecture Document  
**Audience:** Technology leaders, architects, engineering managers, delivery teams, AI stakeholders  
**Version:** 1.0  
**Status:** Draft for exhibition and technical review  

---

## 1. Executive Summary

### 1.1 Business Challenge

Customer support teams are expected to respond quickly, accurately, and
consistently across a growing number of customer cases. In many organizations,
support knowledge is spread across PDF policy documents, product manuals,
internal process guides, order systems, CRM tools, email systems, warranty
systems, and operational dashboards.

This creates a common set of business problems:

- Support agents spend time searching through policy documents.
- Customers receive inconsistent answers from different agents.
- Refund, replacement, warranty, and escalation decisions are not always
  grounded in the latest business rules.
- Product damage verification is manual and slow.
- Ticket creation and email follow-up are repetitive.
- Managers do not get a single operational view of support cases and image
  inspection outcomes.

LexiFlow addresses these problems by combining Retrieval-Augmented Generation
(RAG), customer database lookup, AI-assisted support workflow, MCP-based image
inspection, ticket automation, and dashboard visibility.

### 1.2 Current Support Process Issues

The current manual or semi-manual process has several inefficiencies:

| Issue | Business Impact |
|---|---|
| Policy lookup is manual | Slower average handling time |
| Answers vary by agent | Inconsistent customer experience |
| Customer facts are checked separately | Higher chance of eligibility mistakes |
| Image proof review is manual | Delayed refund or replacement decisions |
| Ticket creation is repetitive | Lower agent productivity |
| Email follow-up is manual | Delays and inconsistent language |
| Limited operational visibility | Managers cannot track workload in real time |

### 1.3 Proposed AI-Powered Solution

LexiFlow proposes an AI-powered customer support architecture with these core
capabilities:

- Business rules ingestion using RAG.
- Customer/order/warranty lookup using database integration.
- Customer Care Agent workflow for support conversation and eligibility
  reasoning.
- Damage Detection Agent through MCP for image inspection.
- Ticket and email draft automation.
- Admin dashboard for operational visibility.
- Clear separation between Customer View and Admin View.

The current implementation is a proof of concept running in Streamlit with
SQLite and FAISS. The architecture is designed so that the same logical
components can later move to React, APIs, Kubernetes, PostgreSQL, Redis, and an
enterprise vector database.

### 1.4 Key Business Outcomes

Expected business outcomes include:

- Reduced customer response time.
- More consistent policy-aware responses.
- Improved support agent productivity.
- Faster complaint registration.
- Structured damage inspection evidence.
- Improved auditability.
- Better operational monitoring.
- Easier transition from proof of concept to production MVP.

### 1.5 Expected ROI

The expected ROI comes from:

- Lower average handle time per case.
- Lower manual policy lookup effort.
- Reduced repeated support work.
- Faster complaint creation and routing.
- Reduced rework caused by incorrect policy interpretation.
- Better prioritization of high-impact cases.

Example ROI assumptions for a medium deployment:

| Metric | Current | Target |
|---|---:|---:|
| Average policy lookup time | 3-5 minutes | < 30 seconds |
| Complaint creation time | 2-4 minutes | < 30 seconds |
| First response consistency | Medium | High |
| Manual image triage | 100% manual | AI-assisted with human review |
| Manager case visibility | Delayed | Near real-time |

---

## 2. Business Requirements

### 2.1 Functional Goals

The solution must support the following functional goals:

- Automate customer support question answering.
- Ground answers in uploaded business rules documents.
- Personalize responses using customer/order/warranty data.
- Detect when complaint ticket creation is appropriate.
- Request product image proof when required.
- Inspect uploaded product images for visible damage.
- Create complaint tickets after user confirmation.
- Generate customer email drafts after ticket creation.
- Persist support activity for admin review.
- Provide operational dashboard metrics.

### 2.2 Customer Support Automation

The system must reduce manual support effort by allowing a customer or support
agent to ask natural language questions and receive a grounded answer. The
answer should combine policy context and customer-specific context.

### 2.3 Policy-Aware Responses

The system must retrieve relevant business policy chunks from uploaded
documents and use them when generating responses. The model must not invent
refund, replacement, warranty, or escalation rules.

### 2.4 Complaint Handling

The system must detect cases where a complaint may be needed and ask the user
for confirmation. The confirmation should be button-based in the UI.

### 2.5 Damage Inspection

The system must support product image upload and call a specialist Image
Detection Agent through MCP. The result must include damage status, severity,
confidence, recommendation, and notes.

### 2.6 Ticket Automation

The system must create support tickets and email drafts after confirmation. The
created ticket and email draft must be visible in Customer View and Admin View.

### 2.7 Stakeholders

| Stakeholder | Responsibility |
|---|---|
| Customer | Raise support queries and provide image proof |
| Support Agent | Review customer cases and AI-generated responses |
| Operations Manager | Monitor KPIs, ticket volume, and inspection outcomes |
| System Administrator | Manage platform configuration and access |
| AI Engineer | Maintain RAG, prompts, tools, and model integrations |
| Data Engineer | Maintain document ingestion, customer data, and analytics pipelines |
| Security Team | Review data protection, access control, and audit requirements |
| Product Owner | Prioritize roadmap and business outcomes |

---

## 3. Functional Requirements

### FR-001 Customer Query Processing

**Description:** The system shall accept a customer support question and return
an AI-generated response.

**Input:**

- Customer question.
- Selected customer/order context.
- Available business rules documents.

**Output:**

- AI-generated response.
- Retrieved source chunks.

**Acceptance Criteria:**

- Answer must include policy grounding.
- Answer must use customer context when available.
- Answer must show sources below the response.

### FR-002 Business Rules Upload

**Description:** The system shall allow business users to upload support policy
documents.

**Input:**

- PDF document.

**Output:**

- Indexed knowledge base chunks.

**Acceptance Criteria:**

- PDF must be parsed successfully.
- Chunks must be stored in FAISS.
- Uploaded source name must be retained.

### FR-003 Website Knowledge Loading

**Description:** The system shall support loading policy or support content
from a website URL.

**Input:**

- Website URL.

**Output:**

- Indexed website content.

**Acceptance Criteria:**

- Website content must be loaded into the same vector store.
- Source URL must be retained in metadata.

### FR-004 Customer Lookup

**Description:** The system shall retrieve customer context by order ID, email,
or phone number.

**Input:**

- Order ID, email, or phone number.

**Output:**

- Customer, order, product, warranty, ticket, draft, and audit context.

**Acceptance Criteria:**

- Matching customer must be shown in Customer View.
- No-match condition must be handled gracefully.

### FR-005 Customer Context Display

**Description:** The system shall show active customer context in Customer View.

**Input:**

- Selected customer record.

**Output:**

- Customer name, order ID, delivery age, warranty status, product, serial
  number, refund window, replacement window.

**Acceptance Criteria:**

- Context must be visible without opening Admin View.
- UI must remain compact enough for conversation access.

### FR-006 Policy-Aware Eligibility Response

**Description:** The system shall answer refund, replacement, warranty, and
technical support questions using both policy and customer facts.

**Input:**

- Customer question.
- Retrieved policy context.
- Customer/order data.

**Output:**

- Eligibility explanation and next action.

**Acceptance Criteria:**

- The response must not mix refund, replacement, warranty, or delivery windows.
- The response must mention relevant customer/order facts when available.

### FR-007 Source Citation Display

**Description:** The system shall display retrieved sources used for answering.

**Input:**

- Retrieved documents from RAG.

**Output:**

- Expandable source list below each response.

**Acceptance Criteria:**

- Each source must show document name and page when available.

### FR-008 Complaint Offer Detection

**Description:** The system shall detect when a customer case may require a
complaint ticket.

**Input:**

- Generated answer.
- Assistant mode.
- Selected customer.

**Output:**

- Pending complaint object.

**Acceptance Criteria:**

- Complaint must be offered only for relevant support cases.
- The user must confirm before ticket creation.

### FR-009 Button-Based Complaint Confirmation

**Description:** The system shall use buttons for complaint confirmation.

**Input:**

- Pending complaint.

**Output:**

- User decision.

**Acceptance Criteria:**

- UI must show Yes and No buttons.
- Text-based yes/no should not be required for the primary path.

### FR-010 Image Proof Request

**Description:** The system shall request a product image when the issue type
requires image proof.

**Input:**

- Pending complaint.
- Issue type.

**Output:**

- Image upload instruction.

**Acceptance Criteria:**

- Message must clearly ask for product image upload.
- Ticket should not be created before required image inspection.

### FR-011 Damage Detection

**Description:** The system shall inspect uploaded product images for visible
damage.

**Input:**

- Product image.

**Output:**

- Damage classification.
- Severity.
- Confidence score.
- Recommendation.

**Acceptance Criteria:**

- Confidence score must be returned.
- Human review flag must be returned.
- Inspection result must be displayed in Image Detection Agent section.

### FR-012 MCP-Based Image Inspection

**Description:** The system shall call image inspection through MCP.

**Input:**

- Image path.
- Optional image URL.
- Optional order ID.

**Output:**

- Structured damage report.

**Acceptance Criteria:**

- `mcp_client.py` must call `mcp_server.py`.
- MCP server must expose `inspect_product_damage`.

### FR-013 Ticket Creation

**Description:** The system shall create complaint tickets after confirmation.

**Input:**

- Customer ID.
- Order ID.
- Issue type.
- Priority.
- Summary.

**Output:**

- Ticket ID and ticket record.

**Acceptance Criteria:**

- Ticket must be persisted in SQLite.
- Ticket must be visible in Customer View and Admin View.

### FR-014 Email Draft Creation

**Description:** The system shall create an email draft after ticket creation.

**Input:**

- Ticket.
- Customer.
- Order.
- Issue type.

**Output:**

- Email draft.

**Acceptance Criteria:**

- Draft must be persisted in SQLite.
- Draft must be visible in Admin View.

### FR-015 Audit Logging

**Description:** The system shall log important support actions.

**Input:**

- Action name.
- Detail.
- Customer/order reference.

**Output:**

- Audit log row.

**Acceptance Criteria:**

- Customer lookup, ticket creation, draft creation, deletion, and image
  inspection must be auditable.

### FR-016 Operations Dashboard

**Description:** The system shall provide an operations dashboard for admins.

**Input:**

- Ticket data.
- Image inspection data.

**Output:**

- Metrics and tables.

**Acceptance Criteria:**

- Dashboard must show total tickets, open tickets, high priority tickets,
  inspections, and human review cases.

### FR-017 Customer View

**Description:** The system shall provide a customer-facing view.

**Input:**

- Selected customer.
- Chat history.
- Support status messages.

**Output:**

- Customer context, conversation, status messages, required image upload step.

**Acceptance Criteria:**

- Admin-only tools must not clutter Customer View.

### FR-018 Admin View

**Description:** The system shall provide an admin-facing view.

**Input:**

- Tickets, drafts, audit logs, image inspections.

**Output:**

- Dashboard and management controls.

**Acceptance Criteria:**

- Admin View must include operations dashboard and record management.

### FR-019 Clear Session

**Description:** The system shall reset demo session and support activity.

**Input:**

- Clear session click.

**Output:**

- Cleared chat, documents, selected customer, tickets, drafts, audit logs, and
  inspection records.

**Acceptance Criteria:**

- Dashboard should show cleared support records after reset.

### FR-020 Local and Cloud Model Options

**Description:** The system shall support OpenAI and local Ollama mode.

**Input:**

- Model selection.

**Output:**

- Active LLM configuration.

**Acceptance Criteria:**

- OpenAI mode must use API key.
- Local mode must use Ollama when available.

### FR-021 Vector Database Save and Load

**Description:** The system shall support saving and loading the vector database.

**Input:**

- Vector DB path.

**Output:**

- Persisted or loaded FAISS index.

**Acceptance Criteria:**

- Saved DB can be loaded without re-uploading documents.

### FR-022 Document Intelligence

**Description:** The system shall provide admin document intelligence actions.

**Input:**

- Loaded knowledge base.

**Output:**

- Support summary, escalation rules, generated FAQ.

**Acceptance Criteria:**

- Actions must use the same RAG pipeline.

### FR-023 Source Search

**Description:** The system shall provide source chunk search in Admin View.

**Input:**

- Search query.

**Output:**

- Matching source chunks.

**Acceptance Criteria:**

- Results must include source metadata and content.

### FR-024 Image Inspection Persistence

**Description:** The system shall persist image inspection results.

**Input:**

- Damage inspection report.

**Output:**

- Damage inspection database row.

**Acceptance Criteria:**

- Inspection must appear in Admin View dashboard.

### FR-025 Future ML Model Integration

**Description:** The system shall allow replacement of OpenAI vision/mock
inspection with the trained product damage ML model.

**Input:**

- Image file.

**Output:**

- Same structured damage inspection report.

**Acceptance Criteria:**

- MCP tool contract must remain stable.
- UI and dashboard should not require major changes.

---

## 4. Non-Functional Requirements

### 4.1 Performance

| Metric | Current PoC Target | Production Target |
|---|---:|---:|
| Customer query response | < 10 sec | < 5 sec |
| Image analysis | < 15 sec | < 10 sec |
| Customer lookup | < 1 sec | < 300 ms |
| Ticket creation | < 1 sec | < 500 ms |
| Dashboard load | < 3 sec | < 2 sec |
| Concurrent users | 1-10 | 1000+ |

### 4.2 Scalability

Production scalability requirements:

- Stateless application services.
- Horizontal scaling for customer agent pods.
- Separate RAG service.
- Separate MCP/tool gateway.
- Redis caching for repeated policy retrieval and session data.
- Managed PostgreSQL for customer and ticket data.
- Managed vector database for large-scale retrieval.

### 4.3 Availability

Production availability targets:

| Component | Target |
|---|---:|
| Customer API | 99.9% |
| Admin dashboard | 99.5% |
| RAG retrieval | 99.5% |
| Damage detection | 99.0% |
| Ticket creation | 99.9% |

### 4.4 Security

Security requirements:

- Role-Based Access Control.
- TLS for all network traffic.
- Encryption at rest for sensitive data.
- Secrets management for API keys.
- Audit logging for support actions.
- Prompt injection prevention.
- Input validation for uploaded files.
- Output filtering for customer-facing responses.

### 4.5 Maintainability

The solution must:

- keep RAG, DB, MCP, and UI concerns separated,
- preserve stable tool contracts,
- maintain clear documentation,
- support automated testing,
- allow future ML model replacement without UI redesign.

---

## 5. Solution Architecture

### 5.1 Enterprise Architecture Diagram

```text
Customer / Support Agent
        |
        v
Frontend Channel
Streamlit PoC / React Future
        |
        v
API Gateway - Future
        |
        v
Customer Care Agent
        |
        +-----------------------------+
        |                             |
        v                             v
RAG Service                    Customer Data Service
        |                             |
        v                             v
Vector DB                       PostgreSQL / SQLite PoC
        |
        v
MCP Gateway
        |
        v
Damage Detection Service
        |
        v
Vision Model / Trained ML Model
```

### 5.2 Current PoC Architecture

```text
Streamlit app.py
   |
   +-- RAGPipeline
   |     +-- PDF loader
   |     +-- Chunking
   |     +-- Embeddings
   |     +-- FAISS
   |     +-- LLM
   |
   +-- customer_db.py
   |     +-- SQLite customers/orders/warranties
   |     +-- tickets/email drafts/audit logs/inspections
   |
   +-- mcp_client.py
         |
         +-- mcp_server.py
               |
               +-- damage_detection_agent.py
```

### 5.3 Target Production Architecture

```text
Web / Mobile Client
        |
Load Balancer
        |
API Gateway
        |
+-------------------------------+
| Customer Agent Service        |
| Ticket Service                |
| Notification Service          |
| Admin Dashboard API           |
+-------------------------------+
        |
        +-- RAG Service -> Vector DB
        +-- Customer Data Service -> PostgreSQL
        +-- MCP Gateway -> Damage Detection Service
        +-- Cache -> Redis
        +-- Observability -> Logs/Metrics/Traces
```

---

## 6. Logical Architecture

### 6.1 Presentation Layer

Current:

- Streamlit application.
- Customer View.
- Admin View.
- Sidebar configuration and customer lookup.

Future:

- React or Next.js frontend.
- Role-based UI.
- Customer-facing web chat.
- Admin operations dashboard.

### 6.2 Application Layer

Current:

- Customer Care Agent flow inside `app.py`.
- Ticket and email draft functions inside the app/database utility layer.
- MCP client for damage inspection.

Future:

- Customer Agent Service.
- Ticket Service.
- Email/Notification Service.
- Admin Dashboard Service.
- RAG Orchestration Service.

### 6.3 Data Layer

Current:

- SQLite for customer and support records.
- FAISS for local vector search.
- Local uploads folder for images.

Future:

- PostgreSQL for relational data.
- Redis for cache and sessions.
- Qdrant, Pinecone, Weaviate, or OpenSearch vector engine.
- Object storage for uploaded images.

### 6.4 Integration Layer

Current:

- MCP-style local stdio server for damage inspection.
- Local Python function calls for ticket/email actions.

Future:

- MCP gateway for external tools.
- CRM APIs.
- Email APIs.
- Warranty APIs.
- Payment/refund APIs.
- Logistics APIs.

---

## 7. Physical Architecture

### 7.1 Current Local Deployment

```text
Developer Laptop
    |
    +-- Python virtual environment
    +-- Streamlit server
    +-- SQLite database file
    +-- FAISS vector DB folder
    +-- uploads folder
    +-- MCP server subprocess
```

### 7.2 Cloud Deployment

```text
Internet
   |
Load Balancer
   |
Kubernetes Ingress
   |
+-------------------------+
| Customer Agent Pods     |
| Admin API Pods          |
| RAG Service Pods        |
| MCP Gateway Pods        |
| Damage Service Pods     |
+-------------------------+
   |
   +-- PostgreSQL
   +-- Redis
   +-- Vector DB
   +-- Object Storage
   +-- Secrets Manager
   +-- Observability Stack
```

### 7.3 Environment Separation

Recommended environments:

- Local development.
- Demo/staging.
- UAT.
- Production.

Each environment should have separate:

- API keys,
- database,
- vector indexes,
- storage buckets,
- model configuration,
- monitoring dashboards.

---

## 8. Sequence Diagrams

### 8.1 Customer Support Flow

```text
Customer
  -> UI: Ask question
UI
  -> Customer Agent: question + selected customer
Customer Agent
  -> RAG: retrieve policy context
RAG
  -> Vector DB: similarity search
Vector DB
  -> RAG: relevant chunks
Customer Agent
  -> Customer DB: order and warranty context
Customer DB
  -> Customer Agent: customer facts
Customer Agent
  -> LLM: prompt with policy + customer facts
LLM
  -> Customer Agent: answer
Customer Agent
  -> UI: answer + sources + complaint option
UI
  -> Customer: response
```

### 8.2 Damage Detection Flow

```text
Customer
  -> UI: upload product image
UI
  -> MCP Client: inspect_product_damage
MCP Client
  -> MCP Server: JSON-RPC tools/call
MCP Server
  -> Damage Detection Agent: inspect image
Damage Detection Agent
  -> Vision/ML Model: classify damage
Vision/ML Model
  -> Damage Detection Agent: result
Damage Detection Agent
  -> MCP Server: structured report
MCP Server
  -> MCP Client: tool result
MCP Client
  -> UI: report
UI
  -> SQLite: persist inspection
UI
  -> Customer/Admin: display inspection output
```

### 8.3 Ticket Creation Flow

```text
Customer
  -> UI: click Create Complaint
UI
  -> Customer Agent Flow: validate pending complaint
Customer Agent Flow
  -> SQLite: create ticket
SQLite
  -> Customer Agent Flow: ticket ID
Customer Agent Flow
  -> SQLite: create email draft
Customer Agent Flow
  -> SQLite: write audit log
Customer Agent Flow
  -> UI: created ticket and draft status
UI
  -> Customer/Admin: display status
```

---

## 9. Data Model

### 9.1 ER Diagram

```text
Customer
  PK id
  name
  email
  phone
  tier
   |
   | 1..n
   v
Order
  PK id
  UK order_id
  FK customer_id
  product_name
  serial_number
  purchase_date
  delivery_date
  order_status
  payment_status
   |
   | 1..1
   v
Warranty
  PK id
  FK order_id
  warranty_end_date
  status

Customer
   |
   | 1..n
   v
Ticket
  PK id
  UK ticket_id
  FK customer_id
  FK order_id
  issue_type
  status
  priority
  created_at
  summary
   |
   | 0..n
   v
EmailDraft
  PK id
  UK draft_id
  FK customer_id
  FK order_id
  ticket_id
  recipient
  subject
  body
  status
  created_at

Order
   |
   | 0..n
   v
DamageInspection
  PK id
  FK customer_id
  order_id
  image_url
  inspection_status
  damage_detected
  damage_type
  severity
  confidence
  needs_human_review
  recommendation
  source
  model
  notes
  created_at
```

### 9.2 Table Details

| Table | Primary Key | Important Foreign Keys |
|---|---|---|
| customers | id | none |
| orders | id | customer_id |
| warranties | id | order_id |
| tickets | id | customer_id, order_id |
| email_drafts | id | customer_id, order_id |
| audit_logs | id | customer_id |
| damage_inspections | id | customer_id, order_id |

### 9.3 Recommended Indexes for Production

| Table | Index |
|---|---|
| customers | email, phone |
| orders | order_id, customer_id |
| warranties | order_id |
| tickets | ticket_id, customer_id, order_id, status, priority |
| email_drafts | draft_id, ticket_id, customer_id, order_id |
| audit_logs | customer_id, order_id, created_at |
| damage_inspections | customer_id, order_id, severity, created_at |

---

## 10. API Contracts

The current PoC is a Streamlit application, but the production architecture
should expose REST APIs.

### 10.1 Customer Query API

**Endpoint:**

```http
POST /api/v1/chat/query
```

**Request:**

```json
{
  "customerId": "1001",
  "orderId": "ORD-1001",
  "question": "Can I get a refund?"
}
```

**Response:**

```json
{
  "answer": "Hi Priya, based on the policy and your delivery date...",
  "sources": [
    {
      "source": "business_rules.pdf",
      "page": 2,
      "content": "Refunds are available within..."
    }
  ],
  "pendingComplaint": {
    "issueType": "refund",
    "priority": "Medium",
    "requiresImage": true
  }
}
```

### 10.2 Damage Inspection API

**Endpoint:**

```http
POST /api/v1/damage/inspect
```

**Request:**

```json
{
  "customerId": "1001",
  "orderId": "ORD-1001",
  "imageUrl": "https://storage.example.com/uploads/ORD-1001.png"
}
```

**Response:**

```json
{
  "inspectionStatus": "completed",
  "damageDetected": true,
  "damageType": "cracked_case",
  "severity": "high",
  "confidence": 0.93,
  "needsHumanReview": true,
  "recommendation": "manual_review_required",
  "notes": "Visible cracks detected on product body."
}
```

### 10.3 Create Ticket API

**Endpoint:**

```http
POST /api/v1/tickets
```

**Request:**

```json
{
  "customerId": "1001",
  "orderId": "ORD-1001",
  "issueType": "technical",
  "priority": "High",
  "summary": "Customer reports product not working after troubleshooting."
}
```

**Response:**

```json
{
  "ticketId": "TKT-2001",
  "status": "Open",
  "priority": "High"
}
```

### 10.4 Email Draft API

**Endpoint:**

```http
POST /api/v1/email-drafts
```

**Request:**

```json
{
  "customerId": "1001",
  "orderId": "ORD-1001",
  "ticketId": "TKT-2001",
  "recipient": "priya.raman@example.com",
  "subject": "Complaint TKT-2001 created",
  "body": "Hi Priya..."
}
```

**Response:**

```json
{
  "draftId": "EML-3001",
  "status": "Draft"
}
```

---

## 11. RAG Design Deep Dive

### 11.1 Current Implementation

The current RAG implementation is in `rag_pipeline.py`.

It includes:

- PDF ingestion.
- Website ingestion.
- Recursive chunking.
- Embedding generation.
- FAISS vector storage.
- Similarity retrieval.
- Query expansion for support topics.
- Priority document retrieval.
- Prompt augmentation.
- Source citations.

### 11.2 Chunking Strategy

Current defaults:

| Setting | Value |
|---|---:|
| Chunk size | 500 |
| Chunk overlap | 50 |

Reasoning:

- 500 characters/tokens is small enough for focused retrieval.
- 50 overlap helps preserve policy continuity across chunk boundaries.
- Smaller chunks reduce the risk of unrelated policy mixing.

### 11.3 Retrieval Strategy

Retrieval uses two techniques:

1. Semantic similarity search in FAISS.
2. Priority document matching for known support policy categories.

Priority terms are used for:

- refund,
- return,
- replacement,
- warranty,
- technical issue,
- login/password,
- shipping/delivery,
- escalation.

### 11.4 Reranking Strategy

The current PoC does not use a separate reranker. It uses priority matching and
deduplication before limiting the retrieved context.

Recommended production reranking:

- Cross-encoder reranker.
- LLM-based relevance scoring for top 20 chunks.
- Policy category classifier before retrieval.
- Metadata filters by document type.

### 11.5 Hallucination Mitigation

Current safeguards:

- System prompt instructs the model to use only provided context.
- Retrieved sources are displayed.
- Customer-care prompt warns not to mix policy categories.
- If answer is unavailable, model should say context is insufficient.
- Customer database context is injected explicitly.

Recommended production safeguards:

- Response validation layer.
- Policy citation requirement.
- Prompt injection detection.
- Output filtering.
- Human approval for high-risk decisions.
- Evaluation set for refund/warranty/replacement scenarios.

---

## 12. MCP Design Deep Dive

### 12.1 MCP Purpose

MCP is used to separate specialist tool execution from the customer conversation
flow.

In LexiFlow, MCP is used only for:

```text
inspect_product_damage
```

This makes the demo easy to explain:

```text
RAG gives the agent knowledge.
MCP gives the agent tools.
```

### 12.2 MCP Server

Current file:

```text
mcp_server.py
```

Responsibilities:

- Accept JSON-RPC messages through stdin.
- Support `initialize`.
- Support `tools/list`.
- Support `tools/call`.
- Expose `inspect_product_damage`.
- Return structured JSON result.

### 12.3 MCP Client

Current file:

```text
mcp_client.py
```

Responsibilities:

- Start MCP server subprocess.
- Send JSON-RPC request.
- Call `inspect_product_damage`.
- Parse response.
- Return damage report to the Streamlit app.

### 12.4 Tool Registry

Current tool registry:

| Tool | Purpose |
|---|---|
| inspect_product_damage | Inspect uploaded product image |

Future tools:

| Tool | Purpose |
|---|---|
| lookup_customer | Retrieve customer and order context |
| create_ticket | Create support ticket in CRM |
| send_email | Send or draft customer email |
| check_warranty | Validate warranty status |
| create_refund_request | Initiate refund workflow |
| escalate_case | Route case to specialist queue |

### 12.5 JSON-RPC Flow

```text
Client -> Server:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "inspect_product_damage",
    "arguments": {
      "image_path": "uploads/ORD-1001.png",
      "order_id": "ORD-1001"
    }
  }
}

Server -> Client:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{...damage report...}"
      }
    ]
  }
}
```

---

## 13. Security Architecture

### 13.1 Authentication

Recommended production authentication:

- OAuth2 authorization code flow.
- JWT access tokens.
- Refresh tokens with rotation.
- Enterprise SSO integration.

### 13.2 Authorization

Recommended roles:

| Role | Access |
|---|---|
| Customer | Own conversation and uploaded files |
| Support Agent | Assigned customer cases |
| Operations Manager | Dashboard and team KPIs |
| Admin | Platform configuration and user management |
| AI Engineer | Prompt, retrieval, and model configuration |

### 13.3 Data Security

Requirements:

- TLS in transit.
- AES encryption at rest.
- Field-level protection for PII.
- Secure object storage for uploaded images.
- Secrets manager for API keys.
- Database backups and retention policy.

### 13.4 LLM Security

Risks:

- Prompt injection.
- Data leakage.
- Policy bypass.
- Untrusted document content.
- Overconfident unsupported answers.

Controls:

- Prompt injection detection.
- Strict system prompts.
- Context boundary markers.
- Output validation.
- Citation requirement.
- Human review for high-risk actions.
- Tool permission checks.

### 13.5 File Upload Security

Controls:

- File type validation.
- File size limits.
- Malware scanning.
- Image metadata stripping.
- Object storage with signed URLs.
- Expiring access tokens.

---

## 14. Error Handling Strategy

| Error | Action |
|---|---|
| LLM failure | Retry with backoff, show fallback message |
| Vector DB failure | Fallback to database context and ask for retry |
| MCP failure | Graceful degradation and manual review |
| DB failure | Circuit breaker and operational alert |
| Image model failure | Mark inspection inconclusive and require human review |
| File upload failure | Ask user to retry with valid image |
| Prompt validation failure | Stop action and route to human support |
| Ticket creation failure | Preserve pending complaint and retry |
| Email draft failure | Create ticket but flag draft creation failure |

Recommended production patterns:

- Retry only idempotent operations.
- Use circuit breakers for downstream services.
- Use correlation IDs across requests.
- Store failed action attempts for audit.
- Do not silently approve refund/replacement when evidence is missing.

---

## 15. Logging and Monitoring

### 15.1 Logging

Recommended logging format:

```json
{
  "timestamp": "2026-05-31T10:00:00Z",
  "level": "INFO",
  "correlationId": "req-123",
  "customerId": "1001",
  "orderId": "ORD-1001",
  "action": "create_ticket",
  "status": "success"
}
```

Log categories:

- customer query,
- retrieval request,
- LLM completion,
- MCP tool call,
- image inspection,
- ticket creation,
- email draft creation,
- admin action,
- error event.

### 15.2 Monitoring

Recommended tools:

- Prometheus for metrics.
- Grafana for dashboards.
- OpenTelemetry for tracing.
- Centralized log platform.

Metrics:

| Metric | Purpose |
|---|---|
| Query latency | User experience |
| Retrieval latency | RAG performance |
| LLM token usage | Cost control |
| MCP call latency | Tool performance |
| Damage model confidence | Model quality |
| Ticket creation count | Operations tracking |
| Human review count | Risk monitoring |
| Error rate | Reliability |

---

## 16. Deployment Architecture

### 16.1 Current Deployment

Current PoC:

- Streamlit application.
- SQLite database.
- FAISS local vector database.
- Local uploads folder.
- Local MCP server subprocess.
- OpenAI API or local Ollama model.

### 16.2 Future Deployment

Future production:

- React frontend.
- API gateway.
- Kubernetes.
- Customer Agent pods.
- RAG service pods.
- MCP gateway pods.
- Damage Detection service pods.
- PostgreSQL.
- Redis.
- Qdrant/Pinecone/Weaviate.
- Object storage.
- Secrets manager.
- Monitoring stack.

---

## 17. CI/CD Pipeline

### 17.1 Pipeline Diagram

```text
Developer
  |
  v
GitHub
  |
  v
GitHub Actions
  |
  +-- Lint
  +-- Unit Tests
  +-- Integration Tests
  +-- Security Scan
  +-- SAST
  +-- Docker Build
  +-- Trivy Scan
  +-- Deploy to Staging
  +-- Smoke Test
  +-- Approval Gate
  +-- Deploy to Production
```

### 17.2 Recommended Checks

| Check | Tool |
|---|---|
| Code quality | Ruff, Black |
| Unit tests | Pytest |
| Security scan | Bandit, Semgrep |
| Dependency scan | pip-audit |
| Container scan | Trivy |
| Code coverage | Coverage.py |
| Static analysis | SonarQube |
| DAST | OWASP ZAP |

---

## 18. Cost Estimation

### 18.1 Monthly Cost Estimate

| Component | Small | Medium | Enterprise |
|---|---:|---:|---:|
| OpenAI usage | $50 | $200 | $1000+ |
| Vector DB | $0-$50 | $50-$200 | $500+ |
| PostgreSQL | $20 | $40 | $300+ |
| Redis | $0-$20 | $50 | $200+ |
| Kubernetes/app hosting | $50 | $250 | $1000+ |
| Object storage | $5 | $25 | $100+ |
| Monitoring/logging | $0-$50 | $100 | $500+ |
| Total | $125-$245 | $715-$865 | $3600+ |

### 18.2 Cost Optimization

Cost control measures:

- Cache repeated answers and retrieval results.
- Use smaller models for simple questions.
- Use local or cheaper embeddings.
- Batch document ingestion.
- Archive old image uploads.
- Use human review only for high-risk cases.
- Apply token budgets per request.

---

## 19. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Hallucinations | High | RAG grounding, citation display, validation |
| Model cost growth | Medium | Caching, token limits, model routing |
| Data leakage | High | RBAC, encryption, prompt filtering |
| Incorrect damage detection | High | Human review and confidence threshold |
| Prompt injection | High | Input validation and prompt injection detection |
| Vector DB stale data | Medium | Document versioning and re-indexing workflow |
| API outage | Medium | Retry, fallback, circuit breaker |
| Poor document quality | Medium | Document preprocessing and admin review |
| Over-automation | High | Confirmation buttons and human approval |
| User trust issues | Medium | Source citations and transparent decisions |

---

## 20. Future Roadmap

### Phase 1: Current PoC

Scope:

- Streamlit UI.
- Customer View and Admin View.
- RAG document upload.
- SQLite customer/order database.
- Customer Care Agent flow.
- MCP damage inspection.
- Ticket and email draft creation.
- Dashboard.

### Phase 2: Production MVP

Scope:

- React frontend.
- FastAPI backend.
- PostgreSQL.
- Managed vector database.
- Object storage.
- Authentication and RBAC.
- Real ticketing API.
- Real email API.
- ML damage model integration.

### Phase 3: Enterprise Platform

Scope:

- Kubernetes deployment.
- API gateway.
- Redis cache.
- Observability stack.
- CI/CD pipeline.
- Security scanning.
- Evaluation framework.
- A/B testing for prompts and retrieval.

### Phase 4: Multi-Agent Ecosystem

Scope:

- Customer Agent.
- Warranty Agent.
- Ticket Agent.
- Damage Detection Agent.
- Escalation Agent.
- Analytics Agent.
- Supervisor Agent.

Target architecture:

```text
Supervisor Agent
  |
  +-- Customer Agent
  +-- Warranty Agent
  +-- Ticket Agent
  +-- Damage Detection Agent
  +-- Escalation Agent
  +-- Analytics Agent
```

---

## Appendix A: Current File Mapping

| Capability | Current File |
|---|---|
| Streamlit UI | `app.py` |
| RAG pipeline | `rag_pipeline.py` |
| Customer database | `customer_db.py` |
| Damage detection | `damage_detection_agent.py` |
| MCP client | `mcp_client.py` |
| MCP server | `mcp_server.py` |
| MCP usage notes | `MCP_USAGE.md` |

## Appendix B: Demo Script

1. Start Streamlit.
2. Upload business rules PDF.
3. Select customer `ORD-1001`.
4. Ask: "My product is not working. What should I do?"
5. Show retrieved sources.
6. Click `Yes, Create Ticket`.
7. Upload product image.
8. Show Image Detection Agent result.
9. Create complaint.
10. Switch to Admin View.
11. Show ticket, email draft, audit log, and inspection dashboard.

## Appendix C: Glossary

| Term | Meaning |
|---|---|
| RAG | Retrieval-Augmented Generation |
| MCP | Model Context Protocol |
| FAISS | Facebook AI Similarity Search |
| LLM | Large Language Model |
| RBAC | Role-Based Access Control |
| PII | Personally Identifiable Information |
| SAST | Static Application Security Testing |
| DAST | Dynamic Application Security Testing |
| OCR | Optical Character Recognition |
