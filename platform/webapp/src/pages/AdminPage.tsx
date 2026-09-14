import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { licensesService } from "@/services/domains/licenses";
import { itemsOf } from "@/lib/envelope";

export function AdminPage() {
  const qc = useQueryClient();
  const [licenseId, setLicenseId] = useState("");
  const list = useQuery({ queryKey: ["licenses"], queryFn: () => licensesService.listLicenseKeys() });
  const revoke = useMutation({
    mutationFn: (id: string) => licensesService.revokeLicenseKey(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["licenses"] }),
  });
  const items = itemsOf(list.data);
  const queue = items.filter((l: any) => l.attestationStatus === "failed" || l.attestationStatus === "pending");

  function onRevoke(e: FormEvent) {
    e.preventDefault();
    if (!licenseId) return;
    revoke.mutate(licenseId);
  }

  return (
    <div>
      <h1 className="page-title">License revoke &amp; attestation queue</h1>
      <p className="page-sub">
        Abuse revoke flows and encryption attestation failures that block production-ready badges.
      </p>
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <form onSubmit={onRevoke}>
          <div className="field">
            <label htmlFor="lid">License ID to revoke</label>
            <input id="lid" value={licenseId} onChange={(e) => setLicenseId(e.target.value)} />
          </div>
          <button className="btn flag" type="submit" disabled={revoke.isPending}>
            Revoke license
          </button>
        </form>
      </div>
      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Attestation queue</h3>
        <table className="table">
          <thead>
            <tr><th>License</th><th>App</th><th>Attestation</th><th>Status</th></tr>
          </thead>
          <tbody>
            {queue.length === 0 ? (
              <tr><td colSpan={4} style={{ color: "var(--color-mute)" }}>Queue empty.</td></tr>
            ) : queue.map((l: any) => (
              <tr key={l.id}>
                <td className="mono">{l.id}</td>
                <td className="mono">{l.appId}</td>
                <td>
                  <span className={`badge ${l.attestationStatus === "failed" ? "bad" : "warn"}`}>
                    {l.attestationStatus}
                  </span>
                </td>
                <td>{l.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
