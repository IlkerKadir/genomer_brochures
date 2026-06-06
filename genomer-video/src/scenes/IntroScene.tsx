import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
  Img,
  staticFile,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Figtree";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "600", "700"],
  subsets: ["latin"],
});

export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Logo animation
  const logoScale = spring({
    frame,
    fps,
    config: { damping: 200 },
  });

  const logoOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Tagline animation
  const taglineProgress = spring({
    frame: frame - 30,
    fps,
    config: { damping: 200 },
  });

  const taglineOpacity = interpolate(frame, [30, 45], [0, 1], {
    extrapolateRight: "clamp",
  });

  const taglineY = interpolate(taglineProgress, [0, 1], [30, 0]);

  // DNA Helix animation
  const helixRotation = interpolate(frame, [0, 150], [0, 360]);

  // Subtitle animation
  const subtitleProgress = spring({
    frame: frame - 60,
    fps,
    config: { damping: 200 },
  });

  const subtitleOpacity = interpolate(frame, [60, 75], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        flex: 1,
        background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        fontFamily,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Animated DNA Helix Background */}
      <div
        style={{
          position: "absolute",
          width: "100%",
          height: "100%",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          opacity: 0.15,
        }}
      >
        <svg
          width="800"
          height="800"
          viewBox="0 0 200 200"
          style={{
            transform: `rotate(${helixRotation}deg)`,
          }}
        >
          <defs>
            <linearGradient id="helixGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#7B4B94" />
              <stop offset="50%" stopColor="#0EA5E9" />
              <stop offset="100%" stopColor="#10B981" />
            </linearGradient>
          </defs>
          <path
            d="M 40 0 Q 120 25, 40 50 Q -40 75, 40 100 Q 120 125, 40 150 Q -40 175, 40 200"
            stroke="url(#helixGrad1)"
            strokeWidth="3"
            fill="none"
          />
          <path
            d="M 160 0 Q 80 25, 160 50 Q 240 75, 160 100 Q 80 125, 160 150 Q 240 175, 160 200"
            stroke="url(#helixGrad1)"
            strokeWidth="3"
            fill="none"
          />
          {[25, 50, 75, 100, 125, 150, 175].map((y, i) => (
            <line
              key={i}
              x1={40 + Math.sin((y / 50) * Math.PI) * 40}
              y1={y}
              x2={160 - Math.sin((y / 50) * Math.PI) * 40}
              y2={y}
              stroke="url(#helixGrad1)"
              strokeWidth="2"
              opacity={0.6}
            />
          ))}
        </svg>
      </div>

      {/* Floating particles */}
      {[...Array(20)].map((_, i) => {
        const x = (i * 97) % 100;
        const y = (i * 73 + frame * (0.5 + (i % 3) * 0.3)) % 120 - 10;
        const size = 3 + (i % 4);
        const opacity = 0.2 + (i % 5) * 0.1;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${x}%`,
              top: `${y}%`,
              width: size,
              height: size,
              borderRadius: "50%",
              background: i % 3 === 0 ? "#7B4B94" : i % 3 === 1 ? "#0EA5E9" : "#10B981",
              opacity,
            }}
          />
        );
      })}

      {/* Logo */}
      <div
        style={{
          transform: `scale(${logoScale})`,
          opacity: logoOpacity,
          marginBottom: 40,
        }}
      >
        <Img
          src={staticFile("genomerlogo.png")}
          style={{
            height: 120,
            width: "auto",
          }}
        />
      </div>

      {/* Tagline */}
      <div
        style={{
          opacity: taglineOpacity,
          transform: `translateY(${taglineY}px)`,
          fontSize: 42,
          fontWeight: 600,
          color: "white",
          textAlign: "center",
          marginBottom: 20,
        }}
      >
        Advanced Molecular Diagnostics
      </div>

      {/* Subtitle */}
      <div
        style={{
          opacity: subtitleOpacity,
          transform: `scale(${subtitleProgress})`,
          fontSize: 28,
          fontWeight: 400,
          color: "rgba(255, 255, 255, 0.8)",
          textAlign: "center",
          maxWidth: 800,
        }}
      >
        Comprehensive Microbiome Testing Solutions
      </div>

      {/* Product badges */}
      <div
        style={{
          display: "flex",
          gap: 30,
          marginTop: 60,
          opacity: interpolate(frame, [90, 105], [0, 1], {
            extrapolateRight: "clamp",
          }),
        }}
      >
        {[
          { name: "FEMOBIOME", color: "#7B4B94" },
          { name: "ANDROBIOME", color: "#0EA5E9" },
          { name: "ENTEROBIOME", color: "#10B981" },
        ].map((product, i) => {
          const badgeProgress = spring({
            frame: frame - 90 - i * 10,
            fps,
            config: { damping: 15, stiffness: 200 },
          });

          return (
            <div
              key={product.name}
              style={{
                transform: `scale(${badgeProgress})`,
                padding: "12px 24px",
                borderRadius: 30,
                background: product.color,
                color: "white",
                fontSize: 18,
                fontWeight: 600,
                boxShadow: `0 4px 20px ${product.color}66`,
              }}
            >
              {product.name}
            </div>
          );
        })}
      </div>
    </div>
  );
};
