interface Props {
  appId: string;
  iframeKey?: number;
}

const PHONE_WIDTH = 280;
const IFRAME_WIDTH = 390; // real iPhone viewport width
const SCALE = PHONE_WIDTH / IFRAME_WIDTH;

export default function PhonePreview({ appId, iframeKey = 0 }: Props) {
  return (
    <div className="mx-auto" style={{ maxWidth: `${PHONE_WIDTH}px` }}>
      <div
        className="relative rounded-[2rem] border-[3px] border-white/10 bg-black overflow-hidden"
        style={{ aspectRatio: "9 / 19.5" }}
      >
        {/* Notch */}
        <div className="h-6 bg-black flex items-center justify-center">
          <div className="w-16 h-4 bg-conjure-card rounded-b-xl" />
        </div>

        {/* App iframe — rendered at real mobile size, scaled down to fit */}
        <div className="overflow-hidden" style={{ height: "calc(100% - 1.5rem)" }}>
          <iframe
            key={iframeKey}
            src={`/apps/${appId}/`}
            className="border-0"
            style={{
              width: `${IFRAME_WIDTH}px`,
              height: `${100 / SCALE}%`,
              transform: `scale(${SCALE})`,
              transformOrigin: "top left",
            }}
            title="App Preview"
            sandbox="allow-scripts allow-same-origin allow-forms"
            scrolling="no"
          />
        </div>
      </div>
    </div>
  );
}
