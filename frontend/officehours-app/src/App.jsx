import { Navigate, Route, Routes, useLocation } from "react-router";
import { useAuth } from "./auth/AuthContext.jsx";
import AppShell from "./shell/AppShell.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import CourseHomePage from "./pages/CourseHomePage.jsx";
import StudentWorkspace from "./pages/StudentWorkspace.jsx";
import StuckRoomPage from "./pages/StuckRoomPage.jsx";
import TaWorkspace from "./pages/TaWorkspace.jsx";
import ProfessorWorkspace from "./pages/ProfessorWorkspace.jsx";
import CanvasSimulatorPage from "./pages/CanvasSimulatorPage.jsx";
import CanvasLaunchPage from "./pages/CanvasLaunchPage.jsx";
import VisionDemoHub from "./pages/VisionDemoHub.jsx";
import VisionDemoBoard from "./pages/VisionDemoBoard.jsx";
import VisionDemoPath from "./pages/VisionDemoPath.jsx";
import VisionDemoTrio from "./pages/VisionDemoTrio.jsx";

function LoadingScreen() {
  return (
    <div className="aui-shell flex min-h-screen items-center justify-center">
      <div className="glass-panel px-8 py-6 text-aui-deep">Loading OfficeHours AI…</div>
    </div>
  );
}

function GuestHomeOrApp({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingScreen />;
  if (!user) {
    if (location.pathname === "/") return <LandingPage />;
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/demo" element={<VisionDemoHub />} />
      <Route path="/demo/board" element={<VisionDemoBoard />} />
      <Route path="/demo/path" element={<VisionDemoPath />} />
      <Route path="/demo/trio" element={<VisionDemoTrio />} />
      <Route path="/canvas-demo" element={<CanvasSimulatorPage />} />
      <Route path="/launch" element={<CanvasLaunchPage />} />
      <Route
        path="/"
        element={
          <GuestHomeOrApp>
            <AppShell />
          </GuestHomeOrApp>
        }
      >
        <Route index element={<CourseHomePage />} />
        <Route path="student" element={<StudentWorkspace />} />
        <Route path="student/room" element={<StuckRoomPage />} />
        <Route path="ta" element={<TaWorkspace />} />
        <Route path="professor" element={<ProfessorWorkspace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
