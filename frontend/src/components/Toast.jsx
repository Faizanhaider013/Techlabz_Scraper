import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Info, XCircle, X, Loader2 } from "lucide-react";
import clsx from "clsx";

const TONES = {
  success: { bar: "bg-emerald-500", icon: CheckCircle2, iconClass: "text-emerald-500" },
  error: { bar: "bg-rose-500", icon: XCircle, iconClass: "text-rose-500" },
  info: { bar: "bg-indigo-500", icon: Info, iconClass: "text-indigo-500" },
};

export default function Toast({ toast, onDismiss }) {
  useEffect(() => {
    if (!toast) return;
    // Persistent for "info" running state is fine; auto-dismiss others.
    const t = setTimeout(onDismiss, toast.type === "info" ? 6000 : 5000);
    return () => clearTimeout(t);
  }, [toast, onDismiss]);

  const tone = toast ? TONES[toast.type] || TONES.info : null;
  const Icon = tone?.icon;

  return (
    <AnimatePresence>
      {toast && (
        <motion.div
          key={toast.id}
          initial={{ opacity: 0, y: 24, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 12, scale: 0.96 }}
          transition={{ type: "spring", stiffness: 350, damping: 28 }}
          className="fixed bottom-5 left-1/2 z-[60] w-[calc(100%-2rem)] max-w-md -translate-x-1/2"
        >
          <div className="flex items-center gap-3 overflow-hidden rounded-2xl border border-slate-200 bg-white py-3 pl-4 pr-3 shadow-card-hover">
            <span className={clsx("h-2 w-2 shrink-0 rounded-full", tone.bar)} />
            {toast.type === "info" ? (
              <Loader2 className={clsx("h-4 w-4 shrink-0 animate-spin", tone.iconClass)} />
            ) : (
              <Icon className={clsx("h-4 w-4 shrink-0", tone.iconClass)} />
            )}
            <p className="flex-1 text-sm font-medium text-slate-700">{toast.message}</p>
            <button
              onClick={onDismiss}
              aria-label="Dismiss"
              className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
