import os

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

hindsight = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY")
)

BANK_ID = "engineering-agent"

try:
    hindsight.create_bank(
        bank_id=BANK_ID,
        name="Engineering Agent Memory",
        background="""
        This memory belongs to the Engineering Agent inside Company Brain.

        Store verified engineering facts about system behavior,
        technical limitations, confirmed fixes, architecture decisions,
        incidents, and roadmap information.

        Do not invent technical facts, fixes, deadlines, or capabilities.
        Only store information explicitly confirmed by Engineering.
        """
    )

    print("SUCCESS: Engineering memory bank created.")

except Exception as e:
    print("ERROR:", e)

hindsight.close()