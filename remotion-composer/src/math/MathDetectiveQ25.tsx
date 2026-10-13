import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";

// ---------------------------------------------------------------------------
// Detective Style Palette (styles/math-detective.yaml)
// ---------------------------------------------------------------------------
const COLORS = {
  bg: "#1C1C1E",             // Nền bàn thám tử tối
  bgAlt: "#2C2C2E",          // Nền thẻ hồ sơ phụ
  folderPaper: "#F5E6C8",    // Giấy hồ sơ ngả vàng
  folderPaperDark: "#E8D5A3",
  paperText: "#1C1C1E",      // Chữ đen trên giấy vàng
  text: "#F5E6C8",           // Chữ vàng nhạt trên nền tối
  muted: "#8E8E93",          // Chữ phụ mờ
  pinRed: "#C0392B",         // Màu ghim đỏ & đường chỉ nối
  clueOrange: "#E67E22",     // Màu highlight manh mối & kích thước
  measureBlue: "#2563EB",    // Màu mũi tên đo đề bài gốc
  measureBlueLight: "#3B82F6",
  shadedRect: "#9CA3AF",     // Màu xám phần tô đậm EFGH
  shadedRectActive: "#D97706",
  boardBorder: "#3A2E1E",    // Viền bìa hồ sơ
  cardBorder: "#4A3B2C",
};

// ---------------------------------------------------------------------------
// Scene Durations in Frames (30 fps) - Total: 4230 frames = 141.0s
// Synchronized with master_narration.mp3
// ---------------------------------------------------------------------------
export const SCENE_DURATIONS = {
  intro: 480,        // 0.0s -> 16.0s (16.0s)
  readEnglish: 630,  // 16.0s -> 37.0s (21.0s)
  readTrans: 570,    // 37.0s -> 56.0s (19.0s)
  strategy: 390,     // 56.0s -> 69.0s (13.0s)
  solution: 900,     // 69.0s -> 99.0s (30.0s)
  check: 600,        // 99.0s -> 119.0s (20.0s)
  answer: 330,       // 119.0s -> 130.0s (11.0s)
  closing: 330,      // 130.0s -> 141.0s (11.0s)
};

// ---------------------------------------------------------------------------
// Reusable Detective SVG Clue Pin
// ---------------------------------------------------------------------------
export const CluePin: React.FC<{ size?: number; color?: string }> = ({
  size = 20,
  color = COLORS.pinRed,
}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{ display: "inline-block", verticalAlign: "middle" }}>
    <circle cx="12" cy="12" r="8" fill={color} stroke="#FFFFFF" strokeWidth="2" />
    <circle cx="10" cy="10" r="3" fill="rgba(255,255,255,0.6)" />
  </svg>
);

