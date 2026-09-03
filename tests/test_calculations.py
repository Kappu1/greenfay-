from datetime import date
from app.models import TaxRate
from app.routers.dispatch import calculate_tax

def test_calculate_tax_standard():
    tr = TaxRate(
        effective_from=date(2025, 1, 1),
        mandi_rate_per_qtl=5.0,
        vikas_rate_per_qtl=2.5,
        mandi_cap=None,
        vikas_cap=None
    )
    # 25,000 KG = 250 Quintals
    # Mandi = 250 * 5 = 1250
    # Vikas = 250 * 2.5 = 625
    res = calculate_tax(25000, tr)
    assert res['taxable_quintals'] == 250.0
    assert res['mandi_tax'] == 1250.0
    assert res['vikas_sulk'] == 625.0

def test_calculate_tax_with_caps():
    tr = TaxRate(
        effective_from=date(2025, 1, 1),
        mandi_rate_per_qtl=6.0,
        vikas_rate_per_qtl=3.0,
        mandi_cap=2000.0,
        vikas_cap=1000.0
    )
    # 50,000 KG = 500 Quintals
    # Raw Mandi = 500 * 6 = 3000 -> capped at 2000
    # Raw Vikas = 500 * 3 = 1500 -> capped at 1000
    res = calculate_tax(50000, tr)
    assert res['taxable_quintals'] == 500.0
    assert res['mandi_tax'] == 2000.0
    assert res['vikas_sulk'] == 1000.0

def test_calculate_tax_below_caps():
    tr = TaxRate(
        effective_from=date(2025, 1, 1),
        mandi_rate_per_qtl=6.0,
        vikas_rate_per_qtl=3.0,
        mandi_cap=2400.0,
        vikas_cap=1200.0
    )
    # 10,000 KG = 100 Quintals
    # Raw Mandi = 100 * 6 = 600 (< 2400)
    # Raw Vikas = 100 * 3 = 300 (< 1200)
    res = calculate_tax(10000, tr)
    assert res['mandi_tax'] == 600.0
    assert res['vikas_sulk'] == 300.0

def test_calculate_tax_null_rate():
    res = calculate_tax(25000, None)
    assert res['mandi_tax'] == 0
    assert res['vikas_sulk'] == 0

