from live_score.domain.resolver import TeamAliasMatcher

def test_match_team_inverted_canonical():
    assert TeamAliasMatcher.match_team("غلطة سراي") == "Galatasaray"
    assert TeamAliasMatcher.match_team("ريال بيتيس") == "Real Betis"
    assert TeamAliasMatcher.match_team("سيلتا فيغو") == "Celta Vigo"
    assert TeamAliasMatcher.match_team("برايتون") == "Brighton & Hove Albion"
    assert TeamAliasMatcher.match_team("فولفسبورغ") == "VfL Wolfsburg"

def test_get_arabic_name_fallback_base():
    # Sabah FK, Viking FK, Slavia Prague must return valid Arabic names
    assert TeamAliasMatcher.get_arabic_name("Sabah FK") == "صباح إف كيه"
    assert TeamAliasMatcher.get_arabic_name("Viking FK") == "فايكنغ"
    assert TeamAliasMatcher.get_arabic_name("Slavia Prague") == "سلافيا براغ"
