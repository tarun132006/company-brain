import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from hindsight_client import Hindsight
from groq import Groq


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# AI SERVICES
# ============================================================

hindsight = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY")
)

groq = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


# ============================================================
# CONFIGURATION
# ============================================================

BANK_ID = "support-agent-clean"

ENGINEERING_BANK_ID = "engineering-agent"

SALES_BANK_ID = "sales-agent"

MODEL = "openai/gpt-oss-120b"


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Company Brain",
    description="Organizational memory for AI agents"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class ChatRequest(BaseModel):
    customer: str
    message: str


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def home():

    return {
        "status": "online",
        "service": "Company Brain",
        "memory": "Hindsight",
        "reasoning": "Groq"
    }


# ============================================================
# SUPPORT AGENT
# ============================================================

@app.post("/api/chat")
def chat(request: ChatRequest):

    customer = request.customer.strip()
    question = request.message.strip()

    # ========================================================
    # 1. RECALL FROM HINDSIGHT
    # ========================================================

    result = hindsight.recall(
        bank_id=BANK_ID,
        query=f"{customer} {question}"
    )

    memories = []

    for memory in result.results:
        memories.append(memory.text)

    if memories:

        memory_context = "\n".join(
            f"- {memory}"
            for memory in memories
        )

    else:

        memory_context = (
            "No relevant previous experience was found."
        )

    # ========================================================
    # 2. ASK GROQ
    # ========================================================

    prompt = f"""
You are the Support Agent inside an AI system called Company Brain.

Customer:
{customer}

Current customer message:
{question}

Relevant organizational memories retrieved from Hindsight:
{memory_context}

IMPORTANT RULES:

1. Treat the retrieved memories as the ONLY source of
   company-specific facts.

2. You may use general reasoning, but NEVER invent internal
   company events, teams, investigations, fixes, ETAs,
   policies, promises, or capabilities.

3. NEVER say that Engineering is investigating, fixing,
   planning, or working on something unless that exact fact
   exists in the retrieved memories.

4. NEVER invent a roadmap, deadline, ETA, technical limit,
   product capability, or company policy.

5. NEVER say:

   "we'll let you know"

   "we are working on it"

   "Engineering is investigating"

   "a fix is coming"

   or similar statements unless the retrieved memory
   explicitly supports the statement.

6. If the memories do not contain enough information to
   answer the question, clearly say that the information
   is not available in company memory.

7. Clearly distinguish confirmed facts from assumptions.

8. Do not turn an assumption into a company fact.

9. Do not claim that a capability is unsupported merely
   because there is no memory confirming it.

10. Answer the customer's question directly.

11. Keep the response concise and professional.
"""

    response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful enterprise support agent "
                    "that relies strictly on verified organizational "
                    "memory."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1
    )

    answer = response.choices[0].message.content.strip()

    # ========================================================
    # 3. LEARN FROM THE INTERACTION
    # ========================================================

    learning_prompt = f"""
You are the long-term memory manager for Company Brain.

Customer:
{customer}

Customer message:
{question}

Previously retrieved verified company memories:
{memory_context}

Your job is to extract ONLY genuinely useful NEW factual
information that was explicitly stated by the customer
in the current message.

IMPORTANT RULES:

1. The customer message is the ONLY source of new information.

2. Do NOT use the Support Agent's answer as evidence.

3. Do NOT invent information.

4. Do NOT infer root causes.

5. Do NOT infer company capabilities or limitations.

6. Do NOT invent Engineering actions, investigations,
   fixes, or plans.

7. Do NOT invent ETAs or deadlines.

8. Do NOT turn questions into facts.

9. Do NOT store conclusions generated by the AI.

10. Do NOT store information that is only present in
    previous memory.

11. Only store facts explicitly stated by the customer.

Useful memories include:

- customer-reported failures
- customer-specific problems
- confirmed workarounds explicitly stated by the customer
- successful solutions explicitly stated by the customer
- technical constraints explicitly stated by the customer
- repeated issues explicitly stated by the customer

Return ONLY one short factual memory.

If the customer did not provide a genuinely new factual
detail, return exactly:

NO_NEW_MEMORY
"""

    learning_response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract only explicitly stated factual "
                    "information from customer interactions for "
                    "long-term organizational memory."
                )
            },
            {
                "role": "user",
                "content": learning_prompt
            }
        ],
        temperature=0
    )

    new_memory = (
        learning_response
        .choices[0]
        .message
        .content
        .strip()
    )

    # ========================================================
    # 4. STORE NEW MEMORY
    # ========================================================

    memory_stored = False

    if new_memory != "NO_NEW_MEMORY":

        hindsight.retain(
            bank_id=BANK_ID,
            content=new_memory,
            context=f"Support interaction with {customer}"
        )

        memory_stored = True

    # ========================================================
    # 5. RETURN RESULT
    # ========================================================

    return {

        "agent": "Support",

        "customer": customer,

        "question": question,

        "answer": answer,

        "memories_used": memories,

        "new_memory": (
            None
            if new_memory == "NO_NEW_MEMORY"
            else new_memory
        ),

        "memory_stored": memory_stored
    }


