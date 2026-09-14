import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

const ROLE_HOMES: Record<string, string> = {
  developer: "/home",
  venue: "/venues",
  devrel: "/contribution",
  analytics: "/density",
  incentives: "/grants",
  admin: "/admin",
};

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@demo.local");
  const [password, setPassword] = useState("sandbox-admin-8");
  const [role, setRole] = useState("developer");
  const [error, setError] = useState<string | null>(null);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!email || !password) {
      setError("Email and password required");
      return;
    }
    localStorage.setItem("denselink_session", "1");
    localStorage.setItem("denselink_role", role);
    navigate(ROLE_HOMES[role] ?? "/home");
  }

  return (
    <div className="login-wrap">
      <div className="login-panel panel">
        <div className="brand surveyor stamp">Denselink</div>
        <h1>Is the mesh useful here yet?</h1>
        <form onSubmit={onSubmit}>
          <div className="field" style={{ textAlign: "left" }}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div className="field" style={{ textAlign: "left" }}>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <div className="field" style={{ textAlign: "left" }}>
            <label htmlFor="role">Role home</label>
            <select
              id="role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="developer">Mobile developer</option>
              <option value="devrel">DevRel manager</option>
              <option value="venue">Venue operator</option>
              <option value="analytics">Analytics lead</option>
              <option value="incentives">Incentives admin</option>
              <option value="admin">Platform administrator</option>
            </select>
          </div>
          {error ? (
            <p style={{ color: "var(--color-flag)", fontSize: "0.85rem" }}>
              {error}
            </p>
          ) : null}
          <button className="btn" type="submit" style={{ width: "100%" }}>
            Enter density console
          </button>
        </form>
        <p
          style={{
            color: "var(--color-mute)",
            fontSize: "0.75rem",
            marginTop: "1rem",
          }}
        >
          Demo uses X-API-Key under the hood. Operator session seeds the shell.
        </p>
      </div>
    </div>
  );
}
