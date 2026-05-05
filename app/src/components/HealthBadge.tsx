type Props = { ok: boolean };

export function HealthBadge({ ok }: Props) {
  return (
    <span data-testid="health-badge" className={ok ? "text-green-600" : "text-red-600"}>
      {ok ? "OK" : "FAIL"}
    </span>
  );
}
