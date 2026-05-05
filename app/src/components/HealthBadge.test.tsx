import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HealthBadge } from "./HealthBadge";

describe("HealthBadge", () => {
  it("renders OK when ok=true", () => {
    render(<HealthBadge ok={true} />);
    const badge = screen.getByTestId("health-badge");
    expect(badge).toHaveTextContent("OK");
    expect(badge).toHaveClass("text-green-600");
  });

  it("renders FAIL when ok=false", () => {
    render(<HealthBadge ok={false} />);
    const badge = screen.getByTestId("health-badge");
    expect(badge).toHaveTextContent("FAIL");
    expect(badge).toHaveClass("text-red-600");
  });
});
