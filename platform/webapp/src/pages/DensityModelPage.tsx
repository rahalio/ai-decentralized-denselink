import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { densityService } from "@/services/domains/density";
import { itemsOf, dataOf } from "@/lib/envelope";

const PRESETS: Record<string, { city: string; populationPerSqKm: number; targetPenetrationPercent: number }> = {
  dhaka: { city: "Dhaka", populationPerSqKm: 23000, targetPenetrationPercent: 5 },
  san_francisco: { city: "San Francisco", populationPerSqKm: 7200, targetPenetrationPercent: 90.82 },
};

export function DensityModelPage() {
  const qc = useQueryClient();
  const [preset, setPreset] = useState("custom");
  const [city, setCity] = useState("Dhaka");
  const [pop, setPop] = useState("23000");
  const [target, setTarget] = useState("5");
  const [range, setRange] = useState("90");
  const [last, setLast] = useState<any>(null);

  const list = useQuery({ queryKey: ["density-models"], queryFn: () => densityService.listDensityModels() });
  const run = useMutation({
    mutationFn: () =>
      densityService.runDensityModel({
        city,
        populationPerSqKm: Number(pop),
        targetPenetrationPercent: Number(target),
        nodeRangeMeters: Number(range),
        benchmarkPreset: preset,
      }),
    onSuccess: (res) => {
      setLast(dataOf(res) ?? res);
      qc.invalidateQueries({ queryKey: ["density-models"] });
    },
  });

  const items = itemsOf(list.data);

  function applyPreset(key: string) {
    setPreset(key);
    const p = PRESETS[key];
    if (p) {
      setCity(p.city);
      setPop(String(p.populationPerSqKm));
      setTarget(String(p.targetPenetrationPercent));
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    run.mutate();
  }

  return (
    <div>
      <h1 className="page-title">Density model calculator</h1>
      <p className="page-sub">
        Accept city/venue parameters and output penetration targets (Dhaka ~5% vs SF ~90%).
      </p>
      <div className="panel DensityModelPanel" style={{ marginBottom: "1rem" }}>
        <div className="row" style={{ marginBottom: "0.75rem" }}>
          <button type="button" className="btn ghost" onClick={() => applyPreset("dhaka")}>Dhaka preset</button>
          <button type="button" className="btn ghost" onClick={() => applyPreset("san_francisco")}>San Francisco preset</button>
        </div>
        <form onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="city">City</label>
            <input id="city" value={city} onChange={(e) => setCity(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="pop">Population / km²</label>
            <input id="pop" value={pop} onChange={(e) => setPop(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="target">Target penetration %</label>
            <input id="target" value={target} onChange={(e) => setTarget(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="range">Node range (80–100m)</label>
            <input id="range" value={range} onChange={(e) => setRange(e.target.value)} />
          </div>
          <button className="btn" type="submit" disabled={run.isPending}>
            {run.isPending ? "Running…" : "Run / save model"}
          </button>
        </form>
      </div>
      {last ? (
        <div className="panel" style={{ marginBottom: "1rem" }}>
          {last.gapBelowThreshold ? (
            <div className="gap-banner">Coverage gap: plan is below useful blanket threshold.</div>
          ) : null}
          <div className="grid-stats">
            <div className="stat">
              <div className="label">Required penetration</div>
              <div className="value">{last.requiredPenetrationPercent ?? "—"}%</div>
            </div>
            <div className="stat">
              <div className="label">Useful coverage</div>
              <div className={`value ${last.estimatedUsefulCoverage ? "" : "flag"}`}>
                {last.estimatedUsefulCoverage ? "yes" : "no"}
              </div>
            </div>
            <div className="stat">
              <div className="label">Est. nodes</div>
              <div className="value">{last.estimatedNodes ?? "—"}</div>
            </div>
          </div>
          {last.benchmarkNote ? <p style={{ color: "var(--color-mute)" }}>{last.benchmarkNote}</p> : null}
        </div>
      ) : null}
      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Saved scenarios</h3>
        <table className="table">
          <thead>
            <tr><th>City</th><th>Penetration</th><th>Useful</th><th>Gap</th></tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr><td colSpan={4} style={{ color: "var(--color-mute)" }}>No saved models yet.</td></tr>
            ) : items.map((m: any) => (
              <tr key={m.id}>
                <td>{m.city}</td>
                <td>{m.requiredPenetrationPercent}%</td>
                <td>{m.estimatedUsefulCoverage ? "yes" : "no"}</td>
                <td>{m.gapBelowThreshold ? <span className="badge warn">gap</span> : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
