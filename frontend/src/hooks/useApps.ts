import { useState, useEffect, useCallback } from "react";
import { listApps } from "@/api/apps";
import type { App } from "@/types/app";

export function useApps() {
  const [apps, setApps] = useState<App[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listApps();
      setApps(data.apps);
    } catch (err) {
      console.error("Failed to load apps:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { apps, loading, refresh };
}
