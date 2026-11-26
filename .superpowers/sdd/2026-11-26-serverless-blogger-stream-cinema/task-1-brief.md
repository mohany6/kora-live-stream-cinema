# Task 1 Brief: Top 3-5 Matches Scraper & High-Dwell-Time Content Generator

**Working Directory:** `C:\Users\Mohany\Desktop\football-live-score-platform`
**Python Venv:** `C:\Users\Mohany\Desktop\football-live-score-platform\.venv\Scripts\python.exe`

## Goal
Enhance the Blogger article generator and auto-publisher to create high-dwell-time articles for Blogger (`kora-live-to.blogspot.com`), supporting two stages (pre-match preview and post-match video highlights/tactical summary), capped at the top 3–5 trending matches per day with deduplication.

## Files to Modify/Create
- `src/live_score/domain/article_generator.py`
- `scripts/auto_blogger_publisher.py`
- `tests/test_article_generator.py`

## Detailed Requirements
1. **`src/live_score/domain/article_generator.py`**:
   - Update `generate_blogger_article(match: Mapping[str, Any], platform_base_url: str = "", stage: str = "pre_match") -> dict[str, str]`
   - If `stage == "pre_match"`:
     - Title: `مشاهدة مباراة {home} و{away} بث مباشر اليوم في {competition} | يلا شوت كورة لايف`
     - Content includes Schema.org `SportsEvent`, lineups, referee, stadium, channel, Arabic commentator, and prominent streaming CTA button linking to `https://<stream-domain>/match/{id}`.
     - Labels: `["بث مباشر", competition, "مباريات اليوم"]`
   - If `stage == "post_match"`:
     - Title: `أهداف وملخص مباراة {home} ({home_score} - {away_score}) {away} في {competition} وتفاصيل القمة`
     - Content includes:
       - Responsive 16:9 embedded video highlight player (if `match.get("highlight_embed_url")`, render responsive iframe; else fallback to YouTube official highlights player wrapper).
       - Visual match timeline with icons for goals ⚽, yellow/red cards 🟨 🟥, substitutions 🔄.
       - Comprehensive 800+ word tactical review section analyzing key plays, manager tactics, and standings impact.
       - Interactive "من هو رجل المباراة؟" poll widget.
     - Labels: `["أهداف وملخصات", "أهداف اليوم", competition]`
2. **`scripts/auto_blogger_publisher.py`**:
   - Update `get_top_trending_matches(limit: int = 5)` to strictly select up to 5 highest-ranking matches for today.
   - Implement deduplication using `data/published_articles.json` to prevent re-publishing the same stage for a match.
3. **Tests (`tests/test_article_generator.py`)**:
   - Add tests verifying pre-match and post-match outputs, video embed presence, and label tags.
   - Run: `.\.venv\Scripts\python.exe -m pytest tests/test_article_generator.py` (Must PASS).
   - Run full suite: `.\.venv\Scripts\python.exe -m pytest` (Must PASS all tests).
