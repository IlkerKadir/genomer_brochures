import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { IntroScene } from "./scenes/IntroScene";
import { ProductScene } from "./scenes/ProductScene";
import { OutroScene } from "./scenes/OutroScene";

export const GenomerVideo: React.FC = () => {
  const transitionDuration = 20;

  return (
    <TransitionSeries>
      {/* Intro Scene - 5 seconds */}
      <TransitionSeries.Sequence durationInFrames={150}>
        <IntroScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: transitionDuration })}
      />

      {/* FEMOBIOME II Line - 7 seconds */}
      <TransitionSeries.Sequence durationInFrames={210}>
        <ProductScene
          productName="FEMOBIOME II"
          productSubtitle="Women's Microbiota Assessment"
          description="Comprehensive molecular diagnostics for women's health with expanded panel of detectable microorganisms"
          color="#7B4B94"
          features={[
            "Quantitative assessment of normobiota state",
            "Group B Streptococcus detection",
            "STI pathogen screening",
            "HPV detection (Types 16, 18, 45+)",
          ]}
        />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: transitionDuration })}
      />

      {/* ANDROBIOME - 7 seconds */}
      <TransitionSeries.Sequence durationInFrames={210}>
        <ProductScene
          productName="ANDROBIOME"
          productSubtitle="Male Urogenital Microbiome"
          description="Comprehensive real-time PCR-based assay for male urogenital tract microbiota assessment"
          color="#0EA5E9"
          features={[
            "Unique test with no analogues worldwide",
            "Quantitative microbiota profiling",
            "STI pathogen detection",
            "Chronic disease diagnosis support",
          ]}
        />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: transitionDuration })}
      />

      {/* ENTEROBIOME Kids - 7 seconds */}
      <TransitionSeries.Sequence durationInFrames={210}>
        <ProductScene
          productName="ENTEROBIOME Kids"
          productSubtitle="Pediatric Gut Microbiome"
          description="Specialized diagnostic test for assessing children's intestinal microbiota health"
          color="#10B981"
          features={[
            "Age-appropriate reference ranges",
            "Gut dysbiosis detection",
            "Pathogen screening",
            "Probiotic guidance support",
          ]}
        />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: transitionDuration })}
      />

      {/* Outro Scene - 4 seconds */}
      <TransitionSeries.Sequence durationInFrames={120}>
        <OutroScene />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
