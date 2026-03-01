import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

interface Props {
  appName: string;
  visible: boolean;
  onClose: () => void;
}

function isIOS() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent);
}

export default function InstallPrompt({ appName, visible, onClose }: Props) {
  const ios = isIOS();

  return (
    <Dialog open={visible} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Install {appName}</DialogTitle>
          <DialogDescription>
            {ios ? "Works in Safari" : "Works in Chrome"} — the app will appear as an icon on your home screen.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {ios ? (
            <>
              <Step n={1} text="Tap the Share button (box with arrow)" />
              <Step n={2} text='Scroll down and tap "Add to Home Screen"' />
              <Step n={3} text='Tap "Add" in the top right' />
            </>
          ) : (
            <>
              <Step n={1} text="Tap the menu button (\u22EE) in your browser" />
              <Step n={2} text='"Add to Home Screen" or "Install app"' />
              <Step n={3} text='Tap "Install" to confirm' />
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Step({ n, text }: { n: number; text: string }) {
  return (
    <div
      className="flex items-center gap-3.5 animate-fade-in-up"
      style={{ animationDelay: `${n * 0.1}s` }}
    >
      <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-sm font-bold bg-foreground text-background">
        {n}
      </div>
      <p className="text-sm text-foreground leading-relaxed">{text}</p>
    </div>
  );
}
