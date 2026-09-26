const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function request(url, options = {}) {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Timezone": Intl.DateTimeFormat().resolvedOptions().timeZone,
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

export async function deleteChat(hcpId, conversationId) {
  return request(
    `/profile/${hcpId}/chats/${encodeURIComponent(conversationId)}`,
    {
      method: "DELETE",
      headers: authHeaders(),
    }
  );
}

export async function getDrugSummary(drugId, hcpId) {
  return request(
    `/drug/${drugId}/summary?hcp_id=${encodeURIComponent(hcpId)}`,
    {
      headers: authHeaders(),
    }
  );
}

export async function askDrugQuestion(
  drugId,
  hcpId,
  query,
  conversationId = null
) {
  return request(`/drug/${drugId}/ask`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      hcp_id: hcpId,
      query,
      conversation_id: conversationId,
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

export async function getPatients(hcpId) {
  return request(`/profile/${hcpId}/patients`, {
    headers: authHeaders(),
  });
}

export async function getPatient(hcpId, patientId) {
  return request(
    `/profile/${hcpId}/patients/${encodeURIComponent(patientId)}`,
    {
      headers: authHeaders(),
    }
  );
}

export async function createPatient(hcpId, patient) {
  const data = await request(`/profile/${hcpId}/patients`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(patient),
  });

  return data.patient;
}

export async function renameChat(hcpId, conversationId, title) {
  return request(
    `/profile/${hcpId}/chats/${encodeURIComponent(conversationId)}`,
    {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ title }),
    }
  );
}