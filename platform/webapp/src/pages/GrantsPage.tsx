import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { grantsService } from "@/services/domains/grants";
import { itemsOf } from "@/lib/envelope";

export function GrantsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("Density commons grant");
  const [metric, setMetric] = useState("active_nodes");
  const [threshold, setThreshold] = useState("500");
  const [reward, setReward] = useState("1000");
  const [selected, setSelected] = useState<string | null>(null);

  const list = useQuery({ queryKey: ["grants"], queryFn: () => grantsService.listGrantProgrammes() });
  const milestones = useQuery({
    queryKey: ["milestones", selected],
    queryFn: () => grantsService.listGrantMilestones(selected!),
    enabled: Boolean(selected),
  });
  const create = useMutation({
    mutationFn: () =>
      grantsService.createGrantProgramme({
        name,
        milestoneMetric: metric,
        milestoneThreshold: Number(threshold),
        rewardAmount: Number(reward),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["grants"] }),
  });
  const disburse = useMutation({
    mutationFn: (milestoneId: string) => grantsService.disburseMilestone(milestoneId, { note: "density milestone hit" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["milestones", selected] }),
  });

  const programmes = itemsOf(list.data);
  const milestoneItems = itemsOf(milestones.data);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div>
      <h1 className="page-title">Grants &amp; milestones</h1>
      <p className="page-sub">
        Release grants on measured density milestones — not vanity install counts.
      </p>
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <form onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="name">Programme name</label>
            <input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="metric">Milestone metric</label>
            <select id="metric" value={metric} onChange={(e) => setMetric(e.target.value)}>
              <option value="active_nodes">active_nodes</option>
              <option value="penetration_percent">penetration_percent</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="threshold">Threshold</label>
            <input id="threshold" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="reward">Reward amount</label>
            <input id="reward" value={reward} onChange={(e) => setReward(e.target.value)} />
          </div>
          <button className="btn" type="submit" disabled={create.isPending}>Create programme</button>
        </form>
      </div>
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <table className="table">
          <thead>
            <tr><th>Name</th><th>Metric</th><th>Reward</th><th>Status</th><th /></tr>
          </thead>
          <tbody>
            {programmes.length === 0 ? (
              <tr><td colSpan={5} style={{ color: "var(--color-mute)" }}>No grant programmes.</td></tr>
            ) : programmes.map((g: any) => (
              <tr key={g.id}>
                <td>{g.name}</td>
                <td>{g.milestoneMetric}</td>
                <td>{g.rewardAmount}</td>
                <td><span className="badge ok">{g.status}</span></td>
                <td>
                  <button className="btn ghost" type="button" onClick={() => setSelected(g.id)}>
                    Milestones
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selected ? (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Milestones</h3>
          <table className="table">
            <thead>
              <tr><th>ID</th><th>Measured</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {milestoneItems.length === 0 ? (
                <tr><td colSpan={4} style={{ color: "var(--color-mute)" }}>No milestones yet.</td></tr>
              ) : milestoneItems.map((m: any) => (
                <tr key={m.id} className="MilestoneGrantRow">
                  <td className="mono">{m.id}</td>
                  <td>{m.measuredValue}</td>
                  <td><span className="badge">{m.status}</span></td>
                  <td>
                    {m.status === "achieved" ? (
                      <button className="btn" type="button" onClick={() => disburse.mutate(m.id)}>
                        Disburse
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
