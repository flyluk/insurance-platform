from datetime import date

from sqlalchemy.orm import Session

from app.defaults import RISK_SCHEMAS, UW_RULES
from app.models import Plan, PlanRider, RateVersion, Rider

SEED = [
    {
        "product_code": "AUTO",
        "plan": {
            "code": "AUTO-BASIC",
            "name": "Auto Basic",
            "description": "Compulsory third-party and basic own-damage cover",
            "base_premium": 800.0,
            "sort_order": 1,
        },
        "riders": [
            {
                "code": "AUTO-ROADSIDE",
                "name": "Roadside assistance",
                "description": "Towing and emergency roadside help",
                "premium": 75.0,
                "sort_order": 1,
            },
            {
                "code": "AUTO-GLASS",
                "name": "Glass cover",
                "description": "Windscreen and window glass",
                "premium": 50.0,
                "sort_order": 2,
            },
        ],
    },
    {
        "product_code": "HOME",
        "plan": {
            "code": "HOME-BASIC",
            "name": "Home Basic",
            "description": "Building and contents against fire and theft",
            "base_premium": 1200.0,
            "sort_order": 1,
        },
        "riders": [
            {
                "code": "HOME-FLOOD",
                "name": "Flood cover",
                "description": "Flood and water damage",
                "premium": 180.0,
                "sort_order": 1,
            },
        ],
    },
    {
        "product_code": "LIFE",
        "plan": {
            "code": "LIFE-BASIC",
            "name": "Life Basic",
            "description": "Term life cover",
            "base_premium": 600.0,
            "sort_order": 1,
        },
        "riders": [
            {
                "code": "LIFE-CI",
                "name": "Critical illness",
                "description": "Lump sum on critical illness diagnosis",
                "premium": 220.0,
                "sort_order": 1,
            },
        ],
    },
]


def seed_catalog(db: Session) -> None:
    if db.query(Plan).count() > 0:
        return
    today = date.today()
    for line in SEED:
        code = line["product_code"]
        plan = Plan(
            product_code=code,
            status="PUBLISHED",
            risk_schema=RISK_SCHEMAS.get(code, []),
            uw_rules=UW_RULES.get(code, {"decline": [], "refer": []}),
            **line["plan"],
        )
        db.add(plan)
        db.flush()
        db.add(
            RateVersion(
                plan_id=plan.id,
                version_code="v1",
                amount=plan.base_premium,
                effective_from=today,
                status="PUBLISHED",
            )
        )
        for rider_data in line["riders"]:
            rider = Rider(
                product_code=code,
                status="PUBLISHED",
                **rider_data,
            )
            db.add(rider)
            db.flush()
            db.add(PlanRider(plan_id=plan.id, rider_id=rider.id))
            db.add(
                RateVersion(
                    rider_id=rider.id,
                    version_code="v1",
                    amount=rider.premium,
                    effective_from=today,
                    status="PUBLISHED",
                )
            )
    db.commit()
