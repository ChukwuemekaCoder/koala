import type { SectionMeeting } from "./api";

export function formatMeetings(meetings: SectionMeeting[]): string {
  return meetings
    .map((m) => `${m.days} ${m.start_time.slice(0, 5)}–${m.end_time.slice(0, 5)}`)
    .join(", ");
}
