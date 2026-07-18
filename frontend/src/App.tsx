import { useEffect, useState } from "react";
import { USE_MOCK, api } from "./api";
import { Dashboard } from "./components/Dashboard";
import { Login } from "./components/Login";
import type { User } from "./types";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    // In mock mode we stay logged out until the user clicks "Continue".
    if (USE_MOCK) {
      setChecked(true);
      return;
    }
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setChecked(true));
  }, []);

  async function logout() {
    await api.logout();
    setUser(null);
  }

  if (!checked) return null;
  if (!user) return <Login onDemo={async () => setUser(await api.me())} />;
  return <Dashboard user={user} onLogout={logout} />;
}
