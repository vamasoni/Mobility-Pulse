from config import POSTGRES, CITY_TIMEZONE, START_DATE, END_DATE

def test_config_defaults():
    assert POSTGRES["dbname"] == "mobilitypulse"
    assert CITY_TIMEZONE == "America/New_York"
    assert START_DATE <= END_DATE
