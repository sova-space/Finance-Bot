"""backfill transaction categories from MCC lookup

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-04
"""

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

# MCC → category mapping — must stay in sync with domains/sync/mcc.py
_MCC_CATEGORY: dict[int, str] = {
    # Food & Drink
    5811: "Food and Drink", 5812: "Food and Drink",
    5813: "Food and Drink", 5814: "Food and Drink",
    # Groceries
    5411: "Groceries", 5412: "Groceries", 5422: "Groceries",
    5441: "Groceries", 5451: "Groceries", 5462: "Groceries", 5499: "Groceries",
    # Transportation
    4111: "Transportation", 4112: "Transportation", 4121: "Transportation",
    4131: "Transportation", 4784: "Transportation", 4789: "Transportation",
    5171: "Transportation", 5172: "Transportation", 5531: "Transportation",
    5533: "Transportation", 5541: "Transportation", 5542: "Transportation",
    7511: "Transportation", 7512: "Transportation", 7513: "Transportation",
    7523: "Transportation", 7531: "Transportation", 7534: "Transportation",
    7535: "Transportation", 7538: "Transportation", 7542: "Transportation",
    7549: "Transportation",
    # Healthcare
    5047: "Healthcare", 5122: "Healthcare", 5912: "Healthcare",
    7297: "Healthcare", 8011: "Healthcare", 8021: "Healthcare",
    8031: "Healthcare", 8041: "Healthcare", 8042: "Healthcare",
    8043: "Healthcare", 8049: "Healthcare", 8050: "Healthcare",
    8062: "Healthcare", 8071: "Healthcare", 8099: "Healthcare",
    # Shopping
    5200: "Shopping", 5211: "Shopping", 5251: "Shopping",
    5261: "Shopping", 5262: "Shopping", 5310: "Shopping",
    5311: "Shopping", 5331: "Shopping", 5399: "Shopping",
    5611: "Shopping", 5621: "Shopping", 5631: "Shopping",
    5641: "Shopping", 5651: "Shopping", 5655: "Shopping",
    5661: "Shopping", 5691: "Shopping", 5699: "Shopping",
    5712: "Shopping", 5713: "Shopping", 5714: "Shopping",
    5719: "Shopping", 5722: "Shopping", 5731: "Shopping",
    5732: "Shopping", 5733: "Shopping", 5940: "Shopping",
    5941: "Shopping", 5942: "Shopping", 5943: "Shopping",
    5944: "Shopping", 5945: "Shopping", 5946: "Shopping",
    5947: "Shopping", 5948: "Shopping", 5949: "Shopping",
    5992: "Shopping", 5999: "Shopping",
    # Entertainment
    7829: "Entertainment", 7832: "Entertainment", 7841: "Entertainment",
    7922: "Entertainment", 7929: "Entertainment", 7932: "Entertainment",
    7933: "Entertainment", 7941: "Entertainment", 7991: "Entertainment",
    7992: "Entertainment", 7993: "Entertainment", 7994: "Entertainment",
    7995: "Entertainment", 7996: "Entertainment", 7997: "Entertainment",
    7998: "Entertainment", 7999: "Entertainment",
    # Travel
    4411: "Travel", 4511: "Travel", 4722: "Travel",
    7011: "Travel", 7012: "Travel", 7032: "Travel", 7033: "Travel",
    # Subscriptions
    4816: "Subscriptions", 5734: "Subscriptions", 5735: "Subscriptions",
    5818: "Subscriptions", 7372: "Subscriptions", 7374: "Subscriptions",
    7375: "Subscriptions", 7379: "Subscriptions",
    # Utilities
    4814: "Utilities", 4899: "Utilities", 4900: "Utilities",
    4911: "Utilities", 4924: "Utilities", 4931: "Utilities",
    4941: "Utilities", 4961: "Utilities", 4991: "Utilities",
    # ATM / Cash
    6010: "ATM/Cash", 6011: "ATM/Cash", 6051: "ATM/Cash",
    # Finance (including wire transfers)
    4829: "Finance", 6012: "Finance", 6099: "Finance",
    6300: "Finance", 6381: "Finance", 6399: "Finance",
    # Education
    8220: "Education", 8241: "Education", 8244: "Education",
    8249: "Education", 8299: "Education",
    # Pets
    742: "Pets", 5995: "Pets",
}


def upgrade() -> None:
    conn = op.get_bind()
    for mcc, category in _MCC_CATEGORY.items():
        conn.execute(
            sa.text(
                "UPDATE transactions SET category = :cat "
                "WHERE mcc = :mcc AND category IS NULL"
            ),
            {"cat": category, "mcc": mcc},
        )


def downgrade() -> None:
    # Backfill-only — no safe rollback without knowing prior state
    pass