# ============================================================
# ENGINEERING AGENT
# ============================================================

@app.post("/api/engineering")
def engineering_chat(request: ChatRequest):

    question = request.message.strip()

    # ========================================================
    # 1. RECALL ENGINEERING MEMORY
    # ========================================================

    result = hindsight.recall(
        bank_id=ENGINEERING_BANK_ID,
        query=question
    )

    memories = []

    for memory in result.results:
        memories.append(memory.text)

    if memories:

        memory_context = "\n".join(
            f"- {memory}"
            for memory in memories
        )

    else:

        memory_context = (
            "No relevant Engineering memory was found."
        )

    # ========================================================
    # 2. ASK GROQ
    # ========================================================

    prompt = f"""
You are the Engineering Agent inside Company Brain.

Engineering question:
{question}

Verified Engineering memories retrieved from Hindsight:
{memory_context}

IMPORTANT RULES:

1. Retrieved Engineering memories are the ONLY source of
   company-specific Engineering facts.

2. NEVER add dates, deadlines, ETAs, statuses, progress,
   completion claims, or roadmap details unless they are
   explicitly present in the retrieved memory.

3. NEVER infer that a planned task is currently in progress.

4. NEVER infer that a planned task has been completed.

5. NEVER infer a current status from the current date.

6. NEVER convert a planned Q3 rewrite into:
   "in progress", "underway", "completed", or
   "scheduled to conclude".

7. If a memory says a rewrite is "planned for Q3", report
   exactly that: it is planned for Q3.

8. Clearly distinguish:

   - confirmed current limitations
   - planned work
   - unknown information

9. If the retrieved memories do not contain enough information
   to answer the question, say:

   "That information is not available in Engineering memory."

10. Do not invent technical details.

11. Keep the response concise and professional.

Answer only from the verified Engineering memories.
"""

    response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful Engineering Agent "
                    "that relies strictly on verified "
                    "organizational memory."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1
    )

    answer = response.choices[0].message.content.strip()

    # ========================================================
    # 3. RETURN RESULT
    # ========================================================

    return {

        "agent": "Engineering",

        "question": question,

        "answer": answer,

        "memories_used": memories
    }


# ============================================================
# SALES AGENT
# ============================================================

@app.post("/api/sales")
def sales_chat(request: ChatRequest):

    question = request.message.strip()

    # ========================================================
    # 1. RECALL SUPPORT MEMORY
    # ========================================================

    support_result = hindsight.recall(
        bank_id=BANK_ID,
        query=question
    )

    support_memories = []

    for memory in support_result.results:
        support_memories.append(memory.text)

    # ========================================================
    # 2. RECALL ENGINEERING MEMORY
    # ========================================================

    engineering_result = hindsight.recall(
        bank_id=ENGINEERING_BANK_ID,
        query=question
    )

    engineering_memories = []

    for memory in engineering_result.results:
        engineering_memories.append(memory.text)

    # ========================================================
    # 3. COMBINE CROSS-TEAM MEMORY
    # ========================================================

    all_memories = []

    for memory in support_memories:

        all_memories.append(
            f"[Support Memory] {memory}"
        )

    for memory in engineering_memories:

        all_memories.append(
            f"[Engineering Memory] {memory}"
        )

    if all_memories:

        memory_context = "\n".join(
            f"- {memory}"
            for memory in all_memories
        )

    else:

        memory_context = (
            "No relevant cross-team memory was found."
        )

    # ========================================================
    # 4. ASK GROQ
    # ========================================================

    prompt = f"""
You are the Sales Agent inside Company Brain.

USER'S SALES QUESTION:
{question}

VERIFIED COMPANY MEMORY:
{memory_context}

TASK:

Answer the user's Sales question directly using the
verified company memory above.

The user has already provided a valid question.

NEVER ask the user to provide another question.

GROUNDING RULES:

1. Use the retrieved memories as the ONLY source of
   company-specific facts.

2. Do NOT invent company facts.

3. Do NOT invent product capabilities.

4. Do NOT invent technical limitations.

5. Do NOT invent dates.

6. Do NOT invent deadlines.

7. Do NOT invent ETAs.

8. Do NOT invent roadmap details.

9. Do NOT infer information that is not explicitly
   present in the retrieved memories.

10. Do NOT treat planned Engineering work as completed.

11. Do NOT treat planned Engineering work as currently
    in progress unless the memory explicitly says so.

12. If Engineering memory says:

    "A capacity rewrite is planned for Q3."

    report only that:

    "A capacity rewrite is planned for Q3."

13. NEVER convert Q3 into July, August, September,
    or any other specific dates.

14. NEVER invent a CSV failure threshold.

15. NEVER say that exports above 300,000 rows fail
    unless that exact fact exists in the retrieved memory.

16. If the memories do not explicitly confirm that
    Sales can promise a capability, clearly say:

    "That capability is not confirmed in Company Brain memory."

17. Clearly separate:

    - Confirmed capability
    - Known limitation
    - Planned work
    - Unknown information

18. If Engineering memory says that the current architecture
    does not reliably support 1 million rows as a single export,
    report that fact exactly.

19. If Support memory says that 300,000-row exports timed out
    and smaller batches worked, report that as a Support
    experience. Do not generalize it into a broader technical
    threshold.

20. Do not use today's date to infer project status.

21. Do not make promises on behalf of Engineering.

22. Do not ask for clarification if the user's question
    is already clear.

23. Answer the user's question directly.

24. Keep the response concise and professional.

IMPORTANT SALES DECISION RULE:

If the user asks:

"Can I promise Acme a 1 million row CSV export?"

and the retrieved Engineering memory says:

"Engineering confirmed that the current CSV export architecture
does not reliably support 1 million rows as a single export."

then clearly state:

- The 1 million-row single export is NOT a confirmed capability.
- Sales should NOT promise it as a confirmed capability.
- A capacity rewrite being planned for Q3 does not mean the
  capability is already available.

Do not add any other dates, thresholds, or technical details.

Now answer the user's Sales question directly.
"""

    response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful enterprise Sales Agent "
                    "that uses verified cross-team organizational "
                    "memory before making customer commitments."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1
    )

    answer = response.choices[0].message.content.strip()

    # ========================================================
    # 5. RETURN RESULT
    # ========================================================

    return {

        "agent": "Sales",

        "question": question,

        "answer": answer,

        "memories_used": all_memories
    }


