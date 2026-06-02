# AIS-OS Intake

This is the source-of-truth file for your AIOS. Fill it in by typing, voice-pasting (Wispr Flow / OS dictation), or running `/onboard` for a guided conversation. Whichever mode, this file is what `/onboard` reads to scaffold your Day-1 setup.

**Hard cap: 7 questions.** Each answerable in under 60 seconds. Don't overthink — you can edit and re-run `/onboard` any time.

---

## Q1 — Who are you, what do you sell, who do you sell it to?

Identity, offer, ICP. One paragraph each is fine.

```
Identity: MAGIQ Documents Software Development Team Leader. Responsible for guiding engineering delivery, shaping architecture, and ensuring the platform scales reliably across complex, enterprise-grade use cases.

Offer: Magiq Software builds secure, scalable document and records management platforms that enable organisations to manage content, metadata, workflows, and compliance requirements in a structured and auditable way.

ICP: Government agencies and large enterprises that manage high volumes of regulated records and require robust, compliant, and extensible systems to support their operational and regulatory needs.
```

---

## Q2 — Paste 1-2 things you've written recently. Don't edit them.

An email, a LinkedIn post, a DM, a doc — anything that sounds like you when you're not trying. **Paste verbatim.** Do not type these mid-conversation with Claude — chat-shaped samples are worse than no samples (voice contamination).

```
Sample 1 — Email (Office Add-in context):
Hey,

It's not an EXE, MSI, MSIX, or PWA type application. It's just an Office Web Addin.

The name could be as simple as:
MAGIQ Documents for Microsoft Office

Not sure which environment to use, but as long as it's up all the time and we just give them a simple account that should be fine. An account in a library they manage so they can perform all the actions available in the application.
```

```
Sample 2 — Email (environment/infra update):
Hi Tom,

Just an update on these:

✅ Deleted the following 3 tables, were created in code because an environment variable wasn't pointing at local:
migrations
media-collection
event-stream

🚫 SSL Policy - The React app we're using doesn't run over http for development - not sure what to do here

✅ S3 - Have updated these - The buckets were created manually and had no idea that setting existed, but looks very useful.
```

```
Sample 3 — Teams (hotfix coordination):
ok there is a branch hotfix/1.0.102. Do you want to pull that one down and check it out. I haven't pushed it as a nuget package until you're ready for it. I'll redeploy your Akshay environment now and let you know when it's done
```

```
Sample 4 — Teams (IIS deployment incident):
Just went through full list of ones with IIS module, fixed up:
Croydon - Needed to be enabled
Dalwallinu - Needed to be enabled (Enterprise storage only)
hbrc - Needed to be enabled (Enterprise storage only)
Katherine - Needed to be enabled
murweh - Had 1.0.15 error
uacac - Needed to be enabled (Enterprise storage only)
westdaly - Needed to be enabled
The IIS module installer seemed to work on some instances and not on others, same installer, different results. My guess is some servers allowed it to stop and start IIS, alter files and others didn't.

The first 3 I tested it on work, banana, balonne and barcaldinerc - from there I assumed the rest would work (naughty me)
```

---

## Q3 — What are your 2-3 biggest priorities for the next 90 days?

Quarterly priorities. Not yearly aspirations. Things that, if not done by July, would make you say "I wasted Q2."

```
1. Complete the magiq-media API
2. Implement tenant management and authentication
3. Implement user security and policies
```

---

## Q4 — Where does revenue actually land, and where is it tracked?

Multiple answers OK. Stripe? Skool? GoHighLevel? QuickBooks? A spreadsheet?

```
N/A — engineering team lead role, no revenue responsibility.
```

---

## Q5 — Where do you talk to customers, your team, and the outside world day-to-day?

Email (which one — Gmail / Outlook)? Slack? Teams? DMs (Skool / Discord / iMessage)? Phone?

```
Email: Outlook
Team/external comms: Microsoft Teams
Calendar: Outlook Calendar (inferred)
```

---

## Q6 — Where do meeting recordings, notes, and important docs live?

Granola? Otter? Fireflies? Google Drive? Notion? Dropbox? A folder on your desktop you keep meaning to organize?

```
Meeting recordings and notes: Notion (target — not yet set up)
Project specs and architecture docs: AIS-OS projects/ folder (this repo), under the relevant project subfolder
```

---

## Q7 — What's the one task that eats your week, and where do you currently track work?

The single biggest time-suck or recurring drudgery. Plus where tasks/projects live (ClickUp / Asana / Linear / Notion / a notebook).

```
Top pain: Managing DevOps tasks (Azure DevOps)
Work tracking: Azure DevOps
```

---

When this file is filled, run `/onboard` (or re-run it) and the wizard will scaffold your Day-1 file set: `context/`, `references/voice.md`, populated `connections.md`, and a filled `CLAUDE.md`.
