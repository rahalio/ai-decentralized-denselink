import { useQuery } from "@tanstack/react-query";
import { reportsService } from "@/services/domains/reports";
import { itemsOf } from "@/lib/envelope";

export function ContributionPage() {
  const rank = useQuery({
    queryKey: ["contribution-rank"],
    queryFn: () => reportsService.getContributionRank(),
  });
  const items = itemsOf(rank.data);

  return (
    <div>
      <h1 className="page-title">Contribution rank</h1>
      <p className="page-sub">
        Rank projects by density contribution for DevRel and public-beta timing.
      </p>
      <div className="panel">
        <table className="table ContributionRankTable">
          <thead>
            <tr>
              <th>Rank</th>
              <th>App</th>
              <th>MeshPort</th>
              <th>SDK</th>
              <th>Score</th>
              <th>Nodes</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr><td colSpan={6} style={{ color: "var(--color-mute)" }}>No contribution data yet.</td></tr>
            ) : items.map((r: any) => (
              <tr key={r.appId}>
                <td>{r.rank}</td>
                <td className="mono">{r.appId}</td>
                <td>{r.meshPort ?? "—"}</td>
                <td>{r.sdkVersion ?? "—"}</td>
                <td>{r.densityContributionScore}</td>
                <td>{r.activeNodes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
