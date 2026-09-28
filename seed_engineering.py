import os

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

hindsight = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY")
)

BANK_ID = "engineering-agent"

engineering_memory = """
Engineering confirmed that the current CSV export architecture
does not reliably support 1 million rows as a single export.

A capacity rewrite is planned for Q3.
"""

hindsight.retain(
    bank_id=BANK_ID,
    content=engineering_memory,
    context="Confirmed Engineering system-capacity update"
)

print("SUCCESS: Engineering memory stored.")

hindsight.close()