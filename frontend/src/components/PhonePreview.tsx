import { useRef, useState, useEffect } from "react";

interface Props {
  appId: string;
  iframeKey?: number;
  activeVersion?: number;
  latestVersion?: number;
}

const PHONE_WIDTH = 396;
const IFRAME_WIDTH = 390;
const SCALE = PHONE_WIDTH / IFRAME_WIDTH;

export default function PhonePreview({ appId, iframeKey = 0, activeVersion, latestVersion }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [fitScale, setFitScale] = useState(1);

  const phoneHeight = Math.round(PHONE_WIDTH * (19.5 / 9));
  const IFRAME_HEIGHT = Math.round(phoneHeight / SCALE);

  // Responsive scaling — shrink phone to fit available width + viewport height
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const update = () => {
      const { width } = el.getBoundingClientRect();
      const scaleX = Math.min(1, width / PHONE_WIDTH);

      let scaleY = 1;
      if (window.innerWidth >= 768) {
        const availableHeight = window.innerHeight - 160;
        scaleY = Math.min(1, availableHeight / phoneHeight);
      }

      setFitScale(Math.min(scaleX, scaleY));
    };

    const observer = new ResizeObserver(update);
    observer.observe(el);
    window.addEventListener("resize", update);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
    };
  }, [phoneHeight]);

  const baseSrc = activeVersion && latestVersion && activeVersion < latestVersion
    ? `/apps/${appId}/_versions/${activeVersion}/`
    : `/apps/${appId}/`;
  const src = `${baseSrc}?v=${iframeKey}`;

  return (
    <div ref={containerRef} className="w-full">
      <div className="mx-auto overflow-hidden" style={{ width: PHONE_WIDTH * fitScale, height: phoneHeight * fitScale }}>
        <div
          className="relative rounded-[1.5rem] border border-border overflow-hidden"
          style={{
            width: PHONE_WIDTH,
            height: phoneHeight,
            transform: `scale(${fitScale})`,
            transformOrigin: "top left",
          }}
        >
          <iframe
            key={iframeKey}
            src={src}
            className="border-0 absolute top-0 left-0"
            style={{
              width: `${IFRAME_WIDTH}px`,
              height: `${IFRAME_HEIGHT}px`,
              transform: `scale(${SCALE})`,
              transformOrigin: "top left",
            }}
            title="App Preview"
            sandbox="allow-scripts allow-same-origin allow-forms"
            scrolling="yes"
          />
        </div>
      </div>
    </div>
  );
}
