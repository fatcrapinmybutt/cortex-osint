---
name: SINGULARITY-creative-engine
description: "Transcendent creative engine for branding, marketing, and multi-platform expansion. Use when: brand identity, marketing website, React Native mobile app, AI content generation, notification infrastructure, growth strategy, data storytelling, logo design, landing pages, SEO, social media, email marketing, content calendar, user acquisition funnels, app store optimization, React Native, Expo, Next.js, Figma, video marketing, podcast, community building, open-source strategy, legal tech positioning, pro se advocacy branding, litigation visualization storytelling."
---

# SINGULARITY-creative-engine — Transcendent Creative Engine

> **Absorbs:** ai-media-creation, messaging-integration, mobile-cross-platform
> **Tier:** APP | **Domain:** Branding, Marketing, Mobile, Growth
> **Stack:** React Native · Expo · Next.js 15 · Tailwind CSS v4 · Figma · Resend · PostHog

---

## 1. LitigationOS Brand Identity

### Brand Foundation

| Element | Value | Rationale |
|---------|-------|-----------|
| **Name** | LitigationOS | Operating system metaphor — systematic, complete |
| **Tagline** | "Your case. Your system. Your justice." | Empowerment, ownership, outcome |
| **Voice** | Authoritative yet accessible | Pro se litigants need confidence, not jargon |
| **Personality** | Precise, relentless, empowering | Mirrors the litigation mindset |
| **Mission** | Democratize litigation intelligence | Level the playing field against funded opponents |

### Color System

```css
:root {
  /* Primary — Justice Blue */
  --primary-50:  #eff6ff;
  --primary-100: #dbeafe;
  --primary-500: #3b82f6;
  --primary-600: #2563eb;
  --primary-900: #1e3a5f;

  /* Accent — Victory Gold */
  --accent-400:  #fbbf24;
  --accent-500:  #f59e0b;
  --accent-600:  #d97706;

  /* Danger — Alert Red */
  --danger-500:  #ef4444;
  --danger-600:  #dc2626;

  /* Success — Progress Green */
  --success-500: #22c55e;
  --success-600: #16a34a;

  /* Neutral — Slate */
  --slate-50:    #f8fafc;
  --slate-100:   #f1f5f9;
  --slate-700:   #334155;
  --slate-900:   #0f172a;
  --slate-950:   #020617;

  /* Dark mode background */
  --bg-dark:     #0a0a0f;
  --bg-card:     #1a1a2e;
  --bg-elevated: #16213e;
}
```

### Typography

```css
/* Headings — Inter or Geist Sans (modern, geometric) */
font-family: 'Inter', 'Geist Sans', system-ui, sans-serif;

/* Body — readable, professional */
font-family: 'Inter', system-ui, sans-serif;
line-height: 1.6;

/* Code/Data — monospace for evidence, case numbers */
font-family: 'JetBrains Mono', 'Fira Code', monospace;

/* Court documents — traditional */
font-family: 'Times New Roman', 'Noto Serif', serif;
```

### Logo Concept

```
┌─────────────────────────────────────┐
│                                     │
│    ⚖   LitigationOS               │
│                                     │
│  Scales of justice icon (⚖)        │
│  merged with circuit board lines    │
│  representing the "OS" aspect       │
│                                     │
│  Variants:                          │
│  • Full: Icon + "LitigationOS"     │
│  • Compact: Icon + "LitOS"         │
│  • Icon only: ⚖ with circuit       │
│  • Favicon: Simplified scales      │
│                                     │
└─────────────────────────────────────┘
```

---

## 2. Marketing Website Architecture (Next.js 15)

### Site Map

