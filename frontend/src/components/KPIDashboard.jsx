export default function KPIDashboard({ kpis }) {
  return (
    <div className="card">
      <h2 className="card-title">Performance Metrics</h2>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Tardiness</div>
          <div className="kpi-value">{kpis.tardiness_minutes} min</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Changeovers</div>
          <div className="kpi-value">{kpis.changeovers}</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Makespan</div>
          <div className="kpi-value">{kpis.makespan_minutes} min</div>
        </div>
      </div>

      <div className="form-group" style={{marginTop: '1rem'}}>
        <div className="form-label">Resource Utilization</div>
        {Object.entries(kpis.utilization).map(([resource, util]) => (
          <div key={resource} style={{marginBottom: '0.5rem'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', marginBottom: '0.25rem'}}>
              <span>{resource}</span>
              <span style={{fontWeight: 600}}>{util}%</span>
            </div>
            <div style={{background: '#e2e8f0', height: '8px', borderRadius: '4px', overflow: 'hidden'}}>
              <div
                style={{
                  background: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`,
                  height: '100%',
                  width: `${util}%`,
                  transition: 'width 0.5s'
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
