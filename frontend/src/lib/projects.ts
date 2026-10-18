/**
 * lib/projects.ts — client-side project folders + recently opened chats.
 *
 * Phase 1 (frontend-only): there is no projects API yet, so everything is
 * persisted in localStorage behind this single module. The backend phase can
 * swap the storage implementation for API calls without touching any
 * component — that is the whole point of keeping it in one place.
 */
import { useSyncExternalStore } from 'react';

export interface Project {
  id: string;
  name: string;
  createdAt: string;
}

export interface RecentEntry {
  conversationId: string;
  openedAt: string;
}

const PROJECTS_KEY = 'spetser.projects';
const MEMBERS_KEY = 'spetser.projectChats';
const RECENT_KEY = 'spetser.recent';
const MAX_RECENT = 5;

/* ── storage helpers (never throw) ─────────────────────────────────────── */

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* private mode / quota exceeded — fail silently */
  }
}

/* ── projects ──────────────────────────────────────────────────────────── */

export function listProjects(): Project[] {
  const list = read<Project[]>(PROJECTS_KEY, []);
  return Array.isArray(list) ? list : [];
}

export function createProject(name: string): Project | null {
  const trimmed = name.trim();
  if (!trimmed) return null;
  const project: Project = {
    id: crypto.randomUUID(),
    name: trimmed,
    createdAt: new Date().toISOString(),
  };
  write(PROJECTS_KEY, [project, ...listProjects()]);
  emit();
  return project;
}

export function renameProject(id: string, name: string): void {
  const trimmed = name.trim();
  if (!trimmed) return;
  write(
    PROJECTS_KEY,
    listProjects().map((p) => (p.id === id ? { ...p, name: trimmed } : p)),
  );
  emit();
}

export function deleteProject(id: string): void {
  write(
    PROJECTS_KEY,
    listProjects().filter((p) => p.id !== id),
  );
  const members = readMembers();
  delete members[id];
  write(MEMBERS_KEY, members);
  emit();
}

/* ── project ↔ chat membership ─────────────────────────────────────────── */

function readMembers(): Record<string, string[]> {
  const m = read<Record<string, string[]>>(MEMBERS_KEY, {});
  return m && typeof m === 'object' ? m : {};
}

export function chatsOfProject(projectId: string): string[] {
  return readMembers()[projectId] ?? [];
}

export function addChatToProject(projectId: string, conversationId: string): void {
  const members = readMembers();
  const list = members[projectId] ?? [];
  if (list.includes(conversationId)) return;
  members[projectId] = [...list, conversationId];
  write(MEMBERS_KEY, members);
  emit();
}

export function removeChatFromProject(projectId: string, conversationId: string): void {
  const members = readMembers();
  members[projectId] = (members[projectId] ?? []).filter((id) => id !== conversationId);
  write(MEMBERS_KEY, members);
  emit();
}

export function projectOfChat(conversationId: string): string | null {
  const members = readMembers();
  for (const [projectId, ids] of Object.entries(members)) {
    if (ids.includes(conversationId)) return projectId;
  }
  return null;
}

/* ── recently opened ───────────────────────────────────────────────────── */

export function listRecent(): RecentEntry[] {
  const list = read<RecentEntry[]>(RECENT_KEY, []);
  return Array.isArray(list) ? list : [];
}

export function touchRecent(conversationId: string): void {
  const entries = listRecent().filter((e) => e.conversationId !== conversationId);
  entries.unshift({ conversationId, openedAt: new Date().toISOString() });
  write(RECENT_KEY, entries.slice(0, MAX_RECENT));
  emit();
}

/* ── reactivity ────────────────────────────────────────────────────────── */

const listeners = new Set<() => void>();
let version = 0;

function subscribe(callback: () => void): () => void {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

function emit(): void {
  version += 1;
  listeners.forEach((cb) => cb());
}

/** Re-renders the calling component whenever projects / recent change. */
export function useProjects(): { projects: Project[]; recent: RecentEntry[] } {
  useSyncExternalStore(subscribe, () => version);
  return { projects: listProjects(), recent: listRecent() };
}
