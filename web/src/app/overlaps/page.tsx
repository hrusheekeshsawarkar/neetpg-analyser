import { OverlapsClient } from "@/components/OverlapsClient";
import { loadOverlaps } from "@/lib/data";

export default function OverlapsPage() {
  const rows = loadOverlaps();
  return <OverlapsClient rows={rows} />;
}
