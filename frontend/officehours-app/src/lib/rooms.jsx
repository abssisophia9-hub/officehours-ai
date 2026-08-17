export function timeAgo(iso) {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.max(1, Math.round(ms / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

export function initials(name) {
  const parts = String(name || "C")
    .trim()
    .split(/\s+/)
    .slice(0, 2);
  return parts.map((part) => part[0]?.toUpperCase() || "").join("") || "C";
}

export function avatarHue(seed) {
  const text = String(seed || "x");
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) hash = (hash * 31 + text.charCodeAt(i)) % 360;
  return hash;
}

export function MarkdownBody({ text }) {
  const blocks = String(text || "").split(/\n{2,}/);
  return (
    <div className="rf-md">
      {blocks.map((block, index) => {
        const line = block.trim();
        if (!line) return null;
        if (line.startsWith("### ")) return <h4 key={index}>{inline(line.slice(4))}</h4>;
        if (line.startsWith("## ")) return <h3 key={index}>{inline(line.slice(3))}</h3>;
        if (line.startsWith("# ")) return <h3 key={index}>{inline(line.slice(2))}</h3>;
        if (line.startsWith("- ")) {
          const items = line.split("\n").filter((row) => row.trim().startsWith("- "));
          return (
            <ul key={index}>
              {items.map((item) => (
                <li key={item}>{inline(item.replace(/^\s*-\s+/, ""))}</li>
              ))}
            </ul>
          );
        }
        return <p key={index}>{inline(line)}</p>;
      })}
    </div>
  );
}

function inline(value) {
  const parts = String(value).split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index}>{part.slice(1, -1)}</code>;
    }
    return <span key={index}>{part}</span>;
  });
}
