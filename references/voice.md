# Voice Reference

Match this register when drafting. Don't fake Chase's voice on external content without showing a draft first.

## Register

- Direct opener — no warm-up, no preamble
- Short declarative sentences
- Lists over paragraphs when enumerating multiple items
- Uses ✅ / 🚫 for status lists
- Technical terms used precisely — no dumbing down, no over-explaining
- Admits uncertainty plainly ("not sure what to do here")
- Casual self-awareness ("naughty me")
- No corporate fluff, no sign-off pleasantries
- Casual-professional — relaxed tone, serious content

## Samples (verbatim — do not edit)

### Email 1 — Office Add-in context
```
Hey,

It's not an EXE, MSI, MSIX, or PWA type application. It's just an Office Web Addin.

The name could be as simple as:
MAGIQ Documents for Microsoft Office

Not sure which environment to use, but as long as it's up all the time and we just give them a simple account that should be fine. An account in a library they manage so they can perform all the actions available in the application.
```

### Email 2 — Environment/infra update
```
Hi Tom,

Just an update on these:

✅ Deleted the following 3 tables, were created in code because an environment variable wasn't pointing at local:
migrations
media-collection
event-stream

🚫 SSL Policy - The React app we're using doesn't run over http for development - not sure what to do here

✅ S3 - Have updated these - The buckets were created manually and had no idea that setting existed, but looks very useful.
```

### Teams — Hotfix coordination
```
ok there is a branch hotfix/1.0.102. Do you want to pull that one down and check it out. I haven't pushed it as a nuget package until you're ready for it. I'll redeploy your Akshay environment now and let you know when it's done
```

### Teams — IIS deployment incident
```
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
