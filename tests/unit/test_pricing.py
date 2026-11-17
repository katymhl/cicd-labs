"""Tests unitaires des règles de prix — POINT DE DÉPART (Atelier 1).

Complétez ce fichier : objectif >= 90 % de couverture sur minishop/pricing.py.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from minishop.pricing import line_total, money, quote

pytestmark = pytest.mark.unit


@pytest.fixture
def fake_catalog(monkeypatch):
    products = {
        "p1": SimpleNamespace(id="p1", price=Decimal("1.00")),
        "p10": SimpleNamespace(id="p10", price=Decimal("10.00")),
        "p20": SimpleNamespace(id="p20", price=Decimal("20.00")),
        "p30": SimpleNamespace(id="p30", price=Decimal("30.00")),
        "p49": SimpleNamespace(id="p49", price=Decimal("49.99")),
        "p50": SimpleNamespace(id="p50", price=Decimal("50.00")),
        "p55": SimpleNamespace(id="p55", price=Decimal("55.00")),
    }

    monkeypatch.setattr("minishop.pricing.get_product", lambda product_id: products[product_id])

    return products


def test_money_arrondi_commercial():
    """0.125 s'arrondit à 0.13 (ROUND_HALF_UP), pas 0.12."""
    assert money("0.125") == Decimal("0.13")


def test_line_total_sans_remise():
    assert line_total(Decimal("12.50"), 2) == Decimal("25.00")


def test_quote_panier_vide():
    """Un panier vide coûte 0 € : pas de frais de livraison."""
    q = quote([])
    assert q.total == Decimal("0.00")
    assert q.shipping == Decimal("0.00")


# TODO Atelier 1 :
#  - remise volume à partir de 10 unités (et pas à 9 !)
#  - quantités invalides (0, 100, -1, "2", True) -> ValueError   (astuce : @pytest.mark.parametrize)
#  - coupons WELCOME10 / FIXED5 / FREESHIP (seuils inclus/exclus), coupon inconnu, casse
#  - livraison offerte à partir de 50 € APRÈS remise
#  - produit inconnu -> KeyError
@pytest.mark.parametrize(
    "qty, expected",
    [
        (9, "9.00"),
        (10, "9.50"),
        (11, "10.45"),
    ],
)
def test_remise_volume(qty, expected):
    result = line_total(Decimal("1.00"), qty)
    assert result == Decimal(expected)


@pytest.mark.parametrize("qty", [0, 100, -1, "2", True])
def test_quantites_invalides(qty):
    with pytest.raises(ValueError):
        line_total(Decimal("10.00"), qty)


def test_welcome10(fake_catalog):
    q = quote([{"product_id": "p20", "qty": 1}], "WELCOME10")
    assert q.discount == Decimal("2.00")


def test_welcome10_seuil_non_atteint(fake_catalog):
    q = quote([{"product_id": "p10", "qty": 1}], "WELCOME10")
    assert q.discount == Decimal("0.00")


def test_fixed5(fake_catalog):
    q = quote([{"product_id": "p30", "qty": 1}], "FIXED5")
    assert q.discount == Decimal("5.00")


def test_fixed5_seuil_non_atteint(fake_catalog):
    q = quote([{"product_id": "p20", "qty": 1}], "FIXED5")
    assert q.discount == Decimal("0.00")


def test_freeship(fake_catalog):
    q = quote([{"product_id": "p10", "qty": 1}], "FREESHIP")
    assert q.shipping == Decimal("0.00")


def test_coupon_inconnu(fake_catalog):
    with pytest.raises(ValueError):
        quote([{"product_id": "p20", "qty": 1}], "SUPER10")


def test_coupon_minuscule(fake_catalog):
    q = quote([{"product_id": "p20", "qty": 1}], "welcome10")
    assert q.discount == Decimal("2.00")


def test_coupon_avec_espaces(fake_catalog):
    q = quote([{"product_id": "p20", "qty": 1}], " WELCOME10 ")
    assert q.discount == Decimal("2.00")


def test_livraison_payante(fake_catalog):
    q = quote([{"product_id": "p49", "qty": 1}])
    assert q.shipping == Decimal("4.90")


def test_livraison_gratuite_a_50(fake_catalog):
    q = quote([{"product_id": "p50", "qty": 1}])
    assert q.shipping == Decimal("0.00")


def test_livraison_apres_remise(fake_catalog):
    q = quote([{"product_id": "p55", "qty": 1}], "WELCOME10")

    assert q.subtotal == Decimal("55.00")
    assert q.discount == Decimal("5.50")
    assert q.shipping == Decimal("4.90")


def test_produit_inconnu(fake_catalog):
    with pytest.raises(KeyError):
        quote([{"product_id": "inexistant", "qty": 1}])


def test_quote_as_dict(fake_catalog):
    q = quote([{"product_id": "p20", "qty": 1}])
    result = q.as_dict()

    assert result["subtotal"] == "20.00"
    assert result["total"] == "24.90"
    assert result["lines"][0]["product_id"] == "p20"


def test_money_bug_arrondi(monkeypatch):
    monkeypatch.setenv("MINISHOP_BUG", "rounding")

    assert money("0.125") == Decimal("0.12")


def test_student15_sans_minimum(fake_catalog):
    q = quote([{"product_id": "p1", "qty": 1}], "STUDENT15")

    assert q.subtotal == Decimal("1.00")
    assert q.discount == Decimal("0.15")


def test_student15_non_cumulable_remise_volume(fake_catalog):
    q = quote([{"product_id": "p1", "qty": 10}], "STUDENT15")

    assert q.subtotal == Decimal("9.50")
    assert q.discount == Decimal("0.00")


def test_student15_panier_mixte(fake_catalog):
    q = quote(
        [
            {"product_id": "p10", "qty": 1},
            {"product_id": "p1", "qty": 10},
        ],
        "STUDENT15",
    )

    assert q.subtotal == Decimal("19.50")
    assert q.discount == Decimal("1.50")
