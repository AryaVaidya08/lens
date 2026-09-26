const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function request(url, options = {}) {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      error.detail || `Request failed (${response.status})`
    );
  }

  return response.json();
}

export async function login(email, password) {
  const data = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  localStorage.setItem("lens_session_token", data.session_token);
  localStorage.setItem("lens_hcp_id", data.hcp_id);
  return data;
}

function authHeaders() {
  const token = localStorage.getItem("lens_session_token");

  return token
    ? { Authorization: `Bearer ${token}` }
    : {};
}

export async function getProfile(hcpId) {
  return request(`/profile/${hcpId}`, {
    headers: authHeaders(),
  });
}

export async function getChats(hcpId) {
  const data = await request(`/profile/${hcpId}/chats`, {
    headers: authHeaders(),
  });

  return data.chats;
}

export async function getDrugSummary(drugId, hcpId) {
  return request(
    `/drug/${drugId}/summary?hcp_id=${encodeURIComponent(hcpId)}`,
    {
      headers: authHeaders(),
    }
  );
}

export async function askDrugQuestion(drugId, hcpId, query) {
  return request(`/drug/${drugId}/ask`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      hcp_id: hcpId,
      query,
    }),
  });
}

export async function logEngagement(hcpId, drugId) {
  return request("/engagement/log", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      hcp_id: hcpId,
      drug_id: drugId,
    }),
  });
}