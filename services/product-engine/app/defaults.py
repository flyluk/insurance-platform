"""Default risk schemas and UW rules for seeded plans."""

from __future__ import annotations

from typing import Any

RISK_SCHEMAS: dict[str, list[dict[str, Any]]] = {
    "AUTO": [
        {"key": "vehicle_year", "label": "Vehicle year", "type": "number", "required": True, "default": 2022, "min": 1980, "max": 2030, "step": 1},
        {"key": "drivers", "label": "Drivers", "type": "number", "required": True, "default": 1, "min": 1, "max": 10, "step": 1},
        {"key": "prior_claims", "label": "Prior claims", "type": "number", "required": True, "default": 0, "min": 0, "max": 20, "step": 1},
        {"key": "driver_age", "label": "Driver age", "type": "number", "required": True, "default": 34, "min": 16, "max": 100, "step": 1},
    ],
    "HOME": [
        {"key": "property_value", "label": "Property value", "type": "number", "required": True, "default": 320000, "min": 10000, "max": 5000000, "step": 1000},
        {"key": "year_built", "label": "Year built", "type": "number", "required": True, "default": 1998, "min": 1800, "max": 2030, "step": 1},
        {
            "key": "flood_zone",
            "label": "Flood zone",
            "type": "boolean",
            "required": True,
            "default": False,
        },
    ],
    "LIFE": [
        {"key": "insured_age", "label": "Insured age", "type": "number", "required": True, "default": 40, "min": 18, "max": 90, "step": 1},
        {"key": "sum_insured", "label": "Sum insured", "type": "number", "required": True, "default": 400000, "min": 10000, "max": 5000000, "step": 10000},
        {"key": "smoker", "label": "Smoker", "type": "boolean", "required": True, "default": False},
    ],
}

UW_RULES: dict[str, dict[str, Any]] = {
    "AUTO": {
        "decline": [
            {"all": [{"field": "prior_claims", "op": "gte", "value": 3}], "reason": "Too many prior claims"},
        ],
        "refer": [
            {"all": [{"field": "prior_claims", "op": "gte", "value": 1}], "reason": "Elevated auto risk requires manual review"},
            {"all": [{"field": "driver_age", "op": "lt", "value": 25}], "reason": "Elevated auto risk requires manual review"},
            {"all": [{"field": "annual_premium", "op": "gt", "value": 2500}], "reason": "Elevated auto risk requires manual review"},
        ],
    },
    "HOME": {
        "decline": [
            {
                "all": [
                    {"field": "flood_zone", "op": "eq", "value": True},
                    {"field": "property_value", "op": "gt", "value": 500000},
                ],
                "reason": "High-value flood zone exposure",
            },
        ],
        "refer": [
            {"all": [{"field": "property_value", "op": "gt", "value": 750000}], "reason": "Property risk outside auto-bind limits"},
            {"all": [{"field": "year_built", "op": "lt", "value": 1950}], "reason": "Property risk outside auto-bind limits"},
        ],
    },
    "LIFE": {
        "decline": [
            {"all": [{"field": "insured_age", "op": "gt", "value": 70}], "reason": "Age or sum insured exceeds life limits"},
            {"all": [{"field": "sum_insured", "op": "gt", "value": 2000000}], "reason": "Age or sum insured exceeds life limits"},
        ],
        "refer": [
            {"all": [{"field": "insured_age", "op": "gt", "value": 55}], "reason": "Life risk requires medical underwriting"},
            {"all": [{"field": "sum_insured", "op": "gt", "value": 750000}], "reason": "Life risk requires medical underwriting"},
            {"all": [{"field": "smoker", "op": "eq", "value": True}], "reason": "Life risk requires medical underwriting"},
        ],
    },
}
