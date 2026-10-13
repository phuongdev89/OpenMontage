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

// ---------------------------------------------------------------------------
// Chalkboard Theme Color Palette (from styles/math-chalkboard.yaml)
// ---------------------------------------------------------------------------
const CHALK = {
  boardBg: "#2D4A3E",          // Bảng xanh đen kinh điển
  boardAlt: "#243B32",         // Bảng tối hơn cho container
  frameWood: "#5D4037",        // Khung gỗ viền ngoài
  frameWoodLight: "#8D6E63",
  white: "#F5F5F0",            // Phấn trắng ngà
  yellow: "#FFD700",           // Phấn vàng highlight
  orange: "#FF9500",           // Phấn cam nhấn mạnh
  borderChalk: "#B0C4B8",      // Viền phấn mờ
  mutedChalk: "#9BB5A8",       // Chữ phấn mờ
  chalkDust: "rgba(200, 216, 200, 0.15)",
};

export const SCENE_DURATIONS = {
  intro: 504,       // 16.80s
  readEnglish: 336, // 11.20s
  readTrans: 288,   // 9.60s
  strategy: 396,    // 13.20s
  solution: 408,    // 13.60s
  check: 306,       // 10.20s
  answer: 126,      // 4.20s
  closing: 126,     // 4.20s
};

// Total frames: 2490 @ 30fps = 83.00s

// ---------------------------------------------------------------------------
// Chalkboard Texture & Frame Container
// ---------------------------------------------------------------------------
const ChalkboardFrame: React.FC<{
  children: React.ReactNode;
  isLandscape: boolean;
}> = ({ children, isLandscape }) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: CHALK.boardBg,
        backgroundImage: `
          radial-gradient(circle at 50% 40%, rgba(255,255,255,0.06) 0%, transparent 70%),
          radial-gradient(circle at 20% 80%, rgba(0,0,0,0.15) 0%, transparent 60%)
        `,
        border: isLandscape ? "18px solid #5D4037" : "14px solid #5D4037",
        boxSizing: "border-box",
        position: "relative",
        overflow: "hidden",
        display: "flex",
        flexDirection: isLandscape ? "row" : "column",
        fontFamily: "'Caveat', 'Patrick Hand', 'Comic Sans MS', cursive, sans-serif",
      }}
    >
      {/* Subtle chalk dust layer */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          pointerEvents: "none",
          opacity: 0.25,
          backgroundImage: `radial-gradient(rgba(240,245,240,0.4) 1px, transparent 1px)`,
          backgroundSize: "24px 24px",
        }}
      />
      {children}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Header / Rail Components
// ---------------------------------------------------------------------------
const ChalkHeaderPortrait: React.FC = () => {
  return (
    <div
      style={{
        width: "100%",
        padding: "36px 30px 16px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        borderBottom: `2px dashed ${CHALK.borderChalk}`,
        zIndex: 10,
      }}
    >
      <div
        style={{
          display: "inline-block",
          padding: "6px 20px",
          borderRadius: 20,
          border: `2px solid ${CHALK.yellow}`,
          color: CHALK.yellow,
          fontSize: 28,
          fontWeight: 700,
          letterSpacing: "0.05em",
          marginBottom: 8,
          textTransform: "uppercase",
        }}
      >
        AMO 2022 • Lớp 2 • Câu 24
      </div>
      <div
        style={{
          color: CHALK.white,
          fontSize: 34,
          fontWeight: 700,
          textAlign: "center",
          textShadow: "0 0 4px rgba(255,255,255,0.4)",
        }}
      >
        BÀI TOÁN NHÂN MỘT SỐ VỚI 10
      </div>
    </div>
  );
};

