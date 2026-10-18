import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useToastStore, type ToastType } from '../../hooks/useToast';

export type { ToastType, Toast, ToastStore } from '../../hooks/useToast';

const iconMap: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle size={20} className="toast__icon toast__icon--success" />,
  error: <XCircle size={20} className="toast__icon toast__icon--error" />,
  warning: <AlertTriangle size={20} className="toast__icon toast__icon--warning" />,
  info: <Info size={20} className="toast__icon toast__icon--info" />,
};

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" role="region" aria-label="Notifications" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast--${toast.type}`} role="alert">
          <div className="toast__content">
            {iconMap[toast.type]}
            <div className="toast__text">
              <p className="toast__title">{toast.title}</p>
              {toast.message && <p className="toast__message">{toast.message}</p>}
            </div>
          </div>
          <button
            className="toast__close"
            onClick={() => removeToast(toast.id)}
            aria-label="Dismiss notification"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
