from datetime import date

def test_full_operational_workflow(auth_client):
    c = auth_client

    # 1. Master Data CRUD
    # Season
    res = c.post("/api/masters/seasons", json={"name": "2025-26", "start_date": "2025-04-01", "end_date": "2026-03-31", "active": True})
    assert res.status_code == 200
    season_id = res.json()["id"]

    # Variety
    res = c.post("/api/masters/varieties", json={"name": "Kufri Pukhraj", "code": "PUKH", "default_seed_packets_per_acre": 25, "default_buyback_bags_per_acre": 250, "active": True})
    assert res.status_code == 200
    variety_id = res.json()["id"]

    # Destination
    res = c.post("/api/masters/destinations", json={"name": "Main Cold Store", "address": "GT Road", "active": True})
    assert res.status_code == 200
    dest_id = res.json()["id"]

    # Tax Rate
    res = c.post("/api/masters/tax-rates", json={
        "effective_from": "2025-01-01",
        "mandi_rate_per_qtl": 5.0,
        "vikas_rate_per_qtl": 2.5,
        "mandi_cap": 2000.0,
        "vikas_cap": 1000.0,
        "active": True
    })
    assert res.status_code == 200

    # 2. Farmer Creation & Duplicate Check
    f_data = {
        "name": "Manpreet Singh",
        "relation_name": "Joginder Singh",
        "relation_type": "Father",
        "mobile": "9812345678",
        "village": "Khakhra Khurd",
        "district": "Hoshiarpur",
        "state": "Punjab"
    }
    res = c.post("/api/farmers", json=f_data)
    assert res.status_code == 200
    farmer_id = res.json()["id"]

    # Attempt duplicate without force -> duplicate_warning returned
    dup_res = c.post("/api/farmers", json={"name": "Manpreet Singh", "mobile": "9812345678", "village": "Khakhra Khurd"})
    assert dup_res.status_code == 200
    assert "duplicate_warning" in dup_res.json()

    # 3. Booking with Variety Lines & Commitments
    booking_payload = {
        "farmer_id": farmer_id,
        "season": "2025-26",
        "season_id": season_id,
        "booking_date": "2025-10-15",
        "agreement_no": "GF-TEST-001",
        "booking_type": "Mixed",
        "total_acres": 5.0,
        "destination": "Main Cold Store",
        "destination_id": dest_id,
        "varieties": [
            {
                "variety": "Kufri Pukhraj",
                "variety_id": variety_id,
                "acres": 5.0,
                "seed_type": "With Seed",
                "planned_seed_packets": 125,
                "expected_buyback_qty": 1250
            }
        ],
        "commitments": [
            {
                "variety_index": 0,
                "contract_month": "January",
                "contract_year": 2026,
                "contracted_bags": 600,
                "buyback_rate": 800,
                "destination": "Main Cold Store"
            },
            {
                "variety_index": 0,
                "contract_month": "February",
                "contract_year": 2026,
                "contracted_bags": 650,
                "buyback_rate": 850,
                "destination": "Main Cold Store"
            }
        ]
    }
    b_res = c.post("/api/bookings", json=booking_payload)
    assert b_res.status_code == 200
    booking_id = b_res.json()["id"]

    # Verify booking detail
    b_detail = c.get(f"/api/bookings/{booking_id}").json()
    assert len(b_detail["varieties"]) == 1
    assert len(b_detail["commitments"]) == 2
    c1_id = b_detail["commitments"][0]["id"]
    c2_id = b_detail["commitments"][1]["id"]
    assert b_detail["commitments"][0]["contracted_bags"] == 600
    assert b_detail["commitments"][0]["received_bags"] == 0
    assert b_detail["commitments"][0]["pending_bags"] == 600
    assert b_detail["commitments"][0]["status"] == "Not Started"

    # 4. Seed Distribution & Payment
    seed_res = c.post("/api/seed/issues", json={
        "booking_id": booking_id,
        "farmer_id": farmer_id,
        "variety": "Kufri Pukhraj",
        "variety_id": variety_id,
        "season_id": season_id,
        "issue_date": "2025-11-01",
        "packets": 100,
        "rate_per_packet": 1500.0,
        "packet_weight_kg": 50,
        "challan_ref": "CH-101"
    })
    assert seed_res.status_code == 200
    seed_id = seed_res.json()["id"]
    assert seed_res.json()["total_value"] == 150000.0

    # Make partial payment
    pay_res = c.post("/api/seed/payments", json={
        "seed_issue_id": seed_id,
        "payment_date": "2025-11-10",
        "amount": 50000.0,
        "mode": "Bank Transfer",
        "reference_no": "TXN12345"
    })
    assert pay_res.status_code == 200

    # Check seed summary
    s_summary = c.get(f"/api/seed/summary/{farmer_id}").json()
    assert s_summary["total_value"] == 150000.0
    assert s_summary["paid"] == 50000.0
    assert s_summary["balance"] == 100000.0
    assert s_summary["status"] == "Partial"

    # 5. Bardana Issue
    bardana_res = c.post("/api/bardana/", json={
        "booking_id": booking_id,
        "farmer_id": farmer_id,
        "issue_date": "2025-12-15",
        "contract_month": "January",
        "bardana_type": "Potato Storage Bag",
        "bags_issued": 600,
        "challan_ref": "BARD-01"
    })
    assert bardana_res.status_code == 200

    # 6. Dispatch in Draft status — verify commitments NOT affected yet
    dsp_res = c.post("/api/dispatches", json={
        "dispatch_date": "2026-01-20",
        "truck_no": "PB10XY9999",
        "destination": "Main Cold Store",
        "destination_id": dest_id,
        "actual_weight_kg": 20000,
        "mandi_weight_kg": 20000,
        "lines": [
            {
                "farmer_id": farmer_id,
                "booking_id": booking_id,
                "commitment_id": c1_id,
                "variety": "Kufri Pukhraj",
                "variety_id": variety_id,
                "bags": 400,
                "weight_kg": 20000
            }
        ]
    })
    assert dsp_res.status_code == 200
    dsp_id = dsp_res.json()["id"]
    assert dsp_res.json()["status"] == "Draft"

    # In Draft status, commitment progress should still be 0 received
    due_draft = c.get("/api/contracts/due").json()
    c1_due = next(x for x in due_draft if x["id"] == c1_id)
    assert c1_due["received_bags"] == 0
    assert c1_due["status"] == "Not Started"

    # 7. Finalize Dispatch -> Commitment progress updates
    fin_res = c.post(f"/api/dispatches/{dsp_id}/finalize")
    assert fin_res.status_code == 200
    assert fin_res.json()["status"] == "Finalized"

    # Verify commitment progress now reflects 400 bags received
    due_fin = c.get("/api/contracts/due").json()
    c1_due = next(x for x in due_fin if x["id"] == c1_id)
    assert c1_due["received_bags"] == 400
    assert c1_due["pending_bags"] == 200
    assert c1_due["status"] == "In Progress"
    assert c1_due["completion_pct"] == 66.67

    # 8. Farmer 360 Summary
    f360 = c.get(f"/api/farmers/{farmer_id}/summary").json()
    assert f360["total_bookings"] == 1
    assert f360["total_acres"] == 5.0
    assert f360["seed_value"] == 150000.0
    assert f360["seed_paid"] == 50000.0
    assert f360["seed_balance"] == 100000.0
    assert f360["bardana_issued"] == 600
    assert f360["contract_bags"] == 1250
    assert f360["potato_received"] == 400
    assert f360["contract_pending"] == 850
    assert f360["payment_status"] == "Partial"

    # 9. Reports (XLSX and PDF exports)
    xlsx_res = c.get("/api/reports/contracts.xlsx")
    assert xlsx_res.status_code == 200
    assert "openxmlformats" in xlsx_res.headers["content-type"]
    assert len(xlsx_res.content) > 1000

    pdf_res = c.get("/api/reports/procurement-due.pdf")
    assert pdf_res.status_code == 200
    assert "pdf" in pdf_res.headers["content-type"]
    assert len(pdf_res.content) > 1000

    # 10. Audit Trail
    audit_res = c.get("/api/audit")
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 5

    # 11. Farmer 360 Tabs
    f_bookings = c.get(f"/api/bookings?farmer_id={farmer_id}")
    assert f_bookings.status_code == 200
    assert len(f_bookings.json()) == 1

    f_seed = c.get(f"/api/farmers/{farmer_id}/seed")
    assert f_seed.status_code == 200
    assert len(f_seed.json()["issues"]) == 1
    assert len(f_seed.json()["payments"]) == 1

    f_bardana = c.get(f"/api/farmers/{farmer_id}/bardana")
    assert f_bardana.status_code == 200
    assert len(f_bardana.json()) == 1

    f_dispatches = c.get(f"/api/farmers/{farmer_id}/dispatches")
    assert f_dispatches.status_code == 200
    assert len(f_dispatches.json()) == 1

    f_audit = c.get(f"/api/farmers/{farmer_id}/audit")
    assert f_audit.status_code == 200

    # 12. Cancellation Workflow & Verification
    # Cancel the finalized dispatch -> verify commitment balance rolls back
    cancel_dsp_res = c.post(f"/api/dispatches/{dsp_id}/cancel", json={"reason": "Incorrect weight recorded"})
    assert cancel_dsp_res.status_code == 200

    due_after_cancel = c.get("/api/contracts/due").json()
    c1_rolled_back = next(x for x in due_after_cancel if x["id"] == c1_id)
    assert c1_rolled_back["received_bags"] == 0
    assert c1_rolled_back["pending_bags"] == 600
    assert c1_rolled_back["status"] == "Not Started"

    # Cancel seed payment
    pay_id = pay_res.json()["id"]
    cancel_pay_res = c.put(f"/api/seed/payments/{pay_id}/cancel", json={"reason": "Bounced cheque"})
    assert cancel_pay_res.status_code == 200

    # Check updated seed summary reflects cancellation
    s_summary_after = c.get(f"/api/seed/summary/{farmer_id}").json()
    assert s_summary_after["paid"] == 0
    assert s_summary_after["balance"] == 150000.0
    assert s_summary_after["status"] == "Not Paid"

    # Cancel bardana
    bard_id = bardana_res.json()["id"]
    cancel_bard_res = c.put(f"/api/bardana/{bard_id}/cancel", json={"reason": "Defective bags returned"})
    assert cancel_bard_res.status_code == 200

    # Check bardana summary reflects cancellation
    b_summary = c.get(f"/api/bardana/summary/{booking_id}").json()
    assert b_summary["issued"] == 0
    assert b_summary["required"] == 1250

    # 13. All 9 XLSX Reports & 4 PDF Reports
    reports_xlsx = [
        "farmers.xlsx", "bookings.xlsx", "contracts.xlsx", "seed-distribution.xlsx",
        "seed-outstanding.xlsx", "bardana.xlsx", "procurement-due.xlsx",
        "dispatch-register.xlsx", "mandi-tax.xlsx"
    ]
    for r in reports_xlsx:
        res = c.get(f"/api/reports/{r}")
        assert res.status_code == 200, f"Failed XLSX: {r}"
        assert len(res.content) > 500

    reports_pdf = [
        "procurement-due.pdf", "dispatch-report.pdf", "dispatch-register.pdf",
        "seed-outstanding.pdf", "mandi-tax.pdf"
    ]
    for r in reports_pdf:
        res = c.get(f"/api/reports/{r}")
        assert res.status_code == 200, f"Failed PDF: {r}"
        assert len(res.content) > 500

    # 14. Dashboard API
    dash = c.get("/api/dashboard").json()
    assert dash["total_farmers"] >= 1
    assert dash["total_bookings"] >= 1
    assert dash["acres"] >= 5.0
