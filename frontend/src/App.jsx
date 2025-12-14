import { useState } from 'react'
import ScheduleInput from './components/ScheduleInput'
import ScheduleResults from './components/ScheduleResults'
import GanttChart from './components/GanttChart'
import KPIDashboard from './components/KPIDashboard'

function App() {
  const [schedule, setSchedule] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSchedule = async (inputData) => {
    setLoading(true)
    setError(null)
    setSchedule(null)

    try {
      const response = await fetch('/api/schedule', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(inputData)
      })

      const data = await response.json()

      if (!response.ok) {
        if (data.error) {
          setError(`${data.error}: ${data.why.join(', ')}`)
        } else {
          setError('Failed to generate schedule')
        }
        return
      }

      setSchedule(data)
    } catch (err) {
      setError(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>🏭 Harmony Production Scheduler</h1>
        <p>Constraint-based scheduling with multi-tenant support</p>
      </header>

      <div className="container">
        <div className="grid grid-2">
          <ScheduleInput onSchedule={handleSchedule} loading={loading} />

          {error && (
            <div className="card">
              <div className="error">{error}</div>
            </div>
          )}

          {loading && (
            <div className="card">
              <div className="loading">
                <div className="spinner"></div>
                <p style={{ marginTop: '1rem' }}>Generating schedule...</p>
              </div>
            </div>
          )}

          {schedule && !loading && (
            <>
              <KPIDashboard kpis={schedule.kpis} />
            </>
          )}
        </div>

        {schedule && !loading && (
          <div className="grid">
            <GanttChart assignments={schedule.assignments} />
            <ScheduleResults assignments={schedule.assignments} />

            <div className="card">
              <h2 className="card-title">
                Output JSON
                <span style={{fontSize: '0.9rem', fontWeight: 'normal', color: '#666', marginLeft: '1rem'}}>
                  ({schedule.assignments.length} assignments received)
                </span>
              </h2>
              <pre style={{
                background: '#f7fafc',
                padding: '1rem',
                borderRadius: '0.5rem',
                overflow: 'auto',
                maxHeight: '400px',
                fontSize: '0.75rem',
                lineHeight: '1.5'
              }}>
                {JSON.stringify(schedule, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
