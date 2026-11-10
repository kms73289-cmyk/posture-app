import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

export function AppLayout() {
  return (
    <div className="flex h-screen min-w-[1100px] bg-[linear-gradient(135deg,var(--page-from),var(--page-to))]">
      <Sidebar />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex min-h-0 flex-1 flex-col overflow-y-auto px-8 pb-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
