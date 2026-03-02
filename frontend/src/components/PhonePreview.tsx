import { useRef, useState, useEffect } from "react";

interface Props {
  appId: string;
  iframeKey?: number;
  activeVersion?: number;
  latestVersion?: number;
}

const PHONE_WIDTH = 396; // 32% bigger than 300
const IFRAME_WIDTH = 390;
const SCALE = PHONE_WIDTH / IFRAME_WIDTH;

// Bezel insets (scaled to phone frame) — app starts below Dynamic Island, ends above home indicator
const TOP_INSET = 44;
const BOTTOM_INSET = 34;

export default function PhonePreview({ appId, iframeKey = 0, activeVersion, latestVersion }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [fitScale, setFitScale] = useState(1);

  const phoneHeight = Math.round(PHONE_WIDTH * (19.5 / 9));
  // iframe height = visible safe area (between insets) in unscaled pixels
  // so 100dvh inside the iframe matches what's actually shown
  const IFRAME_HEIGHT = Math.round((phoneHeight - TOP_INSET - BOTTOM_INSET) / SCALE);

  // Responsive scaling — shrink phone to fit available width + viewport height
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const update = () => {
      const { width } = el.getBoundingClientRect();
      const scaleX = Math.min(1, width / PHONE_WIDTH);

      // On desktop (md: 768px+), also scale down to fit viewport height
      // 160px = header (49) + panel padding (48) + version switcher (48) + breathing room (15)
      let scaleY = 1;
      if (window.innerWidth >= 768) {
        const availableHeight = window.innerHeight - 160;
        scaleY = Math.min(1, availableHeight / phoneHeight);
      }

      setFitScale(Math.min(scaleX, scaleY));
    };

    const observer = new ResizeObserver(update);
    observer.observe(el);
    // Also listen for window resize (viewport height changes don't resize the container)
    window.addEventListener("resize", update);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
    };
  }, [phoneHeight]);

  const src = activeVersion && latestVersion && activeVersion < latestVersion
    ? `/apps/${appId}/_versions/${activeVersion}/`
    : `/apps/${appId}/`;

  return (
    <div ref={containerRef} className="w-full">
      {/* Size wrapper — collapses to scaled dimensions for correct layout flow */}
      <div className="mx-auto overflow-hidden" style={{ width: PHONE_WIDTH * fitScale, height: phoneHeight * fitScale }}>
        <div
          className="relative rounded-[2.5rem] border border-border bg-white shadow-sm"
          style={{
            width: PHONE_WIDTH,
            height: phoneHeight,
            transform: `scale(${fitScale})`,
            transformOrigin: "top left",
          }}
        >
          {/* Dynamic Island */}
          <div className="absolute top-2.5 left-1/2 -translate-x-1/2 w-[108px] h-[32px] bg-black rounded-full z-20" />

          {/* App iframe — clipped to safe area */}
          <div
            className="absolute left-0 right-0 overflow-hidden"
            style={{ top: `${TOP_INSET}px`, bottom: `${BOTTOM_INSET}px`, borderRadius: "0 0 2.5rem 2.5rem" }}
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
              scrolling="no"
            />
          </div>

          {/* Home indicator */}
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 w-[120px] h-1 bg-black/15 rounded-full z-20" />
        </div>
      </div>
    </div>
  );
}
