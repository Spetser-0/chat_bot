/**
 * components/chat/ChatLayout.tsx
 * ──────────────────────────────
 * DEPRECATED — kept only so the file compiles. The app now uses AppShell +
 * AppSidebar + ChatPage. This component is not imported anywhere.
 */
import type { ReactNode } from 'react';

interface ChatLayoutProps {
  children: ReactNode;
}

export function ChatLayout({ children }: ChatLayoutProps) {
  return <>{children}</>;
}
