interface Props {
  appId: string;
  iframeKey?: number;
}

const PHONE_WIDTH = 300;
const IFRAME_WIDTH = 390;
const SCALE = PHONE_WIDTH / IFRAME_WIDTH;

// Simulate real iPhone bezels — app content starts below status bar, ends above home indicator
const TOP_BEZEL = 44; // status bar + dynamic island safe area
const BOTTOM_BEZEL = 28; // home indicator area

export default function PhonePreview({ appId, iframeKey = 0 }: Props) {
  return (
    <div className="mx-auto" style={{ maxWidth: `${PHONE_WIDTH}px` }}>
      <div
        className="relative rounded-[2.5rem] border border-border bg-white shadow-sm"
        style={{ aspectRatio: "9 / 19.5" }}
      >
        {/* Dynamic Island */}
        <div className="absolute top-2.5 left-1/2 -translate-x-1/2 w-[90px] h-[26px] bg-black rounded-full z-20" />

        {/* App iframe — inset to reflect real safe area */}
        <div
          className="absolute left-0 right-0 overflow-hidden"
          style={{
            top: `${TOP_BEZEL}px`,
            bottom: `${BOTTOM_BEZEL}px`,
          }}
        >
          <iframe
            key={iframeKey}
            src={`/apps/${appId}/`}
            className="border-0"
            style={{
              width: `${IFRAME_WIDTH}px`,
              height: `${Math.round(100 / SCALE)}%`,
              transform: `scale(${SCALE})`,
              transformOrigin: "top left",
            }}
            title="App Preview"
            sandbox="allow-scripts allow-same-origin allow-forms"
            scrolling="no"
          />
        </div>

        {/* Home indicator */}
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-[100px] h-1 bg-black/15 rounded-full z-20" />
      </div>
    </div>
  );
}
