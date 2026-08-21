import { useEffect, useState } from 'react'
import { getParkingSpots } from '../services/api'

const VISION_URL = import.meta.env.VITE_VISION_URL || 'http://127.0.0.1:8002'

export default function CameraDetection() {
  const [mode, setMode] = useState('ENTRY')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')
  const [spots, setSpots] = useState([])
  const [spotId, setSpotId] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getParkingSpots()
      .then(data => setSpots(data.filter(spot => spot.status === 'FREE')))
      .catch(err => setError(err.message))
  }, [])

  const handleFile = event => {
    const selected = event.target.files?.[0]
    if (!selected) return
    setFile(selected)
    setPreview(URL.createObjectURL(selected))
    setResult(null)
    setError('')
  }

  const changeMode = nextMode => {
    setMode(nextMode)
    setResult(null)
    setError('')
  }

  const detect = async event => {
    event.preventDefault()
    if (!file) return setError('Select a vehicle image first.')
    if (mode === 'ENTRY' && !spotId) return setError('Select a free parking spot.')

    setLoading(true)
    setError('')
    setResult(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      if (mode === 'ENTRY') formData.append('parking_spot_id', spotId)
      const token = localStorage.getItem('smartpark_token')
      const response = await fetch(`${VISION_URL}/${mode === 'ENTRY' ? 'detect-and-register' : 'detect-and-exit'}`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail?.message || data.detail || 'Vehicle detection failed')
      setResult(data)
      if (mode === 'ENTRY') setSpots(current => current.filter(spot => String(spot.id) !== String(spotId)))
      else getParkingSpots().then(data => setSpots(data.filter(spot => spot.status === 'FREE')))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const detection = result?.detection?.detections?.[0]
  const parkingAction = result?.parking_entry || result?.parking_exit
  const isEntry = mode === 'ENTRY'

  return <>
    <header className="page-head">
      <div><p className="eyebrow">SMARTPARK AI</p><h1>Camera detection</h1><p className="muted">Detect a vehicle to register its parking entry or exit automatically.</p></div>
    </header>
    {error && <p className="error">{error}</p>}
    <div className="camera-layout">
      <section className="panel camera-panel">
        <h2>{isEntry ? 'Vehicle entry' : 'Vehicle exit'}</h2>
        <div className="portal-choice"><button type="button" className={isEntry ? '' : 'secondary'} onClick={() => changeMode('ENTRY')}>Entry</button><button type="button" className={!isEntry ? '' : 'secondary'} onClick={() => changeMode('EXIT')}>Exit</button></div>
        <label className="upload-box">
          {preview ? <img src={preview} alt="Selected vehicle" /> : <span>Select an image containing a vehicle</span>}
          <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handleFile} />
        </label>
        <form onSubmit={detect} className="camera-form">
          {isEntry && <label>Free parking spot<select value={spotId} onChange={event => setSpotId(event.target.value)} required><option value="">Select a spot</option>{spots.map(spot => <option key={spot.id} value={spot.id}>{spot.number} · {spot.zone} · {spot.floor || 'Ground'}</option>)}</select></label>}
          {isEntry && !spots.length && <p className="muted">No FREE parking spots available. Add one from Parking Spots first.</p>}
          <button type="submit" disabled={loading || (isEntry && !spots.length)}>{loading ? 'Detecting...' : isEntry ? 'Detect and register entry' : 'Detect and register exit'}</button>
        </form>
      </section>
      <section className="panel detection-panel">
        <p className="eyebrow">DETECTION RESULT</p>
        {!result && <p className="muted">The detected plate and parking decision will appear here.</p>}
        {result && <div className="detection-result"><div><span>Vehicle</span><strong>{detection?.vehicle_type || 'Not detected'}</strong></div><div><span>Plate</span><strong>{detection?.plate_text || 'Not detected'}</strong></div><div><span>Confidence</span><strong>{detection ? `${Math.round(detection.confidence * 100)}%` : '—'}</strong></div><div><span>Session</span><strong>#{parkingAction?.session?.id}</strong></div><div><span>Parking spot</span><strong>{parkingAction?.session?.parking_spot_id}</strong></div>{isEntry ? <p className="success">Vehicle entry registered. Spot is now occupied.</p> : <p className="success">Vehicle exit registered. Spot is now free and payment is pending.</p>}</div>}
      </section>
    </div>
  </>
}
