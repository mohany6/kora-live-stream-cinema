"""
Priority Ingestion Resolver & Arabic Team Alias Matcher.

Enforces the 3-tier hierarchy:
  Admin Override > Sports API / Open Backend > Scraper Ingestion

Normalizes scraped Arabic club names to standard official team names.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import unicodedata
from typing import Optional

from live_score.domain.models import Match, MatchStatus, StreamServer


class TeamAliasMatcher:
    """Normalizes and matches Arabic team aliases to standard English names."""

    _CUSTOM_ALIASES: dict[str, str] = {}

    # Comprehensive dictionary of Arabic names/nicknames to official standard names
    _BASE_ALIASES: dict[str, str] = {
        # Premier League
        "تشيلسي": "Chelsea",
        "البلوز": "Chelsea",
        "ليفربول": "Liverpool",
        "الريدز": "Liverpool",
        "مانشستر سيتي": "Manchester City",
        "مان سيتي": "Manchester City",
        "السيتي": "Manchester City",
        "مانشستر يونايتد": "Manchester United",
        "مان يونايتد": "Manchester United",
        "اليونايتد": "Manchester United",
        "ارسنال": "Arsenal",
        "أرسنال": "Arsenal",
        "الغانرز": "Arsenal",
        "المدفعجية": "Arsenal",
        "توتنهام": "Tottenham Hotspur",
        "توتنهام هوتسبير": "Tottenham Hotspur",
        "السبيرز": "Tottenham Hotspur",
        "نيوكاسل": "Newcastle United",
        "نيوكاسل يونايتد": "Newcastle United",
        "استون فيلا": "Aston Villa",
        "أستون فيلا": "Aston Villa",
        "وست هام": "West Ham United",
        "إيفرتون": "Everton",
        "ايفرتون": "Everton",
        # La Liga
        "ريال مدريد": "Real Madrid",
        "الريال": "Real Madrid",
        "الميرنغي": "Real Madrid",
        "الملكي": "Real Madrid",
        "برشلونة": "Barcelona",
        "برشلونه": "Barcelona",
        "البارسا": "Barcelona",
        "البارشا": "Barcelona",
        "البلوغرانا": "Barcelona",
        "اتلتيكو مدريد": "Atletico Madrid",
        "أتلتيكو مدريد": "Atletico Madrid",
        "اتلتيكو": "Atletico Madrid",
        "أتلتيكو": "Atletico Madrid",
        "الروخيبلانكوس": "Atletico Madrid",
        "اشبيلية": "Sevilla",
        "إشبيلية": "Sevilla",
        "اشبيليه": "Sevilla",
        "إشبيليه": "Sevilla",
        "ريال سوسيداد": "Real Sociedad",
        "سوسيداد": "Real Sociedad",
        "فياريال": "Villarreal",
        "جيرونا": "Girona",
        "فالنسيا": "Valencia",
        "اتلتيك بلباو": "Athletic Bilbao",
        "أتلتيك بلباو": "Athletic Bilbao",
        # Serie A
        "انتر ميلان": "Inter Milan",
        "إنتر ميلان": "Inter Milan",
        "الانتر": "Inter Milan",
        "الإنتر": "Inter Milan",
        "انتر": "Inter Milan",
        "إنتر": "Inter Milan",
        "النيراتزوري": "Inter Milan",
        "ميلان": "AC Milan",
        "اي سي ميلان": "AC Milan",
        "إيه سي ميلان": "AC Milan",
        "الروسونيري": "AC Milan",
        "يوفنتوس": "Juventus",
        "اليوفي": "Juventus",
        "السيدة العجوز": "Juventus",
        "نابولي": "Napoli",
        "روما": "AS Roma",
        "لاتسيو": "Lazio",
        "اتالانتا": "Atalanta",
        "أتالانتا": "Atalanta",
        "فيورنتينا": "Fiorentina",
        # Bundesliga
        "بايرن ميونخ": "Bayern Munich",
        "بايرن ميونيخ": "Bayern Munich",
        "العملاق البافاري": "Bayern Munich",
        "البافاري": "Bayern Munich",
        "بوروسيا دورتموند": "Borussia Dortmund",
        "دورتموند": "Borussia Dortmund",
        "باير ليفركوزن": "Bayer Leverkusen",
        "ليفركوزن": "Bayer Leverkusen",
        "لايبزيج": "RB Leipzig",
        "لايبتزيغ": "RB Leipzig",
        "اينتراخت فرانكفورت": "Eintracht Frankfurt",
        # Ligue 1
        "باريس سان جيرمان": "Paris Saint-Germain",
        "باريس سان-جيرمان": "Paris Saint-Germain",
        "بي اس جي": "Paris Saint-Germain",
        "بي إس جي": "Paris Saint-Germain",
        "باريس": "Paris Saint-Germain",
        "مارسيليا": "Marseille",
        "اولمبيك مارسيليا": "Marseille",
        "موناكو": "Monaco",
        "ليون": "Lyon",
        "اولمبيك ليون": "Lyon",
        "ليل": "Lille",
        # MENA & Arab Leagues
        "الاهلي": "Al Ahly",
        "الأهلي": "Al Ahly",
        "الاهلي المصري": "Al Ahly",
        "الأهلي المصري": "Al Ahly",
        "المارد الاحمر": "Al Ahly",
        "الزمالك": "Zamalek",
        "الزمالك المصري": "Zamalek",
        "الفارس الابيض": "Zamalek",
        "بيراميدز": "Pyramids FC",
        "الهلال": "Al Hilal",
        "الهلال السعودي": "Al Hilal",
        "الزعيم": "Al Hilal",
        "النصر": "Al Nassr",
        "النصر السعودي": "Al Nassr",
        "العالمي": "Al Nassr",
        "الاتحاد": "Al Ittihad",
        "الاتحاد السعودي": "Al Ittihad",
        "العميد": "Al Ittihad",
        "الاهلي السعودي": "Al-Ahli Saudi",
        "الأهلي السعودي": "Al-Ahli Saudi",
        "الراقي": "Al-Ahli Saudi",
        "الشباب": "Al Shabab",
        "الشباب السعودي": "Al Shabab",
        "العين": "Al Ain",
        "العين الاماراتي": "Al Ain",
        "العين الإماراتي": "Al Ain",
        "الوداد": "Wydad AC",
        "الوداد الرياضي": "Wydad AC",
        "الوداد البيضاوي": "Wydad AC",
        "الرجاء": "Raja CA",
        "الرجاء الرياضي": "Raja CA",
        "الرجاء البيضاوي": "Raja CA",
        "الترجي": "Espérance de Tunis",
        "الترجي التونسي": "Espérance de Tunis",
        "الترجي الرياضي": "Espérance de Tunis",
        "الجيش الملكي": "AS FAR",
        "شباب بلوزداد": "CR Belouizdad",
        "مولودية الجزائر": "MC Alger",
        "اتحاد العاصمة": "USM Alger",
        # UEFA Champions League & European additions
        "فايكينج": "Viking FK",
        "فايكنج": "Viking FK",
        "شتوتجارت": "VfB Stuttgart",
        "شتوتغارت": "VfB Stuttgart",
        "إنتر ميلان": "Inter Milan",
        "انتر ميلان": "Inter Milan",
        "شاختار دونيتسك": "Shakhtar Donetsk",
        "شاختار": "Shakhtar Donetsk",
        "فنربخشة": "Fenerbahce",
        "فنربخشه": "Fenerbahce",
        "كلوب بروج": "Club Brugge",
        "بروج": "Club Brugge",
        "سبورتنج لشبونة": "Sporting CP",
        "سبورتينغ لشبونة": "Sporting CP",
        "سلافيا براغ": "Slavia Prague",
        "صباح": "Sabah FK",
        "صباح إف كيه": "Sabah FK",
        "روما": "AS Roma",
    }

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Strips tashkeel, standardizes alefs/yaas/taas, and removes generic prefixes."""
        if not text or not isinstance(text, str):
            return ""

        # Remove tashkeel diacritics
        tashkeel_pattern = re.compile(r"[\u064B-\u065F\u0670]")
        cleaned = tashkeel_pattern.sub("", text)

        # Normalize alefs with hamza / madda
        cleaned = re.sub(r"[إأآٱ]", "ا", cleaned)

        # Normalize yaa / alef maksura
        cleaned = re.sub(r"ى", "ي", cleaned)

        # Strip leading "نادي " or "فريق " prefix
        cleaned = re.sub(r"^(نادي|فريق)\s+", "", cleaned)

        # Normalize taa marbouta (ة -> ه) for matching tolerance
        cleaned = re.sub(r"ة", "ه", cleaned)

        # Normalize multiple spaces and strip
        return re.sub(r"\s+", " ", cleaned).strip()

    _NORMALIZED_BASE: Optional[dict[str, str]] = None

    @classmethod
    def _get_normalized_base(cls) -> dict[str, str]:
        if cls._NORMALIZED_BASE is None:
            base = {
                cls.normalize_text(k): v for k, v in cls._BASE_ALIASES.items()
            }
            # Bidirectional inversion: all canonical Arabic names resolve to standard English names
            for en_name, ar_name in cls._CANONICAL_ARABIC.items():
                norm_ar = cls.normalize_text(ar_name)
                if norm_ar not in base:
                    base[norm_ar] = en_name
            cls._NORMALIZED_BASE = base
        return cls._NORMALIZED_BASE

    @classmethod
    def match_team(cls, arabic_name: Optional[str]) -> Optional[str]:
        """
        Matches an Arabic club name or alias to its standardized English team name.
        Returns None gracefully when unmatched.
        """
        if not arabic_name or not isinstance(arabic_name, str):
            return None

        norm = cls.normalize_text(arabic_name)
        if not norm:
            return None

        # Check custom registered aliases first
        if norm in cls._CUSTOM_ALIASES:
            return cls._CUSTOM_ALIASES[norm]

        # Check pre-compiled base aliases
        normalized_base = cls._get_normalized_base()
        if norm in normalized_base:
            return normalized_base[norm]

        # Suffix strip fallback (e.g. "المصري", "السعودي", "الرياضي")
        stripped_suffix = re.sub(r"\s+(المصري|السعودي|الرياضي|البيضاوي|الاماراتي|التونسي)$", "", norm)
        if stripped_suffix != norm and stripped_suffix in normalized_base:
            return normalized_base[stripped_suffix]

        return None

    @classmethod
    def register_alias(cls, arabic_name: str, standard_name: str) -> None:
        """Dynamically registers or updates a team alias mapping."""
        norm = cls.normalize_text(arabic_name)
        if norm:
            cls._CUSTOM_ALIASES[norm] = standard_name

    _CANONICAL_ARABIC: dict[str, str] = {
        "Chelsea": "تشيلسي",
        "Sabah FK": "صباح إف كيه",
        "Viking FK": "فايكنغ",
        "Slavia Prague": "سلافيا براغ",
        "Liverpool": "ليفربول",
        "Manchester City": "مانشستر سيتي",
        "Manchester United": "مانشستر يونايتد",
        "Arsenal": "أرسنال",
        "Tottenham Hotspur": "توتنهام",
        "Newcastle United": "نيوكاسل",
        "Aston Villa": "أستون فيلا",
        "West Ham United": "وست هام",
        "Everton": "إيفرتون",
        "Real Madrid": "ريال مدريد",
        "Barcelona": "برشلونة",
        "Atletico Madrid": "أتلتيكو مدريد",
        "Sevilla": "إشبيلية",
        "Real Sociedad": "ريال سوسيداد",
        "Villarreal": "فياريال",
        "Girona": "جيرونا",
        "Valencia": "فالنسيا",
        "Athletic Bilbao": "أتلتيك بلباو",
        "Inter Milan": "إنتر ميلان",
        "AC Milan": "ميلان",
        "Juventus": "يوفنتوس",
        "Napoli": "نابولي",
        "AS Roma": "روما",
        "Lazio": "لاتسيو",
        "Atalanta": "أتالانتا",
        "Fiorentina": "فيورنتينا",
        "Bayern Munich": "بايرن ميونخ",
        "Borussia Dortmund": "بوروسيا دورتموند",
        "Bayer Leverkusen": "باير ليفركوزن",
        "RB Leipzig": "لايبزيج",
        "Eintracht Frankfurt": "آينتراخت فرانكفورت",
        "Paris Saint-Germain": "باريس سان جيرمان",
        "Marseille": "مارسيليا",
        "Monaco": "موناكو",
        "Lyon": "ليون",
        "Lille": "ليل",
        "Al Ahly": "الأهلي",
        "Zamalek": "الزمالك",
        "Pyramids FC": "بيراميدز",
        "Al Hilal": "الهلال",
        "Al Nassr": "النصر",
        "Al Ittihad": "الاتحاد",
        "Al-Ahli Saudi": "الأهلي السعودي",
        "Al Shabab": "الشباب",
        "Al Ain": "العين",
        "Wydad AC": "الوداد",
        "Raja CA": "الرجاء",
        "Espérance de Tunis": "الترجي",
        "AS FAR": "الجيش الملكي",
        "CR Belouizdad": "شباب بلوزداد",
        "MC Alger": "مولودية الجزائر",
        "USM Alger": "اتحاد العاصمة",
        # --- Clubs commonly present in the public livescore feed ---
        # England
        "AFC Bournemouth": "بورنموث",
        "Bournemouth": "بورنموث",
        "Brentford": "برينتفورد",
        "Brighton & Hove Albion": "برايتون",
        "Burnley": "بيرنلي",
        "Crystal Palace": "كريستال بالاس",
        "Fulham": "فولهام",
        "Leeds United": "ليدز يونايتد",
        "Nottingham Forest": "نوتنغهام فورست",
        "Sunderland": "سندرلاند",
        "Wolverhampton Wanderers": "وولفرهامبتون",
        "Leicester City": "ليستر سيتي",
        "Southampton": "ساوثهامبتون",
        "Ipswich Town": "إيبسويتش تاون",
        "Sheffield United": "شيفيلد يونايتد",
        "Sheffield Wednesday": "شيفيلد وينزداي",
        "Norwich City": "نوريتش سيتي",
        "Watford": "واتفورد",
        "Middlesbrough": "ميدلسبره",
        "West Bromwich Albion": "وست بروميتش",
        "Stoke City": "ستوك سيتي",
        "Swansea City": "سوانزي سيتي",
        "Cardiff City": "كارديف سيتي",
        "Hull City": "هال سيتي",
        "Coventry City": "كوفنتري سيتي",
        "Derby County": "ديربي كاونتي",
        "Preston North End": "بريستون",
        "Blackburn Rovers": "بلاكبيرن روفرز",
        "Bristol City": "بريستول سيتي",
        "Bristol Rovers": "بريستول روفرز",
        "Millwall": "ميلوول",
        "Queens Park Rangers": "كوينز بارك رينجرز",
        "Charlton Athletic": "تشارلتون أثلتيك",
        "Portsmouth": "بورتسموث",
        "Oxford United": "أكسفورد يونايتد",
        "Wrexham": "ريكسهام",
        "Birmingham City": "بيرمنغهام سيتي",
        "Bolton Wanderers": "بولتون",
        "Barnsley": "بارنسلي",
        "Wigan Athletic": "ويغان أثلتيك",
        "Rotherham United": "روثرهام يونايتد",
        "Lincoln City": "لينكولن سيتي",
        "Leyton Orient": "ليتون أوريانت",
        "Reading": "ريدينغ",
        "Peterborough United": "بيتربورو",
        "Stevenage": "ستيفينيج",
        "Northampton Town": "نورثهامبتون",
        "Burton Albion": "بيرتون ألبيون",
        "Mansfield Town": "مانسفيلد تاون",
        "Doncaster Rovers": "دونكاستر روفرز",
        "Chesterfield": "تشيسترفيلد",
        "Accrington Stanley": "أكرينغتون ستانلي",
        "Barnet": "بارنيت",
        "Boreham Wood": "بوريهام وود",
        "Southend United": "ساوثيند يونايتد",
        "Cheltenham Town": "تشيلتنهام تاون",
        "Colchester United": "كولتشستر يونايتد",
        "Crawley Town": "كرولي تاون",
        "Crewe Alexandra": "كرو ألكساندرا",
        "Exeter City": "إكستر سيتي",
        "Fleetwood Town": "فليتوود تاون",
        "Grimsby Town": "غريمسبي تاون",
        "Salford City": "سالفورد سيتي",
        "Walsall": "والسال",
        "AFC Wimbledon": "ويمبلدون",
        "Notts County": "نوتس كاونتي",
        "Oldham Athletic": "أولدهام",
        # Spain
        "Athletic Club": "أتلتيك بلباو",
        "Real Betis": "ريال بيتيس",
        "Celta Vigo": "سيلتا فيغو",
        "Getafe": "خيتافي",
        "Osasuna": "أوساسونا",
        "Mallorca": "مايوركا",
        "Rayo Vallecano": "رايو فاييكانو",
        "Espanyol": "إسبانيول",
        "Elche": "إلتشي",
        "Levante": "ليفانتي",
        "Alavés": "ألافيس",
        "Real Oviedo": "ريال أوفييدو",
        "FC Andorra": "أندورا",
        "Leganés": "ليغانيس",
        "Eibar": "إيبار",
        "Deportivo": "ديبورتيفو",
        "FC Badalona": "بادالونا",
        # Italy
        "Bologna": "بولونيا",
        "Torino": "تورينو",
        "Udinese": "أودينيزي",
        "Genoa": "جنوى",
        "Cagliari": "كالياري",
        "Como": "كومو",
        "Lecce": "ليتشي",
        "Parma": "بارما",
        "Sassuolo": "ساسولو",
        "Verona": "هيلاس فيرونا",
        "Cremonese": "كريمونيزي",
        "Pisa": "بيزا",
        "Empoli": "إمبولي",
        "Venezia": "فينيسيا",
        "Monza": "مونزا",
        # Germany
        "VfB Stuttgart": "شتوتغارت",
        "VfL Wolfsburg": "فولفسبورغ",
        "SC Freiburg": "فرايبورغ",
        "Mainz 05": "ماينز",
        "Werder Bremen": "فيردر بريمن",
        "TSG Hoffenheim": "هوفنهايم",
        "FC Augsburg": "أوغسبورغ",
        "Union Berlin": "يونيون برلين",
        "Borussia Mönchengladbach": "بوروسيا مونشنغلادباخ",
        "Hamburger SV": "هامبورغ",
        "FC Cologne": "كولونيا",
        "Cologne": "كولونيا",
        "St. Pauli": "سانت باولي",
        "Heidenheim": "هايدنهايم",
        # France
        "Nice": "نيس",
        "Lens": "لانس",
        "Rennes": "رين",
        "Strasbourg": "ستراسبورغ",
        "Nantes": "نانت",
        "Brest": "بريست",
        "Toulouse": "تولوز",
        "Auxerre": "أوكسير",
        "Le Havre AC": "لوهافر",
        "Metz": "ميتز",
        "Lorient": "لوريان",
        "Paris FC": "باريس إف سي",
        "Angers": "أنجيه",
        "Troyes": "تروا",
        # Netherlands
        "Ajax": "أياكس",
        "PSV": "آيندهوفن",
        "AZ Alkmaar": "ألكمار",
        "FC Twente": "تفينتي",
        "FC Utrecht": "أوترخت",
        "FC Groningen": "غرونينغن",
        "Excelsior": "إكسلسيور",
        "Go Ahead Eagles": "غو أهيد إيغلز",
        "Sparta Rotterdam": "سبارتا روتردام",
        "Fortuna Sittard": "فورتونا سيتارد",
        "NEC Nijmegen": "نيميغن",
        "PEC Zwolle": "زفوله",
        "Heracles": "هيراكليس",
        "NAC Breda": "بريدا",
        "Telstar": "تيلستار",
        "Volendam": "فولندام",
        # Portugal
        "Benfica": "بنفيكا",
        "FC Porto": "بورتو",
        "Sporting CP": "سبورتنغ لشبونة",
        "Sporting Lisbon": "سبورتنغ لشبونة",
        "SC Braga": "براغا",
        "Vitória Guimarães": "فيتوريا غيماريش",
        "Famalicão": "فاماليكاو",
        "Boavista": "بوافيستا",
        "Rio Ave": "ريو أفي",
        "Estoril": "إستوريل",
        "Arouca": "أروكا",
        "Moreirense": "موريرينسي",
        "Casa Pia": "كازا بيا",
        "Santa Clara": "سانتا كلارا",
        "Nacional": "ناسيونال",
        "Gil Vicente": "غيل فيسنتي",
        "Estrela Amadora": "إستريلا",
        # Scotland
        "Rangers": "رينجرز",
        "Heart of Midlothian": "هارتس",
        "Hibernian": "هيبرنيان",
        "Motherwell": "مذرويل",
        "St Mirren": "سانت ميرين",
        "Kilmarnock": "كيلمارنوك",
        "Livingston": "ليفينغستون",
        "St Johnstone": "سانت جونستون",
        "Ross County": "روس كاونتي",
        # Belgium
        "Club Brugge": "كلوب بروج",
        "Anderlecht": "أندرلخت",
        "KRC Genk": "غينك",
        "Antwerp": "أنتويرب",
        "Gent": "غينت",
        "Standard Liège": "ستاندار لييج",
        "Cercle Brugge KSV": "سيركل بروج",
        "KVC Westerlo": "فيسترلو",
        "Union Saint-Gilloise": "يونيون سان جيلواز",
        "Mechelen": "ميشيلين",
        "Charleroi": "شارلروا",
        "OH Leuven": "لوفين",
        # Turkey
        "Galatasaray": "غلطة سراي",
        "Fenerbahce": "فنربخشة",
        "Fenerbahçe": "فنربخشة",
        "Besiktas": "بشكتاش",
        "Beşiktaş": "بشكتاش",
        "Trabzonspor": "طرابزون سبور",
        "Basaksehir": "باشاك شهير",
        "Istanbul Basaksehir": "باشاك شهير",
        "Samsunspor": "سامسون سبور",
        "Antalyaspor": "أنطاليا سبور",
        "Konyaspor": "قونية سبور",
        "Kayserispor": "قيصري سبور",
        "Caykur Rizespor": "ريزة سبور",
        "Amed SFK": "أميد سبور",
        "Göztepe": "غوزتبه",
        "Goztepe": "غوزتبه",
        "Kasimpasa": "قاسم باشا",
        "Kasımpaşa": "قاسم باشا",
        "Alanyaspor": "ألانيا سبور",
        "Gaziantep": "غازي عنتاب",
        "Gaziantep FK": "غازي عنتاب",
        "Genclerbirligi": "غينتشلاربيرليغي",
        "Kocaelispor": "كوجالي سبور",
        "Sivasspor": "سيفاسبور",
        "Adana Demirspor": "أضنة ديميرسبور",
        "Eyupspor": "أيوب سبور",
        "Bodrum FK": "بودروم",
        "Hatayspor": "هاتاي سبور",
        "Erzurum BB": "أرضروم سبور",
        "BB Erzurumspor": "أرضروم سبور",
        "Erzurumspor": "أرضروم سبور",
        # Saudi Arabia
        "Al Ahli": "الأهلي السعودي",
        "Al Ettifaq": "الاتفاق",
        "Al Taawoun": "التعاون",
        "Al Fateh": "الفتح",
        "Al Khaleej": "الخليج",
        "Al Riyadh": "الرياض",
        "Al Fayha": "الفيحاء",
        "Al Okhdood": "الأخدود",
        "Al Najma": "النجمة",
        "Al Kholood": "الخلود",
        "Damac": "ضمك",
        "Neom": "نيوم",
        "Al Qadsiah": "القادسية",
        "Al Hazem": "الحزم",
        # United States
        "Inter Miami": "إنتر ميامي",
        "LA Galaxy": "لوس أنجلوس غالاكسي",
        "Los Angeles FC": "لوس أنجلوس",
        "Seattle Sounders FC": "سياتل ساوندرز",
        "Portland Timbers": "بورتلاند تيمبرز",
        "Atlanta United": "أتلانتا يونايتد",
        "Orlando City SC": "أورلاندو سيتي",
        "Columbus Crew": "كولومبوس كرو",
        "New York City FC": "نيويورك سيتي",
        "New York Red Bulls": "نيويورك ريد بولز",
        "Philadelphia Union": "فيلادلفيا يونيون",
        "FC Cincinnati": "سينسيناتي",
        "Real Salt Lake": "ريال سولت ليك",
        "Minnesota United": "مينيسوتا يونايتد",
        "Chicago Fire": "شيكاغو فاير",
        "Toronto FC": "تورونتو",
        "CF Montréal": "مونتريال",
        "Nashville SC": "ناشفيل",
        "Austin FC": "أوستن",
        "Charlotte FC": "شارلوت",
        "D.C. United": "دي سي يونايتد",
        "New England Revolution": "نيو إنغلاند",
        "Colorado Rapids": "كولورادو رابيدز",
        "Houston Dynamo": "هيوستن دينامو",
        "Sporting Kansas City": "سبورتنغ كانساس",
        "San Jose Earthquakes": "سان خوسيه",
        "St. Louis City": "سانت لويس",
        "San Diego FC": "سان دييغو",
        # Mexico
        "Club América": "أمريكا",
        "Chivas Guadalajara": "غوادالاخارا",
        "Cruz Azul": "كروز أزول",
        "Pumas UNAM": "بوماس",
        "Tigres UANL": "تيغريس",
        "Monterrey": "مونتيري",
        "Atlas": "أطلس",
        "Atlante": "أتلانتي",
        "Atlético de San Luis": "أتلتيكو سان لويس",
        "FC Juárez": "خواريز",
        "León": "ليون",
        "Toluca": "تولوكا",
        "Santos Laguna": "سانتوس لاغونا",
        "Tijuana": "تيخوانا",
        "Puebla": "بويبلا",
        "Necaxa": "نيكاكسا",
        "Querétaro": "كيريتارو",
        "Mazatlán": "مازاتلان",
        "Pachuca": "باتشوكا",
        # Argentina
        "Boca Juniors": "بوكا جونيورز",
        "River Plate": "ريفر بليت",
        "Racing Club": "راسينغ",
        "Independiente": "إنديبندينتي",
        "San Lorenzo": "سان لورينزو",
        "Vélez Sarsfield": "فيليز سارسفيلد",
        "Estudiantes": "إستوديانتس",
        "Belgrano (Córdoba)": "بيلغرانو",
        "Talleres": "تاليريس",
        "Lanús": "لانوس",
        "Newell's Old Boys": "نيويلز",
        "Rosario Central": "روزاريو سنترال",
        "Huracán": "هوراكان",
        "Argentinos Juniors": "أرجنتينوس جونيورز",
        "Defensa y Justicia": "ديفينسا",
        "Banfield": "بانفيلد",
        "Instituto": "إنستيتوتو",
        "Godoy Cruz": "غودوي كروز",
        "Platense": "بلاتينسي",
        "Barracas Central": "باراكاس",
        "Central Córdoba": "سنترال كوردوبا",
        "Gimnasia": "جيمناسيا",
        "Sarmiento": "سارمينتو",
        "Aldosivi": "ألدوسيفي",
        # Brazil
        "Flamengo": "فلامنغو",
        "Palmeiras": "بالميراس",
        "Corinthians": "كورينثيانز",
        "São Paulo": "ساو باولو",
        "Santos": "سانتوس",
        "Grêmio": "غريميو",
        "Internacional": "إنترناسيونال",
        "Fluminense": "فلومينينسي",
        "Botafogo": "بوتافوغو",
        "Vasco da Gama": "فاسكو دا غاما",
        "Cruzeiro": "كروزيرو",
        "Atlético Mineiro": "أتلتيكو مينيرو",
        "Atlético-MG": "أتلتيكو مينيرو",
        "Athletico-PR": "أتلتيكو بارانينسي",
        "Athletico Paranaense": "أتلتيكو بارانينسي",
        "Bahia": "باهيا",
        "Fortaleza": "فورتاليزا",
        "Ceará": "سيارا",
        "Sport Recife": "سبورت ريسيفي",
        "Vitória": "فيتوريا",
        "Juventude": "جوفنتودي",
        "Red Bull Bragantino": "براغانتينو",
        "Mirassol": "ميراسول",
        "Coritiba": "كوريتيبا",
        "Remo": "ريمو",
        "Chapecoense": "شابيكوينسي",
        # Japan
        "Kashima Antlers": "كاشيما أنتلرز",
        "Kashiwa Reysol": "كاشيوا ريسول",
        "Vissel Kobe": "فيسيل كوبي",
        "Shimizu S-Pulse": "شيميزو إس-بولس",
        "JEF United Ichihara-Chiba": "جيف يونايتد",
        "Mito Hollyhock": "ميتو هوليهوك",
        "Urawa Reds": "أوراوا ريدز",
        "Kawasaki Frontale": "كاواساكي فرونتال",
        "Yokohama F. Marinos": "يوكوهاما مارينوس",
        "Sanfrecce Hiroshima": "سانفريتسه هيروشيما",
        "Gamba Osaka": "غامبا أوساكا",
        "Cerezo Osaka": "سيريزو أوساكا",
    }

    @staticmethod
    def normalize_english_name(name: Optional[str]) -> str:
        """Fold accents, punctuation and case so upstream spellings can match."""
        if not name or not isinstance(name, str):
            return ""
        decomposed = unicodedata.normalize("NFKD", name)
        ascii_name = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
        ascii_name = ascii_name.lower().replace("&", " and ")
        return re.sub(r"[^a-z0-9]+", " ", ascii_name).strip()

    _NORMALIZED_CANONICAL: Optional[dict[str, str]] = None

    @classmethod
    def _get_normalized_canonical(cls) -> dict[str, str]:
        if cls._NORMALIZED_CANONICAL is None:
            cls._NORMALIZED_CANONICAL = {
                cls.normalize_english_name(en): ar
                for en, ar in cls._CANONICAL_ARABIC.items()
            }
        return cls._NORMALIZED_CANONICAL

    @classmethod
    def get_arabic_name(cls, standard_name: Optional[str]) -> Optional[str]:
        """Returns standard Arabic display name for an official English team name."""
        if not standard_name or not isinstance(standard_name, str):
            return None
        normalized = cls.normalize_english_name(standard_name)
        if not normalized:
            return None
        # Check custom aliases first
        for ar, en in cls._CUSTOM_ALIASES.items():
            if cls.normalize_english_name(en) == normalized:
                return ar
        # Check canonical mapping
        canonical_val = cls._get_normalized_canonical().get(normalized)
        if canonical_val:
            return canonical_val
        # Check base aliases fallback
        for ar, en in cls._BASE_ALIASES.items():
            if cls.normalize_english_name(en) == normalized:
                return ar
        return None


