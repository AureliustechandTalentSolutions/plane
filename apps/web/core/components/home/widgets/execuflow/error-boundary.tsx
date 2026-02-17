/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

"use client";

import { Component, createRef } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Loader2 } from "lucide-react";
import * as Sentry from "@sentry/react-router";

// ---------------------------------------------------------------------------
// Retry constants
// ---------------------------------------------------------------------------

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 8000;

/**
 * Returns an exponential backoff delay with ±25% jitter.
 * Sequence (without jitter): 1 s → 2 s → 4 s (capped at 8 s).
 */
const getRetryDelay = (retryCount: number): number => {
  const delay = Math.min(BASE_DELAY_MS * Math.pow(2, retryCount), MAX_DELAY_MS);
  return delay + Math.random() * delay * 0.25;
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  widgetName: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  retryCount: number;
  isRetrying: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export class ExecuFlowErrorBoundary extends Component<Props, State> {
  private errorRef = createRef<HTMLDivElement>();

  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, retryCount: 0, isRetrying: false };
  }

  static getDerivedStateFromError(error: Error): Pick<State, "hasError" | "error"> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`ExecuFlow ${this.props.widgetName} error:`, error, errorInfo);

    Sentry.withScope((scope) => {
      scope.setTag("widget", this.props.widgetName);
      scope.setTag("component", "ExecuFlowErrorBoundary");
      scope.setLevel("error");
      scope.setExtra("componentStack", errorInfo.componentStack);
      scope.setExtra("retryCount", this.state.retryCount);
      Sentry.captureException(error);
    });
  }

  componentDidUpdate(_prevProps: Props, prevState: State) {
    // Move focus to the error container when an error first appears so that
    // screen readers announce it immediately.
    if (this.state.hasError && !prevState.hasError && this.errorRef.current) {
      this.errorRef.current.focus();
    }
  }

  handleRetry = async () => {
    if (this.state.retryCount >= MAX_RETRIES || this.state.isRetrying) return;

    this.setState({ isRetrying: true });

    const delay = getRetryDelay(this.state.retryCount);
    await new Promise<void>((resolve) => setTimeout(resolve, delay));

    this.setState((prev) => ({
      hasError: false,
      error: null,
      retryCount: prev.retryCount + 1,
      isRetrying: false,
    }));

    this.props.onReset?.();
  };

  render() {
    const { hasError, retryCount, isRetrying } = this.state;

    if (hasError) {
      if (this.props.fallback) return this.props.fallback;

      const retriesExhausted = retryCount >= MAX_RETRIES;

      return (
        <div
          ref={this.errorRef}
          role="alert"
          tabIndex={-1}
          className="rounded-lg border border-red-200 bg-red-50 p-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500"
        >
          {/* Header */}
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" aria-hidden="true" />
            <span className="text-13 font-medium text-red-700">
              {this.props.widgetName} encountered an error
            </span>
          </div>

          {/* Retry progress indicator */}
          {retryCount > 0 && !retriesExhausted && (
            <p className="text-12 text-red-600 mb-2" aria-live="polite">
              Retry attempt {retryCount} of {MAX_RETRIES}
            </p>
          )}

          {/* Persisted error message after all retries are exhausted */}
          {retriesExhausted && (
            <p className="text-12 text-red-600 mb-2" aria-live="assertive">
              Error persists after {MAX_RETRIES} attempts. Please refresh the page or contact
              support.
            </p>
          )}

          {/* Retry button */}
          {!retriesExhausted && (
            <button
              onClick={this.handleRetry}
              disabled={isRetrying}
              aria-disabled={isRetrying ? "true" : "false"}
              aria-label={
                isRetrying
                  ? "Retrying, please wait"
                  : `Try again (attempt ${retryCount + 1} of ${MAX_RETRIES})`
              }
              className="flex items-center gap-1 min-h-[44px] px-3 py-2 text-12 text-red-600 hover:text-red-800 rounded focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isRetrying ? (
                <>
                  <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
                  Retrying…
                </>
              ) : (
                <>
                  <RefreshCw className="h-3 w-3" aria-hidden="true" />
                  Try again
                </>
              )}
            </button>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
