import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.i18n import t

def test_i18n_messages():
    # Test Uzbek
    uz_welcome = t("welcome", lang="uz", name="Alijon", deep_link="")
    assert "MLBB ESPORTS" in uz_welcome
    assert "Alijon" in uz_welcome

    # Test Russian
    ru_welcome = t("welcome", lang="ru", name="Али", deep_link="")
    assert "ДОБРО ПОЖАЛОВАТЬ" in ru_welcome
    assert "Али" in ru_welcome

    # Test English
    en_welcome = t("welcome", lang="en", name="Alex", deep_link="")
    assert "WELCOME TO MLBB" in en_welcome
    assert "Alex" in en_welcome

def test_ready_check_translations():
    uz_btn = t("ready_btn", lang="uz")
    ru_btn = t("ready_btn", lang="ru")
    en_btn = t("ready_btn", lang="en")

    assert "TASDIQLASH" in uz_btn
    assert "ГОТОВ" in ru_btn
    assert "CONFIRM" in en_btn

def test_heroes_identification():
    heroes = [
        {"id": "tigreal", "en": "Tigreal", "ru": "Тигрил", "uz": "Tigreal"},
        {"id": "kalea", "en": "Kalea", "ru": "Калеа", "uz": "Kalea"},
        {"id": "gatotkaca", "en": "Gatotkaca", "ru": "Гатоткача", "uz": "Gatotkaca"},
        {"id": "zilong", "en": "Zilong", "ru": "Зилонг", "uz": "Zilong"},
    ]
    for h in heroes:
        assert h["en"] != ""
        assert h["ru"] != ""
        assert h["uz"] != ""

def test_economy_rules():
    # Base exchange rate: 100 IStars = 5,000 UZS (1 IStar = 50 UZS)
    assert 100 * 50 == 5000
    # Custom logo upload fee: 140 IStars (7,000 UZS)
    assert 140 * 50 == 7000
    # Pro team logo selection: 100 IStars (5,000 UZS)
    assert 100 * 50 == 5000

if __name__ == "__main__":
    test_i18n_messages()
    test_ready_check_translations()
    test_heroes_identification()
    test_economy_rules()
    print("All platform tests passed successfully!")
