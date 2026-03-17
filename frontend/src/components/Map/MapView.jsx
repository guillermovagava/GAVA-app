import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import L from 'leaflet'

const STATUS_COLORS = {
  new:            '#3b82f6',
  contacted:      '#f59e0b',
  replied:        '#8b5cf6',
  meeting_booked: '#10b981',
  converted:      '#059669',
}

function makeIcon(color) {
  return L.divIcon({
    className: '',
    html: `<div style="
      width:12px;height:12px;
      border-radius:50%;
      background:${color};
      border:2px solid rgba(255,255,255,0.8);
      box-shadow:0 0 6px ${color}88;
    "></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  })
}

function FlyToSelected({ pin }) {
  const map = useMap()
  useEffect(() => {
    if (pin?.lat && pin?.lng) {
      map.flyTo([pin.lat, pin.lng], Math.max(map.getZoom(), 10), { duration: 0.8 })
    }
  }, [pin, map])
  return null
}

function Markers({ pins, onSelect, selectedId }) {
  const markersRef = useRef({})

  return (
    <MarkerClusterGroup
      chunkedLoading
      maxClusterRadius={60}
      showCoverageOnHover={false}
    >
      {pins.map(pin => {
        const color = STATUS_COLORS[pin.status] || STATUS_COLORS.new
        return (
          <L.Marker
            key={pin.id}
            position={[pin.lat, pin.lng]}
            icon={selectedId === pin.id
              ? makeIcon('#fff')   // highlight selected
              : makeIcon(color)
            }
            eventHandlers={{ click: () => onSelect(pin) }}
          />
        )
      })}
    </MarkerClusterGroup>
  )
}

// We can't use L.Marker as JSX — use react-leaflet Marker instead
import { Marker, Popup } from 'react-leaflet'

function PinsLayer({ pins, onSelect, selectedId }) {
  return (
    <MarkerClusterGroup
      chunkedLoading
      maxClusterRadius={60}
      showCoverageOnHover={false}
    >
      {pins.map(pin => {
        const color = STATUS_COLORS[pin.status] || STATUS_COLORS.new
        const icon = selectedId === pin.id
          ? makeIcon('#ffffff')
          : makeIcon(color)
        return (
          <Marker
            key={pin.id}
            position={[pin.lat, pin.lng]}
            icon={icon}
            eventHandlers={{ click: () => onSelect(pin) }}
          >
            <Popup>
              <div style={{ fontSize: 12, minWidth: 140 }}>
                <strong>{pin.business_name}</strong>
                <br />
                {pin.city}, {pin.state}
                <br />
                <span style={{ color: color, textTransform: 'capitalize' }}>{pin.status}</span>
              </div>
            </Popup>
          </Marker>
        )
      })}
    </MarkerClusterGroup>
  )
}

export default function MapView({ pins, onSelectPin, selectedPin }) {
  return (
    <div className="map-container" style={{ height: '100%' }}>
      <MapContainer
        center={[39.5, -98.35]}
        zoom={4}
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
          maxZoom={19}
        />
        <PinsLayer pins={pins} onSelect={onSelectPin} selectedId={selectedPin?.id} />
        {selectedPin && <FlyToSelected pin={selectedPin} />}
      </MapContainer>

      {/* Legend */}
      <div style={{
        position: 'absolute',
        bottom: 24,
        left: 10,
        background: 'rgba(26,29,46,0.92)',
        border: '1px solid #2e3252',
        borderRadius: 8,
        padding: '8px 12px',
        zIndex: 999,
        fontSize: 11,
        display: 'flex',
        flexDirection: 'column',
        gap: 5,
      }}>
        {Object.entries(STATUS_COLORS).map(([status, color]) => (
          <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <div style={{
              width: 10, height: 10, borderRadius: '50%',
              background: color, border: '2px solid rgba(255,255,255,0.6)',
            }} />
            <span style={{ color: '#8892a4', textTransform: 'capitalize' }}>
              {status.replace('_', ' ')}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
