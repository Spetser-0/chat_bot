/**
 * api/skills.ts — Public skill catalogue (Phase 4 Lesson 4.7, UI in 9.5).
 * system_prompt never appears here — server-internal only.
 */
import { apiClient, extractData } from './client';

export interface PublicSkill {
  name: string;
  slug: string;
  description: string | null;
  is_premium: boolean;
  tools: string[];
}

export const skillsApi = {
  async list(): Promise<PublicSkill[]> {
    const res = await apiClient.get('/skills');
    return extractData<PublicSkill[]>(res);
  },
};
