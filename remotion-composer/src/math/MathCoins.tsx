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
  accentOrange: "#EA580C",  // Warm Amber
  accentOrangeLight: "#FFEDD5",
  accentBlue: "#2563EB",    // Royal Blue
  accentBlueLight: "#DBEAFE",
  accentPurple: "#7C3AED",
  accentPurpleLight: "#F3E8FF",
  bg: "#F8FAFC",
  cardBg: "#FFFFFF",
  cardBorder: "#E2E8F0",
  text: "#0F172A",
  muted: "#475569",
};

// SVG Coin Component
export const Coin: React.FC<{
  type: "dime" | "nickel" | "quarter";
  size?: number;
  label?: string;
  countBadge?: number | string;
}> = ({ type, size = 110, label, countBadge }) => {
  const cfg = {
    quarter: {
      colorStart: "#FDE047",
      colorEnd: "#D97706",
      border: "#B45309",
      text: "25¢",
      sub: "Quarter",
      textColor: "#78350F",
      sizeRatio: 1.15,
    },
    dime: {
      colorStart: "#F8FAFC",
      colorEnd: "#94A3B8",
      border: "#475569",
      text: "10¢",
      sub: "Dime",
      textColor: "#1E293B",
      sizeRatio: 1.0,
    },
    nickel: {
      colorStart: "#F1F5F9",
      colorEnd: "#64748B",
      border: "#334155",
      text: "5¢",
      sub: "Nickel",
      textColor: "#0F172A",
      sizeRatio: 0.95,
    },
  }[type];

  const actualSize = size * cfg.sizeRatio;

  return (
    <div
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
      }}
    >
      <div
        style={{
          width: actualSize,
          height: actualSize,
          borderRadius: "50%",
          background: `radial-gradient(circle at 35% 35%, ${cfg.colorStart}, ${cfg.colorEnd})`,
          border: `3px solid ${cfg.border}`,
          boxShadow: "0 8px 18px rgba(0,0,0,0.18), inset 0 2px 4px rgba(255,255,255,0.7)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          userSelect: "none",
        }}
      >
        {/* Inner Coin Ridge Ring */}
        <div
          style={{
            position: "absolute",
            width: actualSize - 14,
            height: actualSize - 14,
            borderRadius: "50%",
            border: `2px dashed ${cfg.border}`,
            opacity: 0.45,
          }}
        />

        <span
          style={{
            fontSize: actualSize * 0.32,
            fontWeight: 900,
            color: cfg.textColor,
            lineHeight: 1,
            textShadow: "0 1px 2px rgba(255,255,255,0.8)",
          }}
        >
          {cfg.text}
        </span>
        <span
          style={{
            fontSize: actualSize * 0.15,
            fontWeight: 800,
            color: cfg.textColor,
            opacity: 0.85,
            marginTop: 2,
            textTransform: "uppercase",
            letterSpacing: 0.5,
          }}
        >
          {cfg.sub}
        </span>
      </div>

      {/* Count Badge */}
      {countBadge !== undefined && (
        <div
          style={{
            position: "absolute",
            top: -6,
            right: -6,
            background: COLORS.accentOrange,
            color: "#FFFFFF",
            fontWeight: 900,
            fontSize: 16,
            padding: "3px 10px",
            borderRadius: 14,
            boxShadow: "0 3px 8px rgba(234,88,12,0.4)",
            border: "2px solid #FFFFFF",
          }}
        >
          ×{countBadge}
        </div>
      )}

      {/* Label under coin */}
      {label && (
        <span
          style={{
            marginTop: 8,
            fontSize: 16,
            fontWeight: 800,
            color: COLORS.text,
            textAlign: "center",
          }}
        >
          {label}
        </span>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene Durations in Frames (30 fps)
// Matches master_narration.mp3
// ---------------------------------------------------------------------------
export const SCENE_DURATIONS = {
  intro: 480,         // 16.00s
  readEnglish: 555,   // 18.50s
  readTrans: 525,     // 17.50s
  strategy: 480,      // 16.00s
  solution: 765,      // 25.50s
  check: 540,         // 18.00s
  answer: 165,        // 5.50s
  closing: 225,       // 7.50s
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
            margin: "0 0 20px",
          }}
        >
          16 Đồng Xu Của Audrey
        </h1>
        <p
          style={{
            fontSize: 20,
            color: COLORS.muted,
            fontWeight: 700,
            lineHeight: 1.5,
            margin: "0 0 24px",
          }}
        >
          Kỳ thi AMO 2022 — Câu 22: Tìm số lượng đồng 5 xu (nickels) và 10 xu (dimes) có tổng 100 xu.
        </p>

        {/* Coin Reference Card */}
        <div
          style={{
            background: "#F8FAFC",
            borderRadius: 18,
            border: "2px solid #E2E8F0",
            padding: "16px 20px",
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 800, color: COLORS.muted, marginBottom: 12 }}>
            🪙 HAI LOẠI ĐỒNG XU:
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ width: 34, height: 34, borderRadius: "50%", background: "#64748B", color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 14 }}>10</div>
              <span style={{ fontSize: 20, fontWeight: 800, color: COLORS.text }}>Dime = <b>10 xu</b></span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ width: 34, height: 34, borderRadius: "50%", background: "#475569", color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 14 }}>5</div>
              <span style={{ fontSize: 20, fontWeight: 800, color: COLORS.text }}>Nickel = <b>5 xu</b></span>
            </div>
            <div style={{ fontSize: 18, fontWeight: 800, color: COLORS.accentOrange, borderTop: "1px dashed #CBD5E1", paddingTop: 10 }}>
              Tổng cộng: <b>16 đồng xu = 100 xu</b>
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
          padding: "12px 18px",
          display: "flex",
          alignItems: "center",
          gap: 14,
        }}
      >
        <span style={{ fontSize: 32 }}>💡</span>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800, color: COLORS.primary }}>HỌC TOÁN TRỰC QUAN</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: COLORS.muted }}>Phương pháp quy đổi đồng xu sinh động</div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Bottom Coin Tray for Portrait Mode
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
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "0 -8px 25px rgba(0,0,0,0.06)",
        zIndex: 5,
      }}
    >
      <div
        style={{
          fontSize: 22,
          fontWeight: 900,
          color: COLORS.muted,
          marginBottom: 10,
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span>🪙</span> HAI LOẠI ĐỒNG XU CỦA AUDREY (TỔNG: 16 XU = 100 XU)
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-around",
          width: "100%",
          maxWidth: 900,
          background: "#F8FAFC",
          borderRadius: 24,
          padding: "16px 20px",
          border: "2px solid #E2E8F0",
        }}
      >
        <Coin type="dime" size={90} label="Dime (10 xu)" />
        <span style={{ fontSize: 32, fontWeight: 900, color: COLORS.primary }}>=</span>
        <div style={{ display: "flex", gap: 14 }}>
          <Coin type="nickel" size={80} label="Nickel (5 xu)" />
          <Coin type="nickel" size={80} label="Nickel (5 xu)" />
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 1: Introduction Content
// ---------------------------------------------------------------------------
const SceneIntroCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const bounce = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: 30,
        border: `3px solid ${COLORS.primary}`,
        padding: isLandscape ? "36px 44px" : "44px 32px",
        boxShadow: "0 12px 36px rgba(46,125,50,0.12)",
        maxWidth: isLandscape ? 1100 : 980,
        margin: "0 auto",
        textAlign: "center",
        transform: `scale(${bounce})`,
      }}
    >
      <div
        style={{
          background: COLORS.primaryLight,
          color: COLORS.primary,
          padding: "8px 24px",
          borderRadius: 24,
          fontSize: 22,
          fontWeight: 800,
          display: "inline-block",
          marginBottom: 20,
        }}
      >
        TOÁN QUỐC TẾ AMO 2022 — LỚP 2
      </div>

      <h1
        style={{
          fontSize: isLandscape ? 42 : 46,
          fontWeight: 900,
          color: COLORS.text,
          margin: "0 0 20px",
          lineHeight: 1.25,
        }}
      >
        Câu 22: Bài Toán Đồng Xu Của Audrey
      </h1>

      <div
        style={{
          background: COLORS.accentOrange,
          color: "#FFFFFF",
          padding: "18px 28px",
          borderRadius: 20,
          fontSize: isLandscape ? 26 : 28,
          fontWeight: 900,
          marginBottom: 32,
          boxShadow: "0 8px 20px rgba(234,88,12,0.25)",
        }}
      >
        🎯 Thử thách: 16 đồng xu vừa 5 xu vừa 10 xu, làm sao gom lại vừa đúng 100 xu?
      </div>

      <div style={{ display: "flex", justifyContent: "center", gap: 40, flexWrap: "wrap", marginBottom: 24 }}>
        <Coin type="dime" size={isLandscape ? 110 : 120} label="Dime (10 xu)" />
        <Coin type="nickel" size={isLandscape ? 110 : 120} label="Nickel (5 xu)" />
      </div>

      <div style={{ fontSize: 24, fontWeight: 700, color: COLORS.muted }}>
        Các con hãy cùng lắng nghe đề bài nguyên văn bằng tiếng Anh nhé! 🎧
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 2: Read English Verbatim
// ---------------------------------------------------------------------------
const SceneReadEnglishCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: 30,
        border: `3px solid ${COLORS.accentBlue}`,
        padding: isLandscape ? "36px 44px" : "40px 32px",
        boxShadow: "0 12px 36px rgba(37,99,235,0.12)",
        maxWidth: isLandscape ? 1100 : 980,
        margin: "0 auto",
        transform: `scale(${s})`,
      }}
    >
      <div
        style={{
          background: COLORS.accentBlueLight,
          color: COLORS.accentBlue,
          padding: "8px 22px",
          borderRadius: 24,
          fontSize: 22,
          fontWeight: 900,
          display: "inline-block",
          marginBottom: 18,
        }}
      >
        📖 ORIGINAL PROBLEM (ĐỀ BÀI TIẾNG ANH NGUYÊN VĂN)
      </div>

      <div style={{ fontSize: 28, fontWeight: 900, color: COLORS.accentBlue, marginBottom: 12 }}>
        Question 22.
      </div>

      <p style={{ fontSize: isLandscape ? 30 : 32, fontWeight: 700, color: COLORS.text, lineHeight: 1.45, margin: "0 0 20px" }}>
        Audrey has <b>16 coins</b>, which are either nickels or dimes.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: isLandscape ? "1fr 1fr" : "1fr", gap: 18, marginBottom: 24 }}>
        <div style={{ background: "#F1F5F9", border: "2px solid #CBD5E1", borderRadius: 18, padding: 18, display: "flex", alignItems: "center", gap: 16 }}>
          <Coin type="nickel" size={65} />
          <div>
            <div style={{ fontWeight: 900, fontSize: 24, color: "#1E293B" }}>Nickels</div>
            <div style={{ fontWeight: 700, fontSize: 20, color: "#475569" }}>5 cents each</div>
          </div>
        </div>

        <div style={{ background: "#F8FAFC", border: "2px solid #94A3B8", borderRadius: 18, padding: 18, display: "flex", alignItems: "center", gap: 16 }}>
          <Coin type="dime" size={65} />
          <div>
            <div style={{ fontWeight: 900, fontSize: 24, color: "#1E293B" }}>Dimes</div>
            <div style={{ fontWeight: 700, fontSize: 20, color: "#475569" }}>10 cents each</div>
          </div>
        </div>
      </div>

      <div style={{ background: "#EFF6FF", padding: "18px 24px", borderRadius: 18, borderLeft: `6px solid ${COLORS.accentBlue}` }}>
        <p style={{ fontSize: isLandscape ? 26 : 28, fontWeight: 800, color: COLORS.accentBlue, margin: 0 }}>
          The total value is exactly <b>100 cents</b>. How many nickels does she have?
        </p>
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
  const s = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: 30,
        border: `3px solid ${COLORS.primary}`,
        padding: isLandscape ? "36px 44px" : "40px 32px",
        boxShadow: "0 12px 36px rgba(46,125,50,0.12)",
        maxWidth: isLandscape ? 1100 : 980,
        margin: "0 auto",
        transform: `scale(${s})`,
      }}
    >
      <div
        style={{
          background: COLORS.primaryLight,
          color: COLORS.primary,
          padding: "8px 22px",
          borderRadius: 24,
          fontSize: 22,
          fontWeight: 900,
          display: "inline-block",
          marginBottom: 18,
        }}
      >
        🇻🇳 BẢN DỊCH TIẾNG VIỆT ĐẦY ĐỦ
      </div>

      <div style={{ fontSize: 28, fontWeight: 900, color: COLORS.primary, marginBottom: 12 }}>
        Câu 22.
      </div>

      <p style={{ fontSize: isLandscape ? 30 : 32, fontWeight: 700, color: COLORS.text, lineHeight: 1.45, margin: "0 0 20px" }}>
        Bạn Audrey có tất cả <b>16 đồng xu</b>, gồm đồng 5 xu và đồng 10 xu:
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: isLandscape ? 26 : 28, fontWeight: 800 }}>
          <span style={{ color: "#64748B", fontSize: 32 }}>🪙</span>
          <span>Mỗi đồng <b>5 xu</b> (nickel) trị giá <b>5 xu</b></span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: isLandscape ? 26 : 28, fontWeight: 800 }}>
          <span style={{ color: "#475569", fontSize: 32 }}>🪙</span>
          <span>Mỗi đồng <b>10 xu</b> (dime) trị giá <b>10 xu</b></span>
        </div>
      </div>

      <div style={{ background: "#ECFDF5", padding: "18px 24px", borderRadius: 18, borderLeft: `6px solid ${COLORS.primary}` }}>
        <p style={{ fontSize: isLandscape ? 26 : 28, fontWeight: 800, color: COLORS.primary, margin: 0 }}>
          Tổng giá trị là đúng <b>100 xu</b>. Hỏi bạn Audrey có bao nhiêu đồng 5 xu?
        </p>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 4: Strategy (Coin Swap Rule)
