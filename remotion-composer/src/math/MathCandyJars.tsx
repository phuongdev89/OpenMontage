import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const COLORS = {
  primary: "#2E7D32",       // Emerald Green
  primaryLight: "#DCFCE7",
  primaryBorder: "#86EFAC",
  accentOrange: "#EA580C",  // Warm Amber / Orange (Lọ 2)
  accentOrangeLight: "#FFEDD5",
  accentBlue: "#2563EB",    // Royal Blue (Lọ 1)
  accentBlueLight: "#DBEAFE",
  accentPurple: "#7C3AED",  // Purple (Difference)
  accentPurpleLight: "#F3E8FF",
  bg: "#F8FAFC",
  cardBg: "#FFFFFF",
  cardBorder: "#E2E8F0",
  text: "#0F172A",
  muted: "#475569",
};

// ---------------------------------------------------------------------------
// SVG Candy Jar Component
// ---------------------------------------------------------------------------
export const CandyJar: React.FC<{
  title: string;
  color: string;
  badgeText: string;
  candiesCount?: number;
  subText?: string;
  size?: number;
}> = ({ title, color, badgeText, candiesCount = 8, subText, size = 160 }) => {
  return (
    <div
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        margin: "0 12px",
      }}
    >
      <div
        style={{
          width: size,
          height: size * 1.25,
          position: "relative",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        {/* Jar Lid */}
        <div
          style={{
            width: size * 0.55,
            height: 18,
            borderRadius: "6px 6px 2px 2px",
            background: "#94A3B8",
            border: "2px solid #475569",
            boxShadow: "0 2px 4px rgba(0,0,0,0.15)",
            zIndex: 2,
          }}
        />
        {/* Jar Neck */}
        <div
          style={{
            width: size * 0.45,
            height: 10,
            background: "#CBD5E1",
            borderLeft: "2px solid #64748B",
            borderRight: "2px solid #64748B",
            zIndex: 1,
          }}
        />
        {/* Jar Body */}
        <div
          style={{
            width: size,
            height: size * 1.05,
            borderRadius: "24px 24px 20px 20px",
            background: "linear-gradient(135deg, rgba(255,255,255,0.95), rgba(241,245,249,0.85))",
            border: `3px solid ${color}`,
            boxShadow: `0 10px 25px rgba(0,0,0,0.08), inset 0 0 15px rgba(255,255,255,0.8)`,
            position: "relative",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: 12,
            boxSizing: "border-box",
          }}
        >
          {/* Glass Reflection Highlight */}
          <div
            style={{
              position: "absolute",
              top: 8,
              left: 10,
              width: 14,
              height: size * 0.7,
              borderRadius: 10,
              background: "rgba(255,255,255,0.7)",
            }}
          />

          {/* Candies Grid */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 6,
              justifyContent: "center",
              alignItems: "center",
              maxWidth: size * 0.8,
            }}
          >
            {Array.from({ length: Math.min(candiesCount, 12) }).map((_, i) => (
              <div
                key={i}
                style={{
                  width: size * 0.16,
                  height: size * 0.16,
                  borderRadius: "50%",
                  background:
                    i % 3 === 0
                      ? "radial-gradient(circle at 35% 35%, #F43F5E, #BE123C)"
                      : i % 3 === 1
                      ? "radial-gradient(circle at 35% 35%, #F59E0B, #D97706)"
                      : "radial-gradient(circle at 35% 35%, #10B981, #047857)",
                  boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
                  border: "1px solid rgba(255,255,255,0.6)",
                }}
              />
            ))}
          </div>

          {/* Center Badge */}
          <div
            style={{
              position: "absolute",
              bottom: 12,
              background: color,
              color: "#FFFFFF",
              fontWeight: 900,
              fontSize: size * 0.13,
              padding: "4px 12px",
              borderRadius: 16,
              boxShadow: "0 3px 6px rgba(0,0,0,0.15)",
              border: "1px solid rgba(255,255,255,0.5)",
            }}
          >
            {badgeText}
          </div>
        </div>
      </div>

      <div
        style={{
          marginTop: 10,
          fontWeight: 800,
          fontSize: 20,
          color: COLORS.text,
          textAlign: "center",
        }}
      >
        {title}
      </div>
      {subText && (
        <div
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: COLORS.muted,
            textAlign: "center",
          }}
        >
          {subText}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene Durations in Frames (30 fps)
// Matches master_narration.mp3 (3924 frames total = 130.80s)
// ---------------------------------------------------------------------------
export const SCENE_DURATIONS = {
  intro: 564,         // 18.80s
  readEnglish: 720,   // 24.00s
  readTrans: 525,     // 17.50s
  strategy: 480,      // 16.00s
  solution: 804,      // 26.80s
  check: 582,         // 19.40s
  answer: 144,        // 4.80s
  closing: 105,       // 3.50s
};

// ---------------------------------------------------------------------------
// Left Rail Component for Landscape Mode
// ---------------------------------------------------------------------------
const LandscapeLeftRail: React.FC = () => {
  return (
    <div
      style={{
        width: 580,
        height: "100%",
        background: "#FFFFFF",
        borderRight: "3px solid #E2E8F0",
        padding: "36px 32px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        boxSizing: "border-box",
        zIndex: 5,
      }}
    >
      <div>
        <div
          style={{
            display: "inline-block",
            background: COLORS.primaryLight,
            color: COLORS.primary,
            fontWeight: 800,
            fontSize: 18,
            padding: "6px 16px",
            borderRadius: 20,
            marginBottom: 16,
            border: `1px solid ${COLORS.primaryBorder}`,
          }}
        >
          TOÁN TIỂU HỌC NÂNG CAO — LỚP 2
        </div>

        <h1
          style={{
            fontSize: 34,
            fontWeight: 900,
            color: COLORS.text,
            lineHeight: 1.25,
            margin: "0 0 16px 0",
          }}
        >
          AMO 2022 — Câu 23
          <span style={{ display: "block", color: COLORS.accentOrange, fontSize: 28, marginTop: 6 }}>
            Bài Toán Hai Lọ Kẹo Bằng Nhau
          </span>
        </h1>

        <p
          style={{
            fontSize: 18,
            color: COLORS.muted,
            lineHeight: 1.6,
            margin: "0 0 24px 0",
          }}
        >
          Kỳ thi AMO 2022: Lấy 18 cái ở lọ 1, lấy 26 cái ở lọ 2. Số kẹo lọ 1 còn lại gấp 3 lần lọ 2. Tìm số kẹo ban đầu.
        </p>

        {/* Candy Jars Summary Card */}
        <div
          style={{
            background: "#F8FAFC",
            borderRadius: 18,
            border: "2px solid #E2E8F0",
            padding: "18px 20px",
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 800, color: COLORS.muted, marginBottom: 14 }}>
            🍬 DỮ KIỆN TRỌNG TÂM:
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 28, height: 28, borderRadius: "50%", background: COLORS.accentBlue, color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 14 }}>1</div>
              <span style={{ fontSize: 18, fontWeight: 700, color: COLORS.text }}>Lọ 1 bớt: <b style={{ color: COLORS.accentBlue }}>18 cái kẹo</b></span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 28, height: 28, borderRadius: "50%", background: COLORS.accentOrange, color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 14 }}>2</div>
              <span style={{ fontSize: 18, fontWeight: 700, color: COLORS.text }}>Lọ 2 bớt: <b style={{ color: COLORS.accentOrange }}>26 cái kẹo</b></span>
            </div>
            <div style={{ fontSize: 17, fontWeight: 800, color: COLORS.accentPurple, borderTop: "1px dashed #CBD5E1", paddingTop: 10 }}>
              Chênh lệch: <b>26 - 18 = 8 cái kẹo (2 phần)</b>
            </div>
            <div style={{ fontSize: 17, fontWeight: 800, color: COLORS.primary }}>
              Tỉ số còn lại: <b>Lọ 1 gấp 3 lần Lọ 2</b>
            </div>
          </div>
        </div>
      </div>

      {/* Visual Learning Banner */}
      <div
        style={{
          background: "#F0FDF4",
          border: `2px solid ${COLORS.primaryBorder}`,
          borderRadius: 16,
          padding: "14px 18px",
          display: "flex",
          alignItems: "center",
          gap: 14,
        }}
      >
        <span style={{ fontSize: 32 }}>💡</span>
        <div>
          <div style={{ fontSize: 17, fontWeight: 800, color: COLORS.primary }}>HỌC TOÁN TRỰC QUAN</div>
          <div style={{ fontSize: 15, fontWeight: 700, color: COLORS.muted }}>Phương pháp sơ đồ đoạn thẳng & hiệu - tỉ</div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Bottom Tray for Portrait Mode
