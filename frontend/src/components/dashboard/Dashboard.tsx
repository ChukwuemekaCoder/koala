import { useCallback, useEffect, useState } from "react";
import {
  getFullPlan,
  getProjection,
  getStudentProfile,
  optimizeSchedule,
  type Projection,
  type ScheduleCourse,
  type Semester,
  type StudentProfile,
} from "../../lib/api";
import { SemesterTimeline, type SemesterNode } from "../SemesterTimeline";
import { AppHeader } from "./AppHeader";
import { MetricCards } from "./MetricCards";
import { SemesterOutlookRow } from "./SemesterOutlookRow";
import { SemesterCalendarGrid } from "./SemesterCalendarGrid";
import { CourseOverrideModal } from "./CourseOverrideModal";
import { AddCourseModal } from "./AddCourseModal";

interface DashboardProps {
  accessToken: string;
  onSignOut: () => void;
}

export function Dashboard({ accessToken, onSignOut }: DashboardProps) {
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [semesters, setSemesters] = useState<Semester[]>([]);
  const [projection, setProjection] = useState<Projection | null>(null);
  const [expandedTerm, setExpandedTerm] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overrideCourse, setOverrideCourse] = useState<ScheduleCourse | null>(null);
  const [addCourseOpen, setAddCourseOpen] = useState(false);
  const [showSwapHint, setShowSwapHint] = useState(false);

  const refreshPlan = useCallback(async () => {
    const [plan, proj] = await Promise.all([
      getFullPlan(accessToken),
      getProjection(accessToken),
    ]);
    setSemesters(plan.semesters);
    setProjection(proj);
  }, [accessToken]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [studentProfile, plan] = await Promise.all([
          getStudentProfile(accessToken),
          getFullPlan(accessToken),
        ]);

        let planSemesters = plan.semesters;
        if (planSemesters.length === 0) {
          const optimized = await optimizeSchedule(accessToken);
          planSemesters = optimized.semesters;
        }

        const proj = await getProjection(accessToken);

        if (cancelled) return;
        setProfile(studentProfile);
        setSemesters(planSemesters);
        setProjection(proj);
        setExpandedTerm(planSemesters[0]?.term ?? null);
      } catch {
        if (!cancelled) {
          setError("Couldn't load your schedule — try refreshing the page.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  if (loading) {
    return <div className="dashboard-page" />;
  }

  if (error || !profile || !projection) {
    return (
      <div className="dashboard-page">
        <div className="dashboard-inner">
          <p className="auth-error">{error ?? "Something went wrong."}</p>
        </div>
      </div>
    );
  }

  const currentTerm = semesters[0]?.term ?? null;
  const timelineNodes: SemesterNode[] = semesters.map((semester, index) => ({
    label: semester.term,
    status: index === 0 ? "current" : "future",
    flagged: semester.is_flagged,
  }));
  const expandedSemester =
    semesters.find((semester) => semester.term === expandedTerm) ?? null;

  return (
    <div className="dashboard-page">
      <div className="dashboard-inner">
        <AppHeader
          firstName={profile.first_name}
          lastName={profile.last_name}
          onSignOut={onSignOut}
        />

        <h1 className="dashboard-greeting">Welcome back, {profile.first_name}</h1>

        <div className="dashboard-timeline-wrap">
          {timelineNodes.length > 0 ? (
            <SemesterTimeline semesters={timelineNodes} />
          ) : (
            <p className="calendar-grid-empty">
              No schedule yet — declare your majors and minors to get started.
            </p>
          )}
        </div>

        <MetricCards projection={projection} />

        {semesters.length > 0 && (
          <>
            <h2 className="dashboard-section-heading">Your semesters</h2>
            <SemesterOutlookRow
              semesters={semesters}
              currentTerm={currentTerm ?? ""}
              expandedTerm={expandedTerm}
              onSelect={(term) => {
                setExpandedTerm(term);
                setShowSwapHint(false);
              }}
            />

            {expandedSemester && (
              <div className="card">
                <div className="semester-detail-header">
                  <p className="semester-detail-heading">{expandedSemester.term}</p>
                  <div className="semester-detail-actions">
                    <button
                      type="button"
                      className="btn-secondary btn-small"
                      onClick={() => setAddCourseOpen(true)}
                    >
                      Add a course
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-small"
                      onClick={() => setShowSwapHint((v) => !v)}
                    >
                      Swap a course
                    </button>
                  </div>
                </div>
                {showSwapHint && (
                  <p className="semester-detail-hint">
                    Click any course below to swap or remove it.
                  </p>
                )}
                <SemesterCalendarGrid
                  semester={expandedSemester}
                  onCourseClick={setOverrideCourse}
                />
              </div>
            )}
          </>
        )}
      </div>

      {overrideCourse && expandedSemester && (
        <CourseOverrideModal
          accessToken={accessToken}
          term={expandedSemester.term}
          course={overrideCourse}
          semesterTotalCredits={expandedSemester.total_credits}
          onClose={() => setOverrideCourse(null)}
          onSaved={() => {
            setOverrideCourse(null);
            refreshPlan();
          }}
        />
      )}

      {addCourseOpen && expandedSemester && (
        <AddCourseModal
          accessToken={accessToken}
          term={expandedSemester.term}
          semesterTotalCredits={expandedSemester.total_credits}
          onClose={() => setAddCourseOpen(false)}
          onSaved={() => {
            setAddCourseOpen(false);
            refreshPlan();
          }}
        />
      )}
    </div>
  );
}
