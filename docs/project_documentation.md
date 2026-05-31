# LexiFlow Project Documentation

## 1. Project Summary

LexiFlow is an AI-powered customer care demo application. It demonstrates how a
support agent can answer customer questions using business rules documents,
customer/order records, image inspection, and automated support actions.

The project started as a RAG chatbot and has evolved into a realistic
multi-capability customer support system:

- RAG for policy-grounded answers.
- SQLite database for customer/order/ticket context.
- Customer Care Agent flow for eligibility reasoning and complaint handling.
- MCP client/server for product image damage inspection.
- Admin dashboard for tickets and image inspection records.
- Customer View and Admin View separation for exhibition storytelling.

## 2. Business Scenario

The demo represents an ecommerce or electronics support team. A customer asks
questions such as:

- "Can I get a refund after 20 days?"
- "My product is not working. What should I do?"
- "Can I replace this product?"
- "I received a damaged product."

The app checks business policy documents, customer order data, warranty status,
delivery age, previous tickets, and uploaded product images before suggesting
the next support action.

## 3. User Roles

### Customer View

Customer View is used for the customer-facing support conversation.

It contains:

- Active customer context.
- Ticket/email creation status messages.
- Pending complaint confirmation buttons.
- Image upload step when image proof is required.
- Customer conversation and retrieved sources.

### Admin View

Admin View is used by the operator or demo presenter.

It contains:

- Operations dashboard.
- Ticket records.
- Email drafts.
- Audit logs.
- Image inspection reports.
- Document intelligence and source search.

## 4. Functional Capabilities

### 4.1 Business Rules Upload

The sidebar contains `Upload Business Rules documents`.

Uploaded PDFs are:

1. Temporarily saved.
2. Loaded through LangChain PDF loaders.
3. Split into chunks.
4. Embedded using OpenAI embeddings or local embeddings.
5. Stored in FAISS.

The resulting vector database is used to retrieve relevant policy chunks when a
customer asks a question.

### 4.2 Customer Lookup

The sidebar includes a Customer Lookup section. A user can search by:

- order ID,
- email,
- phone number.

The lookup pulls data from SQLite:

- customer name,
- order ID,
- product name,
- serial number,
- delivery date,
- warranty status,
- refund window status,
- replacement window status,
- previous tickets,
- email drafts,
- audit logs.

### 4.3 Customer Care Agent Flow

The Customer Care Agent is implemented as an orchestration flow in `app.py`.
It is not a separate microservice yet.

The agent flow:

1. Receives the user question.
2. Retrieves relevant policy chunks from FAISS.
3. Adds selected customer/order context from SQLite.
4. Adds image inspection context when available.
5. Calls the LLM with a customer-care system prompt.
6. Detects whether a complaint should be offered.
7. Asks for confirmation through buttons.
8. Requests image upload when the issue requires image proof.
9. Creates a ticket and email draft after confirmation.

### 4.4 Complaint Ticket Creation

When the agent detects a support case, it asks:

```text
Create a <issue_type> complaint ticket with <priority> priority?
```

The user confirms using buttons:

- `Yes, Create Ticket`
- `No, Skip`

For image-required cases, the user is first asked to upload a product image.
After image inspection, the ticket can be created.

Ticket data is stored in SQLite.

### 4.5 Email Draft Creation

After ticket creation, the app generates an email draft for the customer.

The draft includes:

- customer name,
- ticket ID,
- order ID,
- product name,
- issue type,
- priority,
- status,
- support follow-up message.

Email drafts are not sent automatically. They are stored for admin review.

### 4.6 Image Detection Agent

The Image Detection Agent inspects uploaded product images.

Current behavior:

- Uses OpenAI vision model when `OPENAI_API_KEY` is available.
- Uses mock fallback when no vision API is available.
- Can be forced into mock mode using `DAMAGE_DETECTION_USE_MOCK=1`.

Future behavior:

- Replace or wrap the OpenAI vision call with the trained product damage ML
  project.
