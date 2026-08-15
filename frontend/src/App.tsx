import { BrowserRouter } from "react-router-dom";
import { SessionProvider } from "./lib/SessionContext";
import { OnboardingProvider } from "./lib/OnboardingContext";
import { AnimatedRoutes } from "./routes/AnimatedRoutes";

function App() {
  return (
    <BrowserRouter>
      <SessionProvider>
        <OnboardingProvider>
          <AnimatedRoutes />
        </OnboardingProvider>
      </SessionProvider>
    </BrowserRouter>
  );
}

export default App;
