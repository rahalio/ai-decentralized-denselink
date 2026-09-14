import { useQuery } from "@tanstack/react-query";
import { reportsService } from "@/services/domains/reports";
import { dataOf } from "@/lib/envelope";

export function BetaCohortPage() {
  const cohort = useQuery({
    queryKey: ["beta-cohort"],
    queryFn: () => reportsService.getBetaCohort(),
  });
  const data = dataOf<any>(cohort.data) ?? cohort.data ?? {};

  return (
    <div>
      <h1 className="page-title">Beta cohort</h1>
      <p className="page-sub">
        Private-beta (~80 projects) readiness without breaking shared mesh compatibility.
      </p>
      <div className="grid-stats">
        <div className="stat">
          <div className="label">Cohort size</div>
          <div className="value">{data.cohortSize ?? "—"}</div>
        </div>
        <div className="stat">
          <div className="label">Private-beta target</div>
          <div className="value">{data.privateBetaProjects ?? 80}</div>
        </div>
        <div className="stat">
          <div className="label">Ready for public beta</div>
          <div className={`value ${data.readyForPublicBeta ? "" : "warm"}`}>
            {data.readyForPublicBeta == null ? "—" : data.readyForPublicBeta ? "yes" : "not yet"}
          </div>
        </div>
        <div className="stat">
          <div className="label">Collisions</div>
          <div className={`value ${(data.collisionIncidents ?? 0) > 0 ? "flag" : ""}`}>
            {data.collisionIncidents ?? 0}
          </div>
        </div>
      </div>
    </div>
  );
}
