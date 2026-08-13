const apiUrl = import.meta.env.VITE_API_URL;

async function apiFetch<T>(
  path: string,
  accessToken: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${apiUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...options.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`Request to ${path} failed (${res.status})`);
  }
  return res.json();
}

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

export interface StudentProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  class_standing: string | null;
  current_term: string | null;
  has_completed_tutorial: boolean;
  onboarding_complete: boolean;
}

export async function getStudentProfile(accessToken: string): Promise<StudentProfile> {
  return apiFetch<StudentProfile>("/students/me", accessToken);
}

export interface SectionMeeting {
  days: string;
  start_time: string;
  end_time: string;
}

export interface ScheduleCourse {
  course_id: string;
  code: string;
  title: string;
  credit_hours: number;
  category: "major" | "minor" | "gen_ed";
  section_id: string;
  meetings: SectionMeeting[];
  is_locked: boolean;
  is_flagged: boolean;
  flag_reason: string | null;
}

export interface Semester {
  term: string;
  total_credits: number;
  is_flagged: boolean;
  flag_reason: string | null;
  courses: ScheduleCourse[];
  feasible?: boolean;
}

export interface Projection {
  credits_taken: number;
  credits_in_progress: number;
  credits_remaining: number;
  degree_percent: number;
  projected_graduation: string | null;
}

export async function getFullPlan(
  accessToken: string,
): Promise<{ semesters: Semester[] }> {
  return apiFetch("/schedule/me/plan", accessToken);
}

export async function optimizeSchedule(
  accessToken: string,
): Promise<{ graduated: boolean; semesters: Semester[] }> {
  return apiFetch("/schedule/optimize", accessToken, { method: "POST" });
}

export async function getProjection(accessToken: string): Promise<Projection> {
  return apiFetch("/schedule/me/projection", accessToken);
}

export async function overrideSchedule(
  accessToken: string,
  body: { term: string; add_section_id?: string; remove_course_id?: string },
): Promise<{ graduated: boolean; semesters: Semester[] }> {
  return apiFetch("/schedule/override", accessToken, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getAddableCourses(
  accessToken: string,
  term: string,
): Promise<{ courses: ScheduleCourse[] }> {
  return apiFetch(`/schedule/me/addable?term=${encodeURIComponent(term)}`, accessToken);
}

export interface Program {
  id: string;
  name: string;
  type: "major" | "minor";
  department: string | null;
  required_by_program_id: string | null;
}

export async function getPrograms(accessToken: string): Promise<{ programs: Program[] }> {
  return apiFetch("/programs", accessToken);
}

export async function declarePrograms(
  accessToken: string,
  programIds: string[],
): Promise<void> {
  await apiFetch("/students/me/programs", accessToken, {
    method: "POST",
    body: JSON.stringify({ programs: programIds.map((program_id) => ({ program_id })) }),
  });
}

export async function updateStandingTerm(
  accessToken: string,
  body: { class_standing?: string; current_term?: string },
): Promise<StudentProfile> {
  return apiFetch("/students/me", accessToken, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export type ProgressStatus = "done" | "in_progress" | "not_taken";

export interface CourseHistoryEntry {
  course_id: string;
  code: string;
  title: string;
  credit_hours: number;
  category: "major" | "minor" | "gen_ed";
  status: ProgressStatus;
}

export async function getCourseHistory(
  accessToken: string,
): Promise<{ courses: CourseHistoryEntry[] }> {
  return apiFetch("/students/me/course-history", accessToken);
}

export async function confirmProgress(
  accessToken: string,
  progress: { course_id: string; status: ProgressStatus }[],
): Promise<void> {
  await apiFetch("/students/me/progress", accessToken, {
    method: "POST",
    body: JSON.stringify({ progress }),
  });
}

export interface CourseSection {
  section_id: string;
  meetings: SectionMeeting[];
}

export async function getSections(
  accessToken: string,
  courseId: string,
  term: string,
): Promise<{ sections: CourseSection[] }> {
  return apiFetch(
    `/courses/${courseId}/sections?term=${encodeURIComponent(term)}`,
    accessToken,
  );
}
