export default function ScheduleResults({ assignments }) {
  const formatTime = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }

  // Group by product
  const byProduct = assignments.reduce((acc, a) => {
    if (!acc[a.product]) acc[a.product] = []
    acc[a.product].push(a)
    return acc
  }, {})

  return (
    <div className="card">
      <h2 className="card-title">Schedule Details</h2>

      <div style={{overflowX: 'auto'}}>
        <table style={{width: '100%', fontSize: '0.875rem', borderCollapse: 'collapse'}}>
          <thead>
            <tr style={{borderBottom: '2px solid #e2e8f0', textAlign: 'left'}}>
              <th style={{padding: '0.75rem', fontWeight: 600}}>Product</th>
              <th style={{padding: '0.75rem', fontWeight: 600}}>Operation</th>
              <th style={{padding: '0.75rem', fontWeight: 600}}>Resource</th>
              <th style={{padding: '0.75rem', fontWeight: 600}}>Start</th>
              <th style={{padding: '0.75rem', fontWeight: 600}}>End</th>
              <th style={{padding: '0.75rem', fontWeight: 600}}>Duration</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(byProduct).map(([product, tasks]) =>
              tasks.map((task, idx) => {
                const duration = Math.round((new Date(task.end) - new Date(task.start)) / 60000)
                return (
                  <tr
                    key={`${product}-${idx}`}
                    style={{
                      borderBottom: '1px solid #f7fafc',
                      background: idx === 0 ? '#f7fafc' : 'white'
                    }}
                  >
                    <td style={{padding: '0.75rem', fontWeight: idx === 0 ? 600 : 400}}>
                      {idx === 0 ? product : ''}
                    </td>
                    <td style={{padding: '0.75rem'}}>{task.op}</td>
                    <td style={{padding: '0.75rem'}}>{task.resource}</td>
                    <td style={{padding: '0.75rem'}}>{formatTime(task.start)}</td>
                    <td style={{padding: '0.75rem'}}>{formatTime(task.end)}</td>
                    <td style={{padding: '0.75rem'}}>{duration} min</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {assignments.length === 0 && (
        <p style={{textAlign: 'center', color: '#a0aec0', padding: '2rem'}}>
          No assignments to display
        </p>
      )}
    </div>
  )
}
