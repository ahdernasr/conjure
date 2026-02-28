interface Props {
  appName: string;
  visible: boolean;
  onClose: () => void;
}

function isIOS() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent);
}

export default function InstallPrompt({ appName, visible, onClose }: Props) {
  if (!visible) return null;

  const ios = isIOS();

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60"
         onClick={onClose}>
      <div className="w-full max-w-lg bg-conjure-card border-t border-conjure-border
                      rounded-t-2xl p-6 space-y-4"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Install {appName}</h3>
          <button onClick={onClose} className="text-conjure-muted text-xl leading-none">
            &times;
          </button>
        </div>

        <div className="space-y-3">
          {ios ? (
            <>
              <Step n={1} text={'Tap the Share button (box with arrow)'} />
              <Step n={2} text={'Scroll down and tap "Add to Home Screen"'} />
              <Step n={3} text={'Tap "Add" in the top right'} />
            </>
          ) : (
            <>
              <Step n={1} text={'Tap the menu button (⋮) in your browser'} />
              <Step n={2} text={'"Add to Home Screen" or "Install app"'} />
              <Step n={3} text={'Tap "Install" to confirm'} />
            </>
          )}
        </div>

        <p className="text-xs text-conjure-muted">
          {ios ? "Works in Safari" : "Works in Chrome"} — the app will appear as an icon on your home screen.
        </p>
      </div>
    </div>
  );
}

function Step({ n, text }: { n: number; text: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-7 h-7 rounded-full bg-conjure-accent flex items-center justify-center
                      text-white text-sm font-bold flex-shrink-0">
        {n}
      </div>
      <p className="text-sm text-conjure-text">{text}</p>
    </div>
  );
}
