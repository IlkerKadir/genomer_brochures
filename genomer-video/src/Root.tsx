import { Composition } from "remotion";
import { GenomerVideo } from "./GenomerVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="GenomerVideo"
      component={GenomerVideo}
      durationInFrames={900}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
