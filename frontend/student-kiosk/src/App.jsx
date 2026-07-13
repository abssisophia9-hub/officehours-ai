import { useState } from "react";
import CheckInScreen from "./components/CheckInScreen.jsx";
import RequestForm from "./components/RequestForm.jsx";
import ConfirmationScreen from "./components/ConfirmationScreen.jsx";
import StatusLookupScreen from "./components/StatusLookupScreen.jsx";
import KbAgentScreen from "./components/KbAgentScreen.jsx";

export default function App() {
  const [screen, setScreen] = useState("check-in");
  const [checkIn, setCheckIn] = useState(null);
  const [result, setResult] = useState(null);
  const [statusCode, setStatusCode] = useState("");

  function handleCheckIn(nextCheckIn) {
    setCheckIn(nextCheckIn);
    setScreen("form");
  }

  function handleSubmitted(request) {
    setResult(request);
    setScreen("confirmation");
  }

  function handleReset() {
    setCheckIn(null);
    setResult(null);
    setStatusCode("");
    setScreen("check-in");
  }

  function openStatusLookup(code = "") {
    setStatusCode(code ? String(code) : "");
    setScreen("status");
  }

  return (
    <div className="aui-shell flex min-h-full flex-col">
      <header className="px-5 pt-5 sm:px-8 sm:pt-6">
        <div className="glass-header flex flex-wrap items-center justify-between gap-4 px-5 py-4 sm:px-6">
          <div className="flex items-center gap-4">
            <img
              src="/aui-logo.png"
              alt="Al Akhawayn University"
              className="aui-logo animate-floaty"
            />
            <div>
              <p className="font-display text-2xl font-bold leading-tight text-aui-ink sm:text-3xl">
                OfficeHours AI
              </p>
              <p className="text-sm font-medium text-aui-deep/75">
                AUI Student Help Kiosk · Ifrane
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setScreen("agent")}
              className="btn-ghost px-4 py-2 text-sm"
            >
              Ask KB agent
            </button>
            <button
              type="button"
              onClick={() => openStatusLookup()}
              className="btn-ghost px-4 py-2 text-sm"
            >
              Check request status
            </button>
          </div>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-5 py-8 sm:px-6 sm:pb-12">
        {screen === "check-in" && <CheckInScreen onContinue={handleCheckIn} />}
        {screen === "form" && (
          <RequestForm checkIn={checkIn} onSubmitted={handleSubmitted} />
        )}
        {screen === "confirmation" && (
          <ConfirmationScreen
            result={result}
            onReset={handleReset}
            onCheckStatus={() => openStatusLookup(result.id)}
          />
        )}
        {screen === "status" && (
          <StatusLookupScreen
            initialCode={statusCode}
            onBack={handleReset}
          />
        )}
        {screen === "agent" && <KbAgentScreen onBack={handleReset} />}
      </main>

      <footer className="px-8 pb-6 text-center text-sm text-aui-deep/55">
        Al Akhawayn University · Your privacy matters — anonymous requests never
        store your identity. The KB agent only uses professor-approved answers.
      </footer>
    </div>
  );
}