// ---------------------------------------------------------------------------
// Geometry Diagram Component: Square ABCD & Shaded Rectangle EFGH
// ---------------------------------------------------------------------------
export const GeometryDiagram: React.FC<{
  size?: number;
  highlightClues?: boolean;
  highlightSlide?: boolean;
  highlightCombine?: boolean;
  slideProgress?: number; // 0 to 1
  showSolutionHighlights?: boolean;
}> = ({
  size = 380,
  highlightClues = false,
  highlightSlide = false,
  highlightCombine = false,
  slideProgress = 0,
  showSolutionHighlights = false,
}) => {
  // Coordinate system: 0 to 400
  const pad = 50;
  const sqSize = 300;
  const ax = pad;
  const ay = pad;
  const bx = pad;
  const by = pad + sqSize;
  const cx = pad + sqSize;
  const cy = pad + sqSize;
  const dx = pad + sqSize;
  const dy = pad;

  // EFGH placement:
  // E at 40% (x=170), H at 65% (x=245), width w = 75
  const ex = ax + sqSize * 0.40;
  const hx = ax + sqSize * 0.65;
  const fx = ex;
  const gx = hx;
  const rectW = hx - ex;

  // Sliding segment Y position (from bottom BG to top AH)
  const currentSlideY = by - (by - ay) * slideProgress;

  return (
    <div style={{ display: "inline-flex", flexDirection: "column", alignItems: "center" }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 400 400"
        style={{
          background: "#161618",
          borderRadius: 16,
          border: `2px solid ${COLORS.cardBorder}`,
          boxShadow: "0 8px 24px rgba(0,0,0,0.6)",
        }}
      >
        {/* Subtle coordinate grid for detective blueprint aesthetic */}
        <defs>
          <pattern id="diagGrid" width="20" height="20" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="20" y2="0" stroke="rgba(245,230,200,0.04)" strokeWidth="1" />
            <line x1="0" y1="0" x2="0" y2="20" stroke="rgba(245,230,200,0.04)" strokeWidth="1" />
          </pattern>
          {/* Arrow markers */}
          <marker id="arrowBlue" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill={COLORS.measureBlue} />
          </marker>
          <marker id="arrowOrange" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill={COLORS.clueOrange} />
          </marker>
        </defs>
        <rect width="400" height="400" fill="url(#diagGrid)" />

        {/* Shaded Rectangle EFGH */}
        <rect
          x={ex}
          y={ay}
          width={rectW}
          height={sqSize}
          fill={showSolutionHighlights ? "rgba(230,126,34,0.4)" : COLORS.shadedRect}
          stroke={showSolutionHighlights ? COLORS.clueOrange : "#E2E8F0"}
          strokeWidth={showSolutionHighlights ? 3 : 2}
        />

        {/* Square ABCD outer border */}
        <rect
          x={ax}
          y={ay}
          width={sqSize}
          height={sqSize}
          fill="none"
          stroke={COLORS.folderPaper}
          strokeWidth="3.5"
        />

        {/* Vertical divider lines EF and HG */}
        <line x1={ex} y1={ay} x2={fx} y2={by} stroke="#FFFFFF" strokeWidth="2.5" />
        <line x1={hx} y1={dy} x2={gx} y2={cy} stroke="#FFFFFF" strokeWidth="2.5" />

        {/* Vertex Labels */}
        <text x={ax - 14} y={ay - 8} fill={COLORS.folderPaper} fontSize="20" fontWeight="bold" fontFamily="Courier Prime, monospace">A</text>
        <text x={dx + 10} y={dy - 8} fill={COLORS.folderPaper} fontSize="20" fontWeight="bold" fontFamily="Courier Prime, monospace">D</text>
        <text x={bx - 14} y={by + 20} fill={COLORS.folderPaper} fontSize="20" fontWeight="bold" fontFamily="Courier Prime, monospace">B</text>
        <text x={cx + 10} y={cy + 20} fill={COLORS.folderPaper} fontSize="20" fontWeight="bold" fontFamily="Courier Prime, monospace">C</text>

        <text x={ex - 6} y={ay - 8} fill={COLORS.folderPaper} fontSize="19" fontWeight="bold" fontFamily="Courier Prime, monospace">E</text>
        <text x={hx - 6} y={dy - 8} fill={COLORS.folderPaper} fontSize="19" fontWeight="bold" fontFamily="Courier Prime, monospace">H</text>
        <text x={fx - 6} y={by + 20} fill={COLORS.folderPaper} fontSize="19" fontWeight="bold" fontFamily="Courier Prime, monospace">F</text>
        <text x={gx - 6} y={cy + 20} fill={COLORS.folderPaper} fontSize="19" fontWeight="bold" fontFamily="Courier Prime, monospace">G</text>

        {/* Top Measurement: ED = 4 cm (from E to D) */}
        <g opacity={1}>
          <line
            x1={ex}
            y1={ay - 22}
            x2={dx}
            y2={ay - 22}
            stroke={highlightCombine ? COLORS.clueOrange : COLORS.measureBlue}
            strokeWidth="2.5"
          />
          {/* Arrow ends */}
          <line x1={ex} y1={ay - 28} x2={ex} y2={ay - 16} stroke={highlightCombine ? COLORS.clueOrange : COLORS.measureBlue} strokeWidth="2" />
          <line x1={dx} y1={ay - 28} x2={dx} y2={ay - 16} stroke={highlightCombine ? COLORS.clueOrange : COLORS.measureBlue} strokeWidth="2" />
          <rect x={(ex + dx) / 2 - 26} y={ay - 35} width="52" height="18" fill="#1C1C1E" rx="3" />
          <text
            x={(ex + dx) / 2}
            y={ay - 22}
            fill={highlightCombine ? COLORS.clueOrange : COLORS.measureBlueLight}
            fontSize="15"
            fontWeight="bold"
            textAnchor="middle"
            dominantBaseline="middle"
            fontFamily="Courier Prime, monospace"
          >
            4 cm
          </text>
        </g>

        {/* Bottom Measurement: BG = 8 cm (from B to G) */}
        <g opacity={1}>
          <line
            x1={bx}
            y1={by + 28}
            x2={gx}
            y2={by + 28}
            stroke={highlightClues ? COLORS.clueOrange : COLORS.measureBlue}
            strokeWidth="2.5"
          />
          <line x1={bx} y1={by + 22} x2={bx} y2={by + 34} stroke={highlightClues ? COLORS.clueOrange : COLORS.measureBlue} strokeWidth="2" />
          <line x1={gx} y1={by + 22} x2={gx} y2={by + 34} stroke={highlightClues ? COLORS.clueOrange : COLORS.measureBlue} strokeWidth="2" />
          <rect x={(bx + gx) / 2 - 28} y={by + 34} width="56" height="18" fill="#1C1C1E" rx="3" />
          <text
            x={(bx + gx) / 2}
            y={by + 43}
            fill={highlightClues ? COLORS.clueOrange : COLORS.measureBlueLight}
            fontSize="15"
            fontWeight="bold"
            textAnchor="middle"
            dominantBaseline="middle"
            fontFamily="Courier Prime, monospace"
          >
            8 cm
          </text>
        </g>

        {/* Sliding Animation: Segment BG (8 cm) moving up to AH (8 cm) */}
        {highlightSlide && (
          <g>
            {/* Projected segment at currentSlideY */}
            <line
              x1={ax}
              y1={currentSlideY}
              x2={hx}
              y2={currentSlideY}
              stroke={COLORS.clueOrange}
              strokeWidth="4"
              strokeDasharray="6 4"
            />
            {/* Ghost connector lines */}
            <line x1={ax} y1={by} x2={ax} y2={currentSlideY} stroke="rgba(230,126,34,0.4)" strokeWidth="1.5" strokeDasharray="3 3" />
            <line x1={hx} y1={cy} x2={hx} y2={currentSlideY} stroke="rgba(230,126,34,0.4)" strokeWidth="1.5" strokeDasharray="3 3" />
            {slideProgress > 0.8 && (
              <text
                x={(ax + hx) / 2}
                y={ay + 18}
                fill={COLORS.clueOrange}
                fontSize="16"
                fontWeight="900"
                textAnchor="middle"
                fontFamily="Courier Prime, monospace"
              >
                AH = BG = 8 cm
              </text>
            )}
          </g>
        )}

        {/* Combined Segment Highlight in Solution (AH + ED) */}
        {highlightCombine && (
          <g>
            {/* AH bracket / line */}
            <line x1={ax} y1={ay + 14} x2={hx} y2={ay + 14} stroke={COLORS.clueOrange} strokeWidth="3" />
            {/* ED bracket / line */}
            <line x1={ex} y1={ay + 26} x2={dx} y2={ay + 26} stroke={COLORS.pinRed} strokeWidth="3" />
            {/* Overlap marker on EH */}
            <rect x={ex} y={ay} width={rectW} height="12" fill="rgba(192,57,43,0.7)" />
          </g>
        )}
      </svg>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Header Component (Noir Detective File Badge)
// ---------------------------------------------------------------------------
const DetectiveHeader: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => (
  <div
    style={{
      width: "100%",
      height: isLandscape ? 76 : 90,
      background: "#18181A",
      borderBottom: `2px solid ${COLORS.pinRed}`,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: isLandscape ? "0 40px" : "0 32px",
      boxSizing: "border-box",
      zIndex: 20,
    }}
  >
    <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
      <CluePin size={24} />
      <span
        style={{
          fontFamily: "Courier Prime, monospace",
          fontWeight: 700,
          fontSize: isLandscape ? 22 : 24,
          color: COLORS.folderPaper,
          letterSpacing: "0.04em",
        }}
      >
        HỒ SƠ VỤ ÁN #25 · AMO 2022 LỚP 2
      </span>
    </div>
    <div
      style={{
        background: COLORS.pinRed,
        color: "#FFFFFF",
        padding: "6px 16px",
        borderRadius: 4,
        fontFamily: "Courier Prime, monospace",
        fontWeight: 700,
        fontSize: isLandscape ? 16 : 18,
        letterSpacing: "0.06em",
        boxShadow: "0 2px 8px rgba(192,57,43,0.5)",
      }}
    >
      TOP SECRET
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Scene 1: Hook & Introduction Card
// ---------------------------------------------------------------------------
const SceneIntroCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: COLORS.bgAlt,
        borderRadius: 12,
        border: `3px solid ${COLORS.pinRed}`,
        padding: isLandscape ? "36px 44px" : "36px 28px",
        boxShadow: "0 16px 40px rgba(0,0,0,0.7)",
        maxWidth: isLandscape ? 1100 : 960,
        width: "90%",
        margin: "0 auto",
        textAlign: "center",
        transform: `scale(${scale})`,
        fontFamily: "Courier Prime, monospace",
      }}
    >
      <div
        style={{
          background: COLORS.folderPaper,
          color: COLORS.paperText,
          padding: "6px 20px",
          borderRadius: 4,
          fontSize: isLandscape ? 18 : 20,
          fontWeight: 700,
          display: "inline-block",
          marginBottom: 20,
          letterSpacing: "0.05em",
        }}
      >
        🔎 THÁM TỬ TOÁN HỌC OLYMPIC
      </div>

      <h1
        style={{
          fontSize: isLandscape ? 36 : 40,
          fontWeight: 700,
          color: COLORS.text,
          margin: "0 0 20px",
          lineHeight: 1.35,
        }}
      >
        VỤ ÁN HÌNH CHỮ NHẬT BÍ ẨN
      </h1>

      <div
        style={{
          background: "#1E1A16",
          borderLeft: `6px solid ${COLORS.clueOrange}`,
          padding: "18px 24px",
          textAlign: "left",
          marginBottom: 24,
          borderRadius: 6,
        }}
      >
        <div style={{ color: COLORS.clueOrange, fontSize: isLandscape ? 22 : 24, fontWeight: 700, marginBottom: 8 }}>
          MANH MỐI BÍ ẨN:
        </div>
        <p style={{ color: COLORS.text, fontSize: isLandscape ? 20 : 22, margin: 0, lineHeight: 1.5 }}>
          Một hình chữ nhật nằm lọt thỏm trong hình vuông ABCD với đúng 2 manh mối: <b>ED = 4 cm</b> và <b>BG = 8 cm</b>.
        </p>
      </div>

      <div
        style={{
          background: COLORS.pinRed,
          color: "#FFFFFF",
          padding: "16px 24px",
          borderRadius: 6,
          fontSize: isLandscape ? 24 : 26,
          fontWeight: 700,
          boxShadow: "0 6px 18px rgba(192,57,43,0.4)",
        }}
      >
        ❓ Làm sao tìm ra chu vi hình chữ nhật tô đậm EFGH?
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 2: English Problem Verbatim Card + Diagram
// ---------------------------------------------------------------------------
const SceneReadEnglishCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: isLandscape ? "row" : "column",
        alignItems: "center",
        justifyContent: "center",
        gap: isLandscape ? 36 : 24,
        width: "92%",
        maxWidth: isLandscape ? 1200 : 960,
        transform: `scale(${scale})`,
        fontFamily: "Courier Prime, monospace",
      }}
    >
      <GeometryDiagram size={isLandscape ? 360 : 330} />

      <div
        style={{
          flex: 1,
          background: COLORS.bgAlt,
          borderRadius: 12,
          border: `2px solid ${COLORS.measureBlue}`,
          padding: isLandscape ? "32px 36px" : "28px 24px",
          boxShadow: "0 12px 36px rgba(0,0,0,0.7)",
          textAlign: "left",
        }}
      >
        <div
          style={{
            background: COLORS.measureBlue,
            color: "#FFFFFF",
            padding: "6px 16px",
            borderRadius: 4,
            fontSize: 16,
            fontWeight: 700,
            display: "inline-block",
            marginBottom: 16,
            letterSpacing: "0.05em",
          }}
        >
          ORIGINAL EXAM QUESTION (ENGLISH)
        </div>

        <div style={{ fontSize: 24, fontWeight: 700, color: COLORS.clueOrange, marginBottom: 10 }}>
          Question 25.
        </div>

        <p style={{ fontSize: isLandscape ? 22 : 24, color: COLORS.text, lineHeight: 1.5, margin: "0 0 16px" }}>
          In the following figure, <b>ABCD is a square</b>; the shaded region <b>EFGH is a rectangle</b>.
        </p>

        <div
          style={{
            background: "#161618",
            borderLeft: `4px solid ${COLORS.measureBlue}`,
            padding: "12px 18px",
            marginBottom: 16,
            fontSize: isLandscape ? 21 : 22,
            color: COLORS.folderPaper,
          }}
        >
          • <b>ED = 4 cm</b><br />
          • <b>BG = 8 cm</b>
        </div>

        <p style={{ fontSize: isLandscape ? 22 : 24, fontWeight: 700, color: COLORS.clueOrange, margin: 0 }}>
          What is the perimeter of the shaded rectangle EFGH in cm?
        </p>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 3: Vietnamese Translation Card + Diagram
