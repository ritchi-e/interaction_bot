export function formatDuration(seconds: number | null | undefined) {
  if (seconds == null) return "—";
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  if (minutes === 0) return `${rest}s`;
  return `${minutes}m ${rest}s`;
}

export function endedByLabel(attempt: { ended_by?: string; end_reason?: string } | undefined) {
  if (!attempt) return "—";
  if (attempt.ended_by === "agent") return "Agent";
  if (attempt.ended_by === "caller") return "Caller";
  if (attempt.end_reason) return attempt.end_reason.replaceAll("_", " ");
  return "—";
}

export function latestAttempt<T>(attempts: T[]) {
  return attempts[attempts.length - 1];
}
