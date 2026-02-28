/**
 * Phase 2: iframe preview of generated app.
 * Will show the generated app in a phone-frame mockup
 * before the user installs it to homescreen.
 */

interface Props {
  appId: string | null;
}

export default function AppPreview({ appId }: Props) {
  if (!appId) return null;
  // Phase 2: render <iframe src={`/apps/${appId}/`} />
  return null;
}