- Keep the MCP tool interface unchanged so the app does not need major changes.

### 4.7 MCP Damage Inspection

The app uses MCP only for image inspection.

Flow:

```text
app.py
  -> mcp_client.py
    -> mcp_server.py
      -> damage_detection_agent.py
```

The MCP server exposes one tool:

```text
inspect_product_damage
```

This keeps the MCP concept clean and easy to explain.

### 4.8 Operations Dashboard

Admin View includes an operations dashboard showing:

- total tickets,
- open tickets,
- high-priority tickets,
- image inspections,
- human-review cases,
- ticket table,
- image inspection table.

This gives the demo an enterprise/customer-care feel instead of being only a
chatbot.

## 5. Core Files

| File | Description |
|---|---|
| `app.py` | Streamlit UI, customer/admin views, customer-care orchestration |
| `rag_pipeline.py` | RAG document loading, chunking, FAISS indexing, retrieval, LLM calls |
| `customer_db.py` | SQLite schema, seed data, tickets, drafts, logs, inspections |
| `damage_detection_agent.py` | Image inspection logic using OpenAI vision or mock fallback |
| `mcp_client.py` | Local MCP client used by Streamlit |
| `mcp_server.py` | Local MCP-style stdio server exposing the damage inspection tool |
| `MCP_USAGE.md` | MCP server usage notes |
| `requirements.txt` | Python dependencies |

## 6. Database Schema

SQLite database path:

```text
data/customer_support.db
```

Main tables:

| Table | Purpose |
|---|---|
| `customers` | Customer identity and tier |
| `orders` | Order, product, serial number, delivery details |
| `warranties` | Warranty status and end date |
| `tickets` | Complaint/support tickets |
| `email_drafts` | Draft emails generated after ticket creation |
| `audit_logs` | User and system action history |
| `damage_inspections` | Persisted image inspection reports |
| `app_metadata` | Demo seed metadata |

## 7. RAG Design

The RAG pipeline uses:

- PDF loader for business rules documents.
- Optional website loader.
- Recursive character text splitting.
- OpenAI embeddings or local HuggingFace embeddings.
- FAISS vector store.
- Query expansion for support topics.
- Priority document matching for refund/replacement/warranty/technical issues.
- LLM prompt that combines retrieved policy context with customer database
  context.

The key design choice is grounding. The agent should not invent policy details.
It must answer from:

- retrieved business rules,
- selected customer/order database record,
- image inspection result.

## 8. Agent Design

LexiFlow currently uses an agent-like orchestration flow inside the app. It is
not a fully separate multi-agent runtime yet.

Current logical agents:

| Logical Agent | Role |
|---|---|
| Customer Care Agent | Handles customer question, policy reasoning, eligibility explanation, complaint flow |
| Image Detection Agent | Inspects product image and returns damage evidence |
| Admin/Operations View | Reviews tickets, drafts, logs, inspections |

Future multi-agent version:

```text
Customer Care Agent
  -> RAG retriever
  -> Customer/order database
  -> Damage Detection Agent through MCP
  -> Ticket/email tools
```

## 9. Demo Flow

Recommended exhibition flow:

1. Upload the business rules PDF.
2. Select sample customer `ORD-1001`.
3. Ask: `My product is not working. What should I do?`
4. Show source-grounded answer.
5. Click `Yes, Create Ticket`.
6. Show image proof request.
7. Upload a product image.
8. Show Image Detection Agent output.
9. Create complaint.
10. Switch to Admin View.
11. Show dashboard, ticket, email draft, and image inspection record.

## 10. Remaining Enhancement

The main remaining technical enhancement is replacing the current vision/mock
damage detection with the trained product damage ML project.

Recommended integration approach:

1. Wrap the trained model behind a Python function or REST endpoint.
2. Keep the current MCP tool name: `inspect_product_damage`.
3. Return the same structured JSON fields.
4. Update `damage_detection_agent.py` to call the trained model.
5. Keep Streamlit, ticket flow, dashboard, and database unchanged.
