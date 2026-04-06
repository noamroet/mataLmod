/**
 * Static wizard flow definition for the AI Advisor panel.
 *
 * Structure:
 *   Step 1 — Root node: static message + 4 choices (no API call)
 *   Step 2 — Branch node: advisor responds (API), shows 3 choices
 *   Step 3 — Sub-branch: advisor responds (API), shows 2–3 choices
 *   Step 4 — Final node: advisor gives summary (API), shows one CTA button
 *
 * The advisor API is called on every non-root step.
 * The message sent to the API is built from the full path of choices taken.
 *
 * CTA sections map to tabs/sections on the program detail page:
 *   'roadmap'  → מסלול קבלה tab
 *   'syllabus' → content inside פרטי התוכנית
 *   'career'   → career section
 *   'details'  → top of the page
 */

export type CtaSection = 'roadmap' | 'syllabus' | 'career' | 'details';

export interface WizardChoice {
  /** Hebrew label shown on the button */
  label: string;
  /** ID of the node to navigate to */
  nextId: string;
}

export interface WizardNode {
  id: string;
  step: 1 | 2 | 3 | 4;
  /**
   * If true, clicking a choice on this node leads directly to a final node.
   * The choice's nextId must be a step-4 (isFinal) node.
   */
  leadsToFinal?: boolean;
  /** If true, this is a terminal node — shows CTA instead of choices */
  isFinal?: boolean;
  /** Section to scroll to / tab to activate when CTA is clicked */
  ctaSection?: CtaSection;
  choices: WizardChoice[];
}

// ── Flow definition ───────────────────────────────────────────────────────────

