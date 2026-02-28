import type { App } from "../types/app";

interface Props {
  app: App;
}

export default function AppCard({ app }: Props) {
  const initial = app.name.charAt(0).toUpperCase();

  return (
    <a
      href={`/apps/${app.id}/`}
      target="_blank"
      rel="noopener noreferrer"
      className="flex flex-col items-center gap-2 p-4 rounded-xl
                 bg-conjure-card border border-conjure-border
                 active:scale-95 transition-transform"
    >
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg"
        style={{ backgroundColor: app.theme_color }}
      >
        {initial}
      </div>
      <span className="text-sm text-center truncate w-full">{app.name}</span>
    </a>
  );
}