const ChalkRailLandscape: React.FC = () => {
  return (
    <div
      style={{
        width: 360,
        height: "100%",
        padding: "40px 24px",
        borderRight: `3px dashed ${CHALK.borderChalk}`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "space-between",
        boxSizing: "border-box",
        backgroundColor: CHALK.boardAlt,
        zIndex: 10,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>
        <div
          style={{
            padding: "8px 18px",
            border: `2px solid ${CHALK.yellow}`,
            borderRadius: 16,
            color: CHALK.yellow,
            fontSize: 24,
            fontWeight: 700,
            textAlign: "center",
            marginBottom: 20,
          }}
        >
          AMO 2022 • GRADE 2
        </div>
        <div
          style={{
            color: CHALK.white,
            fontSize: 32,
            fontWeight: 700,
            textAlign: "center",
            lineHeight: 1.3,
            marginBottom: 24,
          }}
        >
          BÀI TOÁN NHÂN VỚI 10
        </div>
        <div
          style={{
            width: "80%",
            height: 2,
            backgroundColor: CHALK.borderChalk,
            marginBottom: 24,
          }}
        />
        <div
          style={{
            backgroundColor: "rgba(0,0,0,0.2)",
            border: `1px solid ${CHALK.borderChalk}`,
            borderRadius: 12,
            padding: "16px 14px",
            width: "100%",
            color: CHALK.white,
            fontSize: 22,
            lineHeight: 1.6,
          }}
        >
          <div style={{ color: CHALK.yellow, fontWeight: 700, marginBottom: 6 }}>
            Phương Pháp:
          </div>
          <div>• Sơ đồ đoạn thẳng</div>
          <div>• Hiệu số phần bằng nhau</div>
          <div>• Tính nhẩm nhanh</div>
        </div>
      </div>

      <div
        style={{
          color: CHALK.mutedChalk,
          fontSize: 20,
          textAlign: "center",
        }}
      >
        Toán Quốc Tế Tiểu Học
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 1: Intro Card
// ---------------------------------------------------------------------------
const SceneIntroCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        padding: isLandscape ? "20px 40px" : "20px",
        boxSizing: "border-box",
        transform: `scale(${scale})`,
      }}
    >
      <div
        style={{
          border: `3px solid ${CHALK.white}`,
          borderRadius: 20,
          padding: isLandscape ? "36px 48px" : "32px 24px",
          backgroundColor: "rgba(0,0,0,0.25)",
          boxShadow: "inset 0 0 30px rgba(0,0,0,0.3)",
          maxWidth: isLandscape ? 1100 : 960,
          width: "100%",
          textAlign: "center",
        }}
      >
        <div
          style={{
            color: CHALK.yellow,
            fontSize: isLandscape ? 36 : 38,
            fontWeight: 700,
            marginBottom: 16,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          Thử Thách Toán Tư Duy
        </div>

        <div
          style={{
            color: CHALK.white,
            fontSize: isLandscape ? 44 : 42,
            lineHeight: 1.5,
            fontWeight: 600,
            marginBottom: 30,
          }}
        >
          "Một số khi <span style={{ color: CHALK.yellow, textDecoration: "underline" }}>nhân với 10</span> thì được kết quả{" "}
          <span style={{ color: CHALK.yellow, textDecoration: "underline" }}>nhiều hơn 63 đơn vị</span> so với số ban đầu."
        </div>

        {/* Visual Mystery Box */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: isLandscape ? 24 : 16,
            fontSize: isLandscape ? 52 : 46,
            color: CHALK.white,
            fontWeight: 700,
            margin: "24px 0",
            flexWrap: "wrap",
          }}
        >
          <div
            style={{
              padding: "10px 28px",
              border: `3px dashed ${CHALK.yellow}`,
              borderRadius: 14,
              backgroundColor: CHALK.boardAlt,
              color: CHALK.yellow,
            }}
          >
            ?
          </div>
          <div>× 10 =</div>
          <div
            style={{
              padding: "10px 28px",
              border: `3px dashed ${CHALK.yellow}`,
              borderRadius: 14,
              backgroundColor: CHALK.boardAlt,
              color: CHALK.yellow,
            }}
          >
            ?
          </div>
          <div>+ 63</div>
        </div>

        <div
          style={{
            color: CHALK.mutedChalk,
            fontSize: isLandscape ? 30 : 32,
            marginTop: 20,
          }}
        >
          Làm sao tìm lại số ban đầu chỉ bằng một phép tính nhẩm?
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 2: Read English Card
// ---------------------------------------------------------------------------
const SceneReadEnglishCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = spring({ frame, fps, config: { damping: 16 } });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        padding: isLandscape ? "20px 40px" : "20px",
        boxSizing: "border-box",
        opacity,
      }}
    >
      <div
        style={{
          border: `3px solid ${CHALK.borderChalk}`,
          borderRadius: 20,
          padding: isLandscape ? "40px 50px" : "36px 26px",
          backgroundColor: "rgba(0,0,0,0.25)",
          maxWidth: isLandscape ? 1100 : 960,
          width: "100%",
          textAlign: "left",
        }}
      >
        <div
          style={{
            display: "inline-block",
            padding: "6px 18px",
            backgroundColor: CHALK.yellow,
            color: CHALK.boardAlt,
            borderRadius: 8,
            fontSize: isLandscape ? 26 : 28,
            fontWeight: 700,
            marginBottom: 24,
            textTransform: "uppercase",
          }}
        >
          Original English Question
        </div>

        <div
          style={{
            color: CHALK.white,
            fontSize: isLandscape ? 40 : 38,
            lineHeight: 1.6,
            fontWeight: 600,
            marginBottom: 24,
          }}
        >
          <strong style={{ color: CHALK.yellow }}>Question 24.</strong> If a number is{" "}
          <span style={{ color: CHALK.yellow, borderBottom: `2px solid ${CHALK.yellow}` }}>
            multiplied by 10
          </span>
          , then the result is{" "}
          <span style={{ color: CHALK.yellow, borderBottom: `2px solid ${CHALK.yellow}` }}>
            63 more
          </span>{" "}
          than the original number.
        </div>

        <div
          style={{
            color: CHALK.yellow,
            fontSize: isLandscape ? 44 : 42,
            fontWeight: 700,
            marginTop: 16,
          }}
        >
          What is this number?
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 3: Read Translation Card
// ---------------------------------------------------------------------------
const SceneTranslationCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = spring({ frame, fps, config: { damping: 16 } });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        padding: isLandscape ? "20px 40px" : "20px",
        boxSizing: "border-box",
        opacity,
      }}
    >
      <div
        style={{
          border: `3px solid ${CHALK.borderChalk}`,
          borderRadius: 20,
          padding: isLandscape ? "36px 48px" : "32px 24px",
          backgroundColor: "rgba(0,0,0,0.25)",
          maxWidth: isLandscape ? 1100 : 960,
          width: "100%",
          textAlign: "left",
        }}
      >
        <div
          style={{
            display: "inline-block",
            padding: "6px 18px",
            backgroundColor: CHALK.orange,
            color: CHALK.white,
            borderRadius: 8,
            fontSize: isLandscape ? 26 : 28,
            fontWeight: 700,
            marginBottom: 20,
            textTransform: "uppercase",
          }}
        >
          Bản Dịch Tiếng Việt
        </div>

        <div
          style={{
            color: CHALK.white,
            fontSize: isLandscape ? 38 : 36,
            lineHeight: 1.6,
            fontWeight: 600,
            marginBottom: 24,
          }}
        >
          <strong style={{ color: CHALK.yellow }}>Câu 24.</strong> Nếu một số nhân với 10, thì kết quả sẽ nhiều hơn số ban đầu 63 đơn vị.
        </div>

        <div
          style={{
            color: CHALK.yellow,
            fontSize: isLandscape ? 42 : 40,
            fontWeight: 700,
            marginBottom: 24,
          }}
        >
          Hỏi số ban đầu là số nào?
        </div>

        {/* 2 Key Clues */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: isLandscape ? "1fr 1fr" : "1fr",
            gap: 16,
            marginTop: 10,
          }}
        >
          <div
            style={{
              padding: "14px 18px",
              border: `2px dashed ${CHALK.white}`,
              borderRadius: 12,
              backgroundColor: "rgba(0,0,0,0.2)",
              color: CHALK.white,
              fontSize: isLandscape ? 26 : 28,
            }}
          >
            📌 Số mới = 10 lần số ban đầu
          </div>
          <div
            style={{
              padding: "14px 18px",
              border: `2px dashed ${CHALK.yellow}`,
              borderRadius: 12,
              backgroundColor: "rgba(0,0,0,0.2)",
              color: CHALK.yellow,
              fontSize: isLandscape ? 26 : 28,
            }}
          >
            📌 Số mới hơn số ban đầu: 63 đơn vị
          </div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 4: Strategy Card (Sơ đồ đoạn thẳng)
