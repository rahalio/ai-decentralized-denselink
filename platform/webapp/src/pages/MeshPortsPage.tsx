import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { meshportsService } from "@/services/domains/meshports";
import { itemsOf } from "@/lib/envelope";

export function MeshPortsPage() {
  const qc = useQueryClient();
  const [appId, setAppId] = useState("app_01HZYXK8J0M0W5N6P7Q8R9S0T123");
  const [preferredPort, setPreferredPort] = useState("");
  const [collision, setCollision] = useState<string | null>(null);

  const list = useQuery({ queryKey: ["meshports"], queryFn: () => meshportsService.listMeshPorts() });
  const allocate = useMutation({
    mutationFn: () =>
      meshportsService.allocateMeshPort({
        appId,
        preferredPort: preferredPort ? Number(preferredPort) : undefined,
        sdkVersion: "1.0.0",
      }),
    onSuccess: () => {
      setCollision(null);
      qc.invalidateQueries({ queryKey: ["meshports"] });
    },
    onError: (err: any) => {
      if (err?.statusCode === 409) {
        setCollision(err.message || "Port collision — publication blocked.");
      }
    },
  });

  const items = itemsOf(list.data);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    allocate.mutate();
  }

  return (
    <div>
      <h1 className="page-title">MeshPort registry</h1>
      <p className="page-sub">
        Allocate unique ports and block publication on collision so one app cannot intercept another&apos;s traffic.
      </p>
      {collision ? <div className="collision-banner">{collision}</div> : null}
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <form onSubmit={onSubmit} className="MeshPortAllocateForm">
          <div className="field">
            <label htmlFor="appId">App ID</label>
            <input id="appId" value={appId} onChange={(e) => setAppId(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="port">Preferred port (optional)</label>
            <input
              id="port"
              value={preferredPort}
              onChange={(e) => setPreferredPort(e.target.value)}
              placeholder="e.g. 4242"
            />
          </div>
          <button className="btn" type="submit" disabled={allocate.isPending}>
            {allocate.isPending ? "Allocating…" : "Allocate MeshPort"}
          </button>
        </form>
      </div>
      <div className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>Port</th>
              <th>App</th>
              <th>SDK</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ color: "var(--color-mute)" }}>
                  No allocations yet — allocate your first MeshPort above.
                </td>
              </tr>
            ) : (
              items.map((p: any) => (
                <tr key={p.id ?? p.port}>
                  <td className="mono">{p.port}</td>
                  <td className="mono">{p.appId}</td>
                  <td>{p.sdkVersion ?? "—"}</td>
                  <td>
                    <span className={`badge ${p.status === "allocated" ? "ok" : "bad"}`}>
                      {p.status}
                    </span>
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
