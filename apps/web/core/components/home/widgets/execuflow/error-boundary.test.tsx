/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExecuFlowErrorBoundary } from "./error-boundary";

// Component that throws an error for testing
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error("Test error");
  }
  return <div>Working component</div>;
};

describe("ExecuFlowErrorBoundary", () => {
  beforeEach(() => {
    // Suppress console.error for cleaner test output
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  describe("when no error occurs", () => {
    it("should render children normally", () => {
      render(
        <ExecuFlowErrorBoundary widgetName="Test Widget">
          <div>Test content</div>
        </ExecuFlowErrorBoundary>
      );

      expect(screen.getByText("Test content")).toBeInTheDocument();
    });
  });

  describe("when error is caught", () => {
    it("should display error UI with widget name", () => {
      render(
        <ExecuFlowErrorBoundary widgetName="Focus Timer">
          <ThrowError shouldThrow={true} />
        </ExecuFlowErrorBoundary>
      );

      expect(screen.getByText(/Focus Timer encountered an error/i)).toBeInTheDocument();
    });

    it("should display try again button", () => {
      render(
        <ExecuFlowErrorBoundary widgetName="Test Widget">
          <ThrowError shouldThrow={true} />
        </ExecuFlowErrorBoundary>
      );

      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    });

    it("should display AlertTriangle icon", () => {
      const { container } = render(
        <ExecuFlowErrorBoundary widgetName="Test Widget">
          <ThrowError shouldThrow={true} />
        </ExecuFlowErrorBoundary>
      );

      // lucide-react adds a svg element with specific attributes
      const alertIcon = container.querySelector("svg");
      expect(alertIcon).toBeInTheDocument();
    });

    it("should call console.error with error details", () => {
      const consoleErrorSpy = vi.spyOn(console, "error");

      render(
        <ExecuFlowErrorBoundary widgetName="Test Widget">
          <ThrowError shouldThrow={true} />
        </ExecuFlowErrorBoundary>
      );

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining("ExecuFlow Test Widget error:"),
        expect.any(Error),
        expect.any(Object)
      );
    });
  });

  describe("reset functionality", () => {
    it("should reset error state when try again is clicked", async () => {
      const user = userEvent.setup();
      let shouldThrow = true;

      const { rerender } = render(
        <ExecuFlowErrorBoundary widgetName="Test Widget">
          <ThrowError shouldThrow={shouldThrow} />
        </ExecuFlowErrorBoundary>
      );

      expect(screen.getByText(/encountered an error/i)).toBeInTheDocument();

      // Fix the error
      shouldThrow = false;

      // Click try again
      const tryAgainButton = screen.getByRole("button", { name: /try again/i });
      await user.click(tryAgainButton);

      // Re-render with fixed component
      rerender(
        <ExecuFlowErrorBoundary widgetName="Test Widget">
          <ThrowError shouldThrow={shouldThrow} />
        </ExecuFlowErrorBoundary>
      );

      expect(screen.getByText("Working component")).toBeInTheDocument();
    });

    it("should call optional onReset callback when reset button is clicked", async () => {
      const user = userEvent.setup();
      const onResetMock = vi.fn();

      render(
        <ExecuFlowErrorBoundary widgetName="Test Widget" onReset={onResetMock}>
          <ThrowError shouldThrow={true} />
        </ExecuFlowErrorBoundary>
      );

      const tryAgainButton = screen.getByRole("button", { name: /try again/i });
      await user.click(tryAgainButton);

      expect(onResetMock).toHaveBeenCalledTimes(1);
    });
  });

  describe("custom fallback", () => {
    it("should render custom fallback when provided", () => {
      const customFallback = <div>Custom error message</div>;

      render(
        <ExecuFlowErrorBoundary widgetName="Test Widget" fallback={customFallback}>
          <ThrowError shouldThrow={true} />
        </ExecuFlowErrorBoundary>
      );

      expect(screen.getByText("Custom error message")).toBeInTheDocument();
      expect(screen.queryByText(/encountered an error/i)).not.toBeInTheDocument();
    });
  });

  describe("error styling", () => {
    it("should apply red border and background styles", () => {
      const { container } = render(
        <ExecuFlowErrorBoundary widgetName="Test Widget">
          <ThrowError shouldThrow={true} />
        </ExecuFlowErrorBoundary>
      );

      const errorContainer = container.querySelector(".border-red-200");
      expect(errorContainer).toBeInTheDocument();
      expect(errorContainer).toHaveClass("bg-red-50");
    });
  });
});
