from inspection_agent import inspect_unit


sample_unit = {
    "record_id": "RCV-TEST-001",
    "unit_id": "UNIT-TEST-001",
    "org_id": "org_demo_alpha",
    "captured_at": "2026-09-25T07:30:00Z",
    "operator_id": "operator-test",

    "po_number": "PO-TEST-001",
    "po_line": "1",
    "supplier": "Test Supplier",

    "sku": "BLUE-BOTTLE-001",
    "asin": "B0DUMMY001",
    "product_title": "Blue Bottle",

    "spec_colour": "blue",
    "spec_variant": "standard",
    "spec_components": [
        "bottle",
        "cap"
    ],

    "cartons_ordered": 2,
    "cartons_received": 2,

    "units_per_carton_ordered": 12,
    "units_per_carton_counted": 11,

    "qty_ordered": 24,
    "qty_received": 22,

    "identity_match": "yes",
    "carton_damage": "crushing",
    "unit_damage": "none",

    "quality_flags": ""
}


result = inspect_unit(sample_unit)

print(result)