def should_hydrate_channel_stream(
    match: Match,
    now: Optional[datetime] = None,
    window_minutes: int = 30,
) -> bool:
    """
    Evaluates whether a match is in the active broadcast window:
    - Must not be FINISHED or POSTPONED.
    - Must be either currently live (is_live) OR within window_minutes of kickoff.
    """
    if match.status in {MatchStatus.FINISHED, MatchStatus.POSTPONED}:
        return False
    if match.is_live:
        return True

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    kickoff = match.kickoff_time
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)

    return current_time >= (kickoff - timedelta(minutes=window_minutes))


class PriorityResolver:
    """
    Resolves live match data across 3 sources using priority rules:
      1. Admin Override (Highest priority: emergency scores, forced status, stream updates)
      2. Sports API / Open Backend (Scores, fixtures, lineups, elapsed match clock)
      3. Scraper Ingestion (Stream embed links, supplementary regional data)
    """

    @classmethod
    def resolve(
        cls,
        api_match: Optional[Match] = None,
        scraped_match: Optional[Match] = None,
        admin_override: Optional[Match] = None,
        now: Optional[datetime] = None,
    ) -> Match:
        """
        Combines match data according to the strict priority rules.
        At least one source must be non-None.
        """
        if api_match is None and scraped_match is None and admin_override is None:
            raise ValueError("At least one match source must be provided")

        # Case 1: Admin Override is provided (Full precedence)
        if admin_override is not None:
            resolved = admin_override.model_copy(deep=True)
            resolved.is_admin_override = True

            # If admin provided stream servers, admin servers stand
            # If admin did not provide stream servers, inherit from API or Scraper
            if not resolved.stream_servers:
                candidate_servers: list[StreamServer] = []
                if api_match and api_match.stream_servers:
                    candidate_servers.extend(api_match.stream_servers)
                if scraped_match and scraped_match.stream_servers:
                    existing_urls = {s.url for s in candidate_servers}
                    for s in scraped_match.stream_servers:
                        if s.url not in existing_urls:
                            candidate_servers.append(s)
                            existing_urls.add(s.url)
                resolved.stream_servers = candidate_servers

            return resolved

        # Case 2: API Match + Optional Scraped Match (API precedence)
        if api_match is not None:
            resolved = api_match.model_copy(deep=True)
            resolved.is_admin_override = False

            # Merge stream servers from scraper if present
            merged_servers = list(resolved.stream_servers)
            if scraped_match and scraped_match.stream_servers:
                existing_urls = {s.url for s in merged_servers}
                for s in scraped_match.stream_servers:
                    if s.url not in existing_urls:
                        merged_servers.append(s)
                        existing_urls.add(s.url)
            resolved.stream_servers = merged_servers

            # Fill in optional broadcast metadata from scraper if missing in API
            if scraped_match:
                if resolved.channel is None and scraped_match.channel is not None:
                    resolved.channel = scraped_match.channel
                if resolved.commentator is None and scraped_match.commentator is not None:
                    resolved.commentator = scraped_match.commentator
                if resolved.stadium is None and scraped_match.stadium is not None:
                    resolved.stadium = scraped_match.stadium
                if resolved.referee is None and scraped_match.referee is not None:
                    resolved.referee = scraped_match.referee

            # If no stream servers exist, but channel is designated and within broadcast window,
            # auto-hydrate resilient AlbaPlayer stream servers.
            if not resolved.stream_servers and resolved.channel:
                if should_hydrate_channel_stream(resolved, now=now):
                    resolved.stream_servers = ChannelStreamMapper.get_servers(resolved.channel)

            return resolved

        # Case 3: Scraped Match only (Fallback)
        # In this case, scraped_match is guaranteed not None
        assert scraped_match is not None
        resolved = scraped_match.model_copy(deep=True)
        resolved.is_admin_override = False
        if not resolved.stream_servers and resolved.channel:
            if should_hydrate_channel_stream(resolved, now=now):
                resolved.stream_servers = ChannelStreamMapper.get_servers(resolved.channel)
        return resolved