// ---------------------------------------------------------------------------
const SceneTranslationCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: isLandscape ? "row" : "column",
        alignItems: "center",
        justifyContent: "center",
        gap: isLandscape ? 36 : 24,
        width: "92%",
        maxWidth: isLandscape ? 1200 : 960,
        transform: `scale(${scale})`,
        fontFamily: "Courier Prime, monospace",
      }}
    >
      <GeometryDiagram size={isLandscape ? 360 : 330} highlightClues />

      <div
        style={{
          flex: 1,
          background: COLORS.bgAlt,
          borderRadius: 12,
          border: `2px solid ${COLORS.pinRed}`,
          padding: isLandscape ? "32px 36px" : "28px 24px",
          boxShadow: "0 12px 36px rgba(0,0,0,0.7)",
          textAlign: "left",
        }}
      >
        <div
          style={{
            background: COLORS.pinRed,
            color: "#FFFFFF",
            padding: "6px 16px",
            borderRadius: 4,
            fontSize: 16,
            fontWeight: 700,
            display: "inline-block",
            marginBottom: 16,
            letterSpacing: "0.05em",
          }}
        >
          BẢN DỊCH TIẾNG VIỆT CHUẨN XÁC
        </div>

        <div style={{ fontSize: 24, fontWeight: 700, color: COLORS.clueOrange, marginBottom: 10 }}>
          Câu 25.
        </div>

        <p style={{ fontSize: isLandscape ? 21 : 23, color: COLORS.text, lineHeight: 1.5, margin: "0 0 16px" }}>
          Trong hình vẽ dưới đây, <b>ABCD là một hình vuông</b>; phần tô đậm <b>EFGH là một hình chữ nhật</b>.
        </p>

        <div
          style={{
            background: "#161618",
            borderLeft: `4px solid ${COLORS.pinRed}`,
            padding: "12px 18px",
            marginBottom: 16,
            fontSize: isLandscape ? 20 : 22,
            color: COLORS.folderPaper,
          }}
        >
          • Đoạn <b>ED = 4 cm</b><br />
          • Đoạn <b>BG = 8 cm</b>
        </div>

        <p style={{ fontSize: isLandscape ? 21 : 23, fontWeight: 700, color: COLORS.clueOrange, margin: 0 }}>
          Hỏi chu vi của hình chữ nhật tô đậm EFGH bằng bao nhiêu xăng-ti-mét?
        </p>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 4: Strategy & Clue Analysis Card