# ============================================================
# ARBITER
# ============================================================

@app.post("/api/arbiter")
def arbiter_chat(request: ChatRequest):

    proposal = request.message.strip()

    # ========================================================
    # 1. RECALL SUPPORT MEMORY
    # ========================================================

    support_result = hindsight.recall(
        bank_id=BANK_ID,
        query=proposal
    )

    support_memories = []

    for memory in support_result.results:
        support_memories.append(memory.text)


    # ========================================================
    # 2. RECALL ENGINEERING MEMORY
    # ========================================================

    engineering_result = hindsight.recall(
        bank_id=ENGINEERING_BANK_ID,
        query=proposal
    )

    engineering_memories = []

    for memory in engineering_result.results:
        engineering_memories.append(memory.text)


    # ========================================================
    # 3. BUILD MEMORY CONTEXT
    # ========================================================

    support_context = (
        "\n".join(
            f"- {memory}"
            for memory in support_memories
        )
        if support_memories
        else "No relevant Support memory found."
    )

    engineering_context = (
        "\n".join(
            f"- {memory}"
            for memory in engineering_memories
        )
        if engineering_memories
        else "No relevant Engineering memory found."
    )


    # ========================================================
    # 4. ASK GROQ TO CHECK FOR CONFLICT
    # ========================================================

    prompt = f"""
You are the Arbiter inside Company Brain.

Your job is to detect contradictions between a proposed
Sales/customer commitment and verified organizational memory.

PROPOSED COMMITMENT:
{proposal}

SUPPORT MEMORY:
{support_context}

ENGINEERING MEMORY:
{engineering_context}


RULES:

1. Support and Engineering memories are the only source
   of company-specific facts.

2. Do not invent facts.

3. Do not invent technical limits.

4. Do not invent dates or deadlines.

5. Do not infer information that is not explicitly stated.

6. A conflict exists only when the proposed commitment
   directly contradicts a verified company fact.

7. If Engineering says the current architecture does not
   reliably support 1 million rows as a single export,
   then a proposal to promise a reliable 1 million-row
   single export is a CONFLICT.

8. A Support observation such as a 300,000-row timeout
   should NOT automatically be treated as a universal
   technical limit.

9. Clearly distinguish:
   - CONFLICT
   - NO CONFLICT
   - INSUFFICIENT INFORMATION

10. Keep the response concise.

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

Decision: CONFLICT / NO CONFLICT / INSUFFICIENT INFORMATION

Reason:
<one or two sentences>

Evidence:
- <relevant memory>
- <relevant memory if needed>

Recommended action:
<short action>


Now evaluate the proposed commitment.
"""

    response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict enterprise conflict arbiter. "
                    "You detect contradictions using verified "
                    "organizational memory and never invent facts."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )


    answer = response.choices[0].message.content.strip()


    # ========================================================
    # 5. RETURN RESULT
    # ========================================================

    all_memories = []

    for memory in support_memories:
        all_memories.append(
            f"[Support Memory] {memory}"
        )

    for memory in engineering_memories:
        all_memories.append(
            f"[Engineering Memory] {memory}"
        )


    return {

        "agent": "Arbiter",

        "proposal": proposal,

        "answer": answer,

        "conflict": "CONFLICT" in answer.upper(),

        "memories_used": all_memories
    }

