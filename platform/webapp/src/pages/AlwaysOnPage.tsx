import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { venuesService } from "@/services/domains/venues";
import { itemsOf } from "@/lib/envelope";

export function AlwaysOnPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("Flare-class always-on");
  const list = useQuery({ queryKey: ["always-on"], queryFn: () => venuesService.listAlwaysOnCampaigns() });
  const create = useMutation({
    mutationFn: () => venuesService.createAlwaysOnCampaign({ name, enabled: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["always-on"] }),
  });
  const items = itemsOf(list.data);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div>
      <h1 className="page-title">Always-on node campaigns</h1>
      <p className="page-sub">
        Configure Flare-style always-on campaigns without inflating consumer UX metrics.
      </p>
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <form onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="name">Campaign name</label>
            <input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <button className="btn" type="submit" disabled={create.isPending}>Create campaign</button>
        </form>
      </div>
      <div className="panel">
        <table className="table">
          <thead>
            <tr><th>Name</th><th>Enabled</th><th>Consumer inflate</th></tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr><td colSpan={3} style={{ color: "var(--color-mute)" }}>No campaigns.</td></tr>
            ) : items.map((c: any) => (
              <tr key={c.id} className="AlwaysOnCampaignFlag">
                <td>{c.name}</td>
                <td><span className={`badge ${c.enabled ? "ok" : ""}`}>{c.enabled ? "on" : "off"}</span></td>
                <td><span className="badge ok">never</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
