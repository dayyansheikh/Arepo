# AREPO cloud economics and operations review (specialist report)

Retrieved 2026-10-10. Read-only research: nothing was signed up for, bought or deployed.

**Repo facts checked:** the remote `github.com/dayyansheikh/Arepo` is public (HTTP 200 unauthenticated). The scan cron in `scheduler-scan.yml` is currently commented out. Collect runs every 15 min, digest every 30 min, and the backup (`backup.yml`) runs weekly. The backup is a pg_dump stored as a GitHub artifact, and it was already cut back from daily because of the Supabase 5 GB egress limit. `PHASE_09_INFRASTRUCTURE.md` says the R2 backend is unimplemented and tier choices must use measured workloads. `data-dumps/` is 21 GB, and `df` shows **8.6 GiB free** on the laptop volume.

## 1. Price table

Tax note: Hetzner and Hetzner Object Storage prices are stated excl. VAT. US providers usually add VAT for UK/EU consumers. **Treat a possible 20% UK VAT (19% DE) as a flag, not a fact.** Where I convert EUR to USD I use an assumed ~1.15 USD/EUR (UNVERIFIED).

| Item | Price | Source (retrieved 2026-10-10) | Status |
|---|---|---|---|
| Cloudflare R2 Standard | $0.015/GB-mo; Class A $4.50/M; Class B $0.36/M; **egress free**; no minimum duration. Free tier: 10 GB-mo, 1M A, 10M B | developers.cloudflare.com/r2/pricing/ | Official |
| R2 Infrequent Access | $0.01/GB-mo; A $9/M; B $0.90/M; retrieval $0.01/GB; **30-day minimum**; no free tier | same | Official |
| Backblaze B2 | $6.95/TB-mo (~$0.00695/GB); egress free up to 3x average stored, then $0.01/GB; Class A/B/C free, Class D $0.004/10k after 2,500/day; first 10 GB free; no minimum duration or file size | backblaze.com/cloud-storage/pricing | Official |
| AWS S3 Standard (us-east-1) | $0.023/GB-mo; PUT/LIST $0.005/1k; GET $0.0004/1k | aws.amazon.com/s3/pricing (GET only; tables did not render); storage and PUT from cloudforecast.io, cloudburn.io | Partly third-party |
| S3 Standard-IA | $0.0125/GB-mo; $0.01/GB retrieval; 30-day min; 128 KB min object | AWS page (minimums); rates third-party | Partly third-party |
| S3 Glacier Instant Retrieval | $0.004/GB-mo; 90-day min | AWS page (min); rate from one third-party source | Rate UNVERIFIED |
| S3 Glacier Deep Archive | ~$0.00099/GB-mo; 180-day min; restore fees | AWS (min); rate third-party | Partly third-party |
| AWS internet egress | first 100 GB/mo free (aggregate); then ~$0.09/GB | AWS S3 page (100 GB); $0.09 UNVERIFIED | Partly UNVERIFIED |
| AWS EC2 t4g.small | $0.0168/h ≈ $12.26/mo | calculator.holori.com | Third-party |
| AWS EBS gp3 | $0.08/GB-mo | cloudburn.io, cloudchipr.com | Third-party |
| AWS public IPv4 | $0.005/h ≈ $3.65/mo, charged even when idle | usage.ai | Third-party |
| AWS NAT Gateway | $0.045/h (≈$32.85/mo) + $0.045/GB processed | cloudburn.io, costgoat.com | Third-party |
| AWS CloudWatch | Free: 5 GB logs, 10 metrics, 10 alarms, 3 dashboards. Logs ingest $0.50/GB; metric $0.30; alarm $0.10/mo | aws.amazon.com/cloudwatch/pricing | Official |
| AWS RDS Postgres db.t4g.micro | $0.016/h ≈ $11.68/mo Single-AZ (Multi-AZ 2x); gp3 storage ~$0.115/GB-mo | holori, infratally, selfhost.dev | Third-party |
| Hetzner Cloud (DE/FI), effective 15 Jun 2026 | CX23 €5.49 (2 vCPU/4 GB/40 GB); CX33 €8.49; CAX11 €5.99; CPX22 €19.49; CCX13 €42.99. **Excl. VAT and IPv4** | docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/ | Official |
| Hetzner Volumes, IPv4, included traffic | Not on the fetched pages | (none) | **UNVERIFIED** |
| Hetzner Storage Box BX11 1 TB | €3.20/mo excl. VAT (listing predates the 2026 increases) | whtop.com | **UNVERIFIED** |
| Hetzner Object Storage | Base fee includes 1 TB storage + 1 TB egress; S3 API calls free; objects <64 KB billed as 64 KB; excl. VAT. Base ~€6.49 per third-party | hetzner.com/storage/object-storage (no price shown) | Price UNVERIFIED |
| DigitalOcean Basic | $6/mo (1 vCPU/1 GB/25 GB/1 TB transfer); $4 for 512 MB | onedollarvps.com, frontdeskreview (re-checked 2026-09-03) | Third-party |
| Vultr Regular 1 GB | $5/mo; one tracker says the plan was removed | costbench.com, getpulsesignal.com | Conflicting |
| Supabase Free | 500 MB DB; 5 GB egress; pauses after 1 week of inactivity | supabase.com/pricing | Official |
| Supabase Pro | $25/mo incl. $10 compute credit (Micro); 8 GB disk, then $0.125/GB; 250 GB egress, then $0.09/GB; spend cap on by default. Small $15, Medium $60 | same | Official |
| Neon Launch | $0.106/CU-h; $0.35/GB-mo storage; no minimum; scale-to-zero. Free: 0.5–1 GB/project, 100 CU-h | neon.com/pricing | Official |
| Render Free web | Spins down after 15 min idle (~1 min cold start); 750 instance-h/mo; free Postgres expires after 30 days; **no free cron or workers** | render.com/docs/free | Official |
| Render Starter / cron | Starter ~$7/mo (512 MB/0.5 CPU); cron $0.00016/min on Starter, $1/mo minimum per cron service; 12 h max run | render.com/docs/cronjobs ($1 min); rates via deploycloud, livemy.app | Rates third-party |
| Vercel Hobby | $0; **personal, non-commercial only**; 1M invocations, 4 h active CPU, 100 GB transfer; hard cap, no overage | vercel.com/pricing | Official |
| Vercel Pro | $20/seat/mo with $20 usage credit; transfer 1 TB then $0.15/GB; invocations $0.60/M; default $200 on-demand budget, optional hard pause | same | Official |
| GitHub Actions | **Public repos: free on standard runners.** Private: 2,000 min (Free) / 3,000 (Pro); Linux 2-core $0.006/min. Self-hosted runners free | docs.github.com billing | Official |
| GitHub schedule reliability | "can be delayed during periods of high loads… start of every hour… some queued jobs may be dropped"; public-repo schedules auto-disable after 60 days without repo activity | docs.github.com events-that-trigger-workflows | Official |
| Resend | Free: 3,000/mo, **100/day**, 3 domains. Pro $20 (50k) | resend.com/pricing | Official |
| External disks (UK retail) | 2 TB portable SSD ~£190–245 (T7 Shield, X9); 4 TB portable HDD ~£120–140 | pricespy.co.uk, wearesync | Snapshot; NAND prices volatile |

