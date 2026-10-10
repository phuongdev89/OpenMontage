import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
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
  type: "quarter" | "dime" | "nickel";
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
      colorStart: "#F1F5F9",
      colorEnd: "#94A3B8",
      border: "#475569",
      text: "10¢",
      sub: "Dime",
      textColor: "#1E293B",
      sizeRatio: 0.9,
    },
    nickel: {
      colorStart: "#E2E8F0",
      colorEnd: "#A1A1AA",
      border: "#71717A",
      text: "5¢",
      sub: "Nickel",
      textColor: "#27272A",
      sizeRatio: 1.0,
    },
  }[type];

  const actualSize = size * cfg.sizeRatio;

  return (
    <div
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        margin: "6px 12px",
        position: "relative",
      }}
    >
      <div
        style={{
          width: actualSize,
          height: actualSize,
          borderRadius: "50%",
          background: `radial-gradient(circle at 35% 30%, ${cfg.colorStart}, ${cfg.colorEnd})`,
          border: `4px solid ${cfg.border}`,
          boxShadow: "0 8px 18px rgba(0,0,0,0.18), inset 0 3px 5px rgba(255,255,255,0.7)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
        }}
      >
        <span
          style={{
            fontSize: actualSize * 0.38,
            fontWeight: 900,
            color: cfg.textColor,
            fontFamily: "system-ui, -apple-system, sans-serif",
            lineHeight: 1,
            textShadow: "0 1px 2px rgba(255,255,255,0.8)",
          }}
        >
          {cfg.text}
        </span>
        <span
          style={{
            fontSize: actualSize * 0.16,
            fontWeight: 800,
            color: cfg.textColor,
            opacity: 0.9,
            marginTop: 2,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          {cfg.sub}
        </span>

        {countBadge !== undefined && (
          <div
            style={{
              position: "absolute",
              top: -10,
              right: -10,
              background: COLORS.primary,
              color: "#FFFFFF",
              fontSize: 18,
              fontWeight: 900,
              padding: "4px 10px",
              minWidth: 32,
              height: 32,
              borderRadius: 16,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 3px 8px rgba(0,0,0,0.3)",
              border: "3px solid #FFFFFF",
            }}
          >
            {countBadge}
          </div>
        )}
      </div>
      {label && (
        <span
          style={{
            marginTop: 8,
            fontSize: 20,
            fontWeight: 800,
            color: COLORS.text,
          }}
        >
          {label}
        </span>
      )}
    </div>
  );
};

