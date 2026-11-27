import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export interface GoalEventItem {
  player: string;
  minute: string;
  side: string;
}

export interface StatBarItem {
  label: string;
  home: string;
  away: string;
}

export interface MatchReelProps {
  stage: string;
  home_team: string;
  away_team: string;
  home_logo: string;
  away_logo: string;
  home_player_img?: string;
  home_player_name?: string;
  away_player_img?: string;
  away_player_name?: string;
  competition: string;
  channel: string;
  venue?: string;
  commentator?: string;
  home_score: number;
  away_score: number;
  goal_events?: GoalEventItem[];
  stat_bars?: StatBarItem[];
  hook_text: string;
  info_primary: string;
  info_secondary: string;
  engagement_prompt: string;
  cta_text: string;
  audio_file?: string;
  duration_seconds?: number;
}

const PARTICLES = Array.from({ length: 34 }, (_, i) => ({
  x: (i * 137.5) % 100,
  yOffset: (i * 53.1) % 100,
  size: 4 + (i % 5) * 2.5,
  speed: 0.35 + (i % 4) * 0.2,
  gold: i % 3 === 0,
}));

const PerspectivePitch: React.FC<{ frame: number }> = ({ frame }) => {
  const scrollY = (frame * 3.5) % 160;
  return (
    <div
      style={{
        position: "absolute",
        bottom: -140,
        left: -260,
        right: -260,
        height: 980,
        transform: "perspective(820px) rotateX(68deg)",
        transformOrigin: "center bottom",
        opacity: 0.42,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          width: "100%",
          height: "100%",
          background:
            "linear-gradient(180deg, rgba(0,230,118,0) 0%, rgba(0,230,118,0.16) 45%, rgba(0,230,118,0.06) 100%)",
          backgroundImage: `
            repeating-linear-gradient(0deg, rgba(0,230,118,0.22) 0px, rgba(0,230,118,0.22) 3px, transparent 3px, transparent 160px),
            repeating-linear-gradient(90deg, rgba(255,255,255,0.08) 0px, rgba(255,255,255,0.08) 2px, transparent 2px, transparent 180px)
          `,
          backgroundPosition: `0px ${scrollY}px, center 0px`,
          borderTop: "4px solid rgba(0,230,118,0.5)",
        }}
      />
      {/* Center Pitch Circle */}
      <div
        style={{
          position: "absolute",
          top: "36%",
          left: "50%",
          width: 420,
          height: 420,
          marginLeft: -210,
          borderRadius: "50%",
          border: "4px solid rgba(0,230,118,0.35)",
          boxShadow: "0 0 40px rgba(0,230,118,0.2)",
        }}
      />
    </div>
  );
};

const Crest3D: React.FC<{
  name: string;
  logo: string;
  accent: string;
  fromX?: number;
  delay?: number;
  size?: number;
}> = ({ name, logo, accent, fromX = 0, delay = 0, size = 250 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = Math.max(0, frame - delay);
  const s = spring({ frame: f, fps, config: { damping: 11, stiffness: 180 } });
  const tx = interpolate(s, [0, 1], [fromX, 0]);
  const sc = interpolate(s, [0, 1], [0.65, 1]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 18,
        width: 380,
        transform: `translateX(${tx}px) scale(${sc})`,
      }}
    >
      <div style={{ position: "relative", width: size, height: size }}>
        {/* Rotating Telemetry Ring */}
        <div
          style={{
            position: "absolute",
            inset: -14,
            borderRadius: "50%",
            border: `2px dashed ${accent}88`,
            transform: `rotate(${frame * 1.4}deg)`,
          }}
        />
        <div
          style={{
            width: "100%",
            height: "100%",
            borderRadius: 52,
            background:
              "linear-gradient(145deg, rgba(255,255,255,0.14), rgba(8,13,26,0.92))",
            border: `3px solid ${accent}`,
            boxShadow: `0 24px 64px rgba(0,0,0,0.75), 0 0 56px ${accent}55`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 26,
          }}
        >
          {logo ? (
            <Img
              src={logo}
              style={{ width: size * 0.72, height: size * 0.72, objectFit: "contain" }}
            />
          ) : (
            <span style={{ fontSize: 80, fontWeight: 900, color: accent }}>
              {name.slice(0, 2)}
            </span>
          )}
        </div>
      </div>
      <div
        style={{
          fontSize: 42,
          fontWeight: 900,
          color: "#FFFFFF",
          textAlign: "center",
          lineHeight: 1.2,
          textShadow: "0 6px 24px rgba(0,0,0,0.9)",
        }}
      >
        {name}
      </div>
    </div>
  );
};

