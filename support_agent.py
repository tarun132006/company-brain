import os
from dotenv import load_dotenv
from hindsight_client import Hindsight
from groq import Groq

load_dotenv()

# -----------------------------
# HINDSIGHT
# -----------------------------

hindsight = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY")
)

BANK_ID = "support-agent"

# -----------------------------
# GROQ
# -----------------------------

groq = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

MODEL = "openai/gpt-oss-120b"


# -----------------------------
# SUPPORT AGENT
# -----------------------------

def ask_support_agent(customer, question):

    print("\n[1/4] Recalling memory from Hindsight...")

    result = hindsight.recall(
        bank_id=BANK_ID,
        query=f"{customer} {question}"
    )

    memories = []

    for memory in result.results:
        memories.append(memory.text)

    memory_context = "\n".join(memories)

    if not memory_context:
        memory_context = "No relevant previous experience was found."

    print("[2/4] Generating support response...")


    # -----------------------------
    # GENERATE ANSWER
    # -----------------------------

    prompt = f"""
You are a SaaS customer support agent.

Customer:
{customer}

Current customer message:
{question}

Relevant memories retrieved from the company's memory system:
{memory_context}

Instructions:

1. Use the memories when they are relevant.
2. Do not invent company-specific facts.
3. Do not claim something happened previously unless the memory supports it.
4. If the available memory is insufficient, say that clearly.
5. Answer the customer's question directly.
6. Keep the answer concise and professional.
"""

    response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a careful SaaS customer support agent."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1
    )

    answer = response.choices[0].message.content


    # -----------------------------
    # EXTRACT NEW MEMORY
    # -----------------------------

    print("[3/4] Learning from this interaction...")

    learning_prompt = f"""
You are the long-term memory manager for a SaaS support agent.

Customer:
{customer}

Customer message:
{question}

Support response:
{answer}

Existing memory:
{memory_context}

Identify ONLY genuinely useful information learned from this
interaction that should be remembered for future support conversations.

Good memories include:

- observed failures
- customer-specific problems
- confirmed workarounds
- successful solutions
- important technical constraints
- repeated issues

Do NOT invent anything.

Return ONLY a short factual memory.

If there is nothing useful to remember, return:

NO_NEW_MEMORY
"""

    learning_response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You extract factual long-term memories from support interactions."
            },
            {
                "role": "user",
                "content": learning_prompt
            }
        ],
        temperature=0
    )

    new_memory = learning_response.choices[0].message.content.strip()


    # -----------------------------
    # STORE MEMORY
    # -----------------------------

    if new_memory != "NO_NEW_MEMORY":

        hindsight.retain(
            bank_id=BANK_ID,
            content=new_memory,
            context=f"Support interaction with {customer}"
        )

        memory_status = "New experience stored in Hindsight."

    else:

        memory_status = "No new long-term memory identified."


    print("[4/4] Done.")

    return answer, new_memory, memory_status


# -----------------------------
# RUN AGENT
# -----------------------------

customer = "Acme"

question = input("\nCustomer question: ")

answer, new_memory, memory_status = ask_support_agent(
    customer,
    question
)


print("\n==============================")
print("SUPPORT AGENT")
print("==============================")

print(answer)


print("\n==============================")
print("WHAT THE AGENT LEARNED")
print("==============================")

print(new_memory)


print("\n==============================")
print("MEMORY STATUS")
print("==============================")

print(memory_status)


hindsight.close()