export const SCENE_DURATIONS = {
  intro: 418,         // 13.92s
  readEnglish: 618,   // 20.60s
  readTrans: 385,     // 12.84s
  strategy: 565,      // 18.82s
  case1: 637,         // 21.24s
  case2Guide: 514,    // 17.14s
  check: 331,         // 11.02s
  practice: 464,      // 15.46s
  closing: 274,       // 9.14s
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
          Đổi Tiền Xu Cùng Bạn Carrie
        </h1>

        {/* Goal Card */}
        <div
          style={{
            background: "#EFF6FF",
            borderRadius: 18,
            border: "2px solid #BFDBFE",
            padding: "16px 20px",
            marginBottom: 20,
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 900, color: COLORS.accentBlue, marginBottom: 6 }}>
            🎯 MỤC TIÊU BÀI TOÁN
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, color: COLORS.text }}>
            Gom các đồng xu để trả đúng: <span style={{ color: COLORS.primary, fontSize: 26 }}>30 cents</span>
          </div>
        </div>

        {/* Coin Bank Reference */}
        <div
          style={{
            background: "#F8FAFC",
            borderRadius: 18,
            border: "2px solid #E2E8F0",
            padding: "16px 20px",
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 800, color: COLORS.muted, marginBottom: 12 }}>
            🪙 3 LOẠI ĐỒNG XU CỦA CARRIE:
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 34, height: 34, borderRadius: "50%", background: "#F59E0B", color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 14 }}>25</div>
              <span style={{ fontSize: 20, fontWeight: 800, color: COLORS.text }}>Quarter = <b>25 xu</b></span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 30, height: 30, borderRadius: "50%", background: "#64748B", color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 14 }}>10</div>
              <span style={{ fontSize: 20, fontWeight: 800, color: COLORS.text }}>Dime = <b>10 xu</b></span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#71717A", color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 14 }}>5</div>
              <span style={{ fontSize: 20, fontWeight: 800, color: COLORS.text }}>Nickel = <b>5 xu</b></span>
            </div>
          </div>
        </div>
      </div>

      {/* Teacher Persona Banner */}
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
        <span style={{ fontSize: 32 }}>👨‍🏫</span>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800, color: COLORS.primary }}>THẦY GIẢNG BÀI</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: COLORS.muted }}>Tiếp cận trực quan, sinh động</div>
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
        height: 380,
        background: "#FFFFFF",
        borderTop: "3px solid #E2E8F0",
        padding: "20px 30px",
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
          marginBottom: 12,
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span>🪙</span> KHAY ĐỒNG XU CỦA BẠN CARRIE (MỤC TIÊU: 30 XU)
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
        <Coin type="quarter" size={95} label="Quarter (25 xu)" />
        <Coin type="dime" size={95} label="Dime (10 xu)" />
        <Coin type="nickel" size={95} label="Nickel (5 xu)" />
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
        TOÁN ĐỐ VUI — PHƯƠNG PHÁP TRỰC QUAN
      </div>

      <h1
        style={{
          fontSize: isLandscape ? 44 : 48,
          fontWeight: 900,
          color: COLORS.text,
          margin: "0 0 20px",
          lineHeight: 1.25,
        }}
      >
        Chào mừng các con đến với bài học đổi tiền xu!
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
        🎯 Thử thách: Làm sao để đổi đúng 30 xu từ 3 loại đồng xu?
      </div>

      <div style={{ display: "flex", justifyContent: "center", gap: 30, flexWrap: "wrap", marginBottom: 24 }}>
        <Coin type="quarter" size={isLandscape ? 110 : 120} label="25 xu" />
        <Coin type="dime" size={isLandscape ? 110 : 120} label="10 xu" />
        <Coin type="nickel" size={isLandscape ? 110 : 120} label="5 xu" />
      </div>

      <div style={{ fontSize: 24, fontWeight: 700, color: COLORS.muted }}>
        Thầy và các con sẽ cùng nghe đề bài nguyên văn bằng tiếng Anh trước nhé! 🎧
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
        Question 20.
      </div>

      <p style={{ fontSize: isLandscape ? 32 : 34, fontWeight: 700, color: COLORS.text, lineHeight: 1.45, margin: "0 0 20px" }}>
        Carrie has three types of coins in large numbers:
      </p>

      <div style={{ display: "grid", gridTemplateColumns: isLandscape ? "repeat(3, 1fr)" : "1fr", gap: 16, marginBottom: 24 }}>
        <div style={{ background: "#FFFBEB", border: "2px solid #FCD34D", borderRadius: 18, padding: 16, display: "flex", alignItems: "center", gap: 14 }}>
          <Coin type="quarter" size={60} />
          <div>
            <div style={{ fontWeight: 900, fontSize: 22, color: "#92400E" }}>Quarters</div>
            <div style={{ fontWeight: 700, fontSize: 18, color: "#B45309" }}>25 cents each</div>
          </div>
        </div>

        <div style={{ background: "#F1F5F9", border: "2px solid #CBD5E1", borderRadius: 18, padding: 16, display: "flex", alignItems: "center", gap: 14 }}>
          <Coin type="dime" size={60} />
          <div>
            <div style={{ fontWeight: 900, fontSize: 22, color: "#1E293B" }}>Dimes</div>
            <div style={{ fontWeight: 700, fontSize: 18, color: "#475569" }}>10 cents each</div>
          </div>
        </div>

        <div style={{ background: "#F4F4F5", border: "2px solid #D4D4D8", borderRadius: 18, padding: 16, display: "flex", alignItems: "center", gap: 14 }}>
          <Coin type="nickel" size={60} />
          <div>
            <div style={{ fontWeight: 900, fontSize: 22, color: "#27272A" }}>Nickels</div>
            <div style={{ fontWeight: 700, fontSize: 18, color: "#52525B" }}>5 cents each</div>
          </div>
        </div>
      </div>

      <div style={{ background: "#EFF6FF", padding: "18px 24px", borderRadius: 18, borderLeft: `6px solid ${COLORS.accentBlue}` }}>
        <p style={{ fontSize: isLandscape ? 28 : 30, fontWeight: 800, color: COLORS.accentBlue, margin: 0 }}>
          In how many different ways can she make a payment of 30 cents?
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
        Câu 20.
      </div>

      <p style={{ fontSize: isLandscape ? 32 : 34, fontWeight: 700, color: COLORS.text, lineHeight: 1.45, margin: "0 0 20px" }}>
        Bạn Carrie có ba loại đồng xu với số lượng rất nhiều:
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: isLandscape ? 26 : 28, fontWeight: 800 }}>
          <span style={{ color: "#D97706", fontSize: 32 }}>🪙</span>
          <span>Đồng <b>25 xu</b> (Quarters)</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: isLandscape ? 26 : 28, fontWeight: 800 }}>
          <span style={{ color: "#64748B", fontSize: 32 }}>🪙</span>
          <span>Đồng <b>10 xu</b> (Dimes)</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: isLandscape ? 26 : 28, fontWeight: 800 }}>
          <span style={{ color: "#71717A", fontSize: 32 }}>🪙</span>
          <span>Đồng <b>5 xu</b> (Nickels)</span>
        </div>
      </div>

      <div style={{ background: "#ECFDF5", padding: "18px 24px", borderRadius: 18, borderLeft: `6px solid ${COLORS.primary}` }}>
        <p style={{ fontSize: isLandscape ? 28 : 30, fontWeight: 800, color: COLORS.primary, margin: 0 }}>
          Hỏi bạn ấy có bao nhiêu cách khác nhau để trả đúng 30 xu?
        </p>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 4: Strategy
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
        💡 CHIẾN LƯỢC: QUAN SÁT ĐỒNG XU LỚN NHẤT
      </div>

      <h2 style={{ fontSize: isLandscape ? 34 : 36, fontWeight: 900, color: "#92400E", margin: "0 0 12px" }}>
        Bắt đầu từ đồng 25 xu (Quarter)
      </h2>
      <p style={{ fontSize: isLandscape ? 22 : 24, fontWeight: 700, color: COLORS.muted, margin: "0 0 24px" }}>
        Vì 2 đồng 25 xu = 50 xu (vượt quá 30 xu), Carrie chỉ có thể dùng tối đa 1 đồng 25 xu.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: isLandscape ? "1fr 1fr" : "1fr", gap: 20 }}>
        <div style={{ background: "#F0FDF4", border: "2px solid #86EFAC", borderRadius: 20, padding: 22, textAlign: "center" }}>
          <div style={{ fontSize: 24, fontWeight: 900, color: COLORS.primary, marginBottom: 6 }}>TRƯỜNG HỢP 1</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: COLORS.text, marginBottom: 12 }}>Có dùng <b>1 đồng 25 xu</b></div>
          <Coin type="quarter" size={85} countBadge={1} />
          <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.muted, marginTop: 8 }}>Còn thiếu: 30 - 25 = 5 xu</div>
        </div>

        <div style={{ background: "#EFF6FF", border: "2px solid #93C5FD", borderRadius: 20, padding: 22, textAlign: "center" }}>
          <div style={{ fontSize: 24, fontWeight: 900, color: COLORS.accentBlue, marginBottom: 6 }}>TRƯỜNG HỢP 2</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: COLORS.text, marginBottom: 12 }}><b>Không dùng</b> đồng 25 xu nào</div>
          <div style={{ display: "flex", justifyContent: "center", gap: 12 }}>
            <Coin type="dime" size={75} />
            <Coin type="nickel" size={75} />
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.muted, marginTop: 8 }}>Chỉ dùng đồng 10 xu và 5 xu</div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 5: Case 1
// ---------------------------------------------------------------------------
const SceneCase1Card: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });
  const coinPop = spring({ frame: frame - 15, fps, config: { damping: 12 } });

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: 30,
        border: `3px solid ${COLORS.primary}`,
        padding: isLandscape ? "32px 40px" : "36px 28px",
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
        🌟 TRƯỜNG HỢP 1: DÙNG 1 ĐỒNG 25 XU
      </div>

      <div style={{ fontSize: isLandscape ? 28 : 30, fontWeight: 800, color: COLORS.text, marginBottom: 14 }}>
        1. Carrie lấy ra <b>1 đồng 25 xu</b>.
      </div>
      <div style={{ fontSize: isLandscape ? 24 : 26, fontWeight: 700, color: COLORS.muted, marginBottom: 20 }}>
        2. Số tiền còn thiếu để đủ 30 xu là: <b>30 - 25 = 5 xu</b>.
      </div>

      <div style={{ background: "#F8FAFC", borderRadius: 20, padding: 20, border: "2px dashed #CBD5E1", marginBottom: 20 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.text, marginBottom: 14 }}>
          Vì 5 xu nhỏ hơn 10 xu, nên Carrie không thể lấy đồng 10 xu. Bạn ấy bắt buộc lấy đúng <b>1 đồng 5 xu</b>:
        </div>

        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 20, transform: `scale(${coinPop})` }}>
          <Coin type="quarter" size={isLandscape ? 90 : 100} label="1 đồng 25 xu" />
          <span style={{ fontSize: 40, fontWeight: 900, color: COLORS.primary }}>+</span>
          <Coin type="nickel" size={isLandscape ? 90 : 100} label="1 đồng 5 xu" />
          <span style={{ fontSize: 40, fontWeight: 900, color: COLORS.primary }}>=</span>
          <div style={{ background: COLORS.primary, color: "#FFFFFF", padding: "12px 24px", borderRadius: 16, fontWeight: 900, fontSize: 28 }}>
            30 XU
          </div>
        </div>
      </div>

      <div style={{ background: "#ECFDF5", borderRadius: 16, padding: "16px 20px", borderLeft: `6px solid ${COLORS.primary}`, fontSize: isLandscape ? 26 : 28, fontWeight: 900, color: COLORS.primary, textAlign: "center" }}>
        🎉 Tìm được CÁCH THỨ NHẤT: (Trường hợp 1 có đúng <b>1 cách</b>)
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 6: Case 2 Guide
// ---------------------------------------------------------------------------
const SceneCase2GuideCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: 30,
        border: `3px solid ${COLORS.accentBlue}`,
        padding: isLandscape ? "32px 40px" : "36px 28px",
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
          marginBottom: 16,
        }}
      >
        🔍 HƯỚNG DẪN TRƯỜNG HỢP 2: KHÔNG CÓ ĐỒNG 25 XU
      </div>

      <p style={{ fontSize: isLandscape ? 28 : 30, fontWeight: 800, color: COLORS.text, margin: "0 0 14px" }}>
        Carrie chỉ dùng các đồng <b>10 xu</b> và <b>5 xu</b>!
      </p>
      <p style={{ fontSize: isLandscape ? 22 : 24, fontWeight: 700, color: COLORS.muted, margin: "0 0 20px" }}>
        Thầy hướng dẫn cách phân loại có hệ thống theo số đồng 10 xu:
      </p>

      <div style={{ display: "grid", gridTemplateColumns: isLandscape ? "repeat(4, 1fr)" : "1fr 1fr", gap: 14 }}>
        <div style={{ background: "#F1F5F9", borderRadius: 16, padding: 16, textAlign: "center", border: "2px solid #CBD5E1" }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: COLORS.accentBlue }}>Khả năng A</div>
          <div style={{ fontSize: 26, fontWeight: 900, color: COLORS.text, margin: "6px 0" }}>3 đồng 10 xu</div>
          <div style={{ fontSize: 18, color: COLORS.muted }}>Đã có: 30 xu</div>
        </div>
        <div style={{ background: "#F1F5F9", borderRadius: 16, padding: 16, textAlign: "center", border: "2px solid #CBD5E1" }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: COLORS.accentBlue }}>Khả năng B</div>
          <div style={{ fontSize: 26, fontWeight: 900, color: COLORS.text, margin: "6px 0" }}>2 đồng 10 xu</div>
          <div style={{ fontSize: 18, color: COLORS.muted }}>Đã có: 20 xu</div>
        </div>
        <div style={{ background: "#F1F5F9", borderRadius: 16, padding: 16, textAlign: "center", border: "2px solid #CBD5E1" }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: COLORS.accentBlue }}>Khả năng C</div>
          <div style={{ fontSize: 26, fontWeight: 900, color: COLORS.text, margin: "6px 0" }}>1 đồng 10 xu</div>
          <div style={{ fontSize: 18, color: COLORS.muted }}>Đã có: 10 xu</div>
        </div>
        <div style={{ background: "#F1F5F9", borderRadius: 16, padding: 16, textAlign: "center", border: "2px solid #CBD5E1" }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: COLORS.accentBlue }}>Khả năng D</div>
          <div style={{ fontSize: 26, fontWeight: 900, color: COLORS.text, margin: "6px 0" }}>0 đồng 10 xu</div>
          <div style={{ fontSize: 18, color: COLORS.muted }}>Dùng toàn bộ 5 xu</div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 7: Self-Check Guidance
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
        border: "3px solid #EF4444",
        padding: isLandscape ? "32px 40px" : "36px 28px",
        boxShadow: "0 12px 36px rgba(239,68,68,0.12)",
        maxWidth: isLandscape ? 1100 : 980,
        margin: "0 auto",
        transform: `scale(${s})`,
      }}
    >
      <div
        style={{
          background: "#FEF2F2",
          color: "#DC2626",
          padding: "8px 22px",
          borderRadius: 24,
          fontSize: 22,
          fontWeight: 900,
          display: "inline-block",
          marginBottom: 16,
        }}
      >
        🛡️ BÍ QUYẾT TỰ KIỂM TRA BÀI LÀM
      </div>

      <h2 style={{ fontSize: isLandscape ? 32 : 34, fontWeight: 900, color: "#991B1B", margin: "0 0 20px" }}>
        Hai bước kiểm tra của học sinh cẩn thận:
      </h2>

      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18, background: "#F8FAFC", padding: "18px 22px", borderRadius: 18, borderLeft: "6px solid #EF4444" }}>
          <span style={{ fontSize: 36 }}>1️⃣</span>
          <div style={{ fontSize: isLandscape ? 24 : 26, fontWeight: 800, color: COLORS.text }}>
            <b>Cộng tổng tiền:</b> Kiểm tra xem các đồng xu đã cộng lại đủ đúng <b>30 xu</b> chưa?
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 18, background: "#F8FAFC", padding: "18px 22px", borderRadius: 18, borderLeft: "6px solid #EF4444" }}>
          <span style={{ fontSize: 36 }}>2️⃣</span>
          <div style={{ fontSize: isLandscape ? 24 : 26, fontWeight: 800, color: COLORS.text }}>
            <b>Kiểm tra trùng lặp:</b> Xác nhận các cách không bị lặp lại số lượng xu giống nhau!
          </div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 8: Practice (Task for Kids)
