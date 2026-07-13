export default function AnonymousToggle({ anonymous, onChange }) {
  const options = [
    {
      value: true,
      label: "Anonymous",
      hint: "Your identity stays private",
    },
    {
      value: false,
      label: "Identified",
      hint: "Share your student ID",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3">
      {options.map((option) => {
        const selected = anonymous === option.value;
        return (
          <button
            key={String(option.value)}
            type="button"
            onClick={() => onChange(option.value)}
            aria-pressed={selected}
            className={[
              "rounded-2xl border-2 px-5 py-4 text-left transition-all duration-200",
              selected
                ? "border-aui-forest bg-aui-mist/80 shadow-md"
                : "border-slate-200 bg-white hover:border-slate-300",
            ].join(" ")}
          >
            <div className="flex items-center justify-between">
              <span
                className={[
                  "text-lg font-semibold",
                  selected ? "text-aui-deep" : "text-slate-700",
                ].join(" ")}
              >
                {option.label}
              </span>
              <span
                className={[
                  "flex h-6 w-6 items-center justify-center rounded-full border-2",
                  selected
                    ? "border-aui-forest bg-aui-forest"
                    : "border-slate-300",
                ].join(" ")}
              >
                {selected && (
                  <svg
                    className="h-4 w-4 text-white"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0L3.3 10.1a1 1 0 111.4-1.4l3.8 3.8 6.8-6.8a1 1 0 011.4 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-500">{option.hint}</p>
          </button>
        );
      })}
    </div>
  );
}
