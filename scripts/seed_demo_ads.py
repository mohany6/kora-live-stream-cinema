"""Seed default sample ads into SQLite database for live match monetization."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from live_score.api.store import AdminStore

DB_PATH = str(ROOT / "data" / "live_score.db")

ADS_TO_SEED = [
    {
        "id": "demo-header-1",
        "title": "بانر ليدربورد علوي - تطبيق كورة لايف الرسمي",
        "position": "header_top",
        "ad_type": "image_banner",
        "image_url": "https://placehold.co/970x90/0b1329/38bdf8?text=Kora+Live+-+Official+Sponsor+Leaderboard",
        "link_url": "https://kora-live-to.blogspot.com",
        "target_device": "all",
        "is_active": True,
        "priority": 10,
    },
    {
        "id": "demo-player-top",
        "title": "بانر أعلى المشغل - سيرفرات فائقة السرعة بدون تقطيع",
        "position": "player_top",
        "ad_type": "image_banner",
        "image_url": "https://placehold.co/728x90/0369a1/ffffff?text=Ultra+Fast+FHD+Live+Stream+-+Premium+Access",
        "link_url": "https://kora-live-to.blogspot.com",
        "target_device": "all",
        "is_active": True,
        "priority": 10,
    },
    {
        "id": "demo-player-1",
        "title": "بانر أسفل المشغل - متابعة كافة الدوريات الأوروبية",
        "position": "player_bottom",
        "ad_type": "image_banner",
        "image_url": "https://placehold.co/728x90/0f172a/38bdf8?text=Premium+Stream+Sponsor+-+Click+To+Support",
        "link_url": "https://kora-live-to.blogspot.com",
        "target_device": "all",
        "is_active": True,
        "priority": 10,
    },
    {
        "id": "demo-match-mid",
        "title": "بانر وسط الصفحة - عروض حصرية لمتابعي دوري أبطال أوروبا",
        "position": "match_mid",
        "ad_type": "image_banner",
        "image_url": "https://placehold.co/728x90/1e1b4b/a855f7?text=UEFA+Champions+League+Exclusive+Offers",
        "link_url": "https://kora-live-to.blogspot.com",
        "target_device": "all",
        "is_active": True,
        "priority": 10,
    },
    {
        "id": "demo-tab-native",
        "title": "كارت إعلاني أصلي - التشكيلات والتكتيكات برعاية الشريك",
        "position": "tab_native",
        "ad_type": "image_banner",
        "image_url": "https://placehold.co/600x120/064e3b/34d399?text=Match+Tactics+%26+Lineups+Partner",
        "link_url": "https://kora-live-to.blogspot.com",
        "target_device": "all",
        "is_active": True,
        "priority": 10,
    },
    {
        "id": "demo-sticky-bottom",
        "title": "شريط إعلاني عائم أسفل الشاشة - كورة لايف VIP",
        "position": "sticky_bottom",
        "ad_type": "image_banner",
        "image_url": "https://placehold.co/728x60/0f172a/22d3ee?text=Kora+Live+VIP+-+Join+Our+Telegram+Channel",
        "link_url": "https://kora-live-to.blogspot.com",
        "target_device": "all",
        "is_active": True,
        "priority": 10,
    },
]


def seed_ads():
    store = AdminStore(DB_PATH)
    print(f"Upserting {len(ADS_TO_SEED)} ads into {DB_PATH}...")
    for ad in ADS_TO_SEED:
        store.upsert_ad(ad)
    print("All ads successfully seeded!")
    store.close()


if __name__ == "__main__":
    seed_ads()
