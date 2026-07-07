# Setting up CDK_DISPATCH_TOKEN — instructions for Tom

## What this is for

magiq-media's CI needs to push a small commit into `cdk-magiq-media` after
every build (bumping an image-tag config file), which is what triggers that
repo's deploy pipeline. GitHub's default `GITHUB_TOKEN` can't write to a
different repo, so this needs a dedicated access token scoped to just that.

## Steps

1. **Confirm access.** You'll need write access to
   `magiqsoftware/cdk-magiq-media` at minimum for the token to actually work.

2. **Create a fine-grained personal access token.**
   - Go to `github.com/settings/personal-access-tokens/new` (or: your profile
     photo (top right) → Settings → Developer settings → Personal access
     tokens → Fine-grained tokens → Generate new token).
   - **Token name:** `magiq-media-ci-cdk-dispatch`
   - **Expiration:** pick something deliberate — 90 days or up to a year.
     Note the date somewhere; it'll need rotating before it lapses.
   - **Resource owner:** `magiqsoftware`
   - **Repository access:** "Only select repositories" → check
     `cdk-magiq-media` only.
   - **Permissions → Repository permissions → Contents:** set to
     **"Read and write."** Leave every other permission on "No access" —
     this token doesn't need anything else.
   - Click **Generate token**.

3. **Copy the token value immediately.** It starts with `github_pat_...`.
   GitHub only shows it once — if you navigate away before copying it,
   you'll have to delete it and generate a new one.

4. **Check for an approval step.** If the org has fine-grained token
   approval policies on, you may see a banner saying the token is pending
   approval from an org owner. It won't work until that's approved.

5. **Add it as a repository secret in magiq-media** — do this yourself
   rather than sending the token to anyone else:
   - Go to `github.com/magiqsoftware/magiq-media/settings/secrets/actions`
   - Click **New repository secret**
   - **Name:** `CDK_DISPATCH_TOKEN`
   - **Value:** paste the token from step 3
   - Click **Add secret**

6. **Confirm it's set** by running (if you have `gh` CLI):
   ```
   gh secret list --repo magiqsoftware/magiq-media
   ```
   You should see `CDK_DISPATCH_TOKEN` listed with a recent "updated" time.
   (Secret values are never viewable after creation, including by you — this
   is just confirming the name exists.)

## If you can't complete step 5 yourself

If you don't have access to magiq-media's repo settings, let Chase know the
token needs to be added — but don't send the raw token value over Slack,
email, or chat. Use a password manager share, or hand it off directly and
have it entered straight into the GitHub secret field, not stored anywhere
in between.

## After this is done

Chase will confirm the secret is in place and will control the timing of
when the deploy pipeline actually goes live from there — nothing else is
needed from you for this part.
