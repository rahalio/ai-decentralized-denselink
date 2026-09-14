import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { meshportsService } from "@/services/domains/meshports";
import { licensesService } from "@/services/domains/licenses";
import { densityService } from "@/services/domains/density";
import { itemsOf } from "@/lib/envelope";

export function DeveloperHomePage() {
  const ports = useQuery({ queryKey: ["meshports"], queryFn: () => meshportsService.listMeshPorts() });
  const licenses = useQuery({ queryKey: ["licenses"], queryFn: () => licensesService.listLicenseKeys() });
  const piggy = useQuery({ queryKey: ["piggyback"], queryFn: () => densityService.listPiggybackRegions() });

  const portItems = itemsOf(ports.data);
  const licItems = itemsOf(licenses.data);
  const regions = itemsOf(piggy.data);
  const activePort = portItems.find((p: any) => p.status === "allocated");
  const activeLic = licItems.find((l: any) => l.status === "active");

  return (
    <div>
      <h1 className="page-title">Developer home</h1>
      <p className="page-sub">
        Do you have a valid MeshPort + license, and where can you piggyback useful density today?
      </p>
      <div className="grid-stats">
        <div className="stat">
          <div className="label">MeshPort</div>
          <div className={`value ${activePort ? "" : "flag"}`}>
            {activePort ? activePort.port : "—"}
          </div>
        </div>
        <div className="stat">
          <div className="label">License</div>
          <div className={`value ${activeLic ? "" : "flag"}`}>
            {activeLic ? activeLic.tier ?? "active" : "none"}
          </div>
        </div>
        <div className="stat">
          <div className="label">Attestation</div>
          <div className={`value ${activeLic?.encryptionAttestation ? "" : "warm"}`}>
            {activeLic?.attestationStatus ?? "pending"}
          </div>
        </div>
        <div className="stat">
          <div className="label">Piggyback regions</div>
          <div className="value">{regions.length}</div>
        </div>
      </div>
      {!activePort ? (
        <div className="gap-banner">
          Register your first app and allocate a MeshPort before production. Collision blocks are hard.
        </div>
      ) : null}
      <div className="row" style={{ marginBottom: "1.25rem" }}>
        <Link className="btn" to="/meshports">Allocate MeshPort</Link>
        <Link className="btn ghost" to="/licenses">Issue license</Link>
        <Link className="btn ghost" to="/piggyback">Open piggyback map</Link>
        <Link className="btn ghost" to="/density">Run density model</Link>
      </div>
      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Piggyback shortlist</h3>
        {regions.length === 0 ? (
          <p style={{ color: "var(--color-mute)" }}>
            No contributor density yet — greenfield regions will show high penetration need in the model.
          </p>
        ) : (
          <div className="card-grid">
            {regions.slice(0, 4).map((r: any, i: number) => (
              <div key={i} className="panel" style={{ margin: 0 }}>
                <strong>{r.region}</strong>
                <div style={{ color: "var(--color-mute)", fontSize: "0.85rem" }}>
                  readiness {r.launchReadinessScore ?? "—"} · apps {r.contributorApps?.length ?? 0}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