## 2. Three architectures with costs

**Workloads.** Starting stock is 20 GB. Monthly growth: Low 50 GB/yr ≈ 4.2 GB/mo; Base 300 GB/yr = 25 GB/mo; High 2 TB/yr ≈ 167 GB/mo.

Stored GB = 20 + growth × month:

| | m1 | m6 | m12 | m36 |
|---|---|---|---|---|
| Low | 24 | 45 | 70 | 170 |
| Base | 45 | 170 | 320 | 920 |
| High | 187 | 1,020 | 2,020 | 6,020 |

Sanity check on Base: 4 scans/day × 16 MB ≈ 23 GB/yr. Book sweeps every 15 min × 4 MB ≈ 140 GB/yr. Add derived Parquet and you land near 300 GB/yr. Full-depth raw books push you toward High or beyond.

### A. Local-first

Laptop collection plus an external disk, a nightly batched upload to B2 (or R2), and the current free hosting (Vercel Hobby, Render Free, Supabase Free, Actions).

- **Offsite storage.** B2 = (GB − 10) × $0.00695. R2 = (GB − 10) × $0.015.
- **Local disk.** Low/Base use one 4 TB HDD at ~£130 ≈ $165, amortised over 36 months ≈ **$4.6/mo**. High needs about 6 TB at m36, so plan two drives ≈ $9/mo.
- **Operations.** Daily tarballs or Parquet partitions mean a few thousand PUTs per month. That is free on B2 and inside R2's 1M Class A free tier.
- **Restore egress.** Free on R2. Free on B2 within 3x of what you store.
- **Other lines.** Monitoring via Resend free alerts is $0. The only cost of the hosting tier is its reliability.

