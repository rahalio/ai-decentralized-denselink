import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { licensesService } from "@/services/domains/licenses";
import { itemsOf, dataOf } from "@/lib/envelope";

export function LicensesPage() {
  const qc = useQueryClient();
  const [appId, setAppId] = useState("app_01HZYXK8J0M0W5N6P7Q8R9S0T123");
  const [developerId, setDeveloperId] = useState("dev_01HZYXK8J0M0W5N6P7Q8R9S0T123");
  const [tier, setTier] = useState("private_beta");
  const [secretOnce, setSecretOnce] = useState<string | null>(null);

  const list = useQuery({ queryKey: ["licenses"], queryFn: () => licensesService.listLicenseKeys() });
  const issue = useMutation({
    mutationFn: () => licensesService.issueLicenseKey({ appId, developerId, tier }),
    onSuccess: (res) => {
      const data = dataOf<any>(res) ?? res;
      setSecretOnce(data?.secret ?? null);
      qc.invalidateQueries({ queryKey: ["licenses"] });
    },
  });
  const attest = useMutation({
    mutationFn: (licenseId: string) =>
      licensesService.bindLicenseAttestation(licenseId, {
        buildFingerprint: `build_${Date.now()}`,
        encryptionProtocol: "signal-protocol",
        passed: true,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["licenses"] }),
  });

  const items = itemsOf(list.data);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    issue.mutate();
  }

  return (
    <div>
      <h1 className="page-title">License keys &amp; build bind</h1>
      <p className="page-sub">
        Issue free SDK license keys, bind to app builds, and show Signal-derived E2E attestation status.
      </p>
      {secretOnce ? (
        <div className="gap-banner">
          Copy secret once: <code className="mono">{secretOnce}</code>
        </div>
      ) : null}
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <form onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="appId">App ID</label>
            <input id="appId" value={appId} onChange={(e) => setAppId(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="devId">Developer ID</label>
            <input id="devId" value={developerId} onChange={(e) => setDeveloperId(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="tier">Tier</label>
            <select id="tier" value={tier} onChange={(e) => setTier(e.target.value)}>
              <option value="private_beta">private_beta</option>
              <option value="public_beta">public_beta</option>
              <option value="production">production</option>
            </select>
          </div>
          <button className="btn" type="submit" disabled={issue.isPending}>
            {issue.isPending ? "Issuing…" : "Issue license key"}
          </button>
        </form>
      </div>
      <div className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>License</th>
              <th>Tier</th>
              <th>Attestation</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ color: "var(--color-mute)" }}>No licenses yet.</td>
              </tr>
            ) : (
              items.map((l: any) => (
                <tr key={l.id}>
                  <td className="mono">{l.id}</td>
                  <td>{l.tier}</td>
                  <td>
                    <span className={`badge LicenseAttestationBadge ${l.encryptionAttestation ? "ok" : "warn"}`}>
                      {l.attestationStatus ?? (l.encryptionAttestation ? "passed" : "pending")}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${l.status === "active" ? "ok" : "bad"}`}>{l.status}</span>
                  </td>
                  <td>
                    {l.status === "active" && !l.encryptionAttestation ? (
                      <button className="btn ghost" type="button" onClick={() => attest.mutate(l.id)}>
                        Bind attestation
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