```
/                       — Hero + value prop + social proof
/features               — Feature deep-dives with screenshots
/features/evidence      — Evidence intelligence showcase
/features/filings       — Filing automation showcase
/features/timeline      — Timeline visualization showcase
/features/analytics     — Analytics dashboard showcase
/pricing                — Tier comparison table
/demo                   — Interactive demo (sandbox tenant)
/docs                   — Documentation (MDX)
/docs/getting-started   — Quick start guide
/docs/api               — API reference (OpenAPI)
/blog                   — Content marketing hub
/blog/[slug]            — Individual blog posts
/about                  — Mission, team, story
/contact                — Contact form + support
/legal/privacy          — Privacy policy
/legal/terms            — Terms of service
/changelog              — Release notes
```

### Hero Section Pattern

```tsx
export function Hero() {
  return (
    <section className="relative overflow-hidden bg-slate-950 py-24">
      {/* Animated graph background (reduced motion safe) */}
      <div className="absolute inset-0 opacity-20">
        <GraphBackground nodeCount={50} />
      </div>

      <div className="relative mx-auto max-w-5xl px-6 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-white sm:text-7xl">
          Your case.{' '}
          <span className="text-blue-400">Your system.</span>{' '}
          Your justice.
        </h1>

        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">
          The litigation intelligence platform that turns evidence chaos
          into court-ready filings. Built by a pro se litigant who needed it.
        </p>

        <div className="mt-10 flex items-center justify-center gap-4">
          <Link href="/demo" className="rounded-lg bg-blue-600 px-6 py-3
            text-white font-semibold hover:bg-blue-500 transition">
            Try the Demo
          </Link>
          <Link href="/docs/getting-started" className="rounded-lg border
            border-slate-600 px-6 py-3 text-slate-300 hover:bg-slate-800 transition">
            Documentation →
          </Link>
        </div>

        {/* Social proof */}
        <div className="mt-16 flex justify-center gap-8 text-slate-400 text-sm">
          <span>175K+ evidence items indexed</span>
          <span>•</span>
          <span>14 specialized engines</span>
          <span>•</span>
          <span>100% local processing</span>
        </div>
      </div>
    </section>
  );
}
```

### SEO Strategy

```tsx
// app/layout.tsx — Global metadata
export const metadata: Metadata = {
  title: {
    default: 'LitigationOS — Litigation Intelligence Platform',
    template: '%s | LitigationOS',
  },
  description: 'Turn evidence chaos into court-ready filings. The litigation intelligence platform for pro se litigants and small law firms.',
  keywords: ['litigation', 'legal tech', 'evidence management', 'court filings',
             'pro se', 'case management', 'legal intelligence'],
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://litigationos.com',
    siteName: 'LitigationOS',
    images: [{ url: '/og-image.png', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
    creator: '@litigationos',
  },
};
```

---

## 3. React Native Mobile App (Expo)

### Feature Roadmap

| Phase | Features | Timeline |
|-------|----------|----------|
| MVP | Case dashboard, evidence viewer, deadline alerts | Month 1-2 |
| v1.1 | Push notifications, offline evidence cache, camera capture | Month 3 |
| v1.2 | Voice memos, document scanner, share to case | Month 4 |
| v2.0 | Timeline viewer, search, filing tracker | Month 5-6 |
| v2.5 | Biometric lock, evidence annotation, witness notes | Month 7 |

### App Architecture (Expo Router)

```typescript
// app/_layout.tsx — Root layout with auth gate
import { Stack } from 'expo-router';
import { AuthProvider, useAuth } from '@/providers/auth';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5 * 60 * 1000, retry: 2 },
  },
});

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(tabs)" />
        </Stack>
      </AuthProvider>
    </QueryClientProvider>
  );
}
```

### Mobile Dashboard Screen

