interface Props {
  appId: string;
  iframeKey?: number;
}

const PHONE_WIDTH = 300;
const IFRAME_WIDTH = 390;
const SCALE = PHONE_WIDTH / IFRAME_WIDTH;

export default function PhonePreview({ appId, iframeKey = 0 }: Props) {
  // iPhone 15 Pro: 393×852 logical points
  const IFRAME_HEIGHT = 844;
  const phoneHeight = Math.round(PHONE_WIDTH * (19.5 / 9));

  return (
    <div className="mx-auto w-full" style={{ maxWidth: `${PHONE_WIDTH}px` }}>
      <div
        className="relative rounded-[2.5rem] border border-border bg-white shadow-sm overflow-hidden"
        style={{ width: `${PHONE_WIDTH}px`, height: `${phoneHeight}px` }}
      >
        {/* Dynamic Island */}
        <div className="absolute top-2.5 left-1/2 -translate-x-1/2 w-[90px] h-[26px] bg-black rounded-full z-20" />

        {/* App iframe — full bleed, scaled down */}
        <iframe
          key={iframeKey}
          src={`/apps/${appId}/`}
          className="border-0 absolute top-0 left-0"
          style={{
            width: `${IFRAME_WIDTH}px`,
            height: `${IFRAME_HEIGHT}px`,
            transform: `scale(${SCALE})`,
            transformOrigin: "top left",
          }}
          title="App Preview"
          sandbox="allow-scripts allow-same-origin allow-forms"
          scrolling="no"
        />

        {/* Home indicator */}
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-[100px] h-1 bg-black/15 rounded-full z-20" />
      </div>
    </div>
  );
}