// ---------------------------------------------------------------------------
const PortraitBottomTray: React.FC = () => {
  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        height: 320,
        background: "#FFFFFF",
        borderTop: "3px solid #E2E8F0",
        padding: "16px 24px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        boxSizing: "border-box",
        zIndex: 10,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 24 }}>🍬</span>
          <span style={{ fontSize: 20, fontWeight: 900, color: COLORS.text }}>
            TỔNG HỢP DỮ KIỆN BÀI TOÁN
          </span>
        </div>
        <span
          style={{
            background: COLORS.accentOrangeLight,
            color: COLORS.accentOrange,
            fontWeight: 800,
            fontSize: 16,
            padding: "4px 12px",
            borderRadius: 12,
          }}
        >
          AMO 2022
        </span>
      </div>

      <div style={{ display: "flex", gap: 16, justifyContent: "space-between" }}>
        <div
          style={{
            flex: 1,
            background: "#F8FAFC",
            borderRadius: 14,
            padding: "10px 14px",
            border: "2px solid #E2E8F0",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 15, fontWeight: 800, color: COLORS.accentBlue }}>LỌ 1</div>
          <div style={{ fontSize: 20, fontWeight: 900, color: COLORS.text }}>-18 kẹo</div>
          <div style={{ fontSize: 14, color: COLORS.muted, fontWeight: 700 }}>Còn lại 3 phần</div>
        </div>

        <div
          style={{
            flex: 1,
            background: "#F8FAFC",
            borderRadius: 14,
            padding: "10px 14px",
            border: "2px solid #E2E8F0",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 15, fontWeight: 800, color: COLORS.accentOrange }}>LỌ 2</div>
          <div style={{ fontSize: 20, fontWeight: 900, color: COLORS.text }}>-26 kẹo</div>
          <div style={{ fontSize: 14, color: COLORS.muted, fontWeight: 700 }}>Còn lại 1 phần</div>
        </div>

        <div
          style={{
            flex: 1.2,
            background: COLORS.primaryLight,
            borderRadius: 14,
            padding: "10px 14px",
            border: `2px solid ${COLORS.primaryBorder}`,
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 15, fontWeight: 800, color: COLORS.primary }}>CHÊNH LỆCH</div>
          <div style={{ fontSize: 20, fontWeight: 900, color: COLORS.primary }}>8 cái kẹo</div>
          <div style={{ fontSize: 14, color: COLORS.primary, fontWeight: 700 }}>= 2 phần bằng nhau</div>
        </div>
      </div>

      <div
        style={{
          background: "#F1F5F9",
          borderRadius: 12,
          padding: "10px 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: 16, fontWeight: 800, color: COLORS.muted }}>
          Quy tắc: Ban đầu hai lọ có số kẹo bằng nhau
        </span>
        <span style={{ fontSize: 16, fontWeight: 900, color: COLORS.accentOrange }}>
          Đáp án: 30 kẹo
        </span>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 1: Introduction & Hook
// ---------------------------------------------------------------------------
const SceneIntroCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({ frame, fps, config: { damping: 14, mass: 0.9 } });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        width: "100%",
        maxWidth: isLandscape ? 1100 : 960,
        background: "#FFFFFF",
        borderRadius: 28,
        border: "3px solid #E2E8F0",
        boxShadow: "0 16px 36px rgba(0,0,0,0.06)",
        padding: isLandscape ? "44px 50px" : "36px 30px",
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <div
        style={{
          background: COLORS.primaryLight,
          color: COLORS.primary,
          fontWeight: 900,
          fontSize: isLandscape ? 22 : 18,
          padding: "8px 24px",
          borderRadius: 24,
          marginBottom: 20,
          border: `2px solid ${COLORS.primaryBorder}`,
        }}
      >
        KỲ THI TOÁN QUỐC TẾ AMO 2022 — LỚP 2
      </div>

      <h2
        style={{
          fontSize: isLandscape ? 38 : 30,
          fontWeight: 900,
          color: COLORS.text,
          textAlign: "center",
          margin: "0 0 16px 0",
          lineHeight: 1.3,
        }}
      >
        Hai lọ kẹo ban đầu bằng nhau, sau khi lấy đi 18 và 26 chiếc...
      </h2>

      <div
        style={{
          fontSize: isLandscape ? 24 : 20,
          fontWeight: 800,
          color: COLORS.accentOrange,
          textAlign: "center",
          marginBottom: 32,
        }}
      >
        Lọ 1 còn lại gấp 3 lần Lọ 2. Ban đầu mỗi lọ có bao nhiêu chiếc kẹo?
      </div>

      {/* Two Candy Jars Side by Side */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: isLandscape ? 60 : 36,
          width: "100%",
          marginBottom: 24,
        }}
      >
        <CandyJar
          title="Lọ Thứ Nhất"
          color={COLORS.accentBlue}
          badgeText="Lấy ra 18"
          candiesCount={10}
          subText="Còn lại 3 phần"
          size={isLandscape ? 170 : 135}
        />

        <div style={{ fontSize: isLandscape ? 40 : 32, fontWeight: 900, color: "#94A3B8" }}>
          vs
        </div>

        <CandyJar
          title="Lọ Thứ Hai"
          color={COLORS.accentOrange}
          badgeText="Lấy ra 26"
          candiesCount={6}
          subText="Còn lại 1 phần"
          size={isLandscape ? 170 : 135}
        />
      </div>

      <div
        style={{
          background: "#F8FAFC",
          borderRadius: 16,
          border: "2px solid #E2E8F0",
          padding: "14px 28px",
          fontSize: isLandscape ? 20 : 17,
          fontWeight: 800,
          color: COLORS.primary,
          textAlign: "center",
        }}
      >
        Hãy cùng lắng nghe đề bài nguyên văn tiếng Anh ngay sau đây! 🎧
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 2: Original English Question
// ---------------------------------------------------------------------------
const SceneReadEnglishCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        width: "100%",
        maxWidth: isLandscape ? 1100 : 960,
        background: "#FFFFFF",
        borderRadius: 28,
        border: `3px solid ${COLORS.accentBlue}`,
        boxShadow: "0 16px 36px rgba(0,0,0,0.06)",
        padding: isLandscape ? "44px 50px" : "36px 30px",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div
          style={{
            background: COLORS.accentBlueLight,
            color: COLORS.accentBlue,
            fontWeight: 900,
            fontSize: isLandscape ? 22 : 18,
            padding: "8px 24px",
            borderRadius: 24,
          }}
        >
          QUESTION 23 (AMO 2022 — GRADE 2)
        </div>
        <div style={{ fontSize: isLandscape ? 20 : 16, fontWeight: 800, color: COLORS.muted }}>
          English Problem
        </div>
      </div>

      <div
        style={{
          background: "#F8FAFC",
          borderRadius: 20,
          border: "2px solid #E2E8F0",
          padding: isLandscape ? "32px 36px" : "24px 22px",
          fontSize: isLandscape ? 28 : 22,
          fontWeight: 700,
          color: COLORS.text,
          lineHeight: 1.6,
          marginBottom: 24,
        }}
      >
        <p style={{ margin: "0 0 16px 0" }}>
          There are <b>two candy jars</b> with the <b style={{ color: COLORS.primary }}>same number of candies</b>.
        </p>
        <p style={{ margin: "0 0 16px 0" }}>
          If we take <b style={{ color: COLORS.accentBlue }}>18 candies</b> out of the first jar and{" "}
          <b style={{ color: COLORS.accentOrange }}>26 candies</b> out of the second jar,
        </p>
        <p style={{ margin: "0 0 16px 0" }}>
          the candies left in the first jar will be{" "}
          <b style={{ color: COLORS.accentPurple }}>three times as many</b> as the candies left in the second.
        </p>
        <p style={{ margin: 0, fontWeight: 900, color: COLORS.primary }}>
          How many candies does each candy jar have at the beginning?
        </p>
      </div>

      {/* Keywords Badge Bar */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center" }}>
        <span style={{ background: "#EEF2FF", color: "#4338CA", padding: "6px 16px", borderRadius: 14, fontWeight: 800, fontSize: 16 }}>
          Same number of candies
        </span>
        <span style={{ background: "#FEF3C7", color: "#B45309", padding: "6px 16px", borderRadius: 14, fontWeight: 800, fontSize: 16 }}>
          Take 18 & Take 26
        </span>
        <span style={{ background: "#F3E8FF", color: "#7E22CE", padding: "6px 16px", borderRadius: 14, fontWeight: 800, fontSize: 16 }}>
          Three times as many (3×)
        </span>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 3: Vietnamese Translation
// ---------------------------------------------------------------------------
const SceneTranslationCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        width: "100%",
        maxWidth: isLandscape ? 1100 : 960,
        background: "#FFFFFF",
        borderRadius: 28,
        border: `3px solid ${COLORS.primary}`,
        boxShadow: "0 16px 36px rgba(0,0,0,0.06)",
        padding: isLandscape ? "44px 50px" : "36px 30px",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div
          style={{
            background: COLORS.primaryLight,
            color: COLORS.primary,
            fontWeight: 900,
            fontSize: isLandscape ? 22 : 18,
            padding: "8px 24px",
            borderRadius: 24,
          }}
        >
          BẢN DỊCH TIẾNG VIỆT
        </div>
        <div style={{ fontSize: isLandscape ? 20 : 16, fontWeight: 800, color: COLORS.muted }}>
          Câu 23 — AMO 2022 Lớp 2
        </div>
      </div>

      <div
        style={{
          background: "#F0FDF4",
          borderRadius: 20,
          border: `2px solid ${COLORS.primaryBorder}`,
          padding: isLandscape ? "32px 36px" : "24px 22px",
          fontSize: isLandscape ? 28 : 22,
          fontWeight: 700,
          color: COLORS.text,
          lineHeight: 1.6,
          marginBottom: 24,
        }}
      >
        <p style={{ margin: "0 0 16px 0" }}>
          Có <b>hai lọ kẹo</b> đựng <b>số kẹo bằng nhau</b>.
        </p>
        <p style={{ margin: "0 0 16px 0" }}>
          Nếu lấy ra <b style={{ color: COLORS.accentBlue }}>18 cái kẹo</b> từ lọ thứ nhất và{" "}
          <b style={{ color: COLORS.accentOrange }}>26 cái kẹo</b> từ lọ thứ hai,
        </p>
        <p style={{ margin: "0 0 16px 0" }}>
          thì số kẹo còn lại trong lọ thứ nhất sẽ{" "}
          <b style={{ color: COLORS.accentPurple }}>gấp 3 lần</b> số kẹo còn lại trong lọ thứ hai.
        </p>
        <p style={{ margin: 0, fontWeight: 900, color: COLORS.accentOrange }}>
          Hỏi ban đầu mỗi lọ kẹo có bao nhiêu cái kẹo?
        </p>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-around",
          alignItems: "center",
          background: "#F8FAFC",
          borderRadius: 16,
          padding: "16px 20px",
          border: "2px solid #E2E8F0",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: COLORS.muted }}>LỌ 1</div>
          <div style={{ fontSize: 24, fontWeight: 900, color: COLORS.accentBlue }}>Bớt 18 cái</div>
        </div>
        <div style={{ fontSize: 28, color: "#94A3B8" }}>→</div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: COLORS.muted }}>LỌ 2</div>
          <div style={{ fontSize: 24, fontWeight: 900, color: COLORS.accentOrange }}>Bớt 26 cái</div>
        </div>
        <div style={{ fontSize: 28, color: "#94A3B8" }}>→</div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: COLORS.muted }}>CÒN LẠI</div>
          <div style={{ fontSize: 24, fontWeight: 900, color: COLORS.accentPurple }}>Lọ 1 = 3 × Lọ 2</div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 4: Strategy (Difference Heuristic)