// ---------------------------------------------------------------------------
const ScenePracticeCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: 30,
        border: "3px solid #A855F7",
        padding: isLandscape ? "32px 40px" : "36px 28px",
        boxShadow: "0 12px 36px rgba(168,85,247,0.15)",
        maxWidth: isLandscape ? 1100 : 980,
        margin: "0 auto",
        transform: `scale(${s})`,
      }}
    >
      <div
        style={{
          background: "#FDF4FF",
          color: "#A855F7",
          padding: "8px 22px",
          borderRadius: 24,
          fontSize: 22,
          fontWeight: 900,
          display: "inline-block",
          marginBottom: 16,
        }}
      >
        ✏️ THỬ TÀI CÙNG THẦY — BÀI TẬP VỀ NHÀ
      </div>

      <h2 style={{ fontSize: isLandscape ? 30 : 32, fontWeight: 900, color: "#7E22CE", margin: "0 0 16px" }}>
        Các con hãy tìm số đồng 5 xu còn thiếu cho từng khả năng:
      </h2>

      <div style={{ display: "grid", gridTemplateColumns: isLandscape ? "1fr 1fr" : "1fr", gap: 14, marginBottom: 20 }}>
        <div style={{ background: "#FAF5FF", borderRadius: 16, padding: "14px 20px", border: "2px solid #E9D5FF", fontSize: 22, fontWeight: 800 }}>
          Khả năng A: 3 đồng 10 xu + <span style={{ color: "#A855F7", fontSize: 26, fontWeight: 900 }}>[ ? ]</span> đồng 5 xu = 30 xu
        </div>
        <div style={{ background: "#FAF5FF", borderRadius: 16, padding: "14px 20px", border: "2px solid #E9D5FF", fontSize: 22, fontWeight: 800 }}>
          Khả năng B: 2 đồng 10 xu + <span style={{ color: "#A855F7", fontSize: 26, fontWeight: 900 }}>[ ? ]</span> đồng 5 xu = 30 xu
        </div>
        <div style={{ background: "#FAF5FF", borderRadius: 16, padding: "14px 20px", border: "2px solid #E9D5FF", fontSize: 22, fontWeight: 800 }}>
          Khả năng C: 1 đồng 10 xu + <span style={{ color: "#A855F7", fontSize: 26, fontWeight: 900 }}>[ ? ]</span> đồng 5 xu = 30 xu
        </div>
        <div style={{ background: "#FAF5FF", borderRadius: 16, padding: "14px 20px", border: "2px solid #E9D5FF", fontSize: 22, fontWeight: 800 }}>
          Khả năng D: 0 đồng 10 xu + <span style={{ color: "#A855F7", fontSize: 26, fontWeight: 900 }}>[ ? ]</span> đồng 5 xu = 30 xu
        </div>
      </div>

      <div style={{ background: "#FDF2F8", padding: "16px 20px", borderRadius: 16, borderLeft: "6px solid #EC4899", fontSize: isLandscape ? 24 : 26, fontWeight: 800, color: "#BE185D", textAlign: "center" }}>
        ❓ Có tất cả bao nhiêu cách trả tiền? Hãy bình luận đáp án của con bên dưới nhé! 💬
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 9: Closing
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
      <h1 style={{ fontSize: isLandscape ? 44 : 48, fontWeight: 900, color: COLORS.primary, margin: "0 0 16px" }}>
        HỌC TOÁN CÙNG THẦY THẬT VUI!
      </h1>

      <div style={{ background: "#F0FDF4", border: `2px solid ${COLORS.primaryBorder}`, borderRadius: 20, padding: "16px 28px", maxWidth: 700, margin: "0 auto 24px", fontSize: isLandscape ? 24 : 26, fontWeight: 800, color: COLORS.text }}>
        👍 Các con hãy nhấn <b>Thích</b> và <b>Theo dõi</b> kênh để cùng thầy học thêm nhiều bài toán vui nhé!
      </div>

      <p style={{ fontSize: isLandscape ? 28 : 32, fontWeight: 900, color: COLORS.primary, margin: 0 }}>
        Thầy chúc các con luôn vui tươi và học toán thật giỏi! ❤️
      </p>
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
              TOÁN ĐỐ VUI — ĐỔI XU CHO CARRIE
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
          height: isLandscape ? "100%" : "calc(100% - 480px)",
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

        {/* Scene 5: Case 1 */}
        <Sequence
          from={
            SCENE_DURATIONS.intro +
            SCENE_DURATIONS.readEnglish +
            SCENE_DURATIONS.readTrans +
            SCENE_DURATIONS.strategy
          }
          durationInFrames={SCENE_DURATIONS.case1}
        >
          <SceneCase1Card isLandscape={isLandscape} />
        </Sequence>

        {/* Scene 6: Case 2 Guide */}
        <Sequence
          from={
            SCENE_DURATIONS.intro +
            SCENE_DURATIONS.readEnglish +
            SCENE_DURATIONS.readTrans +
            SCENE_DURATIONS.strategy +
            SCENE_DURATIONS.case1
          }
          durationInFrames={SCENE_DURATIONS.case2Guide}
        >
          <SceneCase2GuideCard isLandscape={isLandscape} />
        </Sequence>

        {/* Scene 7: Check */}
        <Sequence
          from={
            SCENE_DURATIONS.intro +
            SCENE_DURATIONS.readEnglish +
            SCENE_DURATIONS.readTrans +
            SCENE_DURATIONS.strategy +
            SCENE_DURATIONS.case1 +
            SCENE_DURATIONS.case2Guide
          }
          durationInFrames={SCENE_DURATIONS.check}
        >
          <SceneCheckCard isLandscape={isLandscape} />
        </Sequence>

        {/* Scene 8: Practice */}
        <Sequence
          from={
            SCENE_DURATIONS.intro +
            SCENE_DURATIONS.readEnglish +
            SCENE_DURATIONS.readTrans +
            SCENE_DURATIONS.strategy +
            SCENE_DURATIONS.case1 +
            SCENE_DURATIONS.case2Guide +
            SCENE_DURATIONS.check
          }
          durationInFrames={SCENE_DURATIONS.practice}
        >
          <ScenePracticeCard isLandscape={isLandscape} />
        </Sequence>

        {/* Scene 9: Closing */}
        <Sequence
          from={
            SCENE_DURATIONS.intro +
            SCENE_DURATIONS.readEnglish +
            SCENE_DURATIONS.readTrans +
            SCENE_DURATIONS.strategy +
            SCENE_DURATIONS.case1 +
            SCENE_DURATIONS.case2Guide +
            SCENE_DURATIONS.check +
            SCENE_DURATIONS.practice
          }
          durationInFrames={SCENE_DURATIONS.closing}
        >
          <SceneClosingCard isLandscape={isLandscape} />
        </Sequence>
      </div>

      {/* Portrait Bottom Coin Bank Tray */}
      {!isLandscape && <PortraitBottomTray />}
    </AbsoluteFill>
  );
};

export const MathCoinsPortrait: React.FC = () => <MathCoinsVideo orientation="portrait" />;
export const MathCoinsLandscape: React.FC = () => <MathCoinsVideo orientation="landscape" />;