```typescript
// app/(tabs)/dashboard.tsx
import { View, ScrollView, RefreshControl } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { KPICard, DeadlineList, CaseSelector } from '@/components';

export default function Dashboard() {
  const { data: stats, refetch, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats(),
  });

  const { data: deadlines } = useQuery({
    queryKey: ['deadlines'],
    queryFn: () => api.getUpcomingDeadlines(14),
  });

  return (
    <ScrollView
      className="flex-1 bg-slate-950"
      refreshControl={<RefreshControl refreshing={isLoading} onRefresh={refetch} />}
    >
      <CaseSelector />

      <View className="flex-row flex-wrap gap-3 px-4 py-6">
        <KPICard
          title="Separation"
          value={stats?.separationDays}
          unit="days"
          trend="up"
          color="red"
        />
        <KPICard
          title="Evidence"
          value={stats?.evidenceCount}
          unit="items"
          color="blue"
        />
        <KPICard
          title="Filings"
          value={`${stats?.filingsReady}/${stats?.filingsTotal}`}
          unit="ready"
          color="green"
        />
        <KPICard
          title="Deadlines"
          value={stats?.urgentDeadlines}
          unit="urgent"
          color="orange"
        />
      </View>

      <DeadlineList deadlines={deadlines} />
    </ScrollView>
  );
}
```

### Push Notification System

```typescript
// services/notifications.ts
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

export async function registerForPushNotifications() {
  const { status } = await Notifications.requestPermissionsAsync();
  if (status !== 'granted') return null;

  const token = await Notifications.getExpoPushTokenAsync({
    projectId: process.env.EXPO_PROJECT_ID,
  });

  await api.registerPushToken(token.data);
  return token.data;
}

// Notification categories for litigation
Notifications.setNotificationCategoryAsync('deadline', [
  { identifier: 'view', buttonTitle: 'View Details', options: { opensAppToForeground: true } },
  { identifier: 'snooze', buttonTitle: 'Remind Tomorrow' },
]);

// Server-side notification triggers
const NOTIFICATION_TRIGGERS = {
  deadline_3day:   { title: '⚠️ Deadline in 3 days', priority: 'high' },
  deadline_today:  { title: '🔴 DEADLINE TODAY', priority: 'max' },
  deadline_passed: { title: '❌ DEADLINE MISSED', priority: 'max' },
  new_docket:      { title: '📋 New Docket Entry', priority: 'default' },
  filing_ready:    { title: '✅ Filing Ready for Review', priority: 'default' },
  evidence_added:  { title: '🔍 New Evidence Indexed', priority: 'low' },
};
```

---

## 4. Content Marketing Strategy

### Content Pillars

| Pillar | Topics | Format | Frequency |
|--------|--------|--------|-----------|
| Pro Se Guides | Filing basics, court procedures, evidence | Long-form blog + video | 2/month |
| Legal Tech | AI in litigation, tool comparisons | Blog + newsletter | 2/month |
| Case Studies | Success stories (anonymized) | Blog + social | 1/month |
| Product Updates | Features, changelog, roadmap | Blog + email | As released |
| Data Stories | Visualizations of legal patterns | Social + blog | 2/month |

### Blog Post Template (MDX)

```mdx
---
title: "How to Organize 10,000+ Evidence Items Without Losing Your Mind"
description: "A practical guide to evidence management for pro se litigants using systematic approaches."
date: "2026-04-15"
author: "LitigationOS Team"
tags: ["evidence", "pro-se", "organization"]
image: "/blog/evidence-organization.png"
---

# How to Organize 10,000+ Evidence Items

<Callout type="info">
  This guide is written for pro se litigants managing their own cases.
</Callout>

## The Problem

When you're representing yourself, evidence management becomes overwhelming fast...

<EvidenceScreenshot alt="LitigationOS evidence dashboard showing organized evidence by lane" />

## The Solution: Lane-Based Organization

Organize evidence by litigation lane — each lane represents a distinct legal claim...
```

### Email Marketing (Resend)

```typescript
import { Resend } from 'resend';

const resend = new Resend(process.env.RESEND_API_KEY);

// Drip campaign for new signups
const ONBOARDING_SEQUENCE = [
  { delay: 0, subject: 'Welcome to LitigationOS', template: 'welcome' },
  { delay: 1, subject: 'Import your first evidence', template: 'first-evidence' },
  { delay: 3, subject: 'Set up your case lanes', template: 'case-lanes' },
  { delay: 7, subject: 'Your first filing package', template: 'first-filing' },
  { delay: 14, subject: 'Advanced: Timeline & Analytics', template: 'advanced' },
];

async function sendOnboardingEmail(userId: string, step: number) {
  const user = await getUser(userId);
  const email = ONBOARDING_SEQUENCE[step];

  await resend.emails.send({
    from: 'LitigationOS <hello@litigationos.com>',
    to: user.email,
    subject: email.subject,
    react: renderTemplate(email.template, { user }),
  });
}
```

---

## 5. Growth Strategy for Legal Tech

### User Acquisition Funnel

```
AWARENESS (top of funnel)
  │ SEO blog posts, social media, legal forums, Reddit r/legaladvice
  │ Target: 10K monthly organic visitors
  ▼
INTEREST (consideration)
  │ Feature pages, demo video, comparison guides
  │ Target: 2K demo starts/month
  ▼
TRIAL (activation)
  │ Free tier signup, interactive demo, onboarding emails
  │ Target: 500 free signups/month
  ▼
CONVERSION (revenue)
  │ Usage triggers (hit evidence limit, need analytics)
  │ Target: 10% free→paid conversion (50/month)
  ▼
RETENTION (loyalty)
  │ Push notifications, deadline alerts, new features
  │ Target: 85% monthly retention
  ▼
REFERRAL (growth loop)
  │ "Powered by LitigationOS" in shared docs, referral credits
  │ Target: 20% users refer 1+ person
```

### SEO Keyword Targets

| Keyword Cluster | Volume | Difficulty | Content Type |
|-----------------|--------|------------|--------------|
| "pro se litigation software" | 500/mo | Low | Landing page |
| "how to organize evidence for court" | 2K/mo | Medium | Blog guide |
| "court filing checklist Michigan" | 800/mo | Low | Blog + tool |
| "evidence management software" | 1K/mo | High | Feature page |
| "litigation timeline tool" | 400/mo | Low | Feature page |
| "custody case evidence" | 3K/mo | Medium | Blog series |
| "free legal case management" | 5K/mo | High | Pricing page |

### Community Building

```
1. GitHub — Open-source core tools (evidence indexer, timeline builder)
   - Stars → credibility → organic traffic
   - Contributors → product improvement → community

2. Discord — "Pro Se Warriors" community
   - #general, #evidence-help, #filing-questions
   - Weekly Q&A sessions, template sharing

3. Reddit — r/legaladvice, r/familylaw, r/ProSeLitigation
   - Helpful answers linking to guides (not product spam)
   - "I built a tool that helps with [problem]" posts

4. YouTube — Walkthrough videos, legal explainers
   - "How I organized 175K evidence items" — data storytelling
   - Screen recordings of filing workflows
```

---

## 6. Data Storytelling with Litigation Visualizations

### Shareable Visualization Templates

```typescript
// Social-optimized chart exports (1200x630 for OG images)
const SHARE_CONFIGS = {
  timeline: {
    width: 1200, height: 630,
    title: 'Case Timeline — Key Events',
    branding: { logo: true, url: 'litigationos.com' },
  },
  adversaryNetwork: {
    width: 1200, height: 630,
    title: 'Adversary Connection Map',
    branding: { logo: true, watermark: true },
  },
  filingKanban: {
    width: 1200, height: 630,
    title: 'Filing Pipeline Status',
    branding: { logo: true },
  },
};

function exportForSocial(chart: ChartInstance, config: ShareConfig): Blob {
  const canvas = document.createElement('canvas');
  canvas.width = config.width;
  canvas.height = config.height;
  const ctx = canvas.getContext('2d');

  // Dark background
  ctx.fillStyle = '#0a0a0f';
  ctx.fillRect(0, 0, config.width, config.height);

  // Render chart
  chart.renderToCanvas(ctx, { margin: 40 });

  // Add branding
  if (config.branding.logo) {
    drawLogo(ctx, 40, config.height - 60);
  }
  if (config.branding.url) {
    ctx.fillStyle = '#64748b';
    ctx.font = '14px Inter';
    ctx.fillText(config.branding.url, config.width - 160, config.height - 20);
  }

  return new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
}
```

### Data Story Narratives

```
Story 1: "The Pattern of Escalation"
  → Timeline chart showing false allegations escalating over 18 months
  → Each point labeled with allegation type and debunking evidence
  → Shareable as social media image + blog post

Story 2: "The Judicial Connection Web"
  → Network graph showing McNeill-Hoopes-Ladas-Hoopes connections
  → Professional affiliations, shared addresses, case outcomes
  → Shareable for JTC complaint support

Story 3: "175K Evidence Items, One System"
  → Infographic showing evidence categorization breakdown
  → Before/after: chaos vs organized lanes
  → Marketing material for product landing page

Story 4: "The Separation Counter"
  → Dynamic counter showing days since last contact
  → Emotional impact visualization for appellate briefs
  → Updated daily on social media
```

---

## 7. App Store Optimization (ASO)

### iOS App Store Listing

```
Title: LitigationOS — Case Manager
Subtitle: Evidence, Filings & Deadlines

Keywords: litigation,evidence,court,filing,legal,case,pro se,
          deadline,custody,lawyer,attorney,document,organize

Description (first 3 lines — most important):
Manage your court case with confidence. LitigationOS helps you
organize evidence, track deadlines, and prepare filings — whether
you're a pro se litigant or a small law firm.

Screenshots (6 required):
1. Dashboard with KPI cards and deadline alerts
2. Evidence search with results and filters
3. Timeline visualization of case events
4. Filing Kanban board (Draft → Filed → Docketed)
5. Document scanner capturing evidence
6. Push notification for approaching deadline
```

### Google Play Listing

```
Short Description (80 chars):
Organize evidence, track deadlines, prepare filings for your case.

Feature Graphic: Dark background, scales icon, "Your Case. Your System."
```

---

## 8. Notification Infrastructure

### Multi-Channel Notification System

```typescript
interface NotificationPayload {
  userId: string;
  type: keyof typeof NOTIFICATION_TRIGGERS;
  data: Record<string, unknown>;
  channels: ('push' | 'email' | 'sms' | 'in_app')[];
  priority: 'low' | 'default' | 'high' | 'max';
}

async function sendNotification(payload: NotificationPayload) {
  const user = await getUser(payload.userId);
  const prefs = await getUserNotificationPrefs(user.id);

  const tasks = payload.channels
    .filter(ch => prefs[ch] !== false)
    .map(channel => {
      switch (channel) {
        case 'push':    return sendPushNotification(user, payload);
        case 'email':   return sendEmailNotification(user, payload);
        case 'sms':     return sendSMSNotification(user, payload);
        case 'in_app':  return createInAppNotification(user, payload);
      }
    });

  await Promise.allSettled(tasks);
}

// Deadline-aware scheduling
async function scheduleDeadlineNotifications(caseId: string) {
  const deadlines = await getDeadlines(caseId);

  for (const deadline of deadlines) {
    const daysUntil = daysBetween(new Date(), deadline.due_date);

    if (daysUntil <= 0) {
      await sendNotification({ type: 'deadline_passed', priority: 'max', ... });
    } else if (daysUntil <= 1) {
      await sendNotification({ type: 'deadline_today', priority: 'max', ... });
    } else if (daysUntil <= 3) {
      await sendNotification({ type: 'deadline_3day', priority: 'high', ... });
    } else if (daysUntil <= 7) {
      await sendNotification({ type: 'deadline_7day', priority: 'default', ... });
    }
  }
}
```

---

*SINGULARITY-creative-engine v1.0 — Brand + Marketing + Mobile + Growth — Apex Creative Platform*
