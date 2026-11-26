# -*- coding: utf-8 -*-
from pathlib import Path

script_path = Path(r"C:\Users\Mohany\Desktop\football-live-score-platform\scripts\build_modern_blogger_theme.py")
content = script_path.read_text(encoding="utf-8")

xml_script = '''  <!-- Dynamic Live Sync Script -->
  <script type='text/javascript'><![CDATA[
    var PLATFORM_URL = "{platform_url}";
    var activeDayKey = "today";
    var multiDayData = {json.dumps(MULTI_DAY_DATA, ensure_ascii=False)};
    var FALLBACK_LOGO = "https://cdn-icons-png.flaticon.com/512/53/53283.png";

    function dismissStickyAd() {
      var el = document.getElementById("stickyAdBar");
      if (el) el.style.display = "none";
      try {
        sessionStorage.setItem("kora_blogger_sticky_dismissed", "1");
      } catch(e) {}
    }

    function renderMatchCards(matches) {
      var container = document.getElementById("matchesContainer");
      if (!container || !matches) return;
      var html = "";
      for (var i = 0; i < matches.length; i++) {
        var m = matches[i];
        var matchUrl = PLATFORM_URL + "/match/" + m.id;
        var homeLogo = m.home_logo || (m.home_team && m.home_team.logo_url) || FALLBACK_LOGO;
        var homeName = m.home_name || (m.home_team && m.home_team.name_ar) || "";
        var awayLogo = m.away_logo || (m.away_team && m.away_team.logo_url) || FALLBACK_LOGO;
        var awayName = m.away_name || (m.away_team && m.away_team.name_ar) || "";
        var kTime = m.kickoff_time || m.kickoff_time_local || "20:45";
        var isFin = m.status === "FINISHED" || (m.status_note && m.status_note.indexOf("نهائية") !== -1) || (m.countdown && m.countdown.indexOf("انتهت") !== -1) || activeDayKey === "yesterday";
        var pillText = isFin ? (m.countdown && m.countdown.indexOf("انتهت") !== -1 ? m.countdown : ("انتهت " + (m.home_score||0) + " - " + (m.away_score||0))) : (m.countdown ? ("تبدأ بعد: " + m.countdown) : ("تبدأ: " + kTime));
        var ch = m.channel || "beIN SPORTS";
        var lg = m.league || (m.league && m.league.name_ar) || "دوري أبطال أوروبا";
        var note = m.status_note || (isFin ? "نتيجة نهائية للمباراة" : "سيتم تحديث روابط البث قبل انطلاق المباراة");

        html += '<a href="' + matchUrl + '" target="_blank" class="match-row-card ay-match-compact" data-match-id="' + m.id + '">'
          + '<div class="team-cell home"><div class="team-logo-box"><img src="' + homeLogo + '" alt="' + homeName + '" loading="lazy" onerror="this.onerror=null;this.src=\'' + FALLBACK_LOGO + '\';"/></div><span class="team-name">' + homeName + '</span></div>'
          + '<div class="center-intel-cell"><span class="kickoff-time">' + kTime + '</span><span class="countdown-pill ' + (isFin ? 'finished' : '') + '">' + pillText + '</span>'
          + '<div class="meta-channel-row"><span>📺 ' + ch + '</span><span>• ' + lg + '</span></div><span class="meta-note">' + note + '</span></div>'
          + '<div class="team-cell away"><div class="team-logo-box"><img src="' + awayLogo + '" alt="' + awayName + '" loading="lazy" onerror="this.onerror=null;this.src=\'' + FALLBACK_LOGO + '\';"/></div><span class="team-name">' + awayName + '</span></div></a>'
          + '<div class="ad-card-behind-match"><span>⚡ سيرفر بديل فائق السرعة لمباراة ' + homeName + ' vs ' + awayName + '</span>'
          + '<a href="' + matchUrl + '" target="_blank" style="color:var(--accent-emerald-bright); font-weight:800; text-decoration:none;">' + (isFin ? 'مشاهدة ملخص وأهداف المباراة ↗' : 'مشاهدة البث ↗') + '</a></div>';
      }
      container.innerHTML = html;
    }

    function switchDayTab(dayKey) {
      activeDayKey = dayKey;
      var tabs = ["yesterday", "today", "tomorrow"];
      for (var i = 0; i < tabs.length; i++) {
        var btn = document.getElementById("dayTab_" + tabs[i]);
        if (btn) {
          if (tabs[i] === dayKey) btn.classList.add("active");
          else btn.classList.remove("active");
        }
      }
      var title = document.getElementById("sectionScheduleTitle");
      if (title) {
        if (dayKey === "yesterday") title.innerText = "نتائج مباريات الأمس";
        else if (dayKey === "tomorrow") title.innerText = "مواعيد مباريات الغد";
        else title.innerText = "مباريات اليوم";
      }
      if (multiDayData && multiDayData[dayKey]) {
        renderMatchCards(multiDayData[dayKey]);
      }
      // Dynamic live fetch from API
      if (PLATFORM_URL) {
        var selTz = localStorage.getItem("kora-selected-timezone") || "Asia/Riyadh";
        var dateParam = "";
        var now = new Date();
        if (dayKey === "yesterday") {
          var y = new Date(now.getTime() - 24 * 3600 * 1000);
          dateParam = "&date=" + y.toISOString().slice(0, 10);
        } else if (dayKey === "tomorrow") {
          var t = new Date(now.getTime() + 24 * 3600 * 1000);
          dateParam = "&date=" + t.toISOString().slice(0, 10);
        }
        fetch(PLATFORM_URL + "/api/v1/matches/today?tz=" + encodeURIComponent(selTz) + dateParam)
          .then(function(res) { return res.json(); })
          .then(function(data) {
            if (data && data.matches && data.matches.length > 0) {
              var mapped = data.matches.map(function(m) {
                var isFin = m.status === "FINISHED";
                var cDown = isFin ? ("انتهت " + (m.home_score||0) + " - " + (m.away_score||0)) : (m.countdown_seconds ? "تبدأ قريباً" : (m.kickoff_time_local || "20:45"));
                return {
                  id: m.id,
                  home_name: m.home_team ? m.home_team.name_ar : "",
                  home_logo: m.home_team ? m.home_team.logo_url : FALLBACK_LOGO,
                  away_name: m.away_team ? m.away_team.name_ar : "",
                  away_logo: m.away_team ? m.away_team.logo_url : FALLBACK_LOGO,
                  kickoff_time: m.kickoff_time_local || "20:45",
                  countdown: cDown,
                  status: m.status,
                  home_score: m.home_score,
                  away_score: m.away_score,
                  channel: m.channel || "beIN SPORTS",
                  league: m.league ? m.league.name_ar : "دوري أبطال أوروبا",
                  status_note: isFin ? "نتيجة نهائية • دوري أبطال أوروبا" : "سيتم تحديث روابط البث قبل انطلاق المباراة"
                };
              });
              multiDayData[dayKey] = mapped;
              if (activeDayKey === dayKey) renderMatchCards(mapped);
            }
          })
          .catch(function(e) {});
      }
    }

    function toggleViewMode(mode) {
      if (mode === "compact") document.body.classList.add("compact-mode");
      else document.body.classList.remove("compact-mode");
    }

    function refreshLiveScores() {
      if (!PLATFORM_URL) return;
      var selTz = localStorage.getItem("kora-selected-timezone") || "Asia/Riyadh";
      var fetchUrl = PLATFORM_URL + "/api/v1/matches/today?tz=" + encodeURIComponent(selTz);
      
      fetch(fetchUrl)
        .then(function(res) { return res.json(); })
        .then(function(data) {
          if (data && data.matches && data.matches.length > 0) {
            var mapped = data.matches.map(function(m) {
              var isFin = m.status === "FINISHED";
              var cDown = isFin ? ("انتهت " + (m.home_score||0) + " - " + (m.away_score||0)) : (m.countdown_seconds ? "تبدأ قريباً" : (m.kickoff_time_local || "20:45"));
              return {
                id: m.id,
                home_name: m.home_team ? m.home_team.name_ar : "",
                home_logo: m.home_team ? m.home_team.logo_url : FALLBACK_LOGO,
                away_name: m.away_team ? m.away_team.name_ar : "",
                away_logo: m.away_team ? m.away_team.logo_url : FALLBACK_LOGO,
                kickoff_time: m.kickoff_time_local || "20:45",
                countdown: cDown,
                status: m.status,
                home_score: m.home_score,
                away_score: m.away_score,
                channel: m.channel || "beIN SPORTS",
                league: m.league ? m.league.name_ar : "دوري أبطال أوروبا",
                status_note: isFin ? "نتيجة نهائية • دوري أبطال أوروبا" : "سيتم تحديث روابط البث قبل انطلاق المباراة"
              };
            });
            multiDayData["today"] = mapped;
            if (activeDayKey === "today") {
              renderMatchCards(mapped);
            }
            try {
              localStorage.setItem("kora_cached_matches", JSON.stringify(mapped));
            } catch(e) {}
          }
        })
        .catch(function(err) {
          try {
            var cached = localStorage.getItem("kora_cached_matches");
            if (cached) {
              var parsed = JSON.parse(cached);
              if (parsed && parsed.length > 0) {
                multiDayData["today"] = parsed;
                if (activeDayKey === "today") renderMatchCards(parsed);
              }
            }
          } catch(e) {}
        });
    }

    document.addEventListener("DOMContentLoaded", function() {
      try {
        if (sessionStorage.getItem("kora_blogger_sticky_dismissed") === "1") {
          var bar = document.getElementById("stickyAdBar");
          if (bar) bar.style.display = "none";
        }
      } catch(e) {}
      refreshLiveScores();
    });
  ]]></script>'''

