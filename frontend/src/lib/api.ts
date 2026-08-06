const apiUrl = import.meta.env.VITE_API_URL;

export async function createStudentProfile(
  accessToken: string,
  firstName: string,
  lastName: string,
): Promise<void> {
  const res = await fetch(`${apiUrl}/students/me`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ first_name: firstName, last_name: lastName }),
  });
  if (!res.ok) {
    throw new Error("Couldn't finish setting up your account — try again.");
  }
}
