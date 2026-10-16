import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('UI error:', error, info?.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="boot">
          <p className="banner" style={{ margin: 0 }}>
            Something went wrong rendering the interface — {this.state.error.message}
          </p>
          <button
            className="btn"
            style={{ marginTop: 14 }}
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
