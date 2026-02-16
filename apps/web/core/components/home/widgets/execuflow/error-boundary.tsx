/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

"use client";

import { Component, createRef } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  widgetName: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ExecuFlowErrorBoundary extends Component<Props, State> {
  private errorRef = createRef<HTMLDivElement>();

  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`ExecuFlow ${this.props.widgetName} error:`, error, errorInfo);
    // Optional: Send to error tracking service
  }

  componentDidUpdate(_prevProps: Props, prevState: State) {
    // Move focus to error message when error appears for screen reader announcement
    if (this.state.hasError && !prevState.hasError && this.errorRef.current) {
      this.errorRef.current.focus();
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div
            ref={this.errorRef}
            role="alert"
            tabIndex={-1}
            className="rounded-lg border border-red-200 bg-red-50 p-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500"
          >
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4 text-red-500" aria-hidden="true" />
              <span className="text-13 font-medium text-red-700">{this.props.widgetName} encountered an error</span>
            </div>
            <button
              onClick={this.handleReset}
              className="flex items-center gap-1 min-h-[44px] px-3 py-2 text-12 text-red-600 hover:text-red-800 rounded focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500"
            >
              <RefreshCw className="h-3 w-3" aria-hidden="true" /> Try again
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
