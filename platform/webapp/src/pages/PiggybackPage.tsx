import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { densityService } from "@/services/domains/density";
import { itemsOf } from "@/lib/envelope";

export function PiggybackPage() {
  const [region, setRegion] = useState("");
  const list = useQuery({
    queryKey: ["piggyback", region],
    queryFn: () => densityService.listPiggybackRegions(region ? { region } : undefined),
  });
  const items = itemsOf(list.data);

  return (
    <div>
      <h1 className="page-title">Piggyback discovery</h1>
      <p className="page-sub">
        See which licensed apps already contribute density so launches follow Doctor Easy → Flare logic.
      </p>
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <div className="field">
          <label htmlFor="region">Region filter</label>
          <input id="region" value={region} onChange={(e) => setRegion(e.target.value)} placeholder="e.g. Dhaka" />
        </div>
      </div>
      {items.length === 0 ? (
        <div className="panel">
          <p style={{ color: "var(--color-mute)" }}>
            Empty region = greenfield — model will show high penetration need.
          </p>
          <Link className="btn" to="/density">Open density model</Link>
        </div>
      ) : (
        <div className="card-grid">
          {items.map((r: any, i: number) => (
            <div key={i} className="panel PiggybackRegionCard" style={{ margin: 0 }}>
              <div className="brand" style={{ fontSize: "1rem" }}>{r.region}</div>
              <div style={{ margin: "0.5rem 0" }}>
                Readiness <strong>{r.launchReadinessScore ?? "—"}</strong>
                {r.greenfield ? <span className="badge warn" style={{ marginLeft: 8 }}>greenfield</span> : null}
              </div>
              <ul style={{ margin: 0, paddingLeft: "1.1rem", color: "var(--color-mute)", fontSize: "0.85rem" }}>
                {(r.contributorApps ?? []).map((a: any) => (
                  <li key={a.appId}>
                    {a.appId} · rank {a.densityRank} · nodes {a.activeNodes}
                    {a.alwaysOnCampaign ? " · always-on" : ""}
                  </li>
                ))}
              </ul>
              <div className="row" style={{ marginTop: "0.75rem" }}>
                <Link className="btn ghost" to="/venues">Venue kits</Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
