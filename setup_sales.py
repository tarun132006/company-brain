import os
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

hindsight = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY")
)

BANK_ID = "sales-agent"

try:
    hindsight.create_bank(
        bank_id=BANK_ID,
        name="Sales Agent Memory",
        background="""
        This memory belongs to the Sales Agent inside Company Brain.

        Store verified facts relevant to customer commitments,
        product capabilities, known limitations, customer issues,
        and Engineering updates.

        Never invent product capabilities, commitments,
        deadlines, or roadmap information.
        """
    )

    print("SUCCESS: Sales memory bank created.")

except Exception as e:
    print("ERROR:", e)

hindsight.close()