| A, USD/mo | m1 | m6 | m12 | m36 |
|---|---|---|---|---|
| Low (B2) | 0.10+4.6 = **4.7** | 0.24+4.6 = **4.8** | 0.42+4.6 = **5.0** | 1.11+4.6 = **5.7** |
| Base (B2) | 0.24+4.6 = **4.8** | 1.11+4.6 = **5.7** | 2.15+4.6 = **6.8** | 6.32+4.6 = **10.9** |
| Base (R2 instead) | 5.1 | 7.0 | 9.3 | 18.3 |
| High (B2) | 1.23+9 = **10.2** | 7.02+9 = **16.0** | 13.97+9 = **23.0** | 41.77+9 = **50.8** |
| High (R2 instead) | 11.7 | 24.2 | 39.2 | 99.2 |

**Hidden cost of A.** Upload time. Base is 25 GB/mo, about 3 h/mo at 20 Mbit/s up. High is 167 GB/mo, about 19 h/mo. Check whether your home ISP has a fair-use policy (UNVERIFIED).

**Scientific cost.** A laptop that sleeps, travels or loses network creates gaps that cannot be backfilled. GitHub Actions is officially documented as able to delay or drop scheduled runs.

### B. Lean hybrid (recommended target)

- **Collector.** One Hetzner CX23 (€5.49) runs collection, the scheduler and the cohort freezer under systemd timers. Add an IPv4 address (~€0.50, UNVERIFIED), so roughly €6.0 ≈ **$6.9/mo**, or $8.3 if 20% VAT applies.
- **Local buffer.** Keep only a 7-day buffer on the 40 GB disk and push hourly or daily Parquet batches to R2. R2 is zero-egress and matches the repo's planned R2 backend; B2 is about half the price per GB.
- **High workload.** Needs a CX33 (€8.49 + IPv4 ≈ $10.3) for the 80 GB disk: a week of buffer is about 39 GB.
- **Product side.** Supabase Free stays until its trigger, then Pro at $25. Render Free stays, or Starter at $7 to remove cold starts. Vercel Hobby stays: $0 if non-commercial, Pro at $20 otherwise.
- **Laptop.** Keeps a weekly pulled mirror on the external disk, which counts as the second copy (amortisation as in A).
- **Monitoring.** A dead-man's switch: the VM emails through Resend free if the last snapshot is older than 2× cadence, plus an external heartbeat. Healthchecks.io-style free tiers are UNVERIFIED.

| B, USD/mo (VM + R2 + disk; product tier free) | m1 | m6 | m12 | m36 |
|---|---|---|---|---|
| Low (CX23, R2) | 6.9+0.21+4.6 = **11.7** | 6.9+0.53+4.6 = **12.0** | 6.9+0.90+4.6 = **12.4** | 6.9+2.40+4.6 = **13.9** |
| Base (CX23, R2) | 6.9+0.53+4.6 = **12.0** | 6.9+2.40+4.6 = **13.9** | 6.9+4.65+4.6 = **16.2** | 6.9+13.65+4.6 = **25.2** |
| High (CX33, R2) | 10.3+2.66+9 = **22.0** | 10.3+15.15+9 = **34.5** | 10.3+30.15+9 = **49.5** | 10.3+90.15+9 = **109.5** |
| High (CX33, B2) | 20.5 | 26.3 | 33.3 | 61.1 |
| Add Supabase Pro + Render Starter | +$32 | +$32 | +$32 | +$32 |
| Add Vercel Pro (if commercial) | +$20 | +$20 | +$20 | +$20 |

**Supabase Pro overage.** The product DB should hold only derived summaries and never the archive. If it did reach, say, 20 GB, overage would be (20 − 8) × $0.125 = $1.50/mo. Storage is cheap here.

### C. Scalable managed (AWS us-east-1)

- **Compute.** EC2 t4g.small in a **public subnet, so no NAT gateway**: $12.26. Public IPv4: $3.65. EBS gp3 50 GB: $4.00.
- **Database.** RDS db.t4g.micro Single-AZ $11.68 + 20 GB gp3 $2.30.
- **Monitoring.** CloudWatch inside the free tier (logs <5 GB/mo with 14-day retention), ~$1.
- **Fixed cost ≈ $35/mo.**
- **High fixed cost.** t4g.medium (~$24.5, UNVERIFIED by doubling) + 200 GB EBS ($16) + RDS → **≈ $58/mo**.
- **S3 storage.** The last 3 months stay in Standard ($0.023). Older data moves to Glacier IR ($0.004, 90-day min). An optional Deep Archive DR copy costs $0.00099/GB.
- **Egress.** Analysis pulls to the laptop are free up to 100 GB/mo, then ~$0.09/GB (UNVERIFIED). High pulling 167 GB/mo is about (167 − 100) × 0.09 ≈ $6/mo.
- **Fargate plus private-subnet variant.** Adds a NAT gateway ($32.85) plus $0.045/GB on all API ingress: likely +$35–50/mo.

S3 arithmetic, Base:

| Month | Hot (Standard) | Cold (Glacier IR) | S3 total |
|---|---|---|---|
| m1 | 45 × 0.023 = 1.04 | none | 1.04 |
| m6 | 75 × 0.023 = 1.73 | 95 × 0.004 = 0.38 | 2.11 |
| m12 | 1.73 | 245 × 0.004 = 0.98 | 2.71 |
| m36 | 1.73 | 845 × 0.004 = 3.38 | 5.11 (+0.91 Deep Archive copy) |

| C, USD/mo | m1 | m6 | m12 | m36 |
|---|---|---|---|---|
| Low | 35+0.56 = **35.6** | 35+0.42 = **35.4** | 35+0.52 = **35.5** | 35+0.92 = **35.9** |
| Base | 35+1.04 = **36.0** | 35+2.11 = **37.1** | 35+2.71 = **37.7** | 35+5.11+0.91 = **41.0** |
| High | 58+4.3+6 = **68** | 58+13.6+6 = **78** | 58+17.6+6 = **82** | 58+33.6+6.0+6 = **104** |
| + Vercel Pro if commercial | +20 | +20 | +20 | +20 |

**Takeaway.** Storage is not the main cost at Low or Base. In every architecture, always-on compute dominates. At High, Glacier tiering on AWS ends up cheaper than R2 Standard by m36 ($33.6 vs $90). B2, or R2 Infrequent Access at $0.01, closes that gap.

## 3. Surprise-charge risks and guards

