import { Navigate, Route, Routes } from "react-router";
import { useAuth } from "./auth/AuthContext.jsx";
import AppShell from "./shell/AppShell.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import CourseHomePage from "./pages/CourseHomePage.jsx";
import StudentWorkspace from "./pages/StudentWorkspace.jsx";
import TaWorkspace from "./pages/TaWorkspace.jsx";
import ProfessorWorkspace from "./pages/ProfessorWorkspace.jsx";
import CanvasSimulatorPage from "./pages/CanvasSimulatorPage.jsx";
import CanvasLaunchPage from "./pages/CanvasLaunchPage.jsx";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="aui-shell flex min-h-screen items-center justify-center">
        <div className="glass-panel px-8 py-6 text-aui-deep">Loading OfficeHours AI…</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/canvas-demo" element={<CanvasSimulatorPage />} />
      <Route path="/launch" element={<CanvasLaunchPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <AppShell />
          </Protected>
        }
      >
        <Route index element={<CourseHomePage />} />
        <Route path="student" element={<StudentWorkspace />} />
        <Route path="ta" element={<TaWorkspace />} />
        <Route path="professor" element={<ProfessorWorkspace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