// ---------------------------------------------------------------------------
const SceneStrategyCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        padding: isLandscape ? "20px 40px" : "20px",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          border: `3px solid ${CHALK.borderChalk}`,
          borderRadius: 20,
          padding: isLandscape ? "32px 40px" : "28px 20px",
          backgroundColor: "rgba(0,0,0,0.25)",
          maxWidth: isLandscape ? 1150 : 960,
          width: "100%",
        }}
      >
        <div
          style={{
            color: CHALK.yellow,
            fontSize: isLandscape ? 34 : 34,
            fontWeight: 700,
            textAlign: "center",
            marginBottom: 20,
          }}
        >
          CHIẾN LƯỢC: SƠ ĐỒ ĐOẠN THẲNG
        </div>

        {/* Row 1: Original Number */}
        <div style={{ marginBottom: 26 }}>
          <div style={{ color: CHALK.white, fontSize: isLandscape ? 28 : 28, fontWeight: 700, marginBottom: 8 }}>
            Số ban đầu (1 phần):
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: isLandscape ? 90 : 70,
                height: isLandscape ? 44 : 40,
                border: `3px solid ${CHALK.white}`,
                borderRadius: 6,
                backgroundColor: "rgba(255,255,255,0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: CHALK.white,
                fontSize: 22,
                fontWeight: 700,
              }}
            >
              1 phần
            </div>
          </div>
        </div>

        {/* Row 2: New Number (x10) */}
        <div>
          <div style={{ color: CHALK.yellow, fontSize: isLandscape ? 28 : 28, fontWeight: 700, marginBottom: 8 }}>
            Số mới khi nhân với 10 (10 phần bằng nhau):
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: isLandscape ? 8 : 4,
              flexWrap: isLandscape ? "nowrap" : "wrap",
            }}
          >
            {Array.from({ length: 10 }).map((_, idx) => (
              <div
                key={idx}
                style={{
                  width: isLandscape ? 85 : 56,
                  height: isLandscape ? 44 : 40,
                  border: `2px solid ${idx === 0 ? CHALK.white : CHALK.yellow}`,
                  borderRadius: 6,
                  backgroundColor: idx === 0 ? "rgba(255,255,255,0.15)" : "rgba(255,215,0,0.2)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: idx === 0 ? CHALK.white : CHALK.yellow,
                  fontSize: isLandscape ? 20 : 18,
                  fontWeight: 700,
                  opacity: progress,
                }}
              >
                {idx + 1}
              </div>
            ))}
          </div>
        </div>

        {/* Observation note */}
        <div
          style={{
            marginTop: 26,
            padding: "14px 20px",
            border: `2px dashed ${CHALK.orange}`,
            borderRadius: 12,
            backgroundColor: "rgba(0,0,0,0.2)",
            color: CHALK.white,
            fontSize: isLandscape ? 26 : 26,
            lineHeight: 1.5,
          }}
        >
          💡 <strong>Nhận xét:</strong> Khi nhân với 10, số mới gấp 10 lần số ban đầu, tương ứng với 10 đoạn thẳng bằng nhau!
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 5: Solution Card (Các bước giải chi tiết)
// ---------------------------------------------------------------------------
const SceneSolutionCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const step = spring({ frame, fps, config: { damping: 14 } });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        padding: isLandscape ? "20px 40px" : "20px",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          border: `3px solid ${CHALK.yellow}`,
          borderRadius: 20,
          padding: isLandscape ? "32px 44px" : "28px 20px",
          backgroundColor: "rgba(0,0,0,0.28)",
          maxWidth: isLandscape ? 1150 : 960,
          width: "100%",
        }}
      >
        <div
          style={{
            color: CHALK.yellow,
            fontSize: isLandscape ? 36 : 34,
            fontWeight: 700,
            textAlign: "center",
            marginBottom: 20,
          }}
        >
          CÁC BƯỚC GIẢI CHI TIẾT
        </div>

        {/* Step 1 */}
        <div style={{ marginBottom: 18 }}>
          <div style={{ color: CHALK.mutedChalk, fontSize: isLandscape ? 24 : 24, fontWeight: 700 }}>
            Bước 1: Tìm hiệu số phần bằng nhau
          </div>
          <div
            style={{
              color: CHALK.white,
              fontSize: isLandscape ? 34 : 32,
              fontWeight: 700,
              marginTop: 4,
            }}
          >
            10 phần − 1 phần = <span style={{ color: CHALK.yellow }}>9 phần</span>
          </div>
        </div>

        {/* Step 2 */}
        <div style={{ marginBottom: 18 }}>
          <div style={{ color: CHALK.mutedChalk, fontSize: isLandscape ? 24 : 24, fontWeight: 700 }}>
            Bước 2: Mối liên hệ với giá trị tăng thêm
          </div>
          <div
            style={{
              color: CHALK.white,
              fontSize: isLandscape ? 32 : 30,
              fontWeight: 600,
              marginTop: 4,
            }}
          >
            9 phần bằng nhau này ứng với giá trị nhiều hơn là <span style={{ color: CHALK.yellow }}>63 đơn vị</span>.
          </div>
        </div>

        {/* Step 3 */}
        <div>
          <div style={{ color: CHALK.mutedChalk, fontSize: isLandscape ? 24 : 24, fontWeight: 700 }}>
            Bước 3: Tìm số ban đầu (giá trị 1 phần)
          </div>
          <div
            style={{
              display: "inline-block",
              padding: "10px 24px",
              backgroundColor: CHALK.boardAlt,
              border: `3px solid ${CHALK.yellow}`,
              borderRadius: 12,
              color: CHALK.yellow,
              fontSize: isLandscape ? 44 : 40,
              fontWeight: 700,
              marginTop: 8,
            }}
          >
            63 ÷ 9 = 7
          </div>
        </div>

        {/* Conclusion tag */}
        <div
          style={{
            marginTop: 20,
            color: CHALK.white,
            fontSize: isLandscape ? 28 : 26,
            fontWeight: 700,
            textAlign: "right",
          }}
        >
          👉 Số ban đầu cần tìm chính là <span style={{ color: CHALK.yellow, fontSize: 36 }}>7</span>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 6: Check Card (Kiểm tra lại)
