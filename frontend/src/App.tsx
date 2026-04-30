import { useEffect, useState } from "react";

type Profile = { appScope: string; role: string; context: string | null };
type User = {
  id: string;
  username: string;
  suspended: boolean;
  profiles: Profile[];
};
type SessionProfile = { appScope: string; role: string; context?: string | null };

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const APP_SCOPE_ROLES: Record<string, string[]> = {
  "org-app": ["org-admin", "org-app", "org-third"],
  "provider-app": ["provider-admin", "provider-app", "provider-third"],
  "subscription-app": ["subscribe-admin", "subscribe-app", "subscribe-third"],
  "auth-app": ["auth-admin"],
};

async function api(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem("auth_token");
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};
  const customHeaders =
    options.headers && typeof options.headers === "object"
      ? (options.headers as Record<string, string>)
      : {};
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...customHeaders,
    },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || `HTTP ${response.status}`) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }
  return payload;
}

export default function App() {
  const [status, setStatus] = useState("Please log in");
  const [isError, setIsError] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [authToken, setAuthToken] = useState(localStorage.getItem("auth_token") || "");
  const [sessionUser, setSessionUser] = useState(localStorage.getItem("auth_username") || "");
  const [isAuthAdmin, setIsAuthAdmin] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  const [loginUsername, setLoginUsername] = useState("admin");
  const [loginPassword, setLoginPassword] = useState("admin123");
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [resetUserRef, setResetUserRef] = useState("");
  const [resetPasswordValue, setResetPasswordValue] = useState("");
  const [profileUserId, setProfileUserId] = useState("");
  const [appScope, setAppScope] = useState("org-app");
  const [role, setRole] = useState(APP_SCOPE_ROLES["org-app"][0]);
  const [context, setContext] = useState("org-001");

  const setMessage = (message: string, error = false) => {
    setStatus(message);
    setIsError(error);
  };
  const clearSessionWithMessage = (message: string) => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_username");
    setAuthToken("");
    setSessionUser("");
    setUsers([]);
    setIsAuthAdmin(false);
    setAuthChecked(true);
    setMessage(message, true);
  };
  const handleApiError = (prefix: string, error: unknown) => {
    const apiError = error as Error & { status?: number };
    if (apiError.status === 401) {
      clearSessionWithMessage("Session expired, please login again");
      return;
    }
    setMessage(`${prefix}: ${apiError.message}`, true);
  };

  const loadUsers = async () => {
    if (!authToken || !isAuthAdmin) return;
    try {
      const payload = await api("/admin/auth/users");
      setUsers(payload.data || []);
      setMessage("Users loaded");
    } catch (error) {
      handleApiError("Load failed", error);
    }
  };

  useEffect(() => {
    void loadUsers();
  }, [authToken, isAuthAdmin]);

  const checkAdminAccess = async () => {
    if (!authToken) {
      setIsAuthAdmin(false);
      setAuthChecked(true);
      return;
    }
    try {
      const payload = await api("/third/auth/whois", {
        method: "POST",
        body: JSON.stringify({ token: authToken }),
      });
      const profiles = (payload?.data?.profiles || []) as SessionProfile[];
      const allowed = profiles.some((p) => p.appScope === "auth-app" && p.role === "auth-admin");
      setIsAuthAdmin(allowed);
    } catch (error) {
      const apiError = error as Error & { status?: number };
      if (apiError.status === 401) {
        clearSessionWithMessage("Session expired, please login again");
        return;
      }
      setIsAuthAdmin(false);
    } finally {
      setAuthChecked(true);
    }
  };

  useEffect(() => {
    setAuthChecked(false);
    void checkAdminAccess();
  }, [authToken]);

  useEffect(() => {
    if (!profileUserId && users.length > 0) {
      setProfileUserId(users[0].username);
    }
  }, [users, profileUserId]);

  const login = async () => {
    if (!loginUsername || !loginPassword) {
      return setMessage("username and password are required", true);
    }
    try {
      const tokenPayload = await api("/third/auth/token", {
        method: "POST",
        body: JSON.stringify({ username: loginUsername, password: loginPassword }),
      });
      const token = tokenPayload?.data?.accessToken;
      if (!token) {
        throw new Error("missing token in auth response");
      }
      setAuthToken(token);
      setSessionUser(loginUsername);
      localStorage.setItem("auth_token", token);
      localStorage.setItem("auth_username", loginUsername);
      setMessage(`Logged in as ${loginUsername}`);
    } catch (error) {
      setMessage(`Login failed: ${(error as Error).message}`, true);
    }
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_username");
    setAuthToken("");
    setSessionUser("");
    setUsers([]);
    setMessage("Logged out");
  };

  const createUser = async () => {
    if (!newUsername || !newPassword) return setMessage("username and password are required", true);
    try {
      await api("/admin/auth/users", {
        method: "POST",
        body: JSON.stringify({ username: newUsername, password: newPassword }),
      });
      setNewUsername("");
      setNewPassword("");
      setMessage(`User ${newUsername} created`);
      await loadUsers();
    } catch (error) {
      handleApiError("Create failed", error);
    }
  };

  const profilePayload = () => ({ appScope, role, context: context || null });

  const resetPassword = async () => {
    if (!resetUserRef || !resetPasswordValue) {
      return setMessage("user and password are required for reset", true);
    }
    try {
      await api(`/admin/auth/users/${resetUserRef}/password`, {
        method: "PATCH",
        body: JSON.stringify({ password: resetPasswordValue }),
      });
      setResetPasswordValue("");
      setMessage(`Password reset for ${resetUserRef}`);
      await loadUsers();
    } catch (error) {
      handleApiError("Password reset failed", error);
    }
  };

  const onScopeChange = (nextScope: string) => {
    setAppScope(nextScope);
    const roles = APP_SCOPE_ROLES[nextScope] || [];
    setRole(roles[0] || "");
  };

  const assignProfile = async () => {
    if (!profileUserId) return setMessage("userId is required for profile assignment", true);
    try {
      const payload = await api(`/admin/auth/users/${profileUserId}/profiles`, {
        method: "POST",
        body: JSON.stringify(profilePayload()),
      });
      setMessage(payload?.message || "Profile assigned");
      await loadUsers();
    } catch (error) {
      handleApiError("Assign failed", error);
    }
  };

  const revokeProfile = async () => {
    if (!profileUserId) return setMessage("userId is required for profile revoke", true);
    try {
      await api(`/admin/auth/users/${profileUserId}/profiles`, {
        method: "DELETE",
        body: JSON.stringify(profilePayload()),
      });
      setMessage("Profile revoked");
      await loadUsers();
    } catch (error) {
      handleApiError("Revoke failed", error);
    }
  };

  const removeProfileFromUser = async (user: User, profile: Profile) => {
    try {
      await api(`/admin/auth/users/${user.id}/profiles`, {
        method: "DELETE",
        body: JSON.stringify({
          appScope: profile.appScope,
          role: profile.role,
          context: profile.context || null,
        }),
      });
      setMessage(`Removed ${profile.appScope}/${profile.role} from ${user.username}`);
      await loadUsers();
    } catch (error) {
      handleApiError("Remove profile failed", error);
    }
  };

  const toggleSuspend = async (user: User) => {
    try {
      await api(`/admin/auth/users/${user.id}/suspended`, {
        method: "PATCH",
        body: JSON.stringify({ suspended: !user.suspended }),
      });
      setMessage(user.suspended ? "User unsuspended" : "User suspended");
      await loadUsers();
    } catch (error) {
      handleApiError("Suspend action failed", error);
    }
  };

  if (!authToken) {
    return (
      <main className="container">
        <h1>auth-app login</h1>
        <p className={isError ? "status error" : "status"}>{status}</p>
        <section className="card">
          <h2>Sign in</h2>
          <input value={loginUsername} onChange={(e) => setLoginUsername(e.target.value)} placeholder="username" />
          <input
            value={loginPassword}
            onChange={(e) => setLoginPassword(e.target.value)}
            placeholder="password"
            type="password"
          />
          <button onClick={login}>Login</button>
          <p>
            Demo users: <code>admin/admin123</code> or <code>alice/alice123</code>
          </p>
        </section>
      </main>
    );
  }

  if (!authChecked) {
    return (
      <main className="container">
        <h1>auth-app</h1>
        <p className="status">Checking permissions...</p>
      </main>
    );
  }

  if (!isAuthAdmin) {
    return (
      <main className="container">
        <h1>auth-app</h1>
        <p>
          Signed in as: <strong>{sessionUser}</strong> <button onClick={logout}>Logout</button>
        </p>
        <p className="status error">Access denied. `auth-app/auth-admin` profile is required.</p>
      </main>
    );
  }

  return (
    <main className="container">
      <h1>auth-app admin (React)</h1>
      <p>Signed in as: <strong>{sessionUser}</strong> <button onClick={logout}>Logout</button></p>
      <p className={isError ? "status error" : "status"}>{status}</p>

      <section className="card">
        <h2>Create user</h2>
        <input value={newUsername} onChange={(e) => setNewUsername(e.target.value)} placeholder="username" />
        <input
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          placeholder="password"
          type="password"
        />
        <button onClick={createUser}>Create user</button>
      </section>

      <section className="card">
        <h2>Reset password</h2>
        <label className="field-label">
          User ID or Username
          <input
            value={resetUserRef}
            onChange={(e) => setResetUserRef(e.target.value)}
            placeholder="userId or username"
          />
        </label>
        <label className="field-label">
          New Password
          <input
            value={resetPasswordValue}
            onChange={(e) => setResetPasswordValue(e.target.value)}
            placeholder="new password"
            type="password"
          />
        </label>
        <button onClick={resetPassword}>Reset password</button>
      </section>

      <section className="card">
        <h2>Assign/revoke profile</h2>
        <label className="field-label">
          User ID or Username
          <select value={profileUserId} onChange={(e) => setProfileUserId(e.target.value)}>
            {users.length === 0 ? (
              <option value="">No users available</option>
            ) : (
              users.map((u) => (
                <option key={u.id} value={u.username}>
                  {u.username} ({u.id})
                </option>
              ))
            )}
          </select>
        </label>
        <label className="field-label">
          App Scope
          <select value={appScope} onChange={(e) => onScopeChange(e.target.value)}>
            {Object.keys(APP_SCOPE_ROLES).map((scope) => (
              <option key={scope} value={scope}>
                {scope}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Role
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            {(APP_SCOPE_ROLES[appScope] || []).map((roleOption) => (
              <option key={roleOption} value={roleOption}>
                {roleOption}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Context (optional)
          <input value={context} onChange={(e) => setContext(e.target.value)} placeholder="context (optional)" />
        </label>
        <div className="row">
          <button onClick={assignProfile}>Assign</button>
          <button onClick={revokeProfile}>Revoke</button>
        </div>
      </section>

      <section className="card">
        <div className="row">
          <h2>Users</h2>
          <button onClick={loadUsers}>Refresh</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>ID</th>
              <th>Suspended</th>
              <th>Profiles</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.id}</td>
                <td>{u.suspended ? "yes" : "no"}</td>
                <td>
                  {u.profiles.length
                    ? u.profiles.map((p, idx) => (
                        <div key={`${u.id}-${p.appScope}-${p.role}-${p.context || "none"}-${idx}`} className="profile-row">
                          <span>{`${p.appScope}/${p.role}${p.context ? ` [${p.context}]` : ""}`}</span>
                          <button onClick={() => removeProfileFromUser(u, p)}>Remove</button>
                        </div>
                      ))
                    : "none"}
                </td>
                <td>
                  <button onClick={() => toggleSuspend(u)}>{u.suspended ? "Unsuspend" : "Suspend"}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
