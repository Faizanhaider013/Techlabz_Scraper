import clsx from "clsx";

const VARIANTS = {
  primary:
    "bg-indigo-600 text-white shadow-sm hover:bg-indigo-700 active:bg-indigo-800 focus-visible:ring-indigo-500",
  secondary:
    "bg-slate-900 text-white shadow-sm hover:bg-slate-800 focus-visible:ring-slate-500",
  outline:
    "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-300 focus-visible:ring-indigo-500",
  ghost:
    "text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-slate-400",
  danger:
    "bg-rose-600 text-white shadow-sm hover:bg-rose-700 focus-visible:ring-rose-500",
};

const SIZES = {
  sm: "h-9 px-3 text-sm gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-11 px-5 text-sm gap-2",
};

/**
 * Reusable button. Renders an <a> when `href` is provided, else a <button>.
 */
export default function Button({
  variant = "primary",
  size = "md",
  className,
  href,
  children,
  disabled,
  ...props
}) {
  const classes = clsx(
    "inline-flex items-center justify-center rounded-xl font-medium transition-all",
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-white",
    "disabled:cursor-not-allowed disabled:opacity-60",
    VARIANTS[variant],
    SIZES[size],
    className
  );

  if (href) {
    return (
      <a href={href} className={classes} {...props}>
        {children}
      </a>
    );
  }
  return (
    <button className={classes} disabled={disabled} {...props}>
      {children}
    </button>
  );
}