class ChannelStreamMapper:
    """
    Normalizes broadcast channel names (Arabic & English) into verified AlbaPlayer channel slugs
    and generates resilient multi-server stream embed configurations.
    """

    ALBA_BASE_URL: str = "https://24.shootinggames1.com/albaplayer"
    SANDBOX_CONFIG: str = "allow-forms allow-same-origin allow-scripts allow-presentation"

    KNOWN_M3U8: dict[str, str] = {
        "bein-sports-hd-1": "https://ylp.akhbarnewscdn.store/cdn/master.m3u8",
        "bein-sports-hd-3": "https://ylp.akhbarnewscdn.store/cdn/live2/master.m3u8",
    }

    _ARABIC_DIGITS: dict[str, str] = {
        "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5",
        "٦": "6", "٧": "7", "٨": "8", "٩": "9"
    }

    @classmethod
    def normalize_slug(cls, channel_name: Optional[str]) -> Optional[str]:
        if not channel_name or not isinstance(channel_name, str):
            return None

        clean = channel_name.strip().lower()
        for ar_d, en_d in cls._ARABIC_DIGITS.items():
            clean = clean.replace(ar_d, en_d)

        # 1. beIN SPORTS XTRA 1 & 2
        if any(k in clean for k in ["xtra", "extra", "اكسترا", "إكسترا"]):
            if "1" in clean:
                return "bein-sports-xtra-1"
            if "2" in clean:
                return "bein-sports-xtra-2"

        # 2. beIN SPORTS English
        if "english" in clean or "إنجليزية" in clean or "انجليزية" in clean:
            if "1" in clean:
                return "bein-sports-english-1"

        # 3. beIN SPORTS News / الإخبارية
        if "news" in clean or "إخبارية" in clean or "اخبارية" in clean:
            return "bein-sports-news"

        # 4. beIN SPORTS HD 1 to 9
        is_bein = any(k in clean for k in ["bein", "بي ان", "بين", "سبورت"])
        if is_bein:
            # Look for channel numbers 1-9
            match = re.search(r"\b([1-9])\b", clean)
            if match:
                num = match.group(1)
                return f"bein-sports-hd-{num}"

        return None

    @classmethod
    def get_servers(cls, channel_name: Optional[str]) -> list[StreamServer]:
        slug = cls.normalize_slug(channel_name)
        if not slug:
            return []

        servers: list[StreamServer] = []
        if slug in cls.KNOWN_M3U8:
            servers.append(
                StreamServer(
                    id=f"hls_{slug}",
                    server_name="سيرفر 1 - بث مباشر فائق السرعة (FHD)",
                    url=cls.KNOWN_M3U8[slug],
                    type="m3u8",
                    is_active=True,
                    quality="1080p FHD",
                )
            )

        servers.extend([
            StreamServer(
                id=f"alba_{slug}_0",
                server_name=f"سيرفر {len(servers) + 1} - مشغل AlbaPlayer البديل",
                url=f"/api/v1/stream/player/{slug}",
                type="iframe",
                is_active=True,
                quality="multi",
                sandbox=cls.SANDBOX_CONFIG,
            ),
            StreamServer(
                id=f"alba_{slug}_1",
                server_name=f"سيرفر {len(servers) + 2} - مشغل AlbaPlayer (احتياطي)",
                url=f"/api/v1/stream/player/{slug}?serv=1",
                type="iframe",
                is_active=True,
                quality="multi",
                sandbox=cls.SANDBOX_CONFIG,
            ),
        ])
        return servers


__all__ = [
    "TeamAliasMatcher",
    "PriorityResolver",
    "ChannelStreamMapper",
    "should_hydrate_channel_stream",
]
