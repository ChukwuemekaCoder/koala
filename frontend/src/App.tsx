import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { SessionProvider } from "./lib/SessionContext";
import { OnboardingProvider } from "./lib/OnboardingContext";
import { RequireSession, RequireOnboarded, RedirectIfOnboarded, RedirectIfAuthed } from "./lib/guards";
import { LandingRoute } from "./routes/LandingRoute";
import { AuthRoute } from "./routes/AuthRoute";
import { OnboardingRoute } from "./routes/OnboardingRoute";
import { DashboardRoute } from "./routes/DashboardRoute";
import { NotificationsRoute } from "./routes/NotificationsRoute";

function App() {
  return (
    <BrowserRouter>
      <SessionProvider>
        <OnboardingProvider>
          <Routes>
            <Route element={<RedirectIfAuthed />}>
              <Route path="/" element={<LandingRoute />} />
              <Route path="/auth" element={<AuthRoute />} />
            </Route>

            <Route element={<RequireSession />}>
              <Route element={<RedirectIfOnboarded />}>
                <Route path="/onboarding" element={<OnboardingRoute />} />
              </Route>
              <Route element={<RequireOnboarded />}>
                <Route path="/dashboard" element={<DashboardRoute />} />
                <Route path="/notifications" element={<NotificationsRoute />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </OnboardingProvider>
      </SessionProvider>
    </BrowserRouter>
  );
}

export default App;
