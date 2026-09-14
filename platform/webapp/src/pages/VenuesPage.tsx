import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { venuesService } from "@/services/domains/venues";
import { itemsOf } from "@/lib/envelope";

function Heatmap({ bins = 36 }: { bins?: number }) {
  return (
    <div className="heatmap CoverageHeatmap" aria-label="Coverage heatmap">
      {Array.from({ length: bins }).map((_, i) => {
        const cls = i % 7 === 0 ? "hot" : i % 3 === 0 ? "warm" : i % 2 === 0 ? "cool" : "";
        return <span key={i} className={cls} />;
      })}
    </div>
  );
}

export function VenuesPage() {
  const qc = useQueryClient();
  const [venueType, setVenueType] = useState("stadium");
  const [name, setName] = useState("Event day wedge");
  const [city, setCity] = useState("Dhaka");

  const list = useQuery({ queryKey: ["venues"], queryFn: () => venuesService.listVenueProgrammes() });
  const create = useMutation({
    mutationFn: () => venuesService.createVenueProgramme({ venueType, name, city, activeNodeTarget: 200 }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["venues"] }),
  });

  const items = itemsOf(list.data);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div>
      <h1 className="page-title">Venue programme board</h1>
      <p className="page-sub">
        Stadium / school / mall wedge kits with event-day nodes, sessions, and heatmaps for sponsors.
      </p>
      <div className="panel VenueWedgeKit" style={{ marginBottom: "1rem" }}>
        <form onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="type">Venue type</label>
            <select id="type" value={venueType} onChange={(e) => setVenueType(e.target.value)}>
              <option value="stadium">stadium</option>
              <option value="school">school</option>
              <option value="mall">mall</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="name">Name</label>
            <input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="city">City</label>
            <input id="city" value={city} onChange={(e) => setCity(e.target.value)} />
          </div>
          <button className="btn" type="submit" disabled={create.isPending}>
            {create.isPending ? "Enrolling…" : "Enrol venue programme"}
          </button>
        </form>
      </div>
      <div className="card-grid">
        {items.length === 0 ? (
          <div className="panel" style={{ color: "var(--color-mute)" }}>No venue programmes yet.</div>
        ) : (
          items.map((v: any) => (
            <div key={v.id} className="panel" style={{ margin: 0 }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <strong>{v.name}</strong>
                <span className="badge ok">{v.venueType}</span>
              </div>
              <div style={{ color: "var(--color-mute)", fontSize: "0.85rem", marginTop: 4 }}>
                {v.city ?? "—"} · nodes {v.activeNodes ?? 0}/{v.activeNodeTarget ?? "—"} · {v.status}
              </div>
              <Heatmap bins={v.heatmapBins || 36} />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
