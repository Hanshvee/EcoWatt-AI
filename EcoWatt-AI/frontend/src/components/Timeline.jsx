import { formatLocalTime, parseIso } from "../lib/time.js";

export default function Timeline({ appliances }) {
  if (!appliances?.length) {
    return null;
  }

  const starts = appliances.map((item) => parseIso(item.start).getTime());
  const finishes = appliances.map((item) => parseIso(item.finish).getTime());
  const min = Math.min(...starts);
  const max = Math.max(...finishes);
  const span = Math.max(max - min, 1);

  return (
    <div className="timeline" aria-label="Recommended appliance timeline">
      <div className="timeline-track">
        {appliances.map((item) => {
          const start = parseIso(item.start).getTime();
          const finish = parseIso(item.finish).getTime();
          const left = ((start - min) / span) * 100;
          const width = ((finish - start) / span) * 100;
          return (
            <div className="lane" key={item.id}>
              <div>
                <strong>{item.name}</strong>
                <div className="fine">{formatLocalTime(item.start)}–{formatLocalTime(item.finish)}</div>
              </div>
              <div className="lane-bar">
                <div
                  className="lane-fill"
                  style={{ left: `${left}%`, width: `${Math.max(width, 3)}%`, background: item.color }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
