import React from "react";
import { Composition } from "remotion";
import { MatchReel, MatchReelProps } from "./MatchReel";

const defaultProps: MatchReelProps = {
  stage: "pre_match",
  home_team: "نوتنغهام فورست",
  away_team: "تشيلسي",
  home_logo: "https://a.espncdn.com/i/teamlogos/soccer/500/393.png",
  away_logo: "https://a.espncdn.com/i/teamlogos/soccer/500/363.png",
  home_player_img: "",
  home_player_name: "",
  away_player_img: "",
  away_player_name: "",
  competition: "الدوري الإنجليزي الممتاز",
  channel: "beIN SPORTS Xtra 1",
  home_score: 0,
  away_score: 0,
  venue: "ملعب اللقاء",
  commentator: "",
  goal_events: [],
  stat_bars: [],
  hook_text: "من يحسم قمة نوتنغهام فورست ضد تشيلسي اليوم؟ 🔥⚽",
  info_primary: "10:00 م القاهرة | 11:00 م مكة",
  info_secondary: "الدوري الإنجليزي الممتاز • beIN SPORTS Xtra 1",
  engagement_prompt: "اكتب توقعك للنتيجة قبل صافرة البداية في التعليقات! 👇",
  cta_text: "رابط التشكيلة الرسمية والمتابعة المباشرة في أول تعليق 👇",
  audio_file: "",
  duration_seconds: 18,
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="MatchReel"
      component={MatchReel}
      durationInFrames={540}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultProps}
      calculateMetadata={({ props }) => {
        const secs = Math.max(15, Math.min(25, Math.round(props.duration_seconds || 18)));
        return {
          durationInFrames: secs * 30,
          fps: 30,
          width: 1080,
          height: 1920,
        };
      }}
    />
  );
};
