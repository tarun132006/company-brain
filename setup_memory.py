import os

from dotenv import load_dotenv
from hindsight_client import Hindsight


load_dotenv()


hindsight = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY")
)


BANK_ID = "support-agent-clean"


try:

    hindsight.create_bank(
        bank_id=BANK_ID,
        name="Support Agent Clean Memory",
        background="""
        This memory belongs to the SaaS Support Agent.

        Store only verified customer-reported problems,
        confirmed workarounds, successful solutions,
        and explicit technical constraints.

        Do not store AI-generated assumptions,
        invented Engineering actions, ETAs, or plans.
        """
    )

    print("SUCCESS: Clean Support memory bank created.")

except Exception as e:

    print("ERROR:", e)


hindsight.close()