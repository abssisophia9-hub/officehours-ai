import { Link, NavLink } from "react-router";

const OPTIONS = [
  { to: "/demo/board", n: "01", label: "Board" },
  { to: "/demo/path", n: "02", label: "Path" },
  { to: "/demo/trio", n: "03", label: "Trio" },
];

export default function VisionChrome({ kicker, children }) {
  return (
    <div className="vd">
      <header className="vd-nav">
        <Link to="/demo" className="vd-brand">
          <img src="/aui-logo.png" alt="" />
          <span>
            OfficeHours
            <small>Vision demos · live opening is Option 3</small>
          </span>
        </Link>
        <nav>
          {OPTIONS.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "is-on" : "")}>
              {item.n} {item.label}
            </NavLink>
          ))}
          <Link className="vd-signin" to="/login">
            Sign in
          </Link>
        </nav>
      </header>
      {kicker ? <p className="vd-strip">{kicker}</p> : null}
      {children}
    </div>
  );
}

export function VisionCopy({ option, title, children }) {
  return (
    <div className="vd-copy">
      <p className="vd-kicker">Al Akhawayn University · Campus product · Option {option}</p>
      <h1>
        Get unstuck without the office-hours <span className="vd-mark">lottery.</span>
      </h1>
      {title ? <p className="vd-sub">{title}</p> : null}
      <div className="vd-body">{children}</div>
    </div>
  );
}

export function Person({ kind, label, active, onClick, size = "md" }) {
  return (
    <button
      type="button"
      className={`vd-person vd-person-${kind} vd-person-${size} ${active ? "is-on" : ""}`}
      onClick={onClick}
      aria-pressed={active}
    >
      <span className="vd-person-head" />
      <span className="vd-person-body" />
      <span className="vd-person-label">{label}</span>
    </button>
  );
}