// ---------------------------------------------------------------------------
const SceneStrategyCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: COLORS.bgAlt,
        borderRadius: 12,
        border: `3px solid ${COLORS.clueOrange}`,
        padding: isLandscape ? "36px 44px" : "32px 24px",
        boxShadow: "0 16px 40px rgba(0,0,0,0.7)",
        maxWidth: isLandscape ? 1100 : 960,
        width: "90%",
        margin: "0 auto",
        textAlign: "left",
        transform: `scale(${scale})`,
        fontFamily: "Courier Prime, monospace",
      }}
    >
      <div
        style={{
          background: COLORS.clueOrange,
          color: "#FFFFFF",
          padding: "6px 20px",
          borderRadius: 4,
          fontSize: 18,
          fontWeight: 700,
          display: "inline-block",
          marginBottom: 20,
        }}
      >
        💡 BẢNG PHÂN TÍCH CHIẾN LƯỢC
      </div>

      <h2 style={{ fontSize: isLandscape ? 30 : 34, color: COLORS.text, margin: "0 0 20px" }}>
        MỤC TIÊU: TÍNH CHU VI HÌNH CHỮ NHẬT
      </h2>

      <div style={{ display: "flex", flexDirection: "column", gap: 16, marginBottom: 24 }}>
        <div style={{ background: "#1C1C1E", padding: "16px 20px", borderRadius: 8, borderLeft: `5px solid ${COLORS.pinRed}` }}>
          <div style={{ color: COLORS.pinRed, fontWeight: 700, fontSize: 20 }}>CÔNG THỨC CHU VI:</div>
          <div style={{ color: COLORS.folderPaper, fontSize: 22, marginTop: 4 }}>
            Chu vi = <b>2 × (Chiều dài + Chiều rộng)</b>
          </div>
        </div>

        <div style={{ background: "#1C1C1E", padding: "16px 20px", borderRadius: 8, borderLeft: `5px solid ${COLORS.clueOrange}` }}>
          <div style={{ color: COLORS.clueOrange, fontWeight: 700, fontSize: 20 }}>CHÌA KHÓA PHÁ ÁN:</div>
          <div style={{ color: COLORS.folderPaper, fontSize: 22, marginTop: 4 }}>
            Ta <b>KHÔNG CẦN</b> tìm riêng từng cạnh! Chỉ cần tìm ra <b>TỔNG (dài + rộng)</b>.
          </div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 5: Hero Solution Animation Card (Sliding & Overlapping Segments)
