import { useState } from 'react'

const EXAMPLE_CLIENT_A = {
  "horizon": { "start": "2025-11-03T08:00:00", "end": "2025-11-03T16:00:00" },
  "resources": [
    { "id": "Fill-1", "capabilities": ["fill"], "calendar": [["2025-11-03T08:00:00", "2025-11-03T12:00:00"], ["2025-11-03T12:30:00", "2025-11-03T16:00:00"]] },
    { "id": "Label-1", "capabilities": ["label"], "calendar": [["2025-11-03T08:00:00", "2025-11-03T16:00:00"]] },
    { "id": "Pack-1", "capabilities": ["pack"], "calendar": [["2025-11-03T08:00:00", "2025-11-03T16:00:00"]] }
  ],
  "products": [
    { "id": "P-100", "family": "standard", "due": "2025-11-03T12:30:00", "route": [
      {"capability": "fill", "duration_minutes": 30},
      {"capability": "label", "duration_minutes": 20},
      {"capability": "pack", "duration_minutes": 15}
    ]},
    { "id": "P-101", "family": "premium", "due": "2025-11-03T15:00:00", "route": [
      {"capability": "fill", "duration_minutes": 35},
      {"capability": "label", "duration_minutes": 25}
    ]}
  ],
  "changeover_matrix_minutes": { "values": { "standard->premium": 20, "premium->standard": 20 }},
  "settings": { "time_limit_seconds": 30 }
}

const EXAMPLE_CLIENT_B = {
  "client_id": "client_b",
  "shift_window": "11/03/2025 08:00 - 16:00",
  "machines": ["Fill-1", "Label-1", "Pack-1"],
  "machine_breaks": [{"machine": "Fill-1", "start": "12:00", "end": "12:30"}],
  "setup_times": [
    {"from_family": "standard", "to_family": "premium", "minutes": 20},
    {"from_family": "premium", "to_family": "standard", "minutes": 20}
  ],
  "orders": [
    {
      "order_id": "ORD-100",
      "product_family": "standard",
      "deadline_hour": 12.5,
      "operations": [
        {"step": 1, "type": "fill", "minutes": 30},
        {"step": 2, "type": "label", "minutes": 20},
        {"step": 3, "type": "pack", "minutes": 15}
      ]
    },
    {
      "order_id": "ORD-101",
      "product_family": "premium",
      "deadline_hour": 15.0,
      "operations": [
        {"step": 1, "type": "fill", "minutes": 35},
        {"step": 2, "type": "label", "minutes": 25}
      ]
    }
  ]
}

export default function ScheduleInput({ onSchedule, loading }) {
  const [clientFormat, setClientFormat] = useState('client_a')
  const [jsonInput, setJsonInput] = useState(JSON.stringify(EXAMPLE_CLIENT_A, null, 2))

  const handleFormatChange = (format) => {
    setClientFormat(format)
    if (format === 'client_a') {
      setJsonInput(JSON.stringify(EXAMPLE_CLIENT_A, null, 2))
    } else {
      setJsonInput(JSON.stringify(EXAMPLE_CLIENT_B, null, 2))
    }
  }

  const handleSubmit = () => {
    try {
      const data = JSON.parse(jsonInput)
      onSchedule(data)
    } catch (err) {
      alert(`Invalid JSON: ${err.message}`)
    }
  }

  return (
    <div className="card">
      <h2 className="card-title">Schedule Input</h2>

      <div className="form-group">
        <label className="form-label">Client Format</label>
        <select
          className="form-select"
          value={clientFormat}
          onChange={(e) => handleFormatChange(e.target.value)}
          disabled={loading}
        >
          <option value="client_a">Client A (Original Format)</option>
          <option value="client_b">Client B (Legacy ERP)</option>
        </select>
      </div>

      <div className="form-group">
        <label className="form-label">JSON Input</label>
        <textarea
          className="form-textarea"
          value={jsonInput}
          onChange={(e) => setJsonInput(e.target.value)}
          disabled={loading}
          placeholder="Paste your schedule JSON here..."
        />
      </div>

      <button
        className="btn btn-primary"
        onClick={handleSubmit}
        disabled={loading}
      >
        {loading ? 'Generating...' : 'Generate Schedule'}
      </button>

      <div className="example-links">
        <span className="form-label" style={{marginRight: '0.5rem'}}>Quick load:</span>
        <span className="example-link" onClick={() => handleFormatChange('client_a')}>
          Client A Example
        </span>
        <span className="example-link" onClick={() => handleFormatChange('client_b')}>
          Client B Example
        </span>
      </div>
    </div>
  )
}
