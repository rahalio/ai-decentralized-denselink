import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { LoginPage } from "@/pages/LoginPage";
import { DeveloperHomePage } from "@/pages/DeveloperHomePage";
import { MeshPortsPage } from "@/pages/MeshPortsPage";
import { LicensesPage } from "@/pages/LicensesPage";
import { PiggybackPage } from "@/pages/PiggybackPage";
import { DensityModelPage } from "@/pages/DensityModelPage";
import { VenuesPage } from "@/pages/VenuesPage";
import { AlwaysOnPage } from "@/pages/AlwaysOnPage";
import { GrantsPage } from "@/pages/GrantsPage";
import { ContributionPage } from "@/pages/ContributionPage";
import { BetaCohortPage } from "@/pages/BetaCohortPage";
import { SponsorRoiPage } from "@/pages/SponsorRoiPage";
import { AdminPage } from "@/pages/AdminPage";

function RequireSession({ children }: { children: ReactNode }) {
  const ok =
    typeof window !== "undefined" && localStorage.getItem("denselink_session");
  if (!ok) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireSession>
            <AppShell />
          </RequireSession>
        }
      >
        <Route index element={<Navigate to="/home" replace />} />
        <Route path="home" element={<DeveloperHomePage />} />
        <Route path="meshports" element={<MeshPortsPage />} />
        <Route path="licenses" element={<LicensesPage />} />
        <Route path="piggyback" element={<PiggybackPage />} />
        <Route path="density" element={<DensityModelPage />} />
        <Route path="venues" element={<VenuesPage />} />
        <Route path="always-on" element={<AlwaysOnPage />} />
        <Route path="grants" element={<GrantsPage />} />
        <Route path="contribution" element={<ContributionPage />} />
        <Route path="beta-cohort" element={<BetaCohortPage />} />
        <Route path="sponsor-roi" element={<SponsorRoiPage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
