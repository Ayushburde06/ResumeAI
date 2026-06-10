import { Component, type ErrorInfo, type ReactNode } from 'react'
import { RefreshCw, TriangleAlert } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
}

export default class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('App error boundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-50 to-white px-4">
          <div className="max-w-md w-full rounded-3xl border border-red-100 bg-white shadow-xl p-6 text-center">
            <div className="mx-auto w-12 h-12 rounded-2xl bg-red-50 flex items-center justify-center text-red-600 mb-4">
              <TriangleAlert className="w-6 h-6" />
            </div>
            <h1 className="text-xl font-bold text-gray-900">Something broke on this page</h1>
            <p className="text-sm text-gray-500 mt-2">
              A frontend error stopped the dashboard from rendering. Refreshing usually clears it after a redeploy.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-600 text-white font-medium hover:bg-violet-500 transition"
            >
              <RefreshCw className="w-4 h-4" />
              Reload page
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
