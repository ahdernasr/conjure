/**
 * Phase 2: Install instructions modal.
 * Shows platform-specific instructions:
 * - iOS: "Tap Share -> Add to Home Screen"
 * - Android: "Tap ... -> Add to Home Screen" (or beforeinstallprompt if available)
 */

interface Props {
  appName: string;
  visible: boolean;
  onClose: () => void;
}

export default function InstallPrompt({ appName, visible, onClose }: Props) {
  if (!visible) return null;
  // Phase 2: render modal with platform-detected instructions
  void appName;
  void onClose;
  return null;
}