const PlayerCutout: React.FC<{
  img?: string;
  accent: string;
  side: "right" | "left";
  frame: number;
  fps: number;
}> = ({ img, accent, side, frame, fps }) => {
  if (!img) return null;
  const pop = spring({ frame, fps, config: { damping: 14, stiffness: 120 } });
  const slideX = interpolate(pop, [0, 1], [side === "right" ? 180 : -180, 0]);
  return (
    <div
      style={{
        position: "absolute",
        bottom: 120,
        [side]: -30,
        width: 540,
        height: 620,
        transform: `translateX(${slideX}px) scale(${0.96 + pop * 0.06})`,
        opacity: interpolate(pop, [0, 1], [0, 0.92]),
        pointerEvents: "none",
        WebkitMaskImage: "linear-gradient(to bottom, black 64%, transparent 100%)",
        maskImage: "linear-gradient(to bottom, black 64%, transparent 100%)",
        filter: `drop-shadow(0 0 36px ${accent}66)`,
        zIndex: 5,
      }}
    >
      <Img src={img} style={{ width: "100%", height: "100%", objectFit: "contain", objectPosition: "bottom center" }} />
    </div>
  );
};

export const MatchReel: React.FC<MatchReelProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const scene2Start = 3 * fps;
  const scene3Start = 9 * fps;
  const scene4Start = 14 * fps;

  // Camera shake on impact (frame 10-18) and scene transitions
  const isImpact =
    (frame >= 9 && frame <= 16) ||
    (frame >= scene2Start && frame <= scene2Start + 6) ||
    (frame >= scene3Start && frame <= scene3Start + 6) ||
    (frame >= scene4Start && frame <= scene4Start + 6);

  const shakeX = isImpact ? Math.sin(frame * 2.7) * 10 : 0;
  const shakeY = isImpact ? Math.cos(frame * 3.1) * 8 : 0;

  // White flash frame burst on scene transitions
  const flashOpacity =
    frame >= 9 && frame <= 14
      ? interpolate(frame, [9, 11, 14], [0, 0.35, 0])
      : frame >= scene2Start && frame <= scene2Start + 5
        ? interpolate(frame, [scene2Start, scene2Start + 5], [0.3, 0])
        : frame >= scene3Start && frame <= scene3Start + 5
          ? interpolate(frame, [scene3Start, scene3Start + 5], [0.25, 0])
          : 0;

  const progressPct = interpolate(frame, [0, durationInFrames], [0, 100], {
    extrapolateRight: "clamp",
  });
  const watermarkX = interpolate(frame, [0, durationInFrames], [120, -240]);

  return (
    <AbsoluteFill
      dir="rtl"
      style={{
        backgroundColor: "#040711",
        fontFamily: "'Cairo', 'Segoe UI', Tahoma, sans-serif",
        color: "#F8FAFC",
        overflow: "hidden",
      }}
    >
      <style>
        {`@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@700;900&display=swap');`}
      </style>

      {/* Dual Audio: Procedural Stadium Impact Bed + Crystal-Clear Arabic Voiceover */}
      <Audio src={staticFile("stadium_bed.wav")} volume={0.28} />
      {props.audio_file ? <Audio src={staticFile(props.audio_file)} volume={1.0} /> : null}

      {/* Camera Shake Wrapper */}
      <AbsoluteFill style={{ transform: `translate(${shakeX}px, ${shakeY}px)` }}>
        {/* Deep UCL/ESPN Floodlights */}
        <div
          style={{
            position: "absolute",
            inset: -150,
            background: `
              radial-gradient(circle at 18% 12%, rgba(0,230,118,0.38), transparent 46%),
              radial-gradient(circle at 82% 14%, rgba(56,189,248,0.34), transparent 46%),
              radial-gradient(circle at 50% 85%, rgba(255,179,0,0.22), transparent 52%)
            `,
          }}
        />

        {/* Giant Parallax Background Watermark */}
        <div
          style={{
            position: "absolute",
            top: 420,
            left: -200,
            right: -200,
            fontSize: 220,
            fontWeight: 900,
            color: "rgba(255,255,255,0.035)",
            whiteSpace: "nowrap",
            letterSpacing: 16,
            transform: `translateX(${watermarkX}px) rotate(-6deg)`,
            pointerEvents: "none",
          }}
        >
          KORA LIVE • MATCHDAY • KORA LIVE
        </div>

        {/* 3D Perspective Pitch */}
        <PerspectivePitch frame={frame} />

        {/* 2.5D Star Player Cutouts (Home vs Away) */}
        <PlayerCutout img={props.home_player_img} accent="#00E676" side="right" frame={frame} fps={fps} />
        <PlayerCutout img={props.away_player_img} accent="#38BDF8" side="left" frame={frame} fps={fps} />

        {/* Floating Stadium Sparks / Particles */}
        {PARTICLES.map((p, idx) => {
          const py = (p.yOffset - frame * p.speed + 200) % 105;
          return (
            <div
              key={idx}
              style={{
                position: "absolute",
                left: `${p.x}%`,
                top: `${py}%`,
                width: p.size,
                height: p.size,
                borderRadius: "50%",
                background: p.gold ? "#FFB300" : "#00E676",
                opacity: 0.45,
                boxShadow: `0 0 12px ${p.gold ? "#FFB300" : "#00E676"}`,
              }}
            />
          );
        })}

        {/* Top Broadcast Bar */}
        <div
          style={{
            position: "absolute",
            top: 84,
            left: 52,
            right: 52,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            zIndex: 30,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              background: "rgba(8, 13, 26, 0.88)",
              border: "1px solid rgba(0,230,118,0.5)",
              padding: "12px 26px",
              borderRadius: 14,
              boxShadow: "0 12px 32px rgba(0,0,0,0.6)",
            }}
          >
            <div
              style={{
                width: 12,
                height: 12,
                borderRadius: "50%",
                background: "#EF4444",
                boxShadow: "0 0 14px #EF4444",
              }}
            />
            <span style={{ fontSize: 30, fontWeight: 900 }}>كورة لايف</span>
          </div>

          <div
            style={{
              background: "linear-gradient(135deg, rgba(255,179,0,0.2), rgba(15,23,42,0.9))",
              border: "1px solid rgba(255,179,0,0.55)",
              padding: "12px 24px",
              borderRadius: 14,
              fontSize: 26,
              fontWeight: 900,
              color: "#FFB300",
            }}
          >
            {props.competition}
          </div>
        </div>

        {/* SCENE 1 (0-3s): Diagonal Split-Screen Clash & 3s Viral Hook */}
        <Sequence from={0} durationInFrames={scene2Start}>
          <AbsoluteFill>
            {/* Diagonal Split Backdrop */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                background:
                  "linear-gradient(135deg, rgba(0,230,118,0.18) 0%, transparent 49%, rgba(56,189,248,0.18) 51%, transparent 100%)",
              }}
            />
            <div
              style={{
                position: "absolute",
                top: "50%",
                left: -100,
                right: -100,
                height: 4,
                background: "linear-gradient(90deg, #00E676, #FFB300, #38BDF8)",
                transform: "rotate(-22deg)",
                boxShadow: "0 0 30px rgba(255,179,0,0.8)",
                opacity: 0.7,
              }}
            />

            <AbsoluteFill
              style={{
                justifyContent: "center",
                alignItems: "center",
                padding: "0 54px",
                gap: 54,
              }}
            >
              <div
                style={{
                  background: "linear-gradient(135deg, #FFB300, #F59E0B)",
                  color: "#040711",
                  fontSize: 34,
                  fontWeight: 900,
                  padding: "12px 42px",
                  borderRadius: 12,
                  boxShadow: "0 0 40px rgba(255,179,0,0.55)",
                  transform: `scale(${spring({ frame, fps, config: { damping: 10 } })})`,
                }}
              >
                {props.stage === "post_match" ? "صافرة النهاية • ملخص القمة" : "صدام ناري مرتقب"}
              </div>

              <div
                style={{
                  fontSize: 74,
                  fontWeight: 900,
                  textAlign: "center",
                  lineHeight: 1.3,
                  textShadow: "0 12px 48px rgba(0,0,0,0.95)",
                  transform: `scale(${interpolate(frame, [0, 10], [1.18, 1], {
                    extrapolateRight: "clamp",
                    easing: Easing.out(Easing.cubic),
                  })})`,
                }}
              >
                {props.hook_text}
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
                <Crest3D name={props.home_team} logo={props.home_logo} accent="#00E676" fromX={260} delay={2} size={230} />
                <div
                  style={{
                    fontSize: 64,
                    fontWeight: 900,
                    color: "#FFB300",
                    textShadow: "0 0 36px rgba(255,179,0,0.8)",
                  }}
                >
                  VS
                </div>
                <Crest3D name={props.away_team} logo={props.away_logo} accent="#38BDF8" fromX={-260} delay={4} size={230} />
              </div>
            </AbsoluteFill>
          </AbsoluteFill>
        </Sequence>

        {/* SCENE 2 (3-9s): 3D Broadcast Matchup HUD */}
        <Sequence from={scene2Start} durationInFrames={scene3Start - scene2Start}>
          <AbsoluteFill
            style={{
              justifyContent: "center",
              alignItems: "center",
              padding: "0 48px",
              gap: 54,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
              <Crest3D name={props.home_team} logo={props.home_logo} accent="#00E676" size={245} />
              <div
                style={{
                  background: "rgba(8, 13, 26, 0.94)",
                  border: "3px solid #FFB300",
                  borderRadius: 24,
                  padding: "22px 34px",
                  fontSize: 64,
                  fontWeight: 900,
                  color: "#FFB300",
                  minWidth: 175,
                  textAlign: "center",
                  boxShadow: "0 0 50px rgba(255,179,0,0.35)",
                }}
              >
                {props.stage === "post_match"
                  ? `${props.home_score} - ${props.away_score}`
                  : "VS"}
              </div>
              <Crest3D name={props.away_team} logo={props.away_logo} accent="#38BDF8" size={245} />
            </div>

            <div
              style={{
                width: "100%",
                background: "linear-gradient(160deg, rgba(12,20,38,0.92), rgba(5,8,18,0.96))",
                border: "1px solid rgba(255,255,255,0.16)",
                borderTop: "4px solid #00E676",
                borderBottom: "4px solid #38BDF8",
                borderRadius: 28,
                padding: "46px 36px",
                textAlign: "center",
                boxShadow: "0 30px 80px rgba(0,0,0,0.75)",
              }}
            >
              <div style={{ fontSize: 44, fontWeight: 900, color: "#00E676", marginBottom: 16 }}>
                {props.info_primary}
              </div>
              <div style={{ fontSize: 32, fontWeight: 700, color: "#E2E8F0" }}>
                {props.info_secondary}
              </div>
              {props.stage === "post_match" && props.goal_events && props.goal_events.length > 0 ? (
                <div
                  style={{
                    marginTop: 28,
                    paddingTop: 22,
                    borderTop: "1px solid rgba(255,255,255,0.12)",
                    display: "flex",
                    flexWrap: "wrap",
                    justifyContent: "center",
                    gap: 14,
                  }}
                >
                  {props.goal_events.slice(0, 6).map((g, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: g.side === "away" ? "rgba(56,189,248,0.16)" : "rgba(0,230,118,0.16)",
                        border: `1px solid ${g.side === "away" ? "#38BDF8" : "#00E676"}`,
                        borderRadius: 999,
                        padding: "8px 22px",
                        fontSize: 26,
                        fontWeight: 700,
                        color: "#FFFFFF",
                      }}
                    >
                      {g.player} {g.minute ? `(${g.minute})` : ""}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </AbsoluteFill>
        </Sequence>

        {/* SCENE 3 (9-14s): Match Stats HUD (for post_match) OR Fan Poll & Debate Trigger */}
        <Sequence from={scene3Start} durationInFrames={scene4Start - scene3Start}>
          <AbsoluteFill
            style={{
              justifyContent: "center",
              alignItems: "center",
              padding: "0 56px",
              gap: 36,
            }}
          >
            <div
              style={{
                background: "rgba(0, 230, 118, 0.16)",
                border: "2px solid #00E676",
                color: "#00E676",
                fontSize: 34,
                fontWeight: 900,
                padding: "12px 36px",
                borderRadius: 14,
              }}
            >
              {props.stage === "post_match" && props.stat_bars && props.stat_bars.length > 0
                ? "إحصائيات القمة الكاملة"
                : "تحدي التوقعات • شارك برأيك"}
            </div>

            {props.stage === "post_match" && props.stat_bars && props.stat_bars.length > 0 ? (
              <div
                style={{
                  width: "100%",
                  background: "linear-gradient(145deg, rgba(12,22,42,0.95), rgba(5,8,18,0.98))",
                  border: "2px solid rgba(0,230,118,0.45)",
                  borderRadius: 34,
                  padding: "40px 42px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 26,
                  boxShadow: "0 0 80px rgba(0,230,118,0.2)",
                }}
              >
                {props.stat_bars.slice(0, 4).map((st, idx) => {
                  const hNum = parseFloat(st.home.replace(/[^0-9.]/g, "")) || 1;
                  const aNum = parseFloat(st.away.replace(/[^0-9.]/g, "")) || 1;
                  const pct = Math.round((hNum / Math.max(1, hNum + aNum)) * 100);
                  const animPct = interpolate(frame - scene3Start, [0, 30], [50, pct], {
                    extrapolateRight: "clamp",
                  });
                  return (
                    <div key={idx} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 30, fontWeight: 900 }}>
                        <span style={{ color: "#00E676" }}>{st.home}</span>
                        <span style={{ color: "#E2E8F0" }}>{st.label}</span>
                        <span style={{ color: "#38BDF8" }}>{st.away}</span>
                      </div>
                      <div style={{ height: 14, borderRadius: 999, background: "#38BDF8", overflow: "hidden", display: "flex" }}>
                        <div style={{ width: `${animPct}%`, background: "#00E676" }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div
                style={{
                  width: "100%",
                  background: "linear-gradient(145deg, rgba(12,22,42,0.95), rgba(5,8,18,0.98))",
                  border: "2px solid rgba(56,189,248,0.5)",
                  borderRadius: 34,
                  padding: "54px 44px",
                  textAlign: "center",
                  boxShadow: "0 0 80px rgba(56,189,248,0.22)",
                }}
              >
                <div style={{ fontSize: 54, fontWeight: 900, lineHeight: 1.45, marginBottom: 36 }}>
                  {props.engagement_prompt}
                </div>

                {/* Animated Prediction Bar */}
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 28, fontWeight: 900, marginBottom: 12 }}>
                  <span style={{ color: "#00E676" }}>{props.home_team}</span>
                  <span style={{ color: "#38BDF8" }}>{props.away_team}</span>
                </div>
                <div style={{ height: 18, borderRadius: 999, background: "#38BDF8", overflow: "hidden", display: "flex" }}>
                  <div
                    style={{
                      width: `${interpolate(frame - scene3Start, [0, 45], [50, 58], { extrapolateRight: "clamp" })}%`,
                      background: "#00E676",
                    }}
                  />
                </div>
              </div>
            )}
          </AbsoluteFill>
        </Sequence>

        {/* SCENE 4 (14-18s): High-Conversion First-Comment CTA + Loop */}
        <Sequence from={scene4Start} durationInFrames={durationInFrames - scene4Start}>
          <AbsoluteFill
            style={{
              justifyContent: "center",
              alignItems: "center",
              padding: "0 56px",
              gap: 38,
            }}
          >
            <svg
              width="124"
              height="124"
              viewBox="0 0 24 24"
              fill="none"
              style={{
                transform: `translateY(${Math.sin(frame * 0.3) * 18}px)`,
                filter: "drop-shadow(0 0 28px rgba(255,179,0,0.8))",
              }}
            >
              <path
                d="M12 4v14m0 0l-6-6m6 6l6-6"
                stroke="#FFB300"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>

            <div
              style={{
                background: "linear-gradient(135deg, #FFB300, #F59E0B)",
                color: "#040711",
                fontSize: 48,
                fontWeight: 900,
                padding: "20px 54px",
                borderRadius: 16,
                boxShadow: "0 18px 50px rgba(255,179,0,0.45)",
              }}
            >
              الرابط في أول تعليق
            </div>
            <div
              style={{
                fontSize: 46,
                fontWeight: 900,
                textAlign: "center",
                lineHeight: 1.45,
                color: "#FFFFFF",
              }}
            >
              {props.cta_text}
            </div>
          </AbsoluteFill>
        </Sequence>
      </AbsoluteFill>

      {/* Flash Frame Burst */}
      {flashOpacity > 0 ? (
        <AbsoluteFill style={{ backgroundColor: "#FFFFFF", opacity: flashOpacity, pointerEvents: "none" }} />
      ) : null}

      {/* Bottom Broadcast Progress Bar */}
      <div
        style={{
          position: "absolute",
          bottom: 72,
          left: 52,
          right: 52,
          height: 10,
          borderRadius: 999,
          background: "rgba(255,255,255,0.14)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${progressPct}%`,
            height: "100%",
            background: "linear-gradient(90deg, #00E676, #FFB300, #38BDF8)",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