xml_script_fstring = xml_script.replace("{json.dumps(MULTI_DAY_DATA, ensure_ascii=False)}", "___MULTI_DAY_DATA___")
xml_script_fstring = xml_script_fstring.replace("{platform_url}", "___PLATFORM_URL___")
xml_script_fstring = xml_script_fstring.replace("{", "{{").replace("}", "}}")
xml_script_fstring = xml_script_fstring.replace("___MULTI_DAY_DATA___", "{json.dumps(MULTI_DAY_DATA, ensure_ascii=False)}")
xml_script_fstring = xml_script_fstring.replace("___PLATFORM_URL___", "{platform_url}")

xml_script_start = content.find("  <!-- Dynamic Live Sync Script -->\n  <script type='text/javascript'><![CDATA[")
xml_script_end = content.find("</body>\n</html>\n\"\"\"\n    return xml_content")

if xml_script_start != -1 and xml_script_end != -1:
    content = content[:xml_script_start] + xml_script_fstring + "\n" + content[xml_script_end:]
    print("[✓] Updated build_blogger_xml script")
else:
    print(f"[!] Could not find build_blogger_xml script bounds: {xml_script_start}, {xml_script_end}")

script_path.write_text(content, encoding="utf-8")
print("[✓] build_modern_blogger_theme.py updated successfully!")
