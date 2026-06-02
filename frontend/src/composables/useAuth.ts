import { ref, computed } from "vue";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const TOKEN_KEY = "comp-org-review-token";
const USER_KEY = "comp-org-review-user";

interface AuthUser {
  id: number;
  student_id: string;
  nickname: string | null;
  created_at: string;
}

const token = ref<string | null>(localStorage.getItem(TOKEN_KEY));
const user = ref<AuthUser | null>(JSON.parse(localStorage.getItem(USER_KEY) ?? "null"));

export function useAuth() {
  const isAuthenticated = computed(() => !!token.value);

  async function register(studentId: string, password: string, nickname?: string) {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId, password, nickname: nickname || null }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "注册失败" }));
      throw new Error(err.detail ?? "注册失败");
    }
    const data = await res.json();
    token.value = data.access_token;
    localStorage.setItem(TOKEN_KEY, data.access_token);
    await fetchUser();
  }

  async function login(studentId: string, password: string) {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "登录失败" }));
      throw new Error(err.detail ?? "登录失败");
    }
    const data = await res.json();
    token.value = data.access_token;
    localStorage.setItem(TOKEN_KEY, data.access_token);
    await fetchUser();
  }

  async function fetchUser() {
    if (!token.value) return;
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token.value}` },
      });
      if (!res.ok) {
        logout();
        return;
      }
      user.value = await res.json();
      localStorage.setItem(USER_KEY, JSON.stringify(user.value));
    } catch {
      logout();
    }
  }

  function logout() {
    token.value = null;
    user.value = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function getToken(): string | null {
    return token.value;
  }

  return {
    token,
    user,
    isAuthenticated,
    register,
    login,
    logout,
    fetchUser,
    getToken,
  };
}