// ---------------------------------------------------------------------------
const SceneStrategyCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: 30,
        border: "3px solid #F59E0B",
        padding: isLandscape ? "32px 40px" : "36px 28px",
        boxShadow: "0 12px 36px rgba(245,158,11,0.15)",
        maxWidth: isLandscape ? 1100 : 980,
        margin: "0 auto",
        transform: `scale(${s})`,
      }}
    >
      <div
        style={{
          background: "#FEF3C7",
          color: "#B45309",
          padding: "8px 22px",
          borderRadius: 24,
          fontSize: 22,
          fontWeight: 900,
          display: "inline-block",
          marginBottom: 16,
        }}
      >
        💡 CHIẾN LƯỢC: QUY TẮC ĐỔI TIỀN XU
      </div>

      <h2 style={{ fontSize: isLandscape ? 34 : 36, fontWeight: 900, color: "#92400E", margin: "0 0 16px" }}>
        Một đồng 10 xu = Hai đồng 5 xu
      </h2>

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 24,
          background: "#FFFBEB",
          padding: "20px",
          borderRadius: 20,
          border: "2px dashed #FCD34D",
          marginBottom: 24,
        }}
      >
        <Coin type="dime" size={90} label="1 đồng 10 xu" />
        <span style={{ fontSize: 44, fontWeight: 900, color: "#D97706" }}>⇄</span>
        <div style={{ display: "flex", gap: 14 }}>
          <Coin type="nickel" size={80} label="1 đồng 5 xu" />
          <Coin type="nickel" size={80} label="1 đồng 5 xu" />
        </div>
      </div>

      <div style={{ background: "#EFF6FF", border: "2px solid #93C5FD", borderRadius: 20, padding: 20, textAlign: "center" }}>
        <div style={{ fontSize: isLandscape ? 24 : 26, fontWeight: 800, color: COLORS.accentBlue, marginBottom: 8 }}>
          🔑 QUY TẮC VÀNG:
        </div>
        <div style={{ fontSize: isLandscape ? 22 : 24, fontWeight: 700, color: COLORS.text }}>
          Mỗi lần đổi <b>1 đồng 10 xu</b> thành <b>2 đồng 5 xu</b>:
          <br />
          👉 <b>Tổng số tiền giữ nguyên 100 xu</b>, nhưng <b>số lượng đồng xu tăng thêm đúng 1 đồng</b>!
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 5: Step-by-Step Solution
// ---------------------------------------------------------------------------
const SceneSolutionCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: 30,
        border: `3px solid ${COLORS.primary}`,
        padding: isLandscape ? "30px 40px" : "32px 24px",
        boxShadow: "0 12px 36px rgba(46,125,50,0.12)",
        maxWidth: isLandscape ? 1100 : 980,
        margin: "0 auto",
        transform: `scale(${s})`,
      }}
    >
      <div
        style={{
          background: COLORS.primaryLight,
          color: COLORS.primary,
          padding: "8px 22px",
          borderRadius: 24,
          fontSize: 22,
          fontWeight: 900,
          display: "inline-block",
          marginBottom: 16,
        }}
      >
        🌟 CÁC BƯỚC GIẢI CHI TIẾT
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14, textAlign: "left" }}>
        <div style={{ background: "#F8FAFC", borderRadius: 16, padding: "14px 20px", border: "2px solid #E2E8F0" }}>
          <div style={{ fontSize: 22, fontWeight: 900, color: COLORS.accentBlue }}>
            Bước 1: Giả sử có 10 đồng 10 xu
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.text, marginTop: 4 }}>
            10 × 10 xu = 100 xu (đủ tiền nhưng mới có 10 xu, thiếu: <b>16 - 10 = 6 đồng xu</b>).
          </div>
        </div>

        <div style={{ background: "#F8FAFC", borderRadius: 16, padding: "14px 20px", border: "2px solid #E2E8F0" }}>
          <div style={{ fontSize: 22, fontWeight: 900, color: COLORS.accentOrange }}>
            Bước 2: Mỗi lần đổi 1 đồng 10 xu → tăng thêm 1 đồng xu
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.text, marginTop: 4 }}>
            Vì cần tăng thêm <b>6 đồng xu</b>, ta cần đổi đúng <b>6 đồng 10 xu</b> thành đồng 5 xu!
          </div>
        </div>

        <div style={{ background: "#F0FDF4", borderRadius: 16, padding: "14px 20px", border: `2px solid ${COLORS.primaryBorder}` }}>
          <div style={{ fontSize: 22, fontWeight: 900, color: COLORS.primary }}>
            Bước 3: Tính số đồng 5 xu và 10 xu
          </div>
          <div style={{ fontSize: 20, fontWeight: 800, color: COLORS.text, marginTop: 4 }}>
            • 6 đồng 10 xu đổi thành: 6 × 2 = <b>12 đồng 5 xu (nickels)</b>.
            <br />
            • Số đồng 10 xu còn lại: 10 - 6 = <b>4 đồng 10 xu (dimes)</b>.
          </div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 6: Verification (Check)
