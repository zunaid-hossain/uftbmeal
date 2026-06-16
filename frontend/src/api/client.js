import axios from "axios";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  timeout: 10000,
});

export async function api(path, options = {}) {
  const token = localStorage.getItem("uftb_token");
  try {
    const response = await http.request({
      url: path,
      method: options.method || "GET",
      data: options.body ? JSON.parse(options.body) : undefined,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
    return response.status === 204 ? null : response.data;
  } catch (error) {
    const detail = error.response?.data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(". ")
      : detail;
    throw new Error(message || (error.request ? "Cannot connect to the server" : error.message));
  }
}

export function saveSession(data) {
  localStorage.setItem("uftb_token", data.access_token);
  localStorage.setItem("uftb_user", JSON.stringify(data.user));
}

export function clearSession() {
  localStorage.removeItem("uftb_token");
  localStorage.removeItem("uftb_user");
}

export function storedUser() {
  try {
    return JSON.parse(localStorage.getItem("uftb_user"));
  } catch {
    return null;
  }
}