export const WIZARD_FLOWS: Record<string, WizardNode> = {

  // ── Step 1: Root (static, no API call) ──────────────────────────────────
  root: {
    id: 'root', step: 1,
    choices: [
      { label: 'איך אני מגיע לסף הקבלה?',   nextId: 'gap'      },
      { label: 'מה לומדים בתואר הזה?',       nextId: 'syllabus' },
      { label: 'כמה מרוויחים אחרי?',          nextId: 'salary'   },
      { label: 'השווה לי עם תואר אחר',        nextId: 'compare'  },
    ],
  },

  // ── Branch 1: Gap / Admission threshold ─────────────────────────────────

  gap: {
    id: 'gap', step: 2,
    choices: [
      { label: 'שיפור פסיכומטרי',              nextId: 'gap_psycho'   },
      { label: 'שיפור ציוני בגרות (מועד ב׳)', nextId: 'gap_bagrut'   },
      { label: 'מסלול קבלה חלופי',             nextId: 'gap_parallel' },
    ],
  },

  gap_psycho: {
    id: 'gap_psycho', step: 3, leadsToFinal: true,
    choices: [
      { label: 'בכמה נקודות כדאי לשפר?',        nextId: 'gap_psycho_size'  },
      { label: 'מה הדרך הכי יעילה להתכונן?',    nextId: 'gap_psycho_prep'  },
    ],
  },
  gap_bagrut: {
    id: 'gap_bagrut', step: 3, leadsToFinal: true,
    choices: [
      { label: 'אילו מקצועות כדאי לשפר?',       nextId: 'gap_bagrut_which' },
      { label: 'כמה שיפור יוסיף לסקם?',         nextId: 'gap_bagrut_gain'  },
    ],
  },
  gap_parallel: {
    id: 'gap_parallel', step: 3, leadsToFinal: true,
    choices: [
      { label: 'תוכנית דומה בסף נמוך יותר',     nextId: 'gap_par_lower'   },
      { label: 'הגשה מוקדמת — מה זה ואיך?',     nextId: 'gap_par_early'   },
      { label: 'פטור ממועד ב׳ (בגרות חלקית)',    nextId: 'gap_par_partial' },
    ],
  },

  // Branch 1 finals
  gap_psycho_size:  { id: 'gap_psycho_size',  step: 4, isFinal: true, ctaSection: 'roadmap', choices: [] },
  gap_psycho_prep:  { id: 'gap_psycho_prep',  step: 4, isFinal: true, ctaSection: 'roadmap', choices: [] },
  gap_bagrut_which: { id: 'gap_bagrut_which', step: 4, isFinal: true, ctaSection: 'roadmap', choices: [] },
  gap_bagrut_gain:  { id: 'gap_bagrut_gain',  step: 4, isFinal: true, ctaSection: 'roadmap', choices: [] },
  gap_par_lower:    { id: 'gap_par_lower',    step: 4, isFinal: true, ctaSection: 'roadmap', choices: [] },
  gap_par_early:    { id: 'gap_par_early',    step: 4, isFinal: true, ctaSection: 'roadmap', choices: [] },
  gap_par_partial:  { id: 'gap_par_partial',  step: 4, isFinal: true, ctaSection: 'roadmap', choices: [] },

  // ── Branch 2: Syllabus ───────────────────────────────────────────────────

  syllabus: {
    id: 'syllabus', step: 2,
    choices: [
      { label: 'מה לומדים בשנה הראשונה?',       nextId: 'syl_year1'  },
      { label: 'מה מסלולי ההתמחות?',            nextId: 'syl_tracks' },
      { label: 'כמה קשה זה ביחס לתארים אחרים?', nextId: 'syl_level'  },
    ],
  },

  syl_year1: {
    id: 'syl_year1', step: 3, leadsToFinal: true,
    choices: [
      { label: 'מה הקורסים הכי מאתגרים?',       nextId: 'syl_y1_hard' },
      { label: 'איך להתכונן לפני הלימודים?',     nextId: 'syl_y1_prep' },
    ],
  },
  syl_tracks: {
    id: 'syl_tracks', step: 3, leadsToFinal: true,
    choices: [
      { label: 'AI ולמידת מכונה',               nextId: 'syl_track_ai'  },
      { label: 'אבטחת מידע',                    nextId: 'syl_track_sec' },
      { label: 'פיתוח תוכנה / Backend',         nextId: 'syl_track_dev' },
    ],
  },
  syl_level: {
    id: 'syl_level', step: 3, leadsToFinal: true,
    choices: [
      { label: 'מה הרמה הנדרשת במתמטיקה?',     nextId: 'syl_math'    },
      { label: 'כמה שעות לימוד ביום בממוצע?',   nextId: 'syl_hours'   },
    ],
  },

  // Branch 2 finals
  syl_y1_hard:    { id: 'syl_y1_hard',    step: 4, isFinal: true, ctaSection: 'syllabus', choices: [] },
  syl_y1_prep:    { id: 'syl_y1_prep',    step: 4, isFinal: true, ctaSection: 'syllabus', choices: [] },
  syl_track_ai:   { id: 'syl_track_ai',   step: 4, isFinal: true, ctaSection: 'syllabus', choices: [] },
  syl_track_sec:  { id: 'syl_track_sec',  step: 4, isFinal: true, ctaSection: 'syllabus', choices: [] },
  syl_track_dev:  { id: 'syl_track_dev',  step: 4, isFinal: true, ctaSection: 'syllabus', choices: [] },
  syl_math:       { id: 'syl_math',       step: 4, isFinal: true, ctaSection: 'syllabus', choices: [] },
  syl_hours:      { id: 'syl_hours',      step: 4, isFinal: true, ctaSection: 'syllabus', choices: [] },

  // ── Branch 3: Salary / Career ────────────────────────────────────────────

  salary: {
    id: 'salary', step: 2,
    choices: [
      { label: 'שכר ראשוני ממוצע',              nextId: 'sal_entry'   },
      { label: 'פוטנציאל קידום וגדילה',         nextId: 'sal_growth'  },
      { label: 'ביקוש בשוק העבודה',             nextId: 'sal_demand'  },
    ],
  },

  sal_entry: {
    id: 'sal_entry', step: 3, leadsToFinal: true,
    choices: [
      { label: 'ישר אחרי התואר',                nextId: 'sal_e_fresh' },
      { label: 'אחרי 3–5 שנים ניסיון',         nextId: 'sal_e_3y'    },
    ],
  },
  sal_growth: {
    id: 'sal_growth', step: 3, leadsToFinal: true,
    choices: [
      { label: 'מסלול טכני (Senior/Principal)', nextId: 'sal_g_tech'  },
      { label: 'מסלול ניהולי (Team Lead/VP)',   nextId: 'sal_g_mgmt'  },
    ],
  },
  sal_demand: {
    id: 'sal_demand', step: 3, leadsToFinal: true,
    choices: [
      { label: 'אילו חברות מגייסות?',           nextId: 'sal_d_co'    },
      { label: 'מה מגמת השוק ב-5 שנים?',       nextId: 'sal_d_trend' },
      { label: 'האם יש שינויים בגלל AI?',       nextId: 'sal_d_ai'    },
    ],
  },

  // Branch 3 finals
  sal_e_fresh:  { id: 'sal_e_fresh',  step: 4, isFinal: true, ctaSection: 'career', choices: [] },
  sal_e_3y:     { id: 'sal_e_3y',     step: 4, isFinal: true, ctaSection: 'career', choices: [] },
  sal_g_tech:   { id: 'sal_g_tech',   step: 4, isFinal: true, ctaSection: 'career', choices: [] },
  sal_g_mgmt:   { id: 'sal_g_mgmt',   step: 4, isFinal: true, ctaSection: 'career', choices: [] },
  sal_d_co:     { id: 'sal_d_co',     step: 4, isFinal: true, ctaSection: 'career', choices: [] },
  sal_d_trend:  { id: 'sal_d_trend',  step: 4, isFinal: true, ctaSection: 'career', choices: [] },
  sal_d_ai:     { id: 'sal_d_ai',     step: 4, isFinal: true, ctaSection: 'career', choices: [] },

  // ── Branch 4: Compare ────────────────────────────────────────────────────

  compare: {
    id: 'compare', step: 2,
    choices: [
      { label: 'תואר זהה באוניברסיטה אחרת',    nextId: 'cmp_inst'    },
      { label: 'תחום לימוד שונה לגמרי',         nextId: 'cmp_field'   },
      { label: 'תוכניות שאני זכאי אליהן',        nextId: 'cmp_eligible'},
    ],
  },

  cmp_inst: {
    id: 'cmp_inst', step: 3, leadsToFinal: true,
    choices: [
      { label: 'השוואת שכר לימוד',              nextId: 'cmp_i_tuition'   },
      { label: 'השוואת סף הקבלה',              nextId: 'cmp_i_threshold' },
    ],
  },
  cmp_field: {
    id: 'cmp_field', step: 3, leadsToFinal: true,
    choices: [
      { label: 'הנדסת חשמל ואלקטרוניקה',      nextId: 'cmp_f_ee'   },
      { label: 'מינהל עסקים / כלכלה',         nextId: 'cmp_f_biz'  },
      { label: 'פסיכולוגיה ומדעי החברה',      nextId: 'cmp_f_psy'  },
    ],
  },
  cmp_eligible: {
    id: 'cmp_eligible', step: 3, leadsToFinal: true,
    choices: [
      { label: 'תוכניות שזכאי אליהן עכשיו',  nextId: 'cmp_e_now'   },
      { label: 'תוכניות גבוליות (קרוב לסף)', nextId: 'cmp_e_close' },
    ],
  },

  // Branch 4 finals
  cmp_i_tuition:   { id: 'cmp_i_tuition',   step: 4, isFinal: true, ctaSection: 'details',  choices: [] },
  cmp_i_threshold: { id: 'cmp_i_threshold', step: 4, isFinal: true, ctaSection: 'roadmap',  choices: [] },
  cmp_f_ee:        { id: 'cmp_f_ee',        step: 4, isFinal: true, ctaSection: 'career',   choices: [] },
  cmp_f_biz:       { id: 'cmp_f_biz',       step: 4, isFinal: true, ctaSection: 'career',   choices: [] },
  cmp_f_psy:       { id: 'cmp_f_psy',       step: 4, isFinal: true, ctaSection: 'career',   choices: [] },
  cmp_e_now:       { id: 'cmp_e_now',       step: 4, isFinal: true, ctaSection: 'roadmap',  choices: [] },
  cmp_e_close:     { id: 'cmp_e_close',     step: 4, isFinal: true, ctaSection: 'roadmap',  choices: [] },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Return the parent node ID by traversing the flow. */
export function findParentNodeId(
  targetId: string,
  flows: Record<string, WizardNode> = WIZARD_FLOWS
): string | null {
  for (const node of Object.values(flows)) {
    if (node.choices.some((c) => c.nextId === targetId)) {
      return node.id;
    }
  }
  return null;
}

/** Build the full path label string from a list of choice labels. */
export function buildPathContext(
  programName: string,
  institutionName: string,
  pathLabels: string[],
  isFinal: boolean,
  suffixFinal: string,
  suffixStep: string,
): string {
  const path = pathLabels.join(' → ');
  const suffix = isFinal ? suffixFinal : suffixStep;
  return `התוכנית: ${programName} ב${institutionName}. המשתמש בחר: ${path}. ${suffix}`;
}
