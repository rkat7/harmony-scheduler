import { useMemo } from 'react'

export default function GanttChart({ assignments }) {
  const { resources, timeline, minTime, maxTime } = useMemo(() => {
    if (!assignments || assignments.length === 0) return { resources: {}, timeline: [], minTime: 0, maxTime: 0 }

    // Group by resource
    const resourceMap = {}
    let minTime = Infinity
    let maxTime = -Infinity

    assignments.forEach(a => {
      if (!resourceMap[a.resource]) {
        resourceMap[a.resource] = []
      }

      const start = new Date(a.start).getTime()
      const end = new Date(a.end).getTime()

      resourceMap[a.resource].push({
        ...a,
        startTime: start,
        endTime: end,
        startDate: new Date(a.start),
        endDate: new Date(a.end)
      })

      minTime = Math.min(minTime, start)
      maxTime = Math.max(maxTime, end)
    })

    return { resources: resourceMap, minTime, maxTime }
  }, [assignments])

  const timeRange = maxTime - minTime

  const getBarPosition = (startTime, endTime) => {
    const left = ((startTime - minTime) / timeRange) * 100
    const width = ((endTime - startTime) / timeRange) * 100
    return { left: `${left}%`, width: `${width}%` }
  }

  const getBarColor = (product) => {
    // Generate consistent color based on product ID
    const hash = product.split('').reduce((acc, char) => char.charCodeAt(0) + ((acc << 5) - acc), 0)
    const hue = Math.abs(hash) % 360
    return `hsl(${hue}, 70%, 60%)`
  }

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
  }

  return (
    <div className="card">
      <h2 className="card-title">Gantt Chart - Resource Schedule</h2>

      <div className="gantt-container">
        {Object.entries(resources).map(([resourceId, tasks]) => (
          <div key={resourceId} className="gantt-row">
            <div className="gantt-label">{resourceId}</div>
            <div className="gantt-timeline">
              {tasks.map((task, idx) => {
                const style = {
                  ...getBarPosition(task.startTime, task.endTime),
                  background: getBarColor(task.product)
                }
                return (
                  <div
                    key={idx}
                    className="gantt-bar"
                    style={style}
                    title={`${task.product} - ${task.op}\n${formatTime(task.startDate)} - ${formatTime(task.endDate)}`}
                  >
                    <span style={{overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                      {task.product}/{task.op}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {Object.keys(resources).length === 0 && (
        <p style={{textAlign: 'center', color: '#a0aec0', padding: '2rem'}}>
          No schedule data to display
        </p>
      )}
    </div>
  )
}
