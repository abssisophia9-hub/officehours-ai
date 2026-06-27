import { useState } from "react";
import RequestForm from "./components/RequestForm.jsx";
import ConfirmationScreen from "./components/ConfirmationScreen.jsx";

export default function App() {
  const [screen, setScreen] = useState("form");
  const [result, setResult] = useState(null);

  function handleSubmitted(request) {
    setResult(request);
    setScreen("confirmation");
  }

  function handleReset() {
    setResult(null);
    setScreen("form");
  }

  return (
    <div className="flex min-h-full flex-col bg-gradient-to-br from-indigo-50 via-slate-50 to-emerald-50">
      <header className="flex items-center gap-3 px-8 py-6">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-600 text-lg font-extrabold text-white shadow-lg shadow-indigo-300">
          OH
        </div>
        <div>
          <p className="text-lg font-bold leading-tight text-slate-900">
            OfficeHours AI
          </p>
          <p className="text-sm leading-tight text-slate-500">
            Student Help Kiosk
          </p>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-6 pb-12">
        {screen === "form" ? (
          <RequestForm onSubmitted={handleSubmitted} />
        ) : (
          <ConfirmationScreen result={result} onReset={handleReset} />
        )}
      </main>

      <footer className="px-8 pb-6 text-center text-sm text-slate-400">
        Your privacy matters — anonymous requests never store your identity.
      </footer>
    </div>
  );
}
