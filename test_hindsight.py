import os
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

client = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY")
)

BANK_ID = "support-agent"

print("Asking Hindsight what it remembers...\n")

result = client.recall(
    bank_id=BANK_ID,
    query="What happened when Acme tried to export a very large CSV?"
)

print("----- HINDSIGHT RECALL -----")

for memory in result.results:
    print(memory.text)

client.close()