// ---------------------------------------------------------------------------
const SceneCheckCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 15 } });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        padding: isLandscape ? "20px 40px" : "20px",
        boxSizing: "border-box",
        transform: `scale(${scale})`,
      }}
    >
      <div
        style={{
          border: `3px solid ${CHALK.borderChalk}`,
          borderRadius: 20,
          padding: isLandscape ? "36px 48px" : "32px 22px",
          backgroundColor: "rgba(0,0,0,0.25)",
          maxWidth: isLandscape ? 1100 : 960,
          width: "100%",
        }}
      >
        <div
          style={{
            color: CHALK.yellow,
            fontSize: isLandscape ? 36 : 34,
            fontWeight: 700,
            textAlign: "center",
            marginBottom: 24,
          }}
        >
          KIỂM TRA LẠI KẾT QUẢ
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              padding: "14px 20px",
              border: `2px dashed ${CHALK.white}`,
              borderRadius: 12,
              backgroundColor: "rgba(255,255,255,0.06)",
              fontSize: isLandscape ? 32 : 30,
              color: CHALK.white,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>Nhân số 7 với 10:</span>
            <span style={{ fontWeight: 700, color: CHALK.yellow }}>7 × 10 = 70</span>
          </div>

          <div
            style={{
              padding: "14px 20px",
              border: `2px dashed ${CHALK.white}`,
              borderRadius: 12,
              backgroundColor: "rgba(255,255,255,0.06)",
              fontSize: isLandscape ? 32 : 30,
              color: CHALK.white,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>So sánh với số ban đầu:</span>
            <span style={{ fontWeight: 700, color: CHALK.yellow }}>70 − 7 = 63</span>
          </div>

          <div
            style={{
              padding: "16px 20px",
              border: `3px solid ${CHALK.yellow}`,
              borderRadius: 12,
              backgroundColor: "rgba(255,215,0,0.15)",
              fontSize: isLandscape ? 34 : 32,
              color: CHALK.yellow,
              fontWeight: 700,
              textAlign: "center",
              marginTop: 10,
            }}
          >
            ✓ Đúng nhiều hơn 63 đơn vị! Kết quả hoàn toàn chính xác.
          </div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scene 7: Answer Card (Đáp án cuối cùng)
// ---------------------------------------------------------------------------
const SceneAnswerCard: React.FC<{ isLandscape: boolean }> = ({ isLandscape }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 12 } });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        padding: "20px",
        boxSizing: "border-box",
        transform: `scale(${scale})`,
      }}
    >
      <div
        style={{
          border: `5px solid ${CHALK.yellow}`,
          borderRadius: 24,
          padding: isLandscape ? "48px 80px" : "40px 36px",
          backgroundColor: CHALK.boardAlt,
          boxShadow: "0 0 50px rgba(0,0,0,0.5), inset 0 0 30px rgba(255,215,0,0.1)",
          textAlign: "center",
        }}
      >
        <div
          style={{
            color: CHALK.white,
            fontSize: isLandscape ? 36 : 38,
            fontWeight: 700,
            marginBottom: 16,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          Đáp Án Chính Xác
        </div>

        <div
          style={{
            color: CHALK.yellow,
            fontSize: isLandscape ? 120 : 100,
            fontWeight: 900,
            lineHeight: 1,
            margin: "12px 0 20px",
            textShadow: "0 0 20px rgba(255,215,0,0.6)",
          }}
        >
          7
        </div>

        <div
          style={{
            color: CHALK.white,
            fontSize: isLandscape ? 34 : 32,
            fontWeight: 600,
          }}
        >
          Số ban đầu cần tìm là <strong>7</strong>
        </div>
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
  const opacity = spring({ frame, fps, config: { damping: 16 } });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        padding: "20px",
        boxSizing: "border-box",
        opacity,
      }}
    >
      <div
        style={{
          border: `3px dashed ${CHALK.borderChalk}`,
          borderRadius: 20,
          padding: isLandscape ? "44px 60px" : "36px 30px",
          backgroundColor: "rgba(0,0,0,0.25)",
          textAlign: "center",
          maxWidth: isLandscape ? 900 : 800,
        }}
      >
        <div
          style={{
            fontSize: isLandscape ? 60 : 54,
            marginBottom: 12,
          }}
        >
          ⭐ 🎓 ⭐
        </div>
        <div
          style={{
            color: CHALK.yellow,
            fontSize: isLandscape ? 44 : 40,
            fontWeight: 700,
            marginBottom: 14,
          }}
        >
          Chúc Các Con Học Tốt!
        </div>
        <div
          style={{
            color: CHALK.white,
            fontSize: isLandscape ? 32 : 30,
            lineHeight: 1.5,
          }}
        >
          Tự tin và luôn hào hứng với những bài toán tư duy hay!
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Video Component with Sequences
// ---------------------------------------------------------------------------
export const MathMultipliedBy10Video: React.FC<{
  orientation: "portrait" | "landscape";
}> = ({ orientation }) => {
  const isLandscape = orientation === "landscape";

  return (
    <AbsoluteFill>
      <ChalkboardFrame isLandscape={isLandscape}>
        {/* Landscape Rail */}
        {isLandscape && <ChalkRailLandscape />}

        {/* Content Container */}
        <div
          style={{
            flex: 1,
            height: "100%",
            display: "flex",
            flexDirection: "column",
            position: "relative",
          }}
        >
          {/* Portrait Header */}
          {!isLandscape && <ChalkHeaderPortrait />}

          {/* Sequences */}
          <div
            style={{
              flex: 1,
              position: "relative",
              width: "100%",
              height: "100%",
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
        </div>

        {/* Master Narration Audio */}
        <Audio src={staticFile("master_narration.mp3")} />
      </ChalkboardFrame>
    </AbsoluteFill>
  );
};

export const MathMultipliedBy10Portrait: React.FC = () => (
  <MathMultipliedBy10Video orientation="portrait" />
);

export const MathMultipliedBy10Landscape: React.FC = () => (
  <MathMultipliedBy10Video orientation="landscape" />
);