// ---------------------------------------------------------------------------
const SceneCheckCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: 30,
        border: "3px solid #0284C7",
        padding: isLandscape ? "32px 40px" : "36px 28px",
        boxShadow: "0 12px 36px rgba(2,132,199,0.12)",
        maxWidth: isLandscape ? 1100 : 980,
        margin: "0 auto",
        transform: `scale(${s})`,
      }}
    >
      <div
        style={{
          background: "#E0F2FE",
          color: "#0369A1",
          padding: "8px 22px",
          borderRadius: 24,
          fontSize: 22,
          fontWeight: 900,
          display: "inline-block",
          marginBottom: 16,
        }}
      >
        🛡️ BẢNG KIỂM TRA LẠI KẾT QUẢ
      </div>

      <h2 style={{ fontSize: isLandscape ? 30 : 32, fontWeight: 900, color: "#0C4A6E", margin: "0 0 18px" }}>
        Kiểm tra cả số lượng xu và tổng giá trị:
      </h2>

      <div style={{ display: "grid", gridTemplateColumns: isLandscape ? "1fr 1fr" : "1fr", gap: 16, marginBottom: 20 }}>
        <div style={{ background: "#F0FDF4", padding: 18, borderRadius: 18, border: "2px solid #86EFAC" }}>
          <div style={{ fontSize: 20, fontWeight: 800, color: COLORS.primary }}>12 đồng 5 xu (Nickels):</div>
          <div style={{ fontSize: 28, fontWeight: 900, color: COLORS.text, marginTop: 4 }}>12 × 5 = 60 xu</div>
        </div>

        <div style={{ background: "#EFF6FF", padding: 18, borderRadius: 18, border: "2px solid #93C5FD" }}>
          <div style={{ fontSize: 20, fontWeight: 800, color: COLORS.accentBlue }}>4 đồng 10 xu (Dimes):</div>
          <div style={{ fontSize: 28, fontWeight: 900, color: COLORS.text, marginTop: 4 }}>4 × 10 = 40 xu</div>
        </div>
      </div>

      <div style={{ background: "#FEF3C7", padding: "16px 20px", borderRadius: 16, border: "2px solid #FCD34D", textAlign: "center" }}>
        <div style={{ fontSize: 22, fontWeight: 900, color: "#92400E" }}>
          ✅ Tổng tiền: 60 + 40 = <b>100 xu</b> (Chính xác!)
        </div>
        <div style={{ fontSize: 22, fontWeight: 900, color: "#92400E", marginTop: 4 }}>
          ✅ Tổng số xu: 12 + 4 = <b>16 đồng xu</b> (Chính xác!)
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 7: Answer
// ---------------------------------------------------------------------------
const SceneAnswerCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: 30,
        border: `4px solid ${COLORS.primary}`,
        padding: isLandscape ? "36px 48px" : "40px 28px",
        boxShadow: "0 16px 40px rgba(46,125,50,0.18)",
        maxWidth: isLandscape ? 1100 : 980,
        margin: "0 auto",
        textAlign: "center",
        transform: `scale(${s})`,
      }}
    >
      <div
        style={{
          background: COLORS.primaryLight,
          color: COLORS.primary,
          padding: "8px 24px",
          borderRadius: 24,
          fontSize: 22,
          fontWeight: 900,
          display: "inline-block",
          marginBottom: 16,
        }}
      >
        🏆 ĐÁP ÁN CHÍNH XÁC
      </div>

      <div style={{ fontSize: isLandscape ? 32 : 36, fontWeight: 800, color: COLORS.text, marginBottom: 16 }}>
        Audrey có bao nhiêu đồng 5 xu (nickels)?
      </div>

      <div
        style={{
          background: "linear-gradient(135deg, #16A34A, #15803D)",
          color: "#FFFFFF",
          padding: "20px 36px",
          borderRadius: 24,
          display: "inline-block",
          boxShadow: "0 8px 24px rgba(22,163,74,0.3)",
          marginBottom: 16,
        }}
      >
        <div style={{ fontSize: isLandscape ? 52 : 56, fontWeight: 900, letterSpacing: 1 }}>
          12 ĐỒNG 5 XU
        </div>
        <div style={{ fontSize: 24, fontWeight: 800, opacity: 0.9 }}>
          (12 Nickels)
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 8: Closing
// ---------------------------------------------------------------------------
const SceneClosingCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: 30,
        border: `3px solid ${COLORS.primary}`,
        padding: isLandscape ? "40px 48px" : "48px 32px",
        boxShadow: "0 12px 36px rgba(46,125,50,0.12)",
        maxWidth: isLandscape ? 1100 : 980,
        margin: "0 auto",
        textAlign: "center",
        transform: `scale(${s})`,
      }}
    >
      <div style={{ fontSize: 64, marginBottom: 12 }}>🌟</div>
      <h1 style={{ fontSize: isLandscape ? 40 : 44, fontWeight: 900, color: COLORS.primary, margin: "0 0 16px" }}>
        HỌC TOÁN TRỰC QUAN THẬT VUI!
      </h1>
      <p style={{ fontSize: isLandscape ? 26 : 28, fontWeight: 800, color: COLORS.text, lineHeight: 1.5, margin: "0 0 24px" }}>
        Cách đổi tiền xu thật thú vị và dễ hiểu phải không các con.
      </p>
      <div
        style={{
          background: "#F0FDF4",
          border: `2px solid ${COLORS.primaryBorder}`,
          borderRadius: 20,
          padding: "16px 24px",
          fontSize: isLandscape ? 24 : 26,
          fontWeight: 800,
          color: COLORS.primary,
          display: "inline-block",
        }}
      >
        ❤️ Chúc các con học tốt và luôn tự tin khi giải toán!
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main MathCoinsVideo Component
// ---------------------------------------------------------------------------
export const MathCoinsVideo: React.FC<{ orientation: "portrait" | "landscape" }> = ({ orientation }) => {
  const isLandscape = orientation === "landscape";

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.bg,
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
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
            <span style={{ fontSize: 36 }}>🪙</span>
            <span style={{ fontWeight: 900, fontSize: 28, color: COLORS.primary }}>
              TOÁN AMO 2022 — ĐỒNG XU AUDREY
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

export const MathCoinsPortrait: React.FC = () => <MathCoinsVideo orientation="portrait" />;
export const MathCoinsLandscape: React.FC = () => <MathCoinsVideo orientation="landscape" />;
