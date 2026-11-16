import { Navigate, Outlet, Route, Routes, useLocation } from "react-router";
import { useAuth } from "./auth/AuthContext.jsx";
import { usePublicConfig } from "./config/PublicConfig.jsx";
import AppShell from "./shell/AppShell.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SsoCompletePage from "./pages/SsoCompletePage.jsx";
import CourseHomePage from "./pages/CourseHomePage.jsx";
import StudentAgentPage from "./pages/StudentAgentPage.jsx";
import StudentWorkspace from "./pages/StudentWorkspace.jsx";
import StudentAsksPage from "./pages/StudentAsksPage.jsx";
import StudentRevisionPage from "./pages/StudentRevisionPage.jsx";
import StudentNotesPage from "./pages/StudentNotesPage.jsx";
import StuckRoomPage from "./pages/StuckRoomPage.jsx";
import TaWorkspace from "./pages/TaWorkspace.jsx";
import TaPastAsksPage from "./pages/TaPastAsksPage.jsx";
import TaDashboardPage from "./pages/TaDashboardPage.jsx";
import MaterialPage from "./pages/professor/MaterialPage.jsx";
import AsksPage from "./pages/professor/AsksPage.jsx";
import InsightsPage from "./pages/professor/InsightsPage.jsx";
import TeamPage from "./pages/professor/TeamPage.jsx";
import CanvasSimulatorPage from "./pages/CanvasSimulatorPage.jsx";
import CanvasLaunchPage from "./pages/CanvasLaunchPage.jsx";
import VisionDemoHub from "./pages/VisionDemoHub.jsx";
import VisionDemoBoard from "./pages/VisionDemoBoard.jsx";
import VisionDemoPath from "./pages/VisionDemoPath.jsx";
import VisionDemoTrio from "./pages/VisionDemoTrio.jsx";
import StudentVisionPrototype from "./pages/StudentVisionPrototype.jsx";

function LoadingScreen() {
  return (
    <div className="aui-shell flex min-h-screen items-center justify-center">
      <div className="glass-panel px-8 py-6 text-aui-deep">Loading OfficeHours AI…</div>
    </div>
  );
}

function ProfessorGate() {
  const { activeCourse } = useAuth();
  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "professor") {
    return <Navigate to={activeCourse.role === "ta" ? "/ta" : "/student"} replace />;
  }
  return <Outlet />;
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
  const { demo } = usePublicConfig();
  const showDemos = demo;

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/sso" element={<SsoCompletePage />} />
      {/* Prototype always reachable for feedback - not behind demo race */}
      <Route path="/demo/student-vision" element={<StudentVisionPrototype />} />
      {showDemos ? (
        <>
          <Route path="/demo" element={<VisionDemoHub />} />
          <Route path="/demo/board" element={<VisionDemoBoard />} />
          <Route path="/demo/path" element={<VisionDemoPath />} />
          <Route path="/demo/trio" element={<VisionDemoTrio />} />
          <Route path="/canvas-demo" element={<CanvasSimulatorPage />} />
          <Route path="/launch" element={<CanvasLaunchPage />} />
        </>
      ) : null}
      <Route
        path="/"
        element={
          <GuestHomeOrApp>
            <AppShell />
          </GuestHomeOrApp>
        }
      >
        <Route index element={<CourseHomePage />} />
        <Route path="student" element={<StudentAgentPage />} />
        <Route path="student/ask" element={<StudentWorkspace />} />
        <Route path="student/asks" element={<StudentAsksPage />} />
        <Route path="student/revision" element={<StudentRevisionPage />} />
        <Route path="student/notes" element={<StudentNotesPage />} />
        <Route path="student/room" element={<StuckRoomPage />} />
        <Route path="ta" element={<TaWorkspace />} />
        <Route path="ta/home" element={<TaDashboardPage />} />
        <Route path="ta/past" element={<TaPastAsksPage />} />
        <Route path="professor" element={<ProfessorGate />}>
          <Route index element={<MaterialPage />} />
          <Route path="asks" element={<AsksPage />} />
          <Route path="insights" element={<InsightsPage />} />
          <Route path="team" element={<TeamPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
