import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { MeasurePage } from "./pages/MeasurePage";
import { ReportPage } from "./pages/ReportPage";
import { HistoryPage } from "./pages/HistoryPage";
import { SettingsPage } from "./pages/SettingsPage";
import { useMonitorSocket } from "./hooks/useMonitorSocket";

export default function App() {
  useMonitorSocket();
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<MeasurePage />} />
        <Route path="/report" element={<ReportPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
