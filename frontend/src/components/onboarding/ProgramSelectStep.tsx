import { useEffect, useMemo, useState } from "react";
import { IconInfoCircle, IconX } from "@tabler/icons-react";
import {
  declarePrograms,
  getDeclaredPrograms,
  getPrograms,
  type Program,
} from "../../lib/api";
import { OnboardingStepHeader } from "./OnboardingStepHeader";

interface ProgramSelectStepProps {
  accessToken: string;
  onContinue: () => void;
}

export function ProgramSelectStep({ accessToken, onContinue }: ProgramSelectStepProps) {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getPrograms(accessToken), getDeclaredPrograms(accessToken)])
      .then(([catalogRes, declaredRes]) => {
        setPrograms(catalogRes.programs);

        // Re-hydration for Back navigation: split what's already declared
        // into explicit picks vs. auto-required minors, so the auto ones
        // still render as the outlined chip variant instead of a normal
        // removable one — same distinction the search-select flow itself
        // maintains, just derived from saved state instead of a fresh pick.
        const declaredIds = new Set(declaredRes.programs.map((p) => p.program_id));
        const declaredMajorIds = new Set(
          catalogRes.programs
            .filter((p) => p.type === "major" && declaredIds.has(p.id))
            .map((p) => p.id),
        );
        const explicitIds = new Set(
          [...declaredIds].filter((id) => {
            const program = catalogRes.programs.find((p) => p.id === id);
            return !(
              program?.required_by_program_id &&
              declaredMajorIds.has(program.required_by_program_id)
            );
          }),
        );
        setSelectedIds(explicitIds);
      })
      .catch(() => setError("Couldn't load the program list — try refreshing."))
      .finally(() => setLoading(false));
  }, [accessToken]);

  const selectedMajorIds = useMemo(
    () =>
      new Set(
        programs
          .filter((p) => p.type === "major" && selectedIds.has(p.id))
          .map((p) => p.id),
      ),
    [programs, selectedIds],
  );

  const autoRequired = useMemo(
    () =>
      programs.filter(
        (p) =>
          p.required_by_program_id &&
          selectedMajorIds.has(p.required_by_program_id) &&
          !selectedIds.has(p.id),
      ),
    [programs, selectedMajorIds, selectedIds],
  );

  const autoRequiredIds = useMemo(
    () => new Set(autoRequired.map((p) => p.id)),
    [autoRequired],
  );

  const results = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return [];
    return programs.filter(
      (p) =>
        !selectedIds.has(p.id) &&
        !autoRequiredIds.has(p.id) &&
        p.name.toLowerCase().includes(query),
    );
  }, [programs, search, selectedIds, autoRequiredIds]);

  const majorResults = results.filter((p) => p.type === "major");
  const minorResults = results.filter((p) => p.type === "minor");

  function select(id: string) {
    setSelectedIds((prev) => new Set(prev).add(id));
    setSearch("");
  }

  function remove(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }

  async function handleContinue() {
    setSaving(true);
    setError(null);
    try {
      await declarePrograms(accessToken, [...selectedIds, ...autoRequiredIds]);
      onContinue();
    } catch {
      setError("Couldn't save your majors and minors — try again.");
    } finally {
      setSaving(false);
    }
  }

  const hasSelection = selectedIds.size > 0;

  return (
    <div>
      <OnboardingStepHeader step={1} />
      <h1 className="onboarding-heading">Your majors and minors</h1>
      <p className="onboarding-subtext">
        Search to add each program you're declared in. We'll add any minor your
        major structurally requires automatically.
      </p>

      {(selectedIds.size > 0 || autoRequired.length > 0) && (
        <div className="chip-row">
          {programs
            .filter((p) => selectedIds.has(p.id))
            .map((p) => (
              <span className="chip chip--solid" key={p.id}>
                <span className="chip-label">{p.name}</span>
                <button
                  type="button"
                  className="chip-remove"
                  onClick={() => remove(p.id)}
                  aria-label={`Remove ${p.name}`}
                >
                  <IconX size={12} stroke={2.5} />
                </button>
              </span>
            ))}
          {autoRequired.map((p) => (
            <span className="chip chip--outlined" key={p.id}>
              <IconInfoCircle size={14} stroke={2} className="chip-info-icon" />
              <span className="chip-label chip-label--outlined">{p.name}</span>
            </span>
          ))}
        </div>
      )}

      {autoRequired.length > 0 && (
        <p className="onboarding-subtext chip-explanation">
          Outlined chips are required by your major — added automatically, not
          removable here.
        </p>
      )}

      <div className="search-field">
        <input
          type="text"
          placeholder="Search majors and minors…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          disabled={loading}
        />
        {results.length > 0 && (
          <div className="search-results">
            {majorResults.length > 0 && (
              <>
                <p className="search-results-group-label">Majors</p>
                {majorResults.map((p) => (
                  <button
                    type="button"
                    className="search-result-row"
                    key={p.id}
                    onClick={() => select(p.id)}
                  >
                    {p.name}
                  </button>
                ))}
              </>
            )}
            {minorResults.length > 0 && (
              <>
                <p className="search-results-group-label">Minors</p>
                {minorResults.map((p) => (
                  <button
                    type="button"
                    className="search-result-row"
                    key={p.id}
                    onClick={() => select(p.id)}
                  >
                    {p.name}
                  </button>
                ))}
              </>
            )}
          </div>
        )}
      </div>

      {error && <p className="auth-error">{error}</p>}

      <div className="onboarding-actions">
        <button
          type="button"
          className="btn-primary"
          onClick={handleContinue}
          disabled={!hasSelection || saving || loading}
        >
          {saving ? "Saving…" : "Continue"}
        </button>
      </div>
    </div>
  );
}
