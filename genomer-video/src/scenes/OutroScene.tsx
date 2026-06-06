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
  weights: ["400", "500", "600", "700"],
  subsets: ["latin"],
});

export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Logo animation
  const logoProgress = spring({
    frame,
    fps,
    config: { damping: 200 },
  });

  const logoOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Tagline animation
  const taglineProgress = spring({
    frame: frame - 20,
    fps,
    config: { damping: 200 },
  });

  const taglineOpacity = interpolate(frame, [20, 40], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Website animation
  const websiteOpacity = interpolate(frame, [40, 60], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Product badges animation
  const badgesOpacity = interpolate(frame, [50, 70], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        flex: 1,
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        fontFamily,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Animated gradient orbs */}
      <div
        style={{
          position: "absolute",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: "radial-gradient(circle, #7B4B9420 0%, transparent 70%)",
          top: -200,
          left: -100,
          filter: "blur(40px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 400,
          height: 400,
          borderRadius: "50%",
          background: "radial-gradient(circle, #0EA5E920 0%, transparent 70%)",
          bottom: -150,
          right: -100,
          filter: "blur(40px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 300,
          height: 300,
          borderRadius: "50%",
          background: "radial-gradient(circle, #10B98120 0%, transparent 70%)",
          top: "50%",
          right: "30%",
          filter: "blur(40px)",
        }}
      />

      {/* Logo */}
      <div
        style={{
          opacity: logoOpacity,
          transform: `scale(${logoProgress})`,
          marginBottom: 30,
        }}
      >
        <Img
          src={staticFile("genomerlogo.png")}
          style={{
            height: 100,
            width: "auto",
          }}
        />
      </div>

      {/* Tagline */}
      <div
        style={{
          opacity: taglineOpacity,
          transform: `translateY(${interpolate(taglineProgress, [0, 1], [20, 0])}px)`,
          fontSize: 36,
          fontWeight: 600,
          color: "white",
          textAlign: "center",
          marginBottom: 30,
        }}
      >
        Precision Diagnostics for Better Health
      </div>

      {/* Product line badges */}
      <div
        style={{
          display: "flex",
          gap: 20,
          marginBottom: 40,
          opacity: badgesOpacity,
        }}
      >
        {[
          { name: "FEMOBIOME", color: "#7B4B94" },
          { name: "ANDROBIOME", color: "#0EA5E9" },
          { name: "ENTEROBIOME", color: "#10B981" },
        ].map((product, i) => {
          const badgeProgress = spring({
            frame: frame - 50 - i * 8,
            fps,
            config: { damping: 15, stiffness: 200 },
          });

          return (
            <div
              key={product.name}
              style={{
                transform: `scale(${badgeProgress})`,
                padding: "10px 20px",
                borderRadius: 25,
                background: `${product.color}30`,
                border: `2px solid ${product.color}`,
                color: product.color,
                fontSize: 16,
                fontWeight: 600,
              }}
            >
              {product.name}
            </div>
          );
        })}
      </div>

      {/* Website */}
      <div
        style={{
          opacity: websiteOpacity,
          fontSize: 24,
          fontWeight: 500,
          color: "rgba(255, 255, 255, 0.8)",
          marginBottom: 20,
        }}
      >
        www.genomer.com.tr
      </div>

      {/* Bottom text */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          opacity: interpolate(frame, [60, 80], [0, 1], {
            extrapolateRight: "clamp",
          }),
          fontSize: 16,
          fontWeight: 400,
          color: "rgba(255, 255, 255, 0.5)",
        }}
      >
        Biyoteknoloji Arge San. ve Tic. Ltd. Sti.
      </div>

      {/* Decorative line */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 4,
          background: "linear-gradient(90deg, #7B4B94, #0EA5E9, #10B981)",
          opacity: interpolate(frame, [70, 90], [0, 1], {
            extrapolateRight: "clamp",
          }),
        }}
      />
    </div>
  );
};
