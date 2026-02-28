interface Props {
  appId: string;
  iframeKey?: number;
}

export default function PhonePreview({ appId, iframeKey = 0 }: Props) {
  return (
    <div className="mx-auto" style={{ maxWidth: "280px" }}>
      <div
        className="relative rounded-[2rem] border-[3px] border-white/10 bg-black overflow-hidden"
        style={{ aspectRatio: "9 / 19.5" }}
      >
        {/* Notch */}
        <div className="h-6 bg-black flex items-center justify-center">
          <div className="w-16 h-4 bg-conjure-card rounded-b-xl" />
        </div>

        {/* App iframe */}
        <iframe
          key={iframeKey}
          src={`/apps/${appId}/`}
          className="w-full border-0"
          style={{ height: "calc(100% - 1.5rem)" }}
          title="App Preview"
          sandbox="allow-scripts allow-same-origin allow-forms"
        />
      </div>
    </div>
  );
}
