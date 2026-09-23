import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ChatLayout } from "./components/ChatLayout";
import { Login } from "./components/Login";

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="loading-screen">Loading…</div>;
  }

  return user ? <ChatLayout /> : <Login />;
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
