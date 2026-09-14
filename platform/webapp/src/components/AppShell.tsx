import { NavLink, Outlet } from "react-router-dom";

const developer = [
  { to: "/home", label: "Developer home", end: true },
  { to: "/meshports", label: "MeshPorts" },
  { to: "/licenses", label: "Licenses" },
  { to: "/piggyback", label: "Piggyback discovery" },
  { to: "/density", label: "Density model" },
];

const venues = [
  { to: "/venues", label: "Venue programmes", end: true },
  { to: "/always-on", label: "Always-on campaigns" },
  { to: "/sponsor-roi", label: "Sponsor ROI" },
];

const devrel = [
  { to: "/contribution", label: "Contribution rank", end: true },
  { to: "/grants", label: "Grants & milestones" },
  { to: "/beta-cohort", label: "Beta cohort" },
];

const admin = [
  { to: "/admin", label: "Revoke & attestation", end: true },
];

function Group({
  title,
  items,
}: {
  title: string;
  items: Array<{ to: string; label: string; end?: boolean }>;
}) {
  return (
    <div className="nav-group">
      <div className="nav-label">{title}</div>
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
        >
          {item.label}
        </NavLink>
      ))}
    </div>
  );
}

export function AppShell() {
  return (
    <div className="shell">
      <aside className="shell-nav">
        <div className="brand surveyor">
          Denselink
          <small>Coverage commons desk</small>
        </div>
        <Group title="Developer" items={developer} />
        <Group title="Venues" items={venues} />
        <Group title="DevRel / incentives" items={devrel} />
        <Group title="Admin" items={admin} />
        <div style={{ marginTop: "auto" }}>
          <NavLink
            to="/login"
            className="nav-link"
            onClick={() => {
              localStorage.removeItem("denselink_session");
              localStorage.removeItem("denselink_role");
            }}
          >
            Sign out
          </NavLink>
        </div>
      </aside>
      <main className="shell-main">
        <Outlet />
      </main>
    </div>
  );
}
