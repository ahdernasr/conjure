import type { App } from "../types/app";
import AppCard from "./AppCard";

interface Props {
  apps: App[];
  loading: boolean;
  onSelectApp: (appId: string) => void;
}

export default function AppGallery({ apps, loading, onSelectApp }: Props) {
  if (loading) {
    return (
      <div className="text-center text-conjure-muted py-8">Loading apps...</div>
    );
  }

  if (apps.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-conjure-muted text-sm">No apps yet.</p>
        <p className="text-conjure-muted text-xs mt-1">
          Type a prompt below to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {apps.map((app) => (
        <AppCard key={app.id} app={app} onSelect={onSelectApp} />
      ))}
    </div>
  );
}
