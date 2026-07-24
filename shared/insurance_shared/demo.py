"""Stable IDs and party snapshots for demo / seed data across services."""

# Linked to policyholder@insurance.local in the gateway identity DB.
DEMO_PARTY_ID = "00000000-0000-4000-8000-000000000001"
DEMO_POLICY_ID = "00000000-0000-4000-8000-000000000002"
DEMO_INVOICE_ID = "00000000-0000-4000-8000-000000000003"
DEMO_APPLICATION_ID = "00000000-0000-4000-8000-000000000004"
DEMO_INSURED_PARTY_ID = "00000000-0000-4000-8000-000000000005"
DEMO_APPLICATION_NUMBER = "APP-AUTO-DEMO01"

# Extra clients for staff search / multi-product demos
DEMO_PARTY_SAM_ID = "00000000-0000-4000-8000-000000000010"
DEMO_PARTY_RILEY_ID = "00000000-0000-4000-8000-000000000011"
DEMO_PARTY_MORGAN_ID = "00000000-0000-4000-8000-000000000012"
DEMO_PARTY_AVERY_ID = "00000000-0000-4000-8000-000000000013"
DEMO_PARTY_CASEY_ID = "00000000-0000-4000-8000-000000000014"

# Policies
DEMO_HOME_POLICY_ID = "00000000-0000-4000-8000-000000000020"
DEMO_AUTO2_POLICY_ID = "00000000-0000-4000-8000-000000000021"
DEMO_LIFE_POLICY_ID = "00000000-0000-4000-8000-000000000022"
DEMO_CANCELLED_POLICY_ID = "00000000-0000-4000-8000-000000000023"

# Bound / in-flight applications
DEMO_HOME_APPLICATION_ID = "00000000-0000-4000-8000-000000000030"
DEMO_AUTO2_APPLICATION_ID = "00000000-0000-4000-8000-000000000031"
DEMO_LIFE_APPLICATION_ID = "00000000-0000-4000-8000-000000000032"
DEMO_UW_APPLICATION_ID = "00000000-0000-4000-8000-000000000033"
DEMO_REFER_APPLICATION_ID = "00000000-0000-4000-8000-000000000034"
DEMO_CANCELLED_APPLICATION_ID = "00000000-0000-4000-8000-000000000035"

DEMO_HOME_APPLICATION_NUMBER = "APP-HOME-DEMO01"
DEMO_AUTO2_APPLICATION_NUMBER = "APP-AUTO-DEMO02"
DEMO_LIFE_APPLICATION_NUMBER = "APP-LIFE-DEMO01"
DEMO_UW_APPLICATION_NUMBER = "APP-AUTO-DEMOUW"
DEMO_REFER_APPLICATION_NUMBER = "APP-HOME-DEMOREF"
DEMO_CANCELLED_APPLICATION_NUMBER = "APP-AUTO-DEMOCX"

# Quotes (NB tabs)
DEMO_DRAFT_QUOTE_ID = "00000000-0000-4000-8000-000000000040"
DEMO_RATED_QUOTE_ID = "00000000-0000-4000-8000-000000000041"
DEMO_UW_QUOTE_ID = "00000000-0000-4000-8000-000000000042"
DEMO_REFER_QUOTE_ID = "00000000-0000-4000-8000-000000000043"

# Claims
DEMO_CLAIM_OPEN_ID = "00000000-0000-4000-8000-000000000050"
DEMO_CLAIM_PENDING_APPROVAL_ID = "00000000-0000-4000-8000-000000000051"
DEMO_CLAIM_RESERVED_ID = "00000000-0000-4000-8000-000000000052"

# Finance
DEMO_HOME_INVOICE_ID = "00000000-0000-4000-8000-000000000060"
DEMO_PAID_INVOICE_ID = "00000000-0000-4000-8000-000000000061"
DEMO_AUTO2_INVOICE_ID = "00000000-0000-4000-8000-000000000062"

# Underwriting cases
DEMO_UW_CASE_PENDING_ID = "00000000-0000-4000-8000-000000000070"
DEMO_UW_CASE_REFERRED_ID = "00000000-0000-4000-8000-000000000071"


def party_snap(
    party_id: str,
    full_name: str,
    email: str,
    *,
    phone: str | None = None,
    date_of_birth: str | None = None,
    address: str | None = None,
    id_number: str | None = None,
    gender: str = "unspecified",
) -> dict:
    return {
        "id": party_id,
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "date_of_birth": date_of_birth,
        "address": address,
        "id_number": id_number,
        "gender": gender,
    }


ALEX_RIVERA = party_snap(
    DEMO_PARTY_ID,
    "Alex Rivera",
    "policyholder@insurance.local",
    phone="+1-555-0100",
    date_of_birth="1990-04-12",
    address="1200 Meridian Ave, Austin, TX 78701",
    id_number="DRV-DEMO-1001",
)
JORDAN_LEE = party_snap(
    DEMO_INSURED_PARTY_ID,
    "Jordan Lee",
    "jordan.lee@example.com",
    phone="+1-555-0142",
    date_of_birth="1994-08-03",
    address="88 Cedar Lane, Austin, TX 78702",
    id_number="DRV-DEMO-2042",
)
SAM_CHEN = party_snap(
    DEMO_PARTY_SAM_ID,
    "Sam Chen",
    "sam.chen@example.com",
    phone="+1-555-0201",
    date_of_birth="1985-11-21",
    address="410 Oak Street, Dallas, TX 75201",
    id_number="DRV-DEMO-3101",
)
RILEY_QUINN = party_snap(
    DEMO_PARTY_RILEY_ID,
    "Riley Quinn",
    "riley.quinn@example.com",
    phone="+1-555-0202",
    date_of_birth="1988-02-17",
    address="55 Lakeview Dr, Houston, TX 77002",
    id_number="DRV-DEMO-4102",
)
MORGAN_BLAKE = party_snap(
    DEMO_PARTY_MORGAN_ID,
    "Morgan Blake",
    "morgan.blake@example.com",
    phone="+1-555-0203",
    date_of_birth="1992-06-09",
    address="900 Congress Ave, Austin, TX 78701",
    id_number="DRV-DEMO-5103",
)
AVERY_KIM = party_snap(
    DEMO_PARTY_AVERY_ID,
    "Avery Kim",
    "avery.kim@example.com",
    phone="+1-555-0204",
    date_of_birth="1979-12-01",
    address="12 Hillcrest Rd, San Antonio, TX 78205",
    id_number="DRV-DEMO-6104",
)
CASEY_RIVERA = party_snap(
    DEMO_PARTY_CASEY_ID,
    "Casey Rivera",
    "casey.rivera@example.com",
    phone="+1-555-0205",
    date_of_birth="1991-03-28",
    address="77 Riverside, Austin, TX 78704",
    id_number="DRV-DEMO-7105",
)

DEMO_PARTIES = (
    ALEX_RIVERA,
    JORDAN_LEE,
    SAM_CHEN,
    RILEY_QUINN,
    MORGAN_BLAKE,
    AVERY_KIM,
    CASEY_RIVERA,
)