1. **Many small objects (the biggest risk for AREPO).** Suppose each of 43k books from every 15-min sweep becomes its own object. That is 43k × 96 × 30 ≈ 124M PUTs/mo: about **$557/mo on R2** (Class A $4.50/M) or **$620/mo on S3** ($0.005/1k). S3-IA's 128 KB minimum and Hetzner's 64 KB minimum also inflate small-object bills. *Guard:* only write batched Parquet/zstd files of at least 16–128 MB (one per sweep or per hour). Alert if objects/day exceeds 10k.
2. **Minimum storage durations.** S3-IA and R2-IA charge 30 days, Glacier IR 90 days, Deep Archive 180 days. Rewriting or compacting early pays twice. *Guard:* compact before transitioning, and only transition immutable, closed partitions.
3. **Egress.** AWS charges ~$0.09/GB after 100 GB. Supabase Free allows 5 GB; Pro allows 250 GB, then $0.09/GB. The repo already hit this with daily pg_dumps of ~9–11 GB/mo. B2 is free only up to 3x stored. *Guard:* do analysis next to the data (on the VM, or on the laptop against R2). Never back up the product DB by full logical dump at high frequency.
4. **NAT gateway** ($33/mo idle + $0.045/GB). *Guard:* use a public subnet with a security group. No NAT for a single collector.
5. **CloudWatch Logs** ($0.50/GB ingest). Verbose per-market logging at 276k markets × 4 scans can exceed 5 GB fast. *Guard:* set 7–14 day retention, log only summaries, and alarm on IncomingBytes.
6. **Idle IPv4 and orphaned EBS volumes or snapshots** keep billing after the instance is gone. *Guard:* tag everything, and do a monthly cost explorer review.
7. **Supabase.** The spend cap is on by default, but turning it off makes overage open-ended. Free projects pause after 1 week of inactivity. *Guard:* keep the cap on, and alert at 400 MB (80%).
8. **Vercel Pro.** Overage is uncapped, and the default on-demand budget is $200. *Guard:* lower the budget to about $10 and enable hard pause. Hobby is hard-capped but non-commercial.
9. **Render.** The $1 minimum per cron service, plus bandwidth on Hobby (third-party says 5 GB, then $0.15/GB, UNVERIFIED).
10. **Hetzner repricing.** Prices rose twice in 2026 (April and 15 June), and CPX/CCX more than doubled. *Guard:* stay on CX/CAX and re-check at renewal.
11. **Resend free: 100 emails/day.** An alert storm could exhaust it and silence later alerts. *Guard:* debounce alerts to one per incident per hour.
12. **Billing guards for every provider:** an AWS Budget at $50 with 50/80/100% alerts, the Vercel spend hard limit, the Supabase spend cap, and an R2/B2 storage alert at 2x the expected GB.

## 4. Triggers

**A → B.** The scientific trigger is effectively already met. Move when **any** of these is true:
- A frozen prospective protocol needs uninterrupted 00/06/12/18 UTC cohorts and/or 15-min collection, **and** a 14-day measured log shows a missed or late (>10 min after boundary) snapshot rate **>1%**, or any missed freeze boundary.
- GitHub `schedule` p95 start delay exceeds 10 min, or any run is dropped. GitHub documents that both can happen. Note too that the scan schedule is currently disabled.
- The laptop must stay awake on mains power to collect. In the planned week, if it is expected to be asleep, travelling or offline for more than 2% of collection slots, that already exceeds the threshold.
- Laptop free disk is below 20 GB or above 80% used. Today it has 8.6 GiB free, so this is already true. An external disk is needed regardless.

**What the fix costs.** A minimal always-on collector is about **€6/mo (~$7; ~$8.3 with VAT), roughly $85–100/yr**. DigitalOcean ($6) and Vultr ($5) are cheaper but have only 1 GB RAM and 25 GB disk, which risks out-of-memory failures on a 276k-market scan. A Render Starter worker ($7, 512 MB) is likely too small and has no persistent disk.

**What not fixing it costs.** One lost 6-hour cohort cannot be reconstructed under the project's own rules, so it is a permanent hole in the prospective sample. **$7/mo is trivially cheaper than one invalidated multi-week prospective panel.**

**B → C.** Move only on measured need:
- Public product traffic beyond the free tiers: Vercel Hobby limits (1M invocations, 100 GB transfer), or commercial use, which makes Vercel Pro mandatory. Or more than ~1,000 MAU with an availability expectation.
- The product DB exceeds Supabase Pro's 8 GB, or needs read replicas or PITR.
- The collector needs more than one host: the scan exceeds 50% of the cadence window, or CPU stays above 70% on CX33/CAX21.
- The archive exceeds about 5 TB, where Glacier-style tiering beats R2/B2.
- Compliance, team access control or a contractual SLA becomes necessary.

**Supabase Free → Pro.** DB above 400 MB, egress above 4 GB/mo, or any inactivity pause.

**Render Free → Starter.** Cold starts start to matter for users.

## 5. Recommendation

