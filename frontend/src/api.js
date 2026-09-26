const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export async function getProfile(hcpId) {
  const response = await fetch(
    `${API_BASE_URL}/profile/${hcpId}`
  );

  if (!response.ok) {
    throw new Error("Failed to load HCP profile");
  }

  return response.json();
}

export async function getDrugSummary(drugId, hcpId) {
  const response = await fetch(
    `${API_BASE_URL}/drug/${drugId}/summary?hcp_id=${hcpId}`
  );

  if (!response.ok) {
    throw new Error("Failed to load drug information");
  }

  return response.json();
}

export async function askDrugQuestion(drugId, hcpId, query) {
  const response = await fetch(
    `${API_BASE_URL}/drug/${drugId}/ask`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        hcp_id: hcpId,
        query,
      }),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));

    throw new Error(
      error.detail || "Failed to get an answer"
    );
  }

  return response.json();
}