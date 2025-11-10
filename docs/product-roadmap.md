# VibeWP Product Roadmap

**Version:** 1.0
**Date:** 2025-11-10
**Status:** Active Development
**Planning Horizon:** 24 months

---

## Vision Statement

Build the **modern, developer-first WordPress VPS control panel** that agencies love - combining CLI power with SaaS convenience. Differentiate through superior migration quality, modern UX, and competitive pricing.

---

## Strategic Pillars

1. **CLI Excellence** - Best-in-class command-line experience
2. **Agency-First** - Features that drive agency recurring revenue
3. **Modern Stack** - Docker, Python, Caddy - no legacy tech debt
4. **Open Core** - Community trust through open source foundation
5. **Phased Growth** - CLI → Desktop → SaaS progression

---

## Current State (v0.1.0)

### Implemented Features (38 commands)

**Site Management (7 commands)**
- ✅ Site creation (FrankenPHP + OpenLiteSpeed)
- ✅ Site listing and info
- ✅ Site deletion with rollback
- ✅ Container logs viewing

**Domain Management (4 commands)**
- ✅ Add/remove domains
- ✅ Primary domain switching
- ✅ SSL status checking
- ✅ Caddy reverse proxy integration

**VPS Operations**
- ✅ Firewall management (4 commands)
- ✅ SSH configuration (5 commands)
- ✅ Security scanning (5 commands)
- ✅ System monitoring (7 commands)
- ✅ Backup operations (6 commands)

**Current Limitations:**
- Single VPS management only
- CLI only (no web interface)
- No site cloning/staging
- No batch operations
- No remote backup storage
- No team collaboration

---

## Phase 1: CLI Excellence (Months 1-3)

**Timeline:** Nov 2025 - Jan 2026
**Goal:** Establish developer community, validate core features
**Target:** 500+ GitHub stars, 100+ weekly active users

### Priority 1: Agency Essentials (CRITICAL)

#### 1.1 Multi-VPS Management
**Business Impact:** 95/100 | **Effort:** 2-3 weeks

```bash
vibewp vps add <name> <host> <user> <key-path>
vibewp vps list
vibewp vps switch <name>
vibewp vps remove <name>
vibewp vps test-connection <name>
```

**Requirements:**
- Store multiple VPS configs in `~/.vibewp/vps.yaml`
- Context switching (active VPS)
- All existing commands work against active VPS
- Connection pooling/caching

**Success Criteria:**
- Manage 10+ VPS from single CLI
- Switch between VPS in <1 second
- Connection retry logic with backoff

**Why Critical:** Mandatory for agency use case (manage multiple servers)

---

#### 1.2 Site Cloning & Staging
**Business Impact:** 90/100 | **Effort:** 3-4 weeks

```bash
vibewp site clone <source> <target> [--staging] [--db-only] [--files-only]
vibewp site push-to-production <staging-site> <production-site>
vibewp site sync <source> <target> --db-only
```

**Requirements:**
- **True cloning** (not fresh WP install + import)
- Copy Docker volumes (database + files)
- Update wp_options (siteurl, home)
- Search-replace domain in database
- Preserve plugins, themes, configs
- Option for staging subdomain (staging.example.com)

**Success Criteria:**
- Clone 1GB site in <5 minutes
- Zero data loss
- Automated domain replacement
- Works across VPS (with network transfer)

**Why Critical:** GridPane's #1 pain point - their cloning is broken

---

#### 1.3 Batch Operations
**Business Impact:** 85/100 | **Effort:** 2 weeks

```bash
vibewp batch backup --all-sites [--vps <name>] [--tag <tag>]
vibewp batch update-plugins --sites site1,site2 [--exclude staging_*]
vibewp batch update-wordpress --all-sites
vibewp batch restart --tag production
vibewp batch security-scan --all-sites --report
```

**Requirements:**
- Parallel execution (configurable workers)
- Progress reporting (per-site status)
- Error handling (continue on failure)
- Summary report at end
- Tag system for site grouping

**Success Criteria:**
- Process 50 sites in <10 minutes (backup)
- Show real-time progress
- Detailed error reporting

**Why Critical:** Agencies can't manage 50+ sites one-by-one

---

#### 1.4 Performance Testing
**Business Impact:** 85/100 | **Effort:** 1-2 weeks

```bash
vibewp performance test <site> [--report pdf|json|html]
vibewp performance benchmark <site> --tool gtmetrix|lighthouse|pingdom
vibewp performance compare <site1> <site2>
vibewp performance watch <site> --interval 1h --duration 24h
```

**Requirements:**
- Lighthouse CI integration
- Load time, TTFB, FCP, LCP metrics
- Performance score (0-100)
- PDF report generation
- Historical tracking

**Success Criteria:**
- Generate report in <2 minutes
- Professional PDF output
- Actionable recommendations

**Why Critical:** Agencies sell "performance optimization" services ($500-2K)

---

### Priority 2: Operational Efficiency

#### 1.5 Remote Backup Storage
**Business Impact:** 75/100 | **Effort:** 1-2 weeks

```bash
vibewp backup remote-config --provider s3 --bucket name --credentials ~/.aws/creds
vibewp backup create <site> --remote
vibewp backup list --remote
vibewp backup restore <site> <backup-id> --from remote
```

**Providers:**
- Amazon S3
- Backblaze B2
- Wasabi
- DigitalOcean Spaces

**Requirements:**
- Encrypted uploads
- Incremental backups
- Retention policies
- Download on-demand

---

#### 1.6 Monitoring & Health Checks
**Business Impact:** 70/100 | **Effort:** 2 weeks

```bash
vibewp monitor enable <site> --uptime --ssl-expiry --disk-space
vibewp monitor status [--all-sites]
vibewp monitor alerts --webhook <url> --email <email>
vibewp monitor test-alert <site>
```

**Requirements:**
- Uptime monitoring (HTTP checks)
- SSL expiry warnings (30/7/1 day)
- Disk space alerts (>85%)
- Container health checks
- Webhook/email notifications

---

### Phase 1 Deliverables

**Commands Added:** 30+ new commands
**Total Commands:** ~70 commands
**Documentation:** Full CLI reference, video tutorials
**Community:** GitHub README, contributing guide, Discord server

**Success Metrics:**
- GitHub stars: 500+
- Weekly active users: 100+
- Community members: 50+ (Discord)
- Documentation coverage: 100%

---

## Phase 2: Desktop Dashboard (Months 4-9)

**Timeline:** Feb 2026 - Jul 2026
**Goal:** Prove UI value, gather feedback, early revenue
**Target:** 1,000+ downloads, 50-100 paying users, $1K-2.5K MRR

### 2.1 Desktop Application (Electron/Tauri)

**Tech Stack:**
- Frontend: React + TypeScript
- Backend: Python FastAPI (local server)
- Desktop: Tauri (Rust) or Electron
- State: Zustand + React Query

**Features:**

#### Core Dashboard
- Multi-VPS management (visual switcher)
- Site list with status indicators
- Quick actions (restart, backup, logs)
- System resource graphs (CPU, RAM, disk)

#### Site Management UI
- Create site wizard (step-by-step)
- Domain manager (add/remove domains)
- SSL certificate viewer
- Container logs (live streaming)

#### Performance Dashboard
- Performance test results (charts)
- Historical performance tracking
- Recommendation cards

#### Backup Manager
- Visual backup timeline
- Drag-drop restore
- Remote storage configuration
- Scheduled backup calendar

#### Settings
- VPS connection manager
- Notification preferences
- Theme (light/dark mode)
- CLI integration toggle

### 2.2 Freemium Model

**Free Tier:**
- 1 VPS
- Unlimited sites
- All CLI features
- Desktop app with branding

**Pro Tier ($29 one-time):**
- Unlimited VPS
- Performance reports (PDF export)
- Priority support (email)
- No branding

**Success Criteria:**
- 5-10% conversion rate (free → pro)
- 50-100 paying users in 6 months
- NPS score: 50+

---

## Phase 3: SaaS Lite (Months 10-18)

**Timeline:** Aug 2026 - Mar 2027
**Goal:** Validate SaaS willingness to pay, team features
**Target:** 2,000+ users, 300-500 paid, $7.5K-15K MRR

### 3.1 Cloud-Hosted Dashboard (Optional)

**Architecture:**
- Web app: React SPA
- API: Python FastAPI
- Database: PostgreSQL
- Queue: Redis/Celery
- Hosting: AWS/DigitalOcean

**New Features:**

#### Team Collaboration
- User invitations (team members)
- Role-based access control (admin, developer, viewer)
- Audit logs (who did what)
- Shared VPS/site access

#### Multi-User Management
- Client portal (view-only access)
- Per-site permissions
- Activity feed

#### Advanced Monitoring
- Custom alert rules
- Slack/Discord integrations
- SMS alerts (Twilio)
- Status page generation

#### Reporting & Analytics
- Usage reports (bandwidth, storage)
- Uptime reports (99.9% SLA tracking)
- Performance trends
- Client-facing reports (PDF, white-labeled)

### 3.2 Subscription Model

**Free Tier:**
- 1 VPS
- 1 user
- Basic monitoring

**Pro Tier ($15/mo):**
- 3 VPS
- 3 users
- Advanced monitoring
- Performance reports
- Email support

**Agency Tier ($40/mo):**
- Unlimited VPS
- Unlimited users
- Team collaboration
- Client portal (5 clients)
- Priority support

**Enterprise Tier ($100+/mo):**
- Everything in Agency
- White-label branding
- SSO (SAML)
- SLA guarantee
- Dedicated support

### 3.3 Success Criteria

- Total users: 2,000+
- Paid users: 300-500
- MRR: $7.5K-15K
- Churn rate: <5% monthly
- NPS score: 60+
- Break-even: Month 18

---

## Phase 4: Full Platform (Months 18-24+)

**Timeline:** Apr 2027 - Oct 2027
**Goal:** Sustainable profitable SaaS, enterprise features
**Target:** 5,000+ users, 1,000+ paid, $35K-80K MRR

### 4.1 Advanced Features

#### White-Label Portal
```bash
vibewp portal create <agency-name> --logo ./logo.png
vibewp portal custom-domain --domain portal.agency.com
vibewp portal add-client <email> --sites site1,site2
```

- Custom branding (logo, colors)
- Custom domain (CNAME)
- Client self-service portal
- Branded email notifications

#### Git Integration
```bash
vibewp git connect <site> --repo https://github.com/...
vibewp git deploy <site> --branch main
vibewp git auto-deploy <site> --on-push
vibewp git rollback <site> --commits 3
```

- GitHub/GitLab/Bitbucket integration
- Webhook auto-deploy
- Deployment history
- Rollback to any commit

#### AI-Powered Features
```bash
vibewp ai analyze <site> --security --seo --performance
vibewp ai recommend <site> --optimize
vibewp ai troubleshoot <site> --issue "site slow"
vibewp ai content-audit <site>
```

- GPT-4 powered analysis
- Security vulnerability detection
- Performance optimization recommendations
- SEO auditing
- Cost optimization suggestions

#### Marketplace
- Site templates (agency starter kits)
- Plugin bundles
- Theme collections
- Third-party integrations
- Revenue sharing (70/30 split)

### 4.2 Enterprise Features

- SSO (SAML, OAuth)
- Advanced RBAC (custom roles)
- Audit trail (compliance)
- SLA guarantees (99.9% uptime)
- Dedicated account manager
- Custom onboarding
- API access (REST + GraphQL)

### 4.3 Success Metrics

- Total users: 5,000+
- Paid users: 1,000-2,000
- MRR: $35K-80K
- Net revenue retention: >100%
- CAC payback: <6 months
- Gross margin: >70%

---

## Feature Priority Matrix

### High Impact + Low Effort (Do First)

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Batch operations | 85 | 2 weeks | P0 |
| Remote backups | 75 | 2 weeks | P0 |
| Performance testing | 85 | 2 weeks | P0 |
| Monitoring/alerts | 70 | 2 weeks | P1 |

### High Impact + High Effort (Plan Carefully)

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Multi-VPS management | 95 | 3 weeks | P0 |
| Site cloning/staging | 90 | 4 weeks | P0 |
| Desktop dashboard | 80 | 8 weeks | P1 |
| Web dashboard (SaaS) | 90 | 12 weeks | P2 |
| Team collaboration | 75 | 6 weeks | P2 |
| White-label portal | 70 | 6 weeks | P3 |

### Low Impact (Deprioritize)

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Email setup tools | 50 | 2 weeks | P4 |
| Plugin marketplace | 45 | 8 weeks | P5 |
| CDN integration | 60 | 3 weeks | P3 |

---

## Technical Milestones

### Q4 2025 (Months 1-3)
- ✅ Multi-VPS management
- ✅ Site cloning infrastructure
- ✅ Batch operations framework
- ✅ Performance testing integration
- ✅ Remote backup providers

**Release:** v0.2.0 (CLI Excellence)

### Q1 2026 (Months 4-6)
- Desktop app MVP (Tauri)
- UI for site management
- Performance dashboard
- Backup manager UI
- Settings panel

**Release:** v0.5.0 (Desktop Beta)

### Q2 2026 (Months 7-9)
- Desktop app feature complete
- Freemium billing integration
- Documentation site
- Video tutorials
- Community Discord

**Release:** v1.0.0 (Desktop GA)

### Q3 2026 (Months 10-12)
- Web dashboard alpha
- User authentication (Auth0)
- Multi-tenancy architecture
- Team collaboration MVP
- Subscription billing (Stripe)

**Release:** v1.5.0 (SaaS Beta)

### Q4 2026 (Months 13-15)
- Web dashboard feature parity
- Advanced monitoring
- Client portal
- Reporting engine
- Email notifications

**Release:** v2.0.0 (SaaS GA)

### 2027 (Months 16-24)
- White-label features
- Git integration
- AI-powered tools
- Marketplace MVP
- Enterprise features

**Release:** v3.0.0 (Platform)

---

## Resource Requirements

### Phase 1 (Months 1-3)
- **Team:** 1 full-time developer
- **Budget:** $15K/month
  - Development: $12K
  - Infrastructure: $500
  - Tools: $500
  - Marketing: $2K

### Phase 2 (Months 4-9)
- **Team:** 1.5 FTE (1 dev + 0.5 designer)
- **Budget:** $20K/month
  - Development: $15K
  - Design: $3K
  - Infrastructure: $1K
  - Marketing: $1K

### Phase 3 (Months 10-18)
- **Team:** 3 FTE (2 devs + 1 designer/marketer)
- **Budget:** $35K/month
  - Development: $24K
  - Design/Marketing: $6K
  - Infrastructure: $2K
  - Support: $3K

### Phase 4 (Months 18-24)
- **Team:** 5 FTE (3 devs + 1 designer + 1 support)
- **Budget:** $50K/month
  - Development: $36K
  - Design: $6K
  - Support: $5K
  - Infrastructure: $3K

**Total Investment (24 months):** ~$750K

**Expected ROI:** Break-even at month 18-24, profitable by month 30

---

## Risk Mitigation

### Technical Risks

**Risk:** Multi-VPS management complexity
**Mitigation:** Start with SSH connection pooling, proven libraries (Paramiko)

**Risk:** Site cloning data loss
**Mitigation:** Extensive testing, rollback mechanisms, backup before clone

**Risk:** Desktop app distribution (code signing)
**Mitigation:** Budget for code signing certificates, use Tauri auto-updater

**Risk:** SaaS infrastructure costs at scale
**Mitigation:** Usage-based pricing, efficient architecture, caching

### Business Risks

**Risk:** Low free → paid conversion
**Mitigation:** A/B test pricing, feature gating, value demonstration

**Risk:** High customer acquisition cost
**Mitigation:** Content marketing, community building, word-of-mouth

**Risk:** Competitor response (price war)
**Mitigation:** Differentiate on quality (migration, UI), not just price

**Risk:** Support burden overwhelming small team
**Mitigation:** Excellent documentation, community support, tiered support

---

## Success Criteria by Phase

### Phase 1: CLI Excellence
- ✅ 500+ GitHub stars
- ✅ 100+ weekly active users
- ✅ 50+ community members
- ✅ <10 open bugs
- ✅ 100% command documentation

### Phase 2: Desktop Dashboard
- ✅ 1,000+ downloads
- ✅ 5-10% free → pro conversion
- ✅ 50-100 paying users
- ✅ $1K-2.5K MRR
- ✅ NPS 50+

### Phase 3: SaaS Lite
- ✅ 2,000+ total users
- ✅ 300-500 paid users
- ✅ $7.5K-15K MRR
- ✅ <5% monthly churn
- ✅ Break-even

### Phase 4: Full Platform
- ✅ 5,000+ total users
- ✅ 1,000+ paid users
- ✅ $35K-80K MRR
- ✅ >100% net retention
- ✅ 70%+ gross margin

---

## Go/No-Go Decision Points

### After Phase 1 (Month 3)
**Evaluate:**
- GitHub stars >500?
- Weekly users >100?
- Community engagement strong?

**Go:** Proceed to Phase 2 (Desktop)
**No-Go:** Pivot or sunset project

### After Phase 2 (Month 9)
**Evaluate:**
- Downloads >1,000?
- Paying users >50?
- Conversion rate >5%?

**Go:** Proceed to Phase 3 (SaaS)
**No-Go:** Remain desktop-only, adjust model

### After Phase 3 (Month 18)
**Evaluate:**
- MRR >$10K?
- Churn <5%?
- CAC payback <6 months?

**Go:** Proceed to Phase 4 (Platform)
**No-Go:** Optimize existing SaaS, slow growth

---

## Competitive Monitoring

**Quarterly Review:** Track competitor feature additions, pricing changes

**Key Competitors to Watch:**
- GridPane (market leader)
- RunCloud (value leader)
- SpinupWP (UX leader)
- Ploi (developer focused)

**Tracking Metrics:**
- Feature parity score (0-100%)
- Pricing competitiveness
- User reviews/sentiment
- Market share estimates

---

## Conclusion

**Roadmap Philosophy:** Phased validation over big bets

**Phase 1 Focus:** Build credibility, validate agency pain points
**Phase 2 Focus:** Prove UI value, establish revenue stream
**Phase 3 Focus:** Scale SaaS, achieve unit economics
**Phase 4 Focus:** Platform features, enterprise market

**Key Differentiators:**
1. Superior site cloning (solve GridPane pain)
2. Modern UI/UX (CLI + Desktop + Web)
3. Competitive pricing ($15-40 vs $125)
4. Developer-first approach
5. Open source foundation

**Next Steps:** Begin Phase 1 development (Multi-VPS + Cloning)

---

**Document Owner:** Product Management
**Last Updated:** 2025-11-10
**Next Review:** 2026-01-10 (Quarterly)