1. **Now, under A, near-zero cost.** Buy one external disk (about £120–140 for a 4 TB HDD; spend needs user approval) and move `data-dumps/` cold partitions onto it. Then start a batched offsite copy to B2 (cheapest, about $0.1–2/mo at Low/Base for year 1) or R2 (zero egress, matches the planned backend). The repo currently has **no offsite copy of 20 GB of irreplaceable evidence**. That is the single largest operational risk, and fixing it costs under $1/mo of storage.
2. **Before any new prospective freeze, move to B.** Run one Hetzner CX23/CAX11 (~€6/mo) as the canonical collector with systemd timers, a 7-day local buffer, hourly batched Parquet to R2/B2 and a dead-man's-switch email. Keep Vercel Hobby, Render Free and Supabase Free until their triggers fire. Expected total over the first year at Base: **about $12–16/mo** (plus $32 if the product tier is upgraded). The laptop becomes the analysis machine and second copy, not the clock.
3. **Defer C.** At AREPO's scale it costs 2–3x B for availability guarantees the research does not need yet. Revisit only on the B → C triggers.

**Three least-certain assumptions**
1. **Workload size.** The Low/Base/High growth rates are planning figures, not measurements (Phase 9 explicitly needs measured volumes). Full-depth raw books could exceed High by 5–10x, which would change the B2-vs-R2-vs-Glacier choice.
2. **A 4 GB datacenter VM can do the job.** That means completing the 276k-market scan in about 7 min and the 43k-book sweep in about 80 s, **and that Polymarket public APIs do not rate-limit, block or geo-restrict datacenter IPs** (e.g. Hetzner DE/FI ranges). Untested. A one-day trial on the VM is the cheapest way to settle it.
3. **Prices, VAT and FX.** Hetzner repriced twice in 2026. Hetzner Volume, IPv4, Storage Box and Object Storage prices, and several AWS rates (Glacier IR, EC2, EBS, NAT, egress), are third-party or UNVERIFIED. The 20% VAT exposure and the ~1.15 USD/EUR rate are assumptions. Retail SSD prices are volatile because of NAND/DRAM supply.

## Sources (all retrieved 2026-10-10)

**Official:**
- [R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- [Backblaze B2 pricing](https://www.backblaze.com/cloud-storage/pricing)
- [AWS S3 pricing](https://aws.amazon.com/s3/pricing/)
- [AWS CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [Hetzner price adjustment](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)
- [Hetzner Object Storage](https://www.hetzner.com/storage/object-storage/)
- [Hetzner Storage Box](https://www.hetzner.com/storage/storage-box/)
- [Supabase pricing](https://supabase.com/pricing)
- [Neon pricing](https://neon.com/pricing)
- [Render free](https://render.com/docs/free)
- [Render cron](https://render.com/docs/cronjobs)
- [Vercel pricing](https://vercel.com/pricing)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub schedule event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Resend pricing](https://resend.com/pricing)

**Third-party:**
- [cloudforecast S3](https://www.cloudforecast.io/blog/amazon-s3-pricing-and-optimization-guide/)
- [cloudburn S3](https://cloudburn.io/blog/amazon-s3-pricing)
- [cloudburn NAT](https://cloudburn.io/blog/aws-nat-gateway-pricing)
- [usage.ai IPv4](https://www.usage.ai/blogs/aws/networking-cost/data-transfer-costs/)
- [Holori t4g.small](https://calculator.holori.com/aws/ec2/t4g.small/us-east-1)
- [Holori RDS](https://calculator.holori.com/aws/rds/db.t4g.micro)
- [infratally RDS](https://infratally.com/articles/aws-rds-pricing-explained-2026/)
- [cloudchipr EBS](https://cloudchipr.com/blog/aws-ebs-pricing)
- [wz-it Hetzner](https://wz-it.com/en/blog/hetzner-price-increase-june-2026-cpx-ccx-alternatives/)
- [whtop Hetzner](https://www.whtop.com/compare/dogado.de,hetzner)
- [onedollarvps DO](https://onedollarvps.com/pricing/digitalocean-pricing.html)
- [costbench Vultr](https://www.costbench.com/software/cloud-infrastructure/vultr/)
- [getpulsesignal Vultr](https://getpulsesignal.com/changes/vultr)
- [deploycloud Render](https://deploycloud-shopify.devcloudsoftware.com/blog/render-pricing)
- [livemy.app Render](https://livemy.app/blog/render-pricing)
- [PriceSpy UK](https://pricespy.co.uk/s/good-portable-ssd/)
- [wearesync X9](https://shop.wearesync.co.uk/crucial-x9-2-tb-black-ct2000x9ssd9.html)
