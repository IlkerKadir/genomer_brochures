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

type ProductSceneProps = {
  productName: string;
  productSubtitle: string;
  description: string;
  color: string;
  features: string[];
};

export const ProductScene: React.FC<ProductSceneProps> = ({
  productName,
  productSubtitle,
  description,
  color,
  features,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Background gradient animation
  const gradientPosition = interpolate(frame, [0, 210], [0, 100]);

  // Title animation
  const titleProgress = spring({
    frame,
    fps,
    config: { damping: 200 },
  });

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Subtitle animation
  const subtitleProgress = spring({
    frame: frame - 15,
    fps,
    config: { damping: 200 },
  });

  const subtitleOpacity = interpolate(frame, [15, 35], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Description animation
  const descOpacity = interpolate(frame, [30, 50], [0, 1], {
    extrapolateRight: "clamp",
  });

  const descY = interpolate(
    spring({ frame: frame - 30, fps, config: { damping: 200 } }),
    [0, 1],
    [20, 0]
  );

  // DNA Helix decoration
  const helixY = interpolate(frame, [0, 210], [0, -50]);

  // Create lighter version of color for gradient
  const lighterColor = color + "40";
  const darkerColor = color + "80";

  return (
    <div
      style={{
        flex: 1,
        background: `linear-gradient(${135 + gradientPosition}deg, #0f172a 0%, ${lighterColor} 50%, #0f172a 100%)`,
        display: "flex",
        fontFamily,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Decorative DNA helix on the right */}
      <div
        style={{
          position: "absolute",
          right: 50,
          top: 0,
          height: "100%",
          width: 200,
          opacity: 0.2,
          transform: `translateY(${helixY}px)`,
        }}
      >
        <svg width="200" height="1200" viewBox="0 0 200 1200">
          <defs>
            <linearGradient id={`helix-${productName}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={color} stopOpacity="0" />
              <stop offset="50%" stopColor={color} />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path
            d="M 40 0 Q 120 50, 40 100 Q -40 150, 40 200 Q 120 250, 40 300 Q -40 350, 40 400 Q 120 450, 40 500 Q -40 550, 40 600 Q 120 650, 40 700 Q -40 750, 40 800 Q 120 850, 40 900 Q -40 950, 40 1000 Q 120 1050, 40 1100 Q -40 1150, 40 1200"
            stroke={`url(#helix-${productName})`}
            strokeWidth="4"
            fill="none"
          />
          <path
            d="M 160 0 Q 80 50, 160 100 Q 240 150, 160 200 Q 80 250, 160 300 Q 240 350, 160 400 Q 80 450, 160 500 Q 240 550, 160 600 Q 80 650, 160 700 Q 240 750, 160 800 Q 80 850, 160 900 Q 240 950, 160 1000 Q 80 1050, 160 1100 Q 240 1150, 160 1200"
            stroke={`url(#helix-${productName})`}
            strokeWidth="4"
            fill="none"
          />
        </svg>
      </div>

      {/* Floating molecules */}
      {[...Array(15)].map((_, i) => {
        const x = 70 + (i * 17) % 25;
        const y = (i * 47 + frame * (0.3 + (i % 4) * 0.2)) % 120 - 10;
        const size = 4 + (i % 5);
        const opacity = 0.15 + (i % 4) * 0.1;
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
              background: color,
              opacity,
            }}
          />
        );
      })}

      {/* Content container */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "60px 100px",
          maxWidth: "70%",
        }}
      >
        {/* Logo */}
        <div
          style={{
            marginBottom: 40,
            opacity: titleOpacity,
          }}
        >
          <Img
            src={staticFile("genomerlogo.png")}
            style={{
              height: 50,
              width: "auto",
            }}
          />
        </div>

        {/* Product Name */}
        <div
          style={{
            opacity: titleOpacity,
            transform: `translateX(${interpolate(titleProgress, [0, 1], [-50, 0])}px)`,
          }}
        >
          <span
            style={{
              fontSize: 72,
              fontWeight: 700,
              color: "white",
              display: "inline-block",
            }}
          >
            {productName}
          </span>
          <sup
            style={{
              fontSize: 24,
              color: "white",
              verticalAlign: "super",
            }}
          >
            {productName === "FEMOBIOME II" ? "" : "\u00AE"}
          </sup>
        </div>

        {/* Subtitle */}
        <div
          style={{
            opacity: subtitleOpacity,
            transform: `translateX(${interpolate(subtitleProgress, [0, 1], [-30, 0])}px)`,
            fontSize: 32,
            fontWeight: 500,
            color,
            marginBottom: 20,
            marginTop: 10,
          }}
        >
          {productSubtitle}
        </div>

        {/* Description */}
        <div
          style={{
            opacity: descOpacity,
            transform: `translateY(${descY}px)`,
            fontSize: 22,
            fontWeight: 400,
            color: "rgba(255, 255, 255, 0.85)",
            lineHeight: 1.6,
            marginBottom: 40,
            maxWidth: 700,
          }}
        >
          {description}
        </div>

        {/* Features */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          {features.map((feature, i) => {
            const featureProgress = spring({
              frame: frame - 50 - i * 12,
              fps,
              config: { damping: 200 },
            });

            const featureOpacity = interpolate(
              frame,
              [50 + i * 12, 65 + i * 12],
              [0, 1],
              { extrapolateRight: "clamp" }
            );

            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  opacity: featureOpacity,
                  transform: `translateX(${interpolate(featureProgress, [0, 1], [-30, 0])}px)`,
                }}
              >
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    background: color,
                    boxShadow: `0 0 10px ${color}`,
                  }}
                />
                <span
                  style={{
                    fontSize: 20,
                    fontWeight: 500,
                    color: "rgba(255, 255, 255, 0.9)",
                  }}
                >
                  {feature}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Color accent bar */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: 8,
          background: `linear-gradient(180deg, transparent, ${color}, transparent)`,
        }}
      />

      {/* Bottom gradient line */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: 4,
          background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
        }}
      />
    </div>
  );
};
