import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { reportsService } from "@/services/domains/reports";
import { dataOf } from "@/lib/envelope";

export function SponsorRoiPage() {
  const [venueProgrammeId, setVenueProgrammeId] = useState("ven_01HZYXK8J0M0W5N6P7Q8R9S0T123");
  const [enabled, setEnabled] = useState(false);
  const report = useQuery({
    queryKey: ["sponsor-roi", venueProgrammeId],
    queryFn: () => reportsService.getSponsorRoiReport(venueProgrammeId),
    enabled,
  });
  const data = dataOf<any>(report.data) ?? report.data;

  return (
    <div>
      <h1 className="page-title">Sponsor ROI report</h1>
      <p className="page-sub">
        Venue event coverage pack for sponsors. Affordability narrative is contextual — not an SLA.
      </p>
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <div className="field">
          <label htmlFor="vid">Venue programme ID</label>
          <input id="vid" value={venueProgrammeId} onChange={(e) => setVenueProgrammeId(e.target.value)} />
        </div>
        <button className="btn" type="button" onClick={() => setEnabled(true)}>Load ROI pack</button>
      </div>
      {data ? (
        <div className="panel">
          <div className="grid-stats">
            <div className="stat">
              <div className="label">Active nodes</div>
              <div className="value">{data.activeNodes ?? "—"}</div>
            </div>
            <div className="stat">
              <div className="label">Sessions</div>
              <div className="value">{data.sessions ?? "—"}</div>
            </div>
            <div className="stat">
              <div className="label">Avg session min</div>
              <div className="value">{data.avgSessionMinutes ?? "—"}</div>
            </div>
          </div>
          {data.affordabilityBenchmarkNote ? (
            <p style={{ color: "var(--color-concrete)", fontSize: "0.85rem" }}>
              {data.affordabilityBenchmarkNote}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