// ---------------------------------------------------------------------------
const SceneSolutionCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Slide progress from frame 90 to 240 (3s to 8s)
  const slideProgress = interpolate(frame, [90, 240], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const step2Appear = frame > 270;
  const step3Appear = frame > 540;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: isLandscape ? "row" : "column",
        alignItems: "center",
        justifyContent: "center",
        gap: isLandscape ? 36 : 20,
        width: "94%",
        maxWidth: isLandscape ? 1260 : 980,
        fontFamily: "Courier Prime, monospace",
      }}
    >
      <GeometryDiagram
        size={isLandscape ? 380 : 340}
        highlightClues
        highlightSlide={frame > 60}
        highlightCombine={frame > 450}
        slideProgress={slideProgress}
        showSolutionHighlights={frame > 540}
      />

      <div
        style={{
          flex: 1,
          background: COLORS.bgAlt,
          borderRadius: 12,
          border: `2px solid ${COLORS.clueOrange}`,
          padding: isLandscape ? "28px 32px" : "24px 20px",
          boxShadow: "0 12px 36px rgba(0,0,0,0.7)",
          textAlign: "left",
        }}
      >
        <div
          style={{
            background: COLORS.clueOrange,
            color: "#FFFFFF",
            padding: "5px 16px",
            borderRadius: 4,
            fontSize: 16,
            fontWeight: 700,
            display: "inline-block",
            marginBottom: 14,
          }}
        >
          🔍 CÁC BƯỚC PHÁ ÁN HÌNH HỌC
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Manh mối 1 */}
          <div style={{ background: "#1C1C1E", padding: "12px 16px", borderRadius: 6, borderLeft: `4px solid ${COLORS.folderPaper}` }}>
            <div style={{ color: COLORS.clueOrange, fontWeight: 700, fontSize: 18 }}>
              Manh mối 1: Chiều dài EFGH = Cạnh hình vuông
            </div>
            <div style={{ color: COLORS.text, fontSize: 17, marginTop: 2 }}>
              Chiều dài = <b>EF = HG = Cạnh ABCD</b>.
            </div>
          </div>

          {/* Manh mối 2 */}
          <div style={{ background: "#1C1C1E", padding: "12px 16px", borderRadius: 6, borderLeft: `4px solid ${COLORS.pinRed}` }}>
            <div style={{ color: COLORS.pinRed, fontWeight: 700, fontSize: 18 }}>
              Manh mối 2: Chiếu đoạn BG lên đỉnh AH
            </div>
            <div style={{ color: COLORS.text, fontSize: 17, marginTop: 2 }}>
              Vì AE = BF và EH = FG nên <b>AH = BG = 8 cm</b>!
            </div>
          </div>

          {/* Ghép đoạn */}
          {step2Appear && (
            <div style={{ background: "#251C14", padding: "14px 16px", borderRadius: 6, border: `2px solid ${COLORS.clueOrange}` }}>
              <div style={{ color: COLORS.clueOrange, fontWeight: 700, fontSize: 19 }}>
                ⭐ GHÉP HAI ĐOẠN MANH MỐI:
              </div>
              <div style={{ color: "#FFFFFF", fontSize: 18, marginTop: 4, lineHeight: 1.45 }}>
                <b>AH + ED = 8 + 4 = 12 cm</b>
                <br />
                Đoạn EH được tính 2 lần:
                <br />
                <b>(AE + EH + HD) + EH = Cạnh vuông + Chiều rộng = 12 cm!</b>
              </div>
            </div>
          )}

          {/* Kết luận nửa chu vi */}
          {step3Appear && (
            <div style={{ background: COLORS.pinRed, padding: "12px 16px", borderRadius: 6 }}>
              <div style={{ color: "#FFFFFF", fontSize: 19, fontWeight: 700 }}>
                👉 (Chiều dài) + (Chiều rộng) = 12 cm!
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 6: Verification (Check) Card
// ---------------------------------------------------------------------------
const SceneCheckCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: COLORS.bgAlt,
        borderRadius: 12,
        border: `3px solid ${COLORS.folderPaper}`,
        padding: isLandscape ? "36px 44px" : "32px 24px",
        boxShadow: "0 16px 40px rgba(0,0,0,0.7)",
        maxWidth: isLandscape ? 1100 : 960,
        width: "90%",
        margin: "0 auto",
        textAlign: "left",
        transform: `scale(${scale})`,
        fontFamily: "Courier Prime, monospace",
      }}
    >
      <div
        style={{
          background: COLORS.folderPaper,
          color: COLORS.paperText,
          padding: "6px 20px",
          borderRadius: 4,
          fontSize: 18,
          fontWeight: 700,
          display: "inline-block",
          marginBottom: 20,
        }}
      >
        ⚖️ KIỂM CHỨNG TÍNH ĐÚNG ĐẮN
      </div>

      <h2 style={{ fontSize: isLandscape ? 30 : 34, color: COLORS.text, margin: "0 0 20px" }}>
        TỔNG (DÀI + RỘNG) LUÔN KHÔNG ĐỔI = 12 CM
      </h2>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ background: "#1C1C1E", padding: "18px 22px", borderRadius: 8, borderLeft: `5px solid #10B981` }}>
          <div style={{ color: "#10B981", fontSize: 22, fontWeight: 700 }}>
            Trường hợp 1: Nếu cạnh vuông = 10 cm
          </div>
          <div style={{ color: COLORS.folderPaper, fontSize: 20, marginTop: 4 }}>
            Chiều rộng = 12 - 10 = <b>2 cm</b> (ED = 4 cm, AE = 6 cm hợp lý). Tổng = <b>12 cm</b>.
          </div>
        </div>

        <div style={{ background: "#1C1C1E", padding: "18px 22px", borderRadius: 8, borderLeft: `5px solid #10B981` }}>
          <div style={{ color: "#10B981", fontSize: 22, fontWeight: 700 }}>
            Trường hợp 2: Nếu cạnh vuông = 9 cm
          </div>
          <div style={{ color: COLORS.folderPaper, fontSize: 20, marginTop: 4 }}>
            Chiều rộng = 12 - 9 = <b>3 cm</b> (ED = 4 cm, AE = 5 cm hợp lý). Tổng = <b>12 cm</b>.
          </div>
        </div>

        <div style={{ color: COLORS.clueOrange, fontSize: 22, fontWeight: 700, marginTop: 8 }}>
          ✔ Trong mọi trường hợp, tổng luôn luôn là 12 cm!
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 7: Official Answer Card
// ---------------------------------------------------------------------------
const SceneAnswerCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const stamp = spring({ frame, fps, config: { damping: 10, stiffness: 180 } });

  return (
    <div
      style={{
        background: COLORS.bgAlt,
        borderRadius: 12,
        border: `3px solid ${COLORS.pinRed}`,
        padding: isLandscape ? "44px 50px" : "40px 28px",
        boxShadow: "0 20px 50px rgba(0,0,0,0.8)",
        maxWidth: isLandscape ? 1100 : 960,
        width: "90%",
        margin: "0 auto",
        textAlign: "center",
        fontFamily: "Courier Prime, monospace",
      }}
    >
      <div
        style={{
          background: COLORS.pinRed,
          color: "#FFFFFF",
          padding: "8px 24px",
          borderRadius: 4,
          fontSize: 20,
          fontWeight: 700,
          display: "inline-block",
          marginBottom: 20,
          letterSpacing: "0.05em",
        }}
      >
        🏆 KẾT LUẬN ĐÁP SỐ CHÍNH THỨC
      </div>

      <div style={{ fontSize: isLandscape ? 32 : 36, color: COLORS.text, marginBottom: 20 }}>
        Chu vi hình chữ nhật EFGH:
      </div>

      <div
        style={{
          background: "#161618",
          border: `2px dashed ${COLORS.clueOrange}`,
          padding: "16px 28px",
          borderRadius: 8,
          fontSize: isLandscape ? 28 : 30,
          color: COLORS.clueOrange,
          marginBottom: 28,
        }}
      >
        Chu vi = 12 × 2 = <b>24 cm</b>
      </div>

      {/* Red Case Solved Stamp */}
      <div
        style={{
          display: "inline-block",
          transform: `scale(${stamp}) rotate(-8deg)`,
          border: `6px solid ${COLORS.pinRed}`,
          color: COLORS.pinRed,
          padding: "16px 40px",
          borderRadius: 8,
          fontSize: isLandscape ? 48 : 52,
          fontWeight: 900,
          letterSpacing: "0.15em",
          background: "rgba(192,57,43,0.12)",
          boxShadow: "0 8px 30px rgba(192,57,43,0.3)",
        }}
      >
        ĐÃ PHÁ ÁN: 24 CM
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 8: Closing & Good Luck Wish Card
// ---------------------------------------------------------------------------
const SceneClosingCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        background: COLORS.bgAlt,
        borderRadius: 12,
        border: `3px solid ${COLORS.folderPaper}`,
        padding: isLandscape ? "44px 50px" : "40px 28px",
        boxShadow: "0 20px 50px rgba(0,0,0,0.8)",
        maxWidth: isLandscape ? 1100 : 960,
        width: "90%",
        margin: "0 auto",
        textAlign: "center",
        transform: `scale(${scale})`,
        fontFamily: "Courier Prime, monospace",
      }}
    >
      <div style={{ fontSize: 56, marginBottom: 12 }}>🕵️‍♂️</div>

      <h1 style={{ fontSize: isLandscape ? 38 : 42, color: COLORS.folderPaper, margin: "0 0 16px" }}>
        HỒ SƠ VỤ ÁN ĐÃ KHÉP LẠI
      </h1>

      <p style={{ fontSize: isLandscape ? 24 : 26, color: COLORS.text, lineHeight: 1.5, margin: "0 0 24px" }}>
        Phương pháp ghép đoạn thẳng trực quan giúp ta chinh phục đề thi Olympic thật dễ dàng!
      </p>

      <div
        style={{
          background: COLORS.pinRed,
          color: "#FFFFFF",
          padding: "18px 28px",
          borderRadius: 6,
          fontSize: isLandscape ? 24 : 26,
          fontWeight: 700,
          boxShadow: "0 6px 20px rgba(192,57,43,0.4)",
        }}
      >
        ❤️ Chúc các con học tập thật tốt và luôn tự tin khi giải toán!
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Video Component (Handles Portrait and Landscape)
// ---------------------------------------------------------------------------
export const MathDetectiveVideo: React.FC<{ orientation: "portrait" | "landscape" }> = ({
  orientation,
}) => {
  const isLandscape = orientation === "landscape";

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.bg,
        fontFamily: "Courier Prime, monospace",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Synchronized Master Audio Track */}
      <Audio src={staticFile("master_narration.mp3")} />

      {/* Header bar */}
      <DetectiveHeader isLandscape={isLandscape} />

      {/* Main Container */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: isLandscape ? "20px 40px" : "20px 16px",
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
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Compositions for Root.tsx
// ---------------------------------------------------------------------------
export const MathDetectivePortrait: React.FC = () => (
  <MathDetectiveVideo orientation="portrait" />
);

export const MathDetectiveLandscape: React.FC = () => (
  <MathDetectiveVideo orientation="landscape" />
);