// ---------------------------------------------------------------------------
const SceneStrategyCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        width: "100%",
        maxWidth: isLandscape ? 1100 : 960,
        background: "#FFFFFF",
        borderRadius: 28,
        border: "3px solid #E2E8F0",
        boxShadow: "0 16px 36px rgba(0,0,0,0.06)",
        padding: isLandscape ? "44px 50px" : "34px 28px",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          display: "inline-block",
          background: COLORS.accentPurpleLight,
          color: COLORS.accentPurple,
          fontWeight: 900,
          fontSize: isLandscape ? 22 : 18,
          padding: "8px 24px",
          borderRadius: 24,
          marginBottom: 20,
        }}
      >
        CHIẾN LƯỢC: SO SÁNH HIỆU SỐ KẸO LẤY RA
      </div>

      <h3
        style={{
          fontSize: isLandscape ? 32 : 26,
          fontWeight: 900,
          color: COLORS.text,
          margin: "0 0 24px 0",
        }}
      >
        So sánh số kẹo lấy ra từ hai lọ kẹo:
      </h3>

      {/* Difference Comparison Cards */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 16,
          marginBottom: 24,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "#F8FAFC",
            borderRadius: 18,
            padding: "16px 24px",
            border: "2px solid #E2E8F0",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 36, height: 36, borderRadius: "50%", background: COLORS.accentOrange, color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 18 }}>2</div>
            <span style={{ fontSize: isLandscape ? 24 : 19, fontWeight: 800, color: COLORS.text }}>Số kẹo lấy ra ở lọ thứ hai:</span>
          </div>
          <span style={{ fontSize: isLandscape ? 28 : 22, fontWeight: 900, color: COLORS.accentOrange }}>26 chiếc</span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "#F8FAFC",
            borderRadius: 18,
            padding: "16px 24px",
            border: "2px solid #E2E8F0",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 36, height: 36, borderRadius: "50%", background: COLORS.accentBlue, color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 18 }}>1</div>
            <span style={{ fontSize: isLandscape ? 24 : 19, fontWeight: 800, color: COLORS.text }}>Số kẹo lấy ra ở lọ thứ nhất:</span>
          </div>
          <span style={{ fontSize: isLandscape ? 28 : 22, fontWeight: 900, color: COLORS.accentBlue }}>18 chiếc</span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: COLORS.accentPurpleLight,
            borderRadius: 18,
            padding: "18px 24px",
            border: `2px solid ${COLORS.accentPurple}`,
          }}
        >
          <span style={{ fontSize: isLandscape ? 24 : 19, fontWeight: 900, color: COLORS.accentPurple }}>
            Lọ 2 lấy nhiều hơn Lọ 1:
          </span>
          <span style={{ fontSize: isLandscape ? 32 : 24, fontWeight: 900, color: COLORS.accentPurple }}>
            26 - 18 = 8 cái kẹo
          </span>
        </div>
      </div>

      {/* Key Insight Box */}
      <div
        style={{
          background: "#FEF3C7",
          border: "2px solid #F59E0B",
          borderRadius: 18,
          padding: "16px 24px",
          display: "flex",
          alignItems: "center",
          gap: 16,
        }}
      >
        <span style={{ fontSize: 32 }}>💡</span>
        <div style={{ fontSize: isLandscape ? 20 : 16, fontWeight: 800, color: "#92400E", lineHeight: 1.5 }}>
          <b>Nhận xét mấu chốt:</b> Vì ban đầu hai lọ có số kẹo bằng nhau, nên lọ thứ nhất sẽ còn nhiều hơn lọ thứ hai đúng <b>8 cái kẹo</b>!
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 5: Solution with Bar Model (Sơ đồ đoạn thẳng)
// ---------------------------------------------------------------------------
const SceneSolutionCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        width: "100%",
        maxWidth: isLandscape ? 1100 : 960,
        background: "#FFFFFF",
        borderRadius: 28,
        border: `3px solid ${COLORS.primary}`,
        boxShadow: "0 16px 36px rgba(0,0,0,0.06)",
        padding: isLandscape ? "40px 48px" : "32px 24px",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          display: "inline-block",
          background: COLORS.primaryLight,
          color: COLORS.primary,
          fontWeight: 900,
          fontSize: isLandscape ? 22 : 18,
          padding: "6px 22px",
          borderRadius: 20,
          marginBottom: 16,
        }}
      >
        CÁC BƯỚC GIẢI CHI TIẾT (SƠ ĐỒ ĐOẠN THẲNG)
      </div>

      {/* Bar Model Visual */}
      <div
        style={{
          background: "#F8FAFC",
          borderRadius: 20,
          border: "2px solid #E2E8F0",
          padding: isLandscape ? "24px 32px" : "18px 20px",
          marginBottom: 20,
        }}
      >
        <div style={{ fontSize: 18, fontWeight: 800, color: COLORS.muted, marginBottom: 14 }}>
          📊 SƠ ĐỒ SỐ KẸO CÒN LẠI Ở HAI LỌ:
        </div>

        {/* Jar 2 remaining bar: 1 unit */}
        <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
          <div style={{ width: isLandscape ? 160 : 120, fontSize: isLandscape ? 20 : 16, fontWeight: 800, color: COLORS.accentOrange }}>
            Lọ 2 còn lại:
          </div>
          <div style={{ display: "flex", alignItems: "center", flex: 1 }}>
            <div
              style={{
                width: isLandscape ? 140 : 110,
                height: 44,
                borderRadius: 8,
                background: COLORS.accentOrangeLight,
                border: `3px solid ${COLORS.accentOrange}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 900,
                fontSize: 18,
                color: COLORS.accentOrange,
              }}
            >
              1 phần
            </div>
          </div>
        </div>

        {/* Jar 1 remaining bar: 3 units */}
        <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
          <div style={{ width: isLandscape ? 160 : 120, fontSize: isLandscape ? 20 : 16, fontWeight: 800, color: COLORS.accentBlue }}>
            Lọ 1 còn lại:
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, flex: 1 }}>
            <div
              style={{
                width: isLandscape ? 140 : 110,
                height: 44,
                borderRadius: 8,
                background: COLORS.accentBlueLight,
                border: `3px solid ${COLORS.accentBlue}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 900,
                fontSize: 18,
                color: COLORS.accentBlue,
              }}
            >
              1 phần
            </div>
            <div
              style={{
                width: isLandscape ? 140 : 110,
                height: 44,
                borderRadius: 8,
                background: COLORS.accentPurpleLight,
                border: `3px solid ${COLORS.accentPurple}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 900,
                fontSize: 18,
                color: COLORS.accentPurple,
              }}
            >
              1 phần
            </div>
            <div
              style={{
                width: isLandscape ? 140 : 110,
                height: 44,
                borderRadius: 8,
                background: COLORS.accentPurpleLight,
                border: `3px solid ${COLORS.accentPurple}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 900,
                fontSize: 18,
                color: COLORS.accentPurple,
              }}
            >
              1 phần
            </div>
            <span
              style={{
                marginLeft: 14,
                fontWeight: 900,
                fontSize: isLandscape ? 20 : 16,
                color: COLORS.accentPurple,
              }}
            >
              ← Hơn 2 phần = 8 kẹo
            </span>
          </div>
        </div>
      </div>

      {/* Step by step calculations */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div
          style={{
            background: "#F0FDF4",
            borderRadius: 14,
            padding: "12px 20px",
            border: `2px solid ${COLORS.primaryBorder}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: isLandscape ? 20 : 16, fontWeight: 700, color: COLORS.text }}>
            <b>Bước 1:</b> Hiệu số phần bằng nhau: 3 - 1 =
          </span>
          <span style={{ fontSize: isLandscape ? 24 : 18, fontWeight: 900, color: COLORS.primary }}>
            2 phần
          </span>
        </div>

        <div
          style={{
            background: "#F0FDF4",
            borderRadius: 14,
            padding: "12px 20px",
            border: `2px solid ${COLORS.primaryBorder}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: isLandscape ? 20 : 16, fontWeight: 700, color: COLORS.text }}>
            <b>Bước 2:</b> Số kẹo còn lại ở lọ 2 (giá trị 1 phần): 8 ÷ 2 =
          </span>
          <span style={{ fontSize: isLandscape ? 24 : 18, fontWeight: 900, color: COLORS.accentOrange }}>
            4 cái kẹo
          </span>
        </div>

        <div
          style={{
            background: "#FEF3C7",
            borderRadius: 14,
            padding: "14px 20px",
            border: "2px solid #F59E0B",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: isLandscape ? 22 : 17, fontWeight: 900, color: "#92400E" }}>
            <b>Bước 3:</b> Số kẹo ban đầu ở mỗi lọ: 4 + 26 =
          </span>
          <span style={{ fontSize: isLandscape ? 28 : 22, fontWeight: 900, color: "#B45309" }}>
            30 chiếc kẹo
          </span>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 6: Verification Card
// ---------------------------------------------------------------------------
const SceneCheckCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        width: "100%",
        maxWidth: isLandscape ? 1100 : 960,
        background: "#FFFFFF",
        borderRadius: 28,
        border: "3px solid #E2E8F0",
        boxShadow: "0 16px 36px rgba(0,0,0,0.06)",
        padding: isLandscape ? "44px 50px" : "34px 28px",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          display: "inline-block",
          background: COLORS.primaryLight,
          color: COLORS.primary,
          fontWeight: 900,
          fontSize: isLandscape ? 22 : 18,
          padding: "8px 24px",
          borderRadius: 24,
          marginBottom: 20,
        }}
      >
        KIỂM TRA LẠI KẾT QUẢ
      </div>

      <h3
        style={{
          fontSize: isLandscape ? 32 : 26,
          fontWeight: 900,
          color: COLORS.text,
          margin: "0 0 24px 0",
        }}
      >
        Thay số kẹo ban đầu 30 chiếc vào đề bài:
      </h3>

      {/* Verification Columns */}
      <div style={{ display: "flex", gap: 20, marginBottom: 24 }}>
        <div
          style={{
            flex: 1,
            background: "#F8FAFC",
            borderRadius: 20,
            border: `2px solid ${COLORS.accentBlue}`,
            padding: "20px 24px",
          }}
        >
          <div style={{ fontSize: 20, fontWeight: 900, color: COLORS.accentBlue, marginBottom: 12 }}>
            🍬 LỌ THỨ NHẤT
          </div>
          <div style={{ fontSize: 18, color: COLORS.muted, marginBottom: 8 }}>
            Ban đầu có: <b>30 cái kẹo</b>
          </div>
          <div style={{ fontSize: 18, color: COLORS.muted, marginBottom: 8 }}>
            Lấy ra: <b>18 cái kẹo</b>
          </div>
          <div
            style={{
              fontSize: 22,
              fontWeight: 900,
              color: COLORS.accentBlue,
              borderTop: "2px dashed #CBD5E1",
              paddingTop: 10,
            }}
          >
            Còn lại: 30 - 18 = 12 cái
          </div>
        </div>

        <div
          style={{
            flex: 1,
            background: "#F8FAFC",
            borderRadius: 20,
            border: `2px solid ${COLORS.accentOrange}`,
            padding: "20px 24px",
          }}
        >
          <div style={{ fontSize: 20, fontWeight: 900, color: COLORS.accentOrange, marginBottom: 12 }}>
            🍬 LỌ THỨ HAI
          </div>
          <div style={{ fontSize: 18, color: COLORS.muted, marginBottom: 8 }}>
            Ban đầu có: <b>30 cái kẹo</b>
          </div>
          <div style={{ fontSize: 18, color: COLORS.muted, marginBottom: 8 }}>
            Lấy ra: <b>26 cái kẹo</b>
          </div>
          <div
            style={{
              fontSize: 22,
              fontWeight: 900,
              color: COLORS.accentOrange,
              borderTop: "2px dashed #CBD5E1",
              paddingTop: 10,
            }}
          >
            Còn lại: 30 - 26 = 4 cái
          </div>
        </div>
      </div>

      {/* Ratio Check Result */}
      <div
        style={{
          background: "#F0FDF4",
          border: `2px solid ${COLORS.primaryBorder}`,
          borderRadius: 18,
          padding: "18px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: isLandscape ? 24 : 18, fontWeight: 800, color: COLORS.text }}>
          So sánh tỉ số kẹo còn lại: <b>12 ÷ 4 = 3 (Gấp đúng 3 lần!)</b>
        </span>
        <span
          style={{
            background: COLORS.primary,
            color: "#FFFFFF",
            padding: "6px 20px",
            borderRadius: 16,
            fontWeight: 900,
            fontSize: isLandscape ? 20 : 16,
          }}
        >
          ✓ ĐÚNG TUYỆT ĐỐI
        </span>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 7: Answer Card
// ---------------------------------------------------------------------------
const SceneAnswerCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 12 } });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        width: "100%",
        maxWidth: isLandscape ? 1000 : 900,
        background: "linear-gradient(135deg, #F0FDF4, #DCFCE7)",
        borderRadius: 32,
        border: `4px solid ${COLORS.primary}`,
        boxShadow: "0 20px 45px rgba(46,125,50,0.18)",
        padding: isLandscape ? "50px 60px" : "40px 30px",
        boxSizing: "border-box",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 54, marginBottom: 12 }}>🎉</div>

      <div
        style={{
          fontSize: isLandscape ? 30 : 24,
          fontWeight: 800,
          color: COLORS.primary,
          marginBottom: 16,
          letterSpacing: 1,
        }}
      >
        ĐÁP ÁN CHÍNH XÁC CỦA BÀI TOÁN
      </div>

      <div
        style={{
          fontSize: isLandscape ? 68 : 50,
          fontWeight: 900,
          color: COLORS.primary,
          marginBottom: 16,
        }}
      >
        30 CHIẾC KẸO
      </div>

      <div
        style={{
          fontSize: isLandscape ? 24 : 19,
          fontWeight: 700,
          color: COLORS.muted,
        }}
      >
        Ban đầu mỗi lọ kẹo có <b>30 chiếc kẹo</b>!
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 8: Closing Card
// ---------------------------------------------------------------------------
const SceneClosingCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        width: "100%",
        maxWidth: isLandscape ? 1000 : 900,
        background: "#FFFFFF",
        borderRadius: 32,
        border: "3px solid #E2E8F0",
        boxShadow: "0 20px 45px rgba(0,0,0,0.06)",
        padding: isLandscape ? "50px 60px" : "40px 30px",
        boxSizing: "border-box",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 54, marginBottom: 12 }}>🌟</div>

      <h2
        style={{
          fontSize: isLandscape ? 40 : 32,
          fontWeight: 900,
          color: COLORS.primary,
          margin: "0 0 16px 0",
        }}
      >
        Chúc các con học tốt và luôn tự tin khi giải toán!
      </h2>

      <p
        style={{
          fontSize: isLandscape ? 24 : 19,
          fontWeight: 700,
          color: COLORS.muted,
          margin: "0 0 24px 0",
        }}
      >
        Hẹn gặp lại các con trong những bài toán thú vị tiếp theo! 🚀
      </p>

      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 12,
          background: COLORS.primaryLight,
          color: COLORS.primary,
          fontWeight: 900,
          fontSize: isLandscape ? 22 : 18,
          padding: "10px 28px",
          borderRadius: 24,
        }}
      >
        <span>🍬</span> TOÁN TIỂU HỌC QUỐC TẾ AMO
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main MathCandyJars Video Component
// ---------------------------------------------------------------------------
export const MathCandyJarsVideo: React.FC<{ orientation: "portrait" | "landscape" }> = ({ orientation }) => {
  const isLandscape = orientation === "landscape";

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.bg,
        fontFamily: "Nunito, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        overflow: "hidden",
        display: "flex",
        flexDirection: isLandscape ? "row" : "column",
      }}
    >
      {/* Decorative Grid Pattern */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          opacity: 0.04,
          backgroundImage: "radial-gradient(#2E7D32 2px, transparent 2px)",
          backgroundSize: "32px 32px",
          pointerEvents: "none",
        }}
      />

      {/* Synchronized Master Narration Audio */}
      <Audio src={staticFile("master_narration.mp3")} />

      {/* Landscape Left Rail */}
      {isLandscape && <LandscapeLeftRail />}

      {/* Portrait Header Bar */}
      {!isLandscape && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 100,
            background: "#FFFFFF",
            borderBottom: "3px solid #E2E8F0",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 36px",
            zIndex: 10,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <span style={{ fontSize: 36 }}>🍬</span>
            <span style={{ fontWeight: 900, fontSize: 28, color: COLORS.primary }}>
              TOÁN AMO 2022 — HAI LỌ KẸO
            </span>
          </div>
          <div
            style={{
              background: COLORS.primaryLight,
              color: COLORS.primary,
              fontWeight: 900,
              fontSize: 22,
              padding: "6px 18px",
              borderRadius: 20,
            }}
          >
            LỚP 2
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div
        style={{
          flex: 1,
          height: isLandscape ? "100%" : "calc(100% - 420px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: isLandscape ? "30px 40px" : "20px 24px",
          marginTop: isLandscape ? 0 : 100,
          boxSizing: "border-box",
          position: "relative",
        }}
      >
        {/* Scene 1: Intro */}
        <Sequence from={0} durationInFrames={SCENE_DURATIONS.intro}>
          <SceneIntroCard isLandscape={isLandscape} />
        </Sequence>

        {/* Scene 2: Read English */}
        <Sequence from={SCENE_DURATIONS.intro} durationInFrames={SCENE_DURATIONS.readEnglish}>
          <SceneReadEnglishCard isLandscape={isLandscape} />
        </Sequence>

        {/* Scene 3: Translation */}
        <Sequence
          from={SCENE_DURATIONS.intro + SCENE_DURATIONS.readEnglish}
          durationInFrames={SCENE_DURATIONS.readTrans}
        >
          <SceneTranslationCard isLandscape={isLandscape} />
        </Sequence>

        {/* Scene 4: Strategy */}
        <Sequence
          from={SCENE_DURATIONS.intro + SCENE_DURATIONS.readEnglish + SCENE_DURATIONS.readTrans}
          durationInFrames={SCENE_DURATIONS.strategy}
        >
          <SceneStrategyCard isLandscape={isLandscape} />
        </Sequence>

        {/* Scene 5: Solution */}
        <Sequence
          from={
            SCENE_DURATIONS.intro +
            SCENE_DURATIONS.readEnglish +
            SCENE_DURATIONS.readTrans +
            SCENE_DURATIONS.strategy
          }
          durationInFrames={SCENE_DURATIONS.solution}
        >
          <SceneSolutionCard isLandscape={isLandscape} />
        </Sequence>

        {/* Scene 6: Check */}
        <Sequence
          from={
            SCENE_DURATIONS.intro +
            SCENE_DURATIONS.readEnglish +
            SCENE_DURATIONS.readTrans +
            SCENE_DURATIONS.strategy +
            SCENE_DURATIONS.solution
          }
          durationInFrames={SCENE_DURATIONS.check}
        >
          <SceneCheckCard isLandscape={isLandscape} />
        </Sequence>

        {/* Scene 7: Answer */}
        <Sequence
          from={
            SCENE_DURATIONS.intro +
            SCENE_DURATIONS.readEnglish +
            SCENE_DURATIONS.readTrans +
            SCENE_DURATIONS.strategy +
            SCENE_DURATIONS.solution +
            SCENE_DURATIONS.check
          }
          durationInFrames={SCENE_DURATIONS.answer}
        >
          <SceneAnswerCard isLandscape={isLandscape} />
        </Sequence>

        {/* Scene 8: Closing */}
        <Sequence
          from={
            SCENE_DURATIONS.intro +
            SCENE_DURATIONS.readEnglish +
            SCENE_DURATIONS.readTrans +
            SCENE_DURATIONS.strategy +
            SCENE_DURATIONS.solution +
            SCENE_DURATIONS.check +
            SCENE_DURATIONS.answer
          }
          durationInFrames={SCENE_DURATIONS.closing}
        >
          <SceneClosingCard isLandscape={isLandscape} />
        </Sequence>
      </div>

      {/* Portrait Bottom Tray */}
      {!isLandscape && <PortraitBottomTray />}
    </AbsoluteFill>
  );
};

export const MathCandyJarsPortrait: React.FC = () => <MathCandyJarsVideo orientation="portrait" />;
export const MathCandyJarsLandscape: React.FC = () => <MathCandyJarsVideo orientation="landscape